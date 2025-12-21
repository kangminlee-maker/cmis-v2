"""LLM ModelSelector (Phase 1).

목적(비개발자 설명):
- "어떤 작업(Task)을 어떤 모델로 실행할지"를 결정하는 커널입니다.
- 결정은 감(하드코딩/주석)이 아니라:
  1) 정책(PolicyEngine이 resolve한 effective_policy.llm)
  2) 모델 레지스트리(ModelRegistry)
  3) 태스크 스펙(TaskSpecRegistry)
  에 의해 결정됩니다.
- 동일한 입력(정책 digest + 레지스트리 digest + 요청)이면 결과는 항상 동일해야 합니다(결정적).

Phase 1 범위:
- bounded escalation(실패 유형별 모델 변경)은 Phase 2로 미룹니다.
- Phase 1은 "허용 집합 + capability + 기본 선호" 기반 1차 선택만 제공합니다.

설계 문서:
- dev/docs/architecture/CMIS_LLM_Model_Management_Design_v1.1.0.md (Section 6)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from cmis_core.digest import canonical_digest, sha256_hexdigest

from cmis_core.llm.model_registry import ModelRegistry, ModelSpec
from cmis_core.llm.policy_types import EffectivePolicy
from cmis_core.llm.task_spec_registry import TaskSpecRegistry


class ModelSelectionError(ValueError):
    """모델 선택 실패(정책/능력/예산 제약으로 후보가 없을 때)."""


@dataclass(frozen=True)
class SelectionRequest:
    """ModelSelector 입력(Phase 1).

    NOTE:
    - Phase 1에서는 call_intent/quality_target 등 힌트를 "정렬"에만 약하게 반영합니다.
    - prompt 길이 기반 비용 계산은 Phase 2에서 확장합니다.
    """

    task_type: str
    policy_ref: str
    effective_policy_digest: str

    # 의도/품질 힌트
    call_intent: str = "draft"  # draft|extract|judge|finalize|repair
    quality_target: str = "medium"  # low|medium|high

    # 실행 제약
    confidentiality: str = "public"  # public|internal|confidential
    budget_remaining_usd: float = 1.0
    max_latency_ms: Optional[int] = None

    # 반복 시도/실패 이력
    attempt_index: int = 0
    failure_codes: List[str] = field(default_factory=list)

    def to_digest_input(self) -> Dict[str, Any]:
        return {
            "task_type": str(self.task_type),
            "policy_ref": str(self.policy_ref),
            "effective_policy_digest": str(self.effective_policy_digest),
            "call_intent": str(self.call_intent),
            "quality_target": str(self.quality_target),
            "confidentiality": str(self.confidentiality),
            "budget_remaining_usd": float(self.budget_remaining_usd),
            "max_latency_ms": self.max_latency_ms,
            "attempt_index": int(self.attempt_index),
            "failure_codes": sorted({str(x) for x in (self.failure_codes or []) if str(x).strip()}),
        }


@dataclass(frozen=True)
class SelectionDecision:
    """ModelSelector 출력(Phase 1)."""

    decision_id: str
    model_id: str
    provider: str
    prompt_profile: str
    rationale_codes: List[str] = field(default_factory=list)
    estimated_cost_usd: Optional[float] = None
    registry_digest: str = ""
    task_spec_digest: str = ""
    effective_policy_digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": str(self.decision_id),
            "model_id": str(self.model_id),
            "provider": str(self.provider),
            "prompt_profile": str(self.prompt_profile),
            "rationale_codes": list(self.rationale_codes),
            "estimated_cost_usd": self.estimated_cost_usd,
            "registry_digest": str(self.registry_digest),
            "task_spec_digest": str(self.task_spec_digest),
            "effective_policy_digest": str(self.effective_policy_digest),
        }


class ModelSelector:
    """결정적 ModelSelector (Phase 1)."""

    def __init__(self, *, model_registry: ModelRegistry, task_specs: TaskSpecRegistry) -> None:
        self.model_registry = model_registry
        self.task_specs = task_specs

    def select(self, *, request: SelectionRequest, effective_policy: EffectivePolicy) -> SelectionDecision:
        """모델을 선택해 SelectionDecision을 반환합니다."""

        task_type = str(request.task_type or "").strip()
        if not task_type:
            raise ModelSelectionError("task_type is required")

        if str(request.effective_policy_digest) != str(effective_policy.effective_policy_digest):
            # digest mismatch는 호출자 버그이므로 즉시 실패시킵니다.
            raise ModelSelectionError("effective_policy_digest mismatch between request and effective_policy")

        llm = effective_policy.llm
        if task_type in set(llm.forbidden_tasks or []):
            raise ModelSelectionError(f"task '{task_type}' is forbidden by effective_policy.llm")

        reg_ref = self.model_registry.get_ref()
        spec_ref = self.task_specs.get_ref()

        # Candidate narrowing (deterministic)
        rationale: List[str] = []

        allow_models = set(str(x) for x in (llm.allow_models or []) if str(x).strip())
        if not allow_models:
            # Phase 1 안전 기본값: allow_models가 비어 있으면 아무 것도 허용하지 않습니다.
            raise ModelSelectionError("effective_policy.llm.allow_models is empty (no models allowed)")

        candidates: List[ModelSpec] = []
        for mid in sorted(allow_models):
            ms = self.model_registry.get_model(mid)
            if ms is not None:
                candidates.append(ms)
        if not candidates:
            raise ModelSelectionError("no candidates after allow_models filter")
        rationale.append("allowed_by_policy")

        # execution_profile filter
        profile = str(llm.execution_profile or "prod")
        cand2: List[ModelSpec] = []
        for ms in candidates:
            allowed = set(ms.availability.to_dict().get("allowed_profiles") or [])
            if profile in allowed:
                cand2.append(ms)
        candidates = cand2
        if not candidates:
            raise ModelSelectionError("no candidates after execution_profile filter")
        rationale.append("allowed_by_execution_profile")

        # task capability filter
        task_spec = self.task_specs.get_task_spec(task_type)
        cap_req = task_spec.required_capabilities
        cand3: List[ModelSpec] = []
        for ms in candidates:
            if not _meets_capabilities(ms, cap_req.to_dict()):
                continue
            cand3.append(ms)
        candidates = cand3
        if not candidates:
            raise ModelSelectionError("no candidates after required_capabilities filter")
        rationale.append("meets_required_capabilities")

        # budget filter (Phase 1: heuristic cost estimate)
        max_cost = float(llm.max_cost_per_call_usd)
        budget = float(request.budget_remaining_usd)
        cand4: List[Tuple[ModelSpec, Optional[float]]] = []
        for ms in candidates:
            est = _estimate_cost_usd(ms, request)
            if est is not None:
                if est > max_cost:
                    continue
                if est > budget:
                    continue
            cand4.append((ms, est))
        if not cand4:
            raise ModelSelectionError("no candidates after budget filter")
        rationale.append("within_budget")

        # preference ordering
        override = (llm.task_overrides or {}).get(task_type)
        preferred_models: List[str] = []
        prompt_profile = "default"
        if override is not None:
            preferred_models = list(override.preferred_models or [])
            prompt_profile = str(override.prompt_profile or "default")

        tier_pref = list(llm.default_tier_preference or [])

        ranked = sorted(
            cand4,
            key=lambda t: _rank_key(
                t[0],
                est_cost=t[1],
                preferred_models=preferred_models,
                tier_preference=tier_pref,
                quality_target=str(request.quality_target or "medium"),
            ),
        )
        chosen, chosen_est = ranked[0]

        if preferred_models and chosen.model_id in set(preferred_models):
            rationale.append("preferred_by_policy_task_override")
        else:
            rationale.append("chosen_by_tier_and_cost")

        decision_payload = {
            "request": request.to_digest_input(),
            "effective_policy": effective_policy.to_dict(),
            "model_registry_digest": reg_ref.registry_digest,
            "task_spec_digest": spec_ref.task_spec_digest,
            "chosen": {"model_id": chosen.model_id, "provider": chosen.provider, "prompt_profile": prompt_profile},
        }
        decision_digest = canonical_digest(decision_payload)
        decision_id = f"SEL-{sha256_hexdigest(decision_digest.encode('utf-8'))[:12]}"

        return SelectionDecision(
            decision_id=decision_id,
            model_id=str(chosen.model_id),
            provider=str(chosen.provider),
            prompt_profile=str(prompt_profile),
            rationale_codes=list(rationale),
            estimated_cost_usd=chosen_est,
            registry_digest=str(reg_ref.registry_digest),
            task_spec_digest=str(spec_ref.task_spec_digest),
            effective_policy_digest=str(effective_policy.effective_policy_digest),
        )


def _meets_capabilities(model: ModelSpec, req_caps: Dict[str, Any]) -> bool:
    """ModelSpec이 Task required_capabilities를 충족하는지 확인합니다."""

    caps = model.capabilities

    if "supports_json_mode" in req_caps:
        if bool(caps.supports_json_mode) != bool(req_caps["supports_json_mode"]):
            return False

    if "supports_tool_calling" in req_caps:
        if bool(caps.supports_tool_calling) != bool(req_caps["supports_tool_calling"]):
            return False

    if "multimodal" in req_caps:
        if bool(caps.multimodal) != bool(req_caps["multimodal"]):
            return False

    if "min_max_input_tokens" in req_caps:
        try:
            need = int(req_caps["min_max_input_tokens"])
        except Exception:
            need = 0
        if int(caps.max_input_tokens) < int(need):
            return False

    return True


def _estimate_cost_usd(model: ModelSpec, request: SelectionRequest) -> Optional[float]:
    """Phase 1 비용 추정(휴리스틱).

    NOTE:
    - prompt 토큰/출력 토큰을 실제로 모르면 정확한 비용 산정이 불가능합니다.
    - Phase 1에서는 "선택 가능한지"를 대략 판정할 수 있는 수준의 보수적 추정치만 제공합니다.
    """

    cm = model.cost_model
    # 무료 모델(또는 비용 정보가 없는 경우)은 None이 아니라 0.0으로 취급합니다.
    try:
        in_rate = float(cm.input_per_1m_tokens)
        out_rate = float(cm.output_per_1m_tokens)
    except Exception:
        return None

    # intent/quality_target 기반의 결정적 토큰 추정
    base_in = 1000
    base_out = 500

    intent = str(request.call_intent or "draft")
    if intent == "extract":
        base_in, base_out = 1200, 600
    elif intent == "judge":
        base_in, base_out = 1400, 400
    elif intent == "repair":
        base_in, base_out = 1600, 800
    elif intent == "finalize":
        base_in, base_out = 1200, 900

    qt = str(request.quality_target or "medium")
    if qt == "high":
        base_out = int(base_out * 1.5)
    elif qt == "low":
        base_out = int(base_out * 0.7)

    est = (base_in / 1_000_000.0) * in_rate + (base_out / 1_000_000.0) * out_rate
    # 소수점 6자리까지만 고정(결정성)
    return float(f"{est:.6f}")


def _rank_key(
    model: ModelSpec,
    *,
    est_cost: Optional[float],
    preferred_models: Sequence[str],
    tier_preference: Sequence[str],
    quality_target: str,
) -> Tuple[int, int, float, str]:
    """결정적 정렬 키.

    반환 키의 의미:
    - preferred_rank: policy task_overrides.preferred_models 순서(낮을수록 우선)
    - tier_rank: performance_tier가 tier_preference에서 얼마나 우선인지
    - cost_rank: (가능하면) 낮은 비용 우선
    - model_id: 최종 안정 tie-breaker
    """

    preferred = [str(x) for x in preferred_models if str(x).strip()]
    try:
        preferred_rank = preferred.index(str(model.model_id))
    except ValueError:
        preferred_rank = 10**6

    # quality_target을 tier_preference에 약하게 반영 (Phase 1: 단순)
    tp = [str(x) for x in tier_preference if str(x).strip()]
    tier = str(model.performance_tier or "")
    try:
        tier_rank = tp.index(tier)
    except ValueError:
        tier_rank = 10**6

    # 비용이 None이면 매우 비싸다고 가정
    cost_rank = float(est_cost) if est_cost is not None else 10.0

    return (int(preferred_rank), int(tier_rank), float(cost_rank), str(model.model_id))


