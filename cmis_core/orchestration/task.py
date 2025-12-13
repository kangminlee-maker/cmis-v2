"""Orchestration task model.

Task는 OrchestrationKernel이 실행하는 최소 작업 단위입니다.
Cursor Agent Interface v2에서는 Task 실행 결과가 Ledgers/RunStore로 기록되어
재현성과 디버깅 가능성을 제공합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class TaskType(str, Enum):
    """Task 종류 (Kernel 내부 실행 단위)"""

    RUN_WORKFLOW = "run_workflow"
    COLLECT_EVIDENCE = "collect_evidence"
    COMPUTE_METRIC = "compute_metric"
    VALIDATE_GOAL = "validate_goal"
    PROPOSE_REPLAN = "propose_replan"


class TaskStatus(str, Enum):
    """Task 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """실행 작업 단위"""

    task_id: str
    task_type: TaskType
    inputs: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)

    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    attempt: int = 0
    max_retries: int = 0
    last_error: Optional[str] = None

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.attempt += 1

    def mark_completed(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.last_error = None

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.last_error = error

    def can_retry(self) -> bool:
        return self.attempt <= self.max_retries


class TaskQueue:
    """단순 Task 큐 (Phase 1: FIFO + dependency check)"""

    def __init__(self) -> None:
        self._order: List[str] = []
        self._tasks: Dict[str, Task] = {}

    def enqueue(self, tasks: List[Task]) -> None:
        for t in tasks:
            if t.task_id in self._tasks:
                # 기존 Task가 pending/failed일 수 있으므로 중복 enqueue는 무시
                continue
            self._tasks[t.task_id] = t
            self._order.append(t.task_id)

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def all_tasks(self) -> List[Task]:
        return [self._tasks[tid] for tid in self._order if tid in self._tasks]

    def next_runnable(self, completed_task_ids: List[str]) -> Optional[Task]:
        """실행 가능한 다음 Task 선택"""
        completed_set = set(completed_task_ids)
        for tid in self._order:
            task = self._tasks.get(tid)
            if not task:
                continue
            if task.status != TaskStatus.PENDING:
                continue
            if any(dep not in completed_set for dep in task.depends_on):
                continue
            return task
        return None

