# StrategyEngine의 Greenfield vs Brownfield

**작성일**: 2025-12-11
**목적**: Greenfield/Brownfield 정확한 정의 및 StrategyEngine 적용

---

## 정의 (CMIS 철학)

### Greenfield

**정의**:
- **'나'에 대한 정보가 없는 상태**에서 neutral한 시장 분석
- ProjectContext 없음
- focal_actor 없음
- **단, 최소 제약 조건은 입력 가능** (자본 규모, 시간 등)

**질문**:
- "10억 자본으로 이 시장에 진입한다면 어떤 전략이 유효한가?"
- "시장 구조상 어떤 비즈니스 모델이 통하는가?"
- "누가 들어가도 고려해야 할 패턴은?"

**특징**:
- 시장 전체 관점
- 주체 중립적 (focal_actor 없음)
- 최소 제약 (자본, 시간) 반영
- "시장의 법칙" 탐색

**입력 가능한 제약**:
- `budget`: 투자 가능 자본
- `timeline`: 목표 달성 기간
- `team_size_range`: 팀 규모 범위

**예시**:
- "10억 자본으로 교육 시장 진입 전략" (주체 불명, 제약 있음)
- "100억 자본으로 교육 시장 진입 전략" (주체 불명, 제약 있음)
- 컨설턴트가 "자본 규모별" 전략 옵션 보고서 작성
- 투자자가 "투자 규모별" 시장 매력도 평가

---

### Brownfield

**정의**:
- **'나'(focal_actor)에 대한 정의와 정보가 존재**
- ProjectContext 있음 (baseline_state, assets_profile, constraints)
- '나'의 입장에서 시장 분석 및 전략 도출

**질문**:
- "우리 회사가 이 시장에서 취할 수 있는 전략은?"
- "우리의 자산/역량/제약 조건 하에서 뭐가 가능한가?"
- "우리의 baseline에서 목표까지 어떻게 갈 것인가?"

**특징**:
- 특정 주체 관점 (focal_actor)
- 제약 조건 반영
- 실행 가능성 중심

**예시**:
- 우리 회사의 성장 전략
- 우리 회사의 신규 시장 진입 (신규여도 Brownfield!)
- 우리 회사의 사업 확장 (확장이어도 Brownfield!)

---

## 중요: Greenfield ≠ 신규, Brownfield ≠ 확장

### 잘못된 이해 ❌

| 구분 | 잘못된 정의 |
|------|------------|
| Greenfield | 신규 사업 진입 |
| Brownfield | 기존 사업 확장 |

### 올바른 이해 ✅

| 구분 | 올바른 정의 | 핵심 |
|------|-----------|------|
| Greenfield | '나' 없이 시장 분석 | ProjectContext 없음 |
| Brownfield | '나'의 관점에서 분석 | ProjectContext 있음 |

---

## StrategyEngine 적용

### Greenfield Strategy

**입력**:
```python
strategies = strategy_engine.search_strategies(
    goal=goal,
    reality_snapshot=snapshot,
    pattern_matches=matches,
    gaps=gaps,
    project_context=None  # ← Greenfield
)
```

**전략 생성**:
- 시장 전체의 Pattern/Gap 기반
- 제약 조건 없음
- 모든 가능한 전략 탐색

**전략 예시**:
```
STR-001: Subscription model
  - Pattern: PAT-subscription_model
  - Expected ROI: 시장 평균 (Pattern Benchmark)
  - Execution Fit: N/A (focal_actor 없음)
  - 대상: "누구든지 이 시장에 진입한다면"

STR-002: Platform + Network effects
  - Pattern: PAT-platform + PAT-network_effects
  - Expected ROI: 시장 상위 25% (Pattern Benchmark)
  - Execution Fit: N/A
  - 대상: "플랫폼 역량 있는 주체라면"
```

**활용**:
- 시장 보고서
- 투자 검토
- 업계 전반 인사이트

---

### Brownfield Strategy

**입력**:
```python
# 1. ProjectContext 정의 ('나'를 정의)
project_context = ProjectContext(
    project_context_id="PRJ-my-company",
    focal_actor_id="ACT-my-company",
    baseline_state={
        "current_revenue": 5000000000,  # 우리 회사 현재 매출
        "current_customers": 50000,
        "gross_margin": 0.65
    },
    assets_profile={
        "capability_traits": [
            {"technology_domain": "platform_tech", "maturity": "production"}
        ],
        "channels": [{"type": "online", "reach": 100000}],
        "organizational_assets": {"team_size": 30}
    },
    constraints_profile={
        "hard_constraints": [
            {"type": "budget", "threshold": 300000000},  # 3억 예산
            {"type": "timeline", "max_months": 12}
        ]
    }
)

# 2. '나'의 관점에서 시장 분석
world_engine.ingest_project_context(project_context)
snapshot = world_engine.snapshot(
    domain_id, region,
    project_context_id="PRJ-my-company"  # ← Brownfield
)

# 3. '나'의 관점에서 전략 탐색
strategies = strategy_engine.search_strategies(
    goal=goal,
    reality_snapshot=snapshot,
    pattern_matches=matches,
    gaps=gaps,
    project_context=project_context  # ← Brownfield
)
```

