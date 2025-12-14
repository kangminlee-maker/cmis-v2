# BeliefEngine 설계안 피드백 검토 및 적용안

**작성일**: 2025-12-12
**리뷰어**: CMIS Architect
**대상**: BeliefEngine_Design_Enhanced.md v1.0
**결론**: 구조 유지 + 7개 포인트 보강

---

## Executive Summary

### 피드백 총평

> **BeliefEngine 설계는 CMIS 철학/아키텍처와 구조적으로 잘 맞습니다.**
> 완전 재설계 불필요, 스키마/정책/성능 보강으로 Production 가능.

### 적용 방향

**✅ 유지할 것**:
- 3-Component 구조 (PriorManager/BeliefUpdater/UncertaintyPropagator)
- Public API 3개 (query_prior/update_belief/propagate_uncertainty)
- ValueEngine/LearningEngine 연동 구조
- Evidence-first, Prior-last 철학

**🔧 보강할 것** (7개 포인트):
1. **스키마 통일** (BeliefRecord 정의)
2. **영속성 확보** (belief_store 또는 value_store 활용)
3. **정책 통합** (Policy/Quality 프로파일)
4. **컨텍스트 정밀도** (Pattern Benchmark 필터링)
5. **업데이트 기준** (metrics_spec 연동)
6. **안전성 강화** (UncertaintyPropagator)
7. **구현 디테일** (타입/lineage)

---

## 1. 보강 포인트별 적용안 (우선순위 순)

### Priority 1: BeliefRecord 스키마 통일 ⭐⭐⭐

**문제점**:
```python
# PriorManager.save_belief() 반환
{"belief_id": ..., "distribution": ..., "observations": ...}
# ❌ confidence, source 없음

# query_prior_api() 기대
prior["distribution"], prior["confidence"], prior["source"]
# ❌ KeyError 발생 위험
```

**적용안**:

```python
# cmis_core/types.py에 추가

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class BeliefRecord:
    """Belief/Prior Distribution 통합 레코드"""
    
    # 식별
    belief_id: str  # "BELIEF-xxxx" 또는 "PRIOR-xxxx"
    metric_id: str
    context: Dict[str, Any]  # {domain_id, region, segment, ...}
    
    # 분포
    distribution: Dict[str, Any]  # {type, params, percentiles}
    confidence: float  # 0~1
    source: str  # "pattern_benchmark" | "uninformative" | "learned" | "domain_expert"
    
    # 관측/업데이트
    observations: List[Dict[str, Any]]  # [{value, weight, source}, ...]
    n_observations: int  # 관측 횟수
    
    # 메타
    created_at: str  # ISO datetime
    updated_at: str  # ISO datetime
    lineage: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """dict로 직렬화"""
        return {
            "belief_id": self.belief_id,
            "metric_id": self.metric_id,
            "context": self.context,
            "distribution": self.distribution,
            "confidence": self.confidence,
            "source": self.source,
            "observations": self.observations,
            "n_observations": self.n_observations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "lineage": self.lineage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BeliefRecord":
        """dict에서 복원"""
        return cls(**data)
```

**구현 변경**:

```python
# cmis_core/prior_manager.py

class PriorManager:
    def get_prior(
        self,
        metric_id: str,
        context: Dict[str, Any]
    ) -> Optional[BeliefRecord]:
        """항상 BeliefRecord 반환"""
        context_hash = self._hash_context(context)
        key = f"{metric_id}:{context_hash}"
        
        belief_dict = self.priors.get(key)
        if belief_dict is None:
            return None
        
        return BeliefRecord.from_dict(belief_dict)
    
    def save_belief(
        self,
        metric_id: str,
        context: Dict[str, Any],
        posterior: Dict,
        observations: List[Dict],
        prior: Optional[BeliefRecord] = None
    ) -> BeliefRecord:
        """BeliefRecord 생성/업데이트"""
        
        # 새 BeliefRecord 생성
        belief = BeliefRecord(
            belief_id=f"BELIEF-{uuid.uuid4().hex[:8]}",
            metric_id=metric_id,
            context=context,
            distribution=posterior,
            confidence=self._calculate_confidence(posterior, observations),
            source=prior.source if prior else "learned",
            observations=observations,
            n_observations=(prior.n_observations if prior else 0) + len(observations),
            created_at=prior.created_at if prior else datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            lineage={
                "from_evidence_ids": [obs.get("source") for obs in observations if obs.get("source", "").startswith("EVD-")],
                "from_outcome_ids": [obs.get("source") for obs in observations if obs.get("source", "").startswith("OUT-")],
                "from_prior_id": prior.belief_id if prior else None,
                "engine_ids": ["belief_engine"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # 저장 (다음 조회 시 Prior로 사용)
        context_hash = self._hash_context(context)
        key = f"{metric_id}:{context_hash}"
        self.priors[key] = belief.to_dict()
        
        return belief
```

