# CMIS Adaptive Execution 설계

**작성일**: 2025-12-12
**버전**: v2.0 (Zero-base 재설계)
**이전**: CMIS_Cursor_Agent_Interface_Design.md v1.1
**상태**: 설계 단계

---

## 📝 요구사항 (원문 보존)

### 1. Cursor Agent Interface 추가

**5가지 인터페이스**:
- **CLI**: Agent 자동 테스트
- **Cursor Agent** (신규): Agent와 함께 사용/디버깅/개발
- **Jupyter**: 개발자 직접 테스트
- **Web App**: 프로덕션 서비스
- **API**: 시스템 연동

**신규 사용자 온보딩**:
1. Fork repo
2. Cursor에서 질문
3. 환경 자동 확인/설정
4. CMIS 기능 활용

**고려사항**:
- 온보딩: canonical_workflows vs Setup process
- LLM Context Window 제약 대응
- Process Guardian (v7 계승)

---

### 2. 동적 재설계 (CMIS 핵심 중 핵심)

**왜 필수**:
- Evidence 수집 결과 → Structure/Opportunity/Strategy 모두 달라짐
- 계산/추정 결과 → 다음 작업 재설계
- 새로운 발견 → 능동적 판단 → 경로 변경

**예시**:
```
시장 규모 분석
→ "작고 집중도 높음" 발견
→ Gap Discovery ❌
→ Adjacent Market ✅ (재설계)
```

**원칙**: **Objective-Oriented** (목표 중심, 프로세스 자유)

---

### 3. Process 감독/Logging의 중요성

**프로세스 자유도 높음 → 감독 더욱 중요**:
- 목적 정렬 확인
- 순환 방지
- 완전한 Decision Logging (재현/투명성)

---

### 4. Non-Cursor Orchestration

Cursor 아닌 인터페이스(Web, API)에서도 동일한 orchestration 필요.
→ LLM 추상화 설계

---

## 0. Zero-base 재설계 원칙

### 0.1 설계 철학

**버릴 것**:
- v7 Multi-Agent 구조 (6 agents, complex collaboration)
- 과도한 추상화
- 구현 불가능한 이상적 설계

**취할 것**:
- **실용성**: 구현 가능하고 유지보수 쉬운 구조
- **확장성**: Interface/LLM 추가 쉬움
- **단순성**: 핵심만 남기고 제거

**핵심 질문**:
1. CMIS의 현재 구조 (9 engines, canonical_workflows)에서
2. 최소한의 추가로
3. 동적 재설계 + LLM 추상화를 어떻게 달성?

---

### 0.2 핵심 인사이트

**Orchestration = "실행 모드"일 뿐**

```
CMIS Engines (변경 없음)
    ↑
WorkflowOrchestrator (변경 없음)
    ↑
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
실행 모드 선택 (신규, 간단)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
├─ Fixed Mode: canonical_workflows 그대로
└─ Adaptive Mode: 동적 재설계
    ├─ LLM 있음: LLM이 결정
    └─ LLM 없음: 규칙 기반
```

**별도 "Layer" 불필요** → WorkflowOrchestrator 확장만으로 충분

---

## 1. 재설계안: WorkflowOrchestrator 확장

### 1.1 핵심 아이디어

> WorkflowOrchestrator에 **Execution Mode**만 추가
> 
> - Fixed Mode (기존): canonical_workflows 그대로
> - **Adaptive Mode (신규)**: 동적 재설계

**장점**:
- 기존 코드 재사용
- 최소 변경
- 명확한 책임

---

### 1.2 WorkflowOrchestrator v3.0

