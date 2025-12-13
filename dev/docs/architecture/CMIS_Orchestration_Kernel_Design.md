# CMIS Orchestration Kernel 설계

**작성일**: 2025-12-12
**버전**: v3.0 (Reconcile 기반)
**이전**: CMIS_Adaptive_Execution_Design.md v2.0
**패러다임**: Kubernetes-style Reconcile Loop
**상태**: 설계 단계

---

## 📝 요구사항 및 피드백 (원문 보존)

### 원본 요구사항

1. **Cursor Agent Interface** 추가 (5번째 인터페이스)
2. **동적 재설계** - Evidence 결과에 따라 경로 변경 (CMIS 핵심 중 핵심)
3. **Objective-Oriented** - 목표 중심, 프로세스 자유
4. **Process Guardian** - 감독, Logging (v7 계승)
5. **LLM 추상화** - Cursor/External/Rule
6. **프로덕션 배포** - Non-Cursor도 orchestration

---

### 피드백 핵심

**결론**: **"Reconcile 기반 Orchestration Kernel"이 가장 깔끔**

**이유**:
- 동적 재설계가 커지면 if/else 기반은 복잡도 폭발
- Magentic-One (2-ledger + 2-loop) + OrchVis (goal predicate + verifier) + TEA (리소스 1급화) 조합
- Kubernetes Controller 패턴 (Desired ↔ Observed State 비교)

**핵심 추상화 5개**:
1. **GoalGraph** (What) - D-Graph goal 활용, Success Predicate
2. **TaskGraph/Queue** (How) - 실행 작업, 의존성
3. **Ledgers** (State) - TaskLedger + ProgressLedger (2개로 고정)
4. **Verifier** (Check) - Predicate 검증, Diff Report
5. **Replanner** (Adjust) - 부분 재계획 (브랜치 단위)

**LLM 역할 격하**: 
- 결정권자 ❌
- **PlanPatch 제안자** ✅
- Kernel이 검증 후 적용

---

## 0. 설계 철학

### 0.1 Reconcile Loop 패턴

```
┌─────────────────────────────────────────┐
│  Desired State (Goal)                   │
│  "TAM/SAM 파악, Evidence Quality > 70%" │
└─────────────────────────────────────────┘
              ↓ diff
┌─────────────────────────────────────────┐
│  Observed State (Reality)               │
│  "TAM 있음, SAM 없음, Quality 40%"      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Diff Report                            │
│  - SAM 누락                             │
│  - Evidence Quality 부족 (40% < 70%)    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Task Generation                        │
│  - Task: CollectEvidence(MET-SAM)      │
│  - Task: CollectEvidence(더 수집)       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Execute Tasks                          │
└─────────────────────────────────────────┘
              ↓ (다시 Observed 업데이트)
        Reconcile Loop 반복
```

**장점**:
- 복잡도가 if/else가 아니라 Predicate/Task 추가로 확장
- 검증 가능 (Predicate가 명확)
- 재현 가능 (Event-sourcing)
- 디버깅 쉬움 (Diff Report 명확)

---

### 0.2 CMIS 철학과의 정합성

**CMIS 철학**: "Agent = Persona + Workflow (엔진이 아님)"

**Orchestration도 동일**:
```
Orchestration Kernel (결정/감독/상태)
    ↓
WorkflowOrchestrator (실행기)
    ↓
Engines (능력)
```

**역할 고정**:
- Kernel: What/When/Why (무엇을, 언제, 왜)
- WorkflowOrchestrator: How (어떻게)
- Engines: Can (할 수 있는 것)

---

## 1. Orchestration Kernel 아키텍처

### 1.1 전체 구조

```
[Interface Adapter]
  Cursor / CLI / Web / API / Notebook
        │
        ▼
┌─────────────────────────────────────────┐
│ Orchestration Kernel (Reconcile Engine) │
├─────────────────────────────────────────┤
│                                         │
│  GoalGraph                              │
│  ├─ D-Graph goal 노드 활용              │
│  └─ Success Predicate (검증 가능)       │
│                                         │
│  TaskGraph/Queue                        │
│  ├─ RunWorkflow Task                    │
│  ├─ CollectEvidence Task                │
│  └─ ValidateGoal Task                   │
│                                         │
│  Ledgers (상태 2개로 고정)               │
│  ├─ TaskLedger (문제공간 작업기억)       │
│  └─ ProgressLedger (프로세스 제어판)     │
│                                         │
│  Verifier                               │
│  ├─ Predicate 검증                      │
│  └─ Diff Report 생성                    │
│                                         │
│  Replanner                              │
│  ├─ 부분 재계획 (브랜치 단위)            │
│  └─ Task 생성/수정                      │
│                                         │
│  Governor/Guardian                      │
│  ├─ 예산/루프/품질 제어                  │
│  └─ Policy Engine 연동                  │
│                                         │
│  DecisionLog                            │
│  └─ Patch 단위 감사/리플레이             │
│                                         │
└─────────────────────────────────────────┘
        │ (execute tasks)
        ▼
┌─────────────────────────────────────────┐
│ WorkflowOrchestrator (기존)              │
│  canonical_workflows 실행                │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ CMIS Engines (9개)                      │
│ World/Pattern/Value/Belief/Strategy/... │
│ + Stores (Evidence/Value/D-Graph/...)   │
└─────────────────────────────────────────┘
```

