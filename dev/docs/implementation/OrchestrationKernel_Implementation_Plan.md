# OrchestrationKernel 구현 계획

**날짜**: 2025-12-13
**버전**: v1.0
**기반**: CMIS Philosophy v2 + Architecture Blueprint v3.4 + cmis.yaml v3.4

---

## 0. 설계 철학 정렬 체크

### 0.1 핵심 철학 준수

**Evidence-first, Prior-last** ✅
- Verifier가 PolicyEngine v2와 통합
- MetricEval의 literal_ratio, prior_ratio 검증
- 품질 게이트 실패 시 자동 Evidence 수집 Task 생성

**Objective-Oriented** ✅
- Reconcile Loop (Desired ↔ Observed)
- 고정 프로세스가 아니라 Goal Predicate 기반
- 동적 재계획 (Replanner)

**Ledger-based (유한 컨텍스트 대응)** ✅
- 2-Ledger 구조 (Project + Progress)
- Project Ledger = Substrate (Stores + Graphs)
- Progress Ledger = 실행 제어판

**재현 가능성** ✅
- Decision Log (Event-sourcing)
- 모든 Task/Result lineage 추적
- Ledger 스냅샷 기반 재실행 가능

---

## 1. 아키텍처 설계

### 1.1 전체 구조

```
OrchestrationKernel
├─ Core Components
│  ├─ GoalGraph (D-Graph 활용, Success Predicate)
│  ├─ TaskQueue (의존성 기반 실행 큐)
│  ├─ Ledgers (Project + Progress, 2개 고정)
│  ├─ Verifier (PolicyEngine 통합, Diff Report)
│  ├─ Replanner (부분 재계획, suggested_actions → Tasks)
│  └─ Governor (예산/스톨/품질 제어)
│
├─ Execution Engine
│  ├─ TaskExecutor (Task 타입별 실행)
│  └─ WorkflowOrchestrator 통합
│
└─ Logging & Persistence
   ├─ DecisionLog (Event-sourcing)
   └─ LedgerStore (Substrate)
```

---

## 2. 모듈 분리 전략

### 2.1 파일 구조

```
cmis_core/
├─ orchestration/
│  ├─ __init__.py
│  ├─ kernel.py                # OrchestrationKernel (메인)
│  ├─ goal.py                  # Goal, GoalPredicate
│  ├─ task.py                  # Task, TaskQueue, TaskType
│  ├─ ledgers.py               # Ledgers (Project + Progress)
│  ├─ verifier.py              # Verifier (PolicyEngine 통합)
│  ├─ replanner.py             # Replanner (부분 재계획)
│  ├─ governor.py              # Governor (예산/스톨 제어)
│  └─ executor.py              # TaskExecutor
```

**장점**:
1. ✅ **테스트 용이**: 각 컴포넌트 독립 테스트
2. ✅ **확장 용이**: Task 타입, Gate 추가 간단
3. ✅ **책임 분리**: SOLID 원칙 준수
4. ✅ **재사용 가능**: Verifier, Replanner 독립 사용 가능

---

## 3. 핵심 컴포넌트 설계

### 3.1 Goal & GoalPredicate

**파일**: `cmis_core/orchestration/goal.py`

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class PredicateType(Enum):
    """Predicate 타입"""
    ALL_OF = "all_of"
    ANY_OF = "any_of"
    THRESHOLD = "threshold"


class ConditionType(Enum):
    """Condition 타입"""
    METRIC_EXISTS = "metric_exists"
    EVIDENCE_QUALITY = "evidence_quality"
    COMPLETENESS = "completeness"
    CONVERGENCE = "convergence"
    LITERAL_RATIO = "literal_ratio"


@dataclass
class Condition:
    """Success Predicate 조건

    PolicyEngine과 통합
    """
    type: ConditionType
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "params": dict(self.params)
        }


