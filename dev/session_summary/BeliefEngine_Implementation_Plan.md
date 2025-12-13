# BeliefEngine 구현 계획

**작성일**: 2025-12-12
**기반**: BeliefEngine_Feedback_Review.md
**총 작업**: 23개
**예상 시간**: 9시간

---

## 📊 작업 현황

```
Phase 1 (Core):        5개 작업 ⏱️ 4시간
Phase 2 (Integration): 7개 작업 ⏱️ 3시간
Phase 3 (Advanced):    5개 작업 ⏱️ 2시간
문서/검증:              6개 작업 ⏱️ 추가 작업

총 23개 작업
```

---

## Phase 1: Core Components (4시간)

### 1.1 타입 정의
**파일**: `cmis_core/types.py`
**예상 시간**: 30분

```python
@dataclass
class BeliefRecord:
    belief_id: str
    metric_id: str
    context: Dict[str, Any]
    distribution: Dict[str, Any]
    confidence: float
    source: str
    observations: List[Dict[str, Any]]
    n_observations: int
    created_at: str
    updated_at: str
    lineage: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict) -> "BeliefRecord": ...
```

**체크리스트**:
- [ ] BeliefRecord 클래스 정의
- [ ] 모든 필드 타입 힌트
- [ ] to_dict/from_dict 메서드
- [ ] Docstring 작성

---

### 1.2 PriorManager 구현
**파일**: `cmis_core/prior_manager.py` (150줄)
**예상 시간**: 1시간

**주요 메서드**:
```python
class PriorManager:
    def get_prior(metric_id: str, context: Dict) -> Optional[BeliefRecord]
    def save_belief(metric_id, context, posterior, observations, prior) -> BeliefRecord
    def _hash_context(context: Dict) -> str
    def _calculate_confidence(posterior, observations) -> float
    def load_pattern_benchmark(pattern_id: str) -> Optional[Dict]
```

**체크리스트**:
- [ ] PriorManager 클래스 기본 구조
- [ ] get_prior() 메모리 dict 조회
- [ ] save_belief() BeliefRecord 생성
- [ ] _hash_context() MD5 해시
- [ ] _calculate_confidence() 로직
- [ ] load_pattern_benchmark() 스텁

---

### 1.3 BeliefUpdater 구현
**파일**: `cmis_core/belief_updater.py` (200줄)
**예상 시간**: 1.5시간

**주요 메서드**:
```python
class BeliefUpdater:
    def bayesian_update(prior: Dict, observations: List) -> Dict
    def _normal_normal_update(prior: Dict, observations: List) -> Dict
    def direct_replace(observations: List) -> Dict
```

**체크리스트**:
- [ ] BeliefUpdater 클래스
- [ ] bayesian_update() 분기 로직
- [ ] _normal_normal_update() 베이지안 공식
- [ ] direct_replace() numpy 사용
- [ ] lineage에서 EVD-*/OUT-* 분리
- [ ] Docstring + 수식 주석

---

### 1.4 UncertaintyPropagator 기본
**파일**: `cmis_core/uncertainty_propagator.py` (200줄)
**예상 시간**: 1시간

**주요 메서드**:
```python
class UncertaintyPropagator:
    def monte_carlo(formula, input_distributions, n_samples) -> Dict
    def _sample_distribution(dist: Dict, n: int) -> np.ndarray
    def sensitivity_analysis(formula, input_distributions, output_samples) -> Dict
    def _evaluate_formula(formula: str, var_values: Dict) -> float  # eval() 임시
```

**체크리스트**:
- [ ] UncertaintyPropagator 클래스
- [ ] monte_carlo() 기본 구현
- [ ] _sample_distribution() normal/lognormal/uniform
- [ ] sensitivity_analysis() 간단 버전
- [ ] _evaluate_formula() eval() 사용 (Phase 3에서 개선)

---

### 1.5 단위 테스트 10개
**파일**: `dev/tests/unit/test_belief_engine_phase1.py` (200줄)
**예상 시간**: 1시간

**테스트 구성**:
```
PriorManager (3개):
  - test_prior_manager_get_set
  - test_hash_context
  - test_calculate_confidence

BeliefUpdater (4개):
  - test_bayesian_update_normal_normal
  - test_direct_replace
  - test_lineage_separation
  - test_observation_weighting

UncertaintyPropagator (3개):
  - test_monte_carlo_basic
  - test_sample_distribution
  - test_sensitivity_analysis
```

**체크리스트**:
- [ ] conftest.py에 fixtures
- [ ] 10개 테스트 작성
- [ ] 모든 테스트 통과
- [ ] Coverage 80%+

