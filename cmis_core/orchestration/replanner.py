"""Replanner: Diff report → Tasks.

Phase 1 전략:
- missing_metrics / missing_values: ComputeMetric
- failed_policy_metrics: CollectEvidence + ComputeMetric

LLM 기반 PlanPatch는 Phase 2+에서 추가합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import uuid

from .task import Task, TaskType


@dataclass(frozen=True)
class ReplanResult:
    tasks: List[Task]
    reason: str


class Replanner:
    """규칙 기반 재계획기"""

    def generate_tasks(self, diff_report: Dict[str, Any]) -> ReplanResult:
        missing_metrics = list(diff_report.get("missing_metrics", []))
        missing_values = list(diff_report.get("missing_values", []))
        failed_policy_metrics = list(diff_report.get("failed_policy_metrics", []))
        lineage_missing_metrics = list(diff_report.get("lineage_missing_metrics", []))
        consistency_issues = list(diff_report.get("consistency_issues", [])) or []
        inconsistent_metrics = [
            str(it.get("metric_id"))
            for it in consistency_issues
            if isinstance(it, dict) and it.get("metric_id")
        ]

        tasks: List[Task] = []

        # 1) 정책 실패 → Evidence 추가 수집 후 재계산
        if failed_policy_metrics:
            tasks.append(
                Task(
                    task_id=f"TASK-collect-evidence-{uuid.uuid4().hex[:8]}",
                    task_type=TaskType.COLLECT_EVIDENCE,
                    inputs={"target_metrics": failed_policy_metrics, "force_refresh": True},
                )
            )
            for mid in failed_policy_metrics:
                tasks.append(
                    Task(
                        task_id=f"TASK-compute-{mid}-{uuid.uuid4().hex[:6]}",
                        task_type=TaskType.COMPUTE_METRIC,
                        inputs={"metric_id": mid},
                    )
                )

        # 1b) Lineage 부족 → Evidence 수집 후 재계산 (Phase 1 best-effort)
        if lineage_missing_metrics:
            tasks.append(
                Task(
                    task_id=f"TASK-collect-evidence-lineage-{uuid.uuid4().hex[:8]}",
                    task_type=TaskType.COLLECT_EVIDENCE,
                    inputs={"target_metrics": lineage_missing_metrics, "force_refresh": False},
                )
            )
            for mid in lineage_missing_metrics:
                tasks.append(
                    Task(
                        task_id=f"TASK-compute-{mid}-{uuid.uuid4().hex[:6]}",
                        task_type=TaskType.COMPUTE_METRIC,
                        inputs={"metric_id": mid},
                    )
                )

        # 1c) Consistency issue → 재계산(또는 Phase 2에서 fusion)
        for mid in inconsistent_metrics:
            tasks.append(
                Task(
                    task_id=f"TASK-recompute-{mid}-{uuid.uuid4().hex[:6]}",
                    task_type=TaskType.COMPUTE_METRIC,
                    inputs={"metric_id": mid},
                )
            )

        # 2) metric 자체가 없거나 값이 비었으면 계산 시도
        compute_targets = []
        compute_targets.extend(missing_metrics)
        compute_targets.extend([m for m in missing_values if m not in compute_targets])

        for mid in compute_targets:
            tasks.append(
                Task(
                    task_id=f"TASK-compute-{mid}-{uuid.uuid4().hex[:6]}",
                    task_type=TaskType.COMPUTE_METRIC,
                    inputs={"metric_id": mid},
                )
            )

        reason = "diff_report 기반 재계획"
        if failed_policy_metrics:
            reason = "policy gate 실패 → evidence 재수집 + 재계산"
        elif lineage_missing_metrics:
            reason = "evidence lineage 부족 → evidence 수집 + 재계산"
        elif inconsistent_metrics:
            reason = "consistency issue → 재계산"
        elif missing_metrics or missing_values:
            reason = "missing metric/value → metric 계산"

        return ReplanResult(tasks=tasks, reason=reason)