---

### 1.2 Reconcile Loop

```python
def reconcile_loop():
    """Kubernetes-style Reconcile Loop"""
    
    while not goal_achieved():
        # 1. Desired State (Goal + Predicates)
        desired = get_goal_with_predicates()
        
        # 2. Observed State (Ledgers)
        observed = get_current_state_from_ledgers()
        
        # 3. Diff (Verifier)
        diff_report = verifier.compare(desired, observed)
        
        # 4. Task Generation (Replanner)
        if diff_report.has_gaps():
            tasks = replanner.generate_tasks(diff_report)
            task_queue.enqueue(tasks)
        
        # 5. Execute
        task = task_queue.dequeue()
        result = executor.execute(task)
        
        # 6. Update Ledgers
        ledgers.update(task, result)
        
        # 7. Verify (다시 확인)
        if verifier.check_success(desired, ledgers):
            break
        
        # 8. Governor (제어)
        if governor.should_stop(ledgers):
            break
```

---

## 2. 5개 핵심 추상화

### 2.1 GoalGraph (What)

**D-Graph goal 노드 재사용** (새로 만들지 않음)

```yaml
# D-Graph goal 노드 (이미 존재)
goal:
  goal_id: "GOL-market-size-001"
  name: "한국 어학 시장 규모 파악"
  target_metrics:
    - metric_id: "MET-TAM"
      operator: "exists"
      quality_min: 0.7  # Policy 연동
    - metric_id: "MET-SAM"
      operator: "exists"
      quality_min: 0.7
  
  # Success Predicate (신규 필드)
  success_predicate:
    type: "all_of"
    conditions:
      - type: "metric_exists"
        metric_id: "MET-TAM"
      - type: "metric_exists"
        metric_id: "MET-SAM"
      - type: "evidence_quality"
        threshold: "policy:min_literal_ratio"  # Policy Engine 연동
      - type: "completeness"
        min_metrics: 2
```

**구현**:

```python
@dataclass
class GoalPredicate:
    """Success Predicate (검증 가능)"""
    
    predicate_id: str
    goal_id: str
    type: str  # "all_of" | "any_of" | "threshold"
    conditions: List[Dict[str, Any]]
    
    def evaluate(self, ledgers: Ledgers) -> bool:
        """Predicate 평가
        
        Args:
            ledgers: 현재 상태
        
        Returns:
            True if 성공 조건 만족
        """
        if self.type == "all_of":
            return all(self._check_condition(c, ledgers) for c in self.conditions)
        # ...
    
    def get_diff_report(self, ledgers: Ledgers) -> Dict:
        """실패한 조건 = Diff Report
        
        Returns:
            {
                "missing": ["MET-SAM"],
                "low_quality": ["MET-TAM"],
                "gaps": [...]
            }
        """
        diff = {"missing": [], "low_quality": [], "gaps": []}
        
        for condition in self.conditions:
            if not self._check_condition(condition, ledgers):
                # 어떤 조건이 실패했는지 기록
                if condition["type"] == "metric_exists":
                    diff["missing"].append(condition["metric_id"])
                elif condition["type"] == "evidence_quality":
                    # quality 부족한 metric 찾기
                    pass
        
        return diff
```

---

### 2.2 TaskGraph/Queue (How)

**Task 타입**:

```python
from enum import Enum
from dataclasses import dataclass

class TaskType(Enum):
    """Task 타입"""
    RUN_WORKFLOW = "run_workflow"
    COLLECT_EVIDENCE = "collect_evidence"
    COMPUTE_METRIC = "compute_metric"
    VALIDATE_GOAL = "validate_goal"
    PROPOSE_REPLAN = "propose_replan"

@dataclass
class Task:
    """실행 작업 단위"""
    
    task_id: str
    task_type: TaskType
    
    # 의존성
    depends_on: List[str] = field(default_factory=list)  # task_id 리스트
    
    # 입력/출력
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: List[str] = field(default_factory=list)
    
    # 품질 게이트
    quality_gate: Optional[Dict] = None
    # {"min_literal_ratio": 0.7, "policy_ref": "reporting_strict"}
    
    # 예산
    budget: Optional[Dict] = None
    # {"max_time_sec": 30, "max_retries": 2}
    
    # 상태
    status: str = "pending"  # pending | running | completed | failed
    
    # 결과
    result: Optional[Dict] = None
    
    def can_execute(self, ledgers: Ledgers) -> bool:
        """실행 가능 여부
        
        의존성 완료 + 리소스 가용 확인
        """
        # 의존 Task 모두 완료?
        for dep_id in self.depends_on:
            dep_task = ledgers.get_task(dep_id)
            if not dep_task or dep_task.status != "completed":
                return False
        
        return True
```

