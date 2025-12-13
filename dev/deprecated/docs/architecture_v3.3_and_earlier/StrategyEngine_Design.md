# StrategyEngine 설계 문서

**작성일**: 2025-12-11
**버전**: v1.0
**상태**: 설계 진행 중

---

## Executive Summary

StrategyEngine은 CMIS의 Decision Plane 핵심 엔진으로, Goal/Pattern/Reality/Value를 바탕으로 전략 후보를 탐색하고 평가합니다.

**핵심 역할**:
- Pattern 조합 → Strategy 생성
- Execution Fit 평가 (Reality + ProjectContext 기반)
- Portfolio 평가 (여러 Strategy 조합)
- Scenario 시뮬레이션

**설계 철학**:
- **Model-first**: 전략은 Pattern 조합의 구조적 표현
- **Evidence-first**: 실행 가능성은 Reality/ProjectContext 기반
- **Graph-of-Graphs**: R/P/V/D 그래프 연계
- **Greenfield + Brownfield**: 둘 다 자연스럽게 지원

---

## 1. StrategyEngine의 역할 및 철학

### 1.1 CMIS에서의 위치

```
CMIS 전체 파이프라인:

Reality (현재)
  ↓ WorldEngine
R-Graph (구조)
  ↓ PatternEngine
Patterns (메커니즘)
  ↓ StrategyEngine ⭐
Strategies (전략)
  ↓ ValueEngine.simulate_scenario
Projected Values (예측)
  ↓ DecisionEngine (미래)
Decision (선택)
```

**StrategyEngine의 단일 책임**:
- Pattern → Strategy 변환
- Strategy 실행 가능성 평가
- Strategy Portfolio 구성 및 평가

### 1.2 핵심 철학

**1. Pattern-based Strategy Generation**:
```
Matched Patterns + Gap Patterns
  ↓ Pattern Composition Rules
Strategy Candidates
  ↓ Execution Fit + Feasibility
Viable Strategies
```

**원칙**:
- 모든 Strategy는 Pattern 조합으로 표현
- "무엇을 할 것인가"는 Pattern이 정의
- "실행 가능한가"는 Reality/ProjectContext가 판단

**2. Reality-grounded Evaluation**:
```
Strategy Candidate
  + Reality Graph (현재 구조)
  + Project Context (우리 회사 자원)
  ↓ Execution Fit
Feasibility Score
```

**원칙**:
- 모든 평가는 Evidence-based
- ProjectContext 없으면 시장 평균 가정
- Brownfield는 focal_actor 중심 평가

**3. Graph-of-Graphs 연계**:
```
R-Graph: 현재 시장 구조 (WorldEngine)
  +
P-Graph: 패턴 정의 (PatternEngine)
  +
V-Graph: 지표/공식 (ValueEngine)
  ↓ StrategyEngine
D-Graph: 전략/시나리오 (StrategyEngine)
```

---

## 2. 데이터 모델

### 2.1 Goal (목표)

**정의** (cmis.yaml):
```yaml
goal:
  goal_id: "GOAL-001"
  name: "시장 점유율 10% 달성"
  target_metrics:
    - metric_id: "MET-Market_share"
      target_value: 0.10
      target_horizon: "2Y"
  project_context_id: "PRJ-my-company"  # Brownfield
```

**Python 데이터클래스**:
```python
@dataclass
class Goal:
    goal_id: str
    name: str
    target_metrics: List[Dict[str, Any]]
    # [{"metric_id": "MET-Revenue", "target_value": 10000000000, "target_horizon": "2Y"}]
    
    project_context_id: Optional[str] = None
    
    # 제약 조건
    constraints: Dict[str, Any] = field(default_factory=dict)
    # {"max_budget": 5000000000, "max_time": "2Y", "risk_tolerance": "medium"}
```

### 2.2 Strategy (전략)

