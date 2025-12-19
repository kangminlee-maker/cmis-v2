# StrategyEngine 설계 (Enhanced)

**작성일**: 2025-12-11
**최종 업데이트**: 2025-12-14
**버전**: v1.1 (피드백 반영)
**기반**: Strategy_Engine_Design.md + 피드백
**상태**: 설계 완료
**비고**: (v3.6 문서 정리) Greenfield/Brownfield/Constraints 보조 문서는 본 문서로 통합하고 deprecated로 이동

---

## Executive Summary

이 문서는 StrategyEngine 설계를 cmis.yaml과 완전히 정렬한 Enhanced 버전입니다.

**주요 개선**:
1. **API 레벨 분리** - 공식 API vs 내부 Core 함수
2. **D-Graph 중심 설계** - decision_graph가 진실의 원천
3. **ValueEngine ROI 연동** - ValueEngine이 ROI 계산 담당
4. **Constraints 스키마 정렬** - focal_actor_context_store 일치
5. **PolicyEngine 통합** - policy_ref 인자 및 모드 반영
6. **Preference Profile 정렬** - cmis.yaml 스키마 사용

---

## 1. StrategyEngine 아키텍처 (Enhanced)

### 1.1 레이어 분리

```
┌──────────────────────────────────────────────────────────┐
│          Public API Layer (cmis.yaml 1:1 대응)           │
│  search_strategies_api(goal_id, constraints, context_id) │
│  evaluate_portfolio_api(strategy_ids, policy_ref, ...)   │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│           Orchestration Layer                             │
│  - D-Graph/FocalActorContext 로딩                           │
│  - World/Pattern/Value Engine 호출                       │
│  - Core 함수 호출                                         │
│  - D-Graph 저장                                          │
└──────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Strategy   │  │   Strategy   │  │  Portfolio   │
│   Generator  │  │  Evaluator   │  │  Optimizer   │
│   (Core)     │  │   (Core)     │  │   (Core)     │
└──────────────┘  └──────────────┘  └──────────────┘
```

**설계 원칙**:
- Public API: canonical_workflows가 호출
- Orchestration: 엔진 간 조율
- Core: 순수 로직 (테스트 용이)

---

## 2. Public API Layer

### 2.1 search_strategies_api() (cmis.yaml 대응)

**cmis.yaml 정의**:
```yaml
strategy_engine:
  api:
    - name: search_strategies
      input:
        goal_id: "goal_id"
        constraints: "dict"
        focal_actor_context_id: "focal_actor_context_id (optional)"
      output:
        strategy_set_ref: "strategy_set"
```

**구현**:
```python
class StrategyEngine:
    """Strategy Engine - D-Graph 중심 전략 설계 엔진"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent

        # Engines
        self.world_engine = WorldEngine(project_root)
        self.pattern_engine_v2 = PatternEngineV2()
        self.value_engine = ValueEngine()

        # D-Graph (decision_graph)
        self.d_graph = InMemoryGraph()  # Phase 1: 인메모리

        # Core 컴포넌트
        self.generator = StrategyGenerator(self.pattern_engine_v2)
        self.evaluator = StrategyEvaluator(self.value_engine)
        self.optimizer = PortfolioOptimizer()

    def search_strategies_api(
        self,
        goal_id: str,
        constraints: Dict[str, Any],
        focal_actor_context_id: Optional[str] = None
    ) -> str:
        """
        Public API (cmis.yaml 대응)

        프로세스:
        1. D-Graph에서 Goal 로딩
        2. FocalActorContext 로딩 (있으면)
        3. World/Pattern Engine 호출
        4. Core search_strategies() 호출
        5. Strategy 노드를 D-Graph에 저장
        6. strategy_set_ref 반환

        Args:
            goal_id: Goal ID (D-Graph에서 조회)
            constraints: 추가 제약 (Greenfield에서 사용)
            focal_actor_context_id: FocalActorContext ID (Brownfield)

        Returns:
            strategy_set_ref: "STSET-{timestamp}"
        """
        # 1. Goal 로딩 (D-Graph)
        goal = self._load_goal_from_d_graph(goal_id)

        # 2. FocalActorContext 로딩 (있으면)
        project_context = None
        if focal_actor_context_id:
            project_context = self._load_project_context(focal_actor_context_id)

        # 3. World/Pattern Engine 호출
        # Goal의 scope에서 domain_id, region 추출
        scope = self._extract_scope_from_goal(goal)

        snapshot = self.world_engine.snapshot(
            domain_id=scope["domain_id"],
            region=scope["region"],
            focal_actor_context_id=focal_actor_context_id
        )

        matches = self.pattern_engine_v2.match_patterns(
            snapshot.graph,
            focal_actor_context_id=focal_actor_context_id
        )

        gaps = self.pattern_engine_v2.discover_gaps(
            snapshot.graph,
            focal_actor_context_id=focal_actor_context_id,
            precomputed_matches=matches
        )

        # 4. Core 함수 호출
        greenfield_constraints = constraints if not project_context else None

        strategies = self.search_strategies_core(
            goal=goal,
            reality_snapshot=snapshot,
            pattern_matches=matches,
            gaps=gaps,
            project_context=project_context,
            greenfield_constraints=greenfield_constraints
        )

        # 5. D-Graph에 저장
        strategy_set_ref = self._save_strategies_to_d_graph(
            strategies,
            goal_id,
            focal_actor_context_id
        )

        return strategy_set_ref
```

