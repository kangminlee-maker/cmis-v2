# Strategy Engine 설계 문서

**작성일**: 2025-12-11
**버전**: v1.0
**상태**: 설계 진행 중

---

## Executive Summary

StrategyEngine은 Goal/Pattern/Reality/Value를 바탕으로 **전략 후보를 탐색하고 평가**하는 엔진입니다.

**핵심 역할**:
- Pattern 조합 → Strategy 생성
- Execution Fit 평가
- Portfolio 구성 및 평가
- ROI/Risk 예측

**설계 원칙**:
- **Pattern-driven**: PatternEngine 결과 기반 전략 생성
- **Context-aware**: ProjectContext 제약 반영
- **Evidence-backed**: ValueEngine 연동 ROI 계산
- **Composable**: 여러 Pattern 조합 가능

---

## 1. CMIS 철학 및 아키텍처 분석

### 1.1 CMIS 철학 반영

**Model-first, Number-second**:
- 전략(Strategy) = Pattern 조합 모델
- ROI/Risk = 전략 모델 위의 숫자

**Evidence-first, Prior-last**:
- Pattern 매칭 결과 우선
- Gap의 Execution Fit 기반
- Prior는 보완적

**Graph-of-Graphs**:
- R-Graph (Reality): WorldEngine
- P-Graph (Pattern): PatternEngine
- V-Graph (Value): ValueEngine
- **D-Graph (Decision)**: StrategyEngine

**모든 답 = (세계, 변화, 결과, 논증)**:
- 세계: R-Graph + Pattern
- 변화: Strategy (Pattern 조합)
- 결과: ROI, Risk
- 논증: Execution Fit, Evidence Lineage

---

### 1.2 cmis.yaml 정의 분석

**strategy_engine 정의**:
```yaml
strategy_engine:
  description: "Goal/Pattern/Reality/Value를 바탕으로 전략/포트폴리오 후보 탐색/평가"
  inputs:
    - reality_graph
    - pattern_graph
    - value_graph
    - decision_graph
    - value_engine
  outputs:
    - strategy_candidates
  api:
    - name: search_strategies
      input:
        goal_id
        constraints
        project_context_id (optional)
      output:
        strategy_set_ref
      
    - name: evaluate_portfolio
      input:
        strategy_ids
        policy_ref
        project_context_id (optional)
      output:
        portfolio_eval_ref
```

**decision_graph (D-Graph) 스키마**:
```yaml
decision_graph:
  node_types:
    goal:
      - goal_id
      - name
      - target_metrics (예: ["MET-Revenue > 10B", "MET-CAC < 5000"])
      - target_horizon
      - project_context_id
    
    scenario:
      - scenario_id
      - name
      - assumptions (가정 세트)
      - related_strategy_ids
    
    strategy:
      - strategy_id
      - name
      - pattern_composition (어떤 Pattern 조합)
      - action_set (구체적 행동)
      - expected_outcomes
      - execution_fit_score
    
    action:
      - action_id
      - action_type
      - target_actor/resource
      - parameters
  
  edge_types:
    goal_requires_strategy
    strategy_implements_pattern
    strategy_contains_action
    action_modifies_actor
    strategy_conflicts_with_strategy
```

**canonical_workflows: strategy_design**:
```yaml
strategy_design:
  role_id: strategy_architect
  steps:
    - call: strategy_engine.search_strategies
      with:
        goal_id: "@input.goal_id"
        constraints: {}
    
    - call: strategy_engine.evaluate_portfolio
      with:
        strategy_ids: "@prev.strategy_ids"
        policy_ref: "decision_balanced"
```

---

## 2. StrategyEngine 아키텍처

### 2.1 전체 구조

```
┌──────────────────────────────────────────────────────────┐
│                   StrategyEngine                          │
│  search_strategies() / evaluate_portfolio()              │
└──────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Strategy   │  │   Strategy   │  │  Portfolio   │
│   Generator  │  │  Evaluator   │  │  Optimizer   │
│              │  │              │  │              │
│ Pattern 조합 │  │ Execution    │  │ 조합 평가    │
│ → Strategy   │  │ Fit/ROI/Risk │  │ Synergy      │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────┐
│                     Inputs                                │
│  - PatternEngine (매칭 + Gap)                            │
│  - WorldEngine (R-Graph)                                 │
│  - ValueEngine (ROI 계산)                                │
│  - ProjectContext (제약, Baseline)                       │
└──────────────────────────────────────────────────────────┘
```

### 2.2 핵심 컴포넌트

**1. StrategyGenerator**:
- Pattern 조합 → Strategy 생성
- Gap 기반 전략 제안
- Constraint 필터링

**2. StrategyEvaluator**:
- Execution Fit 계산
- ROI/Risk 예측
- Feasibility 평가

**3. PortfolioOptimizer**:
- 여러 Strategy 조합
- Synergy/Conflict 분석
- 리소스 배분

---

## 3. 데이터 모델

### 3.1 Strategy 데이터 클래스