**정의** (cmis.yaml + 확장):
```yaml
strategy:
  strategy_id: "STR-001"
  name: "구독+프리미엄 전환 전략"
  description: "무료 체험 후 유료 전환, 계층별 가격"
  
  # Pattern 조합
  pattern_composition:
    core_patterns:
      - "PAT-subscription_model"
      - "PAT-freemium_model"
    supporting_patterns:
      - "PAT-tiered_pricing"
      - "PAT-network_effects"
  
  # Execution Requirements
  required_capabilities:
    - technology_domain: "platform_tech"
      maturity_level: "mvp"
  
  required_assets:
    channels:
      online: true
      min_reach: 1000
  
  # Value Assumptions
  key_assumptions:
    - metric_id: "MET-Conversion_rate"
      assumed_value: 0.05
      source: "pattern_benchmark"
```

**Python 데이터클래스**:
```python
@dataclass
class Strategy:
    strategy_id: str
    name: str
    description: str
    
    # Pattern 조합
    core_patterns: List[str]  # Pattern IDs
    supporting_patterns: List[str] = field(default_factory=list)
    
    # Execution Requirements
    required_capabilities: List[Dict[str, Any]] = field(default_factory=list)
    required_assets: Dict[str, Any] = field(default_factory=dict)
    
    # Value Assumptions (Prior/Benchmark 기반)
    key_assumptions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Evaluation Scores
    execution_fit_score: Optional[float] = None
    value_projection: Optional[Dict[str, Any]] = None
    
    # Lineage
    lineage: Dict[str, Any] = field(default_factory=dict)
    # {"from_patterns": [...], "created_at": "...", "generated_by": "strategy_engine"}
```

### 2.3 Scenario (시나리오)

**정의** (cmis.yaml):
```yaml
scenario:
  scenario_id: "SCN-001"
  base_strategy_id: "STR-001"
  name: "공격적 성장 시나리오"
  
  assumptions:
    # Metric 가정
    MET-CAC: 50000  # 고객획득비용
    MET-Conversion_rate: 0.08  # 높은 전환율 가정
    MET-Churn_rate: 0.03  # 낮은 이탈률 가정
  
  parameters:
    marketing_budget_multiplier: 2.0
    pricing_tier_count: 3
```

**Python 데이터클래스**:
```python
@dataclass
class Scenario:
    scenario_id: str
    base_strategy_id: str
    name: str
    
    # Metric 가정
    assumptions: Dict[str, Any]  # metric_id → assumed_value
    
    # 파라미터
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 시뮬레이션 결과 (ValueEngine.simulate_scenario)
    projected_metrics: Optional[Dict[str, Any]] = None
    roi_estimate: Optional[float] = None
```

---

## 3. StrategyEngine API

### 3.1 search_strategies

**시그니처**:
```python
def search_strategies(
    goal: Goal,
    reality_graph: InMemoryGraph,
    project_context_id: Optional[str] = None
) -> List[Strategy]:
    """
    Goal → Strategy 후보 생성
    
    프로세스:
    1. PatternEngine에서 매칭된 패턴 조회
    2. Gap 패턴 조회 (opportunity)
    3. Pattern 조합 규칙 적용
    4. Strategy 후보 생성
    5. Execution Fit 평가
    6. 랭킹 및 필터링
    
    Returns:
        Strategy 리스트 (execution_fit 순)
    """
```

**입력**:
- `goal`: 목표 (target_metrics, horizon, constraints)
- `reality_graph`: 현재 R-Graph (WorldEngine.snapshot)
- `project_context_id`: Brownfield 컨텍스트

**출력**:
- `Strategy` 리스트 (최대 10-20개)
- execution_fit_score 포함
- 랭킹 순 정렬

### 3.2 evaluate_portfolio

**시그니처**:
```python
def evaluate_portfolio(
    strategies: List[Strategy],
    goal: Goal,
    project_context_id: Optional[str] = None
) -> PortfolioEvaluation:
    """
    여러 Strategy를 Portfolio로 평가
    
    프로세스:
    1. Strategy 간 Synergy 계산 (composes_with)
    2. Strategy 간 Conflict 탐지 (conflicts_with)
    3. 자원 경쟁 분석 (예산, 인력, 시간)
    4. Cannibalization 리스크
    5. Portfolio 최적화 (Pareto frontier)
    
    Returns:
        PortfolioEvaluation
    """
```

