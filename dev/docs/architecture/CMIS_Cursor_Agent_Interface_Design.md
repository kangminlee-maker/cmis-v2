# CMIS Cursor Agent Interface 설계

**작성일**: 2025-12-13
**버전**: v1.0
**상태**: 설계 단계

---

## 0. 개요

### 0.1 목표

**Cursor Agent를 CMIS Orchestration의 5번째 인터페이스로 추가**

Cursor는 단순 IDE가 아니라 **자율 실행 가능한 Agent 환경**:
- 파일 읽기/쓰기
- 터미널 명령 실행
- 웹 검색
- 코드 실행
- 반복 작업

**CMIS Orchestration Kernel이 Cursor Agent를 제어**:
- Cursor = Task 실행자
- Kernel = 목표 관리/검증/재계획

---

### 0.2 CMIS 철학 정합성

**Agent = Persona + Workflow + View (엔진 아님)**

```
Cursor Agent Interface
    ↓
Orchestration Kernel (Reconcile Loop)
    ↓
WorkflowOrchestrator
    ↓
CMIS Engines (9개)
```

**역할 분리**:
- Cursor Interface: Cursor API 호출/결과 파싱
- Orchestration Kernel: 무엇을, 언제, 왜
- WorkflowOrchestrator: 어떻게
- Engines: 할 수 있는 것

---

## 1. Architecture

### 1.1 전체 구조

```
┌─────────────────────────────────────────┐
│ User Query                              │
│ "한국 어학 시장 TAM/SAM 파악"            │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Cursor Agent Interface                  │
│  CursorAgentInterface.execute()         │
│                                         │
│  1. Query → Goal (D-Graph)              │
│  2. OrchestrationKernel.execute()       │
│  3. Kernel → Task 생성                  │
│  4. Task → Cursor API 호출               │
│  5. 결과 → Ledger 업데이트               │
│  6. Verify → Diff → Replan               │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Orchestration Kernel (Reconcile Loop)   │
│  GoalGraph + TaskQueue + Ledgers        │
│  + Verifier + Replanner                 │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Task Executor                           │
│  - RunWorkflow Task → WorkflowOrch      │
│  - CollectEvidence Task → EvidenceEngine│
│  - ComputeMetric Task → ValueEngine     │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Cursor API (외부)                        │
│  - 파일 읽기/쓰기                         │
│  - 터미널 실행                           │
│  - 웹 검색                               │
└─────────────────────────────────────────┘
```

---

### 1.2 Cursor의 역할

**Cursor = Task 실행 환경**

```python
Task Types (Cursor 적합):
1. RunWorkflow
   - CMIS canonical_workflows 실행
   - Engines 호출

2. CollectEvidence
   - EvidenceEngine 실행
   - 웹 검색 (Cursor API)

3. ComputeMetric
   - ValueEngine 실행
   - 계산/추론

4. ValidateGoal
   - Verifier 실행
   - Predicate 검증

5. ProposeReplan
   - LLMPatchProvider 실행 (선택)
   - Patch 제안
```

**Cursor가 제공하는 것**:
- 자율 실행 (사람 개입 최소)
- 툴 호출 (파일/터미널/웹)
- 반복 작업
- Context 유지 (긴 대화)

---

## 2. Interface 설계

### 2.1 CursorAgentInterface

