# LearningEngine 설계 (Enhanced)

**작성일**: 2025-12-11
**버전**: v1.1 (피드백 반영)
**기반**: LearningEngine_Design.md + 피드백
**상태**: 설계 완료

---

## Executive Summary

이 문서는 LearningEngine 설계를 cmis.yaml과 완전히 정렬한 Enhanced 버전입니다.

**주요 개선**:
1. **API 출력 형식** - updated_entities dict 반환
2. **Metric별 허용 오차** - metrics_spec/quality_profiles 연동
3. **Strategy-unlinked Outcome** - ValueEngine 비교 경로
4. **Context별 Benchmark** - domain/segment 분리
5. **ProjectContext 버전 관리** - version/lineage 추가
6. **4개 Sub-learner** - Pattern/Metric/Context/Belief 분리
7. **memory_store 통합** - drift_alert, pattern_note

---

## 1. LearningEngine 아키텍처 (Enhanced)

### 1.1 4-Learner 구조

```
┌──────────────────────────────────────────────────────────┐
│                   LearningEngine                          │
│  update_from_outcomes_api() / update_project_context()   │
└──────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┬────────────┐
        ▼                 ▼                 ▼            ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Outcome    │  │   Pattern    │  │   Metric     │  │   Context    │
│  Comparator  │  │   Learner    │  │   Learner    │  │   Learner    │
│              │  │              │  │              │  │              │
│ 예측 vs 실제 │  │ Benchmark    │  │ Formula/     │  │ Baseline     │
│ Delta 계산   │  │ 업데이트     │  │ Belief 보정  │  │ 버전 업데이트│
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

**분리 이유**:
- 책임 명확화
- 독립 테스트
- 확장성

---

## 2. Public API (cmis.yaml 완전 대응)

### 2.1 update_from_outcomes_api() (Enhanced)

**cmis.yaml 정의**:
```yaml
learning_engine:
  api:
    - name: update_from_outcomes
      input:
        outcome_ids: "list[outcome_id]"
      output:
        updated_entities: "dict"
```

**구현** (Enhanced):
```python
def update_from_outcomes_api(
    self,
    outcome_ids: List[str]
) -> Dict[str, Any]:
    """
    Public API (cmis.yaml 대응)
    
    Returns:
        {
            "summary_ref": "LEARN-xxxx",
            "updated_entities": {
                "pattern_ids": ["PAT-subscription_model"],
                "metric_ids": ["MET-Revenue", "MET-Churn_rate"],
                "project_context_ids": ["PRJ-001"],
                "belief_updates": 5
            },
            "learning_quality": {
                "total_outcomes": 10,
                "valid_comparisons": 8,
                "accuracy_avg": 0.85
            }
        }
    """
    learning_results = []
    updated_pattern_ids = set()
    updated_metric_ids = set()
    updated_context_ids = set()
    
    for outcome_id in outcome_ids:
        outcome = self._load_outcome(outcome_id)
        
        if not outcome:
            continue
        
        # Strategy-linked vs unlinked 분기
        if outcome.related_strategy_id:
            # 경로 1: Strategy 기반 학습
            result = self._learn_from_strategy_outcome(outcome)
        else:
            # 경로 2: Direct metric calibration
            result = self._learn_from_direct_outcome(outcome)
        
        if result:
            learning_results.append(result)
            
            # 업데이트된 엔티티 추적
            for update in result.updates.get("pattern_benchmarks", []):
                updated_pattern_ids.add(update["pattern_id"])
            
            for update in result.updates.get("metric_formulas", []):
                updated_metric_ids.add(update["metric_id"])
    
    # Summary 저장
    summary_ref = self._save_learning_summary(learning_results)
    
    # cmis.yaml 형식 반환
    return {
        "summary_ref": summary_ref,
        "updated_entities": {
            "pattern_ids": list(updated_pattern_ids),
            "metric_ids": list(updated_metric_ids),
            "project_context_ids": list(updated_context_ids),
            "belief_updates": sum(
                len(r.updates.get("confidence_adjustments", []))
                for r in learning_results
            )
        },
        "learning_quality": {
            "total_outcomes": len(outcome_ids),
            "valid_comparisons": len(learning_results),
            "accuracy_avg": self._calculate_avg_accuracy(learning_results)
        }
    }