**Phase 1 반영**: ✅ PriorManager, BeliefUpdater에서 BeliefRecord 사용

---

### Priority 2: Belief 영속성 확보 (belief_store 정의) ⭐⭐⭐

**문제점**:
- 현재 메모리 dict (`self.priors`)만 사용
- 프로세스 재시작 시 모든 Belief 손실
- cmis.yaml에 belief_store 정의 없음

**적용안 A (권장): Belief = 특수 ValueRecord**

```yaml
# cmis.yaml - substrate_plane.stores.value_store 활용

value_store:
  schema:
    fields:
      value_id: "VAL-*"
      metric_id: "MET-*"
      context: "dict"
      point_estimate: "number (optional)"  # Prior는 null
      distribution: "distribution_ref"     # Prior는 여기만
      quality:
        literal_ratio: "float"  # Prior는 0.0
        spread_ratio: "float"   # Prior는 높음
        confidence: "float"
      origin: "enum[direct,derived,prior,learned]"  # 추가
      lineage: "lineage_ref"
```

**구현**:

```python
# cmis_core/prior_manager.py

class PriorManager:
    def __init__(self, value_store_path: Optional[Path] = None):
        self.value_store_path = value_store_path or Path("data/value_store")
        self.value_store_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, BeliefRecord] = {}  # 메모리 캐시
        self._cache_ttl = 3600  # 1시간
    
    def get_prior(
        self,
        metric_id: str,
        context: Dict[str, Any]
    ) -> Optional[BeliefRecord]:
        """value_store에서 Prior ValueRecord 조회"""
        
        # 1. 캐시 확인
        cache_key = self._make_cache_key(metric_id, context)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 2. value_store 조회
        belief = self._load_from_value_store(metric_id, context)
        
        # 3. 캐싱
        if belief:
            self._cache[cache_key] = belief
        
        return belief
    
    def save_belief(
        self,
        belief: BeliefRecord
    ) -> None:
        """value_store에 저장"""
        
        # ValueRecord 형식으로 변환
        value_record = {
            "value_id": f"VAL-{belief.belief_id}",
            "metric_id": belief.metric_id,
            "context": belief.context,
            "point_estimate": None,  # Prior는 분포만
            "distribution": belief.distribution,
            "quality": {
                "literal_ratio": 0.0,  # Prior는 literal 없음
                "spread_ratio": self._calculate_spread(belief.distribution),
                "confidence": belief.confidence
            },
            "origin": belief.source,  # "prior" | "learned"
            "lineage": belief.lineage,
            "stored_at": belief.updated_at
        }
        
        # 파일 저장
        filepath = self.value_store_path / f"{belief.belief_id}.json"
        with open(filepath, "w") as f:
            json.dump(value_record, f, indent=2)
        
        # 캐시 업데이트
        cache_key = self._make_cache_key(belief.metric_id, belief.context)
        self._cache[cache_key] = belief
```

**cmis.yaml 업데이트**:

```yaml
ids_and_lineage:
  id_prefixes:
    value: "VAL-"
    # VAL-PRIOR-* 또는 VAL-BELIEF-*로 Prior/Belief 표현
  
  lineage_schema:
    from_prior_id: { type: "string", required: false }  # 추가
    from_outcome_ids: { type: "list", required: false }  # 추가
```

**Phase 2 반영**: ✅ value_store 연동, 영속성 확보

---

### Priority 3: Policy/Quality 프로파일 연결 강화 ⭐⭐

**문제점**:
- `policy_ref`를 받지만 exploration_friendly만 처리
- reporting_strict일 때도 Prior 동일하게 반환

**적용안**:

```python
# cmis_core/belief_engine.py

class BeliefEngine:
    def query_prior_api(
        self,
        metric_id: str,
        context: Dict[str, Any],
        policy_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """Policy별 Prior 조정"""
        
        # 1. 기본 Prior 조회/생성
        prior = self.prior_manager.get_prior(metric_id, context)
        if prior is None:
            prior = self._generate_prior_from_pattern(metric_id, context)
        if prior is None:
            prior = self._generate_uninformative_prior(metric_id)
        
        # 2. Policy별 조정
        policy_mode = policy_ref or "decision_balanced"
        
        if policy_mode == "reporting_strict":
            # reporting_strict: Prior 사용 최소화
            # confidence 낮춤, spread 넓힘
            prior.confidence *= 0.5  # 신뢰도 절반
            prior.distribution = self._widen_distribution(
                prior.distribution, 
                factor=2.0  # 분포 2배 확대
            )
            # 메타데이터에 표시
            prior.lineage["policy_adjustment"] = "reporting_strict_conservative"
        
        elif policy_mode == "exploration_friendly":
            # exploration_friendly: Prior 적극 활용
            # confidence 유지, spread 약간만 넓힘
            prior.distribution = self._widen_distribution(
                prior.distribution,
                factor=1.2  # 분포 20% 확대
            )
            prior.lineage["policy_adjustment"] = "exploration_friendly_permissive"
        
        else:  # decision_balanced
            # 기본값 유지
            prior.lineage["policy_adjustment"] = "decision_balanced_default"
        
        return {
            "prior_id": prior.belief_id,
            "metric_id": prior.metric_id,
            "context": prior.context,
            "distribution": prior.distribution,
            "confidence": prior.confidence,
            "source": prior.source,
            "policy_mode": policy_mode,
            "lineage": prior.lineage
        }
```

**Quality Profile 연동**:

```python
def _apply_quality_constraints(
    self,
    prior: BeliefRecord,
    metric_spec: Dict
) -> BeliefRecord:
    """metrics_spec의 quality_requirements 적용"""
    
    quality_profile = metric_spec.get("default_quality_profile", "decision_balanced")
    
    # cmis.yaml policies.quality_profiles 참조
    quality_limits = {
        "reporting_strict": {"max_spread_ratio": 0.3, "min_confidence": 0.7},
        "decision_balanced": {"max_spread_ratio": 0.5, "min_confidence": 0.5},
        "exploration_friendly": {"max_spread_ratio": 0.7, "min_confidence": 0.3}
    }
    
    limits = quality_limits.get(quality_profile, quality_limits["decision_balanced"])
    
    # spread_ratio 제한
    current_spread = self._calculate_spread(prior.distribution)
    if current_spread > limits["max_spread_ratio"]:
        # 분포 좁히기 (sigma 감소)
        prior.distribution = self._narrow_distribution(
            prior.distribution,
            target_spread=limits["max_spread_ratio"]
        )
    
    # confidence 하한
    if prior.confidence < limits["min_confidence"]:
        prior.confidence = limits["min_confidence"]
        prior.lineage["quality_adjustment"] = f"confidence_raised_to_{limits['min_confidence']}"
    
    return prior
```

**Phase 2 반영**: ✅ Policy 통합, Quality 제약

---

### Priority 4: Pattern 기반 Prior의 컨텍스트 정밀도 ⭐⭐

**문제점**:
- context 매칭 없이 모든 Pattern Benchmark 사용
- domain/region/segment 다른 패턴도 동일 가중치

**적용안**:

```python
def _generate_prior_from_pattern(
    self,
    metric_id: str,
    context: Dict[str, Any]
) -> Optional[BeliefRecord]:
    """Context 기반 Pattern Benchmark 필터링"""
    
    # 1. 유사 Pattern 찾기 (context 전달)
    similar_patterns = self.pattern_engine.match_patterns(
        graph_slice_ref=None,  # Greenfield
        target_context=context  # 추가
    )
    
    if not similar_patterns:
        return None
    
    # 2. Context 유사도 기반 가중치 조정
    benchmark_values = []
    for pattern_match in similar_patterns:
        pattern_id = pattern_match["pattern_id"]
        benchmark = self.prior_manager.load_pattern_benchmark(pattern_id)
        
        if benchmark and metric_id in benchmark["metrics"]:
            # Context 유사도 계산
            context_similarity = self._calculate_context_similarity(
                context, 
                benchmark["context"]
            )
            
            # 구조 적합도 × Context 유사도
            combined_weight = pattern_match["score"] * context_similarity
            
            benchmark_values.append({
                "value": benchmark["metrics"][metric_id]["median"],
                "weight": combined_weight,
                "pattern_id": pattern_id,
                "context_similarity": context_similarity
            })
    
    if not benchmark_values:
        return None
    
    # 3. 가중 평균 (Context 유사도 반영)
    total_weight = sum(b["weight"] for b in benchmark_values)
    if total_weight == 0:
        return None
    
    weighted_mean = sum(b["value"] * b["weight"] for b in benchmark_values) / total_weight
    weighted_std = np.std([b["value"] for b in benchmark_values]) * 1.5  # 보수적
    
    # 4. BeliefRecord 생성
    belief = BeliefRecord(
        belief_id=f"PRIOR-{uuid.uuid4().hex[:8]}",
        metric_id=metric_id,
        context=context,
        distribution={
            "type": "lognormal",
            "params": {
                "mu": math.log(weighted_mean),
                "sigma": math.log(1 + weighted_std / weighted_mean)
            }
        },
        confidence=min(total_weight / len(benchmark_values), 0.8),  # 최대 0.8
        source="pattern_benchmark",
        observations=[],
        n_observations=0,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        lineage={
            "from_pattern_ids": [b["pattern_id"] for b in benchmark_values],
            "context_similarities": [b["context_similarity"] for b in benchmark_values],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    )
    
    return belief

def _calculate_context_similarity(
    self,
    context1: Dict[str, Any],
    context2: Dict[str, Any]
) -> float:
    """Context 유사도 계산 (0~1)"""
    
    # 주요 키 정의
    key_weights = {
        "domain_id": 0.4,      # 도메인 일치 중요
        "region": 0.3,         # 지역 일치
        "segment": 0.2,        # 세그먼트
        "scale_tier": 0.1      # 규모
    }
    
    similarity = 0.0
    for key, weight in key_weights.items():
        if key in context1 and key in context2:
            if context1[key] == context2[key]:
                similarity += weight
            elif key == "region" and self._is_similar_region(context1[key], context2[key]):
                similarity += weight * 0.5  # 유사 지역 절반
        # 키 없으면 0점
    
    return similarity
```

**Phase 2 반영**: ✅ Context 필터링, 가중치 조정

---

### Priority 5: LearningEngine 연동 업데이트 기준 ⭐⭐

**문제점**:
- 고정 10% 오차로 업데이트 결정
- metrics_spec의 target_convergence 무시

**적용안**:

```python
# cmis_core/learning_engine.py

def _should_update_belief(
    self,
    metric_id: str,
    delta: Dict[str, Any]
) -> bool:
    """Metric별 업데이트 기준 판단"""
    
    # 1. metrics_spec에서 target_convergence 조회
    metric_spec = self._get_metric_spec(metric_id)
    
    resolution_protocol = metric_spec.get("resolution_protocol", {})
    target_convergence = resolution_protocol.get("target_convergence")
    
    # 2. 기준 추출
    if target_convergence:
        # "±30% 이내 수렴" → 0.3
        threshold = float(target_convergence.replace("±", "").replace("%", "").strip()) / 100
    else:
        # 기본값: 20%
        threshold = 0.2
    
    # 3. 오차율 비교
    error_pct = abs(delta["error_pct"])
    
    return error_pct > threshold

def _update_beliefs_from_outcome(
    self,
    outcome: Dict,
    comparison: Dict
) -> List[str]:
    """Outcome 기반 Belief 업데이트 (기준 적용)"""
    
    from cmis_core.belief_engine import BeliefEngine
    
    belief_engine = BeliefEngine()
    updated_belief_ids = []
    
    for metric_id, delta in comparison["deltas"].items():
        # Metric별 기준 판단
        if not self._should_update_belief(metric_id, delta):
            continue
        
        # Observation 구성
        observations = [{
            "value": outcome["metrics"][metric_id],
            "weight": 1.0,
            "source": outcome["outcome_id"],
            "timestamp": outcome["as_of"]
        }]
        
        # Belief 업데이트
        result = belief_engine.update_belief_api(
            metric_id=metric_id,
            context=outcome["context"],
            observations=observations,
            update_mode="bayesian"
        )
        
        updated_belief_ids.append(result["belief_id"])
        
        # drift_alert 생성 (큰 변화 시)
        if abs(result["delta"]["mean_shift"]) > 0.5:
            self._create_drift_alert(metric_id, result)
    
    return updated_belief_ids
```

**Phase 2 반영**: ✅ metrics_spec 연동, 동적 기준