@dataclass
class GoalPredicate:
    """Success Predicate (검증 가능)

    Goal 달성 여부를 구조화된 조건으로 정의
    """
    predicate_id: str
    predicate_type: PredicateType
    conditions: List[Condition]

    def evaluate(self, ledgers: 'Ledgers', policy_engine: 'PolicyEngine') -> bool:
        """Predicate 평가

        Args:
            ledgers: 현재 상태
            policy_engine: PolicyEngine (품질 기준)

        Returns:
            True if 성공 조건 만족
        """
        if self.predicate_type == PredicateType.ALL_OF:
            return all(self._eval_condition(c, ledgers, policy_engine) for c in self.conditions)

        elif self.predicate_type == PredicateType.ANY_OF:
            return any(self._eval_condition(c, ledgers, policy_engine) for c in self.conditions)

        elif self.predicate_type == PredicateType.THRESHOLD:
            satisfied_count = sum(1 for c in self.conditions if self._eval_condition(c, ledgers, policy_engine))
            threshold = self.conditions[0].params.get("threshold", len(self.conditions))
            return satisfied_count >= threshold

        return False

    def _eval_condition(self, condition: Condition, ledgers: 'Ledgers', policy_engine: 'PolicyEngine') -> bool:
        """개별 조건 평가"""
        if condition.type == ConditionType.METRIC_EXISTS:
            metric_id = condition.params.get("metric_id")
            return metric_id in ledgers.project.metrics

        elif condition.type == ConditionType.EVIDENCE_QUALITY:
            # PolicyEngine에서 기준 조회
            policy_id = ledgers.progress.policy_ref
            threshold_ref = condition.params.get("threshold", "policy:min_literal_ratio")

            if threshold_ref.startswith("policy:"):
                policy_key = threshold_ref.split(":")[1]
                policy = policy_engine.get_value_policy(policy_id)
                threshold = getattr(policy, policy_key, 0.5)
            else:
                threshold = float(threshold_ref)

            # 평균 품질 체크
            avg_quality = self._get_average_quality(ledgers)
            return avg_quality >= threshold

        elif condition.type == ConditionType.COMPLETENESS:
            min_metrics = condition.params.get("min_metrics", 1)
            return len(ledgers.project.metrics) >= min_metrics

        return False

    @staticmethod
    def _get_average_quality(ledgers: 'Ledgers') -> float:
        """평균 literal_ratio 계산"""
        if not ledgers.project.metrics:
            return 0.0

        total = 0.0
        count = 0

        for metric_id, metric_data in ledgers.project.metrics.items():
            quality = metric_data.get("quality", {})
            literal_ratio = quality.get("literal_ratio", 0.0)
            total += literal_ratio
            count += 1

        return total / count if count > 0 else 0.0


@dataclass
class Goal:
    """Goal (D-Graph 노드)

    CMIS 철학: Goal은 D-Graph의 일급 객체
    """
    goal_id: str
    name: str
    description: str

    # Target metrics
    target_metrics: List[str] = field(default_factory=list)

    # Success Predicate (검증 가능)
    success_predicate: Optional[GoalPredicate] = None

    # Context
    project_context_id: Optional[str] = None

    # Metadata
    created_at: Optional[str] = None
    created_by_role: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "description": self.description,
            "target_metrics": list(self.target_metrics),
            "success_predicate": self.success_predicate.to_dict() if self.success_predicate else None,
            "project_context_id": self.project_context_id,
            "created_at": self.created_at,
            "created_by_role": self.created_by_role
        }