---

### 2.2 evaluate_portfolio_api() (cmis.yaml 대응)

**cmis.yaml 정의**:
```yaml
strategy_engine:
  api:
    - name: evaluate_portfolio
      input:
        strategy_ids: "list[strategy_id]"
        policy_ref: "policy_ref"
        focal_actor_context_id: "focal_actor_context_id (optional)"
      output:
        portfolio_eval_ref: "portfolio_evaluation"
```

**구현**:
```python
def evaluate_portfolio_api(
    self,
    strategy_ids: List[str],
    policy_ref: str = "decision_balanced",
    focal_actor_context_id: Optional[str] = None
) -> str:
    """
    Public API (cmis.yaml 대응)

    프로세스:
    1. D-Graph에서 Strategy 노드 로딩
    2. FocalActorContext 로딩 (있으면)
    3. policy_ref 해석
    4. Core evaluate_portfolio() 호출
    5. PortfolioEvaluation을 D-Graph에 저장
    6. portfolio_eval_ref 반환

    Args:
        strategy_ids: Strategy ID 리스트
        policy_ref: Policy mode
        focal_actor_context_id: FocalActorContext ID

    Returns:
        portfolio_eval_ref: "PEVAL-{timestamp}"
    """
    # 1. Strategy 로딩 (D-Graph)
    strategies = [
        self._load_strategy_from_d_graph(sid)
        for sid in strategy_ids
    ]

    # 2. FocalActorContext 로딩
    project_context = None
    if focal_actor_context_id:
        project_context = self._load_project_context(focal_actor_context_id)

    # 3. Policy 해석
    policy_params = self._resolve_policy(policy_ref)

    # 4. Core 함수
    portfolio_eval = self.evaluate_portfolio_core(
        strategies=strategies,
        project_context=project_context,
        policy_params=policy_params
    )

    # 5. D-Graph 저장
    portfolio_eval_ref = self._save_portfolio_eval_to_d_graph(
        portfolio_eval,
        strategy_ids,
        focal_actor_context_id
    )

    return portfolio_eval_ref
```

---

## 3. Core Functions (내부 로직)

### 3.1 search_strategies_core()

```python
def search_strategies_core(
    self,
    goal: Goal,
    reality_snapshot: RealityGraphSnapshot,
    pattern_matches: List[PatternMatch],
    gaps: List[GapCandidate],
    focal_actor_context_id: Optional[FocalActorContext] = None,
    greenfield_constraints: Optional[Dict[str, Any]] = None
) -> List[Strategy]:
    """
    Core 전략 탐색 (내부 함수)

    이 함수는 Public API에서만 호출됨
    테스트/실험 시 직접 호출 가능
    """
    # 1. StrategyGenerator로 후보 생성
    strategies = self.generator.generate(
        pattern_matches=pattern_matches,
        gaps=gaps,
        goal=goal
    )

    # 2. Constraint 필터링
    if focal_actor_context_id:
        # Brownfield
        strategies = self._filter_by_brownfield_constraints(
            strategies,
            project_context.constraints_profile
        )
    elif greenfield_constraints:
        # Greenfield
        strategies = self._filter_by_greenfield_constraints(
            strategies,
            greenfield_constraints
        )

    # 3. StrategyEvaluator로 평가
    for strategy in strategies:
        # Execution Fit
        if focal_actor_context_id:
            strategy.execution_fit_score = self.evaluator.calculate_execution_fit(
                strategy,
                project_context
            )
        else:
            strategy.execution_fit_score = None

        # ROI/Outcomes (ValueEngine 연동)
        strategy.expected_outcomes = self.evaluator.predict_outcomes(
            strategy,
            baseline_state=project_context.baseline_state if project_context else {},
            value_engine=self.value_engine
        )

        # Risk
        strategy.risks = self.evaluator.assess_risks(
            strategy,
            project_context,
            pattern_matches
        )

    # 4. Preference 반영 (Brownfield)
    if project_context and project_context.preference_profile:
        for strategy in strategies:
            strategy.adjusted_score = self._adjust_by_preferences(
                strategy,
                project_context.preference_profile
            )

    # 5. 정렬
    if focal_actor_context_id:
        # Brownfield: Execution Fit × adjusted_score
        strategies.sort(
            key=lambda s: (s.execution_fit_score or 0) * (s.adjusted_score or s.execution_fit_score or 0),
            reverse=True
        )
    else:
        # Greenfield: ROI
        strategies.sort(
            key=lambda s: s.expected_outcomes.get("roi", 0),
            reverse=True
        )

    return strategies
```