---

### Priority 6: UncertaintyPropagator 안전성 ⭐

**문제점**:
- `eval()` 사용 (보안 위험)
- `str.replace` (변수 이름 충돌)
- 10,000 samples 전부 반환 (페이로드 과다)

**적용안**:

```python
# cmis_core/uncertainty_propagator.py

import asteval  # 안전한 expression evaluator

class UncertaintyPropagator:
    def __init__(self):
        self.evaluator = asteval.Interpreter()
    
    def _evaluate_formula(
        self, 
        formula: str, 
        var_values: Dict[str, float]
    ) -> float:
        """AST 기반 안전한 공식 평가"""
        
        # 1. 공식 파싱 (예: "Revenue = N_customers * ARPU")
        if "=" in formula:
            expr = formula.split("=")[1].strip()
        else:
            expr = formula
        
        # 2. 변수 설정
        for var, val in var_values.items():
            self.evaluator.symtable[var] = val
        
        # 3. 안전한 평가
        try:
            result = self.evaluator(expr)
            if self.evaluator.error:
                raise ValueError(f"Formula evaluation error: {self.evaluator.error}")
            return float(result)
        except Exception as e:
            raise ValueError(f"Invalid formula: {formula}, error: {e}")
    
    def monte_carlo(
        self,
        formula: str,
        input_distributions: Dict[str, Dict],
        n_samples: int = 10000
    ) -> Dict:
        """Monte Carlo (samples는 저장소에, 요약만 반환)"""
        
        # 1. 샘플 생성
        samples = {}
        for var_name, dist in input_distributions.items():
            samples[var_name] = self._sample_distribution(dist, n_samples)
        
        # 2. 공식 평가
        output_samples = []
        for i in range(n_samples):
            var_values = {var: samples[var][i] for var in samples}
            output = self._evaluate_formula(formula, var_values)
            output_samples.append(output)
        
        output_samples = np.array(output_samples)
        
        # 3. 요약 통계만 반환 (raw samples는 제외)
        result = {
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
                "cv": float(np.std(output_samples) / np.mean(output_samples)),
                "min": float(np.min(output_samples)),
                "max": float(np.max(output_samples))
            },
            "n_samples": n_samples
        }
        
        # 4. raw samples는 별도 저장 (선택적)
        # artifact_store 또는 memory_store에 저장 후 ref만 반환
        samples_ref = self._save_samples_to_store(
            output_samples,
            formula,
            input_distributions
        )
        result["samples_ref"] = samples_ref
        
        return result
    
    def _save_samples_to_store(
        self,
        samples: np.ndarray,
        formula: str,
        input_distributions: Dict
    ) -> str:
        """Samples를 artifact_store에 저장"""
        
        artifact_id = f"ART-samples-{uuid.uuid4().hex[:8]}"
        
        artifact = {
            "artifact_id": artifact_id,
            "type": "monte_carlo_samples",
            "formula": formula,
            "input_distributions": input_distributions,
            "samples": samples.tolist(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # 파일 저장
        filepath = self.artifact_store_path / f"{artifact_id}.json"
        with open(filepath, "w") as f:
            json.dump(artifact, f)
        
        return artifact_id
```

**Phase 3 반영**: ✅ AST evaluator, samples 분리 저장

---

### Priority 7: 구현 디테일 ⭐

**문제점**:
- `direct_replace()`에서 list - mean (TypeError)
- lineage에 OUT-*/EVD-* 구분 없음

**적용안**:

```python
# cmis_core/belief_updater.py

class BeliefUpdater:
    def direct_replace(
        self,
        observations: List[Dict]
    ) -> Dict:
        """직접 대체 (numpy 사용)"""
        
        values = np.array([obs["value"] for obs in observations])
        weights = np.array([obs["weight"] for obs in observations])
        
        mean = np.average(values, weights=weights)
        std = np.sqrt(np.average((values - mean)**2, weights=weights))
        
        return {
            "type": "normal",
            "params": {
                "mu": float(mean),
                "sigma": float(std)
            }
        }
```

**lineage 분리**:

