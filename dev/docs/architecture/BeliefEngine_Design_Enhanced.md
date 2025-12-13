# BeliefEngine 설계 (Enhanced)

**작성일**: 2025-12-12
**버전**: v1.0
**상태**: 설계 단계
**목표**: Prior/Belief 관리 및 불확실성 정량화

---

## Executive Summary

BeliefEngine은 CMIS의 마지막 엔진으로, **Evidence가 부족하거나 직접 관찰 불가능한 값**에 대한 Prior/Belief를 관리하고 업데이트하는 역할을 담당합니다.

**핵심 역할**:
1. **Prior Distribution 관리** - Metric/Parameter에 대한 사전 확률 분포
2. **Belief Update** - 새로운 Evidence/Outcome 기반 베이지안 업데이트
3. **Uncertainty Propagation** - 불확실성 전파 및 정량화
4. **ValueEngine 지원** - prior_estimation 단계에서 추정값 제공
5. **LearningEngine 연동** - Outcome 기반 Belief 조정

**핵심 원칙**:
- **Evidence-first, Prior-last** - Prior는 최후 수단
- **Conservative by Default** - 넓은 분포로 시작, 점진적 좁힘
- **Context-aware** - Pattern/Domain/Segment별 다른 Prior
- **Monotonic Improvability** - Belief는 항상 개선 가능

**cmis.yaml 위치**:
```yaml
cognition_plane:
  engines:
    belief_engine:  # 신규 추가 필요
      description: "Prior/Belief 관리 및 불확실성 정량화"
      inputs:
        - "substrate_plane.graphs.pattern_graph"
        - "substrate_plane.graphs.value_graph"
        - "substrate_plane.stores.evidence_store"
      outputs:
        - "prior_distributions"
        - "belief_updates"
```

---

## 1. BeliefEngine 아키텍처

### 1.1 3-Component 구조

```
┌──────────────────────────────────────────────────────────┐
│                   BeliefEngine                            │
│  query_prior_api() / update_belief_api()                 │
└──────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Prior     │  │    Belief    │  │ Uncertainty  │
│   Manager    │  │   Updater    │  │  Propagator  │
│              │  │              │  │              │
│ Prior 저장   │  │ Bayesian     │  │ Monte Carlo  │
│ Context별    │  │ 업데이트     │  │ 분포 계산    │
└──────────────┘  └──────────────┘  └──────────────┘
```

**분리 이유**:
- **PriorManager**: Pattern/Domain별 Prior 관리
- **BeliefUpdater**: Evidence 기반 업데이트 로직
- **UncertaintyPropagator**: 불확실성 전파 및 시뮬레이션

---

## 2. Public API (cmis.yaml 대응)

### 2.1 query_prior_api()

**목적**: ValueEngine의 prior_estimation 단계에서 호출

**cmis.yaml 정의** (신규):
```yaml
belief_engine:
  api:
    - name: query_prior
      description: "특정 Metric/Context에 대한 Prior Distribution 조회"
      input:
        metric_id: "metric_id"
        context: "dict"
        policy_ref: "policy_ref"
      output:
        prior_distribution: "distribution"
        confidence: "float (0~1)"
        lineage: "lineage_ref"
```

