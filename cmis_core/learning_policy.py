"""Learning Policy - 학습 정책 및 안전장치

언제, 얼마나 강하게 학습할지 결정

2025-12-11: LearningEngine Phase 3
"""

from __future__ import annotations

from typing import Dict


class LearningPolicy:
    """학습 정책
    
    역할:
    - 최소 sample_size 관리
    - learning_rate 결정
    - 업데이트 허용 여부 판단
    """
    
    def __init__(self):
        """초기화"""
        # 최소 샘플 수
        self.min_sample_size = {
            "pattern_benchmark": 3,    # 최소 3개
            "metric_formula": 5,        # 최소 5개
            "belief_adjustment": 10,    # 최소 10개
            "context_baseline": 1       # 즉시 가능
        }
        
        # 학습률 (1 - alpha)
        self.base_learning_rate = {
            "pattern_benchmark": 0.2,   # alpha = 0.8
            "metric_formula": 0.3,
            "belief_adjustment": 0.1,   # 매우 보수적
            "context_baseline": 1.0     # 즉시 반영
        }
    
    def should_update(
        self,
        update_type: str,
        sample_size: int
    ) -> bool:
        """업데이트 실행 여부
        
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
        """학습률 계산
        
        샘플이 많을수록 학습률 증가
        
        Args:
            update_type: 업데이트 타입
            sample_size: 샘플 수
        
        Returns:
            학습률 (0.0 ~ 1.0)
        """
        base_rate = self.base_learning_rate.get(update_type, 0.2)
        
        # 샘플 수에 따라 조정
        if sample_size >= 20:
            # 많은 샘플: 학습률 증가
            return min(base_rate * 2.0, 0.5)
        elif sample_size >= 10:
            return min(base_rate * 1.5, 0.4)
        elif sample_size >= 5:
            return base_rate
        else:
            # 적은 샘플: 더 보수적
            return base_rate * 0.5
    
    def get_alpha(
        self,
        update_type: str,
        sample_size: int
    ) -> float:
        """Alpha 계산 (기존 가중치)
        
        alpha = 1 - learning_rate
        
        Returns:
            Alpha (0.0 ~ 1.0)
        """
        learning_rate = self.get_learning_rate(update_type, sample_size)
        return 1 - learning_rate
