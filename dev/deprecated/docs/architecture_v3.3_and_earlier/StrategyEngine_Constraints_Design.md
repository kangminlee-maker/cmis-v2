# StrategyEngine Constraints 설계

**작성일**: 2025-12-11
**목적**: Greenfield/Brownfield 제약 조건 처리

---

## 제약 조건의 두 종류

### 1. Greenfield Constraints (최소 제약)

**정의**:
- FocalActorContext 없을 때 사용
- 주체 중립적 제약
- 자본, 시간, 팀 규모 범위

**구조**:
```python
greenfield_constraints = {
    "budget": 1000000000,         # 투자 가능 자본 (필수)
    "timeline_months": 24,         # 목표 기간 (선택, 기본 36)
    "team_size_range": [10, 50],   # 팀 규모 범위 (선택)
    "min_roi": 2.0                 # 최소 ROI (선택, 기본 1.5)
}
```

**특징**:
- 간단함 (3-4개 필드)
- 주체 무관
- 자본 규모가 핵심

---

### 2. Brownfield Constraints (전체 제약)

**정의**:
- FocalActorContext.constraints_profile 사용
- 우리 회사 특화 제약
- 자본, 시간, 팀, 기술, 시장, 규제 등

**구조**:
```python
project_context.constraints_profile = {
    "hard_constraints": [
        {"type": "budget", "threshold": 500000000},
        {"type": "timeline", "max_months": 12},
        {"type": "team_size", "max": 30},
        {"type": "technology", "must_use": ["existing_platform"]},
        {"type": "market", "avoid_segments": ["K12"]},
        {"type": "regulatory", "compliance": ["data_privacy_KR"]}
    ],
    "soft_preferences": [
        {"type": "risk_appetite", "level": "low"},
        {"type": "prefer_patterns", "ids": ["PAT-subscription_model"]},
        {"type": "execution_speed", "prefer": "fast"}
    ]
}
```

**특징**:
- 복잡함 (6+ 타입)
- 우리 회사 특화
- assets_profile과 연계

---

## 필터링 로직

### Greenfield: filter_by_greenfield_constraints()

```python
def filter_by_greenfield_constraints(
    strategies: List[Strategy],
    greenfield_constraints: Dict[str, Any]
) -> List[Strategy]:
    """
    Greenfield 제약 필터링

    간단한 제약만:
    - budget
    - timeline
    - team_size_range
    """
    filtered = []

    budget_limit = greenfield_constraints.get("budget")
    timeline_limit = greenfield_constraints.get("timeline_months")
    team_range = greenfield_constraints.get("team_size_range")

    for strategy in strategies:
        outcomes = strategy.expected_outcomes

        # Budget
        if budget_limit:
            required = outcomes.get("required_investment", 0)
            if required > budget_limit:
                continue  # 제외

        # Timeline
        if timeline_limit:
            required_months = outcomes.get("required_timeline_months", 36)
            if required_months > timeline_limit:
                continue

        # Team size
        if team_range:
            required_team = outcomes.get("required_team_size", 10)
            if required_team < team_range[0] or required_team > team_range[1]:
                continue

        filtered.append(strategy)

    return filtered
```

---

### Brownfield: filter_by_brownfield_constraints()

```python
def filter_by_brownfield_constraints(
    strategies: List[Strategy],
    project_context: FocalActorContext
) -> List[Strategy]:
    """
    Brownfield 제약 필터링

    복잡한 제약:
    - hard_constraints (모든 타입)
    - assets_profile 충족도 (Execution Fit)
    """
    filtered = []

    hard_constraints = project_context.constraints_profile.get("hard_constraints", [])

    for strategy in strategies:
        violates = False

        for constraint in hard_constraints:
            ctype = constraint["type"]

            if ctype == "budget":
                required = strategy.expected_outcomes.get("required_investment", 0)
                if required > constraint["threshold"]:
                    violates = True
                    break

            elif ctype == "timeline":
                required = strategy.expected_outcomes.get("required_timeline_months", 36)
                if required > constraint["max_months"]:
                    violates = True
                    break

            elif ctype == "team_size":
                required = strategy.expected_outcomes.get("required_team_size", 10)
                if required > constraint["max"]:
                    violates = True
                    break

            elif ctype == "technology":
                # 기술 제약 (우리 기존 플랫폼 사용해야 함)
                if constraint.get("must_use"):
                    # Strategy가 기존 기술 활용하는지 확인
                    pass

            # ... 기타 제약 타입

        if not violates:
            filtered.append(strategy)

    return filtered
```