---

## Phase 2: Integration (3시간)

### 2.1 BeliefEngine 클래스
**파일**: `cmis_core/belief_engine.py` (300줄)
**예상 시간**: 1시간

**Public API**:
```python
class BeliefEngine:
    def query_prior_api(metric_id, context, policy_ref) -> Dict
    def update_belief_api(metric_id, context, observations, update_mode) -> Dict
    def propagate_uncertainty_api(formula, input_distributions, n_samples) -> Dict
    
    # Internal
    def _generate_prior_from_pattern(metric_id, context) -> BeliefRecord
    def _generate_uninformative_prior(metric_id) -> BeliefRecord
```

**체크리스트**:
- [ ] BeliefEngine 클래스 초기화
- [ ] query_prior_api() 구현
- [ ] update_belief_api() 구현
- [ ] propagate_uncertainty_api() 구현
- [ ] _generate_prior_from_pattern() 스텁
- [ ] _generate_uninformative_prior() 구현

---

### 2.2 value_store 연동
**파일**: `cmis_core/prior_manager.py` (수정)
**예상 시간**: 45분

**추가 메서드**:
```python
class PriorManager:
    def __init__(self, value_store_path: Path):
        self.value_store_path = value_store_path
        self._cache: Dict[str, BeliefRecord] = {}
        self._cache_ttl = 3600
    
    def _load_from_value_store(metric_id, context) -> Optional[BeliefRecord]
    def _calculate_spread(distribution: Dict) -> float
```

**체크리스트**:
- [ ] value_store_path 설정
- [ ] _load_from_value_store() 파일 읽기
- [ ] save_belief() ValueRecord 형식 저장
- [ ] 캐싱 로직 (_cache, TTL)
- [ ] _calculate_spread() 구현

---

### 2.3 Policy/Quality 통합
**파일**: `cmis_core/belief_engine.py` (수정)
**예상 시간**: 30분

**추가 메서드**:
```python
def _apply_policy_adjustment(prior, policy_mode) -> BeliefRecord:
    if policy_mode == "reporting_strict":
        prior.confidence *= 0.5
        prior.distribution = widen(dist, 2.0)
    elif policy_mode == "exploration_friendly":
        prior.distribution = widen(dist, 1.2)

def _widen_distribution(dist: Dict, factor: float) -> Dict
def _narrow_distribution(dist: Dict, target_spread: float) -> Dict
def _apply_quality_constraints(prior, metric_spec) -> BeliefRecord
```

**체크리스트**:
- [ ] query_prior_api()에 policy 조정 추가
- [ ] _widen_distribution() 구현
- [ ] _narrow_distribution() 구현
- [ ] _apply_quality_constraints() 구현

---

### 2.4 Context 정밀도 강화
**파일**: `cmis_core/belief_engine.py` (수정)
**예상 시간**: 30min

**추가 메서드**:
```python
def _calculate_context_similarity(context1, context2) -> float:
    key_weights = {
        "domain_id": 0.4,
        "region": 0.3,
        "segment": 0.2,
        "scale_tier": 0.1
    }
    # ...

def _is_similar_region(region1, region2) -> bool
```

**체크리스트**:
- [ ] _generate_prior_from_pattern()에 similarity 추가
- [ ] _calculate_context_similarity() 구현
- [ ] context_similarity × pattern_score 가중치
- [ ] _is_similar_region() 구현

---

### 2.5 LearningEngine 연동
**파일**: `cmis_core/learning_engine.py` (수정)
**예상 시간**: 30분

**추가 메서드**:
```python
def _should_update_belief(metric_id, delta) -> bool:
    metric_spec = self._get_metric_spec(metric_id)
    target_convergence = metric_spec.get("resolution_protocol", {}).get("target_convergence")
    threshold = parse_convergence(target_convergence) or 0.2
    return abs(delta["error_pct"]) > threshold

def _update_beliefs_from_outcome(outcome, comparison) -> List[str]:
    # BeliefEngine.update_belief_api() 호출
    
def _create_drift_alert(metric_id, belief_update_result) -> str:
    if abs(delta["mean_shift"]) > 0.5:
        # memory_store에 저장
```

**체크리스트**:
- [ ] _should_update_belief() 구현
- [ ] _update_beliefs_from_outcome() BeliefEngine 호출
- [ ] _create_drift_alert() 구현
- [ ] memory_store 연동

---

### 2.6 ValueEngine 연동
**파일**: `cmis_core/value_engine.py` (수정)
**예상 시간**: 15분

