# BeliefEngine 사용 가이드

**버전**: v1.0
**작성일**: 2025-12-12
**대상**: CMIS 사용자 (Analyst, Modeler, Developer)

---

## 소개

BeliefEngine은 **Evidence가 부족할 때** Prior Distribution을 제공하고,
Outcome 기반으로 Belief를 업데이트하는 CMIS의 9번째 엔진입니다.

**핵심 원칙**:
- Evidence-first, Prior-last (최후 수단)
- Conservative by Default (넓게 시작, 점진적 좁힘)
- Context-aware (Domain/Region/Segment별 다른 Prior)
- Monotonic Improvability (관측 누적으로 개선)

---

## 1. Prior 조회

### 1.1 기본 사용법

```python
from cmis_core.belief_engine import BeliefEngine

engine = BeliefEngine()

# Prior 조회
prior = engine.query_prior_api(
    metric_id="MET-SAM",
    context={
        "domain_id": "Adult_Language_Education_KR",
        "region": "KR",
        "segment": "online_only"
    },
    policy_ref="decision_balanced"
)

print(f"Prior ID: {prior['prior_id']}")
print(f"분포: {prior['distribution']}")
print(f"신뢰도: {prior['confidence']}")
print(f"출처: {prior['source']}")
```

**출력 예시**:
```
Prior ID: PRIOR-abc12345
분포: {'type': 'lognormal', 'params': {'mu': 10.8, 'sigma': 0.5}}
신뢰도: 0.5
출처: pattern_benchmark
```

---

### 1.2 Policy별 차이

#### reporting_strict (공식/Evidence 중심)

```python
prior_strict = engine.query_prior_api(
    metric_id="MET-SAM",
    context={"domain_id": "...", "region": "KR"},
    policy_ref="reporting_strict"
)

# 특징:
# - confidence × 0.5 (더 낮은 신뢰)
# - spread × 2.0 (더 넓은 분포)
# - Prior 사용 최소화
```

#### decision_balanced (균형)

```python
prior_balanced = engine.query_prior_api(
    metric_id="MET-SAM",
    context={"domain_id": "...", "region": "KR"},
    policy_ref="decision_balanced"  # 기본값
)

# 특징:
# - 기본값 유지
# - Evidence 우선, 필요 시 Prior 허용
```

#### exploration_friendly (기회 탐색)

```python
prior_friendly = engine.query_prior_api(
    metric_id="MET-SAM",
    context={"domain_id": "...", "region": "KR"},
    policy_ref="exploration_friendly"
)

# 특징:
# - spread × 1.2 (약간 넓음)
# - Prior 적극 활용
```

---

### 1.3 Prior 종류

#### Pattern Benchmark (confidence 0.5)

유사한 Pattern의 Benchmark 값 기반.

```python
# Context 유사도:
# - domain_id: 40%
# - region: 30%
# - segment: 20%
# - scale_tier: 10%

# 예: 한국 성인 교육 시장
prior = engine.query_prior_api(
    metric_id="MET-SAM",
    context={
        "domain_id": "Adult_Language_Education_KR",
        "region": "KR"
    }
)

# source="pattern_benchmark"
# confidence=0.5 (중간)
```

#### Uninformative (confidence 0.1)

Evidence 전혀 없을 때.

```python
prior = engine.query_prior_api(
    metric_id="MET-NewMarket",
    context={"domain_id": "unknown", "region": "ZZ"}
)

# source="uninformative"
# confidence=0.1 (매우 낮음)
# distribution: 매우 넓은 범위
# - market_size: 1M ~ 1T (loguniform)
# - unit_economics: 100 ~ 1M
# - ratio: 0 ~ 1
```

---

## 2. Belief 업데이트

### 2.1 Bayesian Update (기본)

```python
from cmis_core.belief_engine import BeliefEngine

engine = BeliefEngine()

# Outcome 관측
observations = [
    {"value": 50000, "weight": 1.0, "source": "OUT-001"},
    {"value": 48000, "weight": 0.8, "source": "EVD-123"}
]

# Belief 업데이트
result = engine.update_belief_api(
    metric_id="MET-SAM",
    context={"domain_id": "...", "region": "KR"},
    observations=observations,
    update_mode="bayesian"  # 기본값
)

print(f"Prior 평균: {result['prior']['distribution']['params']['mu']}")
print(f"Posterior 평균: {result['posterior']['distribution']['params']['mu']}")
print(f"평균 이동: {result['delta']['mean_shift']}")
print(f"신뢰도 증가: {result['posterior']['confidence'] - result['prior']['confidence']}")
```

