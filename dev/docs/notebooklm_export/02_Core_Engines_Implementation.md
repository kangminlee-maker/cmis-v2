# CMIS 핵심 엔진 구현 상세

**생성일**: 2025-12-21 11:28:56
**목적**: 9개 핵심 엔진의 구현 세부사항

---

## 1. belief_engine.py

**경로**: `cmis_core/belief_engine.py`

### 모듈 설명

```
Belief Engine

Prior/Belief 관리 및 불확실성 정량화 엔진.

CMIS의 9번째이자 마지막 엔진으로,
Evidence가 부족할 때 Prior Distribution을 제공하고,
Outcome 기반으로 Belief를 업데이트하는 역할.

핵심 원칙:
- Evidence-first, Prior-last
- Conservative by Default
- Context-aware
- Monotonic Improvability
```

### 주요 클래스

#### `BeliefEngine`

Belief Engine - Prior/Belief 관리 엔진

Usage:
    engine = BeliefEngine()

    # Prior 조회
    prior = engine.query_prior_api(
        metric_id="MET-SAM",
        context={"domain_id": "...", "region": "KR"},
        policy_ref="decision_balanced"
    )

    # Belief 업데이트
    result = engine.update_belief_api(
        metric_id="MET-SAM",
        context={"domain_id": "...", "region": "KR"},
        observations=[{"value": 50000, "weight": 1.0}],
        update_mode="bayesian"
    )

    # 불확실성 전파
    mc_result = engine.propagate_uncertainty_api(
        formula="Revenue = N_customers * ARPU",
        input_distributions={...},
        n_samples=10000
    )

**Public 메서드**:

```python
def query_prior_api(self, metric_id: str, context: Dict[(str, Any)], policy_ref: Optional[str]) -> Dict[(str, Any)]
```
Public API - Prior Distribution 조회

```python
def update_belief_api(self, metric_id: str, context: Dict[(str, Any)], observations: List[Dict], update_mode: str) -> Dict[(str, Any)]
```
Public API - Belief 업데이트

```python
def propagate_uncertainty_api(self, formula: str, input_distributions: Dict[(str, Dict)], n_samples: int) -> Dict[(str, Any)]
```
Public API - 불확실성 전파 (Monte Carlo)

---

## 2. prior_manager.py

**경로**: `cmis_core/prior_manager.py`

### 모듈 설명

```
Prior Manager

Prior/Belief Distribution 저장/조회/관리를 담당하는 모듈.

BeliefEngine의 핵심 컴포넌트로, Context별로 Prior를 캐싱하고
Pattern Benchmark에서 Prior를 생성하는 역할.

Phase 1: 메모리 dict 기반
Phase 2: value_store 영속성 추가
```

### 주요 클래스

#### `PriorManager`

Prior Distribution 관리자

Context별로 Prior/Belief를 저장하고 조회.
Pattern Benchmark 기반 Prior 생성 지원.

Phase 2: value_store 연동으로 영속성 확보.

Usage:
    manager = PriorManager(value_store_path=Path("data/value_store"))

    # Prior 조회 (value_store → 캐시)
    prior = manager.get_prior("MET-SAM", {"domain_id": "...", "region": "KR"})

    # Belief 저장 (value_store + 캐시)
    belief = manager.save_belief(
        metric_id="MET-SAM",
        context={"domain_id": "...", "region": "KR"},
        posterior={"type": "normal", "params": {...}},
        observations=[{"value": 50000, "weight": 1.0}],
        prior=prior
    )

**Public 메서드**:

```python
def get_prior(self, metric_id: str, context: Dict[(str, Any)]) -> Optional[BeliefRecord]
```
Context별 Prior 조회

```python
def save_prior(self, prior: BeliefRecord) -> BeliefRecord
```
Prior(BeliefRecord)를 value_store에 저장하고 캐시에 반영합니다.

```python
def save_belief(self, metric_id: str, context: Dict[(str, Any)], posterior: Dict, observations: List[Dict], prior: Optional[BeliefRecord]) -> BeliefRecord
```
Belief 생성/업데이트

```python
def load_pattern_benchmark(self, pattern_id: str) -> Optional[Dict]
```
Pattern Benchmark 로드

