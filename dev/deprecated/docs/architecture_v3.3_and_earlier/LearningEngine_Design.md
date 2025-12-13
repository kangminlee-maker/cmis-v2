# LearningEngine 설계 문서

**작성일**: 2025-12-11
**버전**: v1.0
**상태**: 설계 완료

---

## Executive Summary

LearningEngine은 **실제 Outcome과 예측을 비교하여 시스템을 자동으로 개선**하는 엔진입니다.

**핵심 역할**:
- Outcome vs 예측 비교
- Pattern Benchmark 업데이트
- Metric 공식 보정
- FocalActorContext 업데이트
- Belief 조정

**설계 원칙**:
- **Monotonic Improvability**: 학습으로 계속 개선
- **Evidence-based Learning**: 실제 데이터 기반
- **Graceful Degradation**: 부분 학습 허용
- **Explainable**: 무엇이 왜 바뀌었는지 추적

---

## 1. CMIS 철학 및 아키텍처 분석

### 1.1 CMIS 4단계 루프

```
1. Understand (이해)
   → World Engine, Pattern Engine, Value Engine

2. Discover (발굴)
   → Pattern Engine (Gap Discovery)

3. Decide (결정)
   → Strategy Engine

4. Learn (학습) ⭐
   → Learning Engine
   → 1번으로 돌아감 (루프 완성)
```

**LearningEngine이 루프를 닫습니다!**

---

### 1.2 cmis.yaml 정의

**learning_engine**:
```yaml
learning_engine:
  description: "Outcome과 예상 값을 비교해 Belief/Pattern/Value Graph 업데이트"
  inputs:
    - outcome_store
    - value_graph
    - pattern_graph
    - project_context_store
  outputs:
    - updated_beliefs
    - updated_project_contexts
  api:
    - name: update_from_outcomes
      input:
        outcome_ids: "list[outcome_id]"
      output:
        update_summary_ref

    - name: update_project_context_from_outcome
      input:
        outcome_id
        project_context_id
      output:
        updated_context_ref
```

**outcome_store 스키마**:
```yaml
outcome_store:
  schema:
    outcome_id: str
    related_strategy_id: Optional[str]
    related_scenario_id: Optional[str]
    as_of: date  # 실제 측정 시점
    metrics: Dict  # metric_id → 실제 값
    context: Dict
```

---

## 2. LearningEngine 아키텍처

### 2.1 전체 구조

```
┌──────────────────────────────────────────────────────────┐
│                   LearningEngine                          │
│  update_from_outcomes() / update_project_context()       │
└──────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Outcome    │  │   Pattern    │  │  Project     │
│  Comparator  │  │   Learner    │  │  Context     │
│              │  │              │  │  Updater     │
│ 예측 vs 실제 │  │ Benchmark    │  │ Baseline     │
│ Delta 계산   │  │ 업데이트     │  │ 업데이트     │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────┐
│                  Inputs/Outputs                           │
│  - outcome_store (실제 결과)                             │
│  - value_graph (Metric 예측)                             │
│  - pattern_graph (Pattern Benchmark)                     │
│  - project_context_store (Baseline)                      │
└──────────────────────────────────────────────────────────┘
```

---

## 3. 데이터 모델

### 3.1 Outcome 데이터 클래스

```python
@dataclass
class Outcome:
    """실제 실행 결과 (outcome_store)

    Strategy/Scenario 실행 후 실제 측정된 결과
    """
    outcome_id: str

    # 연결
    related_strategy_id: Optional[str] = None
    related_scenario_id: Optional[str] = None
    project_context_id: Optional[str] = None

    # 실제 측정 시점
    as_of: str = ""  # 측정 완료 시점

    # 실제 Metric 값
    metrics: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "MET-Revenue": 12000000000,  # 실제 달성
    #   "MET-N_customers": 150000,
    #   "MET-Churn_rate": 0.06
    # }

    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    # {"domain_id": "...", "region": "...", "period": "..."}

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    # {"data_source": "internal_db", "quality": "verified"}
```

### 3.2 LearningResult 데이터 클래스

