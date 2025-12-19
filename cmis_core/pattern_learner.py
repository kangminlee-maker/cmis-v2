"""Pattern Learner - Pattern Benchmark 학습

실제 Outcome으로 Pattern.quantitative_bounds 업데이트

2025-12-11: LearningEngine Phase 1
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .pattern_library import PatternLibrary


class PatternLearner:
    """Pattern 학습기

    역할:
    - Pattern Benchmark 업데이트 (Context별)
    - Bayesian 업데이트
    - sample_size 관리
    """

    def __init__(self, pattern_library: Optional[PatternLibrary] = None):
        """
        Args:
            pattern_library: Pattern 라이브러리
        """
        if pattern_library is None:
            pattern_library = PatternLibrary()
            try:
                pattern_library.load_all()
            except Exception:
                pass

        self.pattern_library = pattern_library

    def update_pattern_benchmark(
        self,
        pattern_id: str,
        metric_id: str,
        actual_value: float,
        context: Dict[str, Any],
        sample_size: int = 1,
        alpha: float = 0.8
    ) -> Dict[str, Any]:
        """Pattern Benchmark 업데이트 (Context별)

        Args:
            pattern_id: Pattern ID
            metric_id: Metric ID (예: "gross_margin")
            actual_value: 실제 값
            context: Context (domain_id, region, segment)
            sample_size: 샘플 수
            alpha: 기존 가중치 (보수적, 기본 0.8)

        Returns:
            업데이트된 Benchmark
        """
        # Pattern 조회
        pattern = self.pattern_library.get(pattern_id)

        if not pattern or not pattern.quantitative_bounds:
            return {}

        current_benchmark = pattern.quantitative_bounds.get(metric_id, {})

        if not current_benchmark:
            return {}

        # Context key
        context_key = str((
            context.get("domain_id", "global"),
            context.get("region", "global"),
            context.get("segment", "all")
        ))

        # by_context 초기화
        if "by_context" not in current_benchmark:
            current_benchmark["by_context"] = {}

        # Context별 Benchmark
        context_bench = current_benchmark["by_context"].get(
            context_key,
            current_benchmark.copy()
        )

        # Bayesian 업데이트
        old_typical = context_bench.get("typical", [])

        if isinstance(old_typical, list) and len(old_typical) >= 2:
            old_avg = sum(old_typical) / len(old_typical)
        else:
            old_avg = old_typical if isinstance(old_typical, (int, float)) else actual_value

        new_avg = old_avg * alpha + actual_value * (1 - alpha)

        # 범위 조정
        old_min = context_bench.get("min", actual_value * 0.5)
        old_max = context_bench.get("max", actual_value * 1.5)

        new_min = min(old_min, actual_value * 0.9)
        new_max = max(old_max, actual_value * 1.1)

        # 업데이트
        updated = {
            "min": new_min,
            "max": new_max,
            "typical": [new_avg * 0.9, new_avg * 1.1],
            "source": "learned",
            "sample_size": context_bench.get("sample_size", 0) + sample_size,
            "last_updated": datetime.now().isoformat(),
            "context": context_key,
            "unit": current_benchmark.get("unit", "ratio")
        }

        # by_context 저장
        current_benchmark["by_context"][context_key] = updated

        # Global도 업데이트
        current_benchmark["typical"] = [new_avg * 0.9, new_avg * 1.1]
        current_benchmark["last_updated"] = datetime.now().isoformat()

        return current_benchmark