---

## 3. belief_updater.py

**경로**: `cmis_core/belief_updater.py`

### 모듈 설명

```
Belief Updater

Bayesian Update 로직을 담당하는 모듈.

Prior Distribution + Observations → Posterior Distribution

Phase 1: Normal-Normal Bayesian Update
Phase 3: Lognormal, Beta 등 추가 분포 지원
```

### 주요 클래스

#### `BeliefUpdater`

Bayesian Belief Update

Prior와 Observations를 받아 Posterior 계산.

Usage:
    updater = BeliefUpdater()
    
    prior = {"type": "normal", "params": {"mu": 50000, "sigma": 10000}}
    observations = [
        {"value": 48000, "weight": 1.0},
        {"value": 52000, "weight": 0.8}
    ]
    
    posterior = updater.bayesian_update(prior, observations)
    # → {"type": "normal", "params": {"mu": 49500, "sigma": 6000}}

**Public 메서드**:

```python
def bayesian_update(self, prior: Dict, observations: List[Dict]) -> Dict
```
베이지안 업데이트

```python
def direct_replace(self, observations: List[Dict]) -> Dict
```
직접 대체 (Bayesian 아님)

---

## 4. uncertainty_propagator.py

**경로**: `cmis_core/uncertainty_propagator.py`

### 모듈 설명

```
Uncertainty Propagator

불확실성 전파 및 Monte Carlo 시뮬레이션.

공식 기반 Metric 계산 시 입력 분포의 불확실성을 출력 분포로 전파.

Phase 1: 기본 Monte Carlo (eval() 사용)
Phase 3: AST evaluator, Sobol Sequence, Samples 분리 저장
```

### 주요 클래스

#### `UncertaintyPropagator`

불확실성 전파 및 시뮬레이션

Monte Carlo 시뮬레이션을 통해 입력 변수의 분포를
공식을 거쳐 출력 분포로 변환.

Phase 3: AST evaluator, Samples 분리, Sobol Sequence

Usage:
    propagator = UncertaintyPropagator(artifact_store_path=Path("data/artifacts"))

    result = propagator.monte_carlo(
        formula="Revenue = N_customers * ARPU",
        input_distributions={
            "N_customers": {"type": "normal", "params": {"mu": 100000, "sigma": 10000}},
            "ARPU": {"type": "lognormal", "params": {"mu": 3.5, "sigma": 0.3}}
        },
        n_samples=10000,
        use_sobol=True  # Phase 3
    )

    # → {"percentiles": {...}, "statistics": {...}, "samples_ref": "ART-..."}

**Public 메서드**:

```python
def monte_carlo(self, formula: str, input_distributions: Dict[(str, Dict)], n_samples: int, use_sobol: bool) -> Dict
```
Monte Carlo 시뮬레이션

```python
def sensitivity_analysis(self, formula: str, input_distributions: Dict[(str, Dict)], output_samples: List[float]) -> Dict[(str, float)]
```
민감도 분석 (분산 기여도)

---

## 5. world_engine.py

**경로**: `cmis_core/world_engine.py`

### 모듈 설명

```
CMIS World Engine

Evidence → R-Graph 변환 및 snapshot 생성

Phase A: RealityGraphStore + ProjectOverlay + 필터링
2025-12-11: World Engine v2.0
```

### 주요 클래스

#### `WorldEngine`

World Engine v2 - Phase A/B/C

기능:
- RealityGraphStore (Global Reality)
- ProjectOverlayStore (Per-Project)
- as_of/segment 필터링
- ingest_focal_actor_context
- 서브그래프 추출
- ingest_evidence
- snapshot() API (통합)

Phase A: Brownfield + 필터링
Phase B: ingest_evidence (동적 확장)
Phase C: 성능 최적화 (백엔드, 캐싱, 인덱싱)

**Public 메서드**:

```python
def load_reality_seed(self, path: Path) -> RealityGraphSnapshot
```
Reality seed YAML → R-Graph 변환