```

---

## 3. OutcomeComparator (Enhanced)

### 3.1 Metric별 허용 오차

**Before**: 모든 Metric ±30% 고정

**After**: metrics_spec + quality_profiles 연동

```python
class OutcomeComparator:
    def __init__(self, config: CMISConfig):
        self.config = config
        
        # Metric별 허용 오차 (metrics_spec)
        self.metric_tolerances = self._load_metric_tolerances()
        
        # Policy별 threshold (quality_profiles)
        self.policy_thresholds = {
            "reporting_strict": 0.2,      # ±20%
            "decision_balanced": 0.3,     # ±30%
            "exploration_friendly": 0.5   # ±50%
        }
    
    def _load_metric_tolerances(self) -> Dict[str, float]:
        """
        metrics_spec에서 target_convergence 로딩
        
        Returns:
            metric_id → tolerance
        """
        tolerances = {}
        
        # metrics_spec 조회
        metrics_spec = self.config.get_metrics_spec()
        
        for metric_id, spec in metrics_spec.items():
            protocol = spec.get("resolution_protocol", {})
            convergence = protocol.get("target_convergence")
            
            if convergence:
                # "±30% 이내" → 0.3
                if "%" in str(convergence):
                    value = float(convergence.replace("%", "").replace("±", "")) / 100
                    tolerances[metric_id] = value
                else:
                    tolerances[metric_id] = 0.3  # 기본값
            else:
                tolerances[metric_id] = 0.3
        
        return tolerances
    
    def is_within_bounds(
        self,
        metric_id: str,
        delta_pct: float,
        policy_mode: str = "decision_balanced"
    ) -> bool:
        """
        오차 범위 내 판단 (Metric + Policy 고려)
        
        Args:
            metric_id: Metric ID
            delta_pct: Delta 백분율
            policy_mode: Policy 모드
        
        Returns:
            범위 내 여부
        """
        # Metric별 tolerance
        metric_tolerance = self.metric_tolerances.get(metric_id, 0.3)
        
        # Policy별 threshold
        policy_threshold = self.policy_thresholds.get(policy_mode, 0.3)
        
        # 둘 중 더 엄격한 것 사용
        tolerance = min(metric_tolerance, policy_threshold)
        
        return abs(delta_pct) <= tolerance
```

---

## 4. Strategy-unlinked Outcome 처리

### 4.1 두 가지 학습 경로

**경로 1: Strategy-linked** (기존):
```python
def _learn_from_strategy_outcome(self, outcome: Outcome) -> LearningResult:
    """
    Strategy 기반 학습
    
    Strategy.expected_outcomes vs Outcome.metrics 비교
    """
    strategy = self._load_strategy(outcome.related_strategy_id)
    
    comparisons = self.outcome_comparator.compare_outcome_vs_prediction(
        outcome,
        strategy
    )
    
    updates = self._learn_from_comparisons(comparisons, strategy, outcome)
    
    return LearningResult(...)
```

**경로 2: Strategy-unlinked** (신규):
```python
def _learn_from_direct_outcome(self, outcome: Outcome) -> LearningResult:
    """
    Direct metric calibration
    
    ValueEngine 과거 예측 또는 Pattern Benchmark와 비교
    """
    comparisons = []
    
    for metric_id, actual_value in outcome.metrics.items():
        # ValueEngine에서 과거 예측 조회
        past_prediction = self._get_past_value_record(
            metric_id,
            outcome.context,
            as_of=outcome.as_of
        )
        
        if past_prediction:
            # 과거 예측 vs 실제
            delta = actual_value - past_prediction.point_estimate
            delta_pct = delta / past_prediction.point_estimate if past_prediction.point_estimate > 0 else 0
            
            comparisons.append({
                "metric_id": metric_id,
                "predicted": past_prediction.point_estimate,
                "actual": actual_value,
                "delta_pct": delta_pct,
                "prediction_source": "value_engine"
            })
        else:
            # Pattern Benchmark와 비교 (일반적 기대값)
            benchmark = self._get_market_benchmark(metric_id, outcome.context)
            
            if benchmark:
                expected = benchmark.get("typical", [0])[0] if isinstance(benchmark.get("typical"), list) else benchmark.get("typical", 0)
                
                delta_pct = (actual_value - expected) / expected if expected > 0 else 0
                
                comparisons.append({
                    "metric_id": metric_id,
                    "predicted": expected,
                    "actual": actual_value,
                    "delta_pct": delta_pct,
                    "prediction_source": "pattern_benchmark"
                })
    
    # 학습 (Pattern Benchmark / Metric Prior 업데이트)
    updates = self._learn_from_direct_calibration(comparisons, outcome)
    
    return LearningResult(
        learning_id=f"LEARN-direct-{uuid.uuid4().hex[:8]}",
        outcome_id=outcome.outcome_id,
        comparisons=comparisons,
        updates=updates
    )