---

## 4. D-Graph 통합

### 4.1 Strategy → D-Graph 매핑

**Strategy 데이터 클래스 (Python)**:
```python
@dataclass
class Strategy:
    strategy_id: str
    name: str
    description: str
    pattern_composition: List[str]
    action_set: List[Dict]
    expected_outcomes: Dict
    execution_fit_score: Optional[float]
    risks: List[Dict]
```

**D-Graph 저장 (분리)**:

**1) strategy 노드** (cmis.yaml 스키마):
```python
d_graph.upsert_node(
    strategy_id,
    "strategy",
    data={
        "name": strategy.name,
        "description": strategy.description
    }
)
```

**2) strategy_uses_pattern edges**:
```python
for pattern_id in strategy.pattern_composition:
    d_graph.add_edge(
        "strategy_uses_pattern",
        source=strategy_id,
        target=pattern_id  # P-Graph의 pattern 노드
    )
```

**3) strategy_targets_goal edge**:
```python
d_graph.add_edge(
    "strategy_targets_goal",
    source=strategy_id,
    target=goal_id
)
```

**4) Metadata/Outcomes** (별도 저장):
```python
# Option A: strategy 노드의 traits/metadata
d_graph.nodes[strategy_id].data["traits"] = {
    "execution_fit_score": strategy.execution_fit_score
}

d_graph.nodes[strategy_id].data["metadata"] = {
    "expected_outcomes": strategy.expected_outcomes,
    "risks": strategy.risks,
    "action_set": strategy.action_set  # 또는 별도 action 노드로
}

# Option B: ValueRecord로 저장 (ValueEngine 연동)
for metric_id, value in strategy.expected_outcomes.items():
    value_record = ValueRecord(
        metric_id=metric_id,
        context={"strategy_id": strategy_id, "horizon": "3y"},
        point_estimate=value,
        quality={"method": "pattern_benchmark_projection", "confidence": 0.6}
    )
    # value_store에 저장
```

### 4.2 매핑 테이블

| Strategy 필드 | D-Graph 저장 위치 | 타입 |
|--------------|------------------|------|
| strategy_id, name, description | strategy 노드 | 노드 필드 |
| pattern_composition | strategy_uses_pattern edge | 엣지 (다수) |
| action_set | strategy 노드 metadata 또는 action 노드 | metadata/노드 |
| expected_outcomes | ValueRecord (value_store) | ValueEngine 연동 |
| execution_fit_score | strategy 노드 traits | traits |
| risks | strategy 노드 metadata | metadata |
| goal 연결 | strategy_targets_goal edge | 엣지 |

---

## 5. ValueEngine 연동 (ROI 계산)

### 5.1 설계 원칙

**StrategyEngine 역할**:
- Strategy 정의 (Pattern 조합, Action)
- Execution Fit 평가
- Risk 평가

**ValueEngine 역할**:
- ROI/Outcomes Metric 계산
- Pattern Benchmark → Prior
- Simulation (What-if)