**구현**:
```python
class BeliefEngine:
    """Belief Engine - Prior/Belief 관리 엔진"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        
        # Components
        self.prior_manager = PriorManager()
        self.belief_updater = BeliefUpdater()
        self.uncertainty_propagator = UncertaintyPropagator()
        
        # Pattern/Value Graph 참조
        self.pattern_engine = PatternEngineV2()
        self.value_engine = ValueEngine()
    
    def query_prior_api(
        self,
        metric_id: str,
        context: Dict[str, Any],
        policy_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Public API - Prior Distribution 조회
        
        Args:
            metric_id: 조회할 Metric ID (예: "MET-SAM")
            context: {domain_id, region, segment, ...}
            policy_ref: Policy (exploration_friendly는 넓은 분포 허용)
        
        Returns:
            {
                "prior_id": "PRIOR-xxxx",
                "metric_id": "MET-SAM",
                "context": {...},
                "distribution": {
                    "type": "lognormal",  # normal, uniform, beta, ...
                    "params": {"mu": 10.5, "sigma": 0.8},
                    "percentiles": {
                        "p10": 15000,
                        "p50": 50000,
                        "p90": 150000
                    }
                },
                "confidence": 0.6,  # Prior 신뢰도 (0~1)
                "source": "pattern_benchmark",  # pattern_benchmark, domain_expert, uninformative
                "lineage": {
                    "from_pattern_ids": ["PAT-subscription_model"],
                    "from_evidence_ids": ["EVD-industry_report"],
                    "created_at": "2025-12-12T10:00:00Z"
                }
            }
        """
        # 1. Context 기반 Prior 조회 시도
        prior = self.prior_manager.get_prior(metric_id, context)
        
        if prior is None:
            # 2. Prior 없으면 Pattern 기반 생성
            prior = self._generate_prior_from_pattern(metric_id, context)
        
        # 3. Policy에 따라 분포 조정
        if policy_ref == "exploration_friendly":
            prior = self._widen_distribution(prior)
        
        return {
            "prior_id": f"PRIOR-{uuid.uuid4().hex[:8]}",
            "metric_id": metric_id,
            "context": context,
            "distribution": prior["distribution"],
            "confidence": prior["confidence"],
            "source": prior["source"],
            "lineage": prior["lineage"]
        }
```

---

### 2.2 update_belief_api()

**목적**: LearningEngine이 Outcome 기반으로 Belief 업데이트 요청

**cmis.yaml 정의** (신규):
```yaml
belief_engine:
  api:
    - name: update_belief
      description: "Evidence/Outcome 기반 Belief 업데이트"
      input:
        metric_id: "metric_id"
        context: "dict"
        observations: "list[observation]"
        update_mode: "enum[bayesian,replace]"
      output:
        updated_belief: "belief_record"
        delta: "dict"  # 업데이트 전/후 차이
```

**구현**:
```python
def update_belief_api(
    self,
    metric_id: str,
    context: Dict[str, Any],
    observations: List[Dict[str, Any]],
    update_mode: str = "bayesian"
) -> Dict[str, Any]:
    """
    Public API - Belief 업데이트
    
    Args:
        metric_id: 업데이트할 Metric ID
        context: {domain_id, region, segment, ...}
        observations: [
            {"value": 50000, "weight": 1.0, "source": "EVD-xxx"},
            {"value": 48000, "weight": 0.8, "source": "OUT-xxx"},
            ...
        ]
        update_mode:
            - "bayesian": 베이지안 업데이트 (기본)
            - "replace": 직접 대체
    
    Returns:
        {
            "belief_id": "BELIEF-xxxx",
            "metric_id": "MET-SAM",
            "context": {...},
            "prior": {
                "distribution": {...},
                "confidence": 0.6
            },
            "posterior": {
                "distribution": {...},
                "confidence": 0.85  # 업데이트 후 증가
            },
            "delta": {
                "mean_shift": +5000,
                "sigma_reduction": -0.2,
                "confidence_gain": +0.25
            },
            "lineage": {...}
        }
    """
    # 1. 기존 Prior/Belief 조회
    prior = self.prior_manager.get_prior(metric_id, context)
    if prior is None:
        prior = self._generate_uninformative_prior(metric_id)
    
    # 2. Bayesian Update
    if update_mode == "bayesian":
        posterior = self.belief_updater.bayesian_update(
            prior=prior["distribution"],
            observations=observations
        )
    else:  # replace
        posterior = self.belief_updater.direct_replace(observations)
    
    # 3. Delta 계산
    delta = self._calculate_delta(prior["distribution"], posterior)
    
    # 4. 업데이트된 Belief 저장
    belief_record = self.prior_manager.save_belief(
        metric_id=metric_id,
        context=context,
        posterior=posterior,
        observations=observations
    )
    
    return {
        "belief_id": belief_record["belief_id"],
        "metric_id": metric_id,
        "context": context,
        "prior": prior,
        "posterior": {
            "distribution": posterior,
            "confidence": self._calculate_confidence(posterior, observations)
        },
        "delta": delta,
        "lineage": belief_record["lineage"]
    }
```

---

### 2.3 propagate_uncertainty_api()