```python
from enum import Enum
from typing import Optional, Callable

class ExecutionMode(Enum):
    """실행 모드"""
    FIXED = "fixed"        # canonical_workflows 고정 실행
    ADAPTIVE = "adaptive"  # 동적 재설계

class DecisionMaker:
    """의사결정 인터페이스 (함수형)
    
    복잡한 Provider 클래스 대신 간단한 함수 인터페이스.
    """
    
    def __init__(self, decide_fn: Optional[Callable] = None):
        """
        Args:
            decide_fn: (query, context, result) -> decision
                       LLM 함수 또는 규칙 함수
        """
        self.decide = decide_fn or self._default_decide
    
    def _default_decide(self, query, context, result):
        """기본 결정 (규칙 기반)"""
        # 키워드 매칭
        if "규모" in query:
            return {"action": "continue", "workflow_id": "structure_analysis"}
        return {"action": "complete"}

class WorkflowOrchestrator:
    """Workflow Orchestrator v3.0
    
    v1: structure_analysis만
    v2: Generic workflow + canonical_workflows
    v3: Execution Mode + Adaptive
    
    핵심 변경:
    - execution_mode 추가 (Fixed/Adaptive)
    - decision_maker 추가 (선택적)
    - _execute_adaptive() 추가
    """
    
    def __init__(
        self,
        config: Optional[CMISConfig] = None,
        execution_mode: ExecutionMode = ExecutionMode.FIXED,
        decision_maker: Optional[DecisionMaker] = None
    ):
        """
        Args:
            config: CMIS 설정
            execution_mode: Fixed (기존) 또는 Adaptive (동적)
            decision_maker: Adaptive Mode용 의사결정 함수
        """
        # 기존 (v2)
        self.config = config or CMISConfig()
        self.world_engine = WorldEngine()
        self.pattern_engine = PatternEngineV2()
        self.value_engine = ValueEngine()
        self.workflows = self._load_canonical_workflows()
        
        # v3 추가
        self.execution_mode = execution_mode
        self.decision_maker = decision_maker or DecisionMaker()
        
        # Adaptive Mode용
        self.current_goal: Optional[str] = None
        self.execution_trace: List[Dict] = []
        self.decision_log: List[Dict] = []
    
    def run_workflow(
        self,
        workflow_id: str,
        inputs: Dict,
        goal: Optional[str] = None
    ) -> Dict:
        """Workflow 실행
        
        Args:
            workflow_id: canonical_workflow ID
            inputs: 입력 (domain_id, region 등)
            goal: 명시적 목표 (Adaptive Mode용)
        
        Returns:
            결과 + trace + decision_log
        """
        if self.execution_mode == ExecutionMode.FIXED:
            # 기존 방식 (v2)
            return self._execute_fixed(workflow_id, inputs)
        
        else:  # ADAPTIVE
            # 신규 방식 (v3)
            self.current_goal = goal or self._extract_goal(inputs.get("query", ""))
            return self._execute_adaptive(workflow_id, inputs)
    
    def _execute_fixed(self, workflow_id: str, inputs: Dict) -> Dict:
        """Fixed Mode 실행 (기존 v2 로직)
        
        canonical_workflows 정해진 steps 순차 실행.
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        
        steps = workflow.get("steps", [])
        results = {}
        
        for step in steps:
            # call: "world_engine.snapshot"
            # with: {...}
            call = step["call"]
            params = step.get("with", {})
            
            # 실행
            result = self._execute_step(call, params, inputs, results)
            results[call] = result
        
        return {
            "workflow_id": workflow_id,
            "mode": "fixed",
            "results": results
        }
    
    def _execute_adaptive(self, workflow_id: str, inputs: Dict) -> Dict:
        """Adaptive Mode 실행 (신규 v3)
        
        동적 재설계 지원:
        1. Execute step
        2. Evaluate result
        3. Decide next (continue/replan/complete)
        4. Repeat
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        
        steps = workflow.get("steps", [])
        results = {}
        
        # 초기 계획
        planned_steps = list(steps)  # 복사
        
        self._log_decision(
            "initial_plan",
            {"steps": [s["call"] for s in planned_steps]},
            f"Goal: {self.current_goal}"
        )
        
        step_idx = 0
        max_steps = len(planned_steps) * 2  # 재설계 대비 여유
        
        while step_idx < len(planned_steps) and step_idx < max_steps:
            step = planned_steps[step_idx]
            
            # 1. Execute
            call = step["call"]
            params = step.get("with", {})
            result = self._execute_step(call, params, inputs, results)
            results[call] = result
            
            self.execution_trace.append({
                "step_idx": step_idx,
                "call": call,
                "result_summary": self._summarize_result(result)
            })
            
            # 2. Evaluate (중간 평가)
            evaluation = self._evaluate_step_result(result, self.current_goal)
            
            # 3. Decide next (decision_maker에 위임)
            decision = self.decision_maker.decide(
                query=inputs.get("query", ""),
                context={
                    "goal": self.current_goal,
                    "current_step": call,
                    "evaluation": evaluation,
                    "results_so_far": results
                },
                result=result
            )
            
            self._log_decision(
                "step_decision",
                decision,
                f"Step {step_idx}: {decision['action']}"
            )
            
            # 4. Action
            if decision["action"] == "complete":
                # 조기 완료
                break
            
            elif decision["action"] == "replan":
                # 재설계!
                new_steps = decision.get("new_steps", [])
                
                self._log_decision(
                    "replanning",
                    {
                        "trigger": decision.get("trigger"),
                        "old_steps": [s["call"] for s in planned_steps[step_idx+1:]],
                        "new_steps": new_steps
                    },
                    f"경로 재설계: {decision.get('reasoning')}"
                )
                
                # 계획 변경
                planned_steps = planned_steps[:step_idx+1] + self._parse_new_steps(new_steps)
            
            elif decision["action"] == "retry":
                # 재시도 (Evidence 더 수집 등)
                # step_idx 유지 (다음 루프에서 재실행)
                continue
            
            else:  # continue
                # 다음 step
                step_idx += 1
        
        return {
            "workflow_id": workflow_id,
            "mode": "adaptive",
            "goal": self.current_goal,
            "results": results,
            "execution_trace": self.execution_trace,
            "decision_log": self.decision_log,
            "replanned": any(d["decision_type"] == "replanning" for d in self.decision_log)
        }
    
    def _evaluate_step_result(self, result: Dict, goal: str) -> Dict:
        """Step 결과 평가
        
        Returns:
            {
                "quality": 0.75,
                "completeness": "partial",
                "sufficient_for_goal": False,
                "new_insights": [...]
            }
        """
        # Evidence Quality
        quality = result.get("quality", {}).get("literal_ratio", 0)
        
        # Completeness
        metrics = result.get("metrics", [])
        completeness = "full" if len(metrics) >= 5 else "partial"
        
        # New Insights
        new_insights = []
        for metric in metrics:
            value = metric.get("point_estimate")
            metric_id = metric.get("metric_id")
            
            # 패턴 감지
            if metric_id == "MET-HHI_revenue" and value and value > 2500:
                new_insights.append("market_concentration_high")
            
            if metric_id == "MET-TAM" and value and value < 1e11:
                new_insights.append("market_size_smaller_than_expected")
        
        # Goal 충족 여부
        sufficient = quality > 0.6 and completeness == "full"
        
        return {
            "quality": quality,
            "completeness": completeness,
            "sufficient_for_goal": sufficient,
            "new_insights": new_insights
        }
    
    def _log_decision(self, decision_type: str, data: Dict, summary: str):
        """Decision Logging"""
        self.decision_log.append({
            "timestamp": datetime.now().isoformat(),
            "decision_type": decision_type,
            "data": data,
            "summary": summary,
            "goal": self.current_goal
        })
    
    def _extract_goal(self, query: str) -> str:
        """Query → Goal 추출"""
        if "규모" in query:
            return "시장 규모 파악"
        elif "기회" in query:
            return "기회 발굴"
        elif "전략" in query:
            return "전략 수립"
        return "시장 이해"
```