**연동**:
```python
class StrategyEvaluator:
    def __init__(self, value_engine: ValueEngine):
        self.value_engine = value_engine

    def predict_outcomes(
        self,
        strategy: Strategy,
        baseline_state: Dict,
        value_engine: ValueEngine
    ) -> Dict[str, Any]:
        """
        ValueEngine 연동 ROI 예측

        프로세스:
        1. Pattern Benchmark → ValueEngine Prior
        2. ValueEngine.evaluate_metrics() 호출
        3. Simulation (baseline → horizon)
        """
        # 1. Pattern Benchmark 추출
        pattern_priors = {}

        for pattern_id in strategy.pattern_composition:
            pattern = pattern_library.get(pattern_id)

            for metric_id in pattern.benchmark_metrics:
                bounds = pattern.quantitative_bounds.get(metric_id)
                if bounds:
                    # ValueEngine Prior 형식으로 변환
                    pattern_priors[metric_id] = {
                        "distribution": {
                            "min": bounds["min"],
                            "max": bounds["max"],
                            "typical": bounds["typical"]
                        },
                        "method": "pattern_benchmark",
                        "confidence": 0.6
                    }

        # 2. ValueEngine 호출 (Phase 2)
        # value_records = value_engine.evaluate_metrics(
        #     graph=reality_snapshot.graph,
        #     metric_requests=[...],
        #     priors=pattern_priors  # Pattern Prior 전달
        # )

        # Phase 1: 간단한 계산
        outcomes = self._simple_roi_calculation(
            strategy,
            baseline_state,
            pattern_priors
        )

        # Lineage 추가
        outcomes["lineage"] = {
            "method": "pattern_benchmark_projection",
            "pattern_ids": strategy.pattern_composition,
            "confidence": 0.6,
            "engine": "strategy_engine_phase1"
        }

        return outcomes
```

---

## 6. Constraints 스키마 정렬

### 6.1 focal_actor_context_store 기준

**cmis.yaml 스키마**:
```yaml
focal_actor_context_store:
  constraints_profile:
    hard_constraints:
      - type: "financial|temporal|regulatory|organizational|technical"
        dimension: "budget|timeline|..."  # 추가
        threshold: <value>
        description: "..."

    soft_preferences:
      - dimension: "risk_appetite|prefer_patterns|..."
        value: <any>
        weight: 0.0~1.0
```

**StrategyEngine 해석**:
```python
def _filter_by_brownfield_constraints(
    strategies: List[Strategy],
    constraints_profile: Dict
) -> List[Strategy]:
    """
    focal_actor_context_store 스키마 기준 필터링
    """
    filtered = []
    hard_constraints = constraints_profile.get("hard_constraints", [])

    for strategy in strategies:
        violates = False

        for constraint in hard_constraints:
            ctype = constraint["type"]
            dimension = constraint.get("dimension", "")
            threshold = constraint.get("threshold")

            # financial + budget
            if ctype == "financial" and "budget" in dimension:
                required = strategy.expected_outcomes.get("required_investment", 0)
                if required > threshold:
                    violates = True
                    break

            # temporal + timeline
            elif ctype == "temporal" and "timeline" in dimension:
                required = strategy.expected_outcomes.get("required_timeline_months", 36)
                if required > threshold:
                    violates = True
                    break

            # organizational + team_size
            elif ctype == "organizational" and "team" in dimension:
                required = strategy.expected_outcomes.get("required_team_size", 10)
                if required > threshold:
                    violates = True
                    break

            # ... 기타

        if not violates:
            filtered.append(strategy)

    return filtered
```

### 6.2 Greenfield Constraints (경량)

**구조**:
```python
greenfield_constraints = {
    "budget": 1000000000,  # 단순 숫자
    "timeline_months": 24,
    "team_size_range": [10, 50]
}
```

**focal_actor_context_store 형식으로 변환** (내부):
```python
def _normalize_greenfield_constraints(constraints: Dict) -> Dict:
    """
    Greenfield constraints → constraints_profile 형식

    내부 통일: 모두 constraints_profile 형식으로 처리
    """
    hard_constraints = []

    if "budget" in constraints:
        hard_constraints.append({
            "type": "financial",
            "dimension": "budget",
            "threshold": constraints["budget"]
        })

    if "timeline_months" in constraints:
        hard_constraints.append({
            "type": "temporal",
            "dimension": "timeline_months",
            "threshold": constraints["timeline_months"]
        })

    # ...

    return {"hard_constraints": hard_constraints}
```

---

## 7. PolicyEngine 통합

### 7.1 policy_ref 해석

**Policy 모드**:
- `reporting_strict`: 보수적, Evidence only
- `decision_balanced`: 균형, Evidence + Prior
- `exploration_friendly`: 탐색적, Prior 허용

