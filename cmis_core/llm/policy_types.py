"""LLM policy types (Phase 1).

이 모듈은 PolicyEngine이 산출하는 effective_policy.llm의 데이터 형식을 정의합니다.

목적(비개발자 설명):
- 정책(Policy)이 해석(resolve)된 결과를 코드에서 "구조화된 타입"으로 다루기 위해 사용합니다.
- ModelSelector는 YAML 파일을 직접 읽지 않고, PolicyEngine이 만든 EffectivePolicy만 입력으로 받습니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class EscalationStep:
    """에스컬레이션 단계(Phase 2 최소).

    when:
      - 예: "gate_failed:json_parseable"
    next:
      - model: 다음 시도에서 사용할 model_id
      - prompt_profile: 다음 시도에서 사용할 prompt profile
    """

    when: str
    next_model: str
    next_prompt_profile: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "when": str(self.when),
            "next": {"model": str(self.next_model), "prompt_profile": str(self.next_prompt_profile)},
        }


@dataclass(frozen=True)
class LLMTaskOverride:
    """task별 모델 선호/프롬프트 프로파일(Phase 1 최소)."""

    preferred_models: List[str] = field(default_factory=list)
    prompt_profile: str = "default"
    escalation_ladder: List[EscalationStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preferred_models": [str(x) for x in (self.preferred_models or []) if str(x).strip()],
            "prompt_profile": str(self.prompt_profile),
            "escalation_ladder": [s.to_dict() for s in (self.escalation_ladder or [])],
        }


@dataclass(frozen=True)
class LLMRoutingPolicy:
    """PolicyEngine이 resolve한 effective_policy.llm (Phase 1 최소)."""

    execution_profile: str = "prod"  # dev|test|prod
    max_cost_per_call_usd: float = 0.01
    default_tier_preference: List[str] = field(default_factory=lambda: ["accurate", "balanced", "fast"])
    allow_models: List[str] = field(default_factory=list)
    forbidden_tasks: List[str] = field(default_factory=list)
    task_overrides: Dict[str, LLMTaskOverride] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # allow_models/forbidden_tasks는 집합 성격이므로 정렬하여 결정성을 확보합니다.
        allow_models = sorted({str(x) for x in (self.allow_models or []) if str(x).strip()})
        forbidden_tasks = sorted({str(x) for x in (self.forbidden_tasks or []) if str(x).strip()})
        return {
            "execution_profile": str(self.execution_profile),
            "max_cost_per_call_usd": float(self.max_cost_per_call_usd),
            "default_tier_preference": [str(x) for x in (self.default_tier_preference or []) if str(x).strip()],
            "allow_models": allow_models,
            "forbidden_tasks": forbidden_tasks,
            "task_overrides": {k: v.to_dict() for k, v in sorted((self.task_overrides or {}).items(), key=lambda kv: str(kv[0]))},
        }


@dataclass(frozen=True)
class EffectivePolicy:
    """PolicyEngine이 산출한 resolved policy 결과(Phase 1 최소)."""

    policy_ref: str
    effective_policy_digest: str
    llm: LLMRoutingPolicy

    def to_dict(self) -> Dict[str, Any]:
        return {"policy_ref": str(self.policy_ref), "effective_policy_digest": str(self.effective_policy_digest), "llm": self.llm.to_dict()}