**수정 메서드**:
```python
def _resolve_metric_prior_estimation(metric_id, context, policy_ref) -> Optional[Dict]:
    from cmis_core.belief_engine import BeliefEngine
    
    belief_engine = BeliefEngine()
    prior_result = belief_engine.query_prior_api(metric_id, context, policy_ref)
    
    # Prior → ValueRecord 변환
    value_record = {
        "value_id": f"VAL-{prior_result['prior_id']}",
        "metric_id": metric_id,
        "context": context,
        "point_estimate": None,
        "distribution": prior_result["distribution"],
        "quality": {
            "literal_ratio": 0.0,  # Prior는 literal 없음
            "spread_ratio": calculate_spread(prior_result["distribution"]),
            "confidence": prior_result["confidence"]
        },
        "origin": "prior",
        "lineage": prior_result["lineage"]
    }
    return value_record
```

**체크리스트**:
- [ ] metric_resolver.py에 prior_estimation 단계 구현
- [ ] BeliefEngine.query_prior_api() 호출
- [ ] Prior → ValueRecord 변환
- [ ] origin="prior" 설정

---

### 2.7 통합 테스트 12개
**파일**: `dev/tests/unit/test_belief_engine_phase2.py` (250줄)
**예상 시간**: 45분

**테스트 구성**:
```
query_prior_api (4개):
  - test_query_prior_pattern_based
  - test_query_prior_uninformative
  - test_query_prior_policy_strict
  - test_query_prior_policy_friendly

update_belief_api (4개):
  - test_update_belief_bayesian
  - test_update_belief_replace
  - test_update_belief_delta
  - test_update_belief_confidence_gain

ValueEngine 연동 (2개):
  - test_value_engine_prior_estimation
  - test_prior_to_value_record

LearningEngine 연동 (2개):
  - test_learning_should_update_belief
  - test_learning_drift_alert
```

**체크리스트**:
- [ ] 12개 테스트 작성
- [ ] 모든 테스트 통과
- [ ] Mock/Fixture 적절히 사용

---

## Phase 3: Advanced Features (2시간)

### 3.1 AST evaluator
**파일**: `cmis_core/uncertainty_propagator.py` (수정)
**예상 시간**: 30min

**수정**:
```python
import asteval

class UncertaintyPropagator:
    def __init__(self):
        self.evaluator = asteval.Interpreter()
    
    def _evaluate_formula(self, formula: str, var_values: Dict) -> float:
        # eval() → asteval로 변경
        for var, val in var_values.items():
            self.evaluator.symtable[var] = val
        
        result = self.evaluator(expr)
        if self.evaluator.error:
            raise ValueError(...)
        return float(result)
```

**체크리스트**:
- [ ] asteval 설치 (requirements.txt)
- [ ] _evaluate_formula() asteval 사용
- [ ] Error handling 추가
- [ ] 안전성 테스트

---

### 3.2 Samples 분리 저장
**파일**: `cmis_core/uncertainty_propagator.py` (수정)
**예상 시간**: 30min

**수정**:
```python
def monte_carlo(self, formula, input_distributions, n_samples) -> Dict:
    # ... (샘플 생성 및 평가)
    
    # Samples는 artifact_store에 저장
    samples_ref = self._save_samples_to_store(output_samples, formula, input_distributions)
    
    # 요약 통계만 반환
    return {
        "percentiles": {...},
        "statistics": {...},
        "samples_ref": samples_ref  # ✅
    }

def _save_samples_to_store(self, samples, formula, input_distributions) -> str:
    artifact_id = f"ART-samples-{uuid.uuid4().hex[:8]}"
    # artifact_store에 JSON 저장
    return artifact_id
```

**체크리스트**:
- [ ] artifact_store_path 설정
- [ ] _save_samples_to_store() 구현
- [ ] monte_carlo() 반환값 수정 (samples 제거, samples_ref 추가)
- [ ] 저장/로딩 테스트

---

### 3.3 추가 분포 지원
**파일**: `cmis_core/belief_updater.py` (수정)
**예상 시간**: 30min

**추가 메서드**:
```python
def _lognormal_update(self, prior: Dict, observations: List) -> Dict
def _beta_binomial_update(self, prior: Dict, observations: List) -> Dict
def _empirical_update(self, prior: Dict, observations: List) -> Dict
```

**체크리스트**:
- [ ] _lognormal_update() 구현
- [ ] _beta_binomial_update() 구현
- [ ] _empirical_update() 구현
- [ ] bayesian_update()에 분기 추가

---

