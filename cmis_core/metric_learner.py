"""Metric Learner - Metric Belief 및 공식 보정

ValueEngine 연동, Prior 조정

2025-12-11: LearningEngine Phase 3
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime

from .value_engine import ValueEngine


class MetricLearner:
    """Metric 학습기
    
    역할:
    - Metric Belief 조정
    - Prior 파라미터 업데이트
    - Quality profile 조정
    """
    
    def __init__(self, value_engine: Optional[ValueEngine] = None):
        """
        Args:
            value_engine: Value Engine
        """
        self.value_engine = value_engine
    
    def adjust_metric_belief(
        self,
        metric_id: str,
        predicted: float,
        actual: float,
        delta_pct: float,
        sample_size: int = 1
    ) -> Dict[str, Any]:
        """Metric Belief 조정
        
        ValueEngine Prior 파라미터 조정
        
        Args:
            metric_id: Metric ID
            predicted: 예측값
            actual: 실제값
            delta_pct: Delta 백분율
            sample_size: 샘플 수
        
        Returns:
            Belief 업데이트
        """
        # 일관된 방향 오차 (bias)
        if abs(delta_pct) > 0.3 and sample_size >= 3:
            # Prior 조정 필요
            adjustment = {
                "metric_id": metric_id,
                "adjustment_type": "prior_bias",
                "bias_direction": "over_estimate" if delta_pct < 0 else "under_estimate",
                "bias_magnitude": abs(delta_pct),
                "recommended_action": "adjust_prior_mean",
                "new_prior_factor": 1 + delta_pct,  # 보정 계수
                "sample_size": sample_size,
                "confidence": min(sample_size / 10, 0.8)  # 샘플 많을수록 신뢰
            }
            
            return adjustment
        
        return {}
    
    def update_metric_quality(
        self,
        metric_id: str,
        accuracy: float,
        sample_size: int = 1
    ) -> Dict[str, Any]:
        """Metric Quality 업데이트
        
        accuracy 기반 confidence 조정
        
        Args:
            metric_id: Metric ID
            accuracy: 정확도 (0.0 ~ 1.0)
            sample_size: 샘플 수
        
        Returns:
            Quality 업데이트
        """
        # accuracy → confidence
        # 샘플 수 고려
        base_confidence = min(accuracy, 0.95)
        
        # 샘플 많으면 신뢰도 증가
        if sample_size >= 10:
            adjusted_confidence = min(base_confidence * 1.1, 0.95)
        elif sample_size >= 5:
            adjusted_confidence = base_confidence
        else:
            adjusted_confidence = base_confidence * 0.9
        
        return {
            "metric_id": metric_id,
            "quality_update": {
                "confidence": adjusted_confidence,
                "accuracy_history": accuracy,
                "sample_size": sample_size,
                "source": "outcome_validation",
                "updated_at": datetime.now().isoformat()
            }
        }
    
    def detect_formula_error(
        self,
        metric_id: str,
        comparisons: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """공식 오류 감지
        
        지속적 오차 → 공식 재검토 필요
        
        Args:
            metric_id: Metric ID
            comparisons: 비교 결과
        
        Returns:
            공식 오류 정보 또는 None
        """
        delta_pct = comparisons.get("delta_pct", 0)
        accuracy = comparisons.get("accuracy", 1)
        
        # 지속적으로 큰 오차 (accuracy < 0.5)
        if accuracy < 0.5:
            return {
                "metric_id": metric_id,
                "issue_type": "formula_error_suspected",
                "accuracy": accuracy,
                "delta_pct": delta_pct,
                "recommendation": "Review metric formula or dependencies",
                "severity": "high" if accuracy < 0.3 else "medium"
            }
        
        return None
