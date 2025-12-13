"""Ledgers (Project/Progress) for OrchestrationKernel.

CMIS 철학상, 유한 컨텍스트 문제를 해결하기 위해 실행 상태는 명시적으로 기록되어야 합니다.
Phase 1에서는 run_store/ledger_store(정본)로 저장하고, Cursor UX에는 export(view)로 제공합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .task import Task, TaskStatus, TaskType


@dataclass
class ProjectLedger:
    """프로젝트 상태 뷰(Project Ledger).

    - Substrate(Stores/Graphs)의 정본(System of Record)을 직접 저장하지 않고,
      정본을 어떻게 묶어 읽을지에 대한 프로젝트 단위 인덱스/포인터 역할을 합니다.
    - Magentic-One의 "Task Ledger"(문제공간 작업기억)와 동일 계열 개념이지만,
      CMIS의 실행 단위 task/workflow step과의 혼선을 피하기 위해 Project Ledger를 정식 용어로 사용합니다.
    """

    # Problem-space "index/pointer" view (not the SoT itself)
    facts: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)

    # Goal & verification view
    goal_graph: Dict[str, Any] = field(default_factory=dict)
    success_predicates: List[Dict[str, Any]] = field(default_factory=list)

    # Scope/constraints for this run/project view
    scope: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Evidence planning + open questions
    evidence_plan: Dict[str, Any] = field(default_factory=dict)
    open_questions: List[str] = field(default_factory=list)

    # Substrate refs
    evidence_refs: List[str] = field(default_factory=list)
    value_refs: List[str] = field(default_factory=list)

    # metric_id -> {value_record, metric_eval, policy_check, evidence_summary}
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    artifact_refs: List[str] = field(default_factory=list)
    last_workflow_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": dict(self.facts),
            "assumptions": list(self.assumptions),
            "goal_graph": dict(self.goal_graph),
            "success_predicates": list(self.success_predicates),
            "scope": dict(self.scope),
            "constraints": dict(self.constraints),
            "evidence_plan": dict(self.evidence_plan),
            "open_questions": list(self.open_questions),
            "evidence_refs": list(self.evidence_refs),
            "value_refs": list(self.value_refs),
            "metrics": dict(self.metrics),
            "artifact_refs": list(self.artifact_refs),
            "last_workflow_result": self.last_workflow_result,
        }


@dataclass
class StepRecord:
    """ProgressLedger step 기록"""

    step_id: str
    call: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    result_ref: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "call": self.call,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_ref": self.result_ref,
            "error": self.error,
        }


@dataclass
class ProgressLedger:
    """프로세스 제어판 (예산/스톨/루프/스텝 이력)"""

    run_id: str
    role_id: str
    policy_id: str
    interface_id: str

    workflow_id: Optional[str] = None
    overall_status: str = "running"  # running|completed|failed|stalled

    step_index: int = 0
    step_status: str = "running"  # running|completed|failed|stalled (last step)

    steps: List[StepRecord] = field(default_factory=list)
    task_statuses: Dict[str, str] = field(default_factory=dict)

    stall_count: int = 0
    stall_counters: Dict[str, int] = field(default_factory=dict)
    loop_flags: Dict[str, bool] = field(default_factory=dict)

    last_engine_calls: List[Dict[str, Any]] = field(default_factory=list)
    last_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    diff_reports: List[Dict[str, Any]] = field(default_factory=list)
    next_step_suggestion: Optional[Dict[str, Any]] = None

    budgets: Dict[str, Any] = field(default_factory=lambda: {"time_spent_sec": 0.0, "llm_calls": 0})
    replanning_count: int = 0

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "role_id": self.role_id,
            "policy_id": self.policy_id,
            "interface_id": self.interface_id,
            "workflow_id": self.workflow_id,
            "overall_status": self.overall_status,
            "step_index": self.step_index,
            "step_status": self.step_status,
            "steps": [s.to_dict() for s in self.steps],
            "task_statuses": dict(self.task_statuses),
            "stall_count": self.stall_count,
            "stall_counters": dict(self.stall_counters),
            "loop_flags": dict(self.loop_flags),
            "last_engine_calls": list(self.last_engine_calls),
            "last_tool_calls": list(self.last_tool_calls),
            "diff_reports": list(self.diff_reports),
            "next_step_suggestion": self.next_step_suggestion,
            "budgets": dict(self.budgets),
            "replanning_count": self.replanning_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Ledgers:
    """ProjectLedger + ProgressLedger 컨테이너"""

    def __init__(self, project_ledger: ProjectLedger, progress_ledger: ProgressLedger) -> None:
        self.project_ledger = project_ledger
        self.progress_ledger = progress_ledger

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_ledger": self.project_ledger.to_dict(),
            "progress_ledger": self.progress_ledger.to_dict(),
        }

    def mark_task_status(self, task: Task, status: TaskStatus) -> None:
        self.progress_ledger.task_statuses[task.task_id] = status.value
        self.progress_ledger.touch()

    def add_step(self, step: StepRecord) -> None:
        self.progress_ledger.steps.append(step)
        self.progress_ledger.step_index = len(self.progress_ledger.steps)
        self.progress_ledger.step_status = step.status
        self.progress_ledger.touch()

    def increment_stall(self, key: str) -> int:
        self.progress_ledger.stall_counters[key] = self.progress_ledger.stall_counters.get(key, 0) + 1
        # aggregate
        self.progress_ledger.stall_count = max(self.progress_ledger.stall_counters.values() or [0])
        self.progress_ledger.touch()
        return self.progress_ledger.stall_counters[key]

    def reset_stall(self, key: str) -> None:
        if key in self.progress_ledger.stall_counters:
            self.progress_ledger.stall_counters[key] = 0
            self.progress_ledger.stall_count = max(self.progress_ledger.stall_counters.values() or [0])
            self.progress_ledger.touch()

    def record_diff_report(self, diff_report: Dict[str, Any]) -> None:
        """Verifier diff report를 ProgressLedger에 누적 기록"""
        self.progress_ledger.diff_reports.append(dict(diff_report))
        self.progress_ledger.touch()

    def set_next_step_suggestion(self, suggestion: Dict[str, Any]) -> None:
        """UI/재계획 참고용 next step 제안"""
        self.progress_ledger.next_step_suggestion = dict(suggestion)
        self.progress_ledger.touch()

    def apply_task_result(self, task: Task, result: Dict[str, Any]) -> None:
        """Task 결과를 Ledgers에 반영"""
        if task.task_type == TaskType.RUN_WORKFLOW:
            self.project_ledger.last_workflow_result = result.get("workflow_result")
            wf_id = task.inputs.get("workflow_id")
            if wf_id:
                self.progress_ledger.workflow_id = str(wf_id)

        elif task.task_type == TaskType.COLLECT_EVIDENCE:
            evidence_ids = result.get("evidence_ids", [])
            for eid in evidence_ids:
                if eid not in self.project_ledger.evidence_refs:
                    self.project_ledger.evidence_refs.append(eid)

        elif task.task_type == TaskType.COMPUTE_METRIC:
            metric_id = result.get("metric_id")
            if metric_id:
                self.project_ledger.metrics[str(metric_id)] = {
                    "value_record": result.get("value_record"),
                    "metric_eval": result.get("metric_eval"),
                    "policy_check": result.get("policy_check"),
                    "evidence_summary": result.get("evidence_summary"),
                }

        # Budget update (best-effort)
        time_sec = result.get("time_sec")
        if isinstance(time_sec, (int, float)):
            self.progress_ledger.budgets["time_spent_sec"] = float(self.progress_ledger.budgets.get("time_spent_sec", 0.0)) + float(time_sec)
            self.progress_ledger.touch()

