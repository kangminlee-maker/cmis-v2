"""OrchestrationKernel: Objective-oriented Reconcile Loop runtime.

Phase 1 목표:
- Query → Goal(규칙 기반) 생성
- Diff → Tasks → Execute → Verify 루프 실행
- 실행 이벤트/결정 로그를 메모리로 유지하고, (추후) run_store/ledger_store로 영속화
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
import time
import uuid

from cmis_core.policy_engine import PolicyEngine
from cmis_core.workflow import WorkflowOrchestrator

from .executor import TaskExecutor
from .goal import GoalBuilder, GoalSpec
from .governor import Budget, Governor
from .ledgers import Ledgers, ProgressLedger, ProjectLedger, StepRecord
from .replanner import Replanner
from .task import Task, TaskQueue, TaskStatus, TaskType
from .verifier import Verifier, VerificationResult


class RunStoreLike(Protocol):
    """RunStore 인터페이스(부분) - stores 단계에서 구현"""

    def create_run(self, run: Dict[str, Any]) -> None: ...

    def append_event(self, run_id: str, event: Dict[str, Any]) -> None: ...

    def append_decision(self, run_id: str, decision: Dict[str, Any]) -> None: ...

    def finalize_run(self, run_id: str, status: str, summary: Dict[str, Any]) -> None: ...


class LedgerStoreLike(Protocol):
    """LedgerStore 인터페이스(부분) - stores 단계에서 구현"""

    def save_snapshot(self, run_id: str, project_ledger: Dict[str, Any], progress_ledger: Dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class RunRequest:
    """Cursor/Web/API 등 인터페이스에서 Kernel에 전달하는 단일 실행 요청"""

    query: str
    interface_id: str = "cursor_agent"
    role_id: Optional[str] = None
    policy_id: Optional[str] = None
    run_mode: str = "autopilot"  # autopilot|approval_required|manual
    budgets: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    run_id: str
    status: str  # success|incomplete|failed|stalled
    goal_satisfied: bool
    goal_id: str
    role_id: str
    policy_id: str
    interface_id: str
    iterations: int
    ledgers: Dict[str, Any]
    decision_log: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    error: Optional[str] = None


class OrchestrationKernel:
    """Reconcile 기반 Orchestration Kernel"""

    def __init__(
        self,
        *,
        project_root: Optional[Path] = None,
        workflow_orchestrator: Optional[WorkflowOrchestrator] = None,
        policy_engine: Optional[PolicyEngine] = None,
        task_executor: Optional[TaskExecutor] = None,
        run_store: Optional[RunStoreLike] = None,
        ledger_store: Optional[LedgerStoreLike] = None,
        enable_stub_source: bool = False,
    ) -> None:
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.project_root = Path(project_root)

        self.policy_engine = policy_engine or PolicyEngine(project_root=self.project_root)
        self.workflow_orchestrator = workflow_orchestrator or WorkflowOrchestrator(project_root=self.project_root)

        self.task_executor = task_executor or TaskExecutor(
            project_root=self.project_root,
            policy_engine=self.policy_engine,
            workflow_orchestrator=self.workflow_orchestrator,
            enable_stub_source=enable_stub_source,
        )

        self.goal_builder = GoalBuilder()
        self.verifier = Verifier(self.policy_engine)
        self.replanner = Replanner()
        self.governor = Governor(self.policy_engine)

        self.run_store = run_store
        self.ledger_store = ledger_store

    def execute(self, request: RunRequest) -> RunResult:
        run_id = self._new_run_id()
        started_at = datetime.now(timezone.utc).isoformat()

        # Role/Policy resolve
        role_id = request.role_id or self._infer_role_from_context(request.context)
        policy_id = request.policy_id or self.policy_engine.resolve_policy_id(role_id=role_id, usage=self._infer_usage(request.query))

        project_ledger = ProjectLedger(facts=dict(request.context))
        progress_ledger = ProgressLedger(
            run_id=run_id,
            role_id=role_id,
            policy_id=policy_id,
            interface_id=request.interface_id,
        )
        ledgers = Ledgers(project_ledger=project_ledger, progress_ledger=progress_ledger)

        events: List[Dict[str, Any]] = []
        decision_log: List[Dict[str, Any]] = []

        def emit_event(event_type: str, payload: Dict[str, Any]) -> None:
            ev = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": event_type,
                "payload": payload,
            }
            events.append(ev)
            if self.run_store:
                self.run_store.append_event(run_id, ev)

        def emit_decision(decision_type: str, payload: Dict[str, Any]) -> None:
            d = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": decision_type,
                "payload": payload,
            }
            decision_log.append(d)
            if self.run_store:
                self.run_store.append_decision(run_id, d)

        # Persist run header (best-effort)
        if self.run_store:
            self.run_store.create_run(
                {
                    "run_id": run_id,
                    "started_at": started_at,
                    "interface_id": request.interface_id,
                    "query": request.query,
                    "role_id": role_id,
                    "policy_id": policy_id,
                    "run_mode": request.run_mode,
                    "context": dict(request.context),
                }
            )

        # Goal
        goal = self.goal_builder.build(request.query, context=request.context)
        emit_decision("goal_created", {"goal_id": goal.goal_id, "workflow_hint": goal.workflow_hint, "required_metrics": goal.required_metrics})

        # ProjectLedger: goal/scope/constraints/evidence plan (Phase 1 best-effort)
        predicate_node_id = f"PRED-{goal.goal_id}"
        project_ledger.goal_graph = {
            "schema_version": 1,
            "nodes": [
                {
                    "id": goal.goal_id,
                    "type": "goal",
                    "data": {
                        "name": goal.name,
                        "query": goal.query,
                        "workflow_hint": goal.workflow_hint,
                        "usage": goal.usage,
                        "required_metrics": list(goal.required_metrics),
                        "completion": {"satisfied": 0, "total": len(goal.required_metrics), "ratio": 0.0},
                    },
                }
            ]
            + [
                {
                    "id": predicate_node_id,
                    "type": "predicate",
                    "data": {
                        "predicate_type": goal.predicate.predicate_type.value,
                        "conditions": [
                            {"type": c.type.value, "params": dict(c.params)}
                            for c in goal.predicate.conditions
                        ],
                    },
                }
            ]
            + [
                {
                    "id": str(mid),
                    "type": "metric",
                    "data": {
                        "metric_id": str(mid),
                        "exists": False,
                        "value_present": False,
                        "policy_passed": False,
                        "satisfied": False,
                    },
                }
                for mid in goal.required_metrics
            ],
            "edges": [
                {"from": goal.goal_id, "to": predicate_node_id, "type": "requires"},
                *[
                    {"from": predicate_node_id, "to": str(mid), "type": "requires"}
                    for mid in goal.required_metrics
                ],
            ],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        project_ledger.success_predicates = [
            {
                "predicate_type": goal.predicate.predicate_type.value,
                "conditions": [
                    {"type": c.type.value, "params": dict(c.params)}
                    for c in goal.predicate.conditions
                ],
            }
        ]
        project_ledger.scope = dict(request.context)
        project_ledger.constraints = {"budgets": dict(request.budgets), "run_mode": request.run_mode}
        project_ledger.evidence_plan = {
            "generated_by": "kernel_rules_v1",
            "required_metrics": list(goal.required_metrics),
            "items": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Initial tasks: run workflow first (hint), then compute required metrics if needed
        queue = TaskQueue()
        initial_tasks: List[Task] = [
            Task(
                task_id=f"TASK-run-workflow-{uuid.uuid4().hex[:8]}",
                task_type=TaskType.RUN_WORKFLOW,
                inputs={
                    "workflow_id": goal.workflow_hint,
                    "inputs": {},
                },
            )
        ]
        queue.enqueue(initial_tasks)
        emit_decision("initial_plan", {"tasks": [t.task_id for t in initial_tasks]})

        # Budgets
        budget = Budget(
            max_iterations=int(request.budgets.get("max_iterations", 20)),
            max_time_sec=int(request.budgets.get("max_time_sec", 300)),
        )

        start_time = time.time()
        completed_task_ids: List[str] = []

        last_verification: Optional[VerificationResult] = None
        iteration = 0

        try:
            while True:
                # 1) Verify
                last_verification = self.verifier.verify(goal, ledgers, policy_id)
                if last_verification.satisfied:
                    emit_decision("goal_satisfied", {"goal_id": goal.goal_id})
                    progress_ledger.overall_status = "completed"
                    break

                emit_decision("diff_detected", dict(last_verification.diff_report))
                ledgers.record_diff_report(last_verification.diff_report)
                ledgers.record_project_insights_from_diff(last_verification.diff_report)

                # 2) Replan -> enqueue tasks
                replan = self.replanner.generate_tasks(last_verification.diff_report)
                if replan.tasks:
                    queue.enqueue(replan.tasks)
                    progress_ledger.replanning_count += 1
                    emit_decision("replanned", {"reason": replan.reason, "tasks": [t.task_id for t in replan.tasks]})
                    ledgers.set_next_step_suggestion(
                        {
                            "reason": replan.reason,
                            "tasks": [{"task_id": t.task_id, "task_type": t.task_type.value} for t in replan.tasks],
                        }
                    )
                    ledgers.reset_stall("no_task")
                else:
                    # No tasks to run -> stall
                    ledgers.increment_stall("no_task")
                    stall_reason = self.governor.check_stall(ledgers, policy_id, stall_key="no_task")
                    if stall_reason:
                        progress_ledger.overall_status = "stalled"
                        emit_decision("stalled", {"reason": stall_reason})
                        ledgers.set_next_step_suggestion({"action": "stop", "reason": stall_reason})
                        break

                # 3) Pick next task
                task = queue.next_runnable(completed_task_ids)
                if task is None:
                    ledgers.increment_stall("no_runnable_task")
                    stall_reason = self.governor.check_stall(ledgers, policy_id, stall_key="no_runnable_task")
                    if stall_reason:
                        progress_ledger.overall_status = "stalled"
                        emit_decision("stalled", {"reason": stall_reason})
                        break
                    continue

                # 4) Budget guard
                stop_reason = self.governor.should_stop(ledgers, iteration=iteration, start_time=start_time, budget=budget)
                if stop_reason:
                    progress_ledger.overall_status = "incomplete"
                    emit_decision("budget_stop", {"reason": stop_reason})
                    ledgers.set_next_step_suggestion({"action": "stop", "reason": stop_reason})
                    break

                # 5) Execute task
                task.mark_running()
                ledgers.mark_task_status(task, TaskStatus.RUNNING)
                step = StepRecord(
                    step_id=task.task_id,
                    call=task.task_type.value,
                    status="running",
                    started_at=datetime.now(timezone.utc).isoformat(),
                )
                ledgers.add_step(step)
                emit_event("task_started", {"task_id": task.task_id, "task_type": task.task_type.value, "inputs": dict(task.inputs)})

                run_context = dict(request.context)
                result = self.task_executor.execute(task, run_context, role_id=role_id, policy_id=policy_id)
                progress_ledger.last_engine_calls.append(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "task_id": task.task_id,
                        "task_type": task.task_type.value,
                        "inputs": dict(task.inputs),
                    }
                )
                progress_ledger.last_engine_calls = progress_ledger.last_engine_calls[-10:]
                progress_ledger.touch()

                tool_calls = result.get("tool_calls") or []
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            progress_ledger.last_tool_calls.append(dict(tc))
                    progress_ledger.last_tool_calls = progress_ledger.last_tool_calls[-20:]
                    progress_ledger.touch()

                value_program = result.get("value_program") or {}
                if isinstance(value_program, dict):
                    prior_decisions = value_program.get("prior_decisions") or []
                    if isinstance(prior_decisions, list):
                        for d in prior_decisions:
                            if isinstance(d, dict):
                                emit_decision("prior_decision", d)

                task.mark_completed()
                ledgers.mark_task_status(task, TaskStatus.COMPLETED)
                completed_task_ids.append(task.task_id)
                ledgers.apply_task_result(task, result)

                # step finalize
                step.status = "completed"
                step.completed_at = datetime.now(timezone.utc).isoformat()
                progress_ledger.step_status = step.status
                progress_ledger.touch()
                emit_event("task_completed", {"task_id": task.task_id, "task_type": task.task_type.value, "result": result})

                # ledger snapshot persist (best-effort)
                if self.ledger_store:
                    self.ledger_store.save_snapshot(run_id, project_ledger.to_dict(), progress_ledger.to_dict())

                iteration += 1

        except Exception as e:
            progress_ledger.overall_status = "failed"
            emit_event("kernel_error", {"error": str(e)})
            if self.run_store:
                self.run_store.finalize_run(run_id, "failed", {"error": str(e)})
            return RunResult(
                run_id=run_id,
                status="failed",
                goal_satisfied=False,
                goal_id=goal.goal_id,
                role_id=role_id,
                policy_id=policy_id,
                interface_id=request.interface_id,
                iterations=iteration,
                ledgers=ledgers.to_dict(),
                decision_log=decision_log,
                events=events,
                error=str(e),
            )

        # finalize status
        goal_satisfied = bool(last_verification.satisfied) if last_verification else False
        if progress_ledger.overall_status == "completed":
            status = "success"
        elif progress_ledger.overall_status == "failed":
            status = "failed"
        elif progress_ledger.overall_status == "stalled":
            status = "stalled"
        else:
            status = "incomplete"

        summary = {
            "status": status,
            "goal_satisfied": goal_satisfied,
            "iterations": iteration,
        }
        if self.run_store:
            self.run_store.finalize_run(run_id, status, summary)
        if self.ledger_store:
            self.ledger_store.save_snapshot(run_id, project_ledger.to_dict(), progress_ledger.to_dict())

        return RunResult(
            run_id=run_id,
            status=status,
            goal_satisfied=goal_satisfied,
            goal_id=goal.goal_id,
            role_id=role_id,
            policy_id=policy_id,
            interface_id=request.interface_id,
            iterations=iteration,
            ledgers=ledgers.to_dict(),
            decision_log=decision_log,
            events=events,
        )

    @staticmethod
    def _new_run_id() -> str:
        return f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    @staticmethod
    def _infer_usage(query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["기회", "발굴", "탐색", "opportunity", "explore"]):
            return "exploration"
        if any(k in q for k in ["전략", "의사결정", "선택", "strategy", "decision", "portfolio"]):
            return "decision"
        return "reporting"

    @staticmethod
    def _infer_role_from_context(context: Dict[str, Any]) -> str:
        # 인터페이스에서 명시적으로 role_id를 넣었으면 우선
        role_id = context.get("role_id")
        if role_id:
            return str(role_id)
        return "structure_analyst"