**입력**:
- `strategies`: Strategy 리스트
- `goal`: 목표
- `project_context_id`: Brownfield

**출력**:
- `PortfolioEvaluation`:
  - synergies: Strategy 간 시너지
  - conflicts: 충돌
  - resource_allocation: 자원 배분
  - pareto_frontier: 최적 조합들

---

## 4. Pattern → Strategy 변환 로직

### 4.1 Pattern Composition Rules

**기본 규칙**:

**1. Single Pattern Strategy**:
```
하나의 Gap Pattern → 하나의 Strategy

예:
  Gap: PAT-freemium_model
  → Strategy: "프리미엄 모델 도입"
     core_patterns: [PAT-freemium_model]
```

**2. Pattern Composition Strategy**:
```
여러 Pattern 조합 → 하나의 Strategy

예:
  Gap: PAT-freemium_model + PAT-tiered_pricing
  → Strategy: "프리미엄 + 계층 가격 전략"
     core_patterns: [PAT-freemium_model, PAT-tiered_pricing]
```

**3. Pattern Enhancement Strategy**:
```
Matched Pattern + Gap Pattern → 강화 전략

예:
  Matched: PAT-subscription_model
  Gap: PAT-network_effects
  → Strategy: "구독 + 네트워크 효과 강화"
     core_patterns: [PAT-subscription_model, PAT-network_effects]
```

### 4.2 Composition Constraints

**composes_with (시너지)**:
```python
# PatternSpec에서 정의
PAT-subscription_model.composes_with = [
    "PAT-freemium_model",
    "PAT-tiered_pricing",
    "PAT-network_effects"
]

# Strategy 생성 시 확인
if pattern_a in pattern_b.composes_with:
    # 조합 가능
    strategy = create_strategy([pattern_a, pattern_b])
```

**conflicts_with (충돌)**:
```python
# PatternSpec에서 정의
PAT-subscription_model.conflicts_with = [
    "PAT-transaction_model"
]

# Strategy 생성 시 필터링
if pattern_a in pattern_b.conflicts_with:
    # 조합 불가 (경고 또는 제외)
```

### 4.3 Strategy Generation Algorithm

**알고리즘**:
```python
def generate_strategy_candidates(
    matched_patterns: List[PatternMatch],
    gap_patterns: List[GapCandidate],
    goal: Goal
) -> List[Strategy]:
    """
    Pattern → Strategy 변환
    
    프로세스:
    1. Single Pattern Strategies (Gap 우선)
    2. Pattern Pair Strategies (composes_with)
    3. Pattern Triple Strategies (선택적)
    4. Goal 적합성 필터링
    5. Execution Fit 사전 평가
    """
    candidates = []
    
    # 1. Single Gap Pattern → Strategy
    for gap in gap_patterns[:10]:  # 상위 10개
        strategy = Strategy(
            strategy_id=f"STR-single-{gap.pattern_id}",
            name=f"{gap.pattern_id} 도입",
            core_patterns=[gap.pattern_id],
            execution_fit_score=gap.execution_fit_score
        )
        candidates.append(strategy)
    
    # 2. Pattern Composition (composes_with)
    for gap in gap_patterns[:5]:
        pattern = pattern_library.get(gap.pattern_id)
        
        for compose_id in pattern.composes_with:
            # compose_id가 이미 매칭됐거나 Gap인지 확인
            strategy = Strategy(
                strategy_id=f"STR-comp-{gap.pattern_id}-{compose_id}",
                name=f"{gap.pattern_id} + {compose_id}",
                core_patterns=[gap.pattern_id, compose_id]
            )
            candidates.append(strategy)
    
    # 3. Goal 적합성 필터링
    filtered = []
    for strategy in candidates:
        if is_relevant_to_goal(strategy, goal):
            filtered.append(strategy)
    
    return filtered
```

---

## 5. Execution Fit 평가

### 5.1 Strategy Execution Fit

