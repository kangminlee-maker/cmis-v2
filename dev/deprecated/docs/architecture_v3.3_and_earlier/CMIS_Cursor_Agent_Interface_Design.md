# CMIS Cursor Agent Interface 설계

**작성일**: 2025-12-12
**버전**: v1.1 (Self-Orchestration 추가)
**상태**: 설계 단계

---

## 📝 배경 및 목적 (원문 보존)

### 사용자 요구사항 - Part 1: Cursor Agent Interface

**Interaction Plane 확장**: CLI/Jupyter/Web/API 외에 **Cursor Agent Interface** 추가

#### 각 인터페이스의 역할

1. **CLI** (구현 완료)
   - Agent가 직접 테스트
   - 개발 과정에서 필요한 영역

2. **Jupyter Notebook** (정의만)
   - 개발자가 직접 서비스 사용/테스트
   - Agent와 함께 진행하기엔 불편

3. **Web & API** (계획)
   - 프로덕션 수준 서비스 제공

4. **Cursor Interface** (신규 제안) ⭐
   - **Agent와 함께 서비스 이용**
   - **동일 인터페이스에서 디버깅/개발 병행**
   - 현재 개발 방식과 동일한 경험

---

### 신규 사용자 온보딩 시나리오

```
1. Fork Repository
   사용자가 Cursor에서 CMIS 레포 fork

2. Cursor Agent에서 질문 시작
   "한국 성인 어학교육 시장 분석해줘"

3. 환경 설정 자동 확인
   - Cursor Agent가 CMIS 환경 확인
   - 설정 필요 시 자동 구성
   
4. CMIS 기능 활용
   - Agent가 CMIS 전체 기능 파악
   - 충분히 활용하며 문제 해결
```

---

### 핵심 고려사항

#### 1. 온보딩 워크플로우 설계
- canonical_workflows에 포함? vs 별도 setup process?
- 외부와의 첫 접점

#### 2. LLM Context Window 제약
- LLM 모델에 따라 성능 제약
- Context Window 크기 → CMIS 기능 인지 범위 달라짐
- 대응 필요

#### 3. Process Guardian 역할 (v7 참조)
- Agent 협업을 프로젝트 목적에 정렬
- 특정 문제에 과도하게 몰입 방지
- 전체 업무 프로세스 관리

**v7 Guardian (Stewart) 역할**:
- Query Memory (순환 감지)
- Goal Memory (목표 정렬)
- RAE Memory (평가 일관성)
- 검증 상태 집계, 품질 평가

---

### 사용자 요구사항 - Part 2: Self-Orchestration 및 LLM 추상화

#### 고민 1: Self-Orchestration 요소 누락 (동적 재설계)

**v7의 특징**:
- Multi-agentic model
- **사용자 + Cursor Agent = Orchestrator**
- 정해진 workflow는 있지만, 그때그때 최선의 방식으로 다양한 agent/tool 사용
- 사용자 요구 결과까지 **스스로 이끌어내는 방식**

**CMIS의 현재 상태**:
- WorkflowOrchestrator: canonical_workflows **실행기** (고정 steps)
- canonical_workflows: 정해진 순서대로 실행
- **Self-orchestration 요소가 보이지 않음** ❌

**질문**: CMIS 설계 시 이 요소를 어디에 담아두었는지?
- 없다면 **매우 중요한 요소로 추가 필요**

#### 고민 2: Non-Cursor Interface의 Orchestration

**문제**:
- Cursor IDE Interface가 **아닌** 경우 (Web App, API, Jupyter)
- Cursor Agent가 수행하는 **orchestration 역할**을 누가?
- **외부 LLM으로 대체** 필요

**설계 필요**:
- Cursor Agent용: 직접 통합
- Non-Cursor용: 외부 LLM API (GPT-4, Claude 등)
- **동일 orchestration 로직, 다른 인터페이스**
- 프로덕션 배포 가능 구조

---

### 사용자 요구사항 - Part 3: 동적 재설계의 핵심성 (CMIS 철학)

#### 핵심 1: 작업 과정의 동적 설계 = CMIS의 핵심 중 핵심

**왜 동적 재설계가 필수인가**:

이 시스템이 **수집한 Evidence, 계산 및 추정한 내용에 따라**
structure analysis, opportunity, strategy 등이 **모두 달라질 수 있기 때문**.

**예시**:
```
[시작] "한국 어학 시장 분석"

[Evidence 수집]
→ TAM: 1.5조원 발견 (예상보다 작음)
→ Top 3 점유율: 80% (예상보다 집중)

[상황 판단] ← 동적!
"시장이 작고 집중도 높음"
→ 기회 발굴 방향 변경
   - Gap Discovery ❌ (시장 포화)
   - Adjacent Market ✅ (인접 시장 탐색)

[재설계] ← 동적!
원래 계획: structure → opportunity (gap)
변경 계획: structure → adjacent_market_search → strategy (pivot)

[결과]
초기 계획과 다른 경로로 더 나은 결과
```

**핵심 원칙**:
- **결론까지 도달하는 과정에서 확인한 새로운 정보**
- **현재 상황에 대해 능동적으로 판단**
- **동적으로 다음 작업 재설계**

**Process-Oriented (고정) ❌**:
```
Step 1 → Step 2 → Step 3 → ... → 결과
(중간 결과 무관하게 정해진 순서)
```

**Objective-Oriented (동적) ✅**:
```
Goal 설정
    ↓
Step 1 실행
    ↓
[결과 평가] ← 능동적 판단!
    ├─ 충분? → 완료
    ├─ 부족? → Evidence 더 수집
    ├─ 방향 전환? → 다른 workflow
    └─ 새로운 발견? → 경로 재설계
```

---

#### 핵심 2: 목표 중심 설계 → Process 감독/Logging 더욱 중요

**프로세스에 자유도를 주는 설계**이기 때문에:

**위험**:
- 목적을 잃을 수 있음
- 특정 문제에 과도하게 몰입
- 순환 (같은 질문 반복)
- 무한 탐색

**대응**: **Process Guardian + Logging**

**Guardian의 역할 (강화)**:
1. **목적 정렬** (Goal Alignment)
   - 초기 목표 기억
   - 현재 작업 ↔ 목표 연결성 확인
   - 이탈 시 경고

2. **Process 감독** (Supervision)
   - 탐색 깊이 제한 (max_depth)
   - 순환 감지 (동일 질문 반복)
   - 품질 게이트 (최소 기준)

3. **Process Logging** (투명성)
   - 모든 결정 기록
   - 중간 평가 기록
   - 경로 변경 이유 기록
   - **완전한 Trace** (재현 가능)

**v7 Guardian (Stewart) 계승 + 강화**:
- Query Memory (순환 감지) ✅
- Goal Memory (목표 정렬) ✅
- **Decision Log (신규)** ⭐ - 모든 동적 결정 기록
- **Quality Gate (신규)** ⭐ - 중간 결과 품질 강제

---

## 0. CMIS Orchestration 구조 분석 및 보완

### 0.1 현재 상태 분석

**CMIS에 있는 것**:
```
WorkflowOrchestrator (cmis_core/workflow.py)
├─ canonical_workflows 로딩
├─ 정해진 steps 순차 실행
└─ Role → Policy 매핑

canonical_workflows (cmis.yaml)
├─ structure_analysis
├─ opportunity_discovery
├─ strategy_design
└─ reality_monitoring

→ 고정된 워크플로우, 정해진 순서
```

**CMIS에 없는 것** ❌:
```
Self-Orchestration (v7 스타일)
├─ 상황 판단 → workflow 선택
├─ 중간 결과 → 다음 단계 결정
├─ 여러 경로 중 최선 선택
└─ 동적 조합/변경

→ v7의 핵심 요소 누락!
```

---

### 0.2 보완 방안: Objective-Oriented Architecture

**핵심 철학**: **Process-Oriented ❌ → Objective-Oriented ✅**

**Process-Oriented (고정 프로세스)**:
```
정해진 Steps:
Step 1 (Evidence) → Step 2 (Pattern) → Step 3 (Metric) → 결과

문제:
- 중간 결과 무시
- Evidence 부족해도 계속 진행
- 새로운 발견 반영 불가
- 고정된 경로만
```

**Objective-Oriented (목표 중심, 동적)**:
```
Goal: "시장 규모 파악"
    ↓
Step 1: Evidence 수집
    ↓
[평가] Evidence Quality?
    ├─ 충분 (>70%) → Step 2: 계산
    ├─ 부족 (30-70%) → Evidence 더 수집 (재시도)
    └─ 매우 부족 (<30%) → Prior Estimation 또는 Proxy
    ↓
Step 2: Metric 계산
    ↓
[평가] 계산 가능?
    ├─ 가능 → 완료
    └─ 불가 → Workflow 변경
    ↓
[새로운 발견] "시장이 예상보다 작고 포화"
    ↓
[재설계] ← 동적!
    원래: Gap Discovery
    변경: Adjacent Market 탐색
    ↓
새로운 경로 실행
```

**AdaptiveOrchestrator의 역할**:

```
[사용자 질문/목표]
     ↓
┌────────────────────────────────────────────────────┐
│  AdaptiveOrchestrator (Objective-Oriented)        │
│  = v7 Self-Orchestration + 목표 중심 설계          │
├────────────────────────────────────────────────────┤
│                                                    │
│  1. Goal 설정 (명시적 목표 추출)                    │
│     - "시장 규모 파악" ← 최종 목표                  │
│     - "Evidence Quality > 70%" ← 품질 목표         │
│                                                    │
│  2. 초기 Plan (가설적)                             │
│     - structure_analysis 선택 (예상)               │
│     - 예상 경로: Evidence → Pattern → Metric       │
│                                                    │
│  3. 실행 + 평가 루프 (동적!)                        │
│     Execute Step                                   │
│         ↓                                          │
│     Evaluate Result                                │
│         ├─ Goal 달성? → 완료                       │
│         ├─ 진행 가능? → 다음 Step                  │
│         ├─ 부족? → 재시도/보완                     │
│         ├─ 막힘? → Workflow 변경                   │
│         └─ 새 발견? → Plan 재설계 ← 핵심!          │
│                                                    │
│  4. Process Guardian (감독)                        │
│     - Goal Alignment 확인 (목적 정렬)              │
│     - Depth 제한 (무한 탐색 방지)                  │
│     - 순환 감지 (같은 작업 반복)                   │
│     - Decision Log (모든 결정 기록)                │
│                                                    │
└────────────────────────────────────────────────────┘
     ↓
WorkflowOrchestrator (실행기)
 └─ canonical_workflows steps 실행
     ↓
[CMIS Engines]
```

**역할 분리**:
- **AdaptiveOrchestrator**: What/Which/Why (무엇을, 왜, 어떤 순서로)
- **WorkflowOrchestrator**: How (어떻게 실행)
- **ProcessGuardian**: Monitor/Control (감독/통제)

---

### 0.3 LLM Orchestration 추상화

**문제**: Cursor가 아닌 인터페이스(Web, API, Jupyter)에서 orchestration을?

**해결**: **LLM Orchestration Layer** 추상화

```python
class OrchestrationProvider(ABC):
    """Orchestration 제공자 (추상 클래스)"""
    
    @abstractmethod
    def decide_workflow(self, query: str, context: Dict) -> str:
        """Query → Workflow 결정"""
        pass
    
    @abstractmethod
    def decide_next_step(self, current_result: Dict) -> str:
        """중간 결과 → 다음 단계 결정"""
        pass

class CursorOrchestrationProvider(OrchestrationProvider):
    """Cursor Agent 사용"""
    
    def decide_workflow(self, query, context):
        # Cursor Agent가 직접 판단 (이미 컨텍스트에 있음)
        return "structure_analysis"  # Agent 응답 파싱

class ExternalLLMOrchestrationProvider(OrchestrationProvider):
    """외부 LLM API 사용 (Web, API, Jupyter)"""
    
    def __init__(self, llm_client):
        self.llm = llm_client  # OpenAI, Anthropic, etc.
    
    def decide_workflow(self, query, context):
        # 외부 LLM 호출
        prompt = f"""
        CMIS 질문: {query}
        사용 가능 워크플로우:
        - structure_analysis: 시장 구조/규모 분석
        - opportunity_discovery: 기회 발굴
        - strategy_design: 전략 수립
        
        어떤 워크플로우를 사용해야 하나요?
        """
        
        response = self.llm.complete(prompt)
        return self._parse_workflow_id(response)

class RuleBasedOrchestrationProvider(OrchestrationProvider):
    """규칙 기반 (Fallback)"""
    
    def decide_workflow(self, query, context):
        # 간단한 규칙
        if "규모" in query or "시장" in query:
            return "structure_analysis"
        elif "기회" in query:
            return "opportunity_discovery"
        else:
            return "structure_analysis"  # 기본값
```