```python
@dataclass
class Strategy:
    """전략 정의
    
    Pattern 조합 + 구체적 행동 계획
    """
    strategy_id: str
    name: str
    description: str
    
    # Pattern 조합
    pattern_composition: List[str]  # pattern_id 리스트
    # ["PAT-subscription_model", "PAT-freemium_model"]
    
    # 구체적 행동
    action_set: List[Dict[str, Any]]
    # [
    #   {"action_type": "launch_product", "target": "digital_service"},
    #   {"action_type": "set_pricing", "params": {"model": "subscription"}}
    # ]
    
    # 예상 결과
    expected_outcomes: Dict[str, Any]
    # {
    #   "revenue_3y": 50000000000,
    #   "customer_3y": 100000,
    #   "market_share_3y": 0.15
    # }
    
    # 적합성
    execution_fit_score: Optional[float] = None
    
    # 리스크
    risks: List[Dict[str, Any]] = field(default_factory=list)
    # [{"type": "execution", "description": "...", "severity": "medium"}]
    
    # 메타
    created_from: str = "pattern_combination"  # "pattern_combination" | "gap_based" | "custom"
    source_patterns: List[str] = field(default_factory=list)  # 출처 Pattern
    
    # Lineage
    lineage: Dict[str, Any] = field(default_factory=dict)
```

### 3.2 Goal 데이터 클래스

```python
@dataclass
class Goal:
    """목표 정의"""
    goal_id: str
    name: str
    description: str
    
    # Target Metrics
    target_metrics: List[Dict[str, Any]]
    # [
    #   {"metric_id": "MET-Revenue", "operator": ">", "value": 10000000000, "horizon": "3y"},
    #   {"metric_id": "MET-CAC", "operator": "<", "value": 50000}
    # ]
    
    # Context
    project_context_id: Optional[str] = None
    
    # Constraints
    hard_constraints: List[Dict[str, Any]] = field(default_factory=list)
    soft_preferences: List[Dict[str, Any]] = field(default_factory=list)
```

### 3.3 PortfolioEvaluation 데이터 클래스

```python
@dataclass
class PortfolioEvaluation:
    """Portfolio 평가 결과"""
    portfolio_id: str
    strategy_ids: List[str]
    
    # 통합 평가
    aggregate_roi: float
    aggregate_risk: float
    
    # Synergy
    synergies: List[Dict[str, Any]] = field(default_factory=list)
    # [{"strategies": ["STR-001", "STR-002"], "synergy_score": 0.3}]
    
    # Conflicts
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    # [{"strategies": ["STR-001", "STR-003"], "conflict_type": "resource"}]
    
    # 리소스
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    # {"budget": 1000000000, "team_size": 50, "timeline": "18m"}
```

---

## 4. StrategyGenerator 설계

### 4.1 Pattern 조합 기반 Strategy 생성

**입력**:
- Matched Patterns (PatternEngine.match_patterns)
- Gap Candidates (PatternEngine.discover_gaps)
- Goal
- ProjectContext

**프로세스**:
```
1. Matched Patterns 분석
   - composes_with 관계 확인
   - conflicts_with 필터링

2. Gap Candidates 우선순위
   - expected_level: core > common > rare
   - feasibility: high > medium > low
   - execution_fit_score 높은 순

3. Pattern 조합 생성
   - 2-3개 Pattern 조합
   - composes_with 기반
   - conflicts_with 제외

4. Strategy 생성
   - Pattern → Action 변환
   - 예상 Outcome 계산 (ValueEngine Prior)

5. Execution Fit 평가
   - ProjectContext.constraints_profile 확인
   - ProjectContext.assets_profile 충족도
```

**알고리즘**:
```python
def generate_strategies_from_patterns(
    matched_patterns: List[PatternMatch],
    gaps: List[GapCandidate],
    goal: Goal,
    project_context: Optional[ProjectContext]
) -> List[Strategy]:
    """
    Pattern 조합 → Strategy
    
    전략 생성 방식:
    1. Single Pattern Strategy
       - 각 Matched Pattern → 1개 Strategy
    
    2. Pattern Composition Strategy
       - composes_with 관계 → 2-3개 조합
    
    3. Gap-based Strategy
       - High feasibility Gap → Strategy
    
    4. Hybrid Strategy
       - Matched + Gap 조합
    """
    strategies = []
    
    # 1. Single Pattern
    for pm in matched_patterns:
        strategy = create_strategy_from_pattern(pm, project_context)
        strategies.append(strategy)
    
    # 2. Pattern Composition
    for pm in matched_patterns:
        pattern = pattern_library.get(pm.pattern_id)
        
        for compose_id in pattern.composes_with:
            # compose_id가 matched 또는 gap에 있는지
            if compose_id in [p.pattern_id for p in matched_patterns]:
                # 조합 Strategy
                strategy = create_composition_strategy(
                    [pm.pattern_id, compose_id],
                    project_context
                )
                strategies.append(strategy)
    
    # 3. Gap-based
    for gap in gaps:
        if gap.feasibility in ["high", "medium"]:
            strategy = create_strategy_from_gap(gap, project_context)
            strategies.append(strategy)
    
    # 4. Goal 필터링
    strategies = filter_by_goal(strategies, goal)
    
    return strategies
```

