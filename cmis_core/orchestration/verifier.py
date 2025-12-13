"""Verifier: GoalPredicate evaluation + Diff report generation.

Phase 1에서는 metric 단위 정책 게이트 결과(policy_check)를 Ledgers에 기록하고,
Verifier는 이를 기반으로 Goal 만족 여부를 판단합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cmis_core.policy_engine import PolicyEngine, PolicyBatchResult

from .goal import Condition, ConditionType, GoalSpec, PredicateType
from .ledgers import Ledgers


@dataclass(frozen=True)
class VerificationResult:
    satisfied: bool
    diff_report: Dict[str, Any]


class Verifier:
    """GoalPredicate 검증기"""

    def __init__(self, policy_engine: PolicyEngine) -> None:
        self.policy_engine = policy_engine

    def verify(self, goal: GoalSpec, ledgers: Ledgers, policy_id: str) -> VerificationResult:
        predicate = goal.predicate

        predicate_satisfied = self._evaluate_predicate(predicate.predicate_type, predicate.conditions, ledgers)

        # Additional gates (Phase 1 best-effort)
        lineage_missing_metrics = self._evidence_lineage_check(goal.required_metrics, ledgers)
        consistency_issues = self._consistency_check(goal.required_metrics, ledgers)

        satisfied = bool(predicate_satisfied) and (not lineage_missing_metrics) and (not consistency_issues)
        if satisfied:
            return VerificationResult(satisfied=True, diff_report={})

        diff = self._build_diff_report(
            goal,
            predicate.conditions,
            ledgers,
            policy_id,
            lineage_missing_metrics=lineage_missing_metrics,
            consistency_issues=consistency_issues,
        )
        return VerificationResult(satisfied=False, diff_report=diff)

    @staticmethod
    def _evaluate_predicate(predicate_type: PredicateType, conditions: List[Condition], ledgers: Ledgers) -> bool:
        results = [Verifier._check_condition(c, ledgers) for c in conditions]
        if predicate_type == PredicateType.ANY_OF:
            return any(results)
        return all(results)

    @staticmethod
    def _check_condition(condition: Condition, ledgers: Ledgers) -> bool:
        t = condition.type
        metric_id = str(condition.params.get("metric_id", ""))

        if t == ConditionType.METRIC_EXISTS:
            return metric_id in ledgers.project_ledger.metrics

        if t == ConditionType.VALUE_PRESENT:
            metric = ledgers.project_ledger.metrics.get(metric_id, {})
            vr = metric.get("value_record") or {}
            return (vr.get("point_estimate") is not None) or (vr.get("distribution") is not None)

        if t == ConditionType.POLICY_PASSED:
            metric = ledgers.project_ledger.metrics.get(metric_id, {})
            pc = metric.get("policy_check") or {}
            # PolicyEngine v2: PolicyCheckResult.to_dict() includes passed
            return bool(pc.get("passed", False))

        # Unknown condition type -> fail closed
        return False

    def _build_diff_report(
        self,
        goal: GoalSpec,
        conditions: List[Condition],
        ledgers: Ledgers,
        policy_id: str,
        *,
        lineage_missing_metrics: List[str],
        consistency_issues: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        missing_metrics: List[str] = []
        missing_values: List[str] = []
        failed_policy_metrics: List[str] = []

        for c in conditions:
            metric_id = str(c.params.get("metric_id", ""))
            if not metric_id:
                continue

            if c.type == ConditionType.METRIC_EXISTS and metric_id not in ledgers.project_ledger.metrics:
                if metric_id not in missing_metrics:
                    missing_metrics.append(metric_id)

            elif c.type == ConditionType.VALUE_PRESENT:
                metric = ledgers.project_ledger.metrics.get(metric_id, {})
                vr = metric.get("value_record") or {}
                if (vr.get("point_estimate") is None) and (vr.get("distribution") is None):
                    if metric_id not in missing_values:
                        missing_values.append(metric_id)

            elif c.type == ConditionType.POLICY_PASSED:
                metric = ledgers.project_ledger.metrics.get(metric_id, {})
                pc = metric.get("policy_check") or {}
                if not bool(pc.get("passed", False)):
                    if metric_id not in failed_policy_metrics:
                        failed_policy_metrics.append(metric_id)

        # Aggregate policy violation summary (best-effort)
        violation_summary: Dict[str, int] = {}
        for metric_id in failed_policy_metrics:
            pc = (ledgers.project_ledger.metrics.get(metric_id, {}).get("policy_check") or {})
            # "violations" is a list of dicts with gate_id
            for v in pc.get("violations", []):
                gate_id = v.get("gate_id", "unknown")
                violation_summary[gate_id] = violation_summary.get(gate_id, 0) + 1

        # Suggested actions extraction (best-effort)
        suggested_actions: List[Dict[str, Any]] = []
        for metric_id in failed_policy_metrics:
            pc = (ledgers.project_ledger.metrics.get(metric_id, {}).get("policy_check") or {})
            for v in pc.get("violations", []):
                suggested_actions.extend(v.get("suggested_actions", []))

        # Provide orchestration policy hints for UI/guardian scoreboard
        orch_policy = self.policy_engine.get_orchestration_policy(policy_id).to_dict()

        return {
            "goal_id": goal.goal_id,
            "missing_metrics": missing_metrics,
            "missing_values": missing_values,
            "failed_policy_metrics": failed_policy_metrics,
            "lineage_missing_metrics": list(lineage_missing_metrics),
            "consistency_issues": list(consistency_issues),
            "violation_summary": violation_summary,
            "suggested_actions": suggested_actions,
            "orchestration_policy": orch_policy,
        }

    @staticmethod
    def _evidence_lineage_check(required_metrics: List[str], ledgers: Ledgers) -> List[str]:
        """핵심 수치/주장이 evidence_id 또는 value_id로 역추적 가능한지 확인.

        Phase 1:
        - value_record.lineage.from_evidence_ids 또는 from_value_ids가 비어 있으면 실패로 간주합니다.
        - 실제 증거 강제/예외(policy prior 허용 등)는 PolicyEngine v2 규칙과 함께 Phase 2+에서 강화합니다.
        """
        missing: List[str] = []
        for metric_id in required_metrics:
            entry = ledgers.project_ledger.metrics.get(metric_id, {}) or {}
            vr = entry.get("value_record") or {}
            if not vr:
                continue
            lineage = vr.get("lineage") or {}
            from_evidence = lineage.get("from_evidence_ids") or []
            from_values = lineage.get("from_value_ids") or []
            if (not from_evidence) and (not from_values):
                missing.append(metric_id)
        return missing

    @staticmethod
    def _consistency_check(required_metrics: List[str], ledgers: Ledgers) -> List[Dict[str, Any]]:
        """간단한 consistency check (Phase 1 best-effort).

        - point_estimate와 distribution(min/max)이 함께 있을 때 범위 밖이면 inconsistency로 기록합니다.
        """
        issues: List[Dict[str, Any]] = []
        for metric_id in required_metrics:
            entry = ledgers.project_ledger.metrics.get(metric_id, {}) or {}
            vr = entry.get("value_record") or {}
            if not vr:
                continue
            pe = vr.get("point_estimate")
            dist = vr.get("distribution") or {}
            if pe is None or not isinstance(dist, dict):
                continue
            try:
                min_v = dist.get("min")
                max_v = dist.get("max")
                if (min_v is not None) and (pe < min_v):
                    issues.append({"metric_id": metric_id, "issue": "point_below_min", "point_estimate": pe, "min": min_v})
                if (max_v is not None) and (pe > max_v):
                    issues.append({"metric_id": metric_id, "issue": "point_above_max", "point_estimate": pe, "max": max_v})
            except Exception:
                continue
        return issues