**AdaptiveOrchestrator에서 사용**:

```python
class AdaptiveOrchestrator:
    def __init__(
        self,
        orchestration_provider: OrchestrationProvider
    ):
        self.provider = orchestration_provider
        self.workflow_orchestrator = WorkflowOrchestrator()
    
    def process_query(self, query: str) -> Dict:
        # 1. Workflow 결정 (Provider에 위임)
        workflow_id = self.provider.decide_workflow(query, {})
        
        # 2. 실행
        result = self.workflow_orchestrator.run_workflow(workflow_id, {...})
        
        # 3. 중간 결과 평가
        if result["quality"] < 0.5:
            # 다음 단계 결정 (Provider에 위임)
            next_action = self.provider.decide_next_step(result)
            
            if next_action == "collect_more_evidence":
                # 추가 Evidence 수집
                pass
        
        return result
```

**인터페이스별 Provider**:

| Interface | Provider | LLM |
|-----------|----------|-----|
| Cursor Agent | CursorOrchestrationProvider | Cursor 내장 |
| Web App | ExternalLLMOrchestrationProvider | GPT-4/Claude API |
| API | ExternalLLMOrchestrationProvider | 클라이언트 지정 |
| Jupyter | CursorOrchestrationProvider (선택) 또는 RuleBasedOrchestrationProvider | 선택적 |
| CLI | RuleBasedOrchestrationProvider | 없음 (규칙만) |

---

## 1. Cursor Agent Interface 개요

### 1.1 정의

> **Cursor Agent Interface**는
> Cursor IDE 내 Agent와의 자연어 대화를 통해
> CMIS의 모든 기능을 사용하고, 동시에 시스템 개선/디버깅/확장을
> 같은 컨텍스트에서 수행할 수 있는 통합 인터페이스입니다.
> 
> **v7의 Self-Orchestration 철학을 계승**하며,
> **AdaptiveOrchestrator**를 통해 동적 workflow 선택/조합을 지원합니다.

### 1.2 핵심 특징

**1. 대화형 분석** (Conversational Analysis)
```
User: "한국 성인 어학교육 시장 규모를 알려줘"
Agent: [CMIS 분석 실행]
      → structure_analysis 워크플로우
      → Metric 계산
      → 결과 제공

User: "이 결과가 어떻게 계산된 거야?"
Agent: [Lineage 추적]
      → Evidence 출처
      → 계산 과정
      → 설명
```

**2. 컨텍스트 유지** (Context Persistence)
```
분석 → 질문 → 추가 분석 → 디버깅 → 개선
(모두 하나의 Cursor 세션 내에서)
```

**3. 자가 개선** (Self-Improvement)
```
분석 중 오류 발견
→ Agent가 즉시 코드 수정
→ 테스트
→ 재분석
(사용자 개입 최소)
```

**4. 학습하는 인터페이스** (Learning Interface)
```
사용자의 질문 패턴 학습
→ 자주 묻는 질문 예측
→ 자동 제안
```

---

## 2. Interaction Plane 업데이트

### 2.1 cmis.yaml 확장

```yaml
interaction_plane:
  description: "사람/외부 시스템이 CMIS와 상호작용하는 모든 인터페이스"
  
  interfaces:
    - id: "cli"
      type: "command_line"
      description: "분석가/엔지니어용 CLI"
      status: "production_ready"
      implementation: "cmis_cli/"
      use_case: "Agent 자동 테스트, 배치 처리, 스크립팅"
    
    - id: "cursor_agent"  # 신규
      type: "conversational_ide"
      description: "Cursor Agent 기반 대화형 인터페이스"
      status: "design"
      implementation: "cmis_cursor/"
      use_case: "대화형 분석, 디버깅, 개발, 학습"
      features:
        - "자연어 질문 → CMIS 워크플로우 매핑"
        - "컨텍스트 유지 (세션 메모리)"
        - "자가 개선 (오류 발견 시 자동 수정)"
        - "온보딩 자동화 (환경 설정)"
        - "Process Guardian (목표 정렬, 순환 방지)"
    
    - id: "notebook"
      type: "jupyter"
      description: "Python Notebook 기반 실험/모델링 인터페이스"
      status: "planned"
      use_case: "개발자 직접 테스트, 프로토타이핑"
    
    - id: "web_app"
      type: "web"
      description: "리포트/대시보드/전략 보드 UI"
      status: "planned"
      use_case: "프로덕션 서비스, 비개발자 사용자"
    
    - id: "api"
      type: "http"
      description: "외부 시스템 연동용 API (REST/GraphQL 등)"
      status: "planned"
      use_case: "시스템 간 연동, 자동화"
  
  default_role_bindings:
    - interface_id: "cli"
      default_role_id: "numerical_modeler"
    
    - interface_id: "cursor_agent"  # 신규
      default_role_id: "structure_analyst"
      notes: "초기 진입점, 모든 Role 전환 가능"
    
    - interface_id: "notebook"
      default_role_id: "structure_analyst"
    
    - interface_id: "web_app"
      default_role_id: "structure_analyst"
    
    - interface_id: "api"
      default_role_id: "strategy_architect"
```

---

## 3. AdaptiveOrchestrator 설계 (Self-Orchestration)

### 3.1 v7 vs CMIS Orchestration 비교

**v7 (Multi-Agentic)**:
```
사용자 질문
    ↓
[사용자 + Cursor Agent] ← Orchestrator
    ├─ 상황 판단
    ├─ Agent 선택 (Observer/Explorer/Quantifier/Validator/Guardian)
    ├─ Tool 선택 (RAG, KG, Estimator)
    ├─ 중간 결과 평가
    └─ 다음 Agent/Tool 동적 결정
    ↓
결과
```

**CMIS 현재 (Fixed Workflow)**:
```
사용자 질문
    ↓
WorkflowOrchestrator
    ├─ canonical_workflows 로딩
    └─ 정해진 steps 순차 실행
        ├─ Step 1: world_engine.snapshot()
        ├─ Step 2: pattern_engine.match_patterns()
        └─ Step 3: value_engine.evaluate_metrics()
    ↓
결과
```

**문제**: 동적 판단 없음, 고정된 경로만

---

### 3.2 AdaptiveOrchestrator 아키텍처

**v7의 Self-Orchestration을 CMIS에 도입**:

```
사용자 질문
    ↓
┌──────────────────────────────────────────────────────────────┐
│        AdaptiveOrchestrator (Self-Orchestration)             │
│  (v7 Orchestrator 역할 계승)                                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Intent Analysis (의도 파악)                               │
│     - 질문 유형: market_size? opportunity? strategy?         │
│     - 명확도: clear? ambiguous? multi-part?                  │
│     - 컨텍스트: Greenfield? Brownfield?                       │
│                                                              │
│  2. Situation Assessment (상황 판단)                          │
│     - Evidence 가용성: 충분? 부족? 없음?                      │
│     - Prior Knowledge: 유사 분석 있음? 없음?                  │
│     - Complexity: 단순? 중간? 복잡?                           │
│                                                              │
│  3. Workflow Selection (워크플로우 선택)                       │
│     Decision Tree:                                           │
│     ├─ Single Workflow (간단)                                │
│     ├─ Multi Workflow (복잡)                                 │
│     ├─ Custom Path (특수)                                    │
│     └─ Iterative (점진적)                                    │
│                                                              │
│  4. Mid-Flight Adjustment (중간 조정)                         │
│     - 중간 결과 품질 평가                                     │
│     - 필요 시 경로 변경                                       │
│     - Evidence 추가 수집                                      │
│     - Fallback 전략                                          │
│                                                              │
│  5. LLM Provider (추상화)                                    │
│     ├─ Cursor Agent (IDE 내장)                              │
│     ├─ External LLM (GPT-4, Claude API)                     │
│     └─ Rule-Based (Fallback)                                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│        WorkflowOrchestrator (기존)                            │
│  (canonical_workflows 실행)                                   │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│        CMIS Engines (9개)                                    │
└──────────────────────────────────────────────────────────────┘
```

---

### 3.3 AdaptiveOrchestrator 구현

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum

class WorkflowDecision(Enum):
    """Workflow 결정 타입"""
    SINGLE = "single"           # 하나의 workflow
    MULTI = "multi"             # 여러 workflow 순차
    CUSTOM = "custom"           # Custom path
    ITERATIVE = "iterative"     # 점진적 (중간 평가 후 계속)

