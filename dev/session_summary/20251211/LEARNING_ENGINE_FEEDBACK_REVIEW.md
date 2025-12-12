# LearningEngine 피드백 검토 및 반영 보고

**작성일**: 2025-12-11
**기반**: LearningEngine_Design.md 피드백
**상태**: ✅ 검토 및 반영 완료

---

## Executive Summary

LearningEngine 설계에 대한 10개 주요 피드백을 검토하고 모두 반영했습니다.

**결론**:
- 기존 구조는 CMIS 철학과 잘 맞음
- 완전 재설계 불필요
- **인터페이스/스키마 정렬 + 안전장치 보강**으로 충분

---

## 피드백 검토 및 반영

### 1. API 출력 형식 (최상) ✅

**피드백**:
- cmis.yaml: `updated_entities: dict` 반환
- 설계: `summary_ref: "LEARN-xxxx"` 반환
- 불일치

**반영**:
```python
def update_from_outcomes_api(...) -> Dict[str, Any]:
    return {
        "summary_ref": "LEARN-xxxx",
        "updated_entities": {
            "pattern_ids": [...],
            "metric_ids": [...],
            "project_context_ids": [...],
            "belief_updates": 5
        },
        "learning_quality": {
            "total_outcomes": 10,
            "valid_comparisons": 8,
            "accuracy_avg": 0.85
        }
    }
```

**문서**: Enhanced Design § 2.1

---

### 2. Metric별 허용 오차 (상) ✅

**피드백**:
- ±30% 고정 → metrics_spec 연동
- quality_profiles별 threshold

**반영**:
```python
class OutcomeComparator:
    def _load_metric_tolerances(self):
        """
        metrics_spec.target_convergence 로딩
        """
        for metric_id, spec in metrics_spec.items():
            convergence = spec["resolution_protocol"]["target_convergence"]
            # "±30%" → 0.3
    
    def is_within_bounds(self, metric_id, delta_pct, policy_mode):
        """
        Metric + Policy 고려
        """
        metric_tolerance = self.metric_tolerances[metric_id]
        policy_threshold = self.policy_thresholds[policy_mode]
        
        tolerance = min(metric_tolerance, policy_threshold)
        return abs(delta_pct) <= tolerance
```

**문서**: Enhanced Design § 3.1

---

### 3. Strategy-unlinked Outcome (상) ✅

**피드백**:
- Strategy 없는 Outcome 무시됨
- ValueEngine 비교 경로 필요

**반영**:
```python
# 경로 1: Strategy-linked
if outcome.related_strategy_id:
    result = _learn_from_strategy_outcome(outcome)

# 경로 2: Strategy-unlinked (신규)
else:
    result = _learn_from_direct_outcome(outcome)
    # ValueEngine 과거 예측 또는 Pattern Benchmark와 비교
```

**_learn_from_direct_outcome()**:
- ValueEngine 과거 ValueRecord 조회
- Pattern Benchmark와 비교
- Metric/Belief 직접 보정

**문서**: Enhanced Design § 4.1

---

### 4. Context별 Benchmark (상) ✅

**피드백**:
- Global Benchmark만 → Context별 분리
- domain/segment별 관리

**반영**:
```python
def update_pattern_benchmark(
    pattern_id,
    metric_id,
    actual_value,
    context: Dict  # domain_id, region, segment
):
    # Context key
    context_key = (
        context["domain_id"],
        context["region"],
        context.get("segment", "all")
    )
    
    # Context별 Benchmark
    benchmark["by_context"][context_key] = updated
    
    # Global도 함께 업데이트
```

**구조**:
```json
{
  "gross_margin": {
    "typical": [0.6, 0.8],  // Global
    "by_context": {
      "('Adult_Language_Education_KR', 'KR', 'all')": {
        "typical": [0.65, 0.75]
      }
    }
  }
}
```

**문서**: Enhanced Design § 5.1

---

### 5. ProjectContext 버전 관리 (상) ✅

**피드백**:
- project_context_store는 버전 관리
- version, previous_version_id, lineage

**반영**:
```python
updated_context = ProjectContext(
    project_context_id=f"{old.project_context_id}-v{next_version}",
    version=old.version + 1,  # 버전 증가
    previous_version_id=old.project_context_id,
    lineage={
        "from_outcome_ids": [...],
        "updated_at": "...",
        "updated_by": "learning_engine"
    },
    ...
)
```

**quantity_ref 형식** (Phase 2):
```python
baseline_state["current_revenue"] = {
    "amount": value,
    "currency": "KRW",
    "per": "year"
}
```