```python
@dataclass
class LearningResult:
    """학습 결과"""
    learning_id: str
    outcome_id: str

    # 비교 결과
    comparisons: List[Dict[str, Any]] = field(default_factory=list)
    # [
    #   {
    #     "metric_id": "MET-Revenue",
    #     "predicted": 10000000000,
    #     "actual": 12000000000,
    #     "delta": 2000000000,
    #     "delta_pct": 0.2,  # 20% 차이
    #     "within_bounds": True
    #   }
    # ]

    # 업데이트
    updates: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "pattern_benchmarks": [...],
    #   "metric_formulas": [...],
    #   "project_context": {...}
    # }

    # 학습 품질
    learning_quality: Dict[str, Any] = field(default_factory=dict)
    # {"confidence": 0.8, "sample_size": 1}

    # Lineage
    lineage: Dict[str, Any] = field(default_factory=dict)
```

---

## 4. OutcomeComparator 설계

### 4.1 예측 vs 실제 비교

**프로세스**:
```
1. Outcome에서 related_strategy_id 조회
   ↓
2. Strategy의 expected_outcomes 조회
   ↓
3. Outcome.metrics와 비교
   ↓
4. Delta 계산 (절대값, 백분율)
   ↓
5. 오차 범위 내/외 판단
```

**코드**:
```python
class OutcomeComparator:
    """Outcome 비교기"""

    def compare_outcome_vs_prediction(
        self,
        outcome: Outcome,
        strategy: Strategy
    ) -> List[Dict[str, Any]]:
        """
        실제 vs 예측 비교

        Returns:
            비교 결과 리스트
        """
        comparisons = []

        predicted = strategy.expected_outcomes
        actual = outcome.metrics

        # 공통 Metric
        common_metrics = set(predicted.keys()) & set(actual.keys())

        for metric_id in common_metrics:
            pred_value = predicted[metric_id]
            actual_value = actual[metric_id]

            # Delta
            delta = actual_value - pred_value
            delta_pct = delta / pred_value if pred_value > 0 else 0

            # 오차 범위 (±30%)
            within_bounds = abs(delta_pct) <= 0.3

            comparison = {
                "metric_id": metric_id,
                "predicted": pred_value,
                "actual": actual_value,
                "delta": delta,
                "delta_pct": delta_pct,
                "within_bounds": within_bounds,
                "accuracy": 1 - abs(delta_pct)
            }

            comparisons.append(comparison)

        return comparisons

    def calculate_prediction_accuracy(
        self,
        comparisons: List[Dict]
    ) -> float:
        """
        전체 예측 정확도

        Returns:
            0.0 ~ 1.0
        """
        if not comparisons:
            return 0.0

        accuracies = [c["accuracy"] for c in comparisons]
        return sum(accuracies) / len(accuracies)
```

---

## 5. PatternLearner 설계

### 5.1 Pattern Benchmark 업데이트

**학습 대상**:
- Pattern.quantitative_bounds 조정
- revenue_growth_yoy, gross_margin 등

**알고리즘**:
```python
class PatternLearner:
    """Pattern 학습기"""

    def update_pattern_benchmark(
        self,
        pattern_id: str,
        metric_id: str,
        actual_value: float,
        current_benchmark: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Pattern Benchmark 업데이트

        Bayesian 업데이트 (간단한 버전):
        new_typical = (old_typical × α) + (actual × (1-α))
        """
        alpha = 0.8  # 기존 가중치 (보수적)

        old_typical = current_benchmark.get("typical", [])

        if isinstance(old_typical, list) and len(old_typical) == 2:
            old_avg = sum(old_typical) / 2
        else:
            old_avg = old_typical

        # Bayesian 업데이트
        new_avg = old_avg * alpha + actual_value * (1 - alpha)

        # 범위도 조정
        old_min = current_benchmark.get("min", actual_value * 0.5)
        old_max = current_benchmark.get("max", actual_value * 1.5)

        new_min = min(old_min, actual_value * 0.9)
        new_max = max(old_max, actual_value * 1.1)

        new_typical = [new_avg * 0.9, new_avg * 1.1]

        updated_benchmark = {
            "min": new_min,
            "max": new_max,
            "typical": new_typical,
            "source": "learned",
            "sample_size": current_benchmark.get("sample_size", 0) + 1,
            "last_updated": datetime.now().isoformat()
        }

        return updated_benchmark
```