**개념**:
```
Strategy Execution Fit = (Pattern Execution Fit의 조합)

Strategy = [Pattern A, Pattern B]
  ↓
Pattern A: execution_fit = 0.8
Pattern B: execution_fit = 0.6
  ↓
Strategy Execution Fit = min(0.8, 0.6) × synergy_factor
                       = 0.6 × 1.1 (composes_with 보너스)
                       = 0.66
```

**계산 로직**:
```python
def calculate_strategy_execution_fit(
    strategy: Strategy,
    pattern_matches: List[PatternMatch],
    gap_patterns: List[GapCandidate],
    project_context: Optional[ProjectContext]
) -> float:
    """
    Strategy의 실행 가능성
    
    규칙:
    1. 각 Pattern의 execution_fit 조회
    2. Bottleneck 원칙: min(execution_fit)
    3. Synergy 보너스: composes_with면 +10%
    4. Conflict 페널티: conflicts_with면 -30%
    """
    pattern_fits = []
    
    for pattern_id in strategy.core_patterns:
        # 매칭된 패턴에서 찾기
        fit = find_pattern_execution_fit(
            pattern_id,
            pattern_matches,
            gap_patterns
        )
        pattern_fits.append(fit)
    
    # Bottleneck
    base_fit = min(pattern_fits)
    
    # Synergy
    synergy = calculate_synergy(strategy.core_patterns)
    
    # Conflict
    conflict_penalty = calculate_conflict_penalty(strategy.core_patterns)
    
    final_fit = base_fit * synergy * (1 - conflict_penalty)
    
    return max(0.0, min(1.0, final_fit))
```

### 5.2 Synergy 계산

**규칙**:
```python
def calculate_synergy(core_patterns: List[str]) -> float:
    """
    Pattern 간 시너지
    
    규칙:
    - 모든 패턴이 composes_with 관계: +15%
    - 일부만 composes_with: +5% ~ +10%
    - 관계 없음: +0%
    """
    if len(core_patterns) == 1:
        return 1.0  # Single pattern, no synergy
    
    # composes_with 관계 카운트
    compose_count = 0
    total_pairs = 0
    
    for i, pattern_a in enumerate(core_patterns):
        for pattern_b in core_patterns[i+1:]:
            total_pairs += 1
            
            spec_a = pattern_library.get(pattern_a)
            if pattern_b in spec_a.composes_with:
                compose_count += 1
    
    if total_pairs == 0:
        return 1.0
    
    compose_ratio = compose_count / total_pairs
    
    # 15% 최대 보너스
    synergy_bonus = compose_ratio * 0.15
    
    return 1.0 + synergy_bonus
```

---

## 6. 구현 아키텍처

### 6.1 전체 구조

```
┌─────────────────────────────────────────────┐
│          StrategyEngine                      │
│  search_strategies()                         │
│  evaluate_portfolio()                        │
└─────────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Strategy │   │Pattern  │   │Execution│
│Generator│   │Composer │   │Evaluator│
└─────────┘   └─────────┘   └─────────┘
    │               │               │
    ▼               ▼               ▼
┌─────────────────────────────────────────────┐
│         Data Layer                           │
│  - PatternEngine (매칭 결과)               │
│  - ProjectContext (자원/제약)              │
│  - ValueEngine (Prior/Benchmark)            │
└─────────────────────────────────────────────┘
```

### 6.2 컴포넌트 설계

**1. StrategyGenerator**:
```python
class StrategyGenerator:
    """
    Pattern → Strategy 변환
    
    역할:
    - Single pattern strategy 생성
    - Pattern composition strategy 생성
    - Goal 적합성 필터링
    """
    
    def generate_from_gaps(
        self,
        gap_patterns: List[GapCandidate],
        matched_patterns: List[PatternMatch],
        goal: Goal
    ) -> List[Strategy]:
        """Gap → Strategy 후보 생성"""
```