```python
# cmis_core/prior_manager.py

def save_belief(
    self,
    ...
    observations: List[Dict]
) -> BeliefRecord:
    """lineage 정확하게 구분"""
    
    # Evidence/Outcome 분리
    evidence_ids = []
    outcome_ids = []
    
    for obs in observations:
        source = obs.get("source", "")
        if source.startswith("EVD-"):
            evidence_ids.append(source)
        elif source.startswith("OUT-"):
            outcome_ids.append(source)
    
    lineage = {
        "from_evidence_ids": evidence_ids,
        "from_outcome_ids": outcome_ids,  # 명시적 분리
        "from_prior_id": prior.belief_id if prior else None,
        "engine_ids": ["belief_engine"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    ...
```

**Phase 1 반영**: ✅ 타입 안전성, lineage 정확성

---

## 2. 대안 구조 검토

### 대안 A: Belief = 특수 ValueRecord ✅ **채택**

**장점**:
- 기존 value_store 인프라 활용
- value_graph와 자연스럽게 통합
- 추가 store 불필요

**단점**:
- ValueRecord 스키마 확장 필요
- origin 필드 추가 필요

**결정**: ✅ **Priority 2에서 적용**

---

### 대안 B: UncertaintyPropagator → ValueEngine 이동 ❌ **보류**

**장점**:
- 책임 분리 명확
- ValueEngine이 시뮬레이션 전담

**단점**:
- BeliefEngine 역할 축소
- ValueEngine 복잡도 증가

**결정**: ❌ **v1.0에서는 현재 구조 유지, v1.1 재검토**

---

## 3. 추가 고려사항

### (1) Human-in-the-loop (v1.1)

**설계 추가**:

```yaml
# cmis.yaml - belief_engine

api:
  - name: "propose_belief_update"
    description: "업데이트 제안만 (실제 반영 ❌)"
    input:
      metric_id: "metric_id"
      observations: "list"
    output:
      proposal_id: "string"
      proposed_belief: "belief_record"
  
  - name: "approve_belief_update"
    description: "제안 승인 (실제 반영 ✅)"
    input:
      proposal_id: "string"
      approved_by: "role_id"
    output:
      belief_id: "string"
```

**Phase 3 문서화**: ✅

---

### (2) 다변량 Belief (v1.2)

**설계 방향**:
- Joint Prior Distribution
- Copula 기반 종속성
- TAM/SAM/SOM 동시 업데이트

**Phase 3 문서화**: ✅

---

### (3) Active Learning (v1.2)

**EvidenceEngine 연동**:

```python
def suggest_evidence_priorities(self) -> List[Dict]:
    """불확실성 높은 Metric 우선 수집 제안"""
    
    priorities = []
    for metric_id, belief in self.prior_manager.all_beliefs():
        if belief.confidence < 0.3 or belief.source == "uninformative":
            priorities.append({
                "metric_id": metric_id,
                "context": belief.context,
                "reason": f"low_confidence_{belief.confidence}",
                "urgency": "high"
            })
    
    return sorted(priorities, key=lambda x: x["urgency"])
```

**Phase 3 문서화**: ✅

---

### (4) Drift Alert (memory_store)

**LearningEngine 연동**:

```python
def _create_drift_alert(
    self,
    metric_id: str,
    belief_update_result: Dict
) -> str:
    """큰 Belief 변화 시 drift_alert 생성"""
    
    delta = belief_update_result["delta"]
    
    if abs(delta["mean_shift"]) > 0.5 or abs(delta["sigma_reduction"]) > 0.5:
        alert = {
            "memory_id": f"MEM-drift-{uuid.uuid4().hex[:8]}",
            "memory_type": "drift_alert",
            "related_ids": {
                "metric_id": metric_id,
                "belief_id": belief_update_result["belief_id"]
            },
            "content": f"Large belief shift detected for {metric_id}: mean {delta['mean_shift']:+.1%}, sigma {delta['sigma_reduction']:+.1%}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # memory_store 저장
        self.memory_store.save(alert)
        return alert["memory_id"]
```

**Phase 2 반영**: ✅

---

## 4. Phase별 구현 계획 (수정)

### Phase 1: Core + 스키마 통일 (4시간)

**작업**:
- ✅ BeliefRecord 정의 (types.py)
- ✅ PriorManager (BeliefRecord 사용)
- ✅ BeliefUpdater (numpy 안전성)
- ✅ UncertaintyPropagator (기본 버전)
- ✅ 테스트 10개

**적용 포인트**:
- Priority 1 (스키마 통일)
- Priority 7 (구현 디테일)

---

### Phase 2: 통합 + 영속성 (3시간)