```

**핵심 설계 결정**:
1. ✅ **D-Graph 활용**: Goal은 새 객체가 아니라 D-Graph 노드
2. ✅ **Success Predicate**: 검증 가능한 구조화된 조건
3. ✅ **PolicyEngine 통합**: 품질 기준을 Policy에서 조회 (하드코딩 ❌)
4. ✅ **확장 가능**: Condition 타입 추가 가능

---

### 3.2 Task & TaskQueue

**파일**: `cmis_core/orchestration/task.py`

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime, timezone


class TaskType(Enum):
    """Task 타입 (확장 가능)"""
    RUN_WORKFLOW = "run_workflow"
    COLLECT_EVIDENCE = "collect_evidence"
    COMPUTE_METRIC = "compute_metric"
    VALIDATE_GOAL = "validate_goal"
    PROPOSE_REPLAN = "propose_replan"
    UPDATE_CONTEXT = "update_context"


class TaskStatus(Enum):
    """Task 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """실행 작업 단위

    CMIS 철학: Task는 엔진 호출의 명시적 래퍼
    """
    task_id: str
    task_type: TaskType

    # 의존성
    depends_on: List[str] = field(default_factory=list)

    # 입력/출력
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: List[str] = field(default_factory=list)

    # 품질 게이트 (PolicyEngine 통합)
    quality_gate: Optional[Dict[str, Any]] = None

    # 예산
    budget: Optional[Dict[str, Any]] = None

    # 상태
    status: TaskStatus = TaskStatus.PENDING

    # 결과
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # Lineage
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def can_execute(self, ledgers: 'Ledgers') -> bool:
        """실행 가능 여부

        의존성 완료 + 리소스 가용 확인
        """
        # 의존 Task 모두 완료?
        for dep_id in self.depends_on:
            dep_status = ledgers.progress.task_statuses.get(dep_id)
            if dep_status != TaskStatus.COMPLETED.value:
                return False

        # Budget 체크
        if self.budget:
            max_time = self.budget.get("max_time_sec")
            current_time = ledgers.progress.budgets.get("time_spent_sec", 0)
            budget_limit = ledgers.progress.budgets.get("max_time_sec", float('inf'))

            if max_time and (current_time + max_time) > budget_limit:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "depends_on": list(self.depends_on),
            "inputs": dict(self.inputs),
            "expected_outputs": list(self.expected_outputs),
            "quality_gate": self.quality_gate,
            "budget": self.budget,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


class TaskQueue:
    """Task 실행 큐 (의존성 기반)

    CMIS 철학: 고정 순서가 아니라 의존성 기반 동적 스케줄링
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.execution_order: List[str] = []

    def enqueue(self, tasks: List[Task]) -> None:
        """Task 추가 (의존성 정렬)

        Args:
            tasks: Task 리스트
        """
        for task in tasks:
            self.tasks[task.task_id] = task

        # 의존성 기반 정렬 (Topological Sort)
        self.execution_order = self._topological_sort()

    def dequeue(self, ledgers: 'Ledgers') -> Optional[Task]:
        """실행 가능한 Task 반환

        Args:
            ledgers: Ledgers (의존성 체크용)

        Returns:
            실행 가능한 Task (없으면 None)
        """
        for task_id in self.execution_order:
            task = self.tasks.get(task_id)

            if not task:
                continue

            if task.status != TaskStatus.PENDING:
                continue

            if task.can_execute(ledgers):
                task.status = TaskStatus.RUNNING
                return task

        return None

    def _topological_sort(self) -> List[str]:
        """위상 정렬 (의존성 기반)

        Returns:
            실행 순서 (task_id 리스트)
        """
        # In-degree 계산
        in_degree = {task_id: 0 for task_id in self.tasks}

        for task in self.tasks.values():
            for dep_id in task.depends_on:
                if dep_id in in_degree:
                    in_degree[task.task_id] += 1

        # Queue 초기화 (in-degree = 0)
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            task_id = queue.pop(0)
            result.append(task_id)

            # 의존성 감소
            task = self.tasks[task_id]
            for other_task in self.tasks.values():
                if task_id in other_task.depends_on:
                    in_degree[other_task.task_id] -= 1
                    if in_degree[other_task.task_id] == 0:
                        queue.append(other_task.task_id)

        return result

    def get_pending_count(self) -> int:
        """대기 중인 Task 개수"""
        return sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)

    def get_completed_count(self) -> int:
        """완료된 Task 개수"""
        return sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
```

**핵심 설계 결정**:
1. ✅ **의존성 기반**: 위상 정렬로 실행 순서 결정
2. ✅ **Budget 통합**: Task별 예산 + 전체 예산 체크
3. ✅ **확장 가능**: TaskType 추가 간단
4. ✅ **Lineage**: created_at, completed_at 추적

---

### 3.3 Ledgers (Project + Progress)