```python
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from cmis_core.orchestration_kernel import OrchestrationKernel
from cmis_core.workflow import WorkflowOrchestrator
from cmis_core.policy_engine import PolicyEngine


@dataclass
class CursorAgentConfig:
    """Cursor Agent 설정"""

    # 기본 설정
    project_root: Path
    default_role_id: str = "structure_analyst"
    default_policy_mode: str = "reporting_strict"

    # Orchestration 설정
    max_iterations: int = 20
    max_time_sec: int = 300
    max_llm_calls: int = 20

    # Cursor 설정
    enable_cursor_tools: bool = True
    enable_web_search: bool = True
    enable_file_ops: bool = True
    enable_terminal: bool = False  # 안전장치


class CursorAgentInterface:
    """Cursor Agent Interface v1.0

    역할:
    - User Query → Goal 변환
    - OrchestrationKernel 실행
    - Task → Cursor API 호출
    - 결과 포맷팅 (Cursor 출력)

    설계:
    - Orchestration Kernel이 핵심
    - Cursor는 Task 실행 환경
    - Interface는 번역기/어댑터
    """

    def __init__(
        self,
        config: Optional[CursorAgentConfig] = None
    ):
        """
        Args:
            config: Cursor Agent 설정
        """
        if config is None:
            config = CursorAgentConfig(
                project_root=Path(__file__).parent.parent.parent
            )

        self.config = config

        # Core Components
        self.policy_engine = PolicyEngine(config.project_root)
        self.workflow_orch = WorkflowOrchestrator(
            project_root=config.project_root
        )

        # Orchestration Kernel (v3.7.0)
        self.kernel = OrchestrationKernel(
            workflow_orchestrator=self.workflow_orch,
            policy_engine=self.policy_engine,
            llm_patch_provider=None  # Phase 1: 규칙 기반만
        )

    def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        role_id: Optional[str] = None,
        policy_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """User Query 실행

        프로세스:
        1. Query → Goal 변환
        2. OrchestrationKernel.execute()
        3. 결과 포맷팅

        Args:
            query: 사용자 질문
            context: 컨텍스트 (project_context_id 등)
            role_id: Role 오버라이드
            policy_mode: Policy 오버라이드

        Returns:
            {
                "goal_satisfied": True/False,
                "results": {...},
                "execution_trace": [...],
                "decision_log": [...]
            }
        """
        # Role/Policy 결정
        if role_id is None:
            role_id = self.config.default_role_id

        if policy_mode is None:
            usage = self._infer_usage_from_query(query)
            policy_mode = self.policy_engine.resolve_policy(role_id, usage)

        # Context 보강
        if context is None:
            context = {}

        context["role_id"] = role_id
        context["policy_mode"] = policy_mode

        # Orchestration Kernel 실행
        result = self.kernel.execute(query, context)

        # Cursor 출력 포맷팅
        formatted = self._format_for_cursor(result)

        return formatted

    def _infer_usage_from_query(self, query: str) -> str:
        """Query에서 usage 추론

        Args:
            query: 사용자 질문

        Returns:
            "reporting" | "exploration" | "decision"

        Rules:
            - "파악", "분석", "현황" → reporting
            - "기회", "발굴", "탐색" → exploration
            - "전략", "의사결정", "선택" → decision
        """
        query_lower = query.lower()

        # Exploration keywords
        if any(kw in query_lower for kw in ["기회", "발굴", "탐색", "opportunity", "explore"]):
            return "exploration"

        # Decision keywords
        if any(kw in query_lower for kw in ["전략", "의사결정", "선택", "strategy", "decision"]):
            return "decision"

        # Default: reporting
        return "reporting"

    def _format_for_cursor(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestration 결과 → Cursor 출력 포맷

        Args:
            result: OrchestrationKernel 결과

        Returns:
            Cursor 출력용 Dict
        """
        # Ledgers 추출
        ledgers = result.get("ledgers")

        # 핵심 Metrics
        metrics = {}
        if ledgers and hasattr(ledgers, "project_ledger"):
            metrics = ledgers.project_ledger.metrics

        # Evidence
        evidence_refs = []
        if ledgers and hasattr(ledgers, "project_ledger"):
            evidence_refs = ledgers.project_ledger.evidence_refs

        # Artifacts
        artifacts = []
        if ledgers and hasattr(ledgers, "project_ledger"):
            artifacts = ledgers.project_ledger.artifacts

        return {
            "status": "success" if result.get("goal_satisfied") else "incomplete",
            "goal_satisfied": result.get("goal_satisfied", False),
            "metrics": metrics,
            "evidence_refs": evidence_refs,
            "artifacts": artifacts,
            "execution_summary": {
                "iterations": result.get("iterations", 0),
                "total_tasks": len(result.get("decision_log", [])),
            },
            "decision_log": result.get("decision_log", []),
            "next_steps": self._suggest_next_steps(result)
        }

    def _suggest_next_steps(self, result: Dict[str, Any]) -> list[str]:
        """다음 단계 제안

        Args:
            result: Orchestration 결과

        Returns:
            Next steps 리스트
        """
        suggestions = []

        # Goal 미달성 시
        if not result.get("goal_satisfied"):
            ledgers = result.get("ledgers")

            if ledgers and hasattr(ledgers, "project_ledger"):
                gaps = ledgers.project_ledger.gaps

                if gaps:
                    suggestions.append(f"부족한 Metrics 수집: {', '.join(gaps)}")

        # 품질 개선 가능 시
        # TODO: Quality 체크 로직

        # 추가 분석 제안
        suggestions.append("opportunity_discovery 실행 (기회 발굴)")
        suggestions.append("strategy_design 실행 (전략 수립)")

        return suggestions
```