**출력 예시**:
```
Prior 평균: 100000
Posterior 평균: 95000
평균 이동: -5000
신뢰도 증가: +0.15
```

---

### 2.2 Direct Replace

```python
# Prior 무시하고 관측값만 사용 (강한 Evidence)
observations = [
    {"value": 50000, "weight": 1.0, "source": "EVD-official-001"},
    {"value": 51000, "weight": 1.0, "source": "EVD-official-002"},
    {"value": 49000, "weight": 1.0, "source": "EVD-official-003"}
]

result = engine.update_belief_api(
    metric_id="MET-Revenue",
    context={"domain_id": "...", "region": "KR"},
    observations=observations,
    update_mode="replace"  # Prior 무시
)

# Posterior는 관측값 기반만
# mean ≈ 50000
```

**언제 사용**:
- 공식 데이터 (DART, KOSIS)
- Prior보다 훨씬 신뢰도 높은 Evidence
- Prior가 부정확하다고 판단될 때

---

### 2.3 누적 업데이트 (Monotonic Improvability)

```python
# 1차 업데이트
obs1 = [{"value": 50000, "weight": 1.0, "source": "EVD-001"}]
result1 = engine.update_belief_api(
    metric_id="MET-TAM",
    context={"domain_id": "test"},
    observations=obs1,
    update_mode="bayesian"
)

print(f"1차 신뢰도: {result1['posterior']['confidence']}")
# → 0.6 (n_observations=1)

# 2차 업데이트 (추가 관측)
obs2 = [{"value": 52000, "weight": 1.0, "source": "OUT-002"}]
result2 = engine.update_belief_api(
    metric_id="MET-TAM",
    context={"domain_id": "test"},
    observations=obs2,
    update_mode="bayesian"
)

print(f"2차 신뢰도: {result2['posterior']['confidence']}")
# → 0.7 (n_observations=2, 증가!)

print(f"분산 감소: {result2['delta']['sigma_reduction']}")
# → 음수 (불확실성 감소)
```

**효과**:
- 관측 누적 → 신뢰도 증가
- 분산 감소 → 불확실성 개선
- Lineage 추적 (from_prior_id)

---

## 3. 불확실성 전파 (Monte Carlo)

### 3.1 기본 사용법

```python
# Revenue = N_customers × ARPU
result = engine.propagate_uncertainty_api(
    formula="Revenue = N_customers * ARPU",
    input_distributions={
        "N_customers": {
            "type": "normal",
            "params": {"mu": 100000, "sigma": 10000}
        },
        "ARPU": {
            "type": "lognormal",
            "params": {"mu": 3.91, "sigma": 0.3}  # median ≈ 50
        }
    },
    n_samples=10000
)

print(f"평균 Revenue: {result['output_distribution']['statistics']['mean']:,.0f}원")
print(f"P10: {result['output_distribution']['percentiles']['p10']:,.0f}원")
print(f"P50: {result['output_distribution']['percentiles']['p50']:,.0f}원")
print(f"P90: {result['output_distribution']['percentiles']['p90']:,.0f}원")

print(f"\n민감도:")
for var, contrib in result['sensitivity'].items():
    print(f"  {var}: {contrib:.1%}")
```

**출력 예시**:
```
평균 Revenue: 5,000,000원
P10: 3,500,000원
P50: 4,900,000원
P90: 6,800,000원

민감도:
  N_customers: 60.0%
  ARPU: 40.0%
```

---

### 3.2 위험 평가

```python
# Downside risk (P10)
p10 = result['output_distribution']['percentiles']['p10']
p50 = result['output_distribution']['percentiles']['p50']

downside_risk = (p50 - p10) / p50
print(f"Downside Risk: {downside_risk:.1%}")
# → 28% (P50에서 P10까지 28% 하락 가능)

# Upside potential (P90)
p90 = result['output_distribution']['percentiles']['p90']

upside_potential = (p90 - p50) / p50
print(f"Upside Potential: {upside_potential:.1%}")
# → 39% (P50에서 P90까지 39% 상승 가능)
```

---

## 4. Policy별 사용법

### 4.1 reporting_strict (보고서용)

**언제**: 공식 보고서, IR 자료, 이사회 보고

**특징**:
- Prior 사용 최소화
- 보수적 추정

```python
# Reporting용 Metric 계산
from cmis_core.value_engine import ValueEngine

value_engine = ValueEngine()

# Policy: reporting_strict
value_record = value_engine._resolve_metric_prior_estimation(
    metric_id="MET-SAM",
    context={"domain_id": "...", "region": "KR"},
    policy_ref="reporting_strict"
)

# Prior 사용 안 함 (Evidence 없으면 None 반환)
if value_record is None:
    print("Evidence 부족 - Prior도 신뢰할 수 없음")
```