**핵심**:
- WorkflowOrchestrator **확장**만으로 Adaptive Mode 추가
- 별도 AdaptiveOrchestrator 클래스 불필요
- decision_maker는 **함수형 인터페이스** (간단)

---

## 2. DecisionMaker 구현 (3가지)

### 2.1 함수형 인터페이스

```python
DecisionMaker = Callable[
    [str, Dict, Dict],  # (query, context, result)
    Dict[str, Any]       # decision
]

# 시그니처:
def decide(query: str, context: Dict, result: Dict) -> Dict:
    """
    Returns:
        {
            "action": "continue" | "replan" | "complete" | "retry",
            "reasoning": "...",
            "new_steps": [...] (replan 시)
        }
    """
    pass
```

**장점**:
- 복잡한 Provider 클래스 불필요
- 간단한 함수만 전달
- 테스트 쉬움

---

### 2.2 CursorDecisionMaker

```python
def cursor_decision_maker(query: str, context: Dict, result: Dict) -> Dict:
    """Cursor Agent 기반 의사결정
    
    Cursor가 이미 전체 컨텍스트를 가지고 있으므로,
    자연스럽게 판단하도록 .cursorrules에 가이드만 제공.
    
    실제로는 규칙 기반 + Agent 판단 조합.
    """
    evaluation = context.get("evaluation", {})
    
    # 1. 충분하면 완료
    if evaluation.get("sufficient_for_goal"):
        return {"action": "complete"}
    
    # 2. 새 발견 → 재설계
    new_insights = evaluation.get("new_insights", [])
    
    if "market_concentration_high" in new_insights:
        return {
            "action": "replan",
            "reasoning": "시장 집중도 높음 → Gap 어려움",
            "new_steps": [
                {"call": "pattern_engine.discover_adjacent_markets"},
                {"call": "strategy_engine.search_strategies"}
            ]
        }
    
    if "market_size_smaller_than_expected" in new_insights:
        return {
            "action": "replan",
            "reasoning": "시장 작음 → Niche 전략",
            "new_steps": [
                {"call": "pattern_engine.discover_niche_segments"}
            ]
        }
    
    # 3. Evidence 부족 → 재시도
    if evaluation.get("quality", 0) < 0.3:
        return {
            "action": "retry",
            "reasoning": "Evidence 부족, 재수집"
        }
    
    # 4. 기본: 계속
    return {"action": "continue"}
```