**TaskQueue**:

```python
class TaskQueue:
    """Task 실행 큐 (의존성 기반)"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.execution_order: List[str] = []
    
    def enqueue(self, tasks: List[Task]):
        """Task 추가 (의존성 정렬)"""
        for task in tasks:
            self.tasks[task.task_id] = task
        
        # 의존성 기반 정렬 (Topological Sort)
        self.execution_order = self._topological_sort()
    
    def dequeue(self) -> Optional[Task]:
        """실행 가능한 Task 반환"""
        for task_id in self.execution_order:
            task = self.tasks[task_id]
            if task.status == "pending" and task.can_execute(self.ledgers):
                return task
        
        return None
```

---

### 2.3 Ledgers (State)

**2개로 상태 고정** (Magentic-One 핵심)

```python
@dataclass
class TaskLedger:
    """문제공간 작업기억
    
    Facts, Evidence, Metrics, Gaps, Artifacts
    """
    
    # Facts
    facts: Dict[str, Any] = field(default_factory=dict)
    # {"domain_id": "Adult_Language_Education_KR", "region": "KR"}
    
    # Assumptions
    assumptions: List[str] = field(default_factory=list)
    # ["TAM > 1조원 가정", ...]
    
    # Evidence
    evidence_refs: List[str] = field(default_factory=list)
    # ["EVD-001", "EVD-002", ...]
    
    # Derived Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    # {"MET-TAM": {"value": 1.5e12, "quality": 0.75}, ...}
    
    # Gaps (부족한 것)
    gaps: List[str] = field(default_factory=list)
    # ["MET-SAM", "MET-SOM"]
    
    # Artifacts
    artifacts: List[str] = field(default_factory=list)
    # ["ART-market-size-001", ...]
    
    def get_metric_quality(self, metric_id: str) -> float:
        """Metric 품질 조회"""
        metric = self.metrics.get(metric_id)
        if not metric:
            return 0.0
        return metric.get("quality", 0.0)

@dataclass
class ProgressLedger:
    """프로세스 제어판
    
    Task 상태, Stall, Loop, Budget
    """
    
    # Task 상태
    task_statuses: Dict[str, str] = field(default_factory=dict)
    # {"TASK-001": "completed", "TASK-002": "running", ...}
    
    # Stall 카운터
    stall_counters: Dict[str, int] = field(default_factory=dict)
    # {"evidence_collection": 2, ...}
    
    # Loop 플래그
    loop_flags: Dict[str, bool] = field(default_factory=dict)
    # {"query_loop": False, "task_loop": False}
    
    # Budget
    budgets: Dict[str, Any] = field(default_factory=dict)
    # {"time_spent_sec": 120, "llm_calls": 5, "max_time": 300}
    
    # Next Action
    next_action: Optional[str] = None
    # "continue" | "replan" | "stop"
    
    # Replanning 카운터
    replanning_count: int = 0

class Ledgers:
    """Ledger 컨테이너"""
    
    def __init__(self):
        self.task_ledger = TaskLedger()
        self.progress_ledger = ProgressLedger()
    
    def update_from_task_result(self, task: Task, result: Dict):
        """Task 결과 → Ledger 업데이트"""
        
        # TaskLedger 업데이트
        if task.task_type == TaskType.COLLECT_EVIDENCE:
            self.task_ledger.evidence_refs.extend(result.get("evidence_ids", []))
        
        elif task.task_type == TaskType.COMPUTE_METRIC:
            metric_id = result.get("metric_id")
            self.task_ledger.metrics[metric_id] = {
                "value": result.get("value"),
                "quality": result.get("quality", {})
            }
        
        # ProgressLedger 업데이트
        self.progress_ledger.task_statuses[task.task_id] = "completed"
        self.progress_ledger.budgets["time_spent_sec"] += result.get("time_sec", 0)
```

---

### 2.4 Verifier (Check)

**Predicate 검증 + Diff Report 생성**