**목적**: Metric 계산 시 불확실성 전파

**cmis.yaml 정의** (신규):
```yaml
belief_engine:
  api:
    - name: propagate_uncertainty
      description: "공식 기반 불확실성 전파 (Monte Carlo)"
      input:
        formula: "string"  # 예: "Revenue = N_customers * ARPU"
        input_distributions: "dict"  # 각 변수의 분포
        n_samples: "int"
      output:
        output_distribution: "distribution"
        sensitivity: "dict"  # 각 입력의 민감도
```

**구현**:
```python
def propagate_uncertainty_api(
    self,
    formula: str,
    input_distributions: Dict[str, Dict],
    n_samples: int = 10000
) -> Dict[str, Any]:
    """
    Public API - 불확실성 전파 (Monte Carlo)
    
    Args:
        formula: "Revenue = N_customers * ARPU"
        input_distributions: {
            "N_customers": {
                "type": "normal",
                "params": {"mu": 100000, "sigma": 10000}
            },
            "ARPU": {
                "type": "lognormal",
                "params": {"mu": 3.5, "sigma": 0.3}
            }
        }
        n_samples: Monte Carlo 샘플 수
    
    Returns:
        {
            "output_distribution": {
                "type": "empirical",
                "samples": [...],
                "percentiles": {
                    "p10": 3500000,
                    "p50": 5000000,
                    "p90": 7000000
                }
            },
            "sensitivity": {
                "N_customers": 0.6,  # 분산 기여도
                "ARPU": 0.4
            },
            "statistics": {
                "mean": 5000000,
                "std": 1200000,
                "cv": 0.24  # Coefficient of Variation
            }
        }
    """
    # Monte Carlo 시뮬레이션
    result = self.uncertainty_propagator.monte_carlo(
        formula=formula,
        input_distributions=input_distributions,
        n_samples=n_samples
    )
    
    # 민감도 분석
    sensitivity = self.uncertainty_propagator.sensitivity_analysis(
        formula=formula,
        input_distributions=input_distributions,
        output_samples=result["samples"]
    )
    
    return {
        "output_distribution": {
            "type": "empirical",
            "samples": result["samples"],
            "percentiles": result["percentiles"]
        },
        "sensitivity": sensitivity,
        "statistics": result["statistics"]
    }
```

---

## 3. Core Components

### 3.1 PriorManager

**책임**: Prior Distribution 저장/조회/생성

```python
class PriorManager:
    """Prior Distribution 관리"""
    
    def __init__(self):
        self.priors: Dict[str, Dict] = {}  # (metric_id, context_hash) -> prior
        self.pattern_priors: Dict[str, Dict] = {}  # pattern_id -> benchmark
    
    def get_prior(
        self,
        metric_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict]:
        """Context별 Prior 조회"""
        context_hash = self._hash_context(context)
        key = f"{metric_id}:{context_hash}"
        return self.priors.get(key)
    
    def save_belief(
        self,
        metric_id: str,
        context: Dict[str, Any],
        posterior: Dict,
        observations: List[Dict]
    ) -> Dict:
        """업데이트된 Belief 저장 (Prior로 재사용)"""
        context_hash = self._hash_context(context)
        key = f"{metric_id}:{context_hash}"
        
        belief_record = {
            "belief_id": f"BELIEF-{uuid.uuid4().hex[:8]}",
            "metric_id": metric_id,
            "context": context,
            "distribution": posterior,
            "observations": observations,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "lineage": {
                "from_evidence_ids": [obs["source"] for obs in observations],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # 다음 조회 시 Prior로 사용
        self.priors[key] = belief_record
        return belief_record
    
    def load_pattern_benchmark(
        self,
        pattern_id: str
    ) -> Optional[Dict]:
        """Pattern Benchmark에서 Prior 로드"""
        # PatternEngine의 learned_benchmarks 연동
        return self.pattern_priors.get(pattern_id)
    
    def _hash_context(self, context: Dict) -> str:
        """Context를 해시로 변환 (캐싱용)"""
        sorted_items = sorted(context.items())
        return hashlib.md5(str(sorted_items).encode()).hexdigest()[:8]
```

---

### 3.2 BeliefUpdater

**책임**: Bayesian Update 로직