**전략 생성**:
- focal_actor 기준 Pattern/Gap
- 제약 조건 필터링 (budget 3억 이내만)
- Execution Fit 계산 (우리 assets로 가능한가?)
- 실행 가능한 전략만

**전략 예시**:
```
STR-101: Build network effects
  - Pattern: PAT-network_effects (Gap)
  - Expected ROI: 우리 baseline에서 2배 성장
  - Execution Fit: 0.75 (우리 platform_tech로 가능)
  - Required Investment: 250000000 (2.5억, 예산 내)
  - 대상: "우리 회사가 실행 가능"

STR-102: Freemium 추가
  - Pattern: PAT-freemium_model
  - Expected ROI: 1.5배 성장
  - Execution Fit: 0.85 (우리 온라인 채널 활용)
  - Required Investment: 100000000 (1억)
  - 대상: "우리 회사에 적합"

(제외됨) STR-X: Vertical integration
  - Pattern: PAT-vertical_integration
  - Execution Fit: 0.3 (우리 역량 부족)
  - Required Investment: 500000000 (예산 초과)
  - 이유: 실행 불가능
```

**활용**:
- 우리 회사 전략 수립
- 실행 계획
- 의사결정

---

## StrategyEngine 설계 반영

### search_strategies() 동작 차이

**Greenfield (project_context=None, constraints 있음)**:
```python
def search_strategies(
    ...,
    project_context=None,
    greenfield_constraints: Optional[Dict[str, Any]] = None
):
    """
    greenfield_constraints 예시:
    {
        "budget": 1000000000,  # 10억 자본
        "timeline_months": 24,  # 2년
        "team_size_range": [10, 50]
    }
    """
    # 1. 모든 Pattern/Gap에서 전략 생성
    all_strategies = generate_all_possible_strategies(
        matched_patterns, gaps
    )
    
    # 2. Goal 필터링
    strategies = filter_by_goal(all_strategies, goal)
    
    # 3. Greenfield Constraints 필터링 (신규)
    if greenfield_constraints:
        strategies = filter_by_greenfield_constraints(
            strategies,
            greenfield_constraints
        )
        # 예: budget 10억 이내 전략만
    
    # 4. Pattern Benchmark 기반 ROI
    for strategy in strategies:
        strategy.expected_outcomes = predict_from_benchmarks(strategy)
        strategy.execution_fit_score = None  # focal_actor 없음
    
    # 5. ROI 기준 정렬
    strategies.sort(key=lambda s: s.expected_outcomes["roi"], reverse=True)
    
    return strategies
```

**Brownfield (project_context 있음)**:
```python
def search_strategies(..., project_context):
    # 1. focal_actor 중심 Pattern/Gap에서 전략 생성
    focal_strategies = generate_strategies_for_focal_actor(
        matched_patterns, gaps, project_context.focal_actor_id
    )
    
    # 2. Hard Constraints 필터링
    strategies = filter_by_constraints(
        focal_strategies,
        project_context.constraints_profile["hard_constraints"]
    )
    
    # 3. Execution Fit 계산
    for strategy in strategies:
        strategy.execution_fit_score = calculate_execution_fit(
            strategy,
            project_context  # assets_profile 활용
        )
    
    # 4. baseline_state 기반 ROI (우리 회사 기준)
    for strategy in strategies:
        strategy.expected_outcomes = predict_from_baseline(
            strategy,
            project_context.baseline_state
        )
    
    # 5. Soft Preferences 반영
    for strategy in strategies:
        strategy.adjusted_score = adjust_by_preferences(
            strategy,
            project_context.preference_profile
        )
    
    # 6. Execution Fit × adjusted_score 정렬
    strategies.sort(
        key=lambda s: s.execution_fit_score * s.adjusted_score,
        reverse=True
    )
    
    return strategies
```

---

## 예시 시나리오 (수정)

### 시나리오 A: 시장 보고서 작성 (Greenfield)

**역할**: 컨설턴트, 투자자, 연구자

**질문**:
- "10억 자본으로 한국 성인 교육 시장에 진입한다면?"
- "100억 자본으로 진입한다면?"
- "어떤 전략 패턴이 성공 확률이 높은가?"