---

## 5. StrategyEvaluator 설계

### 5.1 Execution Fit 계산

**재사용: PatternEngine의 Execution Fit**:
- Strategy의 각 Pattern에 대해 Execution Fit 계산
- 평균 또는 최소값 사용

```python
def calculate_execution_fit(
    strategy: Strategy,
    project_context: ProjectContext
) -> float:
    """
    Strategy Execution Fit
    
    계산:
    - 각 Pattern의 Execution Fit 계산
    - 평균 또는 최소값 (보수적)
    """
    pattern_fits = []
    
    for pattern_id in strategy.pattern_composition:
        pattern = pattern_library.get(pattern_id)
        
        # PatternScorer 재사용
        fit = pattern_scorer.calculate_execution_fit(
            pattern,
            project_context
        )
        
        pattern_fits.append(fit)
    
    # 보수적: 최소값
    return min(pattern_fits) if pattern_fits else 0.0
```

### 5.2 ROI 예측

**ValueEngine 연동**:
```python
def estimate_roi(
    strategy: Strategy,
    baseline_state: Dict[str, Any],
    horizon: str = "3y"
) -> Dict[str, Any]:
    """
    Strategy ROI 예측
    
    프로세스:
    1. Pattern Benchmark → Metric Prior
    2. Baseline State → 시작점
    3. Growth 시뮬레이션
    4. 3년 후 예상 Revenue/Profit
    """
    # 1. Pattern Benchmark
    benchmarks = {}
    for pattern_id in strategy.pattern_composition:
        pattern = pattern_library.get(pattern_id)
        
        for metric_id in pattern.benchmark_metrics:
            if metric_id not in benchmarks:
                # quantitative_bounds → Prior
                bounds = pattern.quantitative_bounds.get(metric_id)
                if bounds:
                    benchmarks[metric_id] = bounds["typical"]
    
    # 2. Baseline
    current_revenue = baseline_state.get("current_revenue", 0)
    current_customers = baseline_state.get("current_customers", 0)
    
    # 3. Growth 시뮬레이션
    # 간단한 모델: Benchmark의 성장률 적용
    growth_rate = benchmarks.get("revenue_growth_yoy", [0.3, 0.5])
    avg_growth = sum(growth_rate) / len(growth_rate)
    
    # Compound growth
    years = int(horizon[:-1])  # "3y" → 3
    future_revenue = current_revenue * ((1 + avg_growth) ** years)
    
    # 4. ROI
    roi = {
        "revenue_3y": future_revenue,
        "revenue_growth_cagr": avg_growth,
        "confidence": 0.6  # Pattern Prior 기반이므로 중간
    }
    
    return roi
```

### 5.3 Risk 평가

**Risk 타입**:
1. **Execution Risk**: Execution Fit 낮음
2. **Market Risk**: 시장 경쟁 강도
3. **Resource Risk**: 필요 자원 > 가용 자원
4. **Cannibalization Risk**: 기존 사업과 충돌

```python
def assess_risks(
    strategy: Strategy,
    project_context: Optional[ProjectContext],
    matched_patterns: List[PatternMatch]
) -> List[Dict[str, Any]]:
    """
    Risk 평가
    """
    risks = []
    
    # 1. Execution Risk
    if strategy.execution_fit_score < 0.5:
        risks.append({
            "type": "execution",
            "severity": "high",
            "description": f"Execution Fit 낮음 ({strategy.execution_fit_score:.2f})"
        })
    
    # 2. Resource Risk
    if project_context:
        required = estimate_resource_requirements(strategy)
        available = project_context.assets_profile
        
        if required["budget"] > available.get("budget", 0):
            risks.append({
                "type": "resource",
                "severity": "medium",
                "description": "예산 부족"
            })
    
    # 3. Cannibalization
    for pattern_id in strategy.pattern_composition:
        if pattern_id in [pm.pattern_id for pm in matched_patterns]:
            # 이미 매칭된 Pattern을 또 추가 → Cannibalization 가능
            risks.append({
                "type": "cannibalization",
                "severity": "low",
                "description": f"{pattern_id} 기존 사업과 충돌 가능"
            })
    
    return risks
```

---

## 6. PortfolioOptimizer 설계

### 6.1 Portfolio 구성

**입력**:
- Strategy 후보 리스트
- Goal
- 리소스 제약

**최적화 목표**:
- Goal 달성 확률 최대화
- 리스크 최소화
- 리소스 제약 내