class OrchestrationProvider(ABC):
    """Orchestration 제공자 추상 클래스
    
    Cursor Agent, 외부 LLM, 규칙 기반 중 선택.
    
    핵심: Objective-Oriented 설계 지원
    - 목표 중심 판단
    - 동적 재설계
    - Evidence 기반 경로 변경
    """
    
    @abstractmethod
    def decide_workflow(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query → 초기 Workflow 결정
        
        Returns:
            {
                "decision_type": "single" | "multi" | "custom" | "iterative",
                "workflow_ids": ["structure_analysis"],
                "reasoning": "시장 규모 질문이므로...",
                "expected_path": ["evidence", "pattern", "metric"]
            }
        """
        pass
    
    @abstractmethod
    def decide_replanning(
        self,
        query: str,
        current_result: Dict,
        new_insights: List[str]
    ) -> Dict[str, Any]:
        """중간 결과 + 새 발견 → 재설계 결정
        
        CMIS 핵심: 동적 재설계
        
        Args:
            query: 원래 질문
            current_result: 현재까지 결과
            new_insights: 새로운 발견 ["시장 집중도 높음", ...]
        
        Returns:
            {
                "replan": True/False,
                "new_workflow_id": "adjacent_market_search",
                "reasoning": "시장 포화 → 인접 시장 탐색으로 전환",
                "plan_changes": {
                    "before": ["structure", "opportunity_gap"],
                    "after": ["structure", "adjacent_market", "strategy_pivot"]
                }
            }
        """
        pass
    
    @abstractmethod
    def decide_next_step(
        self,
        query: str,
        current_result: Dict,
        workflow_trace: List[Dict]
    ) -> Dict[str, Any]:
        """중간 결과 → 다음 단계 결정
        
        Returns:
            {
                "action": "continue" | "collect_evidence" | "change_workflow" | "complete",
                "next_workflow_id": "...",
                "reasoning": "..."
            }
        """
        pass
    
    @abstractmethod
    def assess_situation(
        self,
        query: str,
        context: Dict
    ) -> Dict[str, Any]:
        """상황 평가
        
        Returns:
            {
                "clarity": "clear" | "ambiguous",
                "evidence_availability": "sufficient" | "partial" | "none",
                "complexity": "simple" | "medium" | "complex"
            }
        """
        pass

class AdaptiveOrchestrator:
    """Adaptive Orchestrator (Objective-Oriented Self-Orchestration)
    
    CMIS의 핵심 중 핵심: 동적 재설계 엔진.
    
    핵심 철학:
    1. **Objective-Oriented** (목표 중심)
       - Process-Oriented ❌: 정해진 순서대로
       - Objective-Oriented ✅: 목표 달성까지 최선의 경로
    
    2. **Evidence-Driven Re-planning** (증거 기반 재계획)
       - 수집한 Evidence → 상황 재평가
       - 계산/추정 결과 → 다음 단계 재설계
       - 새로운 발견 → 경로 변경
    
    3. **Dynamic Path Selection** (동적 경로 선택)
       - Structure/Opportunity/Strategy 모두 중간 결과에 따라 달라짐
       - 고정된 프로세스 없음
       - 목표 달성이 유일한 제약
    
    4. **Process Supervision** (프로세스 감독)
       - 자유도 높음 → Guardian 더욱 중요
       - 목적 정렬 확인
       - 완전한 Decision Logging
    
    v7 Self-Orchestration + Objective-Oriented 설계
    """
    
    def __init__(
        self,
        orchestration_provider: OrchestrationProvider,
        workflow_orchestrator: WorkflowOrchestrator,
        guardian: Optional[CursorProcessGuardian] = None
    ):
        """
        Args:
            orchestration_provider: LLM 기반 또는 규칙 기반
            workflow_orchestrator: canonical_workflows 실행기
            guardian: Process Guardian (필수 - 자유도 높은 설계에서 감독)
        """
        self.provider = orchestration_provider
        self.workflow_orch = workflow_orchestrator
        self.guardian = guardian or CursorProcessGuardian()
        
        # Goal & Plan
        self.goal: Optional[str] = None  # 명시적 목표
        self.initial_plan: Optional[Dict] = None  # 초기 계획
        self.current_plan: Optional[Dict] = None  # 현재 계획 (동적 변경)
        
        # Execution Trace (완전한 Logging)
        self.execution_trace: List[Dict] = []  # 실행 이력
        self.decision_log: List[Dict] = []  # 결정 이력 (재설계 포함)
    
    def process_query(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Query 처리 (Objective-Oriented Self-Orchestration)
        
        CMIS 핵심: 동적 재설계 엔진
        - 목표 중심 실행
        - 중간 결과 기반 재계획
        - Evidence Quality → 다음 단계 결정
        - 완전한 Decision Logging
        
        Args:
            query: 사용자 질문
            context: 추가 컨텍스트 (project_context_id 등)
        
        Returns:
            {
                "answer": "...",
                "results": [...],
                "execution_trace": [...],  # 실행 이력
                "decision_log": [...],     # 결정 이력 (재설계 포함)
                "quality": "A"
            }
        """
        context = context or {}
        
        # 0. Guardian - 순환 감지
        loop_check = self.guardian.check_query_loop(query)
        if loop_check["is_loop"]:
            return {
                "answer": loop_check["suggestion"],
                "type": "loop_detected",
                "previous_results": loop_check["previous_results"]
            }
        
        # 1. Goal 추출 (명시적 목표 설정)
        self.goal = self._extract_goal(query)
        self.guardian.push_goal(self.goal)
        
        self._log_decision(
            "goal_setting",
            {"goal": self.goal, "query": query},
            "사용자 질문에서 목표 추출"
        )
        
        # 2. 상황 평가 (초기)
        situation = self.provider.assess_situation(query, context)
        
        self._log_decision(
            "situation_assessment",
            situation,
            f"명확도: {situation['clarity']}, 복잡도: {situation['complexity']}"
        )
        
        # 3. 초기 Plan 수립
        initial_decision = self.provider.decide_workflow(query, context)
        self.initial_plan = initial_decision
        self.current_plan = initial_decision.copy()
        
        self._log_decision(
            "initial_planning",
            initial_decision,
            f"초기 계획: {initial_decision['workflow_ids']}"
        )
        
        # 4. 실행 + 동적 재설계 루프
        results = []
        max_replanning = 3  # 최대 재계획 횟수
        replanning_count = 0
        
        if self.current_plan["decision_type"] == "single":
            # Single Workflow (동적 평가 포함)
            result = self._execute_with_evaluation(
                self.current_plan["workflow_ids"][0],
                query,
                context
            )
            results.append(result)
            
            # 중간 평가 → 재설계 필요?
            need_replanning = self._evaluate_and_replan(result, query, context)
            
            while need_replanning and replanning_count < max_replanning:
                self._log_decision(
                    "replanning",
                    {
                        "trigger": "insufficient_result",
                        "new_plan": self.current_plan
                    },
                    f"재계획 {replanning_count+1}회: {self.current_plan['workflow_ids']}"
                )
                
                # 재설계된 경로 실행
                result = self._execute_with_evaluation(
                    self.current_plan["workflow_ids"][0],
                    query,
                    context
                )
                results.append(result)
                
                replanning_count += 1
                need_replanning = self._evaluate_and_replan(result, query, context)
        
        elif decision["decision_type"] == "multi":
            # Multi Workflow (순차)
            for workflow_id in decision["workflow_ids"]:
                result = self._execute_single(workflow_id, query, context)
                results.append(result)
                
                # 중간 평가
                if not self._is_result_sufficient(result):
                    # 다음 단계 결정
                    next_decision = self.provider.decide_next_step(
                        query, result, self.execution_trace
                    )
                    
                    if next_decision["action"] == "change_workflow":
                        # 경로 변경
                        workflow_id = next_decision["next_workflow_id"]
                        result = self._execute_single(workflow_id, query, context)
                        results.append(result)
        
        elif decision["decision_type"] == "iterative":
            # Iterative (점진적)
            result = self._execute_iterative(decision, query, context)
            results.append(result)
        
        # 5. Guardian - 최종 품질 확인
        quality_check = self.guardian.check_analysis_quality(results[-1])
        
        self._log_decision(
            "final_quality_check",
            quality_check,
            f"품질: {quality_check['quality_level']}"
        )
        
        # 6. Guardian - Goal 완료
        goal_check = self.guardian.check_goal_alignment("complete")
        self.guardian.pop_goal()
        
        # 7. 응답 생성
        return {
            "answer": self._generate_answer(results, query),
            "goal": self.goal,
            "initial_plan": self.initial_plan,
            "final_plan": self.current_plan,
            "replanned": replanning_count > 0,
            "replanning_count": replanning_count,
            "results": results,
            "execution_trace": self.execution_trace,
            "decision_log": self.decision_log,  # 완전한 결정 이력
            "quality": quality_check["quality_level"],
            "issues": quality_check.get("issues", [])
        }
    
    def _extract_goal(self, query: str) -> str:
        """Query에서 명시적 목표 추출
        
        Args:
            query: "한국 어학 시장 규모 알려줘"
        
        Returns:
            "시장 규모 파악"
        """
        # 간단 버전: 키워드 기반
        if "규모" in query or "크기" in query:
            return "시장 규모 파악"
        elif "기회" in query:
            return "기회 발굴"
        elif "전략" in query:
            return "전략 수립"
        else:
            return "시장 이해"
    
    def _execute_with_evaluation(
        self,
        workflow_id: str,
        query: str,
        context: Dict
    ) -> Dict:
        """Workflow 실행 + 중간 평가
        
        실행 후 즉시 평가하여 다음 단계 판단 재료로 사용.
        """
        # 실행
        result = self._execute_single(workflow_id, query, context)
        
        # 즉시 평가
        evaluation = self._evaluate_intermediate_result(result)
        
        self._log_decision(
            "intermediate_evaluation",
            evaluation,
            f"Evidence Quality: {evaluation['evidence_quality']:.1%}, "
            f"Completeness: {evaluation['completeness']}"
        )
        
        # 결과에 평가 첨부
        result["evaluation"] = evaluation
        
        return result
    
    def _evaluate_intermediate_result(self, result: Dict) -> Dict:
        """중간 결과 평가
        
        다음 단계 재설계 판단 재료.
        
        Returns:
            {
                "evidence_quality": 0.75,
                "completeness": "partial",
                "gaps": ["MET-SAM 부족"],
                "new_insights": ["시장 집중도 높음"]
            }
        """
        quality = result.get("quality", {})
        metrics = result.get("metrics", [])
        
        # Evidence Quality
        evidence_quality = quality.get("literal_ratio", 0)
        
        # Completeness
        if len(metrics) >= 5:
            completeness = "full"
        elif len(metrics) >= 3:
            completeness = "partial"
        else:
            completeness = "insufficient"
        
        # Gaps (부족한 Metric)
        gaps = [
            m["metric_id"] for m in metrics
            if m.get("quality", {}).get("literal_ratio", 0) < 0.3
        ]
        
        # New Insights (새로운 발견)
        new_insights = self._detect_insights(result)
        
        return {
            "evidence_quality": evidence_quality,
            "completeness": completeness,
            "gaps": gaps,
            "new_insights": new_insights
        }
    
    def _detect_insights(self, result: Dict) -> List[str]:
        """새로운 발견 감지
        
        중간 결과에서 예상과 다른 발견 → 재설계 트리거.
        
        Returns:
            ["시장 규모 예상보다 작음", "집중도 매우 높음", ...]
        """
        insights = []
        
        # Metric 값 기반 발견
        metrics = result.get("metrics", [])
        
        for metric in metrics:
            metric_id = metric.get("metric_id")
            value = metric.get("point_estimate")
            
            # 예시: HHI 높으면 집중도 높음
            if metric_id == "MET-HHI_revenue" and value and value > 2500:
                insights.append("시장 집중도 매우 높음 (HHI>2500)")
            
            # 예시: CR3 높으면 상위 집중
            if metric_id == "MET-Top3_revenue_share" and value and value > 0.7:
                insights.append("상위 3사 점유율 70% 초과 (과점 구조)")
        
        return insights
    
    def _evaluate_and_replan(
        self,
        result: Dict,
        query: str,
        context: Dict
    ) -> bool:
        """중간 결과 평가 → 재설계 필요 여부
        
        CMIS 핵심: 동적 재설계 판단
        
        Args:
            result: 중간 실행 결과
            query: 원래 질문
            context: 컨텍스트
        
        Returns:
            True if 재설계 필요
        """
        evaluation = result.get("evaluation", {})
        
        # 1. 충분하면 완료
        if (evaluation["evidence_quality"] > 0.7 and
            evaluation["completeness"] == "full"):
            return False
        
        # 2. 새로운 발견 → 재설계
        new_insights = evaluation.get("new_insights", [])
        
        if new_insights:
            # LLM에게 재설계 요청
            replan_decision = self.provider.decide_replanning(
                query=query,
                current_result=result,
                new_insights=new_insights
            )
            
            if replan_decision.get("replan"):
                # 계획 변경
                self.current_plan = {
                    "decision_type": "single",
                    "workflow_ids": [replan_decision["new_workflow_id"]],
                    "reasoning": replan_decision["reasoning"]
                }
                return True
        
        # 3. Evidence 부족 → 재시도 or Fallback
        if evaluation["evidence_quality"] < 0.3:
            self.current_plan["retry_with_more_evidence"] = True
            return True
        
        return False
    
    def _log_decision(
        self,
        decision_type: str,
        decision_data: Any,
        summary: str
    ):
        """결정 로깅 (완전한 투명성)
        
        모든 동적 결정을 기록하여:
        - 재현 가능
        - 디버깅 가능
        - 감사 가능
        
        Args:
            decision_type: "goal_setting" | "initial_planning" | "replanning" | ...
            decision_data: 결정 데이터
            summary: 요약
        """
        self.decision_log.append({
            "timestamp": datetime.now().isoformat(),
            "decision_type": decision_type,
            "data": decision_data,
            "summary": summary,
            "goal": self.goal,
            "plan": self.current_plan
        })
    
    def _execute_single(
        self,
        workflow_id: str,
        query: str,
        context: Dict
    ) -> Dict:
        """Single Workflow 실행"""
        
        # WorkflowOrchestrator에 위임
        result = self.workflow_orch.run_workflow(
            workflow_id=workflow_id,
            inputs={
                "query": query,
                **context
            }
        )
        
        self.execution_trace.append({
            "step": "execution",
            "workflow_id": workflow_id,
            "result_summary": self._summarize_result(result)
        })
        
        return result
    
    def _is_result_sufficient(self, result: Dict) -> bool:
        """결과 충분성 판단"""
        
        # Evidence 품질
        quality = result.get("quality", {})
        literal_ratio = quality.get("literal_ratio", 0)
        
        if literal_ratio < 0.5:
            return False
        
        # Metric 개수
        metrics = result.get("metrics", [])
        if len(metrics) < 3:
            return False
        
        return True
    
    def _execute_iterative(
        self,
        decision: Dict,
        query: str,
        context: Dict
    ) -> Dict:
        """Iterative 실행 (점진적)
        
        중간 결과 평가 → 다음 단계 결정 → 계속
        """
        workflow_id = decision["workflow_ids"][0]
        max_iterations = 3
        
        for i in range(max_iterations):
            result = self._execute_single(workflow_id, query, context)
            
            # 충분한가?
            if self._is_result_sufficient(result):
                return result
            
            # 다음 단계 결정
            next_decision = self.provider.decide_next_step(
                query, result, self.execution_trace
            )
            
            if next_decision["action"] == "complete":
                return result
            
            elif next_decision["action"] == "collect_evidence":
                # Evidence 추가 수집
                self._collect_more_evidence(result)
                # 재실행
                continue
            
            elif next_decision["action"] == "change_workflow":
                workflow_id = next_decision["next_workflow_id"]
                continue
        
        return result
    
    def _generate_answer(
        self,
        results: List[Dict],
        query: str
    ) -> str:
        """결과 → 자연어 답변
        
        LLM Provider에 위임 (선택) 또는 템플릿 기반
        """
        # 간단 버전: 템플릿
        if len(results) == 1:
            result = results[0]
            metrics = result.get("metrics", [])
            
            answer_parts = [f"질문: {query}\n"]
            answer_parts.append("분석 결과:\n")
            
            for metric in metrics[:5]:  # Top 5
                answer_parts.append(
                    f"- {metric.get('metric_id')}: {metric.get('point_estimate')}"
                )
            
            return "\n".join(answer_parts)
        
        # 복잡한 경우: LLM 사용
        return "Multiple workflows executed. See results."
```

---

### 3.4 LLM Provider 구현

#### 3.4.1 CursorOrchestrationProvider

```python
class CursorOrchestrationProvider(OrchestrationProvider):
    """Cursor Agent 기반 Orchestration
    
    Cursor IDE 내에서 사용.
    Agent가 이미 전체 컨텍스트를 가지고 있음.
    """
    
    def decide_workflow(self, query: str, context: Dict) -> Dict:
        """Cursor Agent가 판단
        
        Agent가 자연스럽게 workflow를 선택하도록
        .cursorrules에 가이드 제공.
        """
        # Cursor Agent는 자동으로 판단
        # 여기서는 Agent 응답 파싱만
        
        # 간단한 규칙 (Agent가 없을 때 fallback)
        if "규모" in query or "시장" in query:
            return {
                "decision_type": "single",
                "workflow_ids": ["structure_analysis"],
                "reasoning": "시장 규모/구조 질문"
            }
        elif "기회" in query:
            return {
                "decision_type": "single",
                "workflow_ids": ["opportunity_discovery"],
                "reasoning": "기회 발굴 질문"
            }
        else:
            # Agent에게 물어봄 (Cursor 컨텍스트에서)
            return {
                "decision_type": "single",
                "workflow_ids": ["structure_analysis"],
                "reasoning": "기본 workflow"
            }
    
    def assess_situation(self, query: str, context: Dict) -> Dict:
        """상황 평가 (Cursor Agent 활용)"""
        
        # Cursor Agent는 이미 파악하고 있음
        # 명시적 확인만
        
        clarity = "clear" if len(query.split()) < 10 else "ambiguous"
        
        return {
            "clarity": clarity,
            "evidence_availability": "unknown",  # 실행 전 모름
            "complexity": "medium"
        }
    
    def decide_next_step(
        self,
        query: str,
        current_result: Dict,
        workflow_trace: List
    ) -> Dict:
        """다음 단계 결정 (Cursor Agent)"""
        
        # 결과 품질 확인
        quality = current_result.get("quality", {})
        
        if quality.get("literal_ratio", 0) < 0.5:
            return {
                "action": "collect_evidence",
                "reasoning": "Evidence 부족"
            }
        
        return {
            "action": "complete",
            "reasoning": "분석 완료"
        }
```

#### 3.4.2 ExternalLLMOrchestrationProvider

```python
class ExternalLLMOrchestrationProvider(OrchestrationProvider):
    """외부 LLM API 기반 Orchestration
    
    Web App, HTTP API, Jupyter에서 사용.
    Cursor Agent 없이도 동일한 orchestration 가능.
    """
    
    def __init__(self, llm_client, model: str = "gpt-4"):
        """
        Args:
            llm_client: OpenAI, Anthropic 등 LLM 클라이언트
            model: "gpt-4" | "claude-3-opus" | ...
        """
        self.llm = llm_client
        self.model = model
        
        # CMIS 지식 (요약)
        self.cmis_knowledge = self._load_cmis_summary()
    
    def decide_workflow(self, query: str, context: Dict) -> Dict:
        """LLM에게 workflow 결정 요청"""
        
        prompt = f"""
        당신은 CMIS (Contextual Market Intelligence System) Orchestrator입니다.
        
        사용자 질문: "{query}"
        
        사용 가능한 canonical_workflows:
        1. structure_analysis
           - 시장 구조, 규모, 경쟁 분석
           - Output: Market Reality Report
        
        2. opportunity_discovery
           - 기회 발굴, Gap 탐지
           - Output: Opportunity List
        
        3. strategy_design
           - 전략 생성, 평가
           - Output: Strategy Portfolio
        
        4. reality_monitoring
           - 실적 모니터링, 학습
           - Output: Learning Report
        
        질문을 분석하고, 어떤 workflow(들)을 사용해야 하는지 결정하세요.
        
        응답 형식 (JSON):
        {{
            "decision_type": "single" | "multi" | "custom",
            "workflow_ids": ["structure_analysis"],
            "reasoning": "..."
        }}
        """
        
        response = self.llm.complete(
            prompt=prompt,
            model=self.model,
            temperature=0.3  # 낮은 온도 (일관성)
        )
        
        # JSON 파싱
        import json
        decision = json.loads(response)
        
        return decision
    
    def assess_situation(self, query: str, context: Dict) -> Dict:
        """LLM에게 상황 평가 요청"""
        
        prompt = f"""
        질문: "{query}"
        
        다음 항목을 평가하세요:
        1. clarity: 질문이 명확한가? (clear/ambiguous)
        2. complexity: 질문의 복잡도? (simple/medium/complex)
        
        JSON 형식:
        {{
            "clarity": "clear",
            "complexity": "medium"
        }}
        """
        
        response = self.llm.complete(prompt, model=self.model, temperature=0.3)
        return json.loads(response)
    
    def decide_next_step(
        self,
        query: str,
        current_result: Dict,
        workflow_trace: List
    ) -> Dict:
        """LLM에게 다음 단계 결정 요청"""
        
        prompt = f"""
        원래 질문: "{query}"
        
        현재까지 실행:
        {json.dumps(workflow_trace, indent=2)}
        
        현재 결과 품질:
        - Evidence Quality: {current_result.get("quality", {}).get("literal_ratio", 0):.1%}
        - Metrics: {len(current_result.get("metrics", []))}개
        
        다음 단계를 결정하세요:
        - continue: 충분함, 완료
        - collect_evidence: Evidence 더 수집
        - change_workflow: 다른 workflow로 전환
        
        JSON:
        {{
            "action": "continue",
            "reasoning": "..."
        }}
        """
        
        response = self.llm.complete(prompt, model=self.model, temperature=0.3)
        return json.loads(response)
    
    def _load_cmis_summary(self) -> str:
        """CMIS 요약 지식 로드
        
        외부 LLM은 CMIS 내부를 모르므로,
        핵심 정보를 요약해서 제공.
        """
        return """
        CMIS는 4단계 루프 (Understand → Discover → Decide → Learn) 기반
        Market Intelligence System.
        
        9개 엔진:
        - World Engine: 시장 구조 (R-Graph)
        - Pattern Engine: 비즈니스 패턴
        - Value Engine: Metric 계산
        - BeliefEngine: Prior/Belief 관리
        - Strategy Engine: 전략 생성
        - Learning Engine: 학습
        - Evidence Engine: 데이터 수집
        - Policy Engine: 품질 관리
        - Workflow CLI: 명령줄
        
        canonical_workflows:
        - structure_analysis: 시장 구조/규모 분석
        - opportunity_discovery: 기회 발굴
        - strategy_design: 전략 수립
        - reality_monitoring: 실적 모니터링
        """
```

#### 3.4.3 RuleBasedOrchestrationProvider

```python
class RuleBasedOrchestrationProvider(OrchestrationProvider):
    """규칙 기반 Orchestration (Fallback)
    
    LLM 없이도 기본 동작 가능.
    간단한 규칙으로 workflow 선택.
    """
    
    def __init__(self):
        # 키워드 → workflow 매핑
        self.keyword_map = {
            "규모": "structure_analysis",
            "시장": "structure_analysis",
            "구조": "structure_analysis",
            "경쟁": "structure_analysis",
            "기회": "opportunity_discovery",
            "갭": "opportunity_discovery",
            "발굴": "opportunity_discovery",
            "전략": "strategy_design",
            "포트폴리오": "strategy_design",
            "ROI": "strategy_design",
            "실적": "reality_monitoring",
            "학습": "reality_monitoring"
        }
    
    def decide_workflow(self, query: str, context: Dict) -> Dict:
        """키워드 기반 workflow 선택"""
        
        # 키워드 매칭
        for keyword, workflow_id in self.keyword_map.items():
            if keyword in query:
                return {
                    "decision_type": "single",
                    "workflow_ids": [workflow_id],
                    "reasoning": f"키워드 '{keyword}' 매칭"
                }
        
        # 기본값
        return {
            "decision_type": "single",
            "workflow_ids": ["structure_analysis"],
            "reasoning": "기본 workflow"
        }
    
    def assess_situation(self, query: str, context: Dict) -> Dict:
        """간단한 규칙 기반 평가"""
        
        word_count = len(query.split())
        
        return {
            "clarity": "clear" if word_count < 15 else "ambiguous",
            "evidence_availability": "unknown",
            "complexity": "simple" if word_count < 10 else "medium"
        }
    
    def decide_next_step(
        self,
        query: str,
        current_result: Dict,
        workflow_trace: List
    ) -> Dict:
        """간단한 규칙 기반 다음 단계"""
        
        quality = current_result.get("quality", {})
        
        if quality.get("literal_ratio", 0) < 0.3:
            return {
                "action": "collect_evidence",
                "reasoning": "Evidence 매우 부족"
            }
        
        return {
            "action": "complete",
            "reasoning": "기본 분석 완료"
        }
```

---

## 4. Cursor Agent Interface 아키텍처 (개정)

### 4.1 5-Layer 구조 (Self-Orchestration 포함)

```
┌──────────────────────────────────────────────────────────────┐
│             Layer 1: Conversation Layer                      │
│  (자연어 대화 → Intent → Workflow 매핑)                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  User: "한국 성인 어학교육 시장 규모 알려줘"                   │
│   ↓                                                          │
│  Intent Classifier:                                          │
│   - Type: market_analysis                                    │
│   - Workflow: structure_analysis                             │
│   - Params: {domain_id: "...", region: "KR"}                │
│   ↓                                                          │
│  Context Manager:                                            │
│   - Session Memory 조회                                      │
│   - 이전 분석 결과 활용                                       │
│   ↓                                                          │
│  Response Generator:                                         │
│   - 분석 결과 → 자연어 설명                                   │
│   - Lineage → 근거 제시                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│             Layer 2: Guardian Layer (v7 계승)                │
│  (목표 정렬, 순환 방지, 품질 관리)                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Process Guardian:                                           │
│   ┌─────────────────────────────────────────┐               │
│   │ Query Memory (순환 감지)                 │               │
│   │ - 동일 질문 반복 → 경고                  │               │
│   │ - 무한 루프 방지                         │               │
│   └─────────────────────────────────────────┘               │
│   ┌─────────────────────────────────────────┐               │
│   │ Goal Memory (목표 정렬)                  │               │
│   │ - 초기 목표 기억                         │               │
│   │ - 과도한 탐색 방지                       │               │
│   │ - "원래 질문으로 돌아가세요" 제안         │               │
│   └─────────────────────────────────────────┘               │
│   ┌─────────────────────────────────────────┐               │
│   │ Quality Gate (품질 관리)                 │               │
│   │ - 분석 완성도 평가                       │               │
│   │ - 필수 단계 누락 감지                    │               │
│   │ - Evidence 품질 확인                     │               │
│   └─────────────────────────────────────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│             Layer 3: CMIS Engine Layer                       │
│  (기존 9개 엔진 활용)                                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  WorkflowOrchestrator → canonical_workflows 실행              │
│  9 Engines → 실제 분석 수행                                   │
│  Stores → 결과 저장/조회                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. 온보딩 워크플로우

### 4.1 첫 실행 시나리오

```python
# cmis_cursor/onboarding.py

class OnboardingWorkflow:
    """신규 사용자 온보딩 워크플로우
    
    canonical_workflows와 별개로 동작하는 Setup Process.
    """
    
    def run(self) -> Dict[str, Any]:
        """온보딩 실행
        
        Returns:
            {
                "status": "ready" | "needs_setup",
                "missing_requirements": [...],
                "suggestions": [...]
            }
        """
        steps = [
            self._check_python_version,
            self._check_dependencies,
            self._check_environment_variables,
            self._check_api_keys,
            self._check_data_directories,
            self._run_sample_analysis
        ]
        
        results = []
        for step in steps:
            result = step()
            results.append(result)
            
            if not result["passed"]:
                # 자동 수정 시도
                if result.get("auto_fixable"):
                    self._auto_fix(result)
        
        return self._summarize_results(results)
    
    def _check_python_version(self) -> Dict:
        """Python 버전 확인 (3.13+)"""
        import sys
        version = sys.version_info
        
        if version >= (3, 13):
            return {"step": "python_version", "passed": True}
        else:
            return {
                "step": "python_version",
                "passed": False,
                "auto_fixable": False,
                "message": f"Python 3.13+ 필요 (현재: {version.major}.{version.minor})"
            }
    
    def _check_dependencies(self) -> Dict:
        """의존성 확인 및 자동 설치"""
        import subprocess
        
        try:
            # requirements.txt 확인
            result = subprocess.run(
                ["pip3", "install", "-r", "requirements.txt", "--dry-run"],
                capture_output=True
            )
            
            if "Would install" in result.stdout.decode():
                return {
                    "step": "dependencies",
                    "passed": False,
                    "auto_fixable": True,
                    "fix_command": "pip3 install -r requirements.txt"
                }
            
            return {"step": "dependencies", "passed": True}
        
        except Exception as e:
            return {
                "step": "dependencies",
                "passed": False,
                "auto_fixable": True,
                "error": str(e)
            }
    
    def _check_environment_variables(self) -> Dict:
        """환경 변수 확인"""
        import os
        
        required_vars = [
            "KOSIS_API_KEY",
            "DART_API_KEY",
            "ECOS_API_KEY"
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            return {
                "step": "environment",
                "passed": False,
                "auto_fixable": True,
                "missing": missing,
                "suggestion": "env.example를 복사하여 .env 파일 생성"
            }
        
        return {"step": "environment", "passed": True}
    
    def _run_sample_analysis(self) -> Dict:
        """샘플 분석 실행 (검증)"""
        from cmis_core.world_engine import WorldEngine
        
        try:
            engine = WorldEngine()
            snapshot = engine.snapshot(
                domain_id="Adult_Language_Education_KR",
                region="KR"
            )
            
            if snapshot.graph.num_nodes() > 0:
                return {
                    "step": "sample_analysis",
                    "passed": True,
                    "message": f"{snapshot.graph.num_nodes()}개 노드 로딩 성공"
                }
            else:
                return {
                    "step": "sample_analysis",
                    "passed": False,
                    "message": "샘플 데이터 로딩 실패"
                }
        
        except Exception as e:
            return {
                "step": "sample_analysis",
                "passed": False,
                "error": str(e)
            }
```

---

### 4.2 온보딩 vs Canonical Workflows

**결론**: **별도 Setup Process로 분리**

**이유**:
1. **외부와의 첫 접점** - CMIS 내부 워크플로우 이전 단계
2. **1회성** - 환경 설정 후 재실행 불필요
3. **시스템 레벨** - 사용자 질문/목표와 무관

**위치**:
```
cmis_cursor/
├─ onboarding.py       # Setup Process
└─ workflows/          # Cursor용 Canonical Workflows 래퍼
```

**canonical_workflows는**:
- 환경 설정 완료 후
- 실제 분석 단계에서 사용

---

## 5. LLM Context Window 대응

### 5.1 모델별 제약

| LLM 모델 | Context Window | CMIS 인지 범위 | 대응 전략 |
|---------|---------------|--------------|----------|
| GPT-4o | 128K | 전체 엔진 | Full Mode |
| Claude Sonnet 3.5 | 200K | 전체 엔진 + 문서 | Full Mode |
| Claude Sonnet 4.0 | 1M | 전체 + 히스토리 | Full Mode |
| GPT-3.5 | 16K | 제한적 | Lite Mode |

### 5.2 Adaptive Mode

```python
class CursorAgentInterface:
    """Cursor Agent Interface
    
    LLM Context Window에 따라 자동으로 모드 조정.
    """
    
    def __init__(self):
        self.context_window = self._detect_context_window()
        self.mode = self._select_mode()
    
    def _detect_context_window(self) -> int:
        """Context Window 감지
        
        Returns:
            추정 Context Window 크기 (tokens)
        """
        # Cursor API 또는 환경 변수에서 감지
        # 기본값: 128K (GPT-4o)
        return 128000
    
    def _select_mode(self) -> str:
        """Mode 선택
        
        Returns:
            "full" | "lite" | "minimal"
        """
        if self.context_window >= 100000:
            return "full"  # 전체 기능
        elif self.context_window >= 50000:
            return "lite"  # 핵심 기능만
        else:
            return "minimal"  # 최소 기능
    
    def get_available_workflows(self) -> List[str]:
        """Mode에 따른 사용 가능 워크플로우
        
        Returns:
            워크플로우 ID 리스트
        """
        if self.mode == "full":
            return [
                "structure_analysis",
                "opportunity_discovery",
                "strategy_design",
                "reality_monitoring"
            ]
        elif self.mode == "lite":
            return [
                "structure_analysis",  # 핵심만
                "opportunity_discovery"
            ]
        else:  # minimal
            return [
                "structure_analysis"  # 최소
            ]
```

### 5.3 동적 문서 로딩

```python
class ContextAwareDocLoader:
    """Context Window에 맞춘 문서 로딩"""
    
    def load_for_query(
        self,
        query: str,
        max_tokens: int
    ) -> str:
        """Query 관련 문서만 선택적 로딩
        
        Args:
            query: 사용자 질문
            max_tokens: 최대 토큰 (Context Window - 여유)
        
        Returns:
            관련 문서 (요약)
        """
        # 1. Query 분석
        intent = self._classify_intent(query)
        
        # 2. 필요한 엔진 파악
        required_engines = self._get_required_engines(intent)
        
        # 3. 엔진별 핵심 문서만 로딩
        docs = []
        for engine in required_engines:
            doc = self._load_engine_summary(engine, max_tokens // len(required_engines))
            docs.append(doc)
        
        return "\n\n".join(docs)
    
    def _load_engine_summary(self, engine_id: str, max_tokens: int) -> str:
        """엔진 요약 문서 (토큰 제한)
        
        전체 설계 문서 → 핵심만 추출
        """
        summaries = {
            "world_engine": """
                World Engine v2.0
                - snapshot(domain, region) → R-Graph
                - ingest_evidence() → R-Graph 확장
                - Greenfield/Brownfield 지원
            """,
            "value_engine": """
                Value Engine
                - evaluate_metrics() → ValueRecord
                - 4-Stage Resolution (Evidence → Derived → Prior → Fusion)
                - metrics_spec 기반
            """,
            # ...
        }
        
        return summaries.get(engine_id, "")
```

---

## 6. Process Guardian 구현

### 6.1 v7 Guardian 역할 계승

**v7 Guardian (Stewart)**:
- Query Memory (순환 감지)
- Goal Memory (목표 정렬)
- RAE Memory (평가 일관성)

**v9 Cursor Guardian**:
- Session Memory (대화 컨텍스트)
- Goal Alignment (목표 정렬)
- Quality Gate (품질 관리)
- Auto-Recovery (자동 복구)

---

### 6.2 구현

```python
class CursorProcessGuardian:
    """Process Guardian for Cursor Agent Interface
    
    v7 Guardian 역할 계승 + 강화.
    
    CMIS는 Objective-Oriented (목표 중심, 프로세스 자유도 높음)
    → Guardian의 감독 역할 더욱 중요!
    
    역할:
    1. 목표 정렬 (Goal Alignment) - 목적 잃지 않도록
    2. 순환 방지 (Loop Detection) - 무한 반복 방지
    3. 품질 관리 (Quality Gate) - 최소 기준 강제
    4. 자동 복구 (Auto-Recovery) - 오류 처리
    5. **Decision Logging** (신규) ⭐ - 모든 동적 결정 기록
    6. **Process Supervision** (신규) ⭐ - 재설계 감독
    
    v7 vs CMIS:
    - v7: 6-Agent 협업 감독
    - CMIS: Objective-Oriented 프로세스 감독 (자유도 높음 → 감독 강화)
    """
    
    def __init__(self):
        # Memory Stores (v7 계승)
        self.query_memory: List[Dict] = []  # 질문 히스토리
        self.goal_stack: List[str] = []  # 목표 스택
        self.workflow_trace: List[Dict] = []  # 워크플로우 실행 이력
        
        # Decision Log (신규) ⭐
        self.decision_log: List[Dict] = []  # 모든 동적 결정 기록
        self.replanning_log: List[Dict] = []  # 재설계 이력
        
        # Quality History (신규) ⭐
        self.quality_history: List[Dict] = []  # 품질 변화 추적
        
        # Thresholds
        self.max_similar_queries = 3  # 동일 질문 반복 한계
        self.max_depth = 5  # 탐색 깊이 한계
        self.max_replanning = 3  # 최대 재설계 횟수 (신규)
        self.min_evidence_quality = 0.5  # 최소 Evidence 품질
    
    # ========================================
    # 1. Query Memory (순환 감지)
    # ========================================
    
    def check_query_loop(self, query: str) -> Dict[str, Any]:
        """질문 순환 감지
        
        Args:
            query: 현재 질문
        
        Returns:
            {
                "is_loop": True/False,
                "similar_count": 3,
                "suggestion": "이미 3번 유사한 질문을 했습니다..."
            }
        """
        # 유사 질문 검색
        similar_queries = [
            q for q in self.query_memory
            if self._similarity(q["query"], query) > 0.8
        ]
        
        if len(similar_queries) >= self.max_similar_queries:
            return {
                "is_loop": True,
                "similar_count": len(similar_queries),
                "suggestion": (
                    f"이미 {len(similar_queries)}번 유사한 질문을 했습니다. "
                    "다른 접근을 시도하거나, 이전 결과를 활용하세요."
                ),
                "previous_results": [q["result_ref"] for q in similar_queries]
            }
        
        # 질문 기록
        self.query_memory.append({
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "result_ref": None  # 나중에 업데이트
        })
        
        return {"is_loop": False}
    
    # ========================================
    # 2. Goal Memory (목표 정렬)
    # ========================================
    
    def check_goal_alignment(self, current_action: str) -> Dict[str, Any]:
        """목표 정렬 확인
        
        현재 작업이 초기 목표와 정렬되어 있는지 확인.
        
        Args:
            current_action: 현재 수행 중인 작업
        
        Returns:
            {
                "aligned": True/False,
                "drift_level": "low" | "medium" | "high",
                "suggestion": "..."
            }
        """
        if not self.goal_stack:
            # 초기 목표 설정
            return {"aligned": True, "drift_level": "low"}
        
        initial_goal = self.goal_stack[0]
        current_depth = len(self.goal_stack)
        
        # 깊이 제한
        if current_depth > self.max_depth:
            return {
                "aligned": False,
                "drift_level": "high",
                "suggestion": (
                    f"탐색 깊이가 너무 깊습니다 (현재: {current_depth}). "
                    f"초기 목표로 돌아가세요: '{initial_goal}'"
                ),
                "initial_goal": initial_goal
            }
        
        # 의미적 유사도 확인
        similarity = self._semantic_similarity(initial_goal, current_action)
        
        if similarity < 0.3:
            drift_level = "high"
        elif similarity < 0.6:
            drift_level = "medium"
        else:
            drift_level = "low"
        
        return {
            "aligned": drift_level != "high",
            "drift_level": drift_level,
            "suggestion": (
                f"현재 작업이 초기 목표와 다소 벗어났습니다. "
                f"초기 목표: '{initial_goal}'"
            ) if drift_level == "high" else None
        }
    
    def push_goal(self, goal: str):
        """하위 목표 추가"""
        self.goal_stack.append(goal)
    
    def pop_goal(self):
        """하위 목표 완료"""
        if len(self.goal_stack) > 1:
            self.goal_stack.pop()
    
    # ========================================
    # 3. Quality Gate (품질 관리)
    # ========================================
    
    def check_analysis_quality(
        self,
        analysis_result: Dict
    ) -> Dict[str, Any]:
        """분석 품질 확인
        
        Args:
            analysis_result: 분석 결과
        
        Returns:
            {
                "quality_level": "A" | "B" | "C" | "F",
                "issues": [...],
                "suggestions": [...]
            }
        """
        issues = []
        
        # Evidence 품질 확인
        if "metrics" in analysis_result:
            low_quality_metrics = [
                m for m in analysis_result["metrics"]
                if m.get("quality", {}).get("literal_ratio", 0) < self.min_evidence_quality
            ]
            
            if low_quality_metrics:
                issues.append({
                    "type": "low_evidence_quality",
                    "metrics": [m["metric_id"] for m in low_quality_metrics],
                    "suggestion": "더 많은 Evidence 수집 필요"
                })
        
        # 필수 단계 누락 확인
        if "pattern_matches" not in analysis_result:
            issues.append({
                "type": "missing_pattern_analysis",
                "suggestion": "Pattern 분석 수행 필요"
            })
        
        # 품질 레벨 결정
        if len(issues) == 0:
            quality_level = "A"
        elif len(issues) <= 2:
            quality_level = "B"
        elif len(issues) <= 4:
            quality_level = "C"
        else:
            quality_level = "F"
        
        return {
            "quality_level": quality_level,
            "issues": issues,
            "passed": quality_level in ["A", "B"]
        }
    
    # ========================================
    # 4. Decision Logging (신규) ⭐
    # ========================================
    
    def log_decision(
        self,
        decision_type: str,
        decision: Dict,
        reasoning: str
    ):
        """모든 동적 결정 기록
        
        Objective-Oriented 설계 → 자유도 높음 → Logging 필수
        
        Args:
            decision_type: "workflow_selection" | "replanning" | "path_change"
            decision: 결정 내용
            reasoning: 이유
        """
        self.decision_log.append({
            "timestamp": datetime.now().isoformat(),
            "decision_type": decision_type,
            "decision": decision,
            "reasoning": reasoning,
            "current_goal": self.goal_stack[-1] if self.goal_stack else None,
            "depth": len(self.goal_stack)
        })
    
    def log_replanning(
        self,
        trigger: str,
        old_plan: Dict,
        new_plan: Dict,
        new_insights: List[str]
    ):
        """재설계 이력 기록
        
        Args:
            trigger: "new_insight" | "insufficient_evidence" | "goal_drift"
            old_plan: 기존 계획
            new_plan: 새 계획
            new_insights: 새로운 발견
        """
        self.replanning_log.append({
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger,
            "old_plan": old_plan,
            "new_plan": new_plan,
            "new_insights": new_insights,
            "replanning_count": len(self.replanning_log) + 1
        })
        
        # 재설계 과다 → 경고
        if len(self.replanning_log) >= self.max_replanning:
            self._emit_warning(
                "excessive_replanning",
                f"재설계가 {len(self.replanning_log)}회 발생했습니다. "
                "목표를 재검토하거나 단순화하세요."
            )
    
    def get_process_trace(self) -> Dict[str, Any]:
        """완전한 Process Trace 반환
        
        재현/디버깅/감사용.
        
        Returns:
            {
                "query_memory": [...],
                "goal_stack": [...],
                "workflow_trace": [...],
                "decision_log": [...],  # 모든 결정
                "replanning_log": [...],  # 모든 재설계
                "quality_history": [...]  # 품질 변화
            }
        """
        return {
            "query_memory": self.query_memory,
            "goal_stack": self.goal_stack,
            "workflow_trace": self.workflow_trace,
            "decision_log": self.decision_log,
            "replanning_log": self.replanning_log,
            "quality_history": self.quality_history,
            "total_decisions": len(self.decision_log),
            "total_replannings": len(self.replanning_log)
        }
    
    def _emit_warning(self, warning_type: str, message: str):
        """경고 발생 (Guardian → User/Agent)"""
        print(f"⚠️ [Guardian Warning] {warning_type}: {message}")
    
    # ========================================
    # 5. Auto-Recovery (자동 복구)
    # ========================================
    
    def auto_recover(self, error: Exception) -> Dict[str, Any]:
        """오류 자동 복구
        
        Args:
            error: 발생한 오류
        
        Returns:
            {
                "recoverable": True/False,
                "recovery_action": "...",
                "fallback_workflow": "..."
            }
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # 알려진 오류 패턴
        if "FileNotFoundError" in error_type:
            return {
                "recoverable": True,
                "recovery_action": "파일 생성 시도",
                "fallback_workflow": None
            }
        
        elif "API" in error_msg or "403" in error_msg:
            return {
                "recoverable": True,
                "recovery_action": "DuckDuckGo로 fallback",
                "fallback_workflow": "search_strategy_fallback"
            }
        
        elif "Evidence 부족" in error_msg:
            return {
                "recoverable": True,
                "recovery_action": "Prior estimation 사용",
                "fallback_workflow": None
            }
        
        else:
            return {
                "recoverable": False,
                "recovery_action": None,
                "suggestion": "수동 확인 필요"
            }
```

---

## 7. Objective-Oriented 실행 예시

### 7.1 동적 재설계 예시 (CMIS 핵심)

**시나리오**: 중간 결과가 예상과 다를 때 경로 재설계

```
User: "한국 성인 어학교육 시장 분석 후 진입 전략 제안해줘"

[AdaptiveOrchestrator] Goal 설정
  목표: "시장 분석 + 진입 전략"

[AdaptiveOrchestrator] 초기 Plan
  예상 경로:
    1. structure_analysis (시장 구조)
    2. opportunity_discovery (기회 발굴)
    3. strategy_design (전략 수립)

[Step 1] structure_analysis 실행
  ├─ Evidence 수집... ✅
  ├─ R-Graph 구축... ✅
  └─ Metric 계산... ✅
  
  결과:
    - TAM: 1.5조원 (예상: 3조원) ← 예상보다 작음!
    - Top 3 점유율: 85% ← 매우 높음!
    - HHI: 3,500 ← 과점 구조!

[AdaptiveOrchestrator] 중간 평가
  새로운 발견:
    - "시장 규모 예상보다 50% 작음"
    - "시장 집중도 매우 높음 (과점)"
    - "신규 진입 장벽 높음"
  
  상황 재평가:
    원래 가정: "성장 시장, 기회 많음"
    현실: "성숙 시장, 포화 상태"

[AdaptiveOrchestrator] Plan 재설계 ← 동적!
  
  [LLM에게 질문]
  "시장이 작고 집중도 높은 상황에서 진입 전략은?"
  
  [LLM 응답]
  "Gap Discovery (X) → Adjacent Market 탐색
   또는 Niche Segment 전략"
  
  [Plan 변경]
  Before:
    1. structure ✅
    2. opportunity (gap discovery)
    3. strategy (market entry)
  
  After:
    1. structure ✅
    2. adjacent_market_analysis (신규)
    3. niche_segment_discovery (신규)
    4. strategy (pivot/differentiation)

[Guardian] 재설계 승인
  ✅ Goal 여전히 정렬 ("진입 전략 제안")
  ✅ 재설계 횟수 1회 (< 3회)
  ✅ 논리적 근거 충분

[Decision Log]
  {
    "decision_type": "replanning",
    "trigger": "market_saturation_discovered",
    "reasoning": "시장 작고 집중도 높음 → Gap 어려움 → Adjacent 탐색",
    "plan_change": {
      "removed": ["opportunity_gap"],
      "added": ["adjacent_market", "niche_segment"]
    }
  }

[Step 2] adjacent_market_analysis 실행 (재설계된 경로)
  ├─ 인접 시장 탐색... ✅
  └─ 결과: "기업 교육 시장 (B2B)" 발견

[Step 3] strategy_design 실행
  └─ B2B Pivot 전략 제안

[완료]
  최종 결과: 초기 계획(B2C)과 다른 경로(B2B)로 더 나은 전략 도출
  
  Decision Log:
    - goal_setting: "시장 분석 + 진입 전략"
    - initial_planning: [structure, opportunity, strategy]
    - intermediate_evaluation: "시장 포화"
    - replanning: [structure, adjacent, niche, strategy]
    - final_quality: "A"
```

**핵심**:
- 중간 결과 ("시장 작고 집중도 높음")
- 능동적 판단 ("Gap 어려움")
- 동적 재설계 ("Adjacent Market으로 전환")
- 완전한 Logging (Decision Log)

---

### 7.2 정상 분석 플로우 (재설계 없음)

```
User: "한국 성인 어학교육 시장 규모 알려줘"

[Guardian] 목표 설정: "시장 규모 분석"
[Guardian] 환경 확인... ✅
[Guardian] 워크플로우 선택: structure_analysis

Agent: 분석을 시작합니다...

[CMIS] structure_analysis 실행
[CMIS] Evidence 수집 (KOSIS, DART, Google)
[CMIS] R-Graph 구축 (50+ 노드)
[CMIS] Metric 계산 (TAM, SAM, SOM)

[Guardian] 품질 확인...
[Guardian] Evidence Quality: 75% (B등급) ✅
[Guardian] 필수 단계: 모두 완료 ✅

Agent: 분석 완료! 

한국 성인 어학교육 시장 규모:
- TAM: 1조 5천억원
- SAM: 1조원 (온라인)
- SOM: 3천억원 (우리 도달 가능)

근거:
- DART: YBM넷 817억원 (2023)
- 업계 추정: Top 10 합산
- 인구 통계: KOSIS 성인 인구 4,200만명

[저장됨: ART-market-size-001]

User: "상세 계산 과정 보여줘"

Agent: [Lineage 추적]
EVD-001 (DART YBM) → ACT-YBM → MFL-customers-to-YBM → ...
```

---

### 7.2 순환 감지 플로우

```
User: "한국 어학 시장 규모는?"

[Guardian] 분석 실행... ✅

User: "한국 성인 어학 시장 규모는?"

[Guardian] 유사 질문 1회 (50% 유사)

User: "한국 어학교육 시장 크기 알려줘"

[Guardian] 유사 질문 2회 (85% 유사)

User: "한국에서 어학 시장 규모가 얼마야?"

[Guardian] 🚨 순환 감지! 유사 질문 3회

Agent: 잠깐만요! 동일한 질문을 4번째 하고 계십니다.
이미 분석한 결과를 확인하시겠습니까?

이전 결과:
- [ART-market-size-001]: TAM 1조 5천억원
- [ART-market-size-002]: SAM 1조원

또는 다른 질문을 해주세요.
```

---

### 7.3 목표 이탈 플로우

```
User: "한국 성인 어학교육 시장 분석해줘"

[Guardian] 목표 설정: "시장 분석"
[Guardian] Depth: 0

Agent: 분석 시작...

User: "YBM넷 재무제표 상세히 봐줘"

[Guardian] 하위 목표: "YBM 재무 분석"
[Guardian] Depth: 1

Agent: YBM넷 재무제표 분석...

User: "YBM의 마케팅 비용 추이는?"

[Guardian] 하위 목표: "마케팅 비용"
[Guardian] Depth: 2

User: "온라인 광고 플랫폼별 비교해줘"

[Guardian] 하위 목표: "광고 플랫폼"
[Guardian] Depth: 3

User: "네이버 광고 API 문서 찾아줘"

[Guardian] 🚨 목표 이탈 감지! Depth: 4

Agent: 잠깐만요! 현재 작업이 초기 목표와 많이 벗어났습니다.

초기 목표: "한국 성인 어학교육 시장 분석"
현재 작업: "네이버 광고 API"

초기 목표로 돌아가시겠습니까?
[Yes] 시장 분석으로 돌아가기
[No] 계속 진행 (Guardian 일시 중지)
```

---

## 8. Cursor Interface 구현 계획

### 8.1 Phase 1: 기본 인터페이스 (1주)

**작업**:
1. `cmis_cursor/interface.py` (300줄)
   - CursorAgentInterface 클래스
   - query() 메서드 (자연어 → 워크플로우)
   - Context Manager

2. `cmis_cursor/onboarding.py` (200줄)
   - OnboardingWorkflow
   - 환경 확인/설정

3. `cmis_cursor/guardian.py` (400줄)
   - CursorProcessGuardian
   - Query/Goal/Quality Memory

4. `.cursorrules` 확장
   - CMIS 사용 가이드
   - 워크플로우 매핑

**테스트**:
- 온보딩 시나리오 (5개)
- 기본 질문 → 워크플로우 (10개)
- Guardian 시나리오 (5개)

---

### 8.2 Phase 2: Context 최적화 (3일)

**작업**:
1. Context Window 감지
2. 동적 문서 로딩
3. Mode 전환 (Full/Lite/Minimal)

**테스트**:
- 모델별 테스트
- Context Window 제약 시뮬레이션

---

### 8.3 Phase 3: 자가 개선 (1주)

**작업**:
1. 오류 자동 복구
2. 코드 자동 수정
3. 학습 메커니즘

**테스트**:
- 오류 복구 시나리오
- 자동 수정 검증

---

## 9. .cursorrules 확장

### 9.1 CMIS 섹션 추가

```markdown
# CMIS - Contextual Market Intelligence System

## 빠른 시작

사용자가 시장 분석 질문을 하면:

1. 환경 확인
   - Python 3.13+
   - requirements.txt 설치
   - .env 파일 (API 키)
   
   확인 명령: `python3 cmis_cursor/onboarding.py`

2. 질문 분류
   - "시장 규모" → structure_analysis
   - "기회 발굴" → opportunity_discovery
   - "전략 수립" → strategy_design
   - "경쟁 분석" → structure_analysis (경쟁 섹션)

3. 워크플로우 실행
   ```python
   from cmis_cursor.interface import CursorAgentInterface
   
   interface = CursorAgentInterface()
   result = interface.query("한국 성인 어학교육 시장 규모는?")
   ```

4. 결과 설명
   - Lineage 추적
   - 근거 제시
   - 자연어로 설명

## Process Guardian

**목표 이탈 방지**:
- 초기 목표 기억
- Depth > 5 → 경고
- 유사 질문 3회 → 순환 감지

**품질 관리**:
- Evidence Quality < 50% → 경고
- 필수 단계 누락 → 제안

## 주의사항

- 모든 분석은 Evidence 기반
- Prior는 최후 수단
- Lineage 완전 추적
- canonical_workflows 활용

## 디버깅

오류 발생 시:
1. 자동 복구 시도
2. Fallback 워크플로우
3. 수동 확인 (필요 시)
```

---

## 10. 구현 파일 구조

```
cmis_cursor/
├─ __init__.py
├─ interface.py              # CursorAgentInterface (Main)
├─ onboarding.py             # OnboardingWorkflow
├─ guardian.py               # CursorProcessGuardian
├─ intent_classifier.py      # 자연어 → Intent
├─ context_manager.py        # Session Memory
├─ response_generator.py     # 결과 → 자연어
├─ doc_loader.py             # Context-aware 문서 로딩
└─ workflows/
   ├─ cursor_structure_analysis.py
   ├─ cursor_opportunity_discovery.py
   └─ cursor_strategy_design.py

.cursorrules                 # Cursor Agent 가이드 (확장)

dev/docs/architecture/
└─ CMIS_Cursor_Agent_Interface_Design.md (본 문서)
```

---

## 11. 사용 예시

### 11.1 Python API

```python
from cmis_cursor.interface import CursorAgentInterface

# Interface 초기화
interface = CursorAgentInterface()

# 온보딩 (첫 실행 시)
onboarding_result = interface.onboard()
if not onboarding_result["ready"]:
    print("환경 설정이 필요합니다:")
    for issue in onboarding_result["issues"]:
        print(f"  - {issue}")
    
    # 자동 수정
    interface.auto_fix()

# 질문
result = interface.query("한국 성인 어학교육 시장 규모는?")

print(result["answer"])
print(f"\n근거: {result['evidence_summary']}")
print(f"품질: {result['quality_level']}")

# 추가 질문 (컨텍스트 유지)
result2 = interface.query("경쟁 구조는?")  # 동일 세션
```

---

### 11.2 Cursor Agent 직접 사용

사용자가 Cursor Agent 창에서:

```
User: "CMIS로 한국 어학 시장 분석해줘"

Agent: [자동 실행]
1. 환경 확인... ✅
2. structure_analysis 실행...
3. 결과 생성...

한국 성인 어학교육 시장:
- 규모: TAM 1.5조원, SAM 1조원
- 경쟁: Top 3 점유율 45%
- 특징: 온라인 전환 가속

더 자세한 분석이 필요하신가요?
```

---

## 12. CMIS 전체 아키텍처 업데이트

### 12.1 새로운 Layer 추가

**Before (v3.5.0)**:
```
Interaction Plane (4개 인터페이스)
    ↓
Role Plane (5개 역할)
    ↓
Cognition Plane (9개 엔진)
    ├─ WorkflowOrchestrator (canonical_workflows 실행)
    └─ Engines
    ↓
Substrate Plane (Graphs & Stores)
```

**After (v3.6.0 제안)**:
```
Interaction Plane (5개 인터페이스)
    ├─ CLI, Cursor, Jupyter, Web, API
    └─ Interface별 OrchestrationProvider
    ↓
┌─────────────────────────────────────────┐
│  Orchestration Layer (신규) ⭐           │
│  - AdaptiveOrchestrator                 │
│  - OrchestrationProvider (추상화)       │
│    ├─ CursorOrchestrationProvider       │
│    ├─ ExternalLLMOrchestrationProvider  │
│    └─ RuleBasedOrchestrationProvider    │
└─────────────────────────────────────────┘
    ↓
Role Plane (5개 역할)
    ↓
Cognition Plane (9개 엔진)
    ├─ WorkflowOrchestrator (실행기)
    └─ Engines
    ↓
Substrate Plane (Graphs & Stores)
```

**핵심 변화**:
1. **Orchestration Layer 신규 추가** (v7 Self-Orchestration 계승)
2. **LLM Provider 추상화** (Cursor/External/Rule-Based)
3. **프로덕션 배포 가능 구조** (Non-Cursor도 orchestration)

---

### 12.2 cmis.yaml 업데이트

```yaml
interaction_plane:
  interfaces:
    - id: "cursor_agent"
      type: "conversational_ide"
      description: "Cursor Agent 기반 대화형 인터페이스"
      version: "v1.0"
      status: "design"
      implementation: "cmis_cursor/"
      
      capabilities:
        - "자연어 질문 → 워크플로우 자동 매핑"
        - "컨텍스트 유지 (세션 메모리)"
        - "자동 온보딩 (환경 설정)"
        - "Process Guardian (목표 정렬, 순환 방지)"
        - "품질 관리 (Evidence Quality Gate)"
        - "자동 복구 (오류 처리)"
        - "Lineage 추적 설명"
      
      context_window_support:
        full_mode: ">= 100K tokens"
        lite_mode: ">= 50K tokens"
        minimal_mode: "< 50K tokens"
      
      guardian_features:
        query_memory:
          max_similar_queries: 3
          similarity_threshold: 0.8
        
        goal_memory:
          max_depth: 5
          drift_threshold: 0.3
        
        quality_gate:
          min_evidence_quality: 0.5
          required_steps: ["evidence","pattern","metric"]
      
      default_role_id: "structure_analyst"
      
      preferred_engines:
        - "world_engine"
        - "pattern_engine"
        - "value_engine"
        - "belief_engine"
      
      output_formats:
        - "markdown"
        - "json"
        - "lineage_trace"
```

---

## 13. 인터페이스별 Orchestration 전략

### 13.1 인터페이스 × Orchestration Provider 매핑

| Interface | Orchestration Provider | LLM | Self-Orchestration | 프로덕션 |
|-----------|----------------------|-----|-------------------|---------|
| **CLI** | RuleBasedOrchestrationProvider | 없음 | ❌ | ✅ |
| **Cursor Agent** | CursorOrchestrationProvider | Cursor 내장 | ✅ | ⚠️ (개발용) |
| **Jupyter** | CursorOrchestrationProvider (선택) 또는 RuleBased | 선택적 | ⚠️ | ⚠️ |
| **Web App** | ExternalLLMOrchestrationProvider | GPT-4/Claude API | ✅ | ✅ |
| **API** | ExternalLLMOrchestrationProvider | 클라이언트 지정 | ✅ | ✅ |

**프로덕션 배포 시 Orchestration**:
- **Web App**: ExternalLLMOrchestrationProvider (GPT-4 API)
- **API**: 클라이언트가 LLM 제공 또는 RuleBased
- **Jupyter**: 개발자가 직접 제어 (Provider 선택)

---

### 13.2 인터페이스 비교표 (확장)

| 항목 | CLI | Cursor Agent | Jupyter | Web App | API |
|------|-----|-------------|---------|---------|-----|
| **대상** | Agent/개발자 | Agent+개발자 | 개발자 | 사용자 | 시스템 |
| **입력** | 명령어 | 자연어 | Python 코드 | UI 클릭 | HTTP |
| **출력** | 텍스트/JSON | 마크다운 | 결과/그래프 | HTML/차트 | JSON |
| **Orchestration** | Rule-Based | **Cursor Agent** ⭐ | 선택적 | **External LLM** ⭐ | **External LLM** ⭐ |
| **Self-Orch** | ❌ | ✅ | ⚠️ | ✅ | ✅ |
| **컨텍스트** | 없음 | 세션 유지 | Kernel 유지 | 세션 | Stateless |
| **디버깅** | 수동 | 자동 | 수동 | 불가 | 로그 |
| **Guardian** | 없음 | **있음** ⭐ | 없음 | **있음** (LLM) | **있음** (LLM) |
| **온보딩** | 수동 | **자동** ⭐ | 수동 | 가이드 | 문서 |
| **프로덕션** | ✅ | ⚠️ 개발용 | ⚠️ | ✅ | ✅ |
| **상태** | ✅ | 🚧 설계 | 📋 계획 | 📋 계획 | 📋 계획 |

**Cursor Agent의 독특한 가치**:
1. **대화형 + 자동화** - 자연어로 묻고, Agent가 자동 실행
2. **컨텍스트 유지** - 이전 대화 기억
3. **자가 개선** - 오류 발견 시 자동 수정
4. **Process Guardian** - 목표 정렬, 품질 관리
5. **개발/사용 통합** - 같은 인터페이스에서 디버깅/개발

---

## 14. 구현 우선순위 (개정)

### Milestone 0: Self-Orchestration 추가 (2주) 🆕

**v7 Self-Orchestration을 CMIS에 도입**

**작업**:
1. `cmis_core/adaptive_orchestrator.py` (500줄)
   - AdaptiveOrchestrator 클래스
   - OrchestrationProvider 추상 클래스
   - Workflow 선택/조합 로직

2. `cmis_core/orchestration_providers.py` (600줄)
   - CursorOrchestrationProvider
   - ExternalLLMOrchestrationProvider
   - RuleBasedOrchestrationProvider

3. `cmis_core/llm_clients.py` (300줄)
   - OpenAI Client 래퍼
   - Anthropic Client 래퍼
   - 통합 인터페이스

4. 테스트 (20개)
   - Provider별 테스트 (9개)
   - AdaptiveOrchestrator 테스트 (6개)
   - Integration 테스트 (5개)

**중요도**: ⭐⭐⭐ (프로덕션 배포 필수)

---

### Milestone 1: Cursor Interface (1주)
- [ ] CursorAgentInterface 클래스
- [ ] OnboardingWorkflow
- [ ] CursorOrchestrationProvider 연동
- [ ] .cursorrules 확장

### Milestone 2: Guardian (1주)
- [ ] CursorProcessGuardian (v7 계승)
- [ ] Query/Goal/Quality Memory
- [ ] 순환 감지, 목표 정렬

### Milestone 3: Web/API Orchestration (1주) 🆕
- [ ] ExternalLLMOrchestrationProvider 구현
- [ ] Web App에 통합
- [ ] API에 통합
- [ ] 프로덕션 테스트

### Milestone 4: Context 최적화 (3일)
- [ ] Context Window 감지
- [ ] 동적 문서 로딩
- [ ] Mode 전환

### Milestone 5: 자가 개선 (1주)
- [ ] Auto-Recovery
- [ ] 자동 수정
- [ ] 학습 메커니즘

**총 예상 시간**: 6-7주 (Self-Orchestration 추가로 증가)

---

## 15. 프로덕션 배포 시나리오

### 15.1 Web App에서 Self-Orchestration

**사용자 시나리오**:
```
[Web UI]
User: "한국 어학 시장 분석해줘" (텍스트 입력)
    ↓
[Backend: FastAPI]
AdaptiveOrchestrator (ExternalLLMOrchestrationProvider)
    ├─ LLM API 호출 (GPT-4)
    │   └─ "structure_analysis 선택"
    ├─ WorkflowOrchestrator 실행
    └─ 결과 반환
    ↓
[Frontend]
결과 렌더링 (차트, 표, Lineage)
```

**Backend 코드**:
```python
from fastapi import FastAPI
from cmis_core.adaptive_orchestrator import AdaptiveOrchestrator
from cmis_core.orchestration_providers import ExternalLLMOrchestrationProvider
from openai import OpenAI

app = FastAPI()

# LLM Client
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Orchestration Provider
provider = ExternalLLMOrchestrationProvider(
    llm_client=llm_client,
    model="gpt-4-turbo"
)

# AdaptiveOrchestrator
orchestrator = AdaptiveOrchestrator(
    orchestration_provider=provider,
    workflow_orchestrator=WorkflowOrchestrator()
)

@app.post("/api/query")
async def query(request: QueryRequest):
    """자연어 질문 → CMIS 분석"""
    
    result = orchestrator.process_query(
        query=request.query,
        context=request.context
    )
    
    return {
        "answer": result["answer"],
        "results": result["results"],
        "quality": result["quality"]
    }
```

**프로덕션 가능**: ✅ External LLM으로 orchestration

---

### 15.2 API에서 Self-Orchestration

**클라이언트 시나리오**:
```python
import requests

# CMIS API 호출
response = requests.post(
    "https://cmis-api.example.com/api/query",
    json={
        "query": "한국 성인 어학교육 시장의 TAM/SAM은?",
        "context": {
            "project_context_id": "PRJ-my-company"  # Brownfield
        },
        "llm_config": {
            "provider": "external_llm",  # 또는 "rule_based"
            "model": "gpt-4"
        }
    },
    headers={"Authorization": "Bearer YOUR_API_KEY"}
)

result = response.json()
```

**Backend**: 동일 (AdaptiveOrchestrator + ExternalLLMOrchestrationProvider)

---

## 16. 향후 확장

### v3.6.0: AdaptiveOrchestrator (핵심) ⭐⭐⭐
**예상**: 2주
- Self-Orchestration 구현
- LLM Provider 추상화
- 프로덕션 배포 가능 구조

### v4.0: Cursor Interface 완성
**예상**: 2주
- CursorAgentInterface
- OnboardingWorkflow
- Process Guardian

### v4.1: Web/API Orchestration
**예상**: 1주
- Web App 통합
- API 통합
- External LLM 연동

### v4.2: Multi-Turn 대화
- 대화 히스토리 관리
- 참조 해결 ("그거", "이전 결과")

### v4.3: Proactive Suggestions
- 다음 질문 제안
- 추가 분석 추천

### v5.0: Collaborative Mode
- 여러 사용자 동시 사용
- 세션 공유

---

## 16. 핵심 설계 결정

### 16.1 Self-Orchestration 도입 ⭐⭐⭐

**결정**: v7의 Self-Orchestration을 **AdaptiveOrchestrator**로 구현

**이유**:
- v7의 핵심 가치 (동적 판단, 유연한 실행)
- canonical_workflows만으로는 제한적
- 복잡한 질문 대응 불가

**구조**:
```
AdaptiveOrchestrator (What/Which)
    ↓
WorkflowOrchestrator (How)
    ↓
CMIS Engines
```

---

### 16.2 LLM Orchestration 추상화 ⭐⭐⭐

**결정**: OrchestrationProvider 추상 클래스로 LLM 분리

**이유**:
- Cursor가 아닌 인터페이스도 orchestration 필요 (프로덕션)
- LLM 교체 가능 (GPT-4, Claude, 규칙 기반)
- 동일 로직, 다른 인터페이스

**Provider 3가지**:
1. **CursorOrchestrationProvider**: Cursor Agent
2. **ExternalLLMOrchestrationProvider**: GPT-4/Claude API (프로덕션)
3. **RuleBasedOrchestrationProvider**: 키워드 기반 (Fallback)

---

### 16.3 인터페이스별 배포 전략

| Interface | Orchestration | 대상 | 배포 |
|-----------|--------------|------|------|
| CLI | Rule-Based | 개발자 | ✅ 현재 |
| Cursor Agent | Cursor Agent | 개발자 | 🚧 v3.6.0 |
| Jupyter | 선택적 (Cursor/Rule) | 개발자 | 📋 v4.0 |
| **Web App** | **External LLM (GPT-4)** | 사용자 | 📋 **v5.0** ⭐ |
| **API** | **External LLM (클라이언트)** | 시스템 | 📋 **v5.0** ⭐ |

**프로덕션 핵심**: Web App/API는 **External LLM**으로 orchestration

---

## 17. 핵심 설계 원칙 정리

### 17.1 Objective-Oriented Architecture ⭐⭐⭐

**CMIS의 핵심 중 핵심**:

```
목표: "한국 어학 시장 진입 전략"
    ↓
[동적 재설계 루프]
    Execute Step
        ↓
    Evaluate (Evidence, Metric, Insight)
        ↓
    [새로운 정보 기반 판단] ← 능동적!
        ├─ 충분? → 다음 Step
        ├─ 부족? → 재시도
        ├─ 예상과 다름? → Plan 재설계 ← 핵심!
        └─ 막힘? → Workflow 변경
    ↓
Goal 달성까지 반복
```

**왜 필수인가**:
1. Evidence 품질 → Structure 분석 깊이 달라짐
2. 시장 규모 (크다/작다) → Opportunity 접근 달라짐
3. 집중도 (높다/낮다) → Strategy 방향 달라짐
4. 새 발견 (포화/성장) → 전체 경로 재설계

**Process-Oriented와의 차이**:

| | Process-Oriented | Objective-Oriented |
|---|-----------------|-------------------|
| **중심** | 프로세스 (정해진 순서) | 목표 (달성 방법 자유) |
| **경로** | 고정 | 동적 (재설계) |
| **중간 결과** | 무시 | 재계획 트리거 |
| **유연성** | 낮음 | 높음 ⭐ |
| **Guardian** | 선택적 | **필수** ⭐ |

---

### 17.2 Process Logging & Supervision ⭐⭐⭐

**프로세스 자유도 높음 → Logging/감독 더욱 중요**

**완전한 Decision Log**:
```json
{
  "decision_log": [
    {
      "timestamp": "2025-12-12T10:00:00Z",
      "decision_type": "goal_setting",
      "data": {"goal": "시장 분석 + 진입 전략"},
      "summary": "사용자 질문에서 목표 추출"
    },
    {
      "timestamp": "2025-12-12T10:00:05Z",
      "decision_type": "initial_planning",
      "data": {"workflows": ["structure", "opportunity", "strategy"]},
      "summary": "초기 계획 수립"
    },
    {
      "timestamp": "2025-12-12T10:05:30Z",
      "decision_type": "intermediate_evaluation",
      "data": {
        "evidence_quality": 0.75,
        "new_insights": ["시장 포화", "집중도 높음"]
      },
      "summary": "중간 평가 - 예상과 다름"
    },
    {
      "timestamp": "2025-12-12T10:05:35Z",
      "decision_type": "replanning",
      "data": {
        "trigger": "market_saturation",
        "old_plan": ["opportunity_gap"],
        "new_plan": ["adjacent_market", "niche_segment"]
      },
      "summary": "경로 재설계 - Adjacent Market으로 전환"
    }
  ],
  "replanning_log": [
    {
      "trigger": "new_insight_market_saturation",
      "old_plan": {...},
      "new_plan": {...},
      "reasoning": "Gap Discovery 어려움 → Adjacent Market 탐색"
    }
  ]
}
```

**Guardian 감독**:
- 모든 재설계 기록
- Goal Alignment 지속 확인
- 과도한 재설계 방지 (max 3회)
- 순환 감지

**투명성**:
- 왜 이 경로를 선택했는지
- 언제 경로를 변경했는지
- 무엇이 재설계를 트리거했는지
- **완전한 재현 가능**

---

## 18. v7 → CMIS 진화

### 18.1 Orchestration 비교

| 요소 | v7 | CMIS (v3.5.0) | CMIS (v3.6.0+) |
|------|-------|-----------|---------------|
| **Architecture** | Multi-Agentic | Fixed Workflow | **Objective-Oriented** ⭐ |
| **Orchestration** | 사용자+Agent (동적) | WorkflowOrchestrator (고정) | **AdaptiveOrchestrator (동적)** ⭐ |
| **중심** | Agent 협업 | Process 순서 | **Goal 달성** ⭐ |
| **유연성** | 매우 높음 | 낮음 | **높음 (재설계)** ⭐ |
| **Guardian** | Stewart | ❌ | **CursorProcessGuardian** ⭐ |
| **Logging** | Query/Goal/RAE | 기본 Trace | **Decision Log (완전)** ⭐ |
| **LLM 통합** | Cursor 고정 | ❌ | **OrchestrationProvider** ⭐ |
| **프로덕션** | Cursor 의존 | Workflow만 | **LLM API 지원** ⭐ |

### 18.2 핵심 개선

**v7의 장점 복원**:
1. ✅ **Self-Orchestration** (동적 판단)
2. ✅ **Guardian** (목적 정렬, 감독)
3. ✅ **Logging** (완전한 추적)

**CMIS 고유 강화**:
1. ✅ **Objective-Oriented** (목표 중심 설계)
2. ✅ **Evidence-Driven Replanning** (증거 기반 재설계)
3. ✅ **LLM 추상화** (프로덕션 배포)

---

## 19. Summary

**핵심 개선**:
1. ✅ **Self-Orchestration 복원** (v7 계승)
2. ✅ **LLM 추상화** (Cursor/External/Rule)
3. ✅ **프로덕션 배포 가능** (Non-Cursor도 orchestration)

---

### Cursor Agent Interface 가치 재정의

**핵심 가치**:
1. **Self-Orchestration** ⭐ - v7 계승, 동적 workflow 선택
2. **자연어 기반** - 명령어/코드 불필요
3. **컨텍스트 유지** - 대화 흐름 기억
4. **자동 온보딩** - 환경 설정 자동화
5. **Process Guardian** - v7 Guardian 계승
6. **자가 개선** - 오류 자동 수정
7. **개발/사용 통합** - 하나의 인터페이스

**온보딩**: 별도 Setup Process (canonical_workflows 외부)

**Context Window 대응**: Full/Lite/Minimal Mode

**LLM 추상화**: 3가지 Provider (Cursor/External/Rule)

---

**작성**: 2025-12-12
**버전**: v1.1 (Self-Orchestration 추가)
**중요도**: ⭐⭐⭐ (프로덕션 배포 필수)
**다음 단계**: Milestone 0 (AdaptiveOrchestrator 구현)