---

## CLI 명령어 반영

### Greenfield 명령어

**structure-analysis (기존)**:
```bash
# 제약 없음
cmis structure-analysis --domain Adult_Language_Education_KR --region KR

# 제약 있음 (개선)
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --budget 1000000000 \
  --timeline 24
```

**opportunity-discovery**:
```bash
cmis opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  --budget 1000000000  # Greenfield constraint
```

**strategy-design (미래, Greenfield)**:
```bash
cmis strategy-design \
  --domain Adult_Language_Education_KR \
  --region KR \
  --goal "revenue_3y > 5B" \
  --budget 1000000000 \
  --timeline 36
```

---

### Brownfield 명령어

**structure-analysis**:
```bash
# FocalActorContext 사용 (제약 자동 반영)
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --project-context PRJ-my-company  # ← constraints_profile 자동 사용
```

**strategy-design (미래, Brownfield)**:
```bash
cmis strategy-design \
  --domain Adult_Language_Education_KR \
  --region KR \
  --goal "revenue_3y > 10B" \
  --project-context PRJ-my-company  # ← 우리 회사 관점
```

---

## 사용 예시

### 컨설턴트: "자본별 진입 전략 보고서"

```python
# 10억 자본 시나리오
strategies_10B = strategy_engine.search_strategies(
    ...,
    greenfield_constraints={"budget": 1000000000}
)

# 50억 자본 시나리오
strategies_50B = strategy_engine.search_strategies(
    ...,
    greenfield_constraints={"budget": 5000000000}
)

# 100억 자본 시나리오
strategies_100B = strategy_engine.search_strategies(
    ...,
    greenfield_constraints={"budget": 10000000000}
)

# 보고서: "자본 규모별 최적 전략"
# - 10억: Asset-light model 추천
# - 50억: Platform + Network effects
# - 100억: Vertical integration + Ecosystem
```

---

### 스타트업: "우리 회사 전략"

```python
# 우리 회사 = Seed 투자 받은 스타트업
project_context = FocalActorContext(
    baseline_state={"current_revenue": 100000000},  # 1억
    assets_profile={
        "capability_traits": [{"technology": "AI_ML"}],  # 우리 강점
        "team_size": 10
    },
    constraints_profile={
        "hard_constraints": [
            {"type": "budget", "threshold": 500000000}  # Seed 5억
        ]
    }
)

# 우리 관점 전략
strategies = strategy_engine.search_strategies(
    ...,
    project_context=project_context  # Brownfield
)

# 결과: "우리 AI 역량 + 구독 모델" (Execution Fit 0.85)
```

---

## 설계 원칙

### 1. Greenfield는 "제약 없음"이 아님

- **잘못**: Greenfield = 무한 자본, 무한 시간
- **올바름**: Greenfield = 주체 중립 + 최소 제약

### 2. 자본 규모는 전략을 근본적으로 바꿈

- 10억: Asset-light, MVP
- 100억: Platform, Ecosystem
- 1,000억: Vertical integration, Market dominance

### 3. Greenfield도 실용적이어야 함

- "모든 가능한 전략" (X)
- "주어진 자본으로 가능한 전략" (O)

---

## API 시그니처 (최종)

```python
def search_strategies(
    goal: Goal,
    reality_snapshot: RealityGraphSnapshot,
    pattern_matches: List[PatternMatch],
    gaps: List[GapCandidate],
    project_context: Optional[FocalActorContext] = None,
    greenfield_constraints: Optional[Dict[str, Any]] = None,
    max_strategies: int = 10
) -> List[Strategy]:
    """
    전략 탐색

    Greenfield:
        project_context=None,
        greenfield_constraints={"budget": 1000000000}

    Brownfield:
        project_context=FocalActorContext(...),
        greenfield_constraints=None (무시됨)

    Validation:
        if project_context and greenfield_constraints:
            raise ValueError("Cannot use both")
    """
```

---

**작성**: 2025-12-11
**상태**: Greenfield 제약 설계 완료 ✅
**핵심**: Greenfield도 자본/시간 제약 입력 가능