```python
class BeliefUpdater:
    """Bayesian Belief Update"""
    
    def bayesian_update(
        self,
        prior: Dict,
        observations: List[Dict]
    ) -> Dict:
        """
        베이지안 업데이트
        
        Args:
            prior: {
                "type": "normal",
                "params": {"mu": 50000, "sigma": 10000}
            }
            observations: [
                {"value": 48000, "weight": 1.0},
                {"value": 52000, "weight": 0.8},
                ...
            ]
        
        Returns:
            posterior: {
                "type": "normal",
                "params": {"mu": 49500, "sigma": 6000}
            }
        """
        if prior["type"] == "normal":
            return self._normal_normal_update(prior, observations)
        elif prior["type"] == "lognormal":
            return self._lognormal_update(prior, observations)
        elif prior["type"] == "beta":
            return self._beta_binomial_update(prior, observations)
        else:
            # Fallback: Empirical update
            return self._empirical_update(prior, observations)
    
    def _normal_normal_update(
        self,
        prior: Dict,
        observations: List[Dict]
    ) -> Dict:
        """
        Normal Prior + Normal Likelihood → Normal Posterior
        
        공식:
        σ²_post = 1 / (1/σ²_prior + Σ(w_i/σ²_obs))
        μ_post = σ²_post * (μ_prior/σ²_prior + Σ(w_i*x_i/σ²_obs))
        """
        mu_prior = prior["params"]["mu"]
        sigma_prior = prior["params"]["sigma"]
        
        # Observation variance (가정: 관측 오차 10%)
        sigma_obs = sigma_prior * 0.1
        
        # Weighted observations
        total_weight = sum(obs["weight"] for obs in observations)
        weighted_sum = sum(obs["value"] * obs["weight"] for obs in observations)
        
        # Precision (1/σ²)
        precision_prior = 1 / (sigma_prior ** 2)
        precision_obs = total_weight / (sigma_obs ** 2)
        precision_post = precision_prior + precision_obs
        
        # Posterior
        sigma_post = math.sqrt(1 / precision_post)
        mu_post = (mu_prior * precision_prior + weighted_sum / (sigma_obs ** 2)) / precision_post
        
        return {
            "type": "normal",
            "params": {
                "mu": mu_post,
                "sigma": sigma_post
            }
        }
    
    def direct_replace(
        self,
        observations: List[Dict]
    ) -> Dict:
        """직접 대체 (Bayesian 아님)"""
        values = [obs["value"] for obs in observations]
        weights = [obs["weight"] for obs in observations]
        
        mean = np.average(values, weights=weights)
        std = np.sqrt(np.average((values - mean)**2, weights=weights))
        
        return {
            "type": "normal",
            "params": {
                "mu": mean,
                "sigma": std
            }
        }
```

---

### 3.3 UncertaintyPropagator

**책임**: Monte Carlo 시뮬레이션 및 민감도 분석