```python
def snapshot(self, domain_id: str, region: str, segment: Optional[str], as_of: Optional[str], focal_actor_context_id: Optional[str], slice_spec: Optional[Dict[(str, Any)]]) -> RealityGraphSnapshot
```
R-Graph snapshot 생성 (v2: 필터링 + Brownfield + 캐싱)

```python
def ingest_focal_actor_context(self, focal_context: FocalActorContext) -> tuple[(str, list[str])]
```
FocalActorContext(record) → ProjectOverlay 투영

```python
def ingest_evidence(self, domain_id: str, evidence_list: List[EvidenceRecord]) -> List[str]
```
Evidence → RealityGraphStore 반영

### 주요 함수

```python
def snapshot(domain_id: str, region: Optional[str], segment: Optional[str], as_of: Optional[str]) -> RealityGraphSnapshot
```
World Engine snapshot 편의 함수

---

## 6. pattern_engine_v2.py

**경로**: `cmis_core/pattern_engine_v2.py`

### 모듈 설명

```
Pattern Engine v2 - Phase 1 Core Infrastructure

Trait 기반 패턴 매칭 및 구조 적합도 계산

2025-12-10: v1.1 설계 반영
- PatternSpec 13개 필드
- PatternMatch 8개 필드
- Structure Fit (Trait + Graph)
- 5개 Pattern 지원
```

### 주요 클래스

#### `PatternEngineV2`

Pattern Engine v2 (Phase 1)

기능:
- Pattern 매칭 (Trait + Graph 기반)
- Structure Fit 계산
- 5개 Pattern 지원 (각 Family 1개)

Phase 1: Core Infrastructure
Phase 2: Execution Fit, Gap Discovery
Phase 3: P-Graph 통합, Learning

**Public 메서드**:

```python
def match_patterns(self, graph: InMemoryGraph, focal_actor_context_id: Optional[str]) -> List[PatternMatch]
```
Pattern 매칭

```python
def discover_gaps(self, graph: InMemoryGraph, focal_actor_context_id: Optional[str], precomputed_matches: Optional[List[PatternMatch]]) -> List[GapCandidate]
```
Gap 탐지

```python
def get_pattern(self, pattern_id: str) -> Optional[PatternSpec]
```
Pattern 조회

```python
def get_all_patterns(self) -> List[PatternSpec]
```
모든 Pattern 조회

---

## 7. pattern_matcher.py

**경로**: `cmis_core/pattern_matcher.py`

### 모듈 설명

```
Pattern Matcher - Trait 기반 패턴 매칭

R-Graph에서 Pattern을 찾는 핵심 매칭 로직

2025-12-10: Phase 1 Core Infrastructure
```

### 주요 클래스

#### `PatternMatcher`

Pattern 매칭 엔진

역할:
1. Trait 기반 필터링 (빠른 제거)
2. Graph 구조 검증
3. Anchor Node 식별

Phase 1: Trait/Graph 매칭
Phase 2: Scoring (PatternScorer로 분리)

**Public 메서드**:

```python
def match(self, graph: InMemoryGraph, pattern_candidates: List[PatternSpec]) -> List[Dict[(str, Any)]]
```
Pattern 후보에 대해 매칭 수행

### 주요 함수

```python
def check_trait_constraints(graph: InMemoryGraph, trait_constraints: Dict[(str, Any)]) -> Dict[(str, Any)]
```
Trait 제약 체크 (v1.1 - 2단계)

Args:
    graph: Reality Graph
    trait_constraints: Pattern의 trait_constraints
        {
            "money_flow": {
                "required_traits": {"revenue_model": "subscription"},
                "optional_traits": {"recurrence": ["monthly", "yearly"]}
            }
        }

Returns:
    {
        "is_match": bool,
        "trait_match": {
            "money_flow": {
                "required": {"matched": 2, "total": 2},
                "optional": {"matched": 1, "total": 3}
            }
        },
        "matched_node_ids": [...],
        "anchor_nodes": {"money_flow": [...]}
    }

```python
def _trait_value_match(node_value: Any, pattern_value: Any) -> bool
```
Trait 값 매칭 (단일 값 또는 리스트)

Args:
    node_value: 노드의 trait 값
    pattern_value: Pattern이 요구하는 값 (단일 또는 리스트)