**알고리즘** (Phase 1: Greedy):
```python
def optimize_portfolio(
    strategies: List[Strategy],
    goal: Goal,
    budget_constraint: float
) -> List[str]:
    """
    Portfolio 최적화 (Greedy)
    
    Phase 1: 단순 Greedy
    Phase 2: Dynamic Programming
    Phase 3: 유전 알고리즘
    """
    # ROI/Risk 기준 정렬
    scored_strategies = [
        (s, s.expected_outcomes.get("roi", 0) / (1 + s.aggregate_risk))
        for s in strategies
    ]
    
    scored_strategies.sort(key=lambda x: x[1], reverse=True)
    
    # Greedy 선택
    selected = []
    total_budget = 0
    
    for strategy, score in scored_strategies:
        required_budget = strategy.expected_outcomes.get("required_investment", 0)
        
        if total_budget + required_budget <= budget_constraint:
            selected.append(strategy.strategy_id)
            total_budget += required_budget
    
    return selected
```

### 6.2 Synergy/Conflict 분석

**Synergy**:
- 같은 Pattern family → 시너지
- composes_with 관계 → 시너지

**Conflict**:
- conflicts_with 관계 → 충돌
- 리소스 경쟁 → 충돌

```python
def analyze_synergy(
    strategy1: Strategy,
    strategy2: Strategy
) -> float:
    """
    두 Strategy 간 시너지
    
    점수: -1.0 (강한 충돌) ~ +1.0 (강한 시너지)
    """
    synergy = 0.0
    
    # 1. Pattern family 일치
    families1 = get_pattern_families(strategy1.pattern_composition)
    families2 = get_pattern_families(strategy2.pattern_composition)
    
    common_families = families1 & families2
    synergy += len(common_families) * 0.2
    
    # 2. composes_with 관계
    for p1 in strategy1.pattern_composition:
        for p2 in strategy2.pattern_composition:
            pattern1 = pattern_library.get(p1)
            
            if p2 in pattern1.composes_with:
                synergy += 0.3
    
    # 3. conflicts_with 관계
    for p1 in strategy1.pattern_composition:
        for p2 in strategy2.pattern_composition:
            pattern1 = pattern_library.get(p1)
            
            if p2 in pattern1.conflicts_with:
                synergy -= 0.5
    
    return max(-1.0, min(1.0, synergy))
```

---

## 7. StrategyEngine API

### 7.1 search_strategies()

```python
def search_strategies(
    goal: Goal,
    reality_snapshot: RealityGraphSnapshot,
    pattern_matches: List[PatternMatch],
    gaps: List[GapCandidate],
    project_context: Optional[ProjectContext] = None,
    greenfield_constraints: Optional[Dict[str, Any]] = None,
    max_strategies: int = 10
) -> List[Strategy]:
    """
    Strategy 후보 탐색
    
    프로세스:
    1. StrategyGenerator로 후보 생성
    2. Goal 필터링
    3. Execution Fit 계산
    4. Top-N 선택
    
    Args:
        goal: 목표
        reality_snapshot: R-Graph
        pattern_matches: 매칭된 Pattern
        gaps: Gap 후보
        project_context: ProjectContext (Brownfield, 선택)
        greenfield_constraints: Greenfield 제약 (자본, 시간 등, 선택)
            예: {"budget": 1000000000, "timeline_months": 24}
        max_strategies: 최대 전략 수
    
    Returns:
        Strategy 리스트
        - Greenfield: ROI 기준 정렬
        - Brownfield: execution_fit × ROI 기준 정렬
    
    Note:
        - project_context와 greenfield_constraints 동시 사용 불가
        - project_context 없고 greenfield_constraints만 있으면 Greenfield
        - project_context 있으면 Brownfield (constraints_profile 사용)
    """
```

### 7.2 evaluate_portfolio()

```python
def evaluate_portfolio(
    strategy_ids: List[str],
    goal: Goal,
    project_context: Optional[ProjectContext] = None
) -> PortfolioEvaluation:
    """
    Portfolio 평가
    
    프로세스:
    1. 각 Strategy 조회
    2. Synergy/Conflict 분석
    3. 통합 ROI/Risk 계산
    4. 리소스 요구사항 합산
    
    Args:
        strategy_ids: Strategy ID 리스트
        goal: 목표
        project_context: ProjectContext
    
    Returns:
        PortfolioEvaluation
    """
```

---

## 8. 구현 계획

### 8.1 Phase 1: Core Infrastructure (1주)

**작업**:
1. **데이터 모델** (1일)
   - Strategy, Goal, PortfolioEvaluation
   - types.py에 추가

2. **StrategyGenerator** (2일)
   - Pattern 조합 로직
   - Gap 기반 전략 생성
   - create_strategy_from_pattern()

3. **StrategyEvaluator** (2일)
   - Execution Fit (PatternScorer 재사용)
   - ROI 예측 (ValueEngine 연동)
   - Risk 평가

4. **StrategyEngine** (1일)
   - search_strategies() API
   - evaluate_portfolio() stub

5. **테스트** (1일)
   - 10개 테스트

---

### 8.2 Phase 2: Portfolio & Optimization (1주)