---

### 2.2 Task Executor

```python
from typing import Protocol

from cmis_core.orchestration_kernel import Task, TaskType


class TaskExecutor(Protocol):
    """Task 실행 인터페이스

    Orchestration Kernel → Task 실행
    """

    def execute(self, task: Task) -> Dict[str, Any]:
        """Task 실행

        Args:
            task: Task 객체

        Returns:
            {
                "task_id": "...",
                "status": "completed" | "failed",
                "result": {...},
                "time_sec": 1.23
            }
        """
        ...


class CursorTaskExecutor:
    """Cursor 기반 Task 실행기

    Task Type별 실행 로직
    """

    def __init__(
        self,
        workflow_orch: WorkflowOrchestrator,
        evidence_engine,
        value_engine
    ):
        """
        Args:
            workflow_orch: WorkflowOrchestrator
            evidence_engine: EvidenceEngine
            value_engine: ValueEngine
        """
        self.workflow_orch = workflow_orch
        self.evidence_engine = evidence_engine
        self.value_engine = value_engine

    def execute(self, task: Task) -> Dict[str, Any]:
        """Task 실행 (타입별 분기)

        Args:
            task: Task

        Returns:
            실행 결과
        """
        import time
        start_time = time.time()

        try:
            if task.task_type == TaskType.RUN_WORKFLOW:
                result = self._execute_run_workflow(task)

            elif task.task_type == TaskType.COLLECT_EVIDENCE:
                result = self._execute_collect_evidence(task)

            elif task.task_type == TaskType.COMPUTE_METRIC:
                result = self._execute_compute_metric(task)

            elif task.task_type == TaskType.VALIDATE_GOAL:
                result = self._execute_validate_goal(task)

            else:
                result = {"error": f"Unsupported task_type: {task.task_type}"}

            execution_time = time.time() - start_time

            return {
                "task_id": task.task_id,
                "status": "completed",
                "result": result,
                "time_sec": execution_time
            }

        except Exception as e:
            execution_time = time.time() - start_time

            return {
                "task_id": task.task_id,
                "status": "failed",
                "error": str(e),
                "time_sec": execution_time
            }

    def _execute_run_workflow(self, task: Task) -> Dict[str, Any]:
        """RunWorkflow Task 실행

        Args:
            task: Task (inputs에 workflow_id 포함)

        Returns:
            Workflow 결과
        """
        workflow_id = task.inputs.get("workflow_id")
        workflow_inputs = task.inputs.get("inputs", {})

        result = self.workflow_orch.run_workflow(
            workflow_id=workflow_id,
            inputs=workflow_inputs
        )

        return result

    def _execute_collect_evidence(self, task: Task) -> Dict[str, Any]:
        """CollectEvidence Task 실행

        Args:
            task: Task (inputs에 target_metrics 포함)

        Returns:
            {
                "evidence_ids": [...],
                "num_collected": N
            }
        """
        target_metrics = task.inputs.get("target_metrics", [])

        # TODO: EvidenceEngine 호출
        # evidence_bundle = self.evidence_engine.fetch_for_metrics(...)

        return {
            "evidence_ids": [],
            "num_collected": 0
        }

    def _execute_compute_metric(self, task: Task) -> Dict[str, Any]:
        """ComputeMetric Task 실행

        Args:
            task: Task (inputs에 metric_id 포함)

        Returns:
            {
                "metric_id": "...",
                "value": 123.45,
                "quality": {...}
            }
        """
        metric_id = task.inputs.get("metric_id")

        # TODO: ValueEngine 호출
        # value_records = self.value_engine.evaluate_metrics(...)

        return {
            "metric_id": metric_id,
            "value": None,
            "quality": {}
        }

    def _execute_validate_goal(self, task: Task) -> Dict[str, Any]:
        """ValidateGoal Task 실행

        Args:
            task: Task (inputs에 goal_id 포함)

        Returns:
            {
                "goal_id": "...",
                "satisfied": True/False,
                "diff_report": {...}
            }
        """
        goal_id = task.inputs.get("goal_id")

        # TODO: Verifier 호출

        return {
            "goal_id": goal_id,
            "satisfied": False,
            "diff_report": {}
        }
```