```

---

## 5. PatternLearner (Context별)

### 5.1 Context별 Benchmark

**Before**: Global Benchmark만

**After**: Context별 분리

```python
class PatternLearner:
    """Pattern 학습기 (Context별)"""
    
    def update_pattern_benchmark(
        self,
        pattern_id: str,
        metric_id: str,
        actual_value: float,
        context: Dict[str, Any],  # domain_id, region, segment
        current_benchmark: Dict[str, Any],
        sample_size: int = 1
    ) -> Dict[str, Any]:
        """
        Pattern Benchmark 업데이트 (Context별)
        
        Context key: (domain_id, region, segment)
        """
        # Context key 생성
        context_key = (
            context.get("domain_id", "global"),
            context.get("region", "global"),
            context.get("segment", "all")
        )
        
        # Context별 Benchmark 관리
        if "by_context" not in current_benchmark:
            current_benchmark["by_context"] = {}
        
        context_bench = current_benchmark["by_context"].get(
            str(context_key),
            current_benchmark.copy()  # Global을 초기값으로
        )
        
        # Bayesian 업데이트
        alpha = 0.8 if sample_size == 1 else 0.9  # 보수적
        
        old_typical = context_bench.get("typical", [])
        old_avg = sum(old_typical) / len(old_typical) if isinstance(old_typical, list) else old_typical
        
        new_avg = old_avg * alpha + actual_value * (1 - alpha)
        
        # 업데이트
        updated = {
            "min": min(context_bench.get("min", actual_value), actual_value * 0.9),
            "max": max(context_bench.get("max", actual_value), actual_value * 1.1),
            "typical": [new_avg * 0.9, new_avg * 1.1],
            "source": "learned",
            "sample_size": context_bench.get("sample_size", 0) + sample_size,
            "last_updated": datetime.now().isoformat(),
            "context": context_key
        }
        
        # Context별 저장
        current_benchmark["by_context"][str(context_key)] = updated
        
        # Global도 함께 업데이트 (평균)
        current_benchmark["typical"] = [new_avg * 0.9, new_avg * 1.1]
        
        return current_benchmark
```

---

## 6. ContextLearner (버전 관리)

### 6.1 ProjectContext 버전 업데이트

**project_context_store 스키마**:
```yaml
project_context_store:
  version: int
  previous_version_id: Optional[str]
  lineage: Dict
```

**구현**:
```python
class ContextLearner:
    """ProjectContext 학습기 (버전 관리)"""
    
    def update_baseline_state(
        self,
        project_context: ProjectContext,
        outcome: Outcome
    ) -> ProjectContext:
        """
        baseline_state 업데이트 (버전 관리)
        """
        # 새 baseline_state
        updated_baseline = dict(project_context.baseline_state)
        
        for metric_id, value in outcome.metrics.items():
            # Metric → baseline 필드 매핑
            if metric_id == "MET-Revenue":
                # quantity_ref 형식 (Phase 2)
                updated_baseline["current_revenue"] = {
                    "amount": value,
                    "currency": "KRW",
                    "per": "year"
                }
            elif metric_id == "MET-N_customers":
                updated_baseline["current_customers"] = value
            # ... 기타 매핑
        
        # as_of 업데이트
        updated_baseline["as_of"] = outcome.as_of
        
        # 새 버전 생성
        new_version_id = f"{project_context.project_context_id}-v{self._next_version()}"
        
        updated_context = ProjectContext(
            project_context_id=new_version_id,
            version=project_context.version + 1,  # 버전 증가
            previous_version_id=project_context.project_context_id,
            scope=project_context.scope,
            assets_profile=project_context.assets_profile,
            baseline_state=updated_baseline,
            constraints_profile=project_context.constraints_profile,
            preference_profile=project_context.preference_profile,
            focal_actor_id=project_context.focal_actor_id,
            lineage={
                **project_context.lineage,
                "from_outcome_ids": project_context.lineage.get("from_outcome_ids", []) + [outcome.outcome_id],
                "updated_at": datetime.now().isoformat(),
                "updated_by": "learning_engine"
            }
        )
        
        return updated_context
