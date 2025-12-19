# Pattern Engine v2.0 최종 설계

**버전**: v2.0
**업데이트**: 2025-12-11
**상태**: 완성 (100%)

---

## Executive Summary

Pattern Engine v2.0은 **Trait 기반 비즈니스 패턴 인식 및 Gap 발굴** 엔진입니다.

**완성도**: 100%
**테스트**: 53/53 (100%)
**Pattern**: 23개 (5개 Family)

---

## 1. 핵심 기능

### 1.1 Pattern 매칭

- **Trait 기반**: Ontology lock-in 최소화
- **23개 Pattern**: 5개 Family 균형 배치
- **이중 평가**: Structure Fit + Execution Fit

### 1.2 Gap Discovery

- **Context Archetype**: 6개 정의
- **Expected Pattern Set**: core/common/rare
- **Feasibility 평가**: high/medium/low

### 1.3 Greenfield/Brownfield

- **Greenfield**: Structure Fit만
- **Brownfield**: Structure Fit × Execution Fit

---

## 2. 데이터 모델

### 2.1 PatternSpec (13개 필드)

```python
@dataclass
class PatternSpec:
    pattern_id: str
    name: str
    family: str
    description: str

    trait_constraints: Dict  # Trait 기반 정의
    graph_structure: Dict
    quantitative_bounds: Dict

    composes_with: List[str]
    conflicts_with: List[str]
    specializes: Optional[str]

    benchmark_metrics: List[str]
    suited_for_contexts: List[str]

    # v1.1 추가
    required_capabilities: List[Dict]
    required_assets: Dict
    constraint_checks: List[str]
```

### 2.2 PatternMatch (8개 필드)

```python
@dataclass
class PatternMatch:
    pattern_id: str
    description: str
    structure_fit_score: float
    execution_fit_score: Optional[float]
    combined_score: float
    evidence: Dict
    anchor_nodes: Dict
    instance_scope: Optional[Dict]
```

---

## 3. 아키텍처

### 3.1 컴포넌트

```
PatternLibrary  → PatternMatcher  → PatternScorer
YAML 로딩         Trait/Graph 매칭    Fit 계산
     ↓                 ↓                 ↓
PatternEngineV2  → GapDiscoverer  → ContextArchetype
Facade API         Gap 탐지           Archetype 결정
```

### 3.2 파일 구조

```
cmis_core/
├── pattern_engine_v2.py      # Facade
├── pattern_library.py         # YAML 로딩
├── pattern_matcher.py         # 매칭
├── pattern_scorer.py          # 점수 계산
├── gap_discoverer.py          # Gap 발굴
└── context_archetype.py       # Archetype

config/
├── patterns/*.yaml            # 23개 Pattern
└── archetypes/*.yaml          # 6개 Archetype
```

---

## 4. Pattern 정의 (23개)

### Business Model (6개)
1. PAT-subscription_model
2. PAT-platform_business_model
3. PAT-transaction_model
4. PAT-freemium_model
5. PAT-marketplace_model
6. PAT-franchise_model

### Value Chain (5개)
7. PAT-asset_light_model
8. PAT-vertical_integration
9. PAT-horizontal_specialization
10. PAT-capital_intensive_model
11. PAT-outsourcing_model

### Growth Mechanism (5개)
12. PAT-network_effects
13. PAT-viral_growth
14. PAT-land_and_expand
15. PAT-ecosystem_lock_in
16. PAT-scale_economies

### Competitive Structure (4개)
17. PAT-market_concentration
18. PAT-fragmented_market
19. PAT-winner_take_all
20. PAT-niche_specialization

### Revenue Architecture (3개)
21. PAT-recurring_revenue
22. PAT-usage_based_pricing
23. PAT-tiered_pricing

---

## 5. Context Archetype (6개)

1. ARCH-digital_service_KR
2. ARCH-education_platform_KR
3. ARCH-marketplace_global
4. ARCH-b2b_saas
5. ARCH-platform_global
6. ARCH-simple_digital

---

## 6. API

### 6.1 match_patterns()

```python
matches = pattern_engine.match_patterns(
    graph,
    focal_actor_context_id=None  # Greenfield
)

# Brownfield
matches = pattern_engine.match_patterns(
    graph,
    focal_actor_context_id="PRJ-001"
)
```

### 6.2 discover_gaps()

```python
gaps = pattern_engine.discover_gaps(
    graph,
    focal_actor_context_id="PRJ-001",
    precomputed_matches=matches
)
```

---

## 7. 테스트

- Phase 1: 21개
- Phase 2: 22개
- Phase 3: 10개
- **총 53개 (100%)**

---

**작성**: 2025-12-11
**상태**: v2.0 완성
**기반**: Phase 1/2/3 통합
