"""Pattern Benchmark - Pattern 기반 Metric Prior Estimation

Pattern의 quantitative_bounds를 Metric Prior로 활용

2025-12-10: Phase 3
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any

from .types import PatternMatch, PatternSpec
from .pattern_library import PatternLibrary


class PatternBenchmarkProvider:
    """Pattern Benchmark 제공

    역할:
    1. Pattern의 quantitative_bounds를 조회
    2. Metric Prior로 변환
    3. ValueEngine Prior Estimation에 제공

    사용:
    - ValueEngine에서 Direct Evidence 없을 때
    - Pattern Benchmark를 Prior로 사용
    """

    def __init__(self, pattern_library: Optional[PatternLibrary] = None):
        """
        Args:
            pattern_library: Pattern 라이브러리
        """
        self.pattern_library = pattern_library or PatternLibrary()

        try:
            self.pattern_library.load_all()
        except Exception as e:
            print(f"Warning: Pattern loading failed: {e}")

    def get_prior_from_patterns(
        self,
        metric_id: str,
        matched_patterns: List[PatternMatch]
    ) -> Optional[Dict[str, Any]]:
        """Matched Pattern에서 Metric Prior 추출

        Args:
            metric_id: Metric ID (예: "MET-Churn_rate")
            matched_patterns: 매칭된 Pattern 리스트

        Returns:
            Prior 정보 (min, max, typical) or None
            {
                "min": 0.01,
                "max": 0.15,
                "typical": [0.03, 0.08],
                "source": "pattern:PAT-subscription_model",
                "confidence": 0.95
            }
        """
        for match in matched_patterns:
            pattern = self.pattern_library.get(match.pattern_id)

            if not pattern:
                continue

            # Metric이 benchmark_metrics에 있는지 확인
            if metric_id not in pattern.benchmark_metrics:
                continue

            # quantitative_bounds에서 해당 Metric 조회
            if not pattern.quantitative_bounds:
                continue

            # Metric ID에서 키 추출 (MET-Churn_rate → churn_rate)
            metric_key = metric_id.replace("MET-", "").lower()

            for bound_key, bound_value in pattern.quantitative_bounds.items():
                if metric_key in bound_key.lower():
                    # Bound 발견!
                    return {
                        "min": bound_value.get("min"),
                        "max": bound_value.get("max"),
                        "typical": bound_value.get("typical"),
                        "source": f"pattern:{match.pattern_id}",
                        "confidence": match.structure_fit_score,
                        "unit": bound_value.get("unit", ""),
                        "note": bound_value.get("note", "")
                    }

        return None

    def get_all_priors_from_patterns(
        self,
        matched_patterns: List[PatternMatch]
    ) -> Dict[str, Dict[str, Any]]:
        """모든 Matched Pattern의 Benchmark 추출

        Args:
            matched_patterns: 매칭된 Pattern 리스트

        Returns:
            Metric ID → Prior 매핑
            {
                "MET-Churn_rate": {"min": ..., "max": ...},
                "MET-Gross_margin": {...}
            }
        """
        priors = {}

        for match in matched_patterns:
            pattern = self.pattern_library.get(match.pattern_id)

            if not pattern or not pattern.quantitative_bounds:
                continue

            # 모든 benchmark metrics에 대해
            for metric_id in pattern.benchmark_metrics:
                if metric_id in priors:
                    continue  # 이미 있음 (첫 번째 Pattern 우선)

                prior = self.get_prior_from_patterns(metric_id, [match])

                if prior:
                    priors[metric_id] = prior

        return priors


# ========================================
# ValueEngine Helper 함수
# ========================================

def estimate_metric_from_pattern(
    metric_id: str,
    matched_patterns: List[PatternMatch],
    pattern_library: Optional[PatternLibrary] = None
) -> Optional[Dict[str, Any]]:
    """Pattern Benchmark 기반 Metric 추정

    ValueEngine Prior Estimation에서 사용

    Args:
        metric_id: Metric ID
        matched_patterns: 매칭된 Pattern 리스트
        pattern_library: Pattern 라이브러리

    Returns:
        Prior 추정값
    """
    provider = PatternBenchmarkProvider(pattern_library)
    return provider.get_prior_from_patterns(metric_id, matched_patterns)