### 3.4 Sobol Monte Carlo
**파일**: `cmis_core/uncertainty_propagator.py` (수정)
**예상 시간**: 15min

**추가**:
```python
from scipy.stats import qmc

def monte_carlo(self, ..., use_sobol=False):
    if use_sobol:
        sampler = qmc.Sobol(d=len(input_distributions))
        samples_unit = sampler.random(n_samples)
        # 각 분포에 맞게 변환
    else:
        # 기존 random sampling
```

**체크리스트**:
- [ ] scipy 설치 (requirements.txt)
- [ ] use_sobol 옵션 추가
- [ ] Sobol Sequence 구현
- [ ] 수렴 속도 테스트

---

### 3.5 고급 테스트 10개
**파일**: `dev/tests/unit/test_belief_engine_phase3.py` (200줄)
**예상 시간**: 30min

**테스트 구성**:
```
Lognormal/Beta 업데이트 (4개):
  - test_lognormal_update
  - test_beta_binomial_update
  - test_empirical_update
  - test_mixed_distributions

Sobol Monte Carlo (2개):
  - test_sobol_vs_random
  - test_sobol_convergence

Samples 저장 (4개):
  - test_save_samples_to_store
  - test_load_samples_from_store
  - test_monte_carlo_without_samples
  - test_artifact_cleanup
```

**체크리스트**:
- [ ] 10개 테스트 작성
- [ ] 모든 테스트 통과

---

## 문서 및 검증 (추가 작업)

### 4.1 cmis.yaml 업데이트
**파일**: `cmis.yaml`
**예상 시간**: 30min

**업데이트 내용**:
```yaml
cmis:
  meta:
    version: "3.5.0"
    engines_completed: "9/9"
    completion: "100%"

  cognition_plane:
    engines:
      belief_engine:
        # ... (전체 정의)

  substrate_plane:
    stores:
      value_store:
        schema:
          origin: "enum[direct,derived,prior,learned]"

  ids_and_lineage:
    lineage_schema:
      from_prior_id: { type: "string", required: false }
      from_outcome_ids: { type: "list", required: false }
```

**체크리스트**:
- [ ] belief_engine 섹션 추가 (api 3개, core_components, prior_strategies, update_modes)
- [ ] value_store.schema.origin 추가
- [ ] lineage_schema 확장
- [ ] meta.version 3.5.0
- [ ] YAML 검증 (yamllint)

---

### 4.2 설계 문서 업데이트
**파일**: `dev/docs/architecture/BeliefEngine_Design_Enhanced.md`
**예상 시간**: 30min

**업데이트 섹션**:
1. Section 3.1: BeliefRecord 스키마 추가
2. Section 4.1: value_store 활용 명시
3. Section 4.2: Policy 통합 설명
4. Section 5.1: Context 정밀도 설명
5. Section 6: Phase별 구현 계획 수정 (Priority 반영)

**체크리스트**:
- [ ] BeliefRecord 스키마 섹션 추가
- [ ] value_store 연동 설명
- [ ] Policy/Quality 통합 섹션
- [ ] Context similarity 알고리즘
- [ ] 구현 계획 업데이트

---

### 4.3 통합 테스트 5개
**파일**: `dev/tests/integration/test_belief_engine_integration.py`
**예상 시간**: 1시간

**테스트 구성**:
```
1. test_e2e_value_engine_prior
   - ValueEngine이 BeliefEngine 호출하여 Prior 가져오기
   
2. test_e2e_learning_belief_update
   - Outcome → LearningEngine → BeliefEngine 업데이트
   
3. test_e2e_uncertainty_propagation
   - 여러 Metric 분포 → 공식 → 결과 분포
   
4. test_e2e_prior_to_improved
   - 초기 Prior → 관측 → 업데이트 → 다음 조회 시 개선
   
5. test_e2e_pattern_benchmark_prior
   - Pattern 매칭 → Benchmark → Prior 생성
```

**체크리스트**:
- [ ] 5개 E2E 테스트 작성
- [ ] 실제 데이터 플로우 검증
- [ ] 모든 엔진 연동 확인

---

### 4.4 사용자 가이드
**파일**: `dev/docs/user_guide/BeliefEngine_Guide.md`
**예상 시간**: 45min

**구성**:
```markdown
# BeliefEngine 사용 가이드

## 1. Prior 조회
- 기본 사용법
- Policy별 차이
- Context 설정

## 2. Belief 업데이트
- 관측 데이터 형식
- Bayesian vs Direct Replace
- 결과 해석

## 3. 불확실성 전파
- Monte Carlo 시뮬레이션
- 민감도 분석
- Samples 접근

## 4. 주의사항
- Prior는 최후 수단
- 업데이트 빈도
- 성능 고려
```

