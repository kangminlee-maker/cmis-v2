"""Learning Engine - 학습 및 피드백 루프

Outcome → 시스템 개선

Phase 1: Core Infrastructure
2025-12-11: LearningEngine Phase 1
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .types import Outcome, LearningResult, Strategy, FocalActorContext
from .outcome_comparator import OutcomeComparator
from .pattern_learner import PatternLearner
from .context_learner import ContextLearner
from .metric_learner import MetricLearner
from .learning_policy import LearningPolicy
from .config import CMISConfig


class LearningEngine:
    """Learning Engine v1

    역할:
    - Outcome vs 예측 비교
    - Pattern Benchmark 업데이트
    - Metric Belief 보정
    - FocalActorContext baseline 업데이트

    Phase 1: Core + API
    Phase 2: ValueEngine 연동, memory_store
    """

    def __init__(
        self,
        config: Optional[CMISConfig] = None,
        project_root: Optional[Path] = None
    ):
        """
        Args:
            config: CMIS 설정
            project_root: 프로젝트 루트
        """
        if config is None:
            config = CMISConfig()

        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.config = config
        self.project_root = Path(project_root)

        # Sub-learners
        self.outcome_comparator = OutcomeComparator(config)
        self.pattern_learner = PatternLearner()
        self.context_learner = ContextLearner()
        self.metric_learner = MetricLearner()  # Phase 3
        self.learning_policy = LearningPolicy()  # Phase 3

        # Stores (인메모리)
        self.outcomes: Dict[str, Outcome] = {}
        self.strategies: Dict[str, Strategy] = {}
        self.project_contexts: Dict[str, FocalActorContext] = {}
        self.learning_history: List[LearningResult] = []

        # memory_store (Phase 3: 간단한 버전)
        self.memory_store: List[Dict[str, Any]] = []

    def update_from_outcomes_api(
        self,
        outcome_ids: List[str]
    ) -> Dict[str, Any]:
        """Public API (cmis.yaml 대응)

        프로세스:
        1. Outcome 로딩
        2. Strategy-linked vs unlinked 분기
        3. 학습 실행
        4. updated_entities 반환

        Args:
            outcome_ids: Outcome ID 리스트

        Returns:
            {
                "summary_ref": "LEARN-xxxx",
                "updated_entities": {...},
                "learning_quality": {...}
            }
        """
        learning_results = []
        updated_pattern_ids = set()
        updated_metric_ids = set()
        updated_context_ids = set()

        for outcome_id in outcome_ids:
            # Outcome 로딩
            outcome = self._load_outcome(outcome_id)

            if not outcome:
                continue

            # 분기
            if outcome.related_strategy_id:
                # 경로 1: Strategy 기반
                result = self._learn_from_strategy_outcome(outcome)
            else:
                # 경로 2: Direct calibration
                result = self._learn_from_direct_outcome(outcome)

            if result:
                learning_results.append(result)
                self.learning_history.append(result)

                # 업데이트 추적
                for update in result.updates.get("pattern_benchmarks", []):
                    updated_pattern_ids.add(update["pattern_id"])

                for update in result.updates.get("metric_formulas", []):
                    updated_metric_ids.add(update.get("metric_id", ""))

        # Summary
        summary_ref = f"LEARN-{uuid.uuid4().hex[:8]}"

        # memory_store 저장 (Phase 3)
        self._save_learning_summary_to_memory(learning_results)

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

    def _learn_from_strategy_outcome(
        self,
        outcome: Outcome
    ) -> Optional[LearningResult]:
        """Strategy 기반 학습

        Args:
            outcome: Outcome

        Returns:
            LearningResult
        """
        # Strategy 로딩
        strategy = self._load_strategy(outcome.related_strategy_id)

        if not strategy:
            return None

        # 비교
        comparisons = self.outcome_comparator.compare_outcome_vs_prediction(
            outcome,
            strategy,
            policy_mode="decision_balanced"
        )

        # Outlier 체크
        is_outlier = self.outcome_comparator.detect_outlier(comparisons)

        if is_outlier:
            # Outlier는 학습 안 함
            return LearningResult(
                learning_id=f"LEARN-outlier-{uuid.uuid4().hex[:8]}",
                outcome_id=outcome.outcome_id,
                comparisons=comparisons,
                updates={},
                learning_quality={"is_outlier": True}
            )

        # 학습
        updates = self._learn_from_comparisons(comparisons, strategy, outcome)

        return LearningResult(
            learning_id=f"LEARN-{uuid.uuid4().hex[:8]}",
            outcome_id=outcome.outcome_id,
            comparisons=comparisons,
            updates=updates,
            learning_quality={
                "accuracy": self.outcome_comparator.calculate_prediction_accuracy(comparisons),
                "sample_size": 1,
                "is_outlier": False
            }
        )

    def _learn_from_direct_outcome(
        self,
        outcome: Outcome
    ) -> Optional[LearningResult]:
        """Direct calibration (Strategy 없음)

        Phase 1: 간단한 구현
        Phase 2: ValueEngine 과거 예측 비교
        """
        # Phase 1: Pattern Benchmark와만 비교
        comparisons = []

        for metric_id, actual_value in outcome.metrics.items():
            # 간단한 비교 (기본값 대비)
            comparisons.append({
                "metric_id": metric_id,
                "predicted": 0,  # Phase 2: ValueEngine 예측
                "actual": actual_value,
                "delta_pct": 0,
                "prediction_source": "none"
            })

        return LearningResult(
            learning_id=f"LEARN-direct-{uuid.uuid4().hex[:8]}",
            outcome_id=outcome.outcome_id,
            comparisons=comparisons,
            updates={},
            learning_quality={"type": "direct", "sample_size": 1}
        )

    def _learn_from_comparisons(
        self,
        comparisons: List[Dict],
        strategy: Strategy,
        outcome: Outcome
    ) -> Dict[str, Any]:
        """비교 결과로부터 학습

        Args:
            comparisons: 비교 결과
            strategy: Strategy
            outcome: Outcome

        Returns:
            updates dict
        """
        updates = {
            "pattern_benchmarks": [],
            "metric_formulas": [],
            "confidence_adjustments": []
        }

        for comp in comparisons:
            metric_id = comp["metric_id"]
            delta_pct = comp["delta_pct"]

            # 오차 큰 경우만 학습
            if abs(delta_pct) > 0.3:
                # Pattern Benchmark 업데이트
                for pattern_id in strategy.pattern_composition:
                    # metric_id에서 "_3y" 제거
                    clean_metric = metric_id.replace("_3y", "").replace("revenue", "gross_margin")

                    # Phase 1: 간단한 업데이트만
                    updated_bench = {
                        "pattern_id": pattern_id,
                        "metric_id": clean_metric,
                        "old_value": comp["predicted"],
                        "new_value": comp["actual"],
                        "delta_pct": delta_pct,
                        "context": outcome.context
                    }

                    updates["pattern_benchmarks"].append(updated_bench)

                # Metric Belief 조정 (Phase 3)
                belief_update = self.metric_learner.adjust_metric_belief(
                    metric_id=metric_id,
                    predicted=comp["predicted"],
                    actual=comp["actual"],
                    delta_pct=delta_pct,
                    sample_size=1
                )

                if belief_update:
                    updates["confidence_adjustments"].append(belief_update)

                # Quality 업데이트
                quality_update = self.metric_learner.update_metric_quality(
                    metric_id=metric_id,
                    accuracy=comp.get("accuracy", 0),
                    sample_size=1
                )

                if quality_update:
                    updates["metric_formulas"].append(quality_update)

        return updates

    def _save_learning_summary_to_memory(
        self,
        learning_results: List[LearningResult]
    ) -> None:
        """Learning summary를 memory_store에 저장

        Phase 3: drift_alert, pattern_note
        """
        for result in learning_results:
            # Drift 감지
            has_drift = any(
                abs(c.get("delta_pct", 0)) > 0.5
                for c in result.comparisons
            )

            memory_type = "drift_alert" if has_drift else "pattern_note"

            # memory_store에 저장
            memory_record = {
                "memory_id": f"MEM-{result.learning_id}",
                "memory_type": memory_type,
                "content": {
                    "learning_id": result.learning_id,
                    "outcome_id": result.outcome_id,
                    "comparisons": result.comparisons,
                    "updates": result.updates
                },
                "related_ids": {
                    "outcome_id": result.outcome_id,
                    "pattern_ids": [u.get("pattern_id") for u in result.updates.get("pattern_benchmarks", [])]
                },
                "created_at": datetime.now().isoformat()
            }

            self.memory_store.append(memory_record)

    def _load_outcome(self, outcome_id: str) -> Optional[Outcome]:
        """Outcome 로딩"""
        return self.outcomes.get(outcome_id)

    def _load_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Strategy 로딩"""
        return self.strategies.get(strategy_id)

    def _calculate_avg_accuracy(
        self,
        learning_results: List[LearningResult]
    ) -> float:
        """평균 accuracy"""
        if not learning_results:
            return 0.0

        accuracies = [
            r.learning_quality.get("accuracy", 0)
            for r in learning_results
            if "accuracy" in r.learning_quality
        ]

        return sum(accuracies) / len(accuracies) if accuracies else 0.0

    def register_outcome(self, outcome: Outcome) -> None:
        """Outcome 등록 (테스트용)"""
        self.outcomes[outcome.outcome_id] = outcome

    def register_strategy(self, strategy: Strategy) -> None:
        """Strategy 등록 (테스트용)"""
        self.strategies[strategy.strategy_id] = strategy

    def register_project_context(self, project_context: FocalActorContext) -> None:
        """FocalActorContext 등록 (테스트용)"""
        self.project_contexts[project_context.project_context_id] = project_context

    def update_project_context_from_outcome_api(
        self,
        outcome_id: str,
        project_context_id: str
    ) -> str:
        """Public API: FocalActorContext 업데이트 (cmis.yaml 대응)

        프로세스:
        1. Outcome 로딩
        2. FocalActorContext 로딩
        3. baseline_state 업데이트
        4. 새 버전 생성
        5. 저장
        6. updated_context_ref 반환

        Args:
            outcome_id: Outcome ID
            project_context_id: FocalActorContext ID

        Returns:
            updated_context_ref: "PRJ-xxx-vN"
        """
        # 1. Outcome 로딩
        outcome = self._load_outcome(outcome_id)

        if not outcome:
            return f"{project_context_id}-unchanged"

        # 2. FocalActorContext 로딩
        project_context = self._load_project_context(project_context_id)

        if not project_context:
            return f"{project_context_id}-notfound"

        # 3. 업데이트
        updated_context = self.context_learner.update_baseline_state(
            project_context,
            outcome
        )

        # 4. 저장 (Phase 2: 캐시)
        self.project_contexts[updated_context.project_context_id] = updated_context

        return updated_context.project_context_id

    def _load_project_context(
        self,
        project_context_id: str
    ) -> Optional[FocalActorContext]:
        """FocalActorContext 로딩"""
        return self.project_contexts.get(project_context_id)