**StrategyEngine 적용**:
```python
def _resolve_policy(self, policy_ref: str) -> Dict[str, Any]:
    """
    policy_ref → 파라미터

    Returns:
        policy_params: {
            "risk_tolerance": 0.0~1.0,
            "prior_usage": "minimal|balanced|extensive",
            "min_evidence_ratio": 0.0~1.0,
            "exploration_depth": 1~3
        }
    """
    if policy_ref == "reporting_strict":
        return {
            "risk_tolerance": 0.3,
            "prior_usage": "minimal",
            "min_evidence_ratio": 0.8,
            "exploration_depth": 1
        }
    elif policy_ref == "decision_balanced":
        return {
            "risk_tolerance": 0.5,
            "prior_usage": "balanced",
            "min_evidence_ratio": 0.5,
            "exploration_depth": 2
        }
    elif policy_ref == "exploration_friendly":
        return {
            "risk_tolerance": 0.7,
            "prior_usage": "extensive",
            "min_evidence_ratio": 0.3,
            "exploration_depth": 3
        }
    else:
        # 기본값
        return self._resolve_policy("decision_balanced")
```

**evaluate_portfolio_core()에 적용**:
```python
def evaluate_portfolio_core(
    self,
    strategies: List[Strategy],
    focal_actor_context_id: Optional[FocalActorContext],
    policy_params: Dict[str, Any]
) -> PortfolioEvaluation:
    """
    Portfolio 평가 (policy 반영)
    """
    # Risk tolerance 반영
    risk_tolerance = policy_params["risk_tolerance"]

    # 고위험 전략 필터링/페널티
    for strategy in strategies:
        risk_score = len(strategy.risks) / 10

        if risk_score > risk_tolerance:
            # exploration_friendly면 허용, reporting_strict면 제외
            if policy_params["prior_usage"] == "minimal":
                # 제외 또는 큰 페널티
                strategy.adjusted_score *= 0.5

    # ...
```

---

## 8. Preference Profile 정렬

### 8.1 focal_actor_context_store 스키마 사용

**cmis.yaml**:
```yaml
preference_profile:
  soft_preferences:
    - dimension: "prefer_patterns"
      value: ["PAT-subscription_model"]
      weight: 0.8

    - dimension: "risk_appetite"
      value: "medium"
      weight: 1.0
```

**StrategyEngine 해석**:
```python
def _adjust_by_preferences(
    self,
    strategy: Strategy,
    preference_profile: Dict
) -> float:
    """
    focal_actor_context_store 스키마 기준
    """
    score = strategy.execution_fit_score or 0.5

    soft_preferences = preference_profile.get("soft_preferences", [])

    for pref in soft_preferences:
        dimension = pref["dimension"]
        value = pref["value"]
        weight = pref.get("weight", 0.5)

        if dimension == "prefer_patterns":
            for pattern_id in strategy.pattern_composition:
                if pattern_id in value:
                    score += 0.1 * weight

        elif dimension == "avoid_patterns":
            for pattern_id in strategy.pattern_composition:
                if pattern_id in value:
                    score -= 0.2 * weight

        elif dimension == "risk_appetite":
            risk_level = value  # "low"|"medium"|"high"
            strategy_risk = len(strategy.risks) / 10

            if risk_level == "low" and strategy_risk > 0.3:
                score -= 0.15 * weight
            elif risk_level == "high" and strategy_risk < 0.2:
                score += 0.1 * weight

    return max(0.0, min(1.0, score))
```

---

## 9. Explore vs Decide 모드 (대안 B 반영)

### 9.1 두 모드

**Explore 모드** (OpportunityDesigner):
- 많은 전략 후보 생성 (max 50개)
- policy_ref = "exploration_friendly"
- D-Graph에 실험적 저장
- 빠른 탐색

**Decide 모드** (StrategyArchitect):
- 적은 전략 심층 평가 (max 10개)
- policy_ref = "decision_balanced"
- Portfolio 최적화
- 의사결정 지원

**API**:
```python
def search_strategies_api(
    self,
    goal_id: str,
    constraints: Dict,
    focal_actor_context_id: Optional[str] = None,
    mode: str = "decide"  # "explore" | "decide"
) -> str:
    """
    mode에 따라 탐색 깊이/정책 조정
    """
    if mode == "explore":
        max_strategies = 50
        policy_ref = "exploration_friendly"
        evaluation_depth = "shallow"
    else:  # decide
        max_strategies = 10
        policy_ref = "decision_balanced"
        evaluation_depth = "deep"

    # ...
```