```python
class UncertaintyPropagator:
    """불확실성 전파 및 시뮬레이션"""
    
    def monte_carlo(
        self,
        formula: str,
        input_distributions: Dict[str, Dict],
        n_samples: int = 10000
    ) -> Dict:
        """
        Monte Carlo 시뮬레이션
        
        Args:
            formula: "Revenue = N_customers * ARPU"
            input_distributions: {...}
            n_samples: 샘플 수
        
        Returns:
            {
                "samples": [...],
                "percentiles": {...},
                "statistics": {...}
            }
        """
        # 1. 각 입력 변수의 샘플 생성
        samples = {}
        for var_name, dist in input_distributions.items():
            samples[var_name] = self._sample_distribution(dist, n_samples)
        
        # 2. 공식 평가 (각 샘플)
        output_samples = []
        for i in range(n_samples):
            var_values = {var: samples[var][i] for var in samples}
            output = self._evaluate_formula(formula, var_values)
            output_samples.append(output)
        
        output_samples = np.array(output_samples)
        
        # 3. 통계 계산
        return {
            "samples": output_samples.tolist(),
            "percentiles": {
                "p10": float(np.percentile(output_samples, 10)),
                "p25": float(np.percentile(output_samples, 25)),
                "p50": float(np.percentile(output_samples, 50)),
                "p75": float(np.percentile(output_samples, 75)),
                "p90": float(np.percentile(output_samples, 90))
            },
            "statistics": {
                "mean": float(np.mean(output_samples)),
                "std": float(np.std(output_samples)),
                "cv": float(np.std(output_samples) / np.mean(output_samples))
            }
        }
    
    def sensitivity_analysis(
        self,
        formula: str,
        input_distributions: Dict[str, Dict],
        output_samples: List[float]
    ) -> Dict[str, float]:
        """
        민감도 분석 (분산 기여도)
        
        Returns:
            {
                "N_customers": 0.6,  # 출력 분산의 60% 기여
                "ARPU": 0.4
            }
        """
        # Sobol Indices (간이 버전: 상관계수 기반)
        output_var = np.var(output_samples)
        sensitivity = {}
        
        for var_name, dist in input_distributions.items():
            # 해당 변수만 변화시킬 때 출력 분산 계산
            # (실제론 Sobol 시퀀스 사용, 여기선 간이 버전)
            var_contribution = self._estimate_variance_contribution(
                formula, var_name, dist, output_var
            )
            sensitivity[var_name] = var_contribution
        
        # 정규화 (합 = 1.0)
        total = sum(sensitivity.values())
        if total > 0:
            sensitivity = {k: v/total for k, v in sensitivity.items()}
        
        return sensitivity
    
    def _sample_distribution(self, dist: Dict, n: int) -> np.ndarray:
        """분포에서 샘플 생성"""
        if dist["type"] == "normal":
            return np.random.normal(
                dist["params"]["mu"],
                dist["params"]["sigma"],
                n
            )
        elif dist["type"] == "lognormal":
            return np.random.lognormal(
                dist["params"]["mu"],
                dist["params"]["sigma"],
                n
            )
        elif dist["type"] == "uniform":
            return np.random.uniform(
                dist["params"]["min"],
                dist["params"]["max"],
                n
            )
        else:
            raise ValueError(f"Unsupported distribution type: {dist['type']}")
    
    def _evaluate_formula(self, formula: str, var_values: Dict) -> float:
        """공식 평가 (간이 버전)"""
        # 예: "Revenue = N_customers * ARPU"
        # 실제론 AST 파싱 필요
        expr = formula.split("=")[1].strip()
        
        # 변수 치환
        for var, val in var_values.items():
            expr = expr.replace(var, str(val))
        
        # 평가
        return eval(expr)
```

---

## 4. Integration with Other Engines

### 4.1 ValueEngine 통합

**시나리오**: ValueEngine의 prior_estimation 단계

```python
# ValueEngine.metric_resolver.py

def _resolve_metric_prior_estimation(
    self,
    metric_id: str,
    context: Dict,
    policy_ref: str
) -> Optional[Dict]:
    """Stage 3: Prior Estimation"""
    
    # BeliefEngine 호출
    from cmis_core.belief_engine import BeliefEngine
    
    belief_engine = BeliefEngine()
    prior_result = belief_engine.query_prior_api(
        metric_id=metric_id,
        context=context,
        policy_ref=policy_ref
    )
    
    # Prior → ValueRecord 변환
    value_record = {
        "value_id": f"VAL-{uuid.uuid4().hex[:8]}",
        "metric_id": metric_id,
        "context": context,
        "distribution": prior_result["distribution"],
        "quality": {
            "literal_ratio": 0.0,  # Prior는 literal 없음
            "spread_ratio": self._calculate_spread(prior_result["distribution"]),
            "confidence": prior_result["confidence"]
        },
        "lineage": {
            "from_prior_id": prior_result["prior_id"],
            **prior_result["lineage"]
        }
    }
    
    return value_record
```

---

### 4.2 LearningEngine 통합

**시나리오**: Outcome 기반 Belief 업데이트

