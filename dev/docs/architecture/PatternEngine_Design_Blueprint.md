# PatternEngine 설계 청사진 (Design Blueprint)

**작성일**: 2025-12-10  
**버전**: v1.0  
**상태**: 설계안 (Design Proposal)

---

## 📋 목차

1. [설계 철학](#설계-철학)
2. [아키텍처 개요](#아키텍처-개요)
3. [핵심 설계 결정](#핵심-설계-결정)
4. [Pattern 분류 체계](#pattern-분류-체계)
5. [Pattern 정의 방식](#pattern-정의-방식)
6. [매칭 알고리즘](#매칭-알고리즘)
7. [Gap Discovery 전략](#gap-discovery-전략)
8. [구현 계획](#구현-계획)
9. [확장성 고려사항](#확장성-고려사항)

---

## 🎯 설계 철학

### CMIS 핵심 원칙 반영

PatternEngine은 다음 CMIS 철학을 준수합니다:

#### 1. **Model-first, Number-second**
- Pattern은 "구조/메커니즘"을 표현하는 모델
- 숫자(Benchmark, 범위)는 Pattern의 결과물이지 정의가 아님
- Pattern 매칭은 구조 적합도(structure_fit)가 우선

#### 2. **Evidence-first, Prior-last**
- Pattern 매칭은 R-Graph의 Evidence(Actor/Event/MoneyFlow) 기반
- Pattern Benchmark는 ValueEngine에서 Evidence 보강 용도로 사용
- Pattern 자체는 추측이 아닌 "관찰된 구조"를 표현

#### 3. **Trait 기반 패턴 정의 (Ontology lock-in 최소화)**
- Pattern은 **Trait 조합**으로 정의 (고정 타입 ❌)
- 새 Pattern 추가 시 Ontology 수정 불필요
- 도메인/산업별 확장 가능

#### 4. **Graph-of-Graphs (R ↔ P ↔ V ↔ D)**
- Pattern Graph는 Reality Graph를 추상화
- Pattern은 Value Graph(Metric Benchmark) 연결
- Pattern은 Decision Graph(Strategy) 생성 입력

#### 5. **Monotonic Improvability**
- Pattern 추가 시 시스템 품질 향상 (기존 기능 유지)
- Pattern Learning (Outcome 반영) 시 점진적 개선

---

## 🏗️ 아키텍처 개요

### Layer 구조 (개선)

```
┌─────────────────────────────────────────────────────────────┐
│                  PatternEngine (Facade)                      │
│  - match_patterns(graph, project_context_id, precomputed)   │
│  - discover_gaps(graph, project_context_id, precomputed)    │
└────────────┬────────────────────────────────────────────────┘
             │
   ┌─────────┴──────────────────────┐
   │     PatternPipeline            │
   │  (Filter→Match→Score→Persist)  │
   └─────────┬──────────────────────┘
             │
   ┌─────────┴─────────────────────────┐
   │                                   │
┌──▼────────────┐  ┌──▼──────────────┐  ┌──▼────────────┐
│ PatternIndex   │  │ PatternMatcher  │  │ PatternScorer │
│ - Trait Index  │  │ - Graph 구조    │  │ - Structure   │
│ - Family Filter│  │ - Constraint    │  │ - Execution   │
└────────┬───────┘  └─────────┬───────┘  └───────┬───────┘
         │                    │                  │
         │          ┌─────────▼──────────┐       │
         │          │  GapDiscoverer     │       │
         │          │  - Expected vs     │       │
         │          │  - Feasibility     │       │
         │          └─────────┬──────────┘       │
         │                    │                  │
    ┌────▼────────────────────▼──────────────────▼────┐
    │                                                  │
┌───▼──────────┐    ┌────▼────────┐   ┌────▼────────┐
│PatternLibrary│    │ P-Graph     │   │Lineage      │
│- YAML 정의    │ => │- pattern    │   │- 추적/기록   │
│- Benchmark   │    │- instance   │   └─────────────┘
│- Validation  │    │- family     │
└──────────────┘    └─────────────┘
```

### 주요 컴포넌트

#### 1. **PatternEngine (Facade)**
- 외부 API 제공 (match_patterns, discover_gaps)
- PatternMatcher, GapDiscoverer 조율
- Project Context 통합

#### 2. **PatternMatcher**
- Trait 기반 매칭
- Graph 구조 매칭
- Scoring (structure_fit, execution_fit)

#### 3. **GapDiscoverer**
- Missing Pattern 탐지
- Opportunity 발굴
- Feasibility 평가 (Project Context 기반)

#### 4. **PatternLibrary**
- Pattern 정의 저장소 (YAML + Code)
- 23+ Built-in Patterns
- Custom Pattern 등록

#### 5. **P-Graph Store**
- Runtime Pattern Graph
- Learning Engine 업데이트
- Pattern 관계 (composes_with, conflicts_with)

---

## 🔑 핵심 설계 결정

### 결정 1: Pattern 정의 방식 (Trait 기반)

**문제**: Pattern을 어떻게 정의할 것인가?

**선택지**:
1. **고정 타입** (Ontology에 Pattern 타입 추가)
2. **Trait 조합** (CMIS 철학)
3. **하이브리드** (Core Pattern은 타입, 나머지는 Trait)

**결정**: **Trait 조합** (선택지 2)

**이유**:
- CMIS 철학: "Trait 기반 패턴/모델 정의로 Ontology lock-in 최소화"
- 확장성: 새 Pattern 추가 시 Ontology 수정 불필요
- 유연성: 도메인별 Pattern 추가 용이

**구현**:
```yaml
pattern:
  pattern_id: "PAT-subscription_model"
  name: "구독형 비즈니스 모델"
  
  # Trait 조합으로 정의
  trait_constraints:
    money_flow:
      required_traits:
        revenue_model: "subscription"
        payment_recurs: true
      optional_traits:
        recurrence: ["monthly", "yearly"]
  
  # Graph 구조로 정의
  graph_structure:
    requires:
      - node_type: "money_flow"
        min_count: 1
        traits: { revenue_model: "subscription" }
      - node_type: "actor"
        role: "payer"
        min_count: 100  # 최소 고객 수
```

### 결정 2: Matching 알고리즘 (2-Stage Scoring)

**문제**: Pattern 매칭을 어떻게 점수화할 것인가?

**결정**: **2-Stage Scoring**

**Stage 1: Structure Fit** (모든 경우)
- R-Graph에서 Pattern 구조 적합도 계산
- Trait 일치도 + Graph 구조 일치도
- 0.0 ~ 1.0 점수

**Stage 2: Execution Fit** (Project Context 있을 때만)
- Project Context의 capability_traits와 비교
- Pattern 실행 가능성 평가
- 0.0 ~ 1.0 점수

**Combined Score** = structure_fit × execution_fit

**이유**:
- Greenfield: structure_fit만으로 객관적 분석
- Brownfield: execution_fit로 실행 가능성 고려
- CMIS 철학: Evidence-first (구조 우선), Prior-last (실행 가능성은 보조)

### 결정 3: Pattern 계층 구조 (Family + Pattern)

**문제**: 23+ Pattern을 어떻게 조직화할 것인가?

**결정**: **2-Level 계층**

**Level 1: Pattern Family** (5개)
```
1. business_model_patterns (비즈니스 모델)
2. value_chain_patterns (가치사슬)
3. growth_mechanism_patterns (성장 메커니즘)
4. competitive_structure_patterns (경쟁 구조)
5. revenue_architecture_patterns (수익 구조)
```

**Level 2: Pattern** (23+)
- 각 Family 내 4~6개 Pattern
- Pattern 간 관계: composes_with, conflicts_with, specializes

**이유**:
- 탐색성: Family 단위로 Pattern 검색
- 조합성: Family 간 Pattern 조합 가능
- 확장성: Family 추가로 확장

### 결정 4: Gap Discovery 방식 (Template Matching)

**문제**: Missing Pattern을 어떻게 탐지할 것인가?

**결정**: **Template-based Gap Detection**

**방법**:
1. **Context Archetype** 정의 (시장/산업별 전형)
2. **Expected Pattern Set** 정의 (Context별 권장 Pattern)
3. **Gap = Expected - Matched**

**예시**:
```yaml
context_archetype:
  archetype_id: "ARCH-digital_service_KR"
  name: "한국 디지털 서비스 시장"
  
  expected_patterns:
    core:  # 거의 항상 존재해야 함
      - "PAT-subscription_model"
      - "PAT-freemium_model"
    common:  # 자주 관찰됨
      - "PAT-network_effects"
      - "PAT-platform_dynamics"
    rare:  # 드물지만 기회
      - "PAT-multi_sided_market"
```

**Gap Candidate**:
- Expected Pattern이지만 R-Graph에 없음
- Feasibility = execution_fit (Project Context 기반)

---

## 📊 Pattern 분류 체계

### 23개 Pattern 목록 (초안)

#### Family 1: Business Model Patterns (6개)

| Pattern ID | 이름 | 핵심 Trait |
|------------|------|-----------|
| PAT-subscription_model | 구독형 모델 | revenue_model=subscription |
| PAT-transaction_model | 거래형 모델 | revenue_model=one_off |
| PAT-freemium_model | 프리미엄 모델 | freemium=true |
| PAT-platform_business_model | 플랫폼 모델 | institution_type=online_platform |
| PAT-marketplace_model | 마켓플레이스 | multi_sided=true |
| PAT-franchise_model | 프랜차이즈 | franchise=true |

#### Family 2: Value Chain Patterns (5개)

| Pattern ID | 이름 | 핵심 특징 |
|------------|------|-----------|
| PAT-vertical_integration | 수직 통합 | 가치사슬 다단계 소유 |
| PAT-horizontal_specialization | 수평 전문화 | 단일 단계 집중 |
| PAT-asset_light_model | 자산 경량화 | marginal_cost_profile=low |
| PAT-capital_intensive_model | 자본 집약형 | capex_ratio=high |
| PAT-outsourcing_model | 외주 중심 | outsourcing_ratio=high |

#### Family 3: Growth Mechanism Patterns (5개)

| Pattern ID | 이름 | 핵심 메커니즘 |
|------------|------|--------------|
| PAT-network_effects | 네트워크 효과 | value_per_user ∝ total_users |
| PAT-viral_growth | 바이럴 성장 | k_factor > 1 |
| PAT-land_and_expand | 확장 전략 | expansion_revenue_ratio > 0.3 |
| PAT-ecosystem_lock_in | 생태계 잠금 | switching_cost=high |
| PAT-scale_economies | 규모의 경제 | unit_cost ↓ as volume ↑ |

#### Family 4: Competitive Structure Patterns (4개)

| Pattern ID | 이름 | 핵심 지표 |
|------------|------|----------|
| PAT-market_concentration | 시장 집중 | HHI > 2500 |
| PAT-fragmented_market | 분산 시장 | HHI < 1000 |
| PAT-winner_take_all | 승자 독식 | top1_share > 50% |
| PAT-niche_specialization | 틈새 전문화 | niche_focus=true |

#### Family 5: Revenue Architecture Patterns (3개)

| Pattern ID | 이름 | 구조 |
|------------|------|------|
| PAT-recurring_revenue | 반복 수익 | recurring_ratio > 0.7 |
| PAT-usage_based_pricing | 사용량 기반 | pricing_model=usage |
| PAT-tiered_pricing | 계층 가격 | tiers >= 3 |

**총 23개 Pattern**

---

## 🔍 Pattern 정의 방식 (상세)

### Pattern Specification 스키마

```python
@dataclass
class PatternSpec:
    """Pattern 정의"""
    pattern_id: str
    name: str
    family: str  # "business_model_patterns"
    description: str
    
    # Trait 제약
    trait_constraints: Dict[str, Any]
    # {
    #   "money_flow": {
    #     "required_traits": {"revenue_model": "subscription"},
    #     "optional_traits": {"recurrence": ["monthly", "yearly"]}
    #   }
    # }
    
    # Graph 구조 제약
    graph_structure: Dict[str, Any]
    # {
    #   "requires": [
    #     {"node_type": "money_flow", "min_count": 1},
    #     {"edge_type": "actor_pays_actor", "min_count": 10}
    #   ]
    # }
    
    # 정량 제약 (선택)
    quantitative_bounds: Optional[Dict[str, Any]]
    # {
    #   "churn_rate": {"min": 0.01, "max": 0.08},  # 1-8%
    #   "gross_margin": {"min": 0.60, "max": 0.85}  # 60-85%
    # }
    
    # Pattern 관계
    composes_with: List[str] = []  # 함께 나타나는 Pattern
    conflicts_with: List[str] = []  # 공존 불가 Pattern
    specializes: Optional[str] = None  # 특수화 대상
    
    # Benchmark (ValueEngine 연동)
    benchmark_metrics: List[str] = []
    # ["MET-Churn_rate", "MET-Gross_margin"]
    
    # Context Archetype 적합성
    suited_for_contexts: List[str] = []
```

### 예시: PAT-subscription_model

```yaml
pattern:
  pattern_id: "PAT-subscription_model"
  name: "구독형 비즈니스 모델"
  family: "business_model_patterns"
  description: |
    정기적인 결제 구조를 가지는 비즈니스 모델.
    월/연 단위 반복 수익이 핵심.
    
  trait_constraints:
    money_flow:
      required_traits:
        revenue_model: "subscription"
        payment_recurs: true
      optional_traits:
        recurrence:
          - "monthly"
          - "yearly"
          - "quarterly"
    
    actor:
      payer_role: "customer"
      min_payers: 10  # 최소 구독자 수
  
  graph_structure:
    requires:
      - node_type: "money_flow"
        min_count: 1
        traits:
          revenue_model: "subscription"
      
      - edge_type: "actor_pays_actor"
        min_count: 10
        pattern: "recurring"
  
  quantitative_bounds:
    churn_rate:
      min: 0.01
      max: 0.15
      typical: [0.03, 0.08]
      source: "pattern_benchmarks"
    
    gross_margin:
      min: 0.40
      max: 0.95
      typical: [0.60, 0.85]
      source: "pattern_benchmarks"
    
    ltv_cac_ratio:
      min: 1.0
      typical: [3.0, 5.0]
  
  composes_with:
    - "PAT-freemium_model"
    - "PAT-tiered_pricing"
    - "PAT-network_effects"
  
  conflicts_with:
    - "PAT-transaction_model"
  
  benchmark_metrics:
    - "MET-Churn_rate"
    - "MET-Gross_margin"
    - "MET-LTV"
    - "MET-CAC"
    - "MET-Payback_period"
  
  suited_for_contexts:
    - "ARCH-digital_service_KR"
    - "ARCH-saas_global"
    - "ARCH-media_streaming"
```

---

## ⚙️ 매칭 알고리즘 (상세)

### Algorithm: Pattern Matching

```python
def match_patterns(
    graph: RealityGraph,
    project_context_id: Optional[str] = None
) -> List[PatternMatch]:
    """
    Pattern 매칭 알고리즘
    
    프로세스:
    1. Trait 기반 필터링 (빠른 제거)
    2. Graph 구조 검증 (정밀 매칭)
    3. Structure Fit 점수 계산
    4. (선택) Execution Fit 점수 계산
    5. Combined Score = structure × execution
    """
    
    matches = []
    patterns = PatternLibrary.get_all()
    
    for pattern in patterns:
        # Stage 1: Trait Filtering (O(n) where n = nodes)
        trait_match = check_trait_constraints(
            graph, 
            pattern.trait_constraints
        )
        
        if not trait_match:
            continue  # 빠른 제거
        
        # Stage 2: Graph Structure Verification
        structure_match = check_graph_structure(
            graph,
            pattern.graph_structure
        )
        
        if not structure_match:
            continue
        
        # Stage 3: Structure Fit Scoring (0.0 ~ 1.0)
        structure_fit = calculate_structure_fit(
            graph,
            pattern,
            trait_match,
            structure_match
        )
        
        # Stage 4: Execution Fit (Project Context 있을 때만)
        execution_fit = None
        if project_context_id:
            project_context = load_project_context(project_context_id)
            execution_fit = calculate_execution_fit(
                pattern,
                project_context
            )
        
        # Pattern Match 생성
        match = PatternMatch(
            pattern_id=pattern.pattern_id,
            description=pattern.description,
            structure_fit_score=structure_fit,
            execution_fit_score=execution_fit,
            evidence={
                "trait_match": trait_match,
                "structure_match": structure_match,
                "node_ids": trait_match["matched_nodes"]
            }
        )
        
        matches.append(match)
    
    # 정렬: structure_fit 우선, 같으면 execution_fit
    matches.sort(
        key=lambda m: (
            m.structure_fit_score,
            m.execution_fit_score or 0.0
        ),
        reverse=True
    )
    
    return matches
```

### Scoring: Structure Fit

```python
def calculate_structure_fit(
    graph: RealityGraph,
    pattern: PatternSpec,
    trait_match: Dict,
    structure_match: Dict
) -> float:
    """
    Structure Fit 점수 계산
    
    점수 = (Trait 점수 × 0.6) + (Graph 구조 점수 × 0.4)
    
    Trait 점수:
    - required_traits 모두 일치: 1.0
    - 일부만 일치: 일치 비율
    
    Graph 구조 점수:
    - requires 모두 만족: 1.0
    - 일부만 만족: 만족 비율
    """
    
    # Trait Score
    required_traits = pattern.trait_constraints
    matched_traits = trait_match["matched_traits"]
    
    trait_score = len(matched_traits) / len(required_traits)
    
    # Structure Score
    required_structures = pattern.graph_structure["requires"]
    satisfied_structures = structure_match["satisfied"]
    
    structure_score = len(satisfied_structures) / len(required_structures)
    
    # Combined
    final_score = (trait_score * 0.6) + (structure_score * 0.4)
    
    return final_score
```

### Scoring: Execution Fit

```python
def calculate_execution_fit(
    pattern: PatternSpec,
    project_context: ProjectContext
) -> float:
    """
    Execution Fit 점수 계산 (Project Context 기반)
    
    점수 = (Capability 일치도 × 0.5) + (제약 충족도 × 0.3) + (자산 충분성 × 0.2)
    
    Capability 일치도:
    - Pattern이 요구하는 capability_traits와
      Project Context의 capability_traits 비교
    
    제약 충족도:
    - Pattern의 실행이 hard_constraints 위반하지 않는지
    
    자산 충분성:
    - Pattern 실행에 필요한 channels, brand_assets 등 확보 여부
    """
    
    # Capability Matching
    required_capabilities = pattern.required_capabilities or []
    available_capabilities = project_context.assets_profile.capability_traits
    
    capability_score = calculate_capability_overlap(
        required_capabilities,
        available_capabilities
    )
    
    # Constraints Check
    hard_constraints = project_context.constraints_profile.hard_constraints
    violates_constraints = check_constraint_violations(
        pattern,
        hard_constraints
    )
    
    constraint_score = 0.0 if violates_constraints else 1.0
    
    # Asset Sufficiency
    required_assets = pattern.required_assets or {}
    available_assets = project_context.assets_profile
    
    asset_score = calculate_asset_sufficiency(
        required_assets,
        available_assets
    )
    
    # Combined
    final_score = (
        capability_score * 0.5 +
        constraint_score * 0.3 +
        asset_score * 0.2
    )
    
    return final_score
```

---

## 🔎 Gap Discovery 전략 (상세)

### Algorithm: Discover Gaps

```python
def discover_gaps(
    graph: RealityGraph,
    project_context_id: Optional[str] = None
) -> List[GapCandidate]:
    """
    Gap Discovery 알고리즘
    
    프로세스:
    1. Context Archetype 결정 (도메인/지역 기반)
    2. Expected Pattern Set 조회
    3. Matched Patterns 조회
    4. Gap = Expected - Matched
    5. Feasibility 평가 (Project Context 기반)
    """
    
    gaps = []
    
    # 1. Context Archetype 결정
    archetype = determine_context_archetype(graph)
    
    if not archetype:
        return []  # Archetype 판별 불가
    
    # 2. Expected Pattern Set
    expected_patterns = ContextArchetypeLibrary.get_expected_patterns(
        archetype.archetype_id
    )
    
    # 3. Matched Patterns
    matched_patterns = match_patterns(graph, project_context_id)
    matched_ids = {m.pattern_id for m in matched_patterns}
    
    # 4. Gap Identification
    for expected in expected_patterns:
        if expected.pattern_id not in matched_ids:
            # Gap 발견!
            pattern = PatternLibrary.get(expected.pattern_id)
            
            # 5. Feasibility 평가
            feasibility = "unknown"
            execution_fit = None
            
            if project_context_id:
                project_context = load_project_context(project_context_id)
                execution_fit = calculate_execution_fit(
                    pattern,
                    project_context
                )
                
                if execution_fit >= 0.7:
                    feasibility = "high"
                elif execution_fit >= 0.4:
                    feasibility = "medium"
                else:
                    feasibility = "low"
            
            gap = GapCandidate(
                pattern_id=pattern.pattern_id,
                description=f"Missing: {pattern.name}",
                expected_level=expected.level,  # "core", "common", "rare"
                feasibility=feasibility,
                execution_fit_score=execution_fit,
                evidence={
                    "archetype": archetype.archetype_id,
                    "expected_level": expected.level
                }
            )
            
            gaps.append(gap)
    
    # 정렬: expected_level (core > common > rare), feasibility (high > medium > low)
    level_order = {"core": 3, "common": 2, "rare": 1}
    feasibility_order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
    
    gaps.sort(
        key=lambda g: (
            level_order.get(g.expected_level, 0),
            feasibility_order.get(g.feasibility, 0)
        ),
        reverse=True
    )
    
    return gaps
```

### Context Archetype 정의 예시

```yaml
context_archetype:
  archetype_id: "ARCH-digital_service_KR"
  name: "한국 디지털 서비스 시장"
  description: "한국의 B2C 디지털 서비스 (SaaS, 플랫폼, 콘텐츠 등)"
  
  criteria:
    region: "KR"
    delivery_channel: "online"
    resource_kind: ["digital_service", "software_license"]
  
  expected_patterns:
    core:  # 거의 항상 존재 (90%+)
      - pattern_id: "PAT-subscription_model"
        weight: 0.9
      
      - pattern_id: "PAT-freemium_model"
        weight: 0.7
    
    common:  # 자주 관찰 (50-90%)
      - pattern_id: "PAT-network_effects"
        weight: 0.6
      
      - pattern_id: "PAT-tiered_pricing"
        weight: 0.5
      
      - pattern_id: "PAT-viral_growth"
        weight: 0.4
    
    rare:  # 드물지만 기회 (10-50%)
      - pattern_id: "PAT-multi_sided_market"
        weight: 0.3
      
      - pattern_id: "PAT-winner_take_all"
        weight: 0.2
```

---

## 🛠️ 구현 계획

### Phase 1: Core Infrastructure (1주)

**목표**: Pattern 정의 및 매칭 기본 구조

**작업**:
1. PatternSpec dataclass 정의
2. PatternLibrary 구현 (YAML 로딩)
3. PatternMatcher 기본 구조
4. Trait-based filtering 구현

**테스트**:
- 5개 Pattern 정의 (각 Family 1개씩)
- Trait 매칭 테스트
- Structure 매칭 테스트

### Phase 2: Scoring & Matching (1주)

**목표**: Structure Fit, Execution Fit 계산

**작업**:
1. Structure Fit 알고리즘 구현
2. Execution Fit 알고리즘 구현
3. Combined Scoring
4. Project Context 통합

**테스트**:
- Structure Fit 점수 검증
- Execution Fit 점수 검증 (3개 Project Context)
- Greenfield vs Brownfield 비교

### Phase 3: Gap Discovery (1주)

**목표**: Context Archetype 기반 Gap 탐지

**작업**:
1. Context Archetype 정의 (3개)
2. Expected Pattern Set 정의
3. GapDiscoverer 구현
4. Feasibility 평가

**테스트**:
- Gap 탐지 정확도 검증
- Feasibility 점수 검증
- Archetype별 Gap 리스트

### Phase 4: Pattern Library (2주)

**목표**: 23개 Pattern 정의 완료

**작업**:
1. 23개 Pattern YAML 작성
2. Benchmark 데이터 연동 (umis_v9_pattern_benchmarks.yaml)
3. Pattern 관계 정의 (composes_with, conflicts_with)
4. Strategic Framework 연동

**테스트**:
- 23개 Pattern 매칭 테스트
- Pattern 조합 테스트
- Benchmark 연동 테스트

### Phase 5: Integration & E2E (1주)

**목표**: ValueEngine, StrategyEngine 통합

**작업**:
1. ValueEngine 연동 (Benchmark 제공)
2. StrategyEngine 연동 (Pattern → Strategy)
3. Workflow 통합
4. E2E 테스트

**테스트**:
- structure_analysis workflow
- opportunity_discovery workflow
- strategy_design workflow

**총 기간**: 6주

---

## 🚀 확장성 고려사항

### 1. Pattern 추가 확장성

**설계**:
- PatternLibrary는 YAML 파일로 Pattern 정의
- 사용자 Custom Pattern 등록 가능
- Pattern Graph에 Runtime 추가

**예시**:
```python
# User-defined Pattern
custom_pattern = PatternSpec(
    pattern_id="PAT-custom_education_model",
    name="맞춤형 교육 모델",
    family="business_model_patterns",
    trait_constraints={
        "actor": {
            "required_traits": {
                "domain_expertise": "education",
                "technology_domain": "AI_ML"
            }
        }
    }
)

# 등록
PatternLibrary.register(custom_pattern)
```

### 2. Learning Engine 연동

**설계**:
- Outcome 기반 Pattern 성능 업데이트
- Pattern Benchmark 자동 조정
- Pattern 관계 학습 (composes_with 발견)

**프로세스**:
```
Outcome → LearningEngine.update_from_outcomes()
         ↓
Pattern Benchmark 업데이트 (quantitative_bounds)
         ↓
Pattern Graph 관계 업데이트
         ↓
Next Matching 시 개선된 Benchmark 사용
```

### 3. Multi-Region 확장

**설계**:
- Context Archetype에 region 포함
- Region별 Expected Pattern 차이 반영
- Region별 Benchmark 차이 (예: KR vs US)

**예시**:
```yaml
context_archetype:
  archetype_id: "ARCH-digital_service_US"
  region: "US"
  
  expected_patterns:
    core:
      - pattern_id: "PAT-freemium_model"  # US에서 더 흔함
        weight: 0.95
```

### 4. Domain-Specific Pattern

**설계**:
- Domain Trait 기반 Pattern 필터링
- 산업별 Pattern Library (Healthcare, Finance, Education)
- Domain별 Context Archetype

**예시**:
```yaml
pattern:
  pattern_id: "PAT-healthcare_subscription"
  family: "business_model_patterns"
  domain: "healthcare"
  
  trait_constraints:
    actor:
      required_traits:
        domain_expertise: "healthcare"
        regulatory_compliance: ["HIPAA"]
```

---

## 📐 Pattern Graph Schema (P-Graph)

### Node Types

```yaml
pattern:
  fields:
    pattern_id: string (PAT-*)
    name: string
    family: string
    description: string
    traits: dict (Trait 제약)
    constraints: list (Graph 구조 제약)
    benchmark_metrics: list (MET-*)
    
pattern_family:
  fields:
    family_id: string
    name: string
    description: string
    
context_archetype:
  fields:
    archetype_id: string (ARCH-*)
    name: string
    criteria: dict (region, domain, etc.)
    expected_patterns: dict (core/common/rare)
```

### Edge Types

```yaml
pattern_composes_with:
  from: pattern
  to: pattern
  properties:
    confidence: float  # 0.0~1.0

pattern_conflicts_with:
  from: pattern
  to: pattern
  properties:
    reason: string

pattern_specializes:
  from: pattern (specialized)
  to: pattern (general)

pattern_belongs_to_family:
  from: pattern
  to: pattern_family

pattern_suited_for_context:
  from: pattern
  to: context_archetype
  properties:
    expected_level: enum (core/common/rare)
    weight: float
```

---

## 🎨 사용 예시

### Example 1: Greenfield 분석 (Structure Fit만)

```python
from cmis_core.pattern_engine import PatternEngine
from cmis_core.world_engine import WorldEngine

# 1. Reality Graph 생성
world_engine = WorldEngine()
graph = world_engine.snapshot(
    as_of="2024",
    scope={
        "domain_id": "Adult_Language_Education_KR",
        "region": "KR"
    }
)

# 2. Pattern 매칭
pattern_engine = PatternEngine()
matches = pattern_engine.match_patterns(graph)

# 결과:
# [
#   PatternMatch(
#     pattern_id="PAT-subscription_model",
#     structure_fit_score=0.95,
#     execution_fit_score=None  # Project Context 없음
#   ),
#   PatternMatch(
#     pattern_id="PAT-freemium_model",
#     structure_fit_score=0.80,
#     execution_fit_score=None
#   )
# ]
```

### Example 2: Brownfield 분석 (Execution Fit 포함)

```python
# 1. Project Context 로드
project_context = load_project_context("PRJ-edtech-startup-001")

# 2. Pattern 매칭 (Execution Fit 포함)
matches = pattern_engine.match_patterns(
    graph,
    project_context_id="PRJ-edtech-startup-001"
)

# 결과:
# [
#   PatternMatch(
#     pattern_id="PAT-subscription_model",
#     structure_fit_score=0.95,
#     execution_fit_score=0.85,  # Capability 높음
#     combined_score=0.81
#   ),
#   PatternMatch(
#     pattern_id="PAT-platform_business_model",
#     structure_fit_score=0.90,
#     execution_fit_score=0.40,  # Capability 부족
#     combined_score=0.36
#   )
# ]
```

### Example 3: Gap Discovery

```python
# Gap 탐지
gaps = pattern_engine.discover_gaps(
    graph,
    project_context_id="PRJ-edtech-startup-001"
)

# 결과:
# [
#   GapCandidate(
#     pattern_id="PAT-network_effects",
#     description="Missing: 네트워크 효과",
#     expected_level="common",
#     feasibility="high",  # Execution Fit 0.75
#     execution_fit_score=0.75
#   ),
#   GapCandidate(
#     pattern_id="PAT-viral_growth",
#     description="Missing: 바이럴 성장",
#     expected_level="common",
#     feasibility="medium",  # Execution Fit 0.55
#     execution_fit_score=0.55
#   )
# ]
```

---

## 🔗 연동 설계

### ValueEngine 연동

**목적**: Pattern Benchmark를 Metric 계산에 활용

**프로세스**:
```
PatternMatch(pattern_id="PAT-subscription_model")
    ↓
ValueEngine.evaluate_metrics([MET-Churn_rate])
    ↓
Metric Resolver: Prior Estimation Stage
    ↓
PatternLibrary.get_benchmark("PAT-subscription_model", "MET-Churn_rate")
    ↓
Prior: Churn ∈ [0.03, 0.08] (Pattern Benchmark)
```

**구현**:
```python
# ValueEngine에서 Pattern Benchmark 조회
def _estimate_from_pattern(
    metric_id: str,
    matched_patterns: List[PatternMatch]
) -> Optional[Distribution]:
    """Pattern Benchmark 기반 Prior 추정"""
    
    for match in matched_patterns:
        pattern = PatternLibrary.get(match.pattern_id)
        
        if metric_id in pattern.benchmark_metrics:
            bounds = pattern.quantitative_bounds.get(metric_id)
            
            if bounds:
                return Distribution(
                    min=bounds["min"],
                    max=bounds["max"],
                    typical_range=bounds.get("typical"),
                    source=f"pattern_benchmark:{match.pattern_id}",
                    confidence=match.structure_fit_score
                )
    
    return None
```

### StrategyEngine 연동

**목적**: Pattern 조합으로 Strategy 생성

**프로세스**:
```
Goal(goal_id="GOL-market_entry")
    ↓
StrategyEngine.search_strategies(goal_id)
    ↓
PatternEngine.match_patterns(graph) + discover_gaps(graph)
    ↓
Strategy Template: Matched Patterns + Gap Patterns
    ↓
Strategy Candidates 생성
```

**구현**:
```python
# StrategyEngine에서 Pattern 활용
def _generate_strategy_from_patterns(
    matched_patterns: List[PatternMatch],
    gap_patterns: List[GapCandidate],
    goal: Goal
) -> List[Strategy]:
    """Pattern 조합 기반 Strategy 생성"""
    
    strategies = []
    
    # 현재 Pattern 유지 + Gap Pattern 추가 전략
    for gap in gap_patterns:
        if gap.feasibility in ["high", "medium"]:
            strategy = Strategy(
                strategy_id=f"STR-add-{gap.pattern_id}",
                name=f"Add {gap.pattern_id}",
                base_patterns=[m.pattern_id for m in matched_patterns],
                target_patterns=[gap.pattern_id],
                expected_impact={
                    "metrics": gap.expected_metrics,
                    "confidence": gap.execution_fit_score
                }
            )
            strategies.append(strategy)
    
    return strategies
```

---

## 📊 성능 고려사항

### 시간 복잡도

- **match_patterns**: O(P × N) where P=패턴 수, N=노드 수
  - Trait Filtering: O(N)
  - Graph Structure: O(N + E) where E=엣지 수
  - 최적화: Trait Index 사용 → O(log N)

- **discover_gaps**: O(A × P) where A=Archetype 수, P=패턴 수
  - Context 판별: O(N)
  - Gap 계산: O(P)

### 공간 복잡도

- **PatternLibrary**: O(P) where P=패턴 수
- **P-Graph Store**: O(P + R) where R=관계 수

### 최적화 전략

1. **Trait Index**: Trait별 노드 인덱스 구축
2. **Pattern Cache**: 자주 매칭되는 Pattern 캐싱
3. **Lazy Evaluation**: Execution Fit는 필요 시만 계산
4. **Parallel Matching**: Pattern별 병렬 매칭

---

## 🎓 학습 가능성 (Learning)

### Learning Engine 연동

**목적**: Outcome 기반 Pattern 성능 개선

**학습 항목**:
1. **Pattern Benchmark 조정**
   - 실제 Outcome과 Pattern Benchmark 비교
   - Quantitative Bounds 업데이트

2. **Execution Fit 개선**
   - Project Context별 Pattern 실행 성과 기록
   - Capability-Pattern 매핑 학습

3. **Pattern 관계 발견**
   - 함께 성공한 Pattern 조합 학습
   - Composes_with 관계 자동 추가

**프로세스**:
```
Outcome(strategy_id="STR-001", actual_metrics={...})
    ↓
LearningEngine.update_from_outcomes(outcome_id)
    ↓
Pattern Performance 평가:
  - Expected Metrics (Pattern Benchmark)
  - Actual Metrics (Outcome)
  - Delta 계산
    ↓
Pattern Benchmark 업데이트:
  - quantitative_bounds 조정
  - confidence 가중치 조정
    ↓
Next Matching에서 개선된 Benchmark 사용
```

---

## 🔐 품질 보장 (Quality Gates)

### Pattern 정의 품질

**체크리스트**:
- [ ] pattern_id가 PAT-* 형식
- [ ] trait_constraints가 비어있지 않음
- [ ] graph_structure가 최소 1개 requires
- [ ] benchmark_metrics가 존재하는 MET-* ID
- [ ] description이 명확함

### Matching 품질

**체크리스트**:
- [ ] structure_fit_score ∈ [0.0, 1.0]
- [ ] execution_fit_score ∈ [0.0, 1.0] or None
- [ ] evidence가 검증 가능한 노드 ID 포함
- [ ] 중복 매칭 없음 (같은 Pattern 2번 매칭 ❌)

### Gap Discovery 품질

**체크리스트**:
- [ ] Gap Pattern이 실제로 매칭되지 않음 (검증)
- [ ] Feasibility가 Execution Fit 기반으로 정확히 계산
- [ ] Expected Level이 Context Archetype에 정의됨

---

## 📖 용어 정리

| 용어 | 정의 | 예시 |
|------|------|------|
| **Pattern** | R-Graph에서 반복적으로 관찰되는 구조/메커니즘 | PAT-subscription_model |
| **Pattern Family** | 유사한 Pattern의 그룹 | business_model_patterns |
| **Context Archetype** | 특정 시장/산업의 전형적인 특징 | ARCH-digital_service_KR |
| **Structure Fit** | R-Graph와 Pattern의 구조 적합도 | 0.95 (95% 일치) |
| **Execution Fit** | Project Context 기반 실행 가능성 | 0.75 (높은 실행 가능성) |
| **Gap** | Expected Pattern이지만 R-Graph에 없음 | PAT-network_effects |
| **Feasibility** | Gap Pattern의 실행 가능성 수준 | high/medium/low |

---

## 🚦 다음 단계

### Immediate (설계 승인 후)

1. **설계 리뷰**
   - CMIS 철학 부합성 검증
   - 아키텍처 타당성 검토
   - 구현 가능성 평가

2. **Spike (1주)**
   - 5개 Pattern 정의 (POC)
   - PatternMatcher 기본 구조
   - Structure Fit 알고리즘 검증

### Short-term (1개월)

1. **Phase 1-3 구현** (3주)
   - Core Infrastructure
   - Scoring & Matching
   - Gap Discovery

2. **통합 테스트** (1주)
   - ValueEngine 연동
   - Workflow 통합
   - E2E 검증

### Long-term (2-3개월)

1. **Pattern Library 완성** (2주)
   - 23개 Pattern 정의
   - Benchmark 데이터
   - Pattern 관계

2. **Learning Engine 연동** (2주)
   - Outcome 기반 학습
   - Benchmark 자동 조정

3. **Production Ready** (2주)
   - 성능 최적화
   - 문서화 완성
   - 배포 준비

---

**작성**: 2025-12-10  
**작성자**: CMIS Architecture Team  
**상태**: Design Proposal  
**다음 단계**: 설계 리뷰 및 Spike 착수