**2. PatternComposer**:
```python
class PatternComposer:
    """
    Pattern 조합 규칙
    
    역할:
    - composes_with 관계 활용
    - conflicts_with 체크
    - Synergy 계산
    """
    
    def find_composable_patterns(
        self,
        base_pattern_id: str,
        available_patterns: List[str]
    ) -> List[List[str]]:
        """조합 가능한 패턴 조합 찾기"""
```

**3. ExecutionEvaluator**:
```python
class ExecutionEvaluator:
    """
    Strategy 실행 가능성 평가
    
    역할:
    - Execution Fit 계산
    - 자원 충족도 확인
    - 제약 조건 검증
    """
    
    def evaluate_strategy(
        self,
        strategy: Strategy,
        project_context: Optional[ProjectContext],
        reality_graph: InMemoryGraph
    ) -> float:
        """Strategy Execution Fit"""
```

**4. PortfolioOptimizer**:
```python
class PortfolioOptimizer:
    """
    Portfolio 최적화
    
    역할:
    - 자원 제약 하 최적 조합
    - Pareto frontier 계산
    - Trade-off 분석
    """
    
    def optimize(
        self,
        strategies: List[Strategy],
        constraints: Dict[str, Any]
    ) -> List[PortfolioSolution]:
        """Pareto 최적 Portfolio 찾기"""
```

---

## 7. 실행 가능성 평가 메커니즘

### 7.1 Strategy Execution Fit

**계산 공식**:
```
Strategy Execution Fit = 
    min(Pattern Execution Fits) × 
    synergy_factor × 
    (1 - conflict_penalty) ×
    resource_sufficiency
```

**요소**:
1. **Pattern Execution Fits**: 각 Pattern의 실행 적합도
2. **Synergy Factor**: composes_with 보너스 (1.0 ~ 1.15)
3. **Conflict Penalty**: conflicts_with 페널티 (0 ~ 0.3)
4. **Resource Sufficiency**: 자원 충족도 (0 ~ 1.0)

### 7.2 Resource Sufficiency

**평가 항목**:
```python
resource_sufficiency = (
    capability_match × 0.4 +
    budget_sufficiency × 0.3 +
    time_sufficiency × 0.2 +
    team_sufficiency × 0.1
)
```

**capability_match**:
- Strategy.required_capabilities vs ProjectContext.assets_profile.capability_traits

**budget_sufficiency**:
- 예상 비용 (Pattern benchmark) vs ProjectContext.constraints.max_budget

**time_sufficiency**:
- 예상 기간 vs Goal.target_horizon

**team_sufficiency**:
- 필요 인력 vs ProjectContext.assets_profile.organizational_assets.team_size

---

## 8. Portfolio 평가

### 8.1 Portfolio Evaluation

**데이터 모델**:
```python
@dataclass
class PortfolioEvaluation:
    portfolio_id: str
    strategies: List[Strategy]
    
    # Synergy
    synergies: List[Dict[str, Any]]
    # [{"strategy_a": "STR-001", "strategy_b": "STR-002", "synergy_score": 0.2}]
    
    # Conflict
    conflicts: List[Dict[str, Any]]
    # [{"strategy_a": "STR-001", "strategy_b": "STR-003", "conflict_type": "resource"}]
    
    # 자원 배분
    resource_allocation: Dict[str, Any]
    # {"budget": {"STR-001": 0.6, "STR-002": 0.4}, "team": {...}}
    
    # 종합 평가
    total_execution_fit: float
    expected_roi: Optional[float] = None
    risk_level: str = "unknown"  # "low", "medium", "high"
```

### 8.2 Synergy 탐지

**Pattern 기반 Synergy**:
```python
def detect_synergies(strategies: List[Strategy]) -> List[Dict]:
    """
    Strategy 간 시너지 탐지
    
    규칙:
    1. Pattern composes_with: 강한 시너지
    2. 같은 family: 약한 시너지
    3. 공통 target_metrics: 목표 시너지
    """
    synergies = []
    
    for i, str_a in enumerate(strategies):
        for str_b in strategies[i+1:]:
            # Pattern 기반
            pattern_synergy = check_pattern_synergy(
                str_a.core_patterns,
                str_b.core_patterns
            )
            
            if pattern_synergy > 0:
                synergies.append({
                    "strategy_a": str_a.strategy_id,
                    "strategy_b": str_b.strategy_id,
                    "synergy_score": pattern_synergy,
                    "type": "pattern_composition"
                })
    
    return synergies
```

