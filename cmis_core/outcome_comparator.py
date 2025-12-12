"""Outcome Comparator - 예측 vs 실제 비교

Outcome과 예측값 비교, Delta 계산

2025-12-11: LearningEngine Phase 1
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from .types import Outcome, Strategy
from .config import CMISConfig


class OutcomeComparator:
    """Outcome 비교기
    
    역할:
    1. Outcome vs Strategy 예측 비교
    2. Outcome vs ValueEngine 예측 비교
    3. Delta 계산
    4. Accuracy 평가
    """
    
    def __init__(self, config: Optional[CMISConfig] = None):
        """
        Args:
            config: CMIS 설정
        """
        if config is None:
            config = CMISConfig()
        
        self.config = config
        
        # Metric별 허용 오차 (metrics_spec)
        self.metric_tolerances = self._load_metric_tolerances()
        
        # Policy별 threshold
        self.policy_thresholds = {
            "reporting_strict": 0.2,      # ±20%
            "decision_balanced": 0.3,     # ±30%
            "exploration_friendly": 0.5   # ±50%
        }
    
    def _load_metric_tolerances(self) -> Dict[str, float]:
        """metrics_spec에서 target_convergence 로딩
        
        Returns:
            metric_id → tolerance
        """
        tolerances = {}
        
        # Phase 1: 기본값만
        # Phase 2: metrics_spec 실제 로딩
        
        default_tolerance = 0.3  # ±30%
        
        # 주요 Metric 기본값
        tolerances["MET-Revenue"] = 0.3
        tolerances["MET-N_customers"] = 0.25
        tolerances["MET-Churn_rate"] = 0.2
        tolerances["MET-Gross_margin"] = 0.15
        
        return tolerances
    
    def compare_outcome_vs_prediction(
        self,
        outcome: Outcome,
        strategy: Strategy,
        policy_mode: str = "decision_balanced"
    ) -> List[Dict[str, Any]]:
        """Outcome vs Strategy 예측 비교
        
        Args:
            outcome: 실제 결과
            strategy: 전략 (예측 포함)
            policy_mode: Policy 모드
        
        Returns:
            비교 결과 리스트
        """
        comparisons = []
        
        predicted = strategy.expected_outcomes
        actual = outcome.metrics
        
        # 공통 Metric
        common_metrics = set(predicted.keys()) & set(actual.keys())
        
        for metric_id in common_metrics:
            # 숫자 Metric만 (revenue_3y 등)
            if not metric_id.startswith("MET-") and not metric_id.endswith("_3y"):
                continue
            
            pred_value = predicted[metric_id]
            actual_value = actual.get(metric_id)
            
            if actual_value is None or not isinstance(pred_value, (int, float)):
                continue
            
            # Delta
            delta = actual_value - pred_value
            delta_pct = delta / pred_value if pred_value > 0 else 0
            
            # 범위 내 판단 (Metric + Policy 고려)
            within_bounds = self.is_within_bounds(metric_id, delta_pct, policy_mode)
            
            # Accuracy
            accuracy = max(0, 1 - abs(delta_pct))
            
            comparison = {
                "metric_id": metric_id,
                "predicted": pred_value,
                "actual": actual_value,
                "delta": delta,
                "delta_pct": delta_pct,
                "within_bounds": within_bounds,
                "accuracy": accuracy,
                "tolerance_used": self.metric_tolerances.get(metric_id, 0.3)
            }
            
            comparisons.append(comparison)
        
        return comparisons
    
    def is_within_bounds(
        self,
        metric_id: str,
        delta_pct: float,
        policy_mode: str = "decision_balanced"
    ) -> bool:
        """오차 범위 내 판단
        
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
        
        # 둘 중 더 엄격한 것
        tolerance = min(metric_tolerance, policy_threshold)
        
        return abs(delta_pct) <= tolerance
    
    def calculate_prediction_accuracy(
        self,
        comparisons: List[Dict[str, Any]]
    ) -> float:
        """전체 예측 정확도
        
        Args:
            comparisons: 비교 결과
        
        Returns:
            0.0 ~ 1.0
        """
        if not comparisons:
            return 0.0
        
        accuracies = [c["accuracy"] for c in comparisons]
        return sum(accuracies) / len(accuracies)
    
    def detect_outlier(
        self,
        comparisons: List[Dict[str, Any]],
        threshold: float = 3.0
    ) -> bool:
        """Outlier 감지
        
        Delta가 ±3σ 벗어나면 outlier
        
        Args:
            comparisons: 비교 결과
            threshold: 표준편차 배수
        
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
            std = 0.3
        
        # Outlier: ±3σ
        for delta in deltas:
            if abs(delta - mean_delta) > threshold * std:
                return True
        
        return False