```python
class Verifier:
    """Predicate 검증 및 Diff 생성
    
    Policy Engine 연동 (품질 기준)
    """
    
    def __init__(self, policy_engine):
        self.policy_engine = policy_engine
    
    def verify_goal(
        self,
        goal: Goal,
        ledgers: Ledgers
    ) -> Dict[str, Any]:
        """Goal Predicate 검증
        
        Returns:
            {
                "satisfied": True/False,
                "diff_report": {...},
                "quality_level": "A"
            }
        """
        predicate = goal.success_predicate
        
        # Predicate 평가
        satisfied = self._evaluate_predicate(predicate, ledgers)
        
        if satisfied:
            return {
                "satisfied": True,
                "diff_report": {},
                "quality_level": self._assess_quality(ledgers)
            }
        
        # Diff Report 생성
        diff_report = self._generate_diff_report(predicate, ledgers)
        
        return {
            "satisfied": False,
            "diff_report": diff_report,
            "quality_level": self._assess_quality(ledgers)
        }
    
    def _evaluate_predicate(
        self,
        predicate: Dict,
        ledgers: Ledgers
    ) -> bool:
        """Predicate 평가"""
        
        conditions = predicate.get("conditions", [])
        
        for condition in conditions:
            cond_type = condition["type"]
            
            if cond_type == "metric_exists":
                metric_id = condition["metric_id"]
                if metric_id not in ledgers.task_ledger.metrics:
                    return False
            
            elif cond_type == "evidence_quality":
                # Policy Engine에서 기준 조회
                threshold = self._get_quality_threshold(condition)
                
                # 모든 Metric 평균 품질
                avg_quality = self._get_average_quality(ledgers)
                
                if avg_quality < threshold:
                    return False
        
        return True
    
    def _get_quality_threshold(self, condition: Dict) -> float:
        """Policy Engine에서 품질 기준 조회
        
        하드코딩 금지! Policy Engine이 단일 소스.
        """
        threshold_ref = condition.get("threshold")
        
        if threshold_ref.startswith("policy:"):
            # "policy:min_literal_ratio" → Policy Engine 조회
            policy_key = threshold_ref.split(":")[1]
            policy = self.policy_engine.get_current_policy()
            return policy.get(policy_key, 0.5)
        
        return float(threshold_ref)
    
    def _generate_diff_report(
        self,
        predicate: Dict,
        ledgers: Ledgers
    ) -> Dict:
        """Diff Report 생성
        
        무엇이 부족한지 명확히 기술.
        
        Returns:
            {
                "missing_metrics": ["MET-SAM", "MET-SOM"],
                "low_quality_metrics": ["MET-TAM"],
                "quality_gap": 0.3,  # 현재 0.4, 필요 0.7
                "missing_evidence": 5  # 추가 필요
            }
        """
        diff = {
            "missing_metrics": [],
            "low_quality_metrics": [],
            "quality_gap": 0.0,
            "missing_evidence": 0
        }
        
        conditions = predicate.get("conditions", [])
        
        for condition in conditions:
            if condition["type"] == "metric_exists":
                metric_id = condition["metric_id"]
                if metric_id not in ledgers.task_ledger.metrics:
                    diff["missing_metrics"].append(metric_id)
            
            elif condition["type"] == "evidence_quality":
                threshold = self._get_quality_threshold(condition)
                current = self._get_average_quality(ledgers)
                
                if current < threshold:
                    diff["quality_gap"] = threshold - current
                    
                    # 어떤 Metric이 부족한지
                    for metric_id, metric in ledgers.task_ledger.metrics.items():
                        if metric.get("quality", 0) < threshold:
                            diff["low_quality_metrics"].append(metric_id)
        
        return diff
```

---

### 2.5 Replanner (Adjust)

**부분 재계획 (브랜치 단위)**