---

## 3. cmis.yaml 업데이트

### 3.1 interaction_plane.interfaces 추가

```yaml
interaction_plane:
  description: "사람/외부 시스템이 CMIS와 상호작용하는 인터페이스"
  interfaces:
    - id: "cli"
      type: "command_line"
      default_role_id: "structure_analyst"

    - id: "api"
      type: "http"
      default_role_id: "strategy_architect"

    - id: "notebook"
      type: "jupyter"
      default_role_id: "numerical_modeler"

    - id: "web_app"
      type: "web"
      default_role_id: "structure_analyst"

    # 5번째 인터페이스 (신규)
    - id: "cursor_agent"
      type: "autonomous_agent"
      default_role_id: "structure_analyst"
      capabilities:
        - "file_read_write"
        - "terminal_exec"
        - "web_search"
        - "code_execution"
        - "iterative_refinement"
      orchestration:
        mode: "autonomous"
        max_iterations: 20
        enable_replanning: true
      safety:
        allow_terminal: false  # Phase 1: 비활성화
        require_approval: false  # 자율 실행
```

---

## 4. 구현 계획

### Phase 1: 기본 Interface (1주)

**파일**:
1. `cmis_cursor/interface.py` (150줄)
   - CursorAgentInterface
   - CursorAgentConfig

2. `cmis_cursor/task_executor.py` (150줄)
   - CursorTaskExecutor
   - Task 실행 로직

**테스트**: 5개

---

### Phase 2: Orchestration 통합 (3일)

**작업**:
- OrchestrationKernel 연동
- Task → Executor 연결
- Ledger 업데이트 로직

**테스트**: 10개

---

### Phase 3: Cursor API 활용 (선택, 1주)

**작업**:
- Cursor API 호출 (파일/터미널)
- 웹 검색 연동
- 반복 실행 최적화

**테스트**: 5개

---

**총 2~3주**

---

## 5. 핵심 설계 결정

### 5.1 Cursor = Task 실행 환경

**Cursor는 엔진이 아님**
- Orchestration Kernel이 무엇을, 언제, 왜 결정
- Cursor는 어떻게 실행

**장점**:
- 명확한 역할 분리
- 테스트 가능
- 다른 Interface로 교체 가능

---

### 5.2 Autonomous 모드

**사람 개입 최소**:
- Kernel이 목표 달성까지 자율 실행
- Replanning 자동
- 검증 실패 시 자동 재시도

**안전장치**:
- max_iterations (무한 루프 방지)
- max_time_sec (시간 제한)
- max_llm_calls (비용 제한)
- Governor 제어

---

### 5.3 Evidence-first 통합

**Cursor도 Evidence-first 준수**:
- Prior 사용 시 명시적 로깅
- Quality Gate 검증
- Policy Engine 연동

---

## 6. 사용 예시

### 6.1 기본 사용

```python
from cmis_cursor import CursorAgentInterface

# Interface 생성
interface = CursorAgentInterface()

# Query 실행
result = interface.execute(
    query="한국 어학 시장 TAM/SAM 파악",
    context={"project_context_id": "PRJ-001"}
)

# 결과 출력
print(f"Goal Satisfied: {result['goal_satisfied']}")
print(f"Metrics: {result['metrics']}")
print(f"Next Steps: {result['next_steps']}")
```

---

### 6.2 고급 사용 (Role/Policy 지정)

```python
result = interface.execute(
    query="한국 어학 시장에서 기회 발굴",
    context={"project_context_id": "PRJ-001"},
    role_id="opportunity_designer",
    policy_mode="exploration_friendly"
)
```

---

## 7. Summary

### 핵심 가치

1. **명확한 역할 분리**
   - Cursor = 실행 환경
   - Kernel = 목표/검증/재계획

2. **Autonomous 실행**
   - 사람 개입 최소
   - 자율 반복/재계획

3. **Evidence-first 준수**
   - Policy Engine 연동
   - Quality Gate 검증

4. **확장 가능**
   - 다른 Agent 환경으로 교체 가능
   - Interface 추가 (6번째, 7번째...)

---

**작성**: 2025-12-13
**버전**: v1.0
**상태**: 설계 완료
**다음**: cmis_cursor/interface.py 구현