**프로세스**:
```python
# ProjectContext 없이 시장 분석
snapshot = world_engine.snapshot("Adult_Language_Education_KR", "KR")
matches = pattern_engine.match_patterns(snapshot.graph)
gaps = pattern_engine.discover_gaps(snapshot.graph)

# Greenfield 전략 (neutral, 제약 있음)
goal = Goal(
    goal_id="GOAL-market-entry-10B",
    name="10억 자본 시장 진입",
    target_metrics=[
        {"metric_id": "MET-Revenue", "operator": ">", "value": 5000000000, "horizon": "3y"}
    ]
)

# Greenfield Constraints (주체는 없지만 제약은 있음)
greenfield_constraints = {
    "budget": 1000000000,  # 10억 자본
    "timeline_months": 36,  # 3년
    "team_size_range": [5, 20]  # 소규모 팀
}

strategies = strategy_engine.search_strategies(
    goal=goal,
    reality_snapshot=snapshot,
    pattern_matches=matches,
    gaps=gaps,
    project_context=None,  # ← Greenfield (주체 없음)
    greenfield_constraints=greenfield_constraints  # ← 제약 있음
)

# 결과: 자본 10억 규모에 맞는 전략
# STR-001: Asset-light + Subscription (투자: 8억, 예상 ROI: 5배)
# STR-002: Marketplace model (투자: 5억, 예상 ROI: 3배)
# (제외) STR-X: Platform + Heavy marketing (투자: 50억 필요 → 제약 위반)
```

**다른 자본 규모**:
```python
# 100억 자본 시나리오
greenfield_constraints_large = {
    "budget": 10000000000,  # 100억
    "timeline_months": 36,
    "team_size_range": [50, 200]  # 대규모 팀
}

strategies_large = strategy_engine.search_strategies(
    ...,
    greenfield_constraints=greenfield_constraints_large
)

# 결과: 자본 100억 규모 전략
# STR-101: Platform + Vertical integration (투자: 80억, ROI: 10배)
# STR-102: Multi-sided marketplace (투자: 60억, ROI: 8배)
```

**특징**:
- 주체 중립적 (누가 해도 동일한 분석)
- 자본 규모별 전략 차별화
- Execution Fit 없음 (focal_actor 없음)
- 시장 평균 ROI

**전략 특징**:
- 주체 중립적
- 시장 평균 ROI
- Execution Fit 없음
- "누구든지" 관점

---

### 시나리오 B: 우리 회사 신규 진입 (Brownfield)

**역할**: 우리 회사 경영진

**질문**:
- "우리 회사가 교육 시장에 진입한다면?"
- "우리의 자산/역량으로 뭐가 가능한가?"

**프로세스**:
```python
# ProjectContext 정의 (우리 회사 = '나')
project_context = ProjectContext(
    project_context_id="PRJ-our-new-venture",
    baseline_state={
        "current_revenue": 0,  # 신규 진입이지만
        "current_customers": 0  # Brownfield (우리 정보 있음)
    },
    assets_profile={
        "capability_traits": [
            {"technology_domain": "AI_ML", "maturity": "production"}  # 우리 강점
        ],
        "brand_assets": {"brand_awareness": "medium"},  # 우리 브랜드
        "organizational_assets": {"team_size": 50}      # 우리 팀
    },
    constraints_profile={
        "hard_constraints": [
            {"type": "budget", "threshold": 2000000000}  # 우리 예산 20억
        ]
    }
)

# '나'의 관점에서 시장 분석
world_engine.ingest_project_context(project_context)
snapshot = world_engine.snapshot(
    "Adult_Language_Education_KR", "KR",
    project_context_id="PRJ-our-new-venture"  # ← Brownfield
)

matches = pattern_engine.match_patterns(snapshot.graph, "PRJ-our-new-venture")
gaps = pattern_engine.discover_gaps(snapshot.graph, "PRJ-our-new-venture")

# 우리 회사 전략 탐색
goal = Goal(
    goal_id="GOAL-our-entry",
    target_metrics=[
        {"metric_id": "MET-Revenue", "operator": ">", "value": 5000000000, "horizon": "2y"}
    ],
    project_context_id="PRJ-our-new-venture"
)

strategies = strategy_engine.search_strategies(
    goal=goal,
    reality_snapshot=snapshot,
    pattern_matches=matches,
    gaps=gaps,
    project_context=project_context  # ← Brownfield
)

# 결과: 우리 회사에 맞는 전략
# "우리 AI 역량을 활용한 맞춤형 튜터링 + 구독 모델"
# Execution Fit: 0.85 (우리 AI_ML 역량 활용)
```

