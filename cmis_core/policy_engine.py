"""
CMIS Policy Engine v2

목표:
- policies.yaml(v2)을 '정책 레지스트리/팩'으로 사용
- role/usage → mode(policy_id) 라우팅을 YAML로 선언
- mode = profiles(evidence/value/prior/convergence/orchestration) 조합
- gates 리스트로 "어떤 검증을 강제할지"를 선언
- PolicyEngine은:
  1) YAML 로딩
  2) mode → CompiledPolicy 컴파일(참조 해소)
  3) 엔진 힌트 제공(예: evidence 정책)
  4) 결과 평가(게이트 실행) + 구조화된 위반 리포트 생성

레거시(v1) 호환 없음.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import yaml

from cmis_core.digest import canonical_digest
from cmis_core.llm.policy_types import EffectivePolicy as LLMEffectivePolicy
from cmis_core.llm.policy_types import EscalationStep, LLMRoutingPolicy, LLMTaskOverride


# -----------------------------
# Exceptions
# -----------------------------

class PolicyError(RuntimeError):
    pass


class PolicyConfigError(PolicyError):
    pass


def _normalize_policy_ref(policy_ref: str) -> str:
    """policy_ref를 내부 policy_id로 정규화합니다.

    허용하는 입력 예:
    - "reporting_strict"
    - "policy:reporting_strict@v3"

    NOTE:
    - 현재 코드베이스에서는 policy_id와 policy_ref가 동일하게 쓰이는 경우가 많아,
      최소한의 정규화만 수행합니다.
    """

    s = str(policy_ref or "").strip()
    if s.startswith("policy:"):
        s = s.split("policy:", 1)[1].strip()
    if "@" in s:
        s = s.split("@", 1)[0].strip()
    return s


def _parse_llm_routing_policy(d: Dict[str, Any]) -> LLMRoutingPolicy:
    """llm_routing.yaml의 policy별 llm 블록을 LLMRoutingPolicy로 파싱합니다."""

    exec_profile = str(d.get("execution_profile", "prod") or "prod")
    try:
        max_cost = float(d.get("max_cost_per_call_usd", 0.01) or 0.01)
    except Exception:
        max_cost = 0.01

    tier_pref_raw = d.get("default_tier_preference") or ["accurate", "balanced", "fast"]
    tier_pref: List[str] = [str(x) for x in tier_pref_raw] if isinstance(tier_pref_raw, list) else ["accurate", "balanced", "fast"]

    allow_models_raw = d.get("allow_models") or ["gpt-4o-mini"]
    allow_models: List[str] = [str(x) for x in allow_models_raw] if isinstance(allow_models_raw, list) else ["gpt-4o-mini"]

    forbidden_raw = d.get("forbidden_tasks") or []
    forbidden_tasks: List[str] = [str(x) for x in forbidden_raw] if isinstance(forbidden_raw, list) else []

    overrides_raw = d.get("task_overrides") or {}
    overrides: Dict[str, LLMTaskOverride] = {}
    if isinstance(overrides_raw, dict):
        for task_type, ov in overrides_raw.items():
            if not isinstance(task_type, str) or not task_type.strip():
                continue
            ov_d = ov if isinstance(ov, dict) else {}
            pm_raw = ov_d.get("preferred_models") or []
            preferred_models: List[str] = [str(x) for x in pm_raw] if isinstance(pm_raw, list) else []
            prompt_profile = str(ov_d.get("prompt_profile", "default") or "default")

            ladder: List[EscalationStep] = []
            ladder_raw = ov_d.get("escalation_ladder") or []
            if isinstance(ladder_raw, list):
                for step in ladder_raw:
                    if not isinstance(step, dict):
                        continue
                    when = str(step.get("when") or "").strip()
                    nxt = step.get("next") or {}
                    nxt_d = nxt if isinstance(nxt, dict) else {}
                    model = str(nxt_d.get("model") or "").strip()
                    prompt_prof = str(nxt_d.get("prompt_profile") or "default").strip() or "default"
                    if when and model:
                        ladder.append(EscalationStep(when=when, next_model=model, next_prompt_profile=prompt_prof))

            overrides[str(task_type)] = LLMTaskOverride(
                preferred_models=preferred_models,
                prompt_profile=prompt_profile,
                escalation_ladder=ladder,
            )

    return LLMRoutingPolicy(
        execution_profile=exec_profile,
        max_cost_per_call_usd=float(max_cost),
        default_tier_preference=list(tier_pref),
        allow_models=list(allow_models),
        forbidden_tasks=list(forbidden_tasks),
        task_overrides=overrides,
    )


# -----------------------------
# Evaluation input models
# -----------------------------

@dataclass(frozen=True)
class EvidenceBundleSummary:
    """
    Evidence bundle summary for policy evaluation.

    - num_sources: number of distinct sources used
    - source_tiers_used: e.g. ["official", "web"]
    - max_age_days: maximum age among sources (days)
    """
    num_sources: int
    source_tiers_used: List[str]
    max_age_days: int

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EvidenceBundleSummary":
        return EvidenceBundleSummary(
            num_sources=int(d.get("num_sources", 0)),
            source_tiers_used=list(d.get("source_tiers_used", [])),
            max_age_days=int(d.get("max_age_days", 10**9)),
        )


@dataclass(frozen=True)
class MetricEval:
    """
    Metric evaluation summary for policy evaluation.

    - metric_id: e.g. "MET-TAM"
    - literal_ratio: proportion of direct evidence in the final estimate (0..1)
    - spread_ratio: uncertainty ratio of the final estimate (0..1). (CI width / mean, etc.)
    - confidence: model confidence score (0..1)
    - methods_used: list of method ids used (excluding or including fusion step)
    - prior_ratio: contribution ratio of prior component to the final estimate (0..1)
    - prior_types_used: e.g. ["pattern_benchmark", "learned_belief"]
    - convergence_ratio: disagreement ratio among multiple methods (0..1).
        Required when methods_required > 1. If None and required > 1 -> gate failure.
    """
    metric_id: str
    literal_ratio: float
    spread_ratio: Optional[float] = None
    confidence: float = 0.0
    methods_used: List[str] = field(default_factory=list)
    prior_ratio: float = 0.0
    prior_types_used: List[str] = field(default_factory=list)
    convergence_ratio: Optional[float] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MetricEval":
        return MetricEval(
            metric_id=str(d.get("metric_id", "")),
            literal_ratio=float(d.get("literal_ratio", 0.0)),
            spread_ratio=(None if d.get("spread_ratio") is None else float(d.get("spread_ratio"))),
            confidence=float(d.get("confidence", 0.0)),
            methods_used=list(d.get("methods_used", [])),
            prior_ratio=float(d.get("prior_ratio", 0.0)),
            prior_types_used=list(d.get("prior_types_used", [])),
            convergence_ratio=(None if d.get("convergence_ratio") is None else float(d.get("convergence_ratio"))),
        )


# -----------------------------
# Policy models (compiled)
# -----------------------------

@dataclass(frozen=True)
class EvidencePolicy:
    min_sources: int
    require_official_sources: bool
    allowed_source_tiers: List[str]
    max_age_days: int
    allow_web: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_sources": self.min_sources,
            "require_official_sources": self.require_official_sources,
            "allowed_source_tiers": list(self.allowed_source_tiers),
            "max_age_days": self.max_age_days,
            "allow_web": self.allow_web,
        }


@dataclass(frozen=True)
class ValuePolicy:
    min_literal_ratio: float
    max_spread_ratio: float
    min_confidence: float
    metric_specific: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def for_metric(self, metric_id: str) -> "ValuePolicy":
        """Apply metric-specific overrides

        Args:
            metric_id: Metric ID (e.g. "MET-TAM")

        Returns:
            ValuePolicy with metric-specific overrides applied
        """
        if metric_id not in self.metric_specific:
            return self

        overrides = self.metric_specific[metric_id]
        return ValuePolicy(
            min_literal_ratio=overrides.get("min_literal_ratio", self.min_literal_ratio),
            max_spread_ratio=overrides.get("max_spread_ratio", self.max_spread_ratio),
            min_confidence=overrides.get("min_confidence", self.min_confidence),
            metric_specific=self.metric_specific
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_literal_ratio": self.min_literal_ratio,
            "max_spread_ratio": self.max_spread_ratio,
            "min_confidence": self.min_confidence,
            "metric_specific": dict(self.metric_specific),
        }


@dataclass(frozen=True)
class PriorPolicy:
    allow_prior: bool
    max_prior_ratio: float
    allowed_prior_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allow_prior": self.allow_prior,
            "max_prior_ratio": self.max_prior_ratio,
            "allowed_prior_types": list(self.allowed_prior_types),
        }


@dataclass(frozen=True)
class MetricConvergenceRule:
    threshold: float
    methods_required: int

    def to_dict(self) -> Dict[str, Any]:
        return {"threshold": self.threshold, "methods_required": self.methods_required}


@dataclass(frozen=True)
class ConvergencePolicy:
    default_threshold: float
    default_methods_required: int
    metric_specific: Dict[str, MetricConvergenceRule]

    def rule_for(self, metric_id: str) -> MetricConvergenceRule:
        if metric_id in self.metric_specific:
            return self.metric_specific[metric_id]
        return MetricConvergenceRule(
            threshold=self.default_threshold,
            methods_required=self.default_methods_required,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_threshold": self.default_threshold,
            "default_methods_required": self.default_methods_required,
            "metric_specific": {k: v.to_dict() for k, v in self.metric_specific.items()},
        }


@dataclass(frozen=True)
class OrchestrationPolicy:
    stall_threshold: int
    allow_partial_replan: bool
    require_human_approval: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stall_threshold": self.stall_threshold,
            "allow_partial_replan": self.allow_partial_replan,
            "require_human_approval": self.require_human_approval,
        }


@dataclass(frozen=True)
class CompiledPolicy:
    policy_id: str
    description: str
    evidence: EvidencePolicy
    value: ValuePolicy
    prior: PriorPolicy
    convergence: ConvergencePolicy
    orchestration: OrchestrationPolicy
    gates: List[str]
    use_cases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "description": self.description,
            "evidence": self.evidence.to_dict(),
            "value": self.value.to_dict(),
            "prior": self.prior.to_dict(),
            "convergence": self.convergence.to_dict(),
            "orchestration": self.orchestration.to_dict(),
            "gates": list(self.gates),
            "use_cases": list(self.use_cases),
        }


# -----------------------------
# Gate results
# -----------------------------

@dataclass(frozen=True)
class GateViolation:
    gate_id: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "message": self.message,
            "details": dict(self.details),
            "suggested_actions": list(self.suggested_actions),
        }


@dataclass(frozen=True)
class PolicyCheckResult:
    policy_id: str
    passed: bool
    violations: List[GateViolation]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
        }


@dataclass(frozen=True)
class PolicyBatchResult:
    policy_id: str
    passed: bool
    by_metric: Dict[str, PolicyCheckResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "passed": self.passed,
            "by_metric": {k: v.to_dict() for k, v in self.by_metric.items()},
        }


GateFn = Callable[[CompiledPolicy, EvidenceBundleSummary, MetricEval], List[GateViolation]]


class GateRegistry:
    def __init__(self) -> None:
        self._gates: Dict[str, GateFn] = {}

    def register(self, gate_id: str, fn: GateFn) -> None:
        if gate_id in self._gates:
            raise PolicyError(f"Gate already registered: {gate_id}")
        self._gates[gate_id] = fn

    def run(self, gate_id: str, policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        if gate_id not in self._gates:
            raise PolicyError(f"Unknown gate_id: {gate_id}")
        return self._gates[gate_id](policy, evidence, metric)

    def available(self) -> List[str]:
        return sorted(self._gates.keys())


# -----------------------------
# PolicyEngine v2
# -----------------------------

class PolicyEngine:
    """
    CMIS PolicyEngine v2
    - loads policy_pack YAML
    - resolves policy_id via YAML routing
    - compiles policy_id into CompiledPolicy (profile deref)
    - evaluates Evidence/Metric outputs with gates
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        policies_path: Optional[Path] = None,
        llm_routing_path: Optional[Path] = None,
    ) -> None:
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = Path(project_root)

        if policies_path is None:
            policies_path = self.project_root / "config" / "policies.yaml"
        self.policies_path = Path(policies_path)

        if llm_routing_path is None:
            llm_routing_path = self.project_root / "config" / "policy_extensions" / "llm_routing.yaml"
        self.llm_routing_path = Path(llm_routing_path)

        self._pack = self._load_policy_pack(self.policies_path)
        self._compiled_cache: Dict[str, CompiledPolicy] = {}
        self._effective_policy_cache: Dict[str, LLMEffectivePolicy] = {}

        self.gates = GateRegistry()
        self._register_default_gates()

    # ---------- Public API ----------

    def list_policies(self) -> List[str]:
        return sorted(self._pack["modes"].keys())

    def resolve_policy_id(
        self,
        role_id: Optional[str] = None,
        usage: Optional[str] = None,
        override_policy_id: Optional[str] = None,
    ) -> str:
        """
        Determine policy_id by:
          1) override_policy_id
          2) usage routing
          3) role routing
          4) fallback
        """
        modes = self._pack["modes"]

        if override_policy_id:
            if override_policy_id not in modes:
                raise PolicyConfigError(f"override_policy_id not found: {override_policy_id}")
            return override_policy_id

        routing = self._pack.get("routing", {})
        by_usage = routing.get("by_usage", {})
        by_role = routing.get("by_role", {})
        fallback = routing.get("fallback", "decision_balanced")

        if usage and usage in by_usage:
            pid = by_usage[usage]
            if pid not in modes:
                raise PolicyConfigError(f"routing.by_usage maps to unknown policy: {usage} -> {pid}")
            return pid

        if role_id and role_id in by_role:
            pid = by_role[role_id]
            if pid not in modes:
                raise PolicyConfigError(f"routing.by_role maps to unknown policy: {role_id} -> {pid}")
            return pid

        if fallback not in modes:
            raise PolicyConfigError(f"routing.fallback maps to unknown policy: {fallback}")
        return fallback

    def get_policy(self, policy_id: str) -> CompiledPolicy:
        if policy_id not in self._compiled_cache:
            self._compiled_cache[policy_id] = self._compile(policy_id)
        return self._compiled_cache[policy_id]

    def resolve_effective_policy(self, policy_ref: str) -> LLMEffectivePolicy:
        """policy_ref를 해석하여 effective_policy(특히 llm 라우팅 포함)를 반환합니다.

        목적(비개발자 설명):
        - 정책은 사람이 보는 "모드 이름"이고, 실행은 "해석된 정책 결과"로 수행합니다.
        - 모델 선택은 이 결과(effective_policy.llm)에 의해 제한됩니다.

        결정성:
        - 동일 정책 + 동일 확장 설정이면 effective_policy_digest가 동일해야 합니다.
        - 캐시는 (policy_ref@digest)로 pinning 합니다.
        """

        policy_id = _normalize_policy_ref(policy_ref)
        base = self.get_policy(policy_id)

        ext = self._load_llm_routing_extension(self.llm_routing_path)
        policies = ext.get("policies", {}) if isinstance(ext, dict) else {}
        per_policy = policies.get(policy_id, {}) if isinstance(policies, dict) else {}
        llm_raw = per_policy.get("llm", {}) if isinstance(per_policy, dict) else {}
        llm_raw_dict = llm_raw if isinstance(llm_raw, dict) else {}

        llm = _parse_llm_routing_policy(llm_raw_dict)

        digest_input = {
            "policy_id": str(policy_id),
            "compiled_policy": base.to_dict(),
            "llm": llm.to_dict(),
        }
        eff_digest = canonical_digest(digest_input)
        cache_key = f"{policy_ref}@{eff_digest}"
        if cache_key in self._effective_policy_cache:
            return self._effective_policy_cache[cache_key]

        effective = LLMEffectivePolicy(policy_ref=str(policy_ref), effective_policy_digest=str(eff_digest), llm=llm)
        self._effective_policy_cache[cache_key] = effective
        return effective

    # Engine hint accessors
    def get_evidence_policy(self, policy_id: str) -> EvidencePolicy:
        return self.get_policy(policy_id).evidence

    def get_value_policy(self, policy_id: str) -> ValuePolicy:
        return self.get_policy(policy_id).value

    def get_prior_policy(self, policy_id: str) -> PriorPolicy:
        return self.get_policy(policy_id).prior

    def get_convergence_policy(self, policy_id: str) -> ConvergencePolicy:
        return self.get_policy(policy_id).convergence

    def get_orchestration_policy(self, policy_id: str) -> OrchestrationPolicy:
        return self.get_policy(policy_id).orchestration

    # Evaluation
    def evaluate_metric(
        self,
        policy_id: str,
        evidence: Union[EvidenceBundleSummary, Dict[str, Any]],
        metric: Union[MetricEval, Dict[str, Any]],
    ) -> PolicyCheckResult:
        policy = self.get_policy(policy_id)

        evidence_obj = evidence if isinstance(evidence, EvidenceBundleSummary) else EvidenceBundleSummary.from_dict(evidence)
        metric_obj = metric if isinstance(metric, MetricEval) else MetricEval.from_dict(metric)

        violations: List[GateViolation] = []
        for gate_id in policy.gates:
            violations.extend(self.gates.run(gate_id, policy, evidence_obj, metric_obj))

        passed = (len(violations) == 0)
        return PolicyCheckResult(policy_id=policy.policy_id, passed=passed, violations=violations)

    def evaluate_metrics(
        self,
        policy_id: str,
        evidence: Union[EvidenceBundleSummary, Dict[str, Any]],
        metrics: Sequence[Union[MetricEval, Dict[str, Any]]],
    ) -> PolicyBatchResult:
        by_metric: Dict[str, PolicyCheckResult] = {}
        all_passed = True
        for m in metrics:
            m_obj = m if isinstance(m, MetricEval) else MetricEval.from_dict(m)
            r = self.evaluate_metric(policy_id, evidence, m_obj)
            by_metric[m_obj.metric_id] = r
            all_passed = all_passed and r.passed
        return PolicyBatchResult(policy_id=policy_id, passed=all_passed, by_metric=by_metric)

    # Utility methods for Orchestration integration
    def extract_all_suggested_actions(
        self,
        result: Union[PolicyCheckResult, PolicyBatchResult],
    ) -> List[Dict[str, Any]]:
        """
        Extract all suggested_actions from check result.

        Useful for Replanner to convert violations into Tasks.

        Args:
            result: PolicyCheckResult or PolicyBatchResult

        Returns:
            List of suggested action dicts
        """
        actions: List[Dict[str, Any]] = []

        if isinstance(result, PolicyCheckResult):
            for violation in result.violations:
                actions.extend(violation.suggested_actions)

        elif isinstance(result, PolicyBatchResult):
            for metric_result in result.by_metric.values():
                for violation in metric_result.violations:
                    actions.extend(violation.suggested_actions)

        return actions

    def summarize_violations(
        self,
        result: Union[PolicyCheckResult, PolicyBatchResult],
    ) -> Dict[str, int]:
        """
        Summarize violations by gate_id.

        Args:
            result: PolicyCheckResult or PolicyBatchResult

        Returns:
            {gate_id: count}
        """
        summary: Dict[str, int] = {}

        if isinstance(result, PolicyCheckResult):
            for violation in result.violations:
                gate_id = violation.gate_id
                summary[gate_id] = summary.get(gate_id, 0) + 1

        elif isinstance(result, PolicyBatchResult):
            for metric_result in result.by_metric.values():
                for violation in metric_result.violations:
                    gate_id = violation.gate_id
                    summary[gate_id] = summary.get(gate_id, 0) + 1

        return summary

    def get_failed_metrics(
        self,
        result: PolicyBatchResult,
    ) -> List[str]:
        """
        Get list of metric_ids that failed policy check.

        Args:
            result: PolicyBatchResult

        Returns:
            List of metric_ids
        """
        failed = []
        for metric_id, metric_result in result.by_metric.items():
            if not metric_result.passed:
                failed.append(metric_id)
        return failed

    def dry_run_policy(
        self,
        policy_id: str,
        evidence: Union[EvidenceBundleSummary, Dict[str, Any]],
        metrics: Sequence[Union[MetricEval, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Dry-run policy check (preview without applying).

        Useful for testing policy changes or previewing violations.

        Args:
            policy_id: Policy ID
            evidence: Evidence summary
            metrics: List of metric evaluations

        Returns:
            {
                "would_pass": True/False,
                "violations_by_metric": {...},
                "summary": {...},
                "total_violations": N
            }
        """
        result = self.evaluate_metrics(policy_id, evidence, metrics)

        violations_by_metric = {}
        all_violations = []

        for metric_id, metric_result in result.by_metric.items():
            if not metric_result.passed:
                violations_by_metric[metric_id] = [v.to_dict() for v in metric_result.violations]
                all_violations.extend(metric_result.violations)

        return {
            "would_pass": result.passed,
            "policy_id": policy_id,
            "violations_by_metric": violations_by_metric,
            "summary": self.summarize_violations(result),
            "total_violations": len(all_violations),
            "failed_metrics": self.get_failed_metrics(result)
        }

    def register_custom_gate(self, gate_id: str, gate_fn: GateFn) -> None:
        """
        Register a custom gate function.

        Allows domain-specific validation logic.

        Args:
            gate_id: Unique gate identifier
            gate_fn: Gate function (policy, evidence, metric) -> List[GateViolation]

        Example:
            def my_custom_gate(policy, evidence, metric):
                violations = []
                if metric.metric_id == "MET-Revenue":
                    if "official" not in evidence.source_tiers_used:
                        violations.append(GateViolation(
                            gate_id="my_custom_gate",
                            message="Revenue requires official sources",
                            suggested_actions=[{"type": "fetch_official_sources"}]
                        ))
                return violations

            policy_engine.register_custom_gate("my_custom_gate", my_custom_gate)
        """
        self.gates.register(gate_id, gate_fn)

    # ---------- Internals ----------

    @staticmethod
    def _load_policy_pack(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"policies.yaml not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            raise PolicyConfigError(f"Failed to load policies.yaml: {e}")

        if "policy_pack" not in data:
            raise PolicyConfigError("policies.yaml must contain root key: policy_pack")

        pack = data["policy_pack"]
        if int(pack.get("schema_version", 0)) != 2:
            raise PolicyConfigError(f"Unsupported policy_pack.schema_version: {pack.get('schema_version')} (expected 2)")

        # Basic shape check
        for k in ["routing", "profiles", "modes"]:
            if k not in pack:
                raise PolicyConfigError(f"policy_pack missing required key: {k}")

        return pack

    @staticmethod
    def _load_llm_routing_extension(path: Path) -> Dict[str, Any]:
        """policy_extensions/llm_routing.yaml을 로드합니다(없으면 빈 확장으로 처리)."""

        if not path.exists():
            return {"schema_version": 1, "policies": {}}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            raise PolicyConfigError(f"Failed to load llm_routing.yaml: {e}")

        if not isinstance(data, dict):
            raise PolicyConfigError("llm_routing.yaml root must be a dict")

        sv = int(data.get("schema_version", 0) or 0)
        if sv != 1:
            raise PolicyConfigError(f"Unsupported llm_routing.yaml schema_version: {sv} (expected 1)")

        policies = data.get("policies", {}) or {}
        if not isinstance(policies, dict):
            raise PolicyConfigError("llm_routing.yaml.policies must be a dict")

        return {"schema_version": 1, "policies": policies}


    def _compile(self, policy_id: str) -> CompiledPolicy:
        modes = self._pack["modes"]
        if policy_id not in modes:
            raise PolicyConfigError(f"Unknown policy_id: {policy_id}")

        mode_def = modes[policy_id]
        profiles_ref = mode_def.get("profiles", {})
        gates = list(mode_def.get("gates", []))

        profiles_root = self._pack["profiles"]

        evidence = self._compile_profile(
            profiles_root,
            group_key="evidence_profiles",
            profile_id=profiles_ref.get("evidence"),
            parser=self._parse_evidence_policy,
            what=f"{policy_id}.profiles.evidence",
        )
        value = self._compile_profile(
            profiles_root,
            group_key="value_profiles",
            profile_id=profiles_ref.get("value"),
            parser=self._parse_value_policy,
            what=f"{policy_id}.profiles.value",
        )
        prior = self._compile_profile(
            profiles_root,
            group_key="prior_profiles",
            profile_id=profiles_ref.get("prior"),
            parser=self._parse_prior_policy,
            what=f"{policy_id}.profiles.prior",
        )
        convergence = self._compile_profile(
            profiles_root,
            group_key="convergence_profiles",
            profile_id=profiles_ref.get("convergence"),
            parser=self._parse_convergence_policy,
            what=f"{policy_id}.profiles.convergence",
        )
        orchestration = self._compile_profile(
            profiles_root,
            group_key="orchestration_profiles",
            profile_id=profiles_ref.get("orchestration"),
            parser=self._parse_orchestration_policy,
            what=f"{policy_id}.profiles.orchestration",
        )

        # Validate gate IDs early
        unknown_gates = [g for g in gates if g not in self.gates.available()]
        if unknown_gates:
            raise PolicyConfigError(
                f"Policy '{policy_id}' references unknown gates: {unknown_gates}. "
                f"Available: {self.gates.available()}"
            )

        return CompiledPolicy(
            policy_id=policy_id,
            description=str(mode_def.get("description", "")),
            evidence=evidence,
            value=value,
            prior=prior,
            convergence=convergence,
            orchestration=orchestration,
            gates=gates,
            use_cases=list(mode_def.get("use_cases", [])),
        )

    @staticmethod
    def _compile_profile(
        profiles_root: Dict[str, Any],
        group_key: str,
        profile_id: Optional[str],
        parser: Callable[[Dict[str, Any]], Any],
        what: str,
    ) -> Any:
        if not profile_id:
            raise PolicyConfigError(f"Missing profile id at {what}")
        group = profiles_root.get(group_key, {})
        if profile_id not in group:
            raise PolicyConfigError(f"Unknown profile '{profile_id}' in group '{group_key}' ({what})")
        return parser(group[profile_id])

    @staticmethod
    def _parse_evidence_policy(d: Dict[str, Any]) -> EvidencePolicy:
        return EvidencePolicy(
            min_sources=int(d.get("min_sources", 0)),
            require_official_sources=bool(d.get("require_official_sources", False)),
            allowed_source_tiers=list(d.get("allowed_source_tiers", [])),
            max_age_days=int(d.get("max_age_days", 10**9)),
            allow_web=bool(d.get("allow_web", True)),
        )

    @staticmethod
    def _parse_value_policy(d: Dict[str, Any]) -> ValuePolicy:
        metric_specific: Dict[str, Dict[str, float]] = {}
        ms = d.get("metric_specific", {}) or {}
        for metric_id, overrides in ms.items():
            metric_specific[str(metric_id)] = {
                k: float(v) for k, v in overrides.items()
                if k in ["min_literal_ratio", "max_spread_ratio", "min_confidence"]
            }

        return ValuePolicy(
            min_literal_ratio=float(d.get("min_literal_ratio", 0.0)),
            max_spread_ratio=float(d.get("max_spread_ratio", 1.0)),
            min_confidence=float(d.get("min_confidence", 0.0)),
            metric_specific=metric_specific,
        )

    @staticmethod
    def _parse_prior_policy(d: Dict[str, Any]) -> PriorPolicy:
        return PriorPolicy(
            allow_prior=bool(d.get("allow_prior", False)),
            max_prior_ratio=float(d.get("max_prior_ratio", 0.0)),
            allowed_prior_types=list(d.get("allowed_prior_types", [])),
        )

    @staticmethod
    def _parse_convergence_policy(d: Dict[str, Any]) -> ConvergencePolicy:
        metric_specific: Dict[str, MetricConvergenceRule] = {}
        ms = d.get("metric_specific", {}) or {}
        for metric_id, rule in ms.items():
            metric_specific[str(metric_id)] = MetricConvergenceRule(
                threshold=float(rule.get("threshold", 0.3)),
                methods_required=int(rule.get("methods_required", 1)),
            )
        return ConvergencePolicy(
            default_threshold=float(d.get("default_threshold", 0.3)),
            default_methods_required=int(d.get("default_methods_required", 1)),
            metric_specific=metric_specific,
        )

    @staticmethod
    def _parse_orchestration_policy(d: Dict[str, Any]) -> OrchestrationPolicy:
        return OrchestrationPolicy(
            stall_threshold=int(d.get("stall_threshold", 2)),
            allow_partial_replan=bool(d.get("allow_partial_replan", True)),
            require_human_approval=bool(d.get("require_human_approval", False)),
        )

    # ---------- Default gates ----------

    def _register_default_gates(self) -> None:
        self.gates.register("evidence_min_sources", self._gate_evidence_min_sources)
        self.gates.register("evidence_require_official_if_configured", self._gate_evidence_require_official_and_allowed_tiers)
        self.gates.register("evidence_max_age_days", self._gate_evidence_max_age_days)

        self.gates.register("value_min_confidence", self._gate_value_min_confidence)
        self.gates.register("value_literal_ratio", self._gate_value_literal_ratio)
        self.gates.register("value_spread_ratio", self._gate_value_spread_ratio)

        self.gates.register("prior_ratio_limit", self._gate_prior_ratio_and_types)
        self.gates.register("convergence_methods_required", self._gate_convergence_methods_required)

    @staticmethod
    def _gate_evidence_min_sources(policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        if evidence.num_sources >= policy.evidence.min_sources:
            return []
        return [
            GateViolation(
                gate_id="evidence_min_sources",
                message=f"Insufficient sources: {evidence.num_sources} < {policy.evidence.min_sources}",
                details={
                    "num_sources": evidence.num_sources,
                    "required_min_sources": policy.evidence.min_sources,
                    "metric_id": metric.metric_id,
                },
                suggested_actions=[
                    {"type": "fetch_more_evidence", "min_sources": policy.evidence.min_sources}
                ],
            )
        ]

    @staticmethod
    def _gate_evidence_require_official_and_allowed_tiers(policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        violations: List[GateViolation] = []

        tiers = set(evidence.source_tiers_used)
        allowed = set(policy.evidence.allowed_source_tiers)

        # disallowed tier
        disallowed = sorted(list(tiers - allowed))
        if disallowed:
            violations.append(
                GateViolation(
                    gate_id="evidence_require_official_if_configured",
                    message="Evidence includes disallowed source tiers",
                    details={"disallowed_tiers": disallowed, "allowed_tiers": sorted(list(allowed)), "metric_id": metric.metric_id},
                    suggested_actions=[{"type": "refetch_with_allowed_tiers", "allowed_tiers": sorted(list(allowed))}],
                )
            )

        # web not allowed
        if (not policy.evidence.allow_web) and ("web" in tiers):
            violations.append(
                GateViolation(
                    gate_id="evidence_require_official_if_configured",
                    message="Web sources are not allowed by evidence policy",
                    details={"metric_id": metric.metric_id},
                    suggested_actions=[{"type": "refetch_without_web"}],
                )
            )

        # official required
        if policy.evidence.require_official_sources and ("official" not in tiers):
            violations.append(
                GateViolation(
                    gate_id="evidence_require_official_if_configured",
                    message="Official sources required but not present in evidence bundle",
                    details={"metric_id": metric.metric_id, "tiers_used": sorted(list(tiers))},
                    suggested_actions=[{"type": "fetch_official_sources"}],
                )
            )

        return violations

    @staticmethod
    def _gate_evidence_max_age_days(policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        if evidence.max_age_days <= policy.evidence.max_age_days:
            return []
        return [
            GateViolation(
                gate_id="evidence_max_age_days",
                message=f"Evidence too old: max_age_days={evidence.max_age_days} > {policy.evidence.max_age_days}",
                details={"max_age_days": evidence.max_age_days, "allowed_max_age_days": policy.evidence.max_age_days, "metric_id": metric.metric_id},
                suggested_actions=[{"type": "refetch_recent_evidence", "max_age_days": policy.evidence.max_age_days}],
            )
        ]

    @staticmethod
    def _gate_value_min_confidence(policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        # Apply metric-specific overrides
        value_policy = policy.value.for_metric(metric.metric_id)

        if metric.confidence >= value_policy.min_confidence:
            return []
        return [
            GateViolation(
                gate_id="value_min_confidence",
                message=f"Confidence too low: {metric.confidence:.3f} < {value_policy.min_confidence:.3f}",
                details={"confidence": metric.confidence, "min_confidence": value_policy.min_confidence, "metric_id": metric.metric_id},
                suggested_actions=[{"type": "improve_evidence_or_methods", "hint": "increase sources or add independent estimation method"}],
            )
        ]

    @staticmethod
    def _gate_value_literal_ratio(policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        # Apply metric-specific overrides
        value_policy = policy.value.for_metric(metric.metric_id)

        if metric.literal_ratio >= value_policy.min_literal_ratio:
            return []
        return [
            GateViolation(
                gate_id="value_literal_ratio",
                message=f"Literal ratio too low: {metric.literal_ratio:.3f} < {value_policy.min_literal_ratio:.3f}",
                details={"literal_ratio": metric.literal_ratio, "min_literal_ratio": value_policy.min_literal_ratio, "metric_id": metric.metric_id},
                suggested_actions=[{"type": "fetch_more_direct_evidence"}],
            )
        ]

    @staticmethod
    def _gate_value_spread_ratio(policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        # Apply metric-specific overrides
        value_policy = policy.value.for_metric(metric.metric_id)

        # If spread_ratio is missing, treat as 0.0 (deterministic). If you want stricter behavior, fail here.
        spread = 0.0 if metric.spread_ratio is None else float(metric.spread_ratio)
        if spread <= value_policy.max_spread_ratio:
            return []
        return [
            GateViolation(
                gate_id="value_spread_ratio",
                message=f"Spread ratio too high: {spread:.3f} > {value_policy.max_spread_ratio:.3f}",
                details={"spread_ratio": spread, "max_spread_ratio": value_policy.max_spread_ratio, "metric_id": metric.metric_id},
                suggested_actions=[{"type": "reduce_uncertainty", "hint": "add evidence or add estimation method and reconcile"}],
            )
        ]

    @staticmethod
    def _gate_prior_ratio_and_types(policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        violations: List[GateViolation] = []

        if (not policy.prior.allow_prior) and (metric.prior_ratio > 0.0 or len(metric.prior_types_used) > 0):
            violations.append(
                GateViolation(
                    gate_id="prior_ratio_limit",
                    message="Prior usage is not allowed by policy",
                    details={"prior_ratio": metric.prior_ratio, "prior_types_used": list(metric.prior_types_used), "metric_id": metric.metric_id},
                    suggested_actions=[{"type": "rerun_without_prior", "policy_hint": "reporting_strict"}],
                )
            )
            return violations

        if metric.prior_ratio > policy.prior.max_prior_ratio:
            violations.append(
                GateViolation(
                    gate_id="prior_ratio_limit",
                    message=f"Prior ratio exceeds limit: {metric.prior_ratio:.3f} > {policy.prior.max_prior_ratio:.3f}",
                    details={"prior_ratio": metric.prior_ratio, "max_prior_ratio": policy.prior.max_prior_ratio, "metric_id": metric.metric_id},
                    suggested_actions=[{"type": "increase_evidence_share", "target_prior_ratio": policy.prior.max_prior_ratio}],
                )
            )

        allowed_types = set(policy.prior.allowed_prior_types)
        used_types = set(metric.prior_types_used)
        disallowed = sorted(list(used_types - allowed_types))
        if disallowed:
            violations.append(
                GateViolation(
                    gate_id="prior_ratio_limit",
                    message="Disallowed prior types used",
                    details={"disallowed_prior_types": disallowed, "allowed_prior_types": sorted(list(allowed_types)), "metric_id": metric.metric_id},
                    suggested_actions=[{"type": "rerun_with_allowed_prior_types", "allowed_prior_types": sorted(list(allowed_types))}],
                )
            )

        return violations

    @staticmethod
    def _gate_convergence_methods_required(policy: CompiledPolicy, evidence: EvidenceBundleSummary, metric: MetricEval) -> List[GateViolation]:
        rule = policy.convergence.rule_for(metric.metric_id)

        # Exclude non-method bookkeeping tokens if your ValueEngine includes them.
        methods = [m for m in metric.methods_used if m and m != "fusion_validation"]
        unique_methods = sorted(list(set(methods)))

        violations: List[GateViolation] = []

        if len(unique_methods) < rule.methods_required:
            violations.append(
                GateViolation(
                    gate_id="convergence_methods_required",
                    message=f"Insufficient independent methods: {len(unique_methods)} < {rule.methods_required}",
                    details={"methods_used": unique_methods, "methods_required": rule.methods_required, "metric_id": metric.metric_id},
                    suggested_actions=[{"type": "run_additional_method", "required": rule.methods_required}],
                )
            )
            return violations

        # If multiple methods required, we also require convergence_ratio.
        if rule.methods_required > 1:
            if metric.convergence_ratio is None:
                violations.append(
                    GateViolation(
                        gate_id="convergence_methods_required",
                        message="convergence_ratio missing for multi-method convergence check",
                        details={"metric_id": metric.metric_id, "methods_used": unique_methods, "threshold": rule.threshold},
                        suggested_actions=[{"type": "compute_convergence_ratio", "threshold": rule.threshold}],
                    )
                )
                return violations

            if float(metric.convergence_ratio) > rule.threshold:
                violations.append(
                    GateViolation(
                        gate_id="convergence_methods_required",
                        message=f"Methods do not converge: {float(metric.convergence_ratio):.3f} > {rule.threshold:.3f}",
                        details={"convergence_ratio": float(metric.convergence_ratio), "threshold": rule.threshold, "metric_id": metric.metric_id, "methods_used": unique_methods},
                        suggested_actions=[{"type": "refine_or_fuse_methods", "threshold": rule.threshold}],
                    )
                )

        return violations