**작업**:
1. **PortfolioOptimizer** (2일)
   - Synergy/Conflict 분석
   - Greedy 최적화

2. **evaluate_portfolio() 완전 구현** (2일)
   - 통합 ROI/Risk
   - 리소스 요구사항

3. **D-Graph 통합** (준비)
   - Goal/Strategy/Scenario 노드
   - 관계 edge

4. **테스트** (1일)
   - 8개 테스트

---

### 8.3 Phase 3: Advanced (선택, 1주)

**작업**:
- 고급 최적화 알고리즘
- Scenario Planning
- Sensitivity 분석

---

---

## 9. Pattern → Strategy 변환 규칙

### 9.1 Single Pattern Strategy

**예시: PAT-subscription_model → Strategy**:
```python
Pattern: PAT-subscription_model
  trait_constraints:
    money_flow:
      required_traits: {revenue_model: "subscription", payment_recurs: true}

↓ 변환 ↓

Strategy: STR-launch-subscription-service
  name: "구독형 서비스 런칭"
  pattern_composition: ["PAT-subscription_model"]
  action_set: [
    {
      "action_type": "design_pricing_model",
      "params": {"model": "subscription", "recurrence": "monthly"}
    },
    {
      "action_type": "build_payment_infra",
      "params": {"recurring": true}
    },
    {
      "action_type": "implement_retention_program",
      "params": {"churn_target": 0.05}
    }
  ]
  expected_outcomes:
    revenue_3y: 50억 (Pattern Benchmark 기반)
    churn_rate: 0.05
    ltv_cac_ratio: 3.0
```

### 9.2 Pattern Composition Strategy

**예시: Subscription + Freemium**:
```python
Patterns:
  - PAT-subscription_model (composes_with: PAT-freemium_model)
  - PAT-freemium_model

↓ 조합 ↓

Strategy: STR-freemium-to-subscription
  name: "프리미엄에서 구독 전환 모델"
  pattern_composition: ["PAT-freemium_model", "PAT-subscription_model"]
  action_set: [
    {
      "action_type": "launch_free_tier",
      "params": {"feature_limit": "basic"}
    },
    {
      "action_type": "design_upgrade_funnel",
      "params": {"target_conversion": 0.05}
    },
    {
      "action_type": "implement_subscription",
      "params": {"tiers": ["basic_free", "pro", "enterprise"]}
    }
  ]
  expected_outcomes:
    conversion_rate: 0.05
    revenue_3y: 80억 (Freemium + Subscription 시너지)
```

### 9.3 Gap-based Strategy

**예시: Missing PAT-network_effects**:
```python
Gap: PAT-network_effects
  expected_level: core
  feasibility: high
  execution_fit_score: 0.75

↓ 변환 ↓

Strategy: STR-build-network-effects
  name: "네트워크 효과 구축"
  pattern_composition: ["PAT-network_effects"]
  action_set: [
    {
      "action_type": "enable_user_generated_content",
      "params": {"content_types": ["review", "recommendation"]}
    },
    {
      "action_type": "build_referral_program",
      "params": {"incentive": "discount"}
    },
    {
      "action_type": "create_community_features",
      "params": {"features": ["forum", "group"]}
    }
  ]
  expected_outcomes:
    network_density: 0.3 (3년 후)
    viral_coefficient: 1.5
```

---

## 10. ROI 예측 메커니즘

### 10.1 Pattern Benchmark 기반 예측

**프로세스**:
```
1. Strategy의 각 Pattern Benchmark 조회
   ↓
2. Target Metrics 추출 (revenue_growth, margin 등)
   ↓
3. Baseline State에서 시작
   ↓
4. Compound Growth 시뮬레이션
   ↓
5. 3년 후 예상 Metric 계산
```

**코드**:
```python
def predict_outcomes(
    strategy: Strategy,
    baseline_state: Dict[str, Any],
    horizon_years: int = 3
) -> Dict[str, Any]:
    """
    Strategy 실행 시 예상 결과
    
    Args:
        strategy: Strategy
        baseline_state: 현재 상태
        horizon_years: 예측 기간
    
    Returns:
        예상 Outcomes
    """
    outcomes = {}
    
    # Baseline
    current_revenue = baseline_state.get("current_revenue", 0)
    current_customers = baseline_state.get("current_customers", 0)
    current_margin = baseline_state.get("gross_margin", 0.5)
    
    # Pattern Benchmarks 통합
    benchmarks = aggregate_pattern_benchmarks(strategy.pattern_composition)
    
    # Revenue 성장
    growth_rate = benchmarks.get("revenue_growth_yoy", [0.3, 0.5])
    avg_growth = sum(growth_rate) / len(growth_rate)
    
    future_revenue = current_revenue * ((1 + avg_growth) ** horizon_years)
    
    # Customer 성장 (비슷한 로직)
    customer_growth = benchmarks.get("customer_growth_yoy", [0.25, 0.40])
    avg_cust_growth = sum(customer_growth) / len(customer_growth)
    
    future_customers = current_customers * ((1 + avg_cust_growth) ** horizon_years)
    
    # Margin (Pattern Benchmark)
    target_margin = benchmarks.get("gross_margin", [0.6, 0.8])
    avg_margin = sum(target_margin) / len(target_margin)
    
    # Outcomes
    outcomes = {
        "revenue_3y": future_revenue,
        "customers_3y": future_customers,
        "gross_margin_3y": avg_margin,
        "revenue_cagr": avg_growth,
        "confidence": 0.6,  # Pattern Prior 기반
        "method": "pattern_benchmark_projection"
    }
    
    return outcomes
```