```python
# LearningEngine.py

def _update_beliefs_from_outcome(
    self,
    outcome: Dict,
    comparison: Dict
) -> List[str]:
    """Outcome 기반 Belief 업데이트"""
    
    from cmis_core.belief_engine import BeliefEngine
    
    belief_engine = BeliefEngine()
    updated_belief_ids = []
    
    for metric_id, delta in comparison["deltas"].items():
        if abs(delta["error_pct"]) > 0.1:  # 10% 이상 오차
            # Observation 구성
            observations = [{
                "value": outcome["metrics"][metric_id],
                "weight": 1.0,
                "source": outcome["outcome_id"]
            }]
            
            # Belief 업데이트
            result = belief_engine.update_belief_api(
                metric_id=metric_id,
                context=outcome["context"],
                observations=observations,
                update_mode="bayesian"
            )
            
            updated_belief_ids.append(result["belief_id"])
    
    return updated_belief_ids
```

---

## 5. Prior Generation Strategies

### 5.1 Pattern-based Prior

**전략**: Pattern Benchmark에서 Prior 생성

```python
def _generate_prior_from_pattern(
    self,
    metric_id: str,
    context: Dict
) -> Dict:
    """Pattern Benchmark 기반 Prior 생성"""
    
    # 1. 유사한 Pattern 찾기
    similar_patterns = self.pattern_engine.match_patterns(context)
    
    if not similar_patterns:
        return self._generate_uninformative_prior(metric_id)
    
    # 2. Pattern Benchmark에서 Metric 값 가져오기
    benchmark_values = []
    for pattern_match in similar_patterns:
        pattern_id = pattern_match["pattern_id"]
        benchmark = self.prior_manager.load_pattern_benchmark(pattern_id)
        
        if benchmark and metric_id in benchmark["metrics"]:
            benchmark_values.append({
                "value": benchmark["metrics"][metric_id]["median"],
                "weight": pattern_match["score"]
            })
    
    if not benchmark_values:
        return self._generate_uninformative_prior(metric_id)
    
    # 3. 가중 평균 및 분산 계산
    values = [b["value"] for b in benchmark_values]
    weights = [b["weight"] for b in benchmark_values]
    
    mean = np.average(values, weights=weights)
    std = np.std(values) * 1.5  # 보수적 확대
    
    return {
        "distribution": {
            "type": "lognormal",  # 시장 규모는 lognormal
            "params": {
                "mu": math.log(mean),
                "sigma": math.log(1 + std / mean)
            }
        },
        "confidence": 0.5,  # Pattern 기반 중간 신뢰도
        "source": "pattern_benchmark",
        "lineage": {
            "from_pattern_ids": [p["pattern_id"] for p in similar_patterns],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    }
```

---

### 5.2 Uninformative Prior

**전략**: Evidence 전혀 없을 때 매우 넓은 분포

```python
def _generate_uninformative_prior(self, metric_id: str) -> Dict:
    """Uninformative Prior (매우 넓은 분포)"""
    
    # Metric category 기반 범위 설정
    metric_spec = self._get_metric_spec(metric_id)
    category = metric_spec.get("category", "custom")
    
    if category == "market_size":
        # 시장 규모: 1M ~ 1T (Order of magnitude 범위)
        return {
            "distribution": {
                "type": "loguniform",
                "params": {
                    "min": 1e6,
                    "max": 1e12
                }
            },
            "confidence": 0.1,  # 매우 낮은 신뢰도
            "source": "uninformative",
            "lineage": {
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
    elif category == "unit_economics":
        # 단가: 100원 ~ 100만원
        return {
            "distribution": {
                "type": "loguniform",
                "params": {
                    "min": 100,
                    "max": 1e6
                }
            },
            "confidence": 0.1,
            "source": "uninformative",
            "lineage": {
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
    else:
        # 기타: 0~1 (비율/확률)
        return {
            "distribution": {
                "type": "uniform",
                "params": {
                    "min": 0.0,
                    "max": 1.0
                }
            },
            "confidence": 0.1,
            "source": "uninformative",
            "lineage": {
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
```

---

## 6. Implementation Plan

### Phase 1: Core Components (4시간)

**목표**: 3개 Component 구현 + 기본 테스트

**작업**:
1. `cmis_core/prior_manager.py` (150 라인)
   - PriorManager 클래스
   - get_prior(), save_belief()
   - Pattern Benchmark 로딩

2. `cmis_core/belief_updater.py` (200 라인)
   - BeliefUpdater 클래스
   - bayesian_update() (Normal-Normal)
   - direct_replace()