```

---

## 7. MetricLearner (신규)

### 7.1 Metric Formula/Belief 보정

```python
class MetricLearner:
    """Metric 학습기
    
    역할:
    - Metric 공식 보정
    - Prior 파라미터 조정
    - Quality profile 업데이트
    """
    
    def __init__(self, value_engine: ValueEngine):
        self.value_engine = value_engine
    
    def adjust_metric_belief(
        self,
        metric_id: str,
        predicted: float,
        actual: float,
        delta_pct: float
    ) -> Dict[str, Any]:
        """
        Metric Belief 조정
        
        ValueEngine의 prior_estimation에 피드백
        
        Returns:
            Belief 업데이트
        """
        # 일관된 방향 오차 (bias)
        if abs(delta_pct) > 0.3:
            # Prior 파라미터 조정
            adjustment = {
                "metric_id": metric_id,
                "adjustment_type": "prior_bias",
                "bias_direction": "over" if delta_pct < 0 else "under",
                "bias_magnitude": abs(delta_pct),
                "recommended_action": "adjust_prior_mean",
                "new_prior_factor": 1 + delta_pct  # 보정 계수
            }
            
            return adjustment
        
        return {}
    
    def update_metric_quality(
        self,
        metric_id: str,
        accuracy: float
    ) -> Dict[str, Any]:
        """
        Metric Quality 업데이트
        
        accuracy 기반으로 confidence 조정
        """
        # accuracy → confidence 변환
        new_confidence = min(accuracy, 0.95)  # 최대 0.95
        
        return {
            "metric_id": metric_id,
            "quality_update": {
                "confidence": new_confidence,
                "source": "outcome_validation",
                "updated_at": datetime.now().isoformat()
            }
        }
```

---

## 8. Belief ↔ ValueEngine 연결

### 8.1 인터페이스 명확화

**LearningEngine → ValueEngine 피드백**:

**Option A: Belief Update Request**:
```python
def _update_value_engine_beliefs(
    self,
    metric_updates: List[Dict]
):
    """
    ValueEngine에 Belief 업데이트 요청
    
    Phase 2: ValueEngine API 확장 필요
    """
    for update in metric_updates:
        metric_id = update["metric_id"]
        new_prior_factor = update.get("new_prior_factor", 1.0)
        
        # ValueEngine에 요청
        # self.value_engine.update_prior_belief(
        #     metric_id=metric_id,
        #     adjustment_factor=new_prior_factor,
        #     reason="learning_from_outcome"
        # )
        
        # Phase 1: 로깅만
        print(f"[Learning] {metric_id} Prior 조정: {new_prior_factor}")
```

**Option B: value_graph 직접 수정**:
```python
def _update_value_graph_directly(
    self,
    metric_id: str,
    new_prior_params: Dict
):
    """
    value_graph의 metric 노드 직접 업데이트
    
    Phase 2: value_graph 접근 필요
    """
    # value_graph.update_metric_node(
    #     metric_id,
    #     prior_params=new_prior_params
    # )
```

**설계 방향**: Option A (ValueEngine API 경유) 권장

---

## 9. memory_store 통합

### 9.1 LearningResult → memory_store

```python
def _save_learning_summary(
    self,
    learning_results: List[LearningResult]
) -> str:
    """
    Learning summary를 memory_store에 저장
    
    memory_type: "drift_alert" | "pattern_note"
    """
    summary_ref = f"LEARN-{uuid.uuid4().hex[:8]}"
    
    # 1. LearningResult를 memory_store에
    for result in learning_results:
        memory_id = f"MEM-{result.learning_id}"
        
        # Drift 감지
        has_drift = any(
            abs(c["delta_pct"]) > 0.5
            for c in result.comparisons
        )
        
        memory_type = "drift_alert" if has_drift else "pattern_note"
        
        # memory_store 저장 (Phase 2)
        # self.memory_store.save(
        #     memory_id=memory_id,
        #     memory_type=memory_type,
        #     content_ref=result,
        #     related_ids={
        #         "outcome_id": result.outcome_id,
        #         "pattern_ids": [u["pattern_id"] for u in result.updates.get("pattern_benchmarks", [])]
        #     }
        # )
    
    return summary_ref
```

---

## 10. 학습 정책 및 안전장치

### 10.1 최소 Sample Size

```python
class LearningPolicy:
    """학습 정책
    
    언제, 얼마나 강하게 학습할지
    """
    
    def __init__(self):
        self.min_sample_size = {
            "pattern_benchmark": 3,  # 최소 3개 샘플
            "metric_formula": 5,      # 최소 5개 샘플
            "belief_adjustment": 10   # 최소 10개 샘플
        }
        
        self.learning_rate = {
            "pattern_benchmark": 0.2,  # alpha = 0.8 (보수적)
            "metric_formula": 0.3,
            "belief_adjustment": 0.1   # 매우 보수적
        }
    
    def should_update(
        self,
        update_type: str,
        sample_size: int
    ) -> bool:
        """
        업데이트 실행 여부
        
        Args:
            update_type: 업데이트 타입
            sample_size: 샘플 수
        
        Returns:
            업데이트 허용 여부
        """
        min_size = self.min_sample_size.get(update_type, 1)
        return sample_size >= min_size
    
    def get_learning_rate(
        self,
        update_type: str,
        sample_size: int
    ) -> float:
        """
        학습률 (1 - alpha)
        
        샘플이 많을수록 학습률 증가
        """
        base_rate = self.learning_rate.get(update_type, 0.2)
        
        # 샘플 많으면 학습률 증가
        if sample_size >= 10:
            return min(base_rate * 1.5, 0.5)
        elif sample_size >= 5:
            return base_rate
        else:
            return base_rate * 0.5  # 적으면 더 보수적