---

### 4.2 decision_balanced (의사결정용)

**언제**: 전략 수립, 투자 결정, ROI 분석

**특징**:
- Evidence 우선, 필요 시 Prior
- 균형잡힌 접근

```python
# 전략 평가용
prior = engine.query_prior_api(
    metric_id="MET-SOM",
    context={"domain_id": "...", "region": "KR"},
    policy_ref="decision_balanced"
)

# Prior 사용 (confidence에 따라 가중치 조정)
if prior['confidence'] < 0.3:
    print("Warning: Prior 신뢰도 낮음")
```

---

### 4.3 exploration_friendly (기회 탐색용)

**언제**: Opportunity Discovery, 시장 탐색, 가설 검증

**특징**:
- Prior 적극 활용
- 넓은 범위 허용

```python
# 기회 탐색
prior = engine.query_prior_api(
    metric_id="MET-TAM",
    context={"domain_id": "new_market", "region": "KR"},
    policy_ref="exploration_friendly"
)

# 넓은 범위 OK (rough sizing)
p10 = prior['distribution']['params']['mu'] * 0.5
p90 = prior['distribution']['params']['mu'] * 2.0

print(f"TAM 범위: {p10:,.0f}원 ~ {p90:,.0f}원")
```

---

## 5. 주의사항

### 5.1 Prior는 최후 수단

**올바른 순서**:

```
1. Direct Evidence (공식 데이터, 재무제표)
   └─ 실패 →

2. Derived (공식 계산, R-Graph 집계)
   └─ 실패 →

3. Prior Estimation (BeliefEngine) ← 여기서만 사용
   └─ Pattern Benchmark → Uninformative

4. Fusion (여러 방법 결합)
```

**잘못된 사용**:
```python
# ❌ Evidence 찾기 전에 Prior 사용
prior = engine.query_prior_api(...)  # 너무 이르게!

# ✅ ValueEngine이 자동으로 순서 관리
value_engine.evaluate_metrics(...)  # ValueEngine 사용 권장
```

---

### 5.2 업데이트 빈도

**너무 자주 업데이트 금지**:

```python
# ❌ 매 관측마다 업데이트
for obs in observations:
    engine.update_belief_api(metric_id, context, [obs])

# ✅ 배치 업데이트
engine.update_belief_api(metric_id, context, observations)
```

**LearningEngine 사용 권장**:

```python
# LearningEngine이 자동으로 판단
# - 오차 > target_convergence → 업데이트
# - 오차 작으면 skip

learning_engine.update_from_outcomes_api(outcome_ids)
```

---

### 5.3 Context 일관성

**동일 Context 사용**:

```python
context = {
    "domain_id": "Adult_Language_Education_KR",
    "region": "KR",
    "segment": "online_only"
}

# ✅ 동일 Context로 조회/업데이트
prior = engine.query_prior_api("MET-SAM", context)
result = engine.update_belief_api("MET-SAM", context, observations)

# ❌ Context 다르면 다른 Belief
prior2 = engine.query_prior_api("MET-SAM", {"domain_id": "...", "region": "US"})
# → 다른 Prior (Context 해시 다름)
```

---

### 5.4 분포 타입 선택

**Metric Category별 권장 분포**:

| Category | 분포 | 이유 |
|----------|------|------|
| market_size (TAM/SAM/SOM) | lognormal | 항상 양수, 오른쪽 꼬리 |
| Revenue, COGS, OPEX | lognormal | 항상 양수, 분산 큼 |
| unit_economics (ARPU, CAC) | lognormal | 항상 양수 |
| ratio (margin, churn_rate) | beta | 0~1 범위 |
| count (N_customers) | normal | 큰 수 → CLT |

**사용자 지정 불필요** (자동 선택):
```python
# BeliefEngine이 metric_id에서 category 추론
# MET-SAM → market_size → lognormal
# MET-Churn_rate → ratio → uniform (Phase 3: beta)
```

---

## 6. 고급 사용법

### 6.1 Samples 접근

**Phase 3: artifact_store에서 로딩**

```python
result = engine.propagate_uncertainty_api(
    formula="Revenue = N_customers * ARPU",
    input_distributions={...},
    n_samples=10000
)

samples_ref = result['samples_ref']
# → "ART-samples-abc12345"

# artifact_store에서 로딩
import json
from pathlib import Path

artifact_path = Path("data/artifacts") / f"{samples_ref}.json"
with open(artifact_path, "r") as f:
    artifact = json.load(f)

samples = artifact["samples"]  # 10,000개 샘플
```