---

### 2.3 ExternalLLMDecisionMaker

```python
def create_llm_decision_maker(llm_client, model="gpt-4") -> DecisionMaker:
    """외부 LLM 기반 DecisionMaker 생성
    
    Web App, API에서 사용.
    """
    
    def llm_decide(query: str, context: Dict, result: Dict) -> Dict:
        """LLM에게 결정 요청"""
        
        evaluation = context.get("evaluation", {})
        
        prompt = f"""
        목표: {context.get("goal")}
        현재 단계: {context.get("current_step")}
        
        결과 평가:
        - Quality: {evaluation.get("quality", 0):.1%}
        - Completeness: {evaluation.get("completeness")}
        - New Insights: {evaluation.get("new_insights", [])}
        
        다음 행동을 결정하세요:
        
        Options:
        1. "continue" - 다음 step 계속
        2. "complete" - 목표 달성, 완료
        3. "replan" - 경로 재설계 (new_steps 제공)
        4. "retry" - 현재 step 재시도
        
        JSON 형식:
        {{
            "action": "continue",
            "reasoning": "..."
        }}
        
        재설계 시:
        {{
            "action": "replan",
            "reasoning": "...",
            "new_steps": [
                {{"call": "pattern_engine.discover_adjacent_markets"}},
                {{"call": "strategy_engine.search_strategies"}}
            ]
        }}
        """
        
        response = llm_client.complete(prompt, model=model, temperature=0.3)
        
        import json
        return json.loads(response)
    
    return llm_decide

# 사용:
from openai import OpenAI

llm = OpenAI(api_key="...")
decision_maker = DecisionMaker(
    decide_fn=create_llm_decision_maker(llm, "gpt-4")
)

orchestrator = WorkflowOrchestrator(
    execution_mode=ExecutionMode.ADAPTIVE,
    decision_maker=decision_maker
)
```