**파일**: `cmis_core/orchestration/ledgers.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class ProjectLedger:
    """Project Ledger (문제공간 작업기억)

    CMIS 철학: Substrate(Stores + Graphs) 참조 집합

    = Task Ledger (Magentic-One 용어)
    """

    # Facts (확정된 사실)
    facts: Dict[str, Any] = field(default_factory=dict)

    # Assumptions (가정)
    assumptions: List[str] = field(default_factory=list)

    # Evidence 참조
    evidence_refs: List[str] = field(default_factory=list)

    # Derived Metrics (ValueRecord 참조)
    metrics: Dict[str, Any] = field(default_factory=dict)
    # {metric_id: {"value": ..., "quality": {...}, "value_record_id": "VAL-..."}}

    # Gaps (부족한 것)
    gaps: List[str] = field(default_factory=list)

    # Artifacts (산출물)
    artifacts: List[str] = field(default_factory=list)

    # Goal References (D-Graph)
    goals: List[str] = field(default_factory=list)

    def get_metric_quality(self, metric_id: str) -> float:
        """Metric 품질 조회 (literal_ratio)"""
        metric = self.metrics.get(metric_id)
        if not metric:
            return 0.0

        quality = metric.get("quality", {})
        return quality.get("literal_ratio", 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": dict(self.facts),
            "assumptions": list(self.assumptions),
            "evidence_refs": list(self.evidence_refs),
            "metrics": dict(self.metrics),
            "gaps": list(self.gaps),
            "artifacts": list(self.artifacts),
            "goals": list(self.goals)
        }


@dataclass
class ProgressLedger:
    """Progress Ledger (프로세스 제어판)

    CMIS 철학: 실행 단계/상태/재시도/스톨 감지 기록
    """

    # Run 식별
    run_id: str = ""

    # Workflow
    workflow_id: Optional[str] = None

    # Role & Policy
    role_id: Optional[str] = None
    policy_ref: Optional[str] = None

    # Task 상태
    task_statuses: Dict[str, str] = field(default_factory=dict)
    # {task_id: "completed" | "running" | "pending" | "failed"}

    # Stall 카운터
    stall_counters: Dict[str, int] = field(default_factory=dict)

    # Loop 플래그
    loop_flags: Dict[str, bool] = field(default_factory=dict)

    # Budget
    budgets: Dict[str, Any] = field(default_factory=dict)
    # {"time_spent_sec": 120, "llm_calls": 5, "max_time_sec": 300}

    # Next Action
    next_action: Optional[str] = None
    # "continue" | "replan" | "stop"

    # Replanning
    replanning_count: int = 0
    replanning_log: List[Dict[str, Any]] = field(default_factory=list)

    # Overall Status
    overall_status: str = "running"
    # "running" | "completed" | "failed" | "stalled"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "role_id": self.role_id,
            "policy_ref": self.policy_ref,
            "task_statuses": dict(self.task_statuses),
            "stall_counters": dict(self.stall_counters),
            "loop_flags": dict(self.loop_flags),
            "budgets": dict(self.budgets),
            "next_action": self.next_action,
            "replanning_count": self.replanning_count,
            "replanning_log": list(self.replanning_log),
            "overall_status": self.overall_status
        }


class Ledgers:
    """Ledger 컨테이너 (2개 고정)

    CMIS 철학: 유한 컨텍스트 대응 (Magentic-One)
    """

    def __init__(self):
        self.project = ProjectLedger()
        self.progress = ProgressLedger()

    def update_from_task_result(self, task: 'Task', result: Dict[str, Any]) -> None:
        """Task 결과 → Ledger 업데이트

        Args:
            task: 완료된 Task
            result: Task 결과
        """
        from .task import TaskType, TaskStatus

        # ProgressLedger 업데이트
        self.progress.task_statuses[task.task_id] = TaskStatus.COMPLETED.value
        self.progress.budgets["time_spent_sec"] = self.progress.budgets.get("time_spent_sec", 0) + result.get("time_sec", 0)

        # ProjectLedger 업데이트 (Task 타입별)
        if task.task_type == TaskType.COLLECT_EVIDENCE:
            evidence_ids = result.get("evidence_ids", [])
            self.project.evidence_refs.extend(evidence_ids)

        elif task.task_type == TaskType.COMPUTE_METRIC:
            metric_id = result.get("metric_id")
            if metric_id:
                self.project.metrics[metric_id] = {
                    "value": result.get("value"),
                    "quality": result.get("quality", {}),
                    "value_record_id": result.get("value_record_id")
                }

        elif task.task_type == TaskType.RUN_WORKFLOW:
            # Workflow 결과 통합
            workflow_result = result.get("workflow_result", {})

            # Metrics 추가
            metrics = workflow_result.get("metrics", [])
            for metric in metrics:
                self.project.metrics[metric.metric_id] = {
                    "value": metric.point_estimate,
                    "quality": metric.quality,
                    "value_record_id": f"VAL-{metric.metric_id}"
                }

            # Evidence 추가
            evidence_refs = workflow_result.get("evidence_refs", [])
            self.project.evidence_refs.extend(evidence_refs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project.to_dict(),
            "progress": self.progress.to_dict()
        }
```

