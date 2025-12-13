"""CMIS Orchestration Kernel (Reconcile Loop).

이 패키지는 인터페이스(Cursor/Web/API/Notebook 등)와 무관하게 공통으로 사용되는
목표 중심 실행 런타임을 제공합니다.

핵심:
- Desired(Goal) ↔ Observed(Ledgers) 비교
- Diff → Tasks → Execute → Verify 반복
- PolicyEngine v2를 단일 품질 게이트 소스로 사용
"""

from .kernel import OrchestrationKernel, RunRequest, RunResult
from .goal import GoalSpec, GoalPredicate, Condition, ConditionType, PredicateType
from .task import Task, TaskType, TaskStatus, TaskQueue
from .ledgers import Ledgers, ProjectLedger, ProgressLedger

__all__ = [
    "OrchestrationKernel",
    "RunRequest",
    "RunResult",
    "GoalSpec",
    "GoalPredicate",
    "PredicateType",
    "Condition",
    "ConditionType",
    "Task",
    "TaskType",
    "TaskStatus",
    "TaskQueue",
    "Ledgers",
    "ProjectLedger",
    "ProgressLedger",
]