---

### 2.4 RuleBasedDecisionMaker

```python
def rule_based_decision_maker(query: str, context: Dict, result: Dict) -> Dict:
    """규칙 기반 의사결정 (LLM 없음)
    
    CLI에서 사용.
    """
    evaluation = context.get("evaluation", {})
    
    # 간단한 규칙
    if evaluation.get("sufficient_for_goal"):
        return {"action": "complete"}
    
    if evaluation.get("quality", 0) < 0.3:
        return {"action": "retry"}
    
    return {"action": "continue"}

# CLI에서:
orchestrator = WorkflowOrchestrator(
    execution_mode=ExecutionMode.FIXED,  # 고정 모드
    decision_maker=None  # 불필요
)
```

---

## 3. Interface별 구성

### 3.1 CLI (기존 유지)

```python
# cmis_cli/commands/structure_analysis.py

orchestrator = WorkflowOrchestrator(
    execution_mode=ExecutionMode.FIXED  # 고정
)

result = orchestrator.run_workflow(
    workflow_id="structure_analysis",
    inputs={"domain_id": "...", "region": "KR"}
)
```

**특징**:
- Fixed Mode
- canonical_workflows 그대로
- 변경 없음 (하위 호환)

---

### 3.2 Cursor Agent (신규)

```python
# cmis_cursor/interface.py

class CursorInterface:
    """Cursor Agent Interface (간소화)"""
    
    def __init__(self):
        self.orchestrator = WorkflowOrchestrator(
            execution_mode=ExecutionMode.ADAPTIVE,
            decision_maker=DecisionMaker(cursor_decision_maker)
        )
        
        self.onboarding = OnboardingWorkflow()
    
    def query(self, question: str) -> Dict:
        """자연어 질문 처리"""
        
        # 1. 온보딩 확인
        if not self.onboarding.is_ready():
            return self.onboarding.run()
        
        # 2. Workflow 선택 (간단한 규칙)
        workflow_id = self._select_workflow(question)
        
        # 3. Adaptive 실행
        result = self.orchestrator.run_workflow(
            workflow_id=workflow_id,
            inputs={"query": question},
            goal=self._extract_goal(question)
        )
        
        return result
    
    def _select_workflow(self, question: str) -> str:
        """간단한 workflow 선택"""
        if "기회" in question:
            return "opportunity_discovery"
        elif "전략" in question:
            return "strategy_design"
        return "structure_analysis"
```

**특징**:
- Adaptive Mode
- Cursor Agent가 decision_maker
- 동적 재설계

---

### 3.3 Web App (프로덕션)

```python
# cmis_web/api.py (FastAPI)

from fastapi import FastAPI
from openai import OpenAI

app = FastAPI()

# LLM Client
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# DecisionMaker (외부 LLM)
decision_maker = DecisionMaker(
    decide_fn=create_llm_decision_maker(llm, "gpt-4")
)

# Orchestrator (Adaptive)
orchestrator = WorkflowOrchestrator(
    execution_mode=ExecutionMode.ADAPTIVE,
    decision_maker=decision_maker
)

@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    """시장 분석 API"""
    
    result = orchestrator.run_workflow(
        workflow_id="structure_analysis",
        inputs={"query": request.query, "region": request.region},
        goal=request.query
    )
    
    return {
        "answer": result["results"],
        "decision_log": result["decision_log"],
        "replanned": result.get("replanned", False)
    }
```

