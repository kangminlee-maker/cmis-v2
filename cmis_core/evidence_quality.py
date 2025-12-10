"""Evidence Quality - 신선도 및 품질 관리

Evidence의 신선도, 품질 점수 계산

2025-12-10: Evidence Engine v2.2
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .types import EvidenceRecord


def adjust_confidence_by_age(
    confidence: float,
    retrieved_at: str,
    max_age_days: Optional[int] = None
) -> float:
    """Age 기반 confidence 조정
    
    Args:
        confidence: 원래 신뢰도
        retrieved_at: 수집 시점 (ISO format)
        max_age_days: 최대 허용 age (None이면 무제한)
    
    Returns:
        조정된 신뢰도
    
    조정 규칙:
    - 1년 이상: -10%
    - 2년 이상: -20%
    - 3년 이상: -30%
    """
    try:
        retrieved_time = datetime.fromisoformat(retrieved_at)
        age_days = (datetime.now(timezone.utc) - retrieved_time).days
        
        # max_age 초과 시 0
        if max_age_days and age_days > max_age_days:
            return 0.0
        
        # Age 기반 감소
        if age_days > 1095:  # 3년
            return confidence * 0.7
        elif age_days > 730:  # 2년
            return confidence * 0.8
        elif age_days > 365:  # 1년
            return confidence * 0.9
        
        return confidence
    
    except Exception:
        # 파싱 실패 시 원래 값
        return confidence


def calculate_freshness_score(
    retrieved_at: str,
    ideal_age_days: int = 30
) -> float:
    """Freshness score 계산
    
    Args:
        retrieved_at: 수집 시점
        ideal_age_days: 이상적인 age (기본 30일)
    
    Returns:
        Freshness score (0.0 ~ 1.0)
        - 최신: 1.0
        - ideal_age: 0.8
        - 1년: 0.5
        - 2년: 0.3
    """
    try:
        retrieved_time = datetime.fromisoformat(retrieved_at)
        age_days = (datetime.now(timezone.utc) - retrieved_time).days
        
        if age_days <= 0:
            return 1.0
        elif age_days <= ideal_age_days:
            # Linear decay: 1.0 → 0.8
            return 1.0 - (age_days / ideal_age_days) * 0.2
        elif age_days <= 365:
            # 30일 ~ 1년: 0.8 → 0.5
            return 0.8 - ((age_days - ideal_age_days) / (365 - ideal_age_days)) * 0.3
        elif age_days <= 730:
            # 1년 ~ 2년: 0.5 → 0.3
            return 0.5 - ((age_days - 365) / 365) * 0.2
        else:
            # 2년 이상: 0.3 이하
            return max(0.1, 0.3 - ((age_days - 730) / 365) * 0.2)
    
    except Exception:
        return 0.5  # 기본값


def calculate_quality_score(
    evidence: EvidenceRecord,
    cross_validation_bonus: float = 0.0
) -> float:
    """Evidence 종합 품질 점수
    
    Args:
        evidence: EvidenceRecord
        cross_validation_bonus: Cross-validation 보너스 (0.0 ~ 0.1)
    
    Returns:
        품질 점수 (0.0 ~ 1.0)
    
    계산:
    - Tier: 40%
    - Confidence: 40%
    - Freshness: 10%
    - Cross-validation: 10%
    """
    # Tier score
    tier_scores = {
        "official": 1.0,
        "curated_internal": 0.8,
        "commercial": 0.6
    }
    tier_score = tier_scores.get(evidence.source_tier, 0.5)
    
    # Confidence
    confidence = evidence.confidence
    
    # Freshness
    freshness = calculate_freshness_score(evidence.retrieved_at)
    
    # Cross-validation (0.0 ~ 0.1)
    cross_val = min(cross_validation_bonus, 0.1)
    
    # 종합
    quality = (
        tier_score * 0.4 +
        confidence * 0.4 +
        freshness * 0.1 +
        cross_val * 0.1
    )
    
    return quality


def is_evidence_fresh(
    retrieved_at: str,
    max_age_days: int = 365
) -> bool:
    """Evidence가 신선한지 여부
    
    Args:
        retrieved_at: 수집 시점
        max_age_days: 최대 허용 age
    
    Returns:
        신선하면 True
    """
    try:
        retrieved_time = datetime.fromisoformat(retrieved_at)
        age_days = (datetime.now(timezone.utc) - retrieved_time).days
        
        return age_days <= max_age_days
    
    except Exception:
        return True  # 파싱 실패 시 허용
