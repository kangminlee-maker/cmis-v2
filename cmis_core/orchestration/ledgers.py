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

    def record_project_insights_from_diff(self, diff_report: Dict[str, Any]) -> None:
        """Diff report를 기반으로 ProjectLedger의 evidence_plan/open_questions를 보강합니다.

        목적:
        - Verifier/Replanner가 발견한 결손(누락/lineage/consistency/policy)을
          프로젝트 단위 working-memory(ledger)에 남겨 UX/재실행에서 활용하도록 합니다.

        원칙:
        - best-effort (Phase 1): 타입이 예상과 다르면 fail-open(무시)합니다.
        - idempotent: 동일한 항목/질문은 중복 추가하지 않습니다.
        """
        if not isinstance(diff_report, dict):
            return

        # -------- evidence_plan normalize --------
        plan = self.project_ledger.evidence_plan
        if not isinstance(plan, dict):
            plan = {}

        items = plan.get("items")
        if not isinstance(items, list):
            items = []

        existing_keys = set()
        for it in items:
            if isinstance(it, dict):
                existing_keys.add((it.get("kind"), it.get("metric_id"), it.get("reason")))

        def add_item(item: Dict[str, Any]) -> None:
            if not isinstance(item, dict):
                return
            key = (item.get("kind"), item.get("metric_id"), item.get("reason"))
            if key in existing_keys:
                return
            items.append(item)
            existing_keys.add(key)

        # -------- open_questions normalize --------
        questions = self.project_ledger.open_questions
        if not isinstance(questions, list):
            questions = []

        def add_question(q: str) -> None:
            q = str(q or "").strip()
            if not q:
                return
            if q in questions:
                return
            questions.append(q)

        # -------- diff parsing --------
        missing_metrics = list(diff_report.get("missing_metrics") or [])
        missing_values = list(diff_report.get("missing_values") or [])
        failed_policy_metrics = list(diff_report.get("failed_policy_metrics") or [])
        lineage_missing_metrics = list(diff_report.get("lineage_missing_metrics") or [])
        consistency_issues = list(diff_report.get("consistency_issues") or [])

        for mid in missing_metrics:
            metric_id = str(mid)
            add_item({"kind": "compute_metric", "metric_id": metric_id, "reason": "missing_metric"})
            add_question(f"{metric_id}: metric 엔트리가 없습니다. 정의/산출식/데이터 소스를 확인해야 합니다.")

        for mid in missing_values:
            metric_id = str(mid)
            add_item({"kind": "compute_metric", "metric_id": metric_id, "reason": "missing_value"})
            add_question(f"{metric_id}: 값(point_estimate/distribution)이 없습니다. 계산을 위한 evidence 수집/재계산이 필요합니다.")

        for mid in lineage_missing_metrics:
            metric_id = str(mid)
            add_item({"kind": "collect_evidence", "metric_id": metric_id, "reason": "evidence_lineage_missing"})
            add_item({"kind": "compute_metric", "metric_id": metric_id, "reason": "evidence_lineage_missing"})
            add_question(f"{metric_id}: value_record.lineage가 비어 있습니다(from_evidence_ids/from_value_ids). 근거(evidence/value) 연결이 필요합니다.")

        for mid in failed_policy_metrics:
            metric_id = str(mid)
            add_item({"kind": "collect_evidence", "metric_id": metric_id, "reason": "policy_failed"})
            add_item({"kind": "compute_metric", "metric_id": metric_id, "reason": "policy_failed"})
            add_question(f"{metric_id}: policy gate 실패. violations/근거 및 remediation을 확인해야 합니다.")

        for it in consistency_issues:
            if not isinstance(it, dict):
                continue
            metric_id = str(it.get("metric_id") or "")
            issue = str(it.get("issue") or "unknown")
            if not metric_id:
                continue
            add_item({"kind": "compute_metric", "metric_id": metric_id, "reason": f"consistency:{issue}"})
            add_question(f"{metric_id}: consistency issue({issue}). point_estimate와 distribution 범위를 점검/재계산해야 합니다.")

        plan.setdefault("generated_by", "kernel_rules_v1")
        plan["items"] = items
        plan["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.project_ledger.evidence_plan = plan
        self.project_ledger.open_questions = questions

    def set_next_step_suggestion(self, suggestion: Dict[str, Any]) -> None:
        """UI/재계획 참고용 next step 제안"""
        self.progress_ledger.next_step_suggestion = dict(suggestion)
        self.progress_ledger.touch()

    def _refresh_goal_graph_metric_status(self, metric_id: str) -> None:
        """goal_graph 내 metric 노드의 상태를 현재 metrics 엔트리로부터 갱신합니다."""
        g = self.project_ledger.goal_graph
        if not isinstance(g, dict):
            return
        nodes = g.get("nodes")
        if not isinstance(nodes, list):
            return

        metric_id = str(metric_id or "")
        if not metric_id:
            return

        node: Optional[Dict[str, Any]] = None
        for n in nodes:
            if isinstance(n, dict) and str(n.get("id")) == metric_id and n.get("type") == "metric":
                node = n
                break
        if node is None:
            node = {"id": metric_id, "type": "metric", "data": {"metric_id": metric_id}}
            nodes.append(node)

        data = node.get("data")
        if not isinstance(data, dict):
            data = {}
            node["data"] = data

        entry = self.project_ledger.metrics.get(metric_id, {}) or {}
        vr = entry.get("value_record") or {}
        pc = entry.get("policy_check") or {}

        exists = metric_id in self.project_ledger.metrics
        value_present = (vr.get("point_estimate") is not None) or (vr.get("distribution") is not None)
        policy_passed = bool(pc.get("passed", False)) if isinstance(pc, dict) else False
        satisfied = bool(exists and value_present and policy_passed)

        data["metric_id"] = metric_id
        data["exists"] = exists
        data["value_present"] = value_present
        data["policy_passed"] = policy_passed
        data["satisfied"] = satisfied
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        g["updated_at"] = datetime.now(timezone.utc).isoformat()

    def _refresh_goal_graph_goal_summary(self) -> None:
        """goal_graph의 goal 노드 completion 요약을 갱신합니다."""
        g = self.project_ledger.goal_graph
        if not isinstance(g, dict):
            return
        nodes = g.get("nodes")
        if not isinstance(nodes, list):
            return

        goal_node: Optional[Dict[str, Any]] = None
        for n in nodes:
            if isinstance(n, dict) and n.get("type") == "goal":
                goal_node = n
                break
        if goal_node is None:
            return

        gdata = goal_node.get("data")
        if not isinstance(gdata, dict):
            gdata = {}
            goal_node["data"] = gdata

        required_metrics: List[str] = []
        plan = self.project_ledger.evidence_plan
        if isinstance(plan, dict) and isinstance(plan.get("required_metrics"), list):
            required_metrics = [str(x) for x in (plan.get("required_metrics") or [])]
        elif isinstance(gdata.get("required_metrics"), list):
            required_metrics = [str(x) for x in (gdata.get("required_metrics") or [])]
        else:
            required_metrics = [
                str(n.get("id"))
                for n in nodes
                if isinstance(n, dict) and n.get("type") == "metric" and n.get("id")
            ]

        metric_satisfied: Dict[str, bool] = {}
        for n in nodes:
            if not isinstance(n, dict) or n.get("type") != "metric":
                continue
            mid = str(n.get("id") or "")
            data = n.get("data") or {}
            if mid and isinstance(data, dict):
                metric_satisfied[mid] = bool(data.get("satisfied", False))

        satisfied = sum(1 for mid in required_metrics if metric_satisfied.get(mid, False))
        total = len(required_metrics)
        ratio = float(satisfied) / float(total) if total else 0.0

        gdata["completion"] = {"satisfied": satisfied, "total": total, "ratio": ratio}
        g["updated_at"] = datetime.now(timezone.utc).isoformat()

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
                self._refresh_goal_graph_metric_status(str(metric_id))
                self._refresh_goal_graph_goal_summary()

        # Budget update (best-effort)
        time_sec = result.get("time_sec")
        if isinstance(time_sec, (int, float)):
            self.progress_ledger.budgets["time_spent_sec"] = float(self.progress_ledger.budgets.get("time_spent_sec", 0.0)) + float(time_sec)
            self.progress_ledger.touch()