Returns:
    매칭 여부

```python
def check_graph_structure(graph: InMemoryGraph, graph_structure: Dict[(str, Any)]) -> Dict[(str, Any)]
```
Graph 구조 제약 체크

Args:
    graph: Reality Graph
    graph_structure: Pattern의 graph_structure
        {
            "requires": [
                {"node_type": "money_flow", "min_count": 1},
                {"edge_type": "actor_pays_actor", "min_count": 10}
            ]
        }

Returns:
    {
        "is_match": bool,
        "satisfied": [...],
        "unsatisfied": [...]
    }

---

## 8. pattern_learner.py

**경로**: `cmis_core/pattern_learner.py`

### 모듈 설명

```
Pattern Learner - Pattern Benchmark 학습

실제 Outcome으로 Pattern.quantitative_bounds 업데이트

2025-12-11: LearningEngine Phase 1
```

### 주요 클래스

#### `PatternLearner`

Pattern 학습기

역할:
- Pattern Benchmark 업데이트 (Context별)
- Bayesian 업데이트
- sample_size 관리

**Public 메서드**:

```python
def update_pattern_benchmark(self, pattern_id: str, metric_id: str, actual_value: float, context: Dict[(str, Any)], sample_size: int, alpha: float) -> Dict[(str, Any)]
```
Pattern Benchmark 업데이트 (Context별)

---

## 9. value_engine.py

**경로**: `cmis_core/value_engine.py`

### 모듈 설명

```
CMIS Value Engine

Metric 계산 및 Fusion 엔진
```

### 주요 클래스

#### `ValueEngine`

Value Engine - R-Graph 기반 Metric 계산 및 Fusion

지원 Metric:
- MET-N_customers: Actor 집계
- MET-Revenue: MoneyFlow 합산
- MET-Avg_price_per_unit: Revenue / N_customers
- (기타 Metric: 확장 가능)

Fusion 기능:
- 4-Method Fusion (Top-down/Bottom-up/Fermi/Proxy)
- 가중 평균 알고리즘
- 범위 교집합
- Convergence 검증 (±30%)

**Public 메서드**:

```python
def evaluate_metrics(self, graph: InMemoryGraph, metric_requests: List[MetricRequest], policy_ref: str, focal_actor_context_id: Optional[str], use_evidence_engine: bool) -> Tuple[(List[ValueRecord], Dict[str, Any], List[MetricEval])]
```
Metric 평가 (v3: PolicyEngine 통합)

```python
def fuse_4method(self, candidates: List[ValueRecord], convergence_threshold: float) -> ValueRecord
```
4-Method 융합 (v7 Fusion 알고리즘)

---

## 10. strategy_engine.py

**경로**: `cmis_core/strategy_engine.py`

### 모듈 설명

```
Strategy Engine - 전략 설계 엔진

Goal/Pattern/Reality/Value 기반 전략 탐색 및 평가

Phase 1: Core Infrastructure + Public API
2025-12-11: StrategyEngine Phase 1
```

### 주요 클래스

#### `StrategyEngine`

Strategy Engine v1

역할:
- Pattern 조합 → Strategy 생성
- Execution Fit/ROI/Risk 평가
- Portfolio 최적화

Phase 1: Core + Public API
Phase 2: D-Graph 통합, Portfolio 고도화

**Public 메서드**:

```python
def search_strategies_api(self, goal_id: str, constraints: Dict[(str, Any)], focal_actor_context_id: Optional[str]) -> str
```
Public API (cmis.yaml 대응)

```python
def search_strategies_core(self, goal: Goal, reality_snapshot: RealityGraphSnapshot, pattern_matches: List[PatternMatch], gaps: List[GapCandidate], focal_actor_context: Optional[FocalActorContext], greenfield_constraints: Optional[Dict[(str, Any)]]) -> List[Strategy]
```
Core 전략 탐색 (내부 함수)

```python
def evaluate_portfolio_api(self, strategy_ids: List[str], policy_ref: str, focal_actor_context_id: Optional[str]) -> str
```
Public API: Portfolio 평가