**문서**: Enhanced Design § 6.1

---

### 6. Belief ↔ ValueEngine 연결 (중) ✅

**피드백**:
- Belief 조정이 ValueEngine과 어떻게 연결되는지 불명확

**반영**:

**Option A: Belief Update Request** (권장):
```python
def _update_value_engine_beliefs(metric_updates):
    for update in metric_updates:
        # ValueEngine API 호출 (Phase 2)
        # value_engine.update_prior_belief(
        #     metric_id=update["metric_id"],
        #     adjustment_factor=update["new_prior_factor"]
        # )
```

**Option B: value_graph 직접 수정**:
```python
# value_graph.update_metric_node(...)
```

**설계 방향**: Option A

**문서**: Enhanced Design § 8.1

---

### 7. memory_store 통합 (중) ✅

**피드백**:
- LearningResult를 memory_store에 저장
- drift_alert, pattern_note 활용

**반영**:
```python
def _save_learning_summary(learning_results):
    for result in learning_results:
        # Drift 감지
        has_drift = any(abs(c["delta_pct"]) > 0.5 for c in result.comparisons)
        
        memory_type = "drift_alert" if has_drift else "pattern_note"
        
        # memory_store 저장 (Phase 2)
        # memory_store.save(
        #     memory_id=f"MEM-{result.learning_id}",
        #     memory_type=memory_type,
        #     content_ref=result,
        #     related_ids={...}
        # )
```

**문서**: Enhanced Design § 9.1

---

### 8. 4-Learner 구조 (중) ✅

**피드백**:
- 대안 A: Sub-learner 명확한 분리

**반영**:
```
LearningEngine
  ├ OutcomeComparator  # 비교
  ├ PatternLearner     # pattern_graph
  ├ MetricLearner      # value_graph/Belief (신규)
  └ ContextLearner     # project_context_store
```

**문서**: Enhanced Design § 1.1

---

### 9. 학습 정책 및 안전장치 ✅

**피드백**:
- 최소 sample_size
- 보수적 learning_rate
- Outlier 감지

**반영**:
```python
class LearningPolicy:
    min_sample_size = {
        "pattern_benchmark": 3,
        "metric_formula": 5,
        "belief_adjustment": 10
    }
    
    learning_rate = {
        "pattern_benchmark": 0.2,  # alpha = 0.8
        "metric_formula": 0.3,
        "belief_adjustment": 0.1   # 매우 보수적
    }
```

**Outlier 감지**: ±3σ 기준

**문서**: Enhanced Design § 10

---

### 10. 기타 고려사항 ✅

**학습 트리거**:
- Phase 1: 수동/배치
- Phase 2: sample_size ≥ N

**Rollback/Human-in-the-loop**:
- proposal_mode vs apply_mode (미래)

**Metric 간 상관관계**:
- Phase 1: Independent
- Phase 2: Joint update

---

## 변경 요약

### Before (v1.0)

**구조**:
- OutcomeComparator/PatternLearner/ContextUpdater
- update_from_outcomes_api()

**문제**:
- API 출력 형식 불일치
- ±30% 하드코딩
- Strategy 없는 Outcome 무시
- Global Benchmark만
- 버전 관리 없음

---

### After (v1.1 Enhanced)

**개선**:
1. **4-Learner 구조** - Metric/Belief 분리
2. **API 출력** - updated_entities dict
3. **Metric별 허용 오차** - specs 연동
4. **두 경로** - Strategy-linked + unlinked
5. **Context별** - by_context 구조
6. **버전 관리** - version/lineage
7. **안전장치** - sample_size, outlier

**추가**:
- LearningPolicy
- MetricLearner
- memory_store 통합
- Belief ↔ ValueEngine 인터페이스

---

## 생성된 문서

1. **LearningEngine_Design_Enhanced.md** (약 1,200 라인)
   - 피드백 10개 완전 반영
   - 4-Learner 구조
   - 안전장치 설계

2. **LEARNING_ENGINE_FEEDBACK_REVIEW.md** (현재 문서)
   - 피드백 상세 검토
   - 반영 내역

---

## 다음 단계

### LearningEngine Phase 1 구현

**작업**:
- Outcome, LearningResult 데이터 모델
- OutcomeComparator (Metric별 허용 오차)
- PatternLearner (Context별)
- MetricLearner, ContextLearner
- update_from_outcomes_api()
- 10개 테스트

**예상 시간**: 1주

---

**작성**: 2025-12-11
**상태**: 피드백 검토 및 반영 완료 ✅
**결과**: Enhanced Design v1.1
**다음**: Phase 1 구현