**특징**:
- Adaptive Mode
- External LLM (GPT-4 API)
- 프로덕션 배포 가능

---

## 4. Guardian 통합 (내장)

### 4.1 WorkflowOrchestrator에 Guardian 내장

**별도 Guardian 클래스 불필요** → Orchestrator 메서드로 충분

```python
class WorkflowOrchestrator:
    # ... (기존)
    
    # ========================================
    # Guardian 기능 (내장)
    # ========================================
    
    def _check_goal_alignment(self) -> bool:
        """목표 정렬 확인"""
        if len(self.execution_trace) > self.max_steps:
            self._emit_warning("탐색 깊이 초과")
            return False
        return True
    
    def _check_loop(self, call: str) -> bool:
        """순환 감지"""
        recent_calls = [t["call"] for t in self.execution_trace[-3:]]
        if recent_calls.count(call) >= 2:
            self._emit_warning(f"순환 감지: {call} 반복")
            return True
        return False
    
    def _check_quality(self, result: Dict) -> bool:
        """품질 게이트"""
        quality = result.get("quality", {}).get("literal_ratio", 0)
        if quality < self.min_quality:
            self._emit_warning(f"품질 부족: {quality:.1%}")
            return False
        return True
    
    def _emit_warning(self, message: str):
        """경고 발생"""
        print(f"⚠️ [Guardian] {message}")
        self.decision_log.append({
            "decision_type": "guardian_warning",
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
```

**장점**:
- 복잡한 Guardian 클래스 불필요
- Orchestrator가 자체 감독
- 코드 간결

---

## 5. 온보딩 (별도 프로세스)

### 5.1 설계 결정

**결론**: **Setup Process** (canonical_workflows 외부)

**이유**:
- 1회성 (환경 설정)
- CMIS 워크플로우 이전 단계
- 모든 인터페이스 공통

---

### 5.2 OnboardingWorkflow (단순화)

```python
class OnboardingWorkflow:
    """온보딩 (환경 설정)
    
    canonical_workflows와 무관.
    모든 인터페이스에서 공통 사용.
    """
    
    def is_ready(self) -> bool:
        """환경 준비 완료 여부"""
        checks = [
            self._check_python(),
            self._check_dependencies(),
            self._check_env_vars()
        ]
        return all(checks)
    
    def run(self) -> Dict:
        """온보딩 실행"""
        if self.is_ready():
            return {"status": "ready"}
        
        # 자동 수정 시도
        issues = []
        
        if not self._check_dependencies():
            self._install_dependencies()
            issues.append("dependencies_installed")
        
        if not self._check_env_vars():
            issues.append("env_vars_needed")
            # .env 예시 제공
        
        return {
            "status": "needs_setup" if issues else "ready",
            "issues": issues
        }
```

---

## 6. Context Window 대응 (단순화)

### 6.1 설계 결정

**복잡한 Mode 전환 불필요** → Document Summarization만

```python
class ContextAwareDocLoader:
    """Context Window에 맞춘 문서 요약
    
    Full/Lite/Minimal Mode 대신,
    동적으로 필요한 부분만 로딩.
    """
    
    def load_for_workflow(
        self,
        workflow_id: str,
        max_tokens: int = 50000
    ) -> str:
        """Workflow 관련 문서만 로딩
        
        Args:
            workflow_id: "structure_analysis"
            max_tokens: Context Window 여유
        
        Returns:
            요약 문서
        """
        if workflow_id == "structure_analysis":
            return """
            structure_analysis:
            - world_engine.snapshot() → R-Graph
            - pattern_engine.match_patterns()
            - value_engine.evaluate_metrics([TAM, SAM, SOM, ...])
            """
        
        # ...
```

**사용**:
```python
# Cursor/.cursorrules에 동적 삽입
doc = doc_loader.load_for_workflow("structure_analysis")
# Agent가 참고
```

---

## 7. 인터페이스 구현 전략

### 7.1 Interface별 구성 (단순화)