```python
def evaluate_portfolio_core(self, strategies, focal_actor_context, policy_params)
```
Core: Portfolio 평가

---

## 11. strategy_generator.py

**경로**: `cmis_core/strategy_generator.py`

### 모듈 설명

```
Strategy Generator - Pattern 조합 기반 전략 생성

Pattern 매칭/Gap 결과 → Strategy 후보 생성

2025-12-11: StrategyEngine Phase 1
```

### 주요 클래스

#### `StrategyGenerator`

전략 생성기

역할:
1. Single Pattern → Strategy
2. Pattern Composition → Strategy
3. Gap-based → Strategy
4. Goal 필터링

**Public 메서드**:

```python
def generate(self, pattern_matches: List[PatternMatch], gaps: List[GapCandidate], goal: Goal) -> List[Strategy]
```
전략 생성

```python
def create_strategy_from_pattern(self, pattern_match: PatternMatch, goal: Goal) -> Optional[Strategy]
```
Single Pattern → Strategy

```python
def create_strategy_from_gap(self, gap: GapCandidate, goal: Goal) -> Optional[Strategy]
```
Gap → Strategy

---

## 12. strategy_evaluator.py

**경로**: `cmis_core/strategy_evaluator.py`

### 모듈 설명

```
Strategy Evaluator - 전략 평가

Execution Fit, ROI, Risk 계산

2025-12-11: StrategyEngine Phase 1
```

### 주요 클래스

#### `StrategyEvaluator`

전략 평가기

역할:
1. Execution Fit 계산 (PatternScorer 재사용)
2. ROI/Outcomes 예측 (ValueEngine 연동)
3. Risk 평가

**Public 메서드**:

```python
def calculate_execution_fit(self, strategy: Strategy, focal_actor_context: FocalActorContext) -> float
```
Strategy Execution Fit 계산

```python
def predict_outcomes(self, strategy: Strategy, baseline_state: Dict[(str, Any)], horizon_years: int) -> Dict[(str, Any)]
```
ROI/Outcomes 예측

```python
def assess_risks(self, strategy: Strategy, focal_actor_context: Optional[FocalActorContext], matched_patterns: List[PatternMatch]) -> List[Dict[(str, Any)]]
```
Risk 평가

---

## 13. learning_engine.py

**경로**: `cmis_core/learning_engine.py`

### 모듈 설명

```
Learning Engine - 학습 및 피드백 루프

Outcome → 시스템 개선

Phase 1: Core Infrastructure
2025-12-11: LearningEngine Phase 1
```

### 주요 클래스

#### `LearningEngine`

Learning Engine v1

역할:
- Outcome vs 예측 비교
- Pattern Benchmark 업데이트
- Metric Belief 보정
- FocalActorContext baseline 업데이트

Phase 1: Core + API
Phase 2: ValueEngine 연동, memory_store

**Public 메서드**:

```python
def update_from_outcomes_api(self, outcome_ids: List[str]) -> Dict[(str, Any)]
```
Public API (cmis.yaml 대응)

```python
def register_outcome(self, outcome: Outcome) -> None
```
Outcome 등록 (테스트용)

```python
def register_strategy(self, strategy: Strategy) -> None
```
Strategy 등록 (테스트용)

```python
def register_focal_actor_context(self, focal_actor_context: FocalActorContext) -> None
```
FocalActorContext 등록 (테스트용)

```python
def update_focal_actor_context_from_outcome_api(self, outcome_id: str, focal_actor_context_id: str) -> str
```
Public API: FocalActorContext 업데이트 (cmis.yaml 대응)

---

## 14. learning_policy.py

**경로**: `cmis_core/learning_policy.py`

### 모듈 설명

```
Learning Policy - 학습 정책 및 안전장치

언제, 얼마나 강하게 학습할지 결정

2025-12-11: LearningEngine Phase 3
```

### 주요 클래스

#### `LearningPolicy`

학습 정책

역할:
- 최소 sample_size 관리
- learning_rate 결정
- 업데이트 허용 여부 판단

**Public 메서드**:

```python
def should_update(self, update_type: str, sample_size: int) -> bool
```
업데이트 실행 여부