**전략 특징**:
- 우리 회사 특화
- 우리 baseline 기준 ROI
- Execution Fit 높음 (우리 assets 활용)
- 예산 20억 이내만

---

### 시나리오 C: 우리 회사 기존 사업 확장 (Brownfield)

**역할**: 우리 회사 경영진

**질문**:
- "우리의 구독 서비스를 어떻게 확장할까?"
- "우리가 가진 50억 매출에서 100억까지 어떻게 갈까?"

**프로세스**:
```python
# ProjectContext (우리 = 기존 사업자)
project_context = ProjectContext(
    project_context_id="PRJ-our-expansion",
    baseline_state={
        "current_revenue": 5000000000,  # 우리 현재
        "current_customers": 50000,
        "gross_margin": 0.65
    },
    assets_profile={
        "existing_channels": ["online", "mobile_app"],  # 우리가 가진 채널
        "customer_data": 50000,                         # 우리 고객 데이터
        "brand_awareness": "medium"                     # 우리 브랜드
    },
    constraints_profile={
        "hard_constraints": [
            {"type": "budget", "threshold": 500000000}  # 확장 예산 5억
        ]
    }
)

# (나머지 동일)
strategies = strategy_engine.search_strategies(..., project_context)

# 결과: 우리 회사 확장 전략
# "우리 고객 데이터를 활용한 추천 시스템 + 네트워크 효과"
# Execution Fit: 0.90 (우리 기존 자산 최대 활용)
```

---

## 핵심 차이

| 구분 | Greenfield | Brownfield |
|------|-----------|-----------|
| **ProjectContext** | 없음 | 있음 |
| **focal_actor** | 없음 | 있음 (우리) |
| **baseline_state** | 없음 | 우리 현재 상태 |
| **assets_profile** | 없음 | 우리 자산/역량 |
| **제약 조건** | **최소 제약만** (자본, 시간) | 우리 전체 제약 |
| **질문** | "N억으로 시장 진입 시 통하는 것은?" | "우리가 할 수 있는 것은?" |
| **전략 관점** | 시장 전체 (주체 중립) | 우리 회사 |
| **ROI 기준** | 시장 평균 | 우리 baseline |
| **Execution Fit** | N/A (주체 없음) | 계산됨 (우리 assets) |
| **활용** | 시장 이해, 자본별 옵션 | 실행 계획, 의사결정 |

---

## StrategyEngine 구현 시 고려사항

### 1. Execution Fit 계산 여부

```python
if project_context is None:
    # Greenfield: Execution Fit 계산 안 함
    strategy.execution_fit_score = None
else:
    # Brownfield: Execution Fit 필수
    strategy.execution_fit_score = calculate_execution_fit(
        strategy,
        project_context
    )
```

### 2. ROI 예측 방식

**Greenfield**:
```python
# Pattern Benchmark만 사용
roi = predict_from_pattern_benchmarks(strategy.pattern_composition)
# → 시장 평균 ROI
```

**Brownfield**:
```python
# baseline_state에서 시작
roi = predict_from_baseline(
    strategy,
    project_context.baseline_state,
    project_context.assets_profile
)
# → 우리 회사 기준 ROI
```

### 3. Constraint 필터링

**Greenfield**:
```python
# 최소 제약 (자본, 시간)만 반영
if greenfield_constraints:
    strategies = filter_by_greenfield_constraints(
        all_strategies,
        greenfield_constraints  # {"budget": 1000000000, "timeline_months": 24}
    )
else:
    strategies = all_strategies  # 제약 없으면 전체
```

**Brownfield**:
```python
# Hard Constraints 필터링
strategies = filter_by_constraints(
    all_strategies,
    project_context.constraints_profile["hard_constraints"]
)
```

### 4. 정렬 기준

**Greenfield**:
```python
# ROI만
strategies.sort(key=lambda s: s.expected_outcomes["roi"], reverse=True)
```

**Brownfield**:
```python
# Execution Fit × ROI
strategies.sort(
    key=lambda s: s.execution_fit_score * s.expected_outcomes["roi"],
    reverse=True
)
```

---

## 용어 정리

### "신규 진입"의 두 경우

**Case 1: 시장 보고서 (Greenfield)**:
- "교육 시장에 진입하려면 어떤 전략이 있을까?" (주체 불명)
- ProjectContext 없음

**Case 2: 우리 회사 진입 (Brownfield)**:
- "우리 회사가 교육 시장에 진입하려면?" (주체 명확)
- ProjectContext 있음

→ **신규 여부가 아니라 '나'의 존재 여부가 기준!**

---

**작성**: 2025-12-11
**상태**: 정의 명확화 완료 ✅
**목적**: StrategyEngine 설계 정확성 확보