| Interface | Mode | DecisionMaker | 구현 난이도 |
|-----------|------|---------------|----------|
| **CLI** | Fixed | None | ⭐ (완료) |
| **Cursor** | Adaptive | cursor_decision_maker | ⭐⭐ |
| **Jupyter** | Fixed 또는 Adaptive | 선택 | ⭐⭐ |
| **Web** | Adaptive | create_llm_decision_maker(GPT-4) | ⭐⭐⭐ |
| **API** | Adaptive | 클라이언트 제공 | ⭐⭐⭐ |

**구현 순서**:
1. WorkflowOrchestrator v3.0 (Adaptive Mode 추가) - 1주
2. Cursor Interface (cursor_decision_maker) - 3일
3. Web App (External LLM) - 1주
4. API (External LLM) - 3일

**총 3주** (기존 6-7주에서 절반 단축)

---

## 8. 파일 구조 (단순화)

```
cmis_core/
├─ workflow.py (확장) ← WorkflowOrchestrator v3.0
│   ├─ ExecutionMode (Fixed/Adaptive)
│   ├─ _execute_adaptive()
│   └─ Guardian 메서드 (내장)
│
└─ decision_makers.py (신규) ← 200줄
    ├─ DecisionMaker (함수형 인터페이스)
    ├─ cursor_decision_maker()
    ├─ create_llm_decision_maker()
    └─ rule_based_decision_maker()

cmis_cursor/ (신규)
├─ __init__.py
├─ interface.py (100줄) ← CursorInterface
└─ onboarding.py (150줄) ← OnboardingWorkflow

cmis_web/ (미래)
├─ app.py (FastAPI)
└─ ...

.cursorrules (확장)
└─ CMIS Adaptive Execution 가이드
```

**총 파일**: 5개 (기존 20+개에서 대폭 축소)

---

## 9. 동적 재설계 예시 (구체적)

### 9.1 시나리오: 시장 포화 발견

```
[Query] "한국 성인 어학교육 시장 진입 전략"

[Goal] "시장 분석 + 진입 전략 수립"

[초기 Plan]
Steps: [structure_analysis, opportunity_discovery, strategy_design]

[Execute] Step 1: structure_analysis
  Result:
    - TAM: 1.5조 (예상: 3조)
    - HHI: 3500 (매우 높음)
    - Top3: 85%
  
  Evaluation:
    - quality: 0.75 ✅
    - new_insights: ["market_small", "concentration_high"]
  
  [DecisionMaker 호출]
  decision_maker(
      query="...",
      context={"goal": "...", "evaluation": {...}},
      result={...}
  )
  
  [Decision]
  {
      "action": "replan",
      "reasoning": "시장 작고 집중 → Gap 어려움 → Adjacent 탐색",
      "new_steps": [
          {"call": "pattern_engine.discover_adjacent_markets"},
          {"call": "strategy_engine.search_strategies", "with": {"focus": "pivot"}}
      ]
  }
  
  [Replanning Log]
  {
      "trigger": "market_saturation",
      "old_plan": ["opportunity_discovery", "strategy_design"],
      "new_plan": ["discover_adjacent", "strategy_pivot"]
  }

[Execute] Step 2: discover_adjacent_markets (재설계된 경로)
  Result: "기업 교육 시장 (B2B) 발견"

[Execute] Step 3: strategy_design (pivot)
  Result: "B2B Pivot 전략"

[Complete]
  Decision Log: 5개 결정
  Replanning: 1회
  최종 경로: structure → adjacent → strategy (초기와 다름)
```

**핵심**:
- Evidence 결과 → 재평가
- 새 발견 → 재설계
- 완전한 Logging

---

## 10. cmis.yaml 업데이트 (단순화)