```python
def get_learning_rate(self, update_type: str, sample_size: int) -> float
```
학습률 계산

```python
def get_alpha(self, update_type: str, sample_size: int) -> float
```
Alpha 계산 (기존 가중치)

---

## 15. evidence_engine.py

**경로**: `cmis_core/evidence_engine.py`

### 모듈 설명

```
CMIS Evidence Engine

Evidence 수집 및 관리 엔진 (v2 개정판)

설계 원칙:
- Evidence-first, Prior-last
- Early Return (상위 tier 성공 시 즉시 반환)
- Graceful Degradation (부분 실패 허용)
- Source-agnostic Interface
- Comprehensive Lineage

아키텍처:
- EvidenceEngine: Facade (public API)
- EvidencePlanner: Plan 생성
- EvidenceExecutor: Plan 실행
- SourceRegistry: Source 관리
- EvidenceStore: 캐싱/저장
```

### 주요 클래스

#### `EvidenceEngineError`

Base exception for Evidence Engine

#### `SourceNotAvailableError`

Source 접근 불가 (API down, 네트워크 등)

#### `DataNotFoundError`

요청한 데이터 없음

---

## 16. policy_engine.py

**경로**: `cmis_core/policy_engine.py`

### 모듈 설명

```
CMIS Policy Engine v2

목표:
- policies.yaml(v2)을 '정책 레지스트리/팩'으로 사용
- role/usage → mode(policy_id) 라우팅을 YAML로 선언
- mode = profiles(evidence/value/prior/convergence/orchestration) 조합
- gates 리스트로 "어떤 검증을 강제할지"를 선언
- PolicyEngine은:
  1) YAML 로딩
  2) mode → CompiledPolicy 컴파일(참조 해소)
  3) 엔진 힌트 제공(예: evidence 정책)
  4) 결과 평가(게이트 실행) + 구조화된 위반 리포트 생성

레거시(v1) 호환 없음.
```

### 주요 클래스

#### `PolicyError`

#### `PolicyConfigError`

#### `EvidenceBundleSummary`

Evidence bundle summary for policy evaluation.

- num_sources: number of distinct sources used
- source_tiers_used: e.g. ["official", "web"]
- max_age_days: maximum age among sources (days)

**Public 메서드**:

```python
def from_dict(d: Dict[(str, Any)]) -> EvidenceBundleSummary
```

---

## 17. workflow.py

**경로**: `cmis_core/workflow.py`

### 모듈 설명

```
CMIS Workflow Orchestrator

canonical_workflows 기반 워크플로우 실행

v2.0: Generic workflow run + Role/Policy 통합
2025-12-11: Workflow CLI Phase 1
```

### 주요 클래스

#### `WorkflowOrchestrator`

Workflow Orchestrator v2

역할:
- canonical_workflows (YAML) 로딩 및 실행
- role_id → policy_mode 해석
- Generic workflow runner
- Lineage 추적

v1: structure_analysis만
v2: Generic workflow run + canonical_workflows 통합

**Public 메서드**:

```python
def run_structure_analysis(self, input_data: StructureAnalysisInput) -> StructureAnalysisResult
```
structure_analysis 워크플로우 실행

```python
def run_opportunity_discovery(self, domain_id: str, region: str, segment: Optional[str], focal_actor_context_id: Optional[str], top_n: int, min_feasibility: Optional[str]) -> Dict[(str, Any)]
```
opportunity_discovery 워크플로우 실행

```python
def run_workflow(self, workflow_id: str, inputs: Dict[(str, Any)], role_id: Optional[str], policy_mode: Optional[str]) -> Dict[(str, Any)]
```
Generic workflow 실행 (canonical_workflows 기반)

### 주요 함수

```python
def run_structure_analysis(domain_id: str, region: str, segment: Optional[str], as_of: Optional[str], focal_actor_context_id: Optional[str]) -> StructureAnalysisResult
```
structure_analysis 실행 편의 함수

Args:
    domain_id: 도메인 ID
    region: 지역
    segment: 세그먼트 (선택)
    as_of: 기준일 (선택)
    focal_actor_context_id: FocalActorContext ID (선택)

Returns:
    StructureAnalysisResult

---