---

## 6. FocalActorContextUpdater 설계

### 6.1 Baseline State 업데이트

**학습 대상**:
- FocalActorContext.baseline_state
- 실제 달성한 매출, 고객수 등

**코드**:
```python
class FocalActorContextUpdater:
    """FocalActorContext 업데이트"""

    def update_baseline_state(
        self,
        project_context: FocalActorContext,
        outcome: Outcome
    ) -> FocalActorContext:
        """
        baseline_state 업데이트

        Outcome의 실제 값으로 업데이트
        """
        updated_baseline = dict(project_context.baseline_state)

        # Outcome의 metrics를 baseline으로
        for metric_id, value in outcome.metrics.items():
            # MET-Revenue → current_revenue
            if metric_id == "MET-Revenue":
                updated_baseline["current_revenue"] = value
            elif metric_id == "MET-N_customers":
                updated_baseline["current_customers"] = value
            elif metric_id == "MET-Gross_margin":
                if "margin_structure" not in updated_baseline:
                    updated_baseline["margin_structure"] = {}
                updated_baseline["margin_structure"]["gross_margin"] = value

        # as_of 업데이트
        updated_baseline["as_of"] = outcome.as_of

        # 새 FocalActorContext
        updated_context = FocalActorContext(
            project_context_id=project_context.project_context_id,
            scope=project_context.scope,
            assets_profile=project_context.assets_profile,
            baseline_state=updated_baseline,
            constraints_profile=project_context.constraints_profile,
            preference_profile=project_context.preference_profile,
            focal_actor_id=project_context.focal_actor_id
        )

        return updated_context
```

---

## 7. LearningEngine API

### 7.1 update_from_outcomes()

**Public API** (cmis.yaml 대응):
```python
class LearningEngine:
    """Learning Engine v1

    역할:
    - Outcome vs 예측 비교
    - Pattern Benchmark 업데이트
    - Metric 공식 보정
    - FocalActorContext 업데이트
    """

    def __init__(self):
        self.outcome_comparator = OutcomeComparator()
        self.pattern_learner = PatternLearner()
        self.context_updater = FocalActorContextUpdater()

        # Stores (Phase 1: 인메모리)
        self.outcomes: Dict[str, Outcome] = {}
        self.learning_history: List[LearningResult] = []

    def update_from_outcomes_api(
        self,
        outcome_ids: List[str]
    ) -> str:
        """
        Public API (cmis.yaml 대응)

        프로세스:
        1. outcome_store에서 Outcome 로딩
        2. 각 Outcome에 대해:
           - Strategy/예측 조회
           - 실제 vs 예측 비교
           - Delta 분석
        3. Pattern Benchmark 업데이트
        4. 학습 결과 저장
        5. update_summary_ref 반환

        Args:
            outcome_ids: Outcome ID 리스트

        Returns:
            update_summary_ref: "LEARN-{uuid}"
        """
        learning_results = []

        for outcome_id in outcome_ids:
            # 1. Outcome 로딩
            outcome = self._load_outcome(outcome_id)

            if not outcome:
                continue

            # 2. Strategy/예측 조회
            if outcome.related_strategy_id:
                strategy = self._load_strategy(outcome.related_strategy_id)

                if strategy:
                    # 3. 비교
                    comparisons = self.outcome_comparator.compare_outcome_vs_prediction(
                        outcome,
                        strategy
                    )

                    # 4. 학습
                    updates = self._learn_from_comparisons(
                        comparisons,
                        strategy,
                        outcome
                    )

                    # 5. 결과 저장
                    learning_result = LearningResult(
                        learning_id=f"LEARN-{uuid.uuid4().hex[:8]}",
                        outcome_id=outcome_id,
                        comparisons=comparisons,
                        updates=updates
                    )

                    learning_results.append(learning_result)

        # 6. Summary 저장
        summary_ref = self._save_learning_summary(learning_results)

        return summary_ref

    def update_project_context_from_outcome_api(
        self,
        outcome_id: str,
        project_context_id: str
    ) -> str:
        """
        Public API (cmis.yaml 대응)

        프로세스:
        1. Outcome 로딩
        2. FocalActorContext 로딩
        3. baseline_state 업데이트 (실제 값으로)
        4. project_context_store 저장
        5. updated_context_ref 반환
        """
        # 1. Outcome
        outcome = self._load_outcome(outcome_id)

        # 2. FocalActorContext
        project_context = self._load_project_context(project_context_id)

        # 3. 업데이트
        updated_context = self.context_updater.update_baseline_state(
            project_context,
            outcome
        )

        # 4. 저장
        updated_ref = self._save_project_context(updated_context)

        return updated_ref
```