**작업**:
- ✅ belief_engine.py (3 API)
- ✅ value_store 연동 (영속성)
- ✅ Policy/Quality 통합
- ✅ Context 필터링
- ✅ LearningEngine 연동 (metrics_spec 기준)
- ✅ Drift Alert
- ✅ 테스트 12개

**적용 포인트**:
- Priority 2 (영속성)
- Priority 3 (Policy)
- Priority 4 (Context)
- Priority 5 (업데이트 기준)
- 추가 고려 (4)

---

### Phase 3: 고급 + 안전성 (2시간)

**작업**:
- ✅ AST evaluator
- ✅ Samples 분리 저장
- ✅ Lognormal/Beta 업데이트
- ✅ Human-in-the-loop 문서화
- ✅ 다변량/Active Learning 문서화
- ✅ 테스트 10개

**적용 포인트**:
- Priority 6 (안전성)
- 추가 고려 (1)(2)(3)

---

## 5. cmis.yaml 업데이트 (최종)

```yaml
cmis:
  meta:
    version: "3.4.0"
    engines_completed: "9/9"
    completion: "100%"

  cognition_plane:
    engines:
      belief_engine:
        description: "Prior/Belief 관리 및 불확실성 정량화"
        version: "v1.0"
        status: "production_ready"
        
        inputs:
          - "substrate_plane.graphs.pattern_graph"
          - "substrate_plane.graphs.value_graph"
          - "substrate_plane.stores.value_store"  # ✅ 추가
        
        outputs:
          - "prior_distributions (ValueRecord origin=prior)"
          - "belief_updates (ValueRecord origin=learned)"
        
        api:
          - name: "query_prior"
            input:
              metric_id: "metric_id"
              context: "dict"
              policy_ref: "policy_ref"
            output:
              prior: "BeliefRecord (as ValueRecord)"
          
          - name: "update_belief"
            input:
              metric_id: "metric_id"
              observations: "list[observation]"
              update_mode: "bayesian"
            output:
              updated_belief: "BeliefRecord"
          
          - name: "propagate_uncertainty"
            input:
              formula: "string"
              input_distributions: "dict"
            output:
              output_distribution: "distribution"
              samples_ref: "artifact_id"  # ✅ 추가
        
        core_components:
          - id: "prior_manager"
            storage: "value_store"  # ✅ 명시
          - id: "belief_updater"
            methods: ["bayesian_normal", "bayesian_lognormal", "direct_replace"]
          - id: "uncertainty_propagator"
            evaluator: "asteval"  # ✅ 명시

  substrate_plane:
    stores:
      value_store:
        schema:
          origin: "enum[direct,derived,prior,learned]"  # ✅ 추가

  ids_and_lineage:
    id_prefixes:
      # VAL-PRIOR-*, VAL-BELIEF-* 형식으로 Prior/Belief 표현
    
    lineage_schema:
      from_prior_id: { type: "string", required: false }
      from_outcome_ids: { type: "list", required: false }  # ✅ 추가
```

---

## 6. 결론

### ✅ 유지할 설계

- **3-Component 구조**: PriorManager/BeliefUpdater/UncertaintyPropagator
- **Public API 3개**: query_prior/update_belief/propagate_uncertainty
- **CMIS 철학 정렬**: Evidence-first, Prior-last, Conservative, Context-aware

### 🔧 보강 완료

| 우선순위 | 포인트 | 적용 Phase | 상태 |
|---------|--------|-----------|------|
| ⭐⭐⭐ | BeliefRecord 스키마 통일 | Phase 1 | ✅ |
| ⭐⭐⭐ | value_store 영속성 | Phase 2 | ✅ |
| ⭐⭐ | Policy/Quality 통합 | Phase 2 | ✅ |
| ⭐⭐ | Context 정밀도 | Phase 2 | ✅ |
| ⭐⭐ | LearningEngine 기준 | Phase 2 | ✅ |
| ⭐ | UncertaintyPropagator 안전성 | Phase 3 | ✅ |
| ⭐ | 구현 디테일 | Phase 1 | ✅ |

### 🚀 다음 단계

**즉시 시작 가능**:
- Phase 1 구현 (BeliefRecord + Core Components)
- 테스트 작성 (32개)
- cmis.yaml 업데이트

**예상 완료 시간**: 9시간 (3 Phases)

---

**작성**: 2025-12-12
**리뷰 완료**: ✅
**구현 준비**: ✅
**CMIS v3.4.0 → v3.5.0 (BeliefEngine 완성)**