3. `cmis_core/uncertainty_propagator.py` (200 라인)
   - UncertaintyPropagator 클래스
   - monte_carlo()
   - sensitivity_analysis()

4. `dev/tests/unit/test_belief_engine_phase1.py` (200 라인, 10 테스트)
   - PriorManager 테스트
   - BeliefUpdater 테스트 (Normal-Normal)
   - UncertaintyPropagator 테스트 (간단한 공식)

**검증**:
- [ ] 10개 테스트 통과
- [ ] Type hints 완전
- [ ] Docstring 완전

---

### Phase 2: Engine Integration (3시간)

**목표**: ValueEngine/LearningEngine 연동

**작업**:
1. `cmis_core/belief_engine.py` (300 라인)
   - BeliefEngine 클래스
   - query_prior_api()
   - update_belief_api()
   - propagate_uncertainty_api()

2. ValueEngine 연동
   - `cmis_core/value_engine.py` 수정
   - prior_estimation 단계에서 BeliefEngine 호출

3. LearningEngine 연동
   - `cmis_core/learning_engine.py` 수정
   - Belief 업데이트 호출

4. `dev/tests/unit/test_belief_engine_phase2.py` (250 라인, 12 테스트)
   - query_prior_api 테스트
   - update_belief_api 테스트
   - ValueEngine 연동 테스트
   - LearningEngine 연동 테스트

**검증**:
- [ ] 12개 테스트 통과
- [ ] ValueEngine prior_estimation 동작
- [ ] LearningEngine Belief 업데이트 동작

---

### Phase 3: Advanced Features (2시간)

**목표**: 고급 분포 및 최적화

**작업**:
1. 추가 분포 지원
   - Lognormal-Lognormal Update
   - Beta-Binomial Update
   - Gamma-Poisson Update

2. 고급 Monte Carlo
   - Sobol Sequence (Quasi-random)
   - Importance Sampling

3. Belief Store
   - 영속성 (파일/DB)
   - 버전 관리

4. `dev/tests/unit/test_belief_engine_phase3.py` (200 라인, 10 테스트)
   - Lognormal 업데이트 테스트
   - Sobol Monte Carlo 테스트
   - Belief Store 테스트

**검증**:
- [ ] 10개 테스트 통과
- [ ] 모든 분포 타입 지원
- [ ] 영속성 동작

---

## 7. cmis.yaml 업데이트

### 7.1 신규 추가

```yaml
cognition_plane:
  engines:
    belief_engine:
      description: "Prior/Belief 관리 및 불확실성 정량화 엔진"
      version: "v1.0"
      status: "production_ready"
      inputs:
        - "substrate_plane.graphs.pattern_graph"
        - "substrate_plane.graphs.value_graph"
        - "substrate_plane.stores.evidence_store"
      outputs:
        - "prior_distributions"
        - "belief_updates"
      api:
        - name: "query_prior"
          description: "특정 Metric/Context에 대한 Prior Distribution 조회"
          input:
            metric_id: "metric_id"
            context: "dict"
            policy_ref: "policy_ref (optional)"
          output:
            prior_distribution: "distribution"
            confidence: "float (0~1)"
            lineage: "lineage_ref"
        
        - name: "update_belief"
          description: "Evidence/Outcome 기반 Belief 업데이트"
          input:
            metric_id: "metric_id"
            context: "dict"
            observations: "list[observation]"
            update_mode: "enum[bayesian,replace]"
          output:
            updated_belief: "belief_record"
            delta: "dict"
        
        - name: "propagate_uncertainty"
          description: "공식 기반 불확실성 전파 (Monte Carlo)"
          input:
            formula: "string"
            input_distributions: "dict"
            n_samples: "int"
          output:
            output_distribution: "distribution"
            sensitivity: "dict"
      
      prior_strategies:
        - id: "pattern_benchmark"
          description: "Pattern Benchmark 기반 Prior 생성"
          confidence: 0.5
        - id: "domain_expert"
          description: "도메인 전문가 의견 기반 Prior"
          confidence: 0.7
        - id: "uninformative"
          description: "매우 넓은 범위의 Uninformative Prior"
          confidence: 0.1
      
      update_modes:
        - id: "bayesian"
          description: "베이지안 업데이트 (Prior × Likelihood → Posterior)"
          default: true
        - id: "replace"
          description: "직접 대체 (관측값 기반 새 분포)"
```

