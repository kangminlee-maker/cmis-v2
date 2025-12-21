# Orchestration Kernel 구현

**생성일**: 2025-12-21 11:28:56
**목적**: Reconcile Loop 기반 실행 관리

---

## 개요

CMIS Orchestration Kernel은 Kubernetes의 Reconcile Loop 패턴을 차용하여
Goal → Task → Verification → Replanning의 동적 실행을 관리합니다.

---

## 1. kernel.py

### 모듈 설명

```
OrchestrationKernel: Objective-oriented Reconcile Loop runtime.

Phase 1 목표:
- Query → Goal(규칙 기반) 생성
- Diff → Tasks → Execute → Verify 루프 실행
- 실행 이벤트/결정 로그를 메모리로 유지하고, (추후) run_store/ledger_store로 영속화
```

### 주요 클래스

#### `RunStoreLike`

RunStore 인터페이스(부분) - stores 단계에서 구현

**Public 메서드**:

```python
def create_run(self, run: Dict[(str, Any)]) -> None
```

```python
def append_event(self, run_id: str, event: Dict[(str, Any)]) -> None
```

```python
def append_decision(self, run_id: str, decision: Dict[(str, Any)]) -> None
```

#### `LedgerStoreLike`

LedgerStore 인터페이스(부분) - stores 단계에서 구현

**Public 메서드**:

```python
def save_snapshot(self, run_id: str, project_ledger: Dict[(str, Any)], progress_ledger: Dict[(str, Any)]) -> None
```

---

## 2. goal.py

### 모듈 설명

```
Goal and predicate models for OrchestrationKernel.

Phase 1에서는 Query → Goal 변환을 규칙 기반으로 처리합니다.
향후 LLM 기반 Goal 해석은 PlanPatchProvider 단계에서 추가합니다.
```

### 주요 클래스

#### `PredicateType`

GoalPredicate 타입

#### `ConditionType`

Predicate 조건 타입

---

## 3. task.py

### 모듈 설명

```
Orchestration task model.

Task는 OrchestrationKernel이 실행하는 최소 작업 단위입니다.
Cursor Agent Interface v2에서는 Task 실행 결과가 Ledgers/RunStore로 기록되어
재현성과 디버깅 가능성을 제공합니다.
```

### 주요 클래스

#### `TaskType`

Task 종류 (Kernel 내부 실행 단위)

#### `TaskStatus`

Task 상태

---

## 4. executor.py

### 모듈 설명

```
Task execution for OrchestrationKernel.

주의:
- Cursor IDE 내부 도구(파일/터미널/웹)는 CMIS가 직접 호출하지 않습니다.
- 여기서의 실행은 CMIS 엔진/워크플로우 호출로 제한됩니다.
```

### 주요 클래스

#### `TaskExecutor`

Task 타입별 실행기

**Public 메서드**:

```python
def execute(self, task: Task, run_context: Dict[(str, Any)]) -> Dict[(str, Any)]
```

---

## 5. verifier.py

### 모듈 설명

```
Verifier: GoalPredicate evaluation + Diff report generation.

Phase 1에서는 metric 단위 정책 게이트 결과(policy_check)를 Ledgers에 기록하고,
Verifier는 이를 기반으로 Goal 만족 여부를 판단합니다.
```

### 주요 클래스

#### `VerificationResult`

#### `Verifier`

GoalPredicate 검증기

**Public 메서드**:

```python
def verify(self, goal: GoalSpec, ledgers: Ledgers, policy_id: str) -> VerificationResult
```

---

## 6. replanner.py

### 모듈 설명

```
Replanner: Diff report → Tasks.

Phase 1 전략:
- missing_metrics / missing_values: ComputeMetric
- failed_policy_metrics: CollectEvidence + ComputeMetric

LLM 기반 PlanPatch는 Phase 2+에서 추가합니다.
```

### 주요 클래스

#### `ReplanResult`

#### `Replanner`

규칙 기반 재계획기

**Public 메서드**:

```python
def generate_tasks(self, diff_report: Dict[(str, Any)]) -> ReplanResult
```

---

## 7. ledgers.py

### 모듈 설명

```
Ledgers (Project/Progress) for OrchestrationKernel.

CMIS 철학상, 유한 컨텍스트 문제를 해결하기 위해 실행 상태는 명시적으로 기록되어야 합니다.
Phase 1에서는 run_store/ledger_store(정본)로 저장하고, Cursor UX에는 export(view)로 제공합니다.
```

### 주요 클래스

#### `ProjectLedger`

프로젝트 상태 뷰(Project Ledger).

- Substrate(Stores/Graphs)의 정본(System of Record)을 직접 저장하지 않고,
  정본을 어떻게 묶어 읽을지에 대한 프로젝트 단위 인덱스/포인터 역할을 합니다.
- Magentic-One의 "Task Ledger"(문제공간 작업기억)와 동일 계열 개념이지만,
  CMIS의 실행 단위 task/workflow step과의 혼선을 피하기 위해 Project Ledger를 정식 용어로 사용합니다.

**Public 메서드**:

```python
def to_dict(self) -> Dict[(str, Any)]
```

#### `StepRecord`

ProgressLedger step 기록

**Public 메서드**:

```python
def to_dict(self) -> Dict[(str, Any)]
```

---

## 8. governor.py

### 모듈 설명

```
Governor/Guardian: budget + stall control.

Phase 1:
- max_iterations/max_time_sec budget 적용
- stall_threshold는 PolicyEngine v2의 orchestration_profile에서 가져옵니다.
```

### 주요 클래스

#### `Budget`

#### `Governor`

실행 제어(예산/스톨/중단 조건)

**Public 메서드**:

```python
def should_stop(self, ledgers: Ledgers) -> Optional[str]
```
중단해야 하면 reason 반환, 아니면 None

```python
def check_stall(self, ledgers: Ledgers, policy_id: str) -> Optional[str]
```
stall_threshold 초과 시 reason 반환

---