```yaml
cmis:
  meta:
    version: "3.6.0"
    new_features:
      - "Adaptive Execution Mode (동적 재설계)"
      - "Objective-Oriented Architecture"
      - "DecisionMaker 함수형 인터페이스"

  core_principles:
    - "Objective-Oriented (목표 중심, 프로세스 동적)"
    - "Evidence-Driven Replanning (증거 기반 재설계)"
    - "Decision Logging (완전한 투명성)"
  
  planes:
    interaction_plane:
      interfaces:
        - id: "cursor_agent"
          type: "conversational_ide"
          execution_mode: "adaptive"
          decision_maker: "cursor_decision_maker"
    
    cognition_plane:
      engines:
        workflow_orchestrator:
          version: "v3.0"
          new_features:
            - "ExecutionMode (Fixed/Adaptive)"
            - "DecisionMaker 인터페이스"
            - "_execute_adaptive() 메서드"
            - "Guardian 기능 내장"
          
          execution_modes:
            - id: "fixed"
              description: "canonical_workflows 고정 실행 (기존)"
              use_case: "CLI, 단순 배치"
            
            - id: "adaptive"
              description: "동적 재설계 (Objective-Oriented)"
              use_case: "Cursor, Web, API (LLM 활용)"
              requires: "DecisionMaker 함수"
          
          decision_maker_interface:
            signature: "(query, context, result) -> decision"
            implementations:
              - "cursor_decision_maker (Cursor Agent)"
              - "create_llm_decision_maker(llm) (External LLM)"
              - "rule_based_decision_maker (Fallback)"
```

---

## 11. 구현 계획 (단순화)

### Phase 1: WorkflowOrchestrator v3.0 (1주)

**작업**:
1. `cmis_core/workflow.py` 확장 (+300줄)
   - ExecutionMode Enum
   - _execute_adaptive() 메서드
   - _evaluate_step_result()
   - Guardian 메서드 (내장)

2. `cmis_core/decision_makers.py` (신규, 200줄)
   - DecisionMaker 함수형 인터페이스
   - cursor_decision_maker()
   - create_llm_decision_maker()
   - rule_based_decision_maker()

3. 테스트 (15개)

**예상**: 1주

---

### Phase 2: Cursor Interface (3일)

**작업**:
1. `cmis_cursor/interface.py` (100줄)
2. `cmis_cursor/onboarding.py` (150줄)
3. `.cursorrules` 확장

**예상**: 3일

---

### Phase 3: Web/API (1주)

**작업**:
1. `cmis_web/app.py` (FastAPI)
2. External LLM 통합
3. 프로덕션 테스트

**예상**: 1주

---

**총 3주** (기존 6-7주 → 절반)

---

## 12. Summary

### Zero-base 재설계 결과

**복잡한 구조 제거**:
- ❌ 별도 AdaptiveOrchestrator 클래스
- ❌ 복잡한 Provider 클래스 계층
- ❌ 별도 Guardian 클래스
- ❌ 별도 Orchestration Layer (Plane)

**단순하고 실용적인 구조**:
- ✅ WorkflowOrchestrator **확장** (ExecutionMode 추가)
- ✅ DecisionMaker **함수형 인터페이스**
- ✅ Guardian **내장** (메서드)
- ✅ Cognition Plane 내 (별도 Layer 불필요)

**핵심 가치 유지**:
- ✅ Objective-Oriented (목표 중심)
- ✅ 동적 재설계 (Evidence 기반)
- ✅ LLM 추상화 (Cursor/External/Rule)
- ✅ 프로덕션 배포 (Non-Cursor도 가능)
- ✅ 완전한 Logging

**구현 간소화**:
- 6-7주 → **3주**
- 20+ 파일 → **5개 파일**
- 복잡한 추상화 → **함수형 인터페이스**

---

**작성**: 2025-12-12
**버전**: v2.0 (Zero-base)
**우선순위**: ⭐⭐⭐ (CMIS 핵심, 프로덕션 필수)
**다음**: WorkflowOrchestrator v3.0 구현
