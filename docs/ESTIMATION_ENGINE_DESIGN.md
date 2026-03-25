# Estimation Engine 설계 문서

> Belief Engine을 폐기하고 완전히 재설계하는 Estimation Engine.
> 8-Agent Panel Review (2026-03-25) 결과 + confidence-sigma 리서치 반영.

## 1. 목적

정확한 숫자가 존재하지 않을 때, 아래 메커니즘을 활용해 합리적으로 추정하는 엔진:

1. **관계 추론** — 메트릭 간 선후관계, 포함관계 (TAM >= SAM >= SOM, Revenue = N x ARPU)
2. **경계 제약** — 물리적 hard constraint (0 <= churn <= 1, SOM <= SAM)
3. **Fermi 추정** — 미지의 숫자를 추정 가능한 하위 요소로 분해

## 2. 핵심 설계 원칙

| 원칙 | 의미 |
|------|------|
| **LLM은 구조를 설계하고, 엔진은 계산한다** | LLM이 분해 구조/관계를 결정하면, 엔진이 구간 산술로 계산 |
| **모든 추정은 구간이다** | 단일 숫자가 아닌 [lo, hi] 구간이 primary, 점추정은 파생 |
| **제약은 선언적이다** | metric 간 관계는 ontology.yaml에 선언, 코드가 자동 전파 |
| **신뢰도는 전파된다** | 입력 신뢰도가 체인을 통해 감쇠 전파 |
| **상충은 명시적이다** | 증거 충돌 시 confidence를 올리지 않고 명시적으로 보고 |

## 3. 데이터 모델

### 3.1 Interval (구간)

모든 추정의 기본 단위. 단일 숫자가 아닌 범위로 표현.

```python
@dataclass
class Interval:
    lo: float          # 하한
    hi: float          # 상한

    @property
    def midpoint(self) -> float: ...
    @property
    def spread_ratio(self) -> float: ...  # (hi-lo)/|midpoint|

    # 구간 산술: __add__, __sub__, __mul__, __truediv__
```

### 3.2 Estimate (추정 레코드)

하나의 메트릭에 대한 하나의 추정 결과.

```python
@dataclass
class Estimate:
    estimate_id: str           # "EST-{uuid6}"
    metric_id: str             # "MET-TAM"
    interval: Interval         # [1.5조, 2.5조]
    point_estimate: float      # midpoint 또는 가중 중심
    method: str                # "fermi", "top_down", "bottom_up", "constraint", "proxy"
    source_reliability: float  # 데이터 소스 신뢰도 (0~1)
    estimate_confidence: float # 추정 과정 확신도 (0~1)
    sigma: float               # confidence_to_sigma()로 파생
    evidence_id: str           # 근거 증거 ID
    decomposition_ref: str     # Fermi 트리 ID (해당 시)
    created_at: str
```

핵심 변경: **confidence를 3가지로 분리**
- `source_reliability`: 데이터 소스의 객관적 품질 (KOSIS=0.9, 뉴스=0.3)
- `estimate_confidence`: 추정자의 주관적 확신도 (sigma 파생의 입력)
- `evidence_weight` (update 시): 기존 대비 반영 비중

### 3.3 MetricEstimation (메트릭별 추정 상태)

하나의 메트릭에 대한 **모든 추정을 동시 보유**. 삼각검증의 전제.

```python
@dataclass
class MetricEstimation:
    metric_id: str
    estimates: list[Estimate]   # 방법별 복수 추정
    fused: Estimate | None      # 삼각검증 합성 결과 (있으면)
    constraints_applied: bool   # 제약 전파 적용 여부
    version: int
    updated_at: str
```

### 3.4 FermiNode (분해 트리)

```python
@dataclass
class FermiNode:
    variable: str                # 목표 변수 이름
    operation: str               # "multiply", "add", "divide", "leaf"
    children: list[FermiNode]    # 하위 노드
    estimate: Interval | None    # leaf 노드의 추정 구간
    source: str                  # 추정 근거
    source_reliability: float    # 소스 신뢰도
```

### 3.5 Constraint (제약)

```python
@dataclass
class Constraint:
    kind: str                    # "identity", "inequality", "bound"
    variables: list[str]         # 관련 메트릭 ID들
    expression: str              # "MET-Revenue = MET-N_customers * MET-ARPU"
```

## 4. confidence → sigma 변환

METRIC_REGISTRY의 unit/bounds 기반 분기:

```python
def confidence_to_sigma(
    estimate_confidence: float,  # 0.05 ~ 0.95 (clamp)
    point_estimate: float,
    metric_id: str,
) -> float:
    unit = METRIC_REGISTRY[metric_id]["unit"]
    bounds = METRIC_REGISTRY[metric_id].get("bounds")

    if unit == "ratio" and bounds:
        # 절대값 방식: bounds 범위 기반
        range_width = bounds["max"] - bounds["min"]
        return range_width * 0.3 * (1 - confidence) ** 1.5

    elif unit in ("currency", "count"):
        # CV 방식: 규모 연동
        cv = 0.5 * (1 - confidence)
        return cv * abs(point_estimate)

    elif unit == "percentage":
        return 2.0 * (1 - confidence)

    elif unit == "index" and bounds:
        range_width = bounds["max"] - bounds["min"]
        return range_width * 0.2 * (1 - confidence) ** 1.5

    else:
        # fallback: CV
        cv = 0.5 * (1 - confidence)
        return cv * abs(point_estimate) if point_estimate else 1.0
```

## 5. 상충 검출 + Variance Inflation

```python
def detect_conflict(prior_mu, prior_sigma, obs_value) -> tuple[float, bool]:
    z = abs(obs_value - prior_mu) / prior_sigma if prior_sigma > 0 else 0
    return z, z > 2.0

def inflate_sigma(base_sigma, z_score) -> float:
    if z_score <= 2.0:
        return base_sigma
    inflation = max(1.0, z_score ** 2 / 4)
    return base_sigma * inflation
```