---

## 10. 설계 검증 (Enhanced)

### 10.1 cmis.yaml 정합성

- [x] search_strategies API 시그니처 일치
- [x] evaluate_portfolio API 시그니처 일치
- [x] D-Graph 스키마 사용
- [x] focal_actor_context_store 스키마 사용
- [x] canonical_workflows 호환

### 10.2 엔진 연계

- [x] **WorldEngine**: snapshot 호출 (API 레이어에서)
- [x] **PatternEngine**: match_patterns, discover_gaps 호출
- [x] **ValueEngine**: ROI 계산, Pattern Prior 활용
- [x] **PolicyEngine**: policy_ref 해석
- [x] **LearningEngine**: StrategyLibrary 준비 (미래)

### 10.3 철학 부합성

- [x] Model-first: Strategy = Pattern 모델
- [x] Evidence-first: Pattern/Value 기반
- [x] Graph-of-Graphs: D-Graph 분리
- [x] 세계·변화·결과·논증: 모두 포함

---

## 11. 피드백 반영 요약

### 반영된 7개 주요 피드백

1. **API 레벨 분리**
   - Public API (cmis.yaml 대응)
   - Core 함수 (내부 로직)
   - Orchestration Layer

2. **D-Graph 스키마 정렬**
   - cmis.yaml 최신 스키마 사용
   - Strategy → D-Graph 매핑 테이블
   - Edge 기반 관계 표현

3. **ValueEngine ROI 연동**
   - ValueEngine이 ROI 계산 담당
   - Pattern Prior → ValueEngine
   - ValueRecord 형식 사용

4. **Constraints 스키마 정렬**
   - focal_actor_context_store 스키마 기준
   - type/dimension/threshold 구조
   - Greenfield → constraints_profile 변환

5. **PolicyEngine 통합**
   - evaluate_portfolio에 policy_ref 추가
   - policy_ref → 파라미터 해석
   - risk_tolerance, prior_usage 반영

6. **Preference Profile 정렬**
   - soft_preferences 스키마 사용
   - dimension/value/weight 구조

7. **Explore/Decide 모드**
   - mode 인자 추가
   - OpportunityDesigner vs StrategyArchitect

---

## 12. 구현 로드맵 (Enhanced)

### Phase 1: Core + API (1주)

**Day 1-2**: 데이터 모델 + D-Graph 통합
- Strategy, Goal dataclass
- D-Graph 매핑 함수
- _save_strategies_to_d_graph()

**Day 3-4**: Core 함수
- search_strategies_core()
- StrategyGenerator
- StrategyEvaluator (ValueEngine 연동)

**Day 5-6**: Public API
- search_strategies_api()
- _load_goal_from_d_graph()
- _load_project_context()

**Day 7**: 테스트
- 10개 테스트

---

### Phase 2: Portfolio + Policy (1주)

**Day 1-2**: evaluate_portfolio_core()
- PortfolioOptimizer
- Synergy/Conflict

**Day 3-4**: evaluate_portfolio_api()
- policy_ref 해석
- D-Graph 저장

**Day 5-6**: ValueEngine 통합
- Pattern Prior → ValueEngine
- ValueRecord 형식

**Day 7**: 테스트
- 8개 테스트

---

## 13. ADR (Architecture Decision Records)

### ADR-1: API 레벨 분리

**결정**: Public API (cmis.yaml) vs Core (내부)

**이유**:
- canonical_workflows 호환
- 테스트 용이성
- 재사용성

---

### ADR-2: D-Graph가 진실의 원천

**결정**: Strategy는 D-Graph 노드 + edge로 저장

**이유**:
- Graph-of-Graphs 철학
- LearningEngine 연동
- 단일 진실 소스

---

### ADR-3: ValueEngine이 ROI 계산

**결정**: StrategyEngine은 ValueEngine 호출

**이유**:
- Evidence-first 철학
- Metric 계산 일관성
- Lineage 추적

---

### ADR-4: focal_actor_context_store 스키마 준수

**결정**: constraints_profile 형식 사용

**이유**:
- 스키마 일관성
- LearningEngine 호환
- 재사용성

---

**작성**: 2025-12-11
**상태**: 설계 완료 (Enhanced)
**기반**: 피드백 7개 완전 반영
**다음**: Phase 1 구현 착수