### 10.2 ValueEngine 연동 (정교한 예측)

**Phase 2: ValueEngine Simulation**:
```python
def predict_outcomes_with_value_engine(
    strategy: Strategy,
    baseline_state: Dict[str, Any],
    value_engine: ValueEngine
) -> Dict[str, Any]:
    """
    ValueEngine 시뮬레이션 기반 예측
    
    프로세스:
    1. Strategy → R-Graph 변화 시뮬레이션
    2. ValueEngine.evaluate_metrics() 호출
    3. What-if 시나리오
    """
    # Phase 2에서 구현
    pass
```

---

## 11. Constraint 처리

### 11.1 Hard Constraints (필수)

**ProjectContext.constraints_profile**:
```python
constraints_profile: {
    "hard_constraints": [
        {"type": "budget", "threshold": 1000000000},
        {"type": "timeline", "max_months": 18},
        {"type": "team_size", "max": 50}
    ]
}
```

**필터링**:
```python
def filter_by_constraints(
    strategies: List[Strategy],
    constraints: List[Dict[str, Any]]
) -> List[Strategy]:
    """
    Hard Constraints 필터링
    
    제약 위반 Strategy 제거
    """
    filtered = []
    
    for strategy in strategies:
        violates = False
        
        for constraint in constraints:
            if constraint["type"] == "budget":
                required = strategy.expected_outcomes.get("required_investment", 0)
                if required > constraint["threshold"]:
                    violates = True
                    break
        
        if not violates:
            filtered.append(strategy)
    
    return filtered
```

### 11.2 Soft Preferences (선호)

**ProjectContext.preference_profile**:
```python
preference_profile: {
    "prefer_patterns": ["PAT-subscription_model"],
    "avoid_patterns": ["PAT-capital_intensive"],
    "risk_appetite": "medium"  # low|medium|high
}
```

**Scoring 조정**:
```python
def adjust_score_by_preferences(
    strategy: Strategy,
    preferences: Dict[str, Any]
) -> float:
    """
    선호도 반영
    
    보너스/페널티 적용
    """
    score = strategy.execution_fit_score
    
    # prefer_patterns 보너스
    for pattern_id in strategy.pattern_composition:
        if pattern_id in preferences.get("prefer_patterns", []):
            score += 0.1
    
    # avoid_patterns 페널티
    for pattern_id in strategy.pattern_composition:
        if pattern_id in preferences.get("avoid_patterns", []):
            score -= 0.2
    
    # Risk appetite
    risk_appetite = preferences.get("risk_appetite", "medium")
    strategy_risk = len(strategy.risks) / 10  # 간단한 risk 점수
    
    if risk_appetite == "low" and strategy_risk > 0.3:
        score -= 0.15
    elif risk_appetite == "high" and strategy_risk < 0.2:
        score += 0.1  # 공격적 전략 선호
    
    return max(0.0, min(1.0, score))
```

---

## 12. 실무 활용 시나리오

### 12.1 Greenfield: Neutral 시장 분석 및 전략

**정의**: 
- '나'에 대한 정보 없이 시장 전체를 neutral하게 분석
- ProjectContext 없음
- "이 시장에서 일반적으로 어떤 전략이 유효한가?"

**상황**:
- 교육 플랫폼 시장 전반 분석
- 목표: 시장에서 통하는 전략 패턴 파악

**프로세스**:
```python
# 1. Goal 정의
goal = Goal(
    goal_id="GOAL-001",
    name="교육 플랫폼 100억 달성",
    target_metrics=[
        {"metric_id": "MET-Revenue", "operator": ">", "value": 10000000000, "horizon": "3y"}
    ]
)

# 2. 시장 분석
snapshot = world_engine.snapshot("Adult_Language_Education_KR", "KR")
matches = pattern_engine.match_patterns(snapshot.graph)
gaps = pattern_engine.discover_gaps(snapshot.graph)

# 3. 전략 탐색
strategies = strategy_engine.search_strategies(
    goal=goal,
    reality_snapshot=snapshot,
    pattern_matches=matches,
    gaps=gaps
)

# 결과: 10개 전략 후보
# - STR-001: Subscription model (ROI: 80억, Risk: low)
# - STR-002: Freemium → Subscription (ROI: 120억, Risk: medium)
# - STR-003: Marketplace model (ROI: 150억, Risk: high)
```