### 8.3 Conflict 탐지

**자원 충돌**:
```python
def detect_conflicts(
    strategies: List[Strategy],
    total_budget: float,
    total_team: int
) -> List[Dict]:
    """
    Strategy 간 충돌 탐지
    
    유형:
    1. Pattern conflicts_with: 논리적 충돌
    2. 자원 경쟁: 예산/인력 부족
    3. Cannibalization: 같은 고객 타겟
    """
    conflicts = []
    
    # Pattern 충돌
    for str_a in strategies:
        for str_b in strategies:
            if str_a == str_b:
                continue
            
            if check_pattern_conflicts(str_a.core_patterns, str_b.core_patterns):
                conflicts.append({
                    "strategy_a": str_a.strategy_id,
                    "strategy_b": str_b.strategy_id,
                    "conflict_type": "pattern_conflict",
                    "severity": "high"
                })
    
    # 자원 충돌
    total_budget_needed = sum(estimate_cost(s) for s in strategies)
    if total_budget_needed > total_budget:
        conflicts.append({
            "conflict_type": "budget_insufficient",
            "total_needed": total_budget_needed,
            "available": total_budget,
            "severity": "high"
        })
    
    return conflicts
```

---

## 9. 구현 계획

### 9.1 Phase 1: Core Strategy Generation (1주)

**목표**: Pattern → Strategy 기본 변환

**작업**:
1. **데이터 모델** (1일)
   - Goal, Strategy, Scenario dataclass
   - types.py에 추가

2. **StrategyGenerator** (2일)
   - Single pattern strategy
   - Pattern composition
   - Goal 적합성 필터링

3. **PatternComposer** (1일)
   - composes_with 활용
   - conflicts_with 체크

4. **StrategyEngine 기본 구조** (1일)
   - search_strategies() 구현
   - PatternEngine 연계

5. **테스트** (1일)
   - 10개 테스트

**결과**:
- Gap → Strategy 변환
- Pattern 조합 규칙
- 기본 전략 생성

---

### 9.2 Phase 2: Execution Fit & Evaluation (1주)

**목표**: 실행 가능성 평가

**작업**:
1. **ExecutionEvaluator** (2일)
   - Strategy Execution Fit
   - Resource Sufficiency
   - Constraint 검증

2. **PortfolioEvaluator** (2일)
   - Synergy 탐지
   - Conflict 탐지
   - evaluate_portfolio() 구현

3. **통합** (1일)
   - search_strategies에 Execution Fit 추가
   - 랭킹 및 필터링

4. **테스트** (1일)
   - 8개 테스트

**결과**:
- Execution Fit 평가
- Portfolio 평가
- Synergy/Conflict 탐지

---

### 9.3 Phase 3: Value Integration (1주)

**목표**: ValueEngine 연계 및 ROI 예측

**작업**:
1. **Scenario 생성** (2일)
   - Strategy → Scenario 변환
   - Assumptions 자동 생성 (Pattern Benchmark)

2. **ValueEngine 연계** (2일)
   - simulate_scenario() 활용
   - ROI 예측
   - Metric projection

3. **Portfolio ROI** (1일)
   - Portfolio 전체 ROI
   - Trade-off 분석

4. **테스트** (1일)
   - 6개 테스트

**결과**:
- ROI 예측
- Scenario 시뮬레이션
- 정량적 평가

---

## 10. 설계 검증 체크리스트

### CMIS 철학 부합성

- [x] **Model-first**: Strategy는 Pattern 조합 구조
- [x] **Evidence-first**: Execution Fit은 Reality/ProjectContext 기반
- [x] **Graph-of-Graphs**: R/P/V/D 연계
- [x] **Greenfield + Brownfield**: Goal에 project_context_id 선택적