## 6. 구간 기반 업데이트 (update_belief 대체)

```python
def update_estimate(
    current: MetricEstimation,
    new_value: float,
    new_sigma: float,
) -> MetricEstimation:
    if not current.estimates:
        # 첫 추정 → 그대로 저장
        ...
    else:
        best = current.fused or current.estimates[-1]
        z, is_conflict = detect_conflict(best.point_estimate, best.sigma, new_value)

        if is_conflict:
            new_sigma = inflate_sigma(new_sigma, z)

        # 정규-정규 켤레 (sigma 기반)
        prior_prec = 1 / best.sigma**2
        obs_prec = 1 / new_sigma**2
        post_prec = prior_prec + obs_prec
        post_mu = (best.point_estimate * prior_prec + new_value * obs_prec) / post_prec
        post_sigma = (1 / post_prec) ** 0.5

        # Interval 자동 갱신: [mu - 2*sigma, mu + 2*sigma]
        ...
```

## 7. 도구 (LLM Tool) 설계

### 7.1 새 도구

| 도구 | 입력 | 출력 | 역할 |
|------|------|------|------|
| `create_estimate` | metric_id, point_estimate, estimate_confidence, method, evidence_id | Estimate | 새 추정 등록 (set_prior + set_metric_value 통합) |
| `get_estimate` | metric_id | MetricEstimation | 현재 추정 상태 조회 (get_prior 대체) |
| `update_estimate` | metric_id, new_value, estimate_confidence, evidence_id | MetricEstimation | 증거 기반 갱신 (update_belief 대체) |
| `list_estimates` | (없음) | list[MetricEstimation] | 전체 목록 (list_beliefs 대체) |
| `create_fermi_tree` | target_metric, decomposition | tree_id, computed_interval | Fermi 분해 계산 |
| `check_constraints` | metric_values | violations, narrowed_intervals | 제약 위반 검출 |

### 7.2 기존 도구 graceful degradation

기존 도구 4개는 새 엔진으로 위임(delegate):

```python
# tools.py에서 기존 인터페이스 유지
def set_prior(self, metric_id, point_estimate, confidence=0.3, source="expert_guess", distribution=None):
    """[DEPRECATED → create_estimate] 기존 호환용."""
    return self.create_estimate(
        metric_id=metric_id,
        point_estimate=point_estimate,
        estimate_confidence=confidence,
        method=source,  # "expert_guess" → method로 매핑
        evidence_id="",
    )

def get_prior(self, metric_id):
    """[DEPRECATED → get_estimate] 기존 호환용."""
    return self.get_estimate(metric_id)

def update_belief(self, metric_id, new_evidence_value, evidence_confidence=0.5):
    """[DEPRECATED → update_estimate] 기존 호환용."""
    return self.update_estimate(
        metric_id=metric_id,
        new_value=new_evidence_value,
        estimate_confidence=evidence_confidence,
        evidence_id="",
    )

def list_beliefs(self):
    """[DEPRECATED → list_estimates] 기존 호환용."""
    return self.list_estimates()
```

## 8. 파일 구조

```
cmis_v2/engines/
├── estimation.py          # 새 Estimation Engine (belief.py 대체)
├── belief.py              # [DEPRECATED] → estimation.py로 위임
├── interval.py            # Interval 데이터 타입 + 구간 산술
├── constraints.py         # Constraint 정의 + 전파 로직
├── fermi.py               # Fermi 분해 트리 구조 + 계산
├── evidence.py            # (기존 유지)
├── value.py               # (기존 유지, estimation과 연결)
├── ...
```

## 9. ontology.yaml 확장 (Phase 2)

```yaml
metrics:
  MET-Revenue:
    relations:
      - type: identity
        formula: "MET-N_customers * MET-ARPU"
  MET-SOM:
    relations:
      - type: inequality
        constraint: "MET-SOM <= MET-SAM"
      - type: inequality
        constraint: "MET-SAM <= MET-TAM"
  MET-LTV:
    relations:
      - type: identity
        formula: "MET-ARPU / MET-Churn_rate"
```

## 10. 구현 단계

### Phase 1: 핵심 (이번 작업)
- [ ] `interval.py` — Interval 타입 + 산술
- [ ] `estimation.py` — Estimate, MetricEstimation, confidence_to_sigma, conflict detection
- [ ] `belief.py` deprecated → estimation.py 위임
- [ ] `tools.py` — 새 도구 등록 + 기존 도구 graceful degradation

### Phase 2: 제약 + 분해
- [ ] `constraints.py` — Constraint 정의 + 전파
- [ ] `fermi.py` — FermiNode + 트리 계산
- [ ] `ontology.yaml` — relations 필드 추가
- [ ] `generate_from_ontology.py` — METRIC_RELATIONS 생성

### Phase 3: 고도화
- [ ] Triangulation (다중 추정 합성)
- [ ] Calibration (Learning Engine 연동)
- [ ] Beta distribution (bounded ratio metrics)
- [ ] Reference Class Forecasting

## 11. 핵심 가치 정합성

| 가치 | 정합 방식 |
|------|----------|
| Evidence-first | create_estimate에 evidence_id 필수 (force_unverified 우회 가능) |
| 구조화된 흐름 | Interval → Estimate → MetricEstimation → fused 단계적 흐름 |
| 인간 검토 게이트 | fused 결과의 spread_ratio가 임계치 초과 시 user gate 트리거 |
| 재현 가능성 | 엔진 계산 수준에서 결정적 (동일 입력 → 동일 출력). LLM 분해 구조는 비결정적임을 명시 |