```python
class Replanner:
    """부분 재계획 엔진
    
    OrchVis: 실패한 브랜치만 재계획
    """
    
    def generate_tasks_from_diff(
        self,
        diff_report: Dict,
        goal: Goal,
        ledgers: Ledgers
    ) -> List[Task]:
        """Diff Report → Task 생성
        
        부족한 것만 채우는 Task.
        
        Args:
            diff_report: Verifier 결과
            goal: 목표
            ledgers: 현재 상태
        
        Returns:
            Task 리스트
        """
        tasks = []
        
        # Missing Metrics → ComputeMetric Task
        for metric_id in diff_report.get("missing_metrics", []):
            tasks.append(Task(
                task_id=f"TASK-compute-{metric_id}",
                task_type=TaskType.COMPUTE_METRIC,
                inputs={"metric_id": metric_id},
                expected_outputs=[metric_id]
            ))
        
        # Low Quality → CollectEvidence Task
        if diff_report.get("quality_gap", 0) > 0:
            tasks.append(Task(
                task_id=f"TASK-collect-evidence-{uuid.uuid4().hex[:8]}",
                task_type=TaskType.COLLECT_EVIDENCE,
                inputs={
                    "target_metrics": diff_report.get("low_quality_metrics", []),
                    "additional_sources": 3
                },
                quality_gate={"min_literal_ratio": diff_report["quality_gap"] + 0.1}
            ))
        
        return tasks
    
    def replan_branch(
        self,
        failed_goal: Goal,
        diff_report: Dict,
        ledgers: Ledgers
    ) -> Dict:
        """실패한 브랜치만 재계획
        
        OrchVis 핵심: 전체 재계획 ❌, 실패 부분만 ✅
        
        Returns:
            {
                "replan_scope": "branch",  # 부분만
                "affected_goals": ["GOL-entry-strategy"],  # 영향 받는 goal
                "new_tasks": [...]
            }
        """
        # 실패한 Goal과 연결된 브랜치 찾기
        affected_goals = self._find_downstream_goals(failed_goal)
        
        # 해당 브랜치만 재계획
        new_tasks = self.generate_tasks_from_diff(diff_report, failed_goal, ledgers)
        
        return {
            "replan_scope": "branch",
            "affected_goals": [g.goal_id for g in affected_goals],
            "new_tasks": new_tasks,
            "unchanged_branches": self._get_unaffected_branches(failed_goal)
        }
```

---

### 2.6 LLM as PlanPatch Provider

**LLM = 결정권자 ❌ → PlanPatch 제안자 ✅**

```python
@dataclass
class PlanPatch:
    """Plan 변경 제안 (구조화)
    
    LLM 출력 → 검증 가능한 구조.
    """
    
    patch_id: str
    patch_type: str  # "add_task" | "remove_task" | "modify_goal"
    
    # 변경 내용
    changes: Dict[str, Any]
    # {
    #   "task_type": "collect_evidence",
    #   "inputs": {...}
    # }
    
    # 근거
    reasoning: str
    
    # LLM 메타
    llm_model: str
    llm_prompt: str
    llm_response: str
    
    def validate_schema(self) -> bool:
        """Patch 스키마 검증"""
        required_fields = ["patch_type", "changes", "reasoning"]
        return all(hasattr(self, f) and getattr(self, f) for f in required_fields)

class LLMPatchProvider:
    """LLM 기반 Patch 제안자
    
    결정 ❌ → 제안 ✅
    Kernel이 검증 후 적용.
    """
    
    def __init__(self, llm_client, model="gpt-4"):
        self.llm = llm_client
        self.model = model
    
    def propose_patch(
        self,
        goal: Goal,
        diff_report: Dict,
        ledgers: Ledgers
    ) -> PlanPatch:
        """Diff Report → PlanPatch 제안
        
        LLM에게 "무엇이 부족한지" 알려주고,
        "어떻게 채울지" 제안 받음.
        """
        prompt = f"""
        목표: {goal.name}
        
        현재 상태:
        - Metrics: {list(ledgers.task_ledger.metrics.keys())}
        - Evidence Quality: {self._get_avg_quality(ledgers):.1%}
        
        부족한 것:
        - Missing: {diff_report.get("missing_metrics", [])}
        - Low Quality: {diff_report.get("low_quality_metrics", [])}
        - Quality Gap: {diff_report.get("quality_gap", 0):.1%}
        
        부족한 것을 채우기 위한 Task를 제안하세요.
        
        Output (JSON):
        {{
            "patch_type": "add_task",
            "changes": {{
                "task_type": "collect_evidence",
                "inputs": {{
                    "target_metrics": ["MET-SAM"],
                    "sources": ["KOSIS", "DART"]
                }}
            }},
            "reasoning": "SAM 없음 → Evidence 수집 필요"
        }}
        """
        
        response = self.llm.complete(prompt, model=self.model, temperature=0.3)
        
        # JSON 파싱
        import json
        patch_data = json.loads(response)
        
        # PlanPatch 생성
        patch = PlanPatch(
            patch_id=f"PATCH-{uuid.uuid4().hex[:8]}",
            patch_type=patch_data["patch_type"],
            changes=patch_data["changes"],
            reasoning=patch_data["reasoning"],
            llm_model=self.model,
            llm_prompt=prompt,
            llm_response=response
        )
        
        return patch

class OrchestrationKernel:
    """Orchestration Kernel (Reconcile Engine)"""
    
    def apply_patch(self, patch: PlanPatch) -> bool:
        """Patch 검증 후 적용
        
        LLM 출력 → 검증 → 적용
        
        Returns:
            True if 적용 성공
        """
        # 1. 스키마 검증
        if not patch.validate_schema():
            self._log_patch_rejection(patch, "invalid_schema")
            return False
        
        # 2. 정책 검증 (Policy Engine)
        if not self._validate_patch_against_policy(patch):
            self._log_patch_rejection(patch, "policy_violation")
            return False
        
        # 3. 리소스 검증
        if not self._check_resource_availability(patch):
            self._log_patch_rejection(patch, "resource_unavailable")
            return False
        
        # 4. 적용
        if patch.patch_type == "add_task":
            task = self._create_task_from_patch(patch)
            self.task_queue.enqueue([task])
        
        # 5. DecisionLog 기록
        self.decision_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "patch_applied",
            "patch_id": patch.patch_id,
            "patch": patch.__dict__,
            "validation": "passed"
        })
        
        return True
```