### cmis.yaml API 일치성

- [x] `search_strategies(goal_id, constraints, project_context_id)`
- [x] `evaluate_portfolio(strategy_ids, policy_ref, project_context_id)`
- [x] D-Graph 노드 타입 (goal, strategy, scenario)
- [x] strategy_uses_pattern edge

### 다른 엔진과의 연계

- [x] **PatternEngine**: 매칭 결과 + Gap → Strategy 생성
- [x] **WorldEngine**: Reality Graph → Execution Fit
- [x] **ValueEngine**: Scenario 시뮬레이션 → ROI
- [x] **ProjectContext**: 자원/제약 → Feasibility

---

## 11. 확장성 고려사항

### 11.1 Strategy Template System

**미래 확장**:
```yaml
# config/strategy_templates/aggressive_growth.yaml
strategy_template:
  template_id: "TMPL-aggressive-growth"
  name: "공격적 성장 템플릿"
  
  pattern_requirements:
    core:
      - family: "growth_mechanism_patterns"
        min_count: 2
    supporting:
      - family: "revenue_architecture_patterns"
        min_count: 1
  
  parameter_ranges:
    marketing_multiplier: [1.5, 3.0]
    pricing_discount: [0.1, 0.3]
```

**효과**:
- 도메인별 전략 템플릿
- 재사용 가능한 전략 구조

### 11.2 Learning Integration

**미래 확장**:
```python
# LearningEngine이 Strategy 성과 학습
learning_engine.update_strategy_performance(
    strategy_id="STR-001",
    actual_roi=0.25,
    expected_roi=0.20
)

# StrategyEngine이 학습 결과 활용
strategies = strategy_engine.search_strategies(
    goal,
    use_historical_performance=True  # 과거 성과 반영
)
```

---

## 12. 사용 예시

### 12.1 Greenfield (시장 진입 전략)

```python
# 1. Goal 설정
goal = Goal(
    goal_id="GOAL-market-entry",
    name="온라인 교육 시장 진입",
    target_metrics=[
        {"metric_id": "MET-Market_share", "target_value": 0.05, "target_horizon": "2Y"}
    ],
    constraints={"max_budget": 5000000000}
)

# 2. Reality 분석
snapshot = world_engine.snapshot("Online_Education_KR", "KR")

# 3. Pattern 분석
pattern_matches = pattern_engine.match_patterns(snapshot.graph)
gaps = pattern_engine.discover_gaps(snapshot.graph)

# 4. Strategy 생성
strategies = strategy_engine.search_strategies(
    goal,
    snapshot.graph
)

# 결과: [
#   Strategy("프리미엄 + 계층 가격", execution_fit=0.75),
#   Strategy("구독 + 네트워크 효과", execution_fit=0.68),
#   ...
# ]
```

### 12.2 Brownfield (우리 회사 전략)

```python
# 1. Goal 설정 (Brownfield)
goal = Goal(
    goal_id="GOAL-growth",
    name="매출 2배 성장",
    target_metrics=[
        {"metric_id": "MET-Revenue", "target_value": 24000000000, "target_horizon": "2Y"}
    ],
    project_context_id="PRJ-my-company"
)

# 2. ProjectContext 로딩
project_context = load_project_context("PRJ-my-company")
world_engine.ingest_project_context(project_context)

# 3. Reality + focal_actor
snapshot = world_engine.snapshot(
    "Online_Education_KR",
    "KR",
    project_context_id="PRJ-my-company"
)

# 4. Strategy 생성 (우리 회사 자원 고려)
strategies = strategy_engine.search_strategies(
    goal,
    snapshot.graph,
    project_context_id="PRJ-my-company"
)

# 결과: [
#   Strategy("네트워크 효과 강화", execution_fit=0.85),  # 우리가 할 수 있음
#   Strategy("프리미엄 도입", execution_fit=0.45),  # 자원 부족
#   ...
# ]
```

---

**작성**: 2025-12-11 (진행 중)
**상태**: 설계 50% 완료
**다음**: 나머지 섹션 작성