---

## 8. 학습 알고리즘

### 8.1 Pattern Benchmark 학습

**시나리오**:
```
예측: revenue_3y = 10억 (Pattern Benchmark 기반)
실제: revenue_3y = 12억 (20% 높음)

→ Pattern의 revenue_growth_yoy Benchmark 상향 조정
```

**알고리즘**:
```python
def _learn_from_comparisons(
    self,
    comparisons: List[Dict],
    strategy: Strategy,
    outcome: Outcome
) -> Dict[str, Any]:
    """
    비교 결과로부터 학습
    """
    updates = {
        "pattern_benchmarks": [],
        "metric_formulas": [],
        "confidence_adjustments": []
    }

    for comp in comparisons:
        metric_id = comp["metric_id"]
        delta_pct = comp["delta_pct"]

        # 오차가 크면 (±30% 초과)
        if abs(delta_pct) > 0.3:
            # Pattern Benchmark 업데이트
            for pattern_id in strategy.pattern_composition:
                update = self.pattern_learner.update_pattern_benchmark(
                    pattern_id=pattern_id,
                    metric_id=metric_id,
                    actual_value=comp["actual"],
                    current_benchmark=...
                )

                updates["pattern_benchmarks"].append({
                    "pattern_id": pattern_id,
                    "metric_id": metric_id,
                    "old_value": comp["predicted"],
                    "new_value": comp["actual"],
                    "update": update
                })

    return updates
```

---

## 9. 구현 계획

### Phase 1: Core (1주)

**Day 1-2**: 데이터 모델
- Outcome, LearningResult
- types.py 추가

**Day 3-4**: OutcomeComparator
- compare_outcome_vs_prediction()
- calculate_prediction_accuracy()

**Day 5-6**: PatternLearner
- update_pattern_benchmark()
- Bayesian 업데이트

**Day 7**: LearningEngine
- update_from_outcomes_api()
- 테스트 10개

---

### Phase 2: FocalActorContext (1주)

**Day 1-3**: FocalActorContextUpdater
- update_baseline_state()
- update_assets_profile()

**Day 4-5**: update_project_context_from_outcome_api()
- Full API 구현

**Day 6-7**: 테스트
- 8개 테스트

---

## 10. 설계 검증

### CMIS 철학

- [x] **Monotonic Improvability**: 학습으로 개선
- [x] **Evidence-first**: 실제 Outcome 기반
- [x] **Re-runnability**: 업데이트 후 재실행
- [x] **Explainable**: 학습 내역 추적

### cmis.yaml 정합성

- [x] update_from_outcomes API
- [x] update_project_context_from_outcome API
- [x] outcome_store 스키마
- [x] canonical_workflows.reality_monitoring

### 엔진 연계

- [x] **PatternEngine**: Benchmark 업데이트
- [x] **ValueEngine**: Metric 공식 보정
- [x] **StrategyEngine**: 개선된 예측
- [x] **WorldEngine**: FocalActorContext 업데이트

---

**작성**: 2025-12-11
**상태**: 설계 완료 ✅
**다음**: Phase 1 구현
**예상 시간**: 2주

**LearningEngine 설계 완성!**