---

## 3. Orchestration Kernel 구현

### 3.1 핵심 Reconcile Loop

```python
class OrchestrationKernel:
    """Orchestration Kernel (Reconcile Engine)
    
    Desired State (Goal) ↔ Observed State (Ledgers) 비교
    → Diff → Tasks → Execute → 반복
    """
    
    def __init__(
        self,
        workflow_orchestrator: WorkflowOrchestrator,
        policy_engine,
        llm_patch_provider: Optional[LLMPatchProvider] = None
    ):
        """
        Args:
            workflow_orchestrator: canonical_workflows 실행기
            policy_engine: Policy Engine (품질 기준)
            llm_patch_provider: LLM 기반 Patch 제안자 (선택)
        """
        self.workflow_orch = workflow_orchestrator
        self.policy_engine = policy_engine
        self.llm_patch_provider = llm_patch_provider
        
        # Core
        self.verifier = Verifier(policy_engine)
        self.replanner = Replanner()
        self.governor = Governor()
        
        # State
        self.goal_graph: Dict[str, Goal] = {}
        self.task_queue = TaskQueue()
        self.ledgers = Ledgers()
        
        # Logging
        self.decision_log: List[Dict] = []
    
    def execute(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """Reconcile Loop 실행
        
        Args:
            query: 사용자 질문
            context: project_context_id 등
        
        Returns:
            {
                "goal_satisfied": True,
                "ledgers": {...},
                "decision_log": [...],
                "execution_trace": [...]
            }
        """
        # 1. Goal 생성 (D-Graph)
        goal = self._create_goal_from_query(query, context)
        self.goal_graph[goal.goal_id] = goal
        
        self._log_decision("goal_created", {"goal": goal.goal_id})
        
        # 2. 초기 Task 생성
        initial_tasks = self._generate_initial_tasks(goal)
        self.task_queue.enqueue(initial_tasks)
        
        # 3. Reconcile Loop
        max_iterations = 20
        iteration = 0
        
        while iteration < max_iterations:
            # 3-1. Verify Goal
            verification = self.verifier.verify_goal(goal, self.ledgers)
            
            if verification["satisfied"]:
                # Goal 달성!
                self._log_decision("goal_satisfied", verification)
                break
            
            # 3-2. Diff Report
            diff_report = verification["diff_report"]
            
            self._log_decision(
                "diff_detected",
                diff_report,
                f"Gap: {len(diff_report.get('missing_metrics', []))}개"
            )
            
            # 3-3. Task 생성/재계획
            if self.llm_patch_provider:
                # LLM Patch 제안
                patch = self.llm_patch_provider.propose_patch(
                    goal, diff_report, self.ledgers
                )
                
                # 검증 후 적용
                if self.apply_patch(patch):
                    self._log_decision("patch_applied", {"patch_id": patch.patch_id})
                else:
                    # Fallback: 규칙 기반
                    tasks = self.replanner.generate_tasks_from_diff(
                        diff_report, goal, self.ledgers
                    )
                    self.task_queue.enqueue(tasks)
            
            else:
                # 규칙 기반
                tasks = self.replanner.generate_tasks_from_diff(
                    diff_report, goal, self.ledgers
                )
                self.task_queue.enqueue(tasks)
            
            # 3-4. Execute Task
            task = self.task_queue.dequeue()
            
            if task is None:
                # Task 없음 → Stall
                if self.governor.check_stall(self.ledgers):
                    break
                continue
            
            result = self._execute_task(task)
            
            # 3-5. Update Ledgers
            self.ledgers.update_from_task_result(task, result)
            
            # 3-6. Governor 체크
            if self.governor.should_stop(self.ledgers):
                self._log_decision("governor_stop", {"reason": "budget_exceeded"})
                break
            
            iteration += 1
        
        return {
            "goal_satisfied": verification["satisfied"],
            "ledgers": self.ledgers,
            "decision_log": self.decision_log,
            "iterations": iteration
        }
```

---

## 4. Evidence-first 원칙 통합