### 7.2 value_engine 업데이트

```yaml
value_engine:
  metric_resolver:
    stages:
      - id: "prior_estimation"
        uses:
          - "belief_engine.query_prior"  # 추가
          - "pattern_engine.match_patterns"
          - "LLM_prior"
```

---

## 8. Testing Strategy

### 8.1 Unit Tests (32개)

**Phase 1 (10개)**:
- PriorManager: 저장/조회/해싱 (3개)
- BeliefUpdater: Normal-Normal 업데이트 (4개)
- UncertaintyPropagator: Monte Carlo/민감도 (3개)

**Phase 2 (12개)**:
- query_prior_api: Pattern/Uninformative (4개)
- update_belief_api: Bayesian/Replace (4개)
- ValueEngine 연동 (2개)
- LearningEngine 연동 (2개)

**Phase 3 (10개)**:
- Lognormal/Beta 업데이트 (4개)
- Sobol Monte Carlo (2개)
- Belief Store 영속성 (4개)

---

### 8.2 Integration Tests (5개)

1. **E2E: ValueEngine Prior Estimation**
   - Evidence 없는 Metric → BeliefEngine → Prior 반환

2. **E2E: LearningEngine Belief Update**
   - Outcome → 오차 → BeliefEngine 업데이트

3. **E2E: Uncertainty Propagation**
   - 여러 Metric 분포 → 공식 → 결과 분포

4. **E2E: Prior → Belief → Improved Prior**
   - 초기 Prior → 관측 → 업데이트 → 다음 조회 시 개선된 Prior

5. **E2E: Pattern Benchmark 기반 Prior**
   - Pattern 매칭 → Benchmark → Prior 생성

---

## 9. Performance Considerations

### 9.1 캐싱

```python
class PriorManager:
    def __init__(self):
        self._cache = {}  # (metric_id, context_hash) -> prior
        self._cache_ttl = 3600  # 1시간
```

### 9.2 Monte Carlo 최적화

- **Quasi-random**: Sobol Sequence (수렴 빠름)
- **병렬화**: multiprocessing (n_samples 큼)
- **조기 종료**: 수렴 감지 (CV < threshold)

---

## 10. Documentation

### 10.1 사용자 가이드

**예시: Prior 조회**
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
    policy_ref="exploration_friendly"
)

print(f"Prior 분포: {prior['distribution']}")
print(f"신뢰도: {prior['confidence']}")
```

**예시: Belief 업데이트**
```python
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
    update_mode="bayesian"
)

print(f"Prior 평균: {result['prior']['distribution']['params']['mu']}")
print(f"Posterior 평균: {result['posterior']['distribution']['params']['mu']}")
print(f"평균 이동: {result['delta']['mean_shift']}")
```

---

## 11. Future Enhancements

### v1.1: 고급 분포
- Student-t (heavy tail)
- Mixture Models
- Copula (다변량 종속성)

### v1.2: 능동 학습
- Acquisition Function (어디를 관측할지)
- Experimental Design

### v1.3: 인과 추론
- Causal DAG
- Do-calculus

---

## 12. Summary

**BeliefEngine 핵심**:
1. **Prior Management** - Pattern/Context별 Prior 관리
2. **Bayesian Update** - Evidence 기반 점진적 개선
3. **Uncertainty Propagation** - Monte Carlo 시뮬레이션
4. **Conservative by Default** - 넓은 분포로 시작, 증거 수집 시 좁힘
5. **Full Integration** - ValueEngine/LearningEngine 완전 연동

**구현 일정**:
- Phase 1: 4시간 (Core)
- Phase 2: 3시간 (Integration)
- Phase 3: 2시간 (Advanced)
- **총 9시간**

**완성 시 효과**:
- ✅ CMIS 9/9 엔진 완성 (100%)
- ✅ Evidence 부족 상황 대응
- ✅ 불확실성 정량화
- ✅ 의사결정 신뢰도 향상

---

**작성**: 2025-12-12
**버전**: v1.0
**다음 단계**: Phase 1 구현 시작