---

### 6.2 Sobol Sequence (빠른 수렴)

```python
# Quasi-random sampling (수렴 빠름)
result = propagator.monte_carlo(
    formula="Revenue = N_customers * ARPU",
    input_distributions={...},
    n_samples=1024,  # 2의 거듭제곱 권장
    use_sobol=True  # ✅
)

# Random보다 적은 샘플로도 안정적
```

---

### 6.3 누적 학습 확인

```python
# Belief 히스토리 추적
belief1 = engine.query_prior_api("MET-SAM", context)
print(f"n_observations: {belief1['lineage'].get('n_observations', 0)}")
print(f"from_prior_id: {belief1['lineage'].get('from_prior_id')}")

# 여러 번 업데이트 후
# n_observations 증가 → confidence 증가
# from_prior_id 체인으로 히스토리 추적
```

---

## 7. 문제 해결

### Q1: Prior 신뢰도가 너무 낮아요 (0.1)

**원인**: Uninformative Prior 사용 중

**해결**:
1. Pattern 추가 → Pattern Benchmark 활성화
2. 직접 관측 → update_belief_api() 호출
3. 다른 Context의 Prior 참고

---

### Q2: Belief가 업데이트되지 않아요

**원인**: 오차가 target_convergence 이하

**확인**:
```python
learning_engine._should_update_belief(metric_id, delta)
# → False면 skip됨
```

**해결**:
- metrics_spec의 target_convergence 확인
- 또는 직접 update_belief_api() 호출

---

### Q3: Monte Carlo가 너무 느려요

**원인**: n_samples 너무 큼

**해결**:
```python
# 1. 샘플 수 줄이기
result = engine.propagate_uncertainty_api(..., n_samples=1000)  # 10000 → 1000

# 2. Sobol 사용 (빠른 수렴)
result = propagator.monte_carlo(..., use_sobol=True)
```

---

### Q4: 분포 타입이 맞지 않아요

**확인**:
```python
prior = engine.query_prior_api(...)
print(prior['distribution']['type'])
# → "lognormal" | "normal" | "uniform" | "beta"
```

**변경** (필요 시):
```python
# 수동으로 Belief 생성 후 저장
from cmis_core.types import BeliefRecord

manual_belief = BeliefRecord(
    belief_id="PRIOR-manual",
    metric_id="MET-test",
    context={...},
    distribution={"type": "beta", "params": {"alpha": 2, "beta": 2}},  # 원하는 분포
    confidence=0.7,
    source="domain_expert",
    ...
)

engine.prior_manager.save_belief(...)
```

---

## 8. Best Practices

### 8.1 Prior 사용 원칙

**DO**:
- ValueEngine이 자동으로 호출하도록 (Stage 3)
- Policy에 맞는 사용 (reporting_strict → 최소)
- Context 명확히 설정

**DON'T**:
- Evidence 찾기 전에 Prior 사용
- 너무 자주 업데이트
- Prior에만 의존

---

### 8.2 업데이트 전략

**배치 업데이트**:
```python
# ✅ 여러 관측 모아서 한 번에
observations = [obs1, obs2, obs3, ...]
engine.update_belief_api(metric_id, context, observations)
```

**점진적 업데이트**:
```python
# ✅ LearningEngine에 맡기기
learning_engine.update_from_outcomes_api(outcome_ids)
# → metrics_spec 기준으로 자동 판단
```

---

### 8.3 결과 해석

**confidence 기준**:
- 0.0~0.2: 매우 낮음 (Uninformative)
- 0.3~0.6: 낮음 (Pattern 1~2개)
- 0.6~0.8: 중간 (관측 1~3개)
- 0.8+: 높음 (관측 5개 이상)

**spread_ratio 기준**:
- 0.0~0.2: 좁음 (정밀)
- 0.2~0.5: 중간
- 0.5+: 넓음 (불확실)

---

## 9. 참고 자료

**설계 문서**:
- `BeliefEngine_Design_Enhanced.md` - 전체 설계
- `BeliefEngine_Feedback_Review.md` - 피드백 반영
- `BeliefEngine_Implementation_Complete.md` - 구현 완료

**테스트**:
- `test_belief_engine_phase1.py` - Core 테스트
- `test_belief_engine_phase2.py` - Integration 테스트
- `test_belief_engine_phase3.py` - Advanced 테스트

**YAML**:
- `cmis.yaml` - belief_engine 정의

---

**작성**: 2025-12-12
**버전**: v1.0
**문의**: CMIS Team