**핵심 설계 결정**:
1. ✅ **2-Ledger 구조**: Project (지속) + Progress (진행) 명확히 분리
2. ✅ **Substrate 참조**: Project Ledger는 ID 참조만 (실제 데이터는 Stores)
3. ✅ **확장 가능**: Task 타입별 업데이트 로직 추가 간단
4. ✅ **재현 가능**: Ledger 스냅샷으로 상태 복원 가능

---

## 4. 구현 우선순위

### Phase 1: 핵심 타입 (1주)
- ✅ goal.py (Goal + GoalPredicate)
- ✅ task.py (Task + TaskQueue)
- ✅ ledgers.py (Ledgers)
- 테스트: 10개

### Phase 2: 검증/재계획/제어 (1주)
- verifier.py (Verifier + PolicyEngine 통합)
- replanner.py (Replanner + suggested_actions)
- governor.py (Governor + orchestration_policy)
- 테스트: 15개

### Phase 3: Kernel (1주)
- kernel.py (OrchestrationKernel + Reconcile Loop)
- executor.py (TaskExecutor)
- 테스트: 10개

### Phase 4: 통합 (3일)
- WorkflowOrchestrator 통합
- PolicyEngine v2 통합
- End-to-end 테스트: 5개

**총 3.5주**

---

## 5. 확장성 고려사항

### 5.1 Task 타입 확장

```python
# 새 Task 타입 추가 (간단)
class TaskType(Enum):
    # ... 기존 타입
    REFINE_HYPOTHESIS = "refine_hypothesis"  # 신규
    COMPARE_SCENARIOS = "compare_scenarios"  # 신규
```

### 5.2 Gate 추가

```python
# Custom gate 등록
def custom_domain_gate(policy, evidence, metric):
    # 도메인 특화 검증
    return []

policy_engine.register_custom_gate("custom_domain_gate", custom_domain_gate)
```

### 5.3 Governor 정책 외부화

```yaml
# config/orchestration.yaml (신규)
governor:
  budgets:
    max_time_sec: 300
    max_llm_calls: 20
  stall_detection:
    threshold: 2
    action: "replan"
```

---

## 6. 성능 최적화

### 6.1 병렬 실행

```python
# TaskQueue에서 병렬 가능 Task 탐지
def get_parallel_tasks(self, ledgers):
    """병렬 실행 가능한 Task 리스트"""
    parallel_tasks = []

    for task in self.tasks.values():
        if task.status == TaskStatus.PENDING and task.can_execute(ledgers):
            # 다른 running task와 의존성 없으면 병렬 가능
            parallel_tasks.append(task)

    return parallel_tasks
```

### 6.2 Ledger 스냅샷 캐싱

```python
# 자주 조회하는 상태는 캐시
@lru_cache(maxsize=128)
def get_metric_quality(self, metric_id: str) -> float:
    # ...
```

---

## 7. 체크리스트

### 철학 정렬
- [ ] Evidence-first가 Verifier + PolicyEngine으로 강제되는가?
- [ ] Objective-Oriented (Reconcile Loop)가 구현되었는가?
- [ ] Ledger-based (2-Ledger)가 구현되었는가?
- [ ] 재현 가능성 (Decision Log)이 보장되는가?

### 확장성
- [ ] Task 타입 추가가 간단한가?
- [ ] Gate 추가가 간단한가?
- [ ] Governor 정책 외부화 가능한가?

### Robustness
- [ ] Stall 감지 및 재계획이 작동하는가?
- [ ] Budget 초과 시 안전하게 종료하는가?
- [ ] 의존성 순환 감지하는가?

---

**작성**: 2025-12-13
**다음**: Phase 1 구현 시작