### 12.2 Brownfield: '나'의 입장에서 전략

**정의**:
- '나'(focal_actor)에 대한 정의와 정보가 존재
- ProjectContext 있음
- "우리 회사가 이 시장에서 취할 수 있는 전략은?"

**상황**:
- 우리 회사: 구독 서비스 운영 중 (baseline_state 있음)
- 목표: 우리 회사의 고객 2배 증가

**프로세스**:
```python
# 1. ProjectContext
project_context = ProjectContext(
    project_context_id="PRJ-my-company",
    baseline_state={
        "current_revenue": 5000000000,  # 50억
        "current_customers": 50000
    },
    assets_profile={...},
    constraints_profile={
        "hard_constraints": [
            {"type": "budget", "threshold": 500000000}  # 5억 예산
        ]
    }
)

# 2. 시장 분석 (focal_actor 중심)
world_engine.ingest_project_context(project_context)
snapshot = world_engine.snapshot(
    "Adult_Language_Education_KR", "KR",
    project_context_id="PRJ-my-company"
)

matches = pattern_engine.match_patterns(snapshot.graph, "PRJ-my-company")
gaps = pattern_engine.discover_gaps(snapshot.graph, "PRJ-my-company")

# 3. 전략 탐색 (제약 반영)
goal = Goal(
    goal_id="GOAL-002",
    target_metrics=[
        {"metric_id": "MET-N_customers", "operator": "*", "value": 2}  # 2배
    ],
    project_context_id="PRJ-my-company"
)

strategies = strategy_engine.search_strategies(
    goal=goal,
    reality_snapshot=snapshot,
    pattern_matches=matches,
    gaps=gaps,
    project_context=project_context  # 제약 자동 반영
)

# 결과: 5억 예산 내 전략만
# - STR-101: Network effects 구축 (예산: 3억, ROI: 150%)
# - STR-102: Referral program (예산: 1억, ROI: 80%)
```

### 12.3 Portfolio: 여러 전략 조합

**상황**:
- 3개 전략 후보
- 최적 조합 찾기

**프로세스**:
```python
# 1. 전략 탐색 (위와 동일)
strategies = strategy_engine.search_strategies(...)

# 2. Portfolio 평가
top_strategy_ids = [s.strategy_id for s in strategies[:5]]

portfolio_eval = strategy_engine.evaluate_portfolio(
    strategy_ids=top_strategy_ids,
    goal=goal,
    project_context=project_context
)

# 결과
portfolio_eval:
  aggregate_roi: 1.8
  aggregate_risk: 0.4
  synergies: [
    {"strategies": ["STR-101", "STR-102"], "synergy_score": 0.3}
  ]
  conflicts: [
    {"strategies": ["STR-101", "STR-103"], "conflict_type": "team_resource"}
  ]
  resource_requirements:
    budget: 450000000
    team_size: 35
    timeline: "15m"
```

---

## 13. 확장성 설계

### 13.1 StrategyTemplate (확장)

**Phase 2: Strategy 템플릿**:
```yaml
# config/strategy_templates/launch_subscription.yaml
strategy_template:
  template_id: "TMPL-launch-subscription"
  name: "구독 서비스 런칭 템플릿"
  
  required_patterns: ["PAT-subscription_model"]
  optional_patterns: ["PAT-freemium_model", "PAT-tiered_pricing"]
  
  action_template:
    - action_type: "design_pricing"
      params_template:
        model: "@pattern.trait.revenue_model"
        recurrence: "@pattern.trait.recurrence"
    
    - action_type: "build_payment"
      condition: "@pattern.trait.payment_recurs == true"
  
  outcome_formula:
    revenue_3y: "baseline.revenue * (1 + benchmark.growth_rate) ^ 3"
```

**효과**:
- Pattern → Strategy 규칙 YAML 정의
- 재사용 가능
- 도메인별 커스터마이즈

### 13.2 StrategyLibrary (확장)

```python
class StrategyLibrary:
    """
    Strategy 템플릿 및 과거 전략 저장소
    
    역할:
    - StrategyTemplate YAML 로딩
    - 과거 Strategy 조회
    - LearningEngine 연동 (성공/실패 학습)
    """
    
    def load_templates(self, template_dir: Path):
        """템플릿 로딩"""
    
    def get_strategies_by_pattern(self, pattern_id: str) -> List[Strategy]:
        """특정 Pattern 사용 전략 조회"""
    
    def get_successful_strategies(
        self,
        goal_type: str,
        min_roi: float = 1.5
    ) -> List[Strategy]:
        """성공한 전략 조회 (LearningEngine 연동)"""
```

---

## 14. 효율성 최적화

### 14.1 Strategy 생성 최적화

**문제**: Pattern 조합 경우의 수 폭발
- 23개 Pattern → 2개 조합: 253가지
- 3개 조합: 1,771가지

**해결책**:

**1) composes_with 기반 Pruning**:
```python
# 모든 조합 시도 (X)
all_combinations = combinations(patterns, 2)  # 253가지

# composes_with만 시도 (O)
valid_combinations = [
    (p1, p2) for p1 in patterns for p2_id in p1.composes_with
    if p2_id in pattern_ids
]  # ~30가지
```

**2) Execution Fit Early Filtering**:
```python
# 모든 Strategy 생성 후 평가 (X)
strategies = generate_all_strategies()  # 100개
evaluated = [evaluate(s) for s in strategies]

# Pattern 단계에서 필터링 (O)
high_fit_patterns = [pm for pm in matched if pm.execution_fit_score > 0.5]
strategies = generate_from(high_fit_patterns)  # 20개만
```

**3) Caching**:
```python
@cache
def create_strategy_from_pattern(pattern_id, project_context_id):
    """
    Strategy 생성 캐싱
    - (pattern_id, project_context_id) → Strategy
    """
```

### 14.2 Portfolio 최적화

**Phase 1: Greedy** (O(n log n)):
```python
def greedy_portfolio(strategies, budget):
    # ROI/Risk 정렬
    sorted_strategies = sorted(strategies, key=lambda s: s.roi / (1 + s.risk))
    
    # Greedy 선택
    selected = []
    total_budget = 0
    
    for s in sorted_strategies:
        if total_budget + s.cost <= budget:
            selected.append(s)
            total_budget += s.cost
    
    return selected
```

**Phase 2: Dynamic Programming** (O(n × budget)):
- Knapsack 문제
- 최적해 보장

**Phase 3: 유전 알고리즘** (복잡한 제약):
- Synergy/Conflict 고려
- 다목표 최적화

---

## 15. 테스트 전략

### 15.1 Unit 테스트 (10개)

**StrategyGenerator**:
1. Single Pattern → Strategy
2. Pattern Composition
3. Gap-based Strategy
4. composes_with 활용
5. conflicts_with 필터링

**StrategyEvaluator**:
6. Execution Fit 계산
7. ROI 예측
8. Risk 평가

**StrategyEngine**:
9. search_strategies API
10. Goal 필터링

### 15.2 Integration 테스트 (5개)

1. Pattern → Strategy → ROI 전체 파이프라인
2. Greenfield 전략 탐색
3. Brownfield 제약 반영
4. Portfolio 평가
5. Synergy/Conflict 분석

---

## 16. 구현 로드맵

### Phase 1: Core (1주)

**Day 1-2**: 데이터 모델
- Strategy, Goal, PortfolioEvaluation
- types.py에 추가

**Day 3-4**: StrategyGenerator
- Pattern → Strategy 변환
- 조합 로직
- Gap 기반 생성

**Day 5-6**: StrategyEvaluator
- Execution Fit (PatternScorer 재사용)
- ROI 예측 (Pattern Benchmark)
- Risk 평가

**Day 7**: StrategyEngine
- search_strategies() API
- 테스트 10개

---

### Phase 2: Portfolio (1주)

**Day 1-3**: PortfolioOptimizer
- Synergy/Conflict 분석
- Greedy 최적화
- 리소스 집계

**Day 4-5**: evaluate_portfolio()
- 통합 ROI/Risk
- 최적 조합 선택

**Day 6-7**: D-Graph 통합
- Goal/Strategy 노드
- 관계 edge
- 테스트 8개

---

### Phase 3: Advanced (선택, 1주)

- Dynamic Programming
- Scenario Planning
- Sensitivity 분석

---

## 17. 설계 검증 체크리스트

### CMIS 철학 부합성

- [x] **Model-first**: Strategy = Pattern 모델
- [x] **Evidence-first**: Pattern 기반, ValueEngine 연동
- [x] **Graph-of-Graphs**: D-Graph (Strategy)
- [x] **세계·변화·결과·논증**: 모두 포함
- [x] **Composable**: Pattern 조합 가능

### cmis.yaml API 일치성

- [x] search_strategies(goal_id, constraints, project_context_id)
- [x] evaluate_portfolio(strategy_ids, policy_ref, project_context_id)
- [x] D-Graph 노드 타입 (goal, strategy, scenario, action)

### 다른 엔진과의 연계

- [x] **PatternEngine**: Pattern 매칭 + Gap → Strategy 생성
- [x] **ValueEngine**: ROI 예측, Benchmark 활용
- [x] **WorldEngine**: R-Graph, ProjectContext
- [x] **LearningEngine**: 성공/실패 학습 (미래)

### 확장성

- [x] StrategyTemplate (Phase 2)
- [x] StrategyLibrary (Phase 2)
- [x] 다양한 최적화 알고리즘

### 효율성

- [x] composes_with Pruning
- [x] Early Filtering
- [x] Caching
- [x] Greedy → DP 진화 경로

---

**작성**: 2025-12-11
**상태**: 설계 완료 ✅
**다음**: Phase 1 구현 착수
**예상 시간**: 2주 (Phase 1+2)

**StrategyEngine 설계 완성!**