```

### 10.2 Outlier 감지

```python
def detect_outlier(
    self,
    comparisons: List[Dict],
    threshold: float = 3.0
) -> bool:
    """
    Outlier 감지
    
    Delta가 너무 크면 outlier로 판단
    
    Args:
        comparisons: 비교 결과
        threshold: Outlier 기준 (표준편차 배수)
    
    Returns:
        Outlier 여부
    """
    deltas = [c["delta_pct"] for c in comparisons]
    
    if not deltas:
        return False
    
    # 평균/표준편차
    mean_delta = sum(deltas) / len(deltas)
    
    if len(deltas) > 1:
        variance = sum((d - mean_delta) ** 2 for d in deltas) / len(deltas)
        std = variance ** 0.5
    else:
        std = 0.3  # 기본값
    
    # Outlier: ±3σ 벗어남
    for delta in deltas:
        if abs(delta - mean_delta) > threshold * std:
            return True
    
    return False
```

---

## 11. 피드백 반영 요약

### 반영된 7개 주요 피드백

1. ✅ **API 출력 형식**
   - updated_entities dict 반환
   - pattern_ids, metric_ids 명시

2. ✅ **Metric별 허용 오차**
   - metrics_spec.target_convergence
   - policy별 threshold

3. ✅ **Strategy-unlinked Outcome**
   - _learn_from_direct_outcome()
   - ValueEngine 과거 예측 비교

4. ✅ **Context별 Benchmark**
   - by_context 구조
   - domain/region/segment 분리

5. ✅ **버전 관리**
   - version 증가
   - previous_version_id
   - lineage.from_outcome_ids

6. ✅ **4-Learner 구조**
   - Pattern/Metric/Context/Belief 분리

7. ✅ **memory_store 통합**
   - MEM-* 저장
   - drift_alert, pattern_note

### 추가 개선

8. ✅ **학습 정책** - 최소 sample_size, learning_rate
9. ✅ **Outlier 감지** - ±3σ 기준
10. ✅ **Belief ↔ ValueEngine** - 명확한 인터페이스

---

## 12. 구현 로드맵 (Enhanced)

### Phase 1: Core + API (1주)

**Day 1-2**: 데이터 모델 + Sub-learners
- Outcome, LearningResult, LearningPolicy
- OutcomeComparator (Metric별 허용 오차)
- PatternLearner (Context별)
- MetricLearner, ContextLearner

**Day 3-4**: 두 가지 학습 경로
- _learn_from_strategy_outcome()
- _learn_from_direct_outcome()

**Day 5-6**: Public API
- update_from_outcomes_api() (updated_entities)
- update_project_context_from_outcome_api() (버전)

**Day 7**: 테스트
- 10개 테스트

---

### Phase 2: ValueEngine 연동 (1주)

**Day 1-3**: ValueEngine 통합
- Belief Update Request
- Past ValueRecord 비교

**Day 4-5**: memory_store 통합
- MEM-* 저장
- drift_alert

**Day 6-7**: 테스트
- 8개 테스트

---

## 13. 설계 검증 (Enhanced)

### cmis.yaml 정합성

- [x] update_from_outcomes → updated_entities dict
- [x] update_project_context_from_outcome → version 관리
- [x] outcome_store 스키마 완전 사용
- [x] project_context_store 버전/lineage

### 엔진 연계

- [x] **PatternEngine**: Benchmark 업데이트
- [x] **ValueEngine**: Belief/Prior 조정 인터페이스
- [x] **StrategyEngine**: 개선된 예측
- [x] **WorldEngine**: ProjectContext 업데이트

### 안전장치

- [x] 최소 sample_size
- [x] 보수적 learning_rate
- [x] Outlier 감지
- [x] Policy별 threshold

---

**작성**: 2025-12-11
**상태**: 설계 완료 (Enhanced) ✅
**기반**: 피드백 10개 완전 반영
**다음**: Phase 1 구현
