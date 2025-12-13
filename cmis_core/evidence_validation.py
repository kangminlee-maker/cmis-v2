"""Evidence Validation - Cross-Source 검증

여러 Source 간 일치도 검증 및 신뢰도 조정

2025-12-10: Evidence Engine v2.2
"""

from __future__ import annotations

import statistics
from typing import List, Dict, Any

from .types import EvidenceRecord


def cross_validate_evidence(
    evidence_list: List[EvidenceRecord]
) -> Dict[str, Any]:
    """Cross-source validation

    여러 Source에서 수집한 Evidence를 비교하여
    일치도를 측정하고 confidence bonus 계산

    Args:
        evidence_list: EvidenceRecord 리스트 (2개 이상)

    Returns:
        {
            "consensus_value": float,
            "confidence_bonus": 0.0 ~ 0.1,
            "divergence": CV (Coefficient of Variation),
            "agreement_level": "high" | "medium" | "low",
            "outliers": [...]
        }
    """
    if len(evidence_list) < 2:
        return {
            "consensus_value": evidence_list[0].value if evidence_list else None,
            "confidence_bonus": 0.0,
            "agreement_level": "single_source"
        }

    # 값 추출
    values = [e.value for e in evidence_list if isinstance(e.value, (int, float))]

    if not values:
        return {"agreement_level": "no_numeric_data"}

    # 통계 계산
    mean_value = statistics.mean(values)
    median_value = statistics.median(values)

    if len(values) >= 2:
        stdev = statistics.stdev(values)
        cv = stdev / mean_value if mean_value > 0 else 1.0
    else:
        cv = 0.0

    # Agreement level 결정
    if cv < 0.1:
        agreement = "high"
        confidence_bonus = 0.1
    elif cv < 0.3:
        agreement = "medium"
        confidence_bonus = 0.05
    else:
        agreement = "low"
        confidence_bonus = 0.0

    # Outlier 탐지
    outliers = detect_outliers(evidence_list, values)

    return {
        "consensus_value": median_value,
        "mean_value": mean_value,
        "confidence_bonus": confidence_bonus,
        "divergence": cv,
        "agreement_level": agreement,
        "outliers": outliers,
        "num_sources": len(evidence_list)
    }


def detect_outliers(
    evidence_list: List[EvidenceRecord],
    values: List[float]
) -> List[str]:
    """Outlier 탐지 (IQR 방법)

    Args:
        evidence_list: Evidence 리스트
        values: 값 리스트

    Returns:
        Outlier Evidence ID 리스트
    """
    if len(values) < 4:
        return []

    sorted_values = sorted(values)
    q1 = statistics.median(sorted_values[:len(sorted_values)//2])
    q3 = statistics.median(sorted_values[len(sorted_values)//2:])
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outliers = []

    for i, evidence in enumerate(evidence_list):
        if isinstance(evidence.value, (int, float)):
            if evidence.value < lower_bound or evidence.value > upper_bound:
                outliers.append(evidence.evidence_id)

    return outliers


def detect_conflicts(
    evidence_list: List[EvidenceRecord],
    conflict_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """Evidence 충돌 탐지

    Args:
        evidence_list: Evidence 리스트
        conflict_threshold: 충돌 기준 (CV > 0.5)

    Returns:
        충돌 리스트
        [
            {
                "type": "high_divergence",
                "evidence_ids": [...],
                "divergence": 0.75,
                "message": "Sources disagree significantly"
            }
        ]
    """
    conflicts = []

    if len(evidence_list) < 2:
        return conflicts

    # Cross-validation
    validation = cross_validate_evidence(evidence_list)

    # 높은 divergence (충돌)
    if validation.get("divergence", 0) > conflict_threshold:
        conflicts.append({
            "type": "high_divergence",
            "evidence_ids": [e.evidence_id for e in evidence_list],
            "divergence": validation["divergence"],
            "message": f"Sources disagree (CV={validation['divergence']:.2f})",
            "consensus": validation["consensus_value"]
        })

    # Tier 간 불일치
    official_values = [
        e.value for e in evidence_list
        if e.source_tier == "official"
    ]
    commercial_values = [
        e.value for e in evidence_list
        if e.source_tier == "commercial"
    ]

    if official_values and commercial_values:
        official_mean = statistics.mean(official_values)
        commercial_mean = statistics.mean(commercial_values)

        diff_ratio = abs(official_mean - commercial_mean) / official_mean

        if diff_ratio > 0.3:  # 30% 이상 차이
            conflicts.append({
                "type": "tier_disagreement",
                "official_value": official_mean,
                "commercial_value": commercial_mean,
                "difference_ratio": diff_ratio,
                "message": f"OFFICIAL vs COMMERCIAL differ by {diff_ratio*100:.1f}%"
            })

    return conflicts


