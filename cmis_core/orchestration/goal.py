"""Goal and predicate models for OrchestrationKernel.

Phase 1에서는 Query → Goal 변환을 규칙 기반으로 처리합니다.
향후 LLM 기반 Goal 해석은 PlanPatchProvider 단계에서 추가합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid


class PredicateType(str, Enum):
    """GoalPredicate 타입"""

    ALL_OF = "all_of"
    ANY_OF = "any_of"


class ConditionType(str, Enum):
    """Predicate 조건 타입"""

    METRIC_EXISTS = "metric_exists"
    VALUE_PRESENT = "value_present"
    POLICY_PASSED = "policy_passed"


@dataclass(frozen=True)
class Condition:
    """GoalPredicate 조건"""

    type: ConditionType
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoalPredicate:
    """검증 가능한 성공 조건(Goal Predicate)"""

    predicate_type: PredicateType
    conditions: List[Condition]


@dataclass(frozen=True)
class GoalSpec:
    """OrchestrationKernel이 사용하는 Goal 스펙 (Phase 1)"""

    goal_id: str
    name: str
    query: str
    required_metrics: List[str]
    workflow_hint: str
    usage: str
    predicate: GoalPredicate


class GoalBuilder:
    """규칙 기반 Query → Goal 변환기"""

    def build(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> GoalSpec:
        if context is None:
            context = {}

        usage = self._infer_usage(query)
        workflow_hint = self._infer_workflow_hint(usage)
        required_metrics = self._infer_required_metrics(query, usage)

        goal_id = f"GOL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        name = context.get("goal_name") or query.strip()[:80]

        predicate = self._default_predicate(required_metrics)

        return GoalSpec(
            goal_id=goal_id,
            name=str(name),
            query=query,
            required_metrics=required_metrics,
            workflow_hint=workflow_hint,
            usage=usage,
            predicate=predicate,
        )

    @staticmethod
    def _infer_usage(query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["기회", "발굴", "탐색", "opportunity", "explore"]):
            return "exploration"
        if any(k in q for k in ["전략", "의사결정", "선택", "strategy", "decision", "portfolio"]):
            return "decision"
        return "reporting"

    @staticmethod
    def _infer_workflow_hint(usage: str) -> str:
        if usage == "exploration":
            return "opportunity_discovery"
        if usage == "decision":
            return "strategy_design"
        return "structure_analysis"

    @staticmethod
    def _infer_required_metrics(query: str, usage: str) -> List[str]:
        q = query.upper()
        metrics: List[str] = []

        # Explicit market size keywords
        if "TAM" in q:
            metrics.append("MET-TAM")
        if "SAM" in q:
            metrics.append("MET-SAM")
        if "SOM" in q:
            metrics.append("MET-SOM")

        if metrics:
            return metrics

        # Default sets by usage
        if usage == "exploration":
            return ["MET-TAM", "MET-SAM"]
        if usage == "decision":
            return ["MET-Revenue", "MET-N_customers"]
        return ["MET-Revenue", "MET-N_customers", "MET-Avg_price_per_unit"]

    @staticmethod
    def _default_predicate(required_metrics: List[str]) -> GoalPredicate:
        conditions: List[Condition] = []
        for mid in required_metrics:
            conditions.append(Condition(type=ConditionType.METRIC_EXISTS, params={"metric_id": mid}))
            conditions.append(Condition(type=ConditionType.VALUE_PRESENT, params={"metric_id": mid}))
            conditions.append(Condition(type=ConditionType.POLICY_PASSED, params={"metric_id": mid}))

        return GoalPredicate(predicate_type=PredicateType.ALL_OF, conditions=conditions)