### 4.1 Metric 계산 = Stage 추적

**4-Stage Resolver**: Evidence → Derived → Prior → Fusion

**Orchestration 역할**:
- Stage 추적 (Ledger)
- Stage 승격 조건 (Policy)
- 자동 Task 생성

```python
class MetricStageTracker:
    """Metric Stage 추적 (Ledger 활용)"""
    
    def get_metric_stage(
        self,
        metric_id: str,
        ledgers: Ledgers
    ) -> str:
        """Metric의 현재 Stage
        
        Returns:
            "evidence" | "derived" | "prior" | "fusion" | "none"
        """
        metric = ledgers.task_ledger.metrics.get(metric_id)
        
        if not metric:
            return "none"
        
        # Quality 기반 Stage 판단
        quality = metric.get("quality", {})
        literal_ratio = quality.get("literal_ratio", 0)
        
        if literal_ratio > 0.7:
            return "evidence"  # Direct Evidence
        elif literal_ratio > 0:
            return "derived"  # 일부 Evidence
        elif quality.get("origin") == "prior":
            return "prior"
        else:
            return "fusion"
    
    def should_collect_more_evidence(
        self,
        metric_id: str,
        ledgers: Ledgers,
        policy_ref: str
    ) -> bool:
        """더 많은 Evidence 수집 필요?
        
        Policy Engine 연동.
        """
        stage = self.get_metric_stage(metric_id, ledgers)
        
        # Evidence Stage가 아니면 수집 시도
        if stage in ["prior", "none"]:
            return True
        
        # Policy 기준 미달이면 수집
        metric = ledgers.task_ledger.metrics[metric_id]
        quality = metric.get("quality", {})
        
        policy = self.policy_engine.get_policy(policy_ref)
        
        if quality.get("literal_ratio", 0) < policy.min_literal_ratio:
            return True
        
        return False
```

**Orchestration에서 사용**:

```python
# Verifier에서:
def _generate_diff_report(self, predicate, ledgers):
    diff = {...}
    
    # Stage 확인
    for metric_id in required_metrics:
        stage = stage_tracker.get_metric_stage(metric_id, ledgers)
        
        if stage == "prior":
            diff["prior_stage_metrics"].append(metric_id)
            # → Evidence 수집 Task 자동 생성
            diff["action_required"] = "collect_evidence"
    
    return diff
```

---

## 5. cmis.yaml 업데이트

### 5.1 orchestration_kernel 섹션

```yaml
orchestration_kernel:
  description: "Reconcile 기반 동적 재설계 엔진 (Desired ↔ Observed)"
  pattern: "Kubernetes Controller"
  
  philosophy:
    architecture: "Objective-Oriented (목표 중심)"
    paradigm: "Reconcile Loop (Desired State ↔ Observed State)"
    core_principle: "Diff → Tasks → Execute → Verify → Repeat"
  
  core_abstractions:
    - id: "goal_graph"
      description: "목표 그래프 (D-Graph goal 노드 활용)"
      reuses: "substrate_plane.graphs.decision_graph.goal"
      extension: "success_predicate 필드 추가"
      
    - id: "task_graph"
      description: "실행 작업 그래프"
      task_types:
        - "run_workflow"
        - "collect_evidence"
        - "compute_metric"
        - "validate_goal"
        - "propose_replan"
    
    - id: "ledgers"
      description: "상태 2개로 고정 (Magentic-One)"
      ledgers:
        - name: "task_ledger"
          description: "문제공간 작업기억"
          fields: ["facts", "assumptions", "evidence_refs", "metrics", "gaps", "artifacts"]
        
        - name: "progress_ledger"
          description: "프로세스 제어판"
          fields: ["task_statuses", "stall_counters", "loop_flags", "budgets", "next_action"]
    
    - id: "verifier"
      description: "Predicate 검증 + Diff Report"
      policy_integration: "Policy Engine에서 품질 기준 조회 (단일 소스)"
      
    - id: "replanner"
      description: "부분 재계획 (OrchVis)"
      strategy: "실패 브랜치만 재계획, 나머지 계속"
  
  llm_role:
    role: "PlanPatch 제안자 (결정권자 ❌)"
    workflow:
      - "LLM → PlanPatch 제안"
      - "Kernel → Schema 검증"
      - "Kernel → Policy 검증"
      - "Kernel → 적용"
      - "DecisionLog → Patch 원문 + 검증 결과 기록"
  
  evidence_first_integration:
    description: "4-Stage Resolver 통합"
    stages: ["evidence", "derived", "prior", "fusion"]
    orchestration_rule:
      - "Metric Stage 추적 (Ledger)"
      - "Stage 승격 조건 (Policy)"
      - "Evidence 부족 → CollectEvidence Task 자동 생성"
      - "Prior 사용 시 명시적 DecisionLog + 경고"
  
  greenfield_brownfield:
    integration: "project_context_id 기반 자동 판단"
    greenfield:
      predicate_mode: "greenfield_constraints만 반영"
    brownfield:
      predicate_mode: "constraints_profile + execution_fit + baseline_ROI"
  
  governor:
    budgets:
      max_time_sec: 300
      max_llm_calls: 20
      max_iterations: 20
    
    stall_detection:
      stall_threshold: 2
      action: "propose_replan or stop"
    
    loop_detection:
      max_similar_tasks: 3
    
    quality_gates:
      source: "policy_engine"  # 단일 소스
  
  decision_log:
    format: "event_sourcing"
    stored_in: "memory_store"
    includes:
      - "goal_created"
      - "initial_plan"
      - "diff_detected"
      - "patch_proposed"
      - "patch_validated"
      - "patch_applied"
      - "task_executed"
      - "replanning"
```