**체크리스트**:
- [ ] 각 API 사용 예시
- [ ] Policy별 권장 사용법
- [ ] 주의사항 명시
- [ ] FAQ 섹션

---

### 4.5 Future Enhancements 문서화
**파일**: `dev/docs/architecture/BeliefEngine_Future.md`
**예상 시간**: 30min

**내용**:
```markdown
# BeliefEngine Future Enhancements

## v1.1: Human-in-the-loop
- propose_belief_update()
- approve_belief_update()
- Rollback 메커니즘

## v1.2: 다변량 Belief
- Joint Prior Distribution
- Copula 기반 종속성
- TAM/SAM/SOM 동시 업데이트

## v1.2: Active Learning
- suggest_evidence_priorities()
- EvidenceEngine 연동
- Acquisition Function

## Drift Alert (memory_store)
- 큰 Belief 변화 감지
- drift_alert 자동 생성
```

**체크리스트**:
- [ ] v1.1 Human-in-the-loop 설계
- [ ] v1.2 다변량 Belief 설계
- [ ] Active Learning 설계
- [ ] Drift Alert 설계

---

### 4.6 검증 체크리스트
**예상 시간**: 1시간

**체크리스트**:

#### 코드 품질
- [ ] 모든 테스트 32개 통과 (10+12+10)
- [ ] Type hints 100%
- [ ] Docstring 100%
- [ ] Linter 오류 0개
- [ ] Coverage 85%+

#### 기능 검증
- [ ] BeliefRecord 스키마 일관성
- [ ] value_store 저장/로딩 동작
- [ ] Policy별 분포 조정 확인
- [ ] Context similarity 계산 정확성
- [ ] ValueEngine 연동 동작
- [ ] LearningEngine 연동 동작
- [ ] Drift Alert 생성 확인

#### 성능 검증
- [ ] Monte Carlo 10,000 samples < 5초
- [ ] value_store 캐싱 동작
- [ ] AST evaluator 안전성

#### 문서 검증
- [ ] cmis.yaml 유효성
- [ ] 설계 문서 최신화
- [ ] 사용자 가이드 완성

---

## 📋 작업 순서 (권장)

### Day 1: Phase 1 (4시간)
1. ✅ BeliefRecord 타입 정의 (30분)
2. ✅ PriorManager 구현 (1시간)
3. ✅ BeliefUpdater 구현 (1.5시간)
4. ✅ UncertaintyPropagator 기본 (1시간)
5. ✅ 단위 테스트 10개 (1시간)

### Day 2: Phase 2 (3시간)
6. ✅ BeliefEngine 클래스 (1시간)
7. ✅ value_store 연동 (45분)
8. ✅ Policy/Quality 통합 (30분)
9. ✅ Context 정밀도 (30분)
10. ✅ LearningEngine 연동 (30분)
11. ✅ ValueEngine 연동 (15분)
12. ✅ 통합 테스트 12개 (45분)

### Day 3: Phase 3 + 문서 (3시간)
13. ✅ AST evaluator (30분)
14. ✅ Samples 분리 저장 (30분)
15. ✅ 추가 분포 지원 (30분)
16. ✅ Sobol Monte Carlo (15분)
17. ✅ 고급 테스트 10개 (30분)
18. ✅ cmis.yaml 업데이트 (30분)
19. ✅ 설계 문서 업데이트 (30분)
20. ✅ 통합 테스트 5개 (1시간)
21. ✅ 사용자 가이드 (45분)
22. ✅ Future 문서화 (30분)
23. ✅ 검증 체크리스트 (1시간)

---

## 🎯 완료 기준

### Minimum Viable (MVP)
- [x] Phase 1 완료 (5개 작업)
- [ ] Phase 2 완료 (7개 작업)
- [ ] 통합 테스트 통과
- [ ] cmis.yaml 업데이트

### Production Ready
- [ ] Phase 3 완료 (5개 작업)
- [ ] 모든 테스트 통과 (32개)
- [ ] 문서 완성 (3개)
- [ ] 검증 체크리스트 통과

### Excellence
- [ ] Coverage 90%+
- [ ] 사용자 가이드 완성
- [ ] Future 설계 문서
- [ ] Performance 벤치마크

---

**작성**: 2025-12-12
**상태**: 준비 완료
**다음**: Phase 1 구현 시작

**CMIS v3.4.0 → v3.5.0 (BeliefEngine 완성)**