---

## 6. 구현 계획 (최종)

### Phase 1: Kernel Core (2주)

**파일**:
1. `cmis_core/orchestration_kernel.py` (600줄)
   - OrchestrationKernel 클래스
   - Reconcile Loop
   - Ledgers

2. `cmis_core/goal_predicate.py` (200줄)
   - GoalPredicate 클래스
   - Predicate 평가

3. `cmis_core/task.py` (300줄)
   - Task 클래스
   - TaskQueue

4. `cmis_core/verifier.py` (200줄)
   - Verifier 클래스
   - Diff Report

5. `cmis_core/replanner.py` (200줄)
   - Replanner 클래스
   - 부분 재계획

6. `cmis_core/plan_patch.py` (150줄)
   - PlanPatch 클래스
   - LLMPatchProvider

**테스트**: 20개

---

### Phase 2: Interface 통합 (1주)

**파일**:
1. `cmis_cursor/interface.py` (150줄)
2. `cmis_web/api.py` (FastAPI)
3. `.cursorrules` 확장

**테스트**: 10개

---

### Phase 3: Policy/D-Graph 연동 (3일)

**작업**:
- Goal → D-Graph 저장
- Policy Engine 연동
- Greenfield/Brownfield 자동 판단

---

**총 3주**

---

## 7. 핵심 개선 6개 반영

### 1. Goal = D-Graph 노드 ✅

```python
# cmis_core/types.py (확장)

@dataclass
class Goal:
    goal_id: str
    name: str
    target_metrics: List[Dict]
    
    # 신규 필드
    success_predicate: Optional[Dict] = None
    # {
    #   "type": "all_of",
    #   "conditions": [
    #     {"type": "metric_exists", "metric_id": "MET-TAM"},
    #     {"type": "evidence_quality", "threshold": "policy:min_literal_ratio"}
    #   ]
    # }
```

### 2. Predicate 기반 Diff Report ✅

### 3. LLM = PlanPatch 제안자 ✅

### 4. Policy Engine = 품질 게이트 단일 소스 ✅

### 5. 부분 재계획 (브랜치) ✅

### 6. 리소스 Registry ✅

```python
class ResourceRegistry:
    """리소스 1급화 (TEA)"""
    
    def __init__(self):
        self.capabilities = {
            "cursor": ["code_edit", "file_write", "shell_exec"],
            "web": ["display_chart", "user_input"],
            "cli": ["shell_exec"],
            "api": []
        }
    
    def can_execute_task(
        self,
        task: Task,
        interface: str
    ) -> bool:
        """Interface에서 Task 실행 가능?"""
        
        required_capabilities = task.required_capabilities
        available = self.capabilities.get(interface, [])
        
        return all(cap in available for cap in required_capabilities)
```

---

## 8. Summary

### 최종 구조

```
Orchestration Kernel (Reconcile)
 ├─ GoalGraph (D-Graph 활용)
 ├─ TaskQueue
 ├─ Ledgers (2개)
 ├─ Verifier (Predicate + Policy)
 ├─ Replanner (부분)
 └─ LLMPatchProvider (제안)
     ↓
WorkflowOrchestrator (기존)
     ↓
Engines (9개)
```

### 핵심 가치

1. **간결함**: if/else 대신 Predicate/Task 추가
2. **검증 가능**: Predicate 명확
3. **재현 가능**: Event-sourcing DecisionLog
4. **확장 가능**: 새 Predicate/Task 타입 추가만
5. **Policy 통합**: Policy Engine이 단일 소스
6. **프로덕션**: LLM Patch 검증

---

**작성**: 2025-12-12
**버전**: v3.0 (Reconcile)
**우선순위**: ⭐⭐⭐
**다음**: orchestration_kernel.py 구현
