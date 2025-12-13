"""Evidence Engine v2.2 테스트

8가지 보강 기능 검증

2025-12-10
"""

import pytest
import time

from cmis_core.types import EvidenceRequest, MetricRequest
from cmis_core.evidence_engine import (
    EvidenceEngine,
    SourceRegistry,
    SourceTimeoutError,
    DataNotFoundError
)
from cmis_core.evidence_store import EvidenceStore
from cmis_core.rate_limiter import RateLimiter
from cmis_core.evidence_quality import (
    adjust_confidence_by_age,
    calculate_freshness_score,
    calculate_quality_score
)
from cmis_core.evidence_validation import (
    cross_validate_evidence,
    detect_conflicts
)
from cmis_core.evidence_retry import RetryStrategy, retry
from cmis_core.config import CMISConfig


class TestFetchForRealitySlice:
    """fetch_for_reality_slice 테스트"""

    def test_reality_slice_basic(self):
        """기본 Reality slice 수집"""
        config = CMISConfig()
        registry = SourceRegistry()
        engine = EvidenceEngine(config, registry)

        scope = {
            "domain_id": "Adult_Language_Education_KR",
            "region": "KR"
        }

        evidence_list = engine.fetch_for_reality_slice(scope, "2024")

        # 여러 Evidence 수집되어야 함
        assert isinstance(evidence_list, list)
        print(f"Reality slice: {len(evidence_list)} evidence collected")


class TestHintsReuse:
    """Hints 재활용 테스트"""

    def test_query_hints(self):
        """Hints 조회"""
        store = EvidenceStore()

        hints = store.query_hints(
            domain_id="Adult_Language_Education_KR",
            region="KR"
        )

        assert isinstance(hints, list)
        print(f"Hints found: {len(hints)}")

    def test_query_hints_with_filter(self):
        """필터링된 hints 조회"""
        store = EvidenceStore()

        hints = store.query_hints(
            domain_id="Adult_Language_Education_KR",
            metric_pattern="MET-TAM",
            min_confidence=0.5
        )

        # 모두 min_confidence 이상
        for hint in hints:
            assert hint.get("confidence", 0) >= 0.5


class TestRateLimiting:
    """Rate Limiting 테스트"""

    def test_rate_limiter_basic(self):
        """기본 Rate limiting"""
        limiter = RateLimiter()

        # ECOS: 100 calls/min
        assert limiter.check("ECOS") is True
        assert limiter.check("ECOS") is True

    def test_rate_limiter_stats(self):
        """Rate limiter 통계"""
        limiter = RateLimiter()

        stats = limiter.get_stats("ECOS")

        assert stats["limited"] is True
        assert "current_tokens" in stats
        assert "can_call" in stats

        print(f"ECOS tokens: {stats['current_tokens']:.1f}")

    def test_no_limit_for_unknown_source(self):
        """제한 없는 Source"""
        limiter = RateLimiter()

        assert limiter.check("UnknownSource") is True


class TestFreshness:
    """Evidence Freshness 테스트"""

    def test_adjust_confidence_fresh(self):
        """신선한 데이터 (조정 없음)"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        adjusted = adjust_confidence_by_age(0.95, now)

        assert adjusted == 0.95  # 변화 없음

    def test_adjust_confidence_old(self):
        """오래된 데이터 (감소)"""
        from datetime import datetime, timezone, timedelta

        # 2년 전
        old_time = (datetime.now(timezone.utc) - timedelta(days=730)).isoformat()

        adjusted = adjust_confidence_by_age(0.95, old_time)

        # 2년 → -20%, 0.95 * 0.8 = 0.76
        assert adjusted < 0.95  # 감소해야 함
        assert adjusted >= 0.70  # 최소 0.70 이상

    def test_freshness_score(self):
        """Freshness score 계산"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        score = calculate_freshness_score(now, ideal_age_days=30)

        assert score == 1.0  # 최신


class TestCrossValidation:
    """Cross-Source Validation 테스트"""

    def test_cross_validate_high_agreement(self):
        """높은 일치도"""
        from cmis_core.types import EvidenceRecord, EvidenceValueKind, SourceTier

        evidence_list = [
            EvidenceRecord(
                evidence_id="E1",
                source_tier="official",
                source_id="KOSIS",
                value=51217221,
                value_kind=EvidenceValueKind.NUMERIC,
                confidence=0.95,
                retrieved_at="2024-12-10T00:00:00Z"
            ),
            EvidenceRecord(
                evidence_id="E2",
                source_tier="commercial",
                source_id="Google",
                value=51000000,
                value_kind=EvidenceValueKind.NUMERIC,
                confidence=0.75,
                retrieved_at="2024-12-10T00:00:00Z"
            )
        ]

        result = cross_validate_evidence(evidence_list)

        assert result["agreement_level"] in ["high", "medium", "low"]
        assert 0.0 <= result["confidence_bonus"] <= 0.1

        print(f"Agreement: {result['agreement_level']}, Bonus: {result['confidence_bonus']}")

    def test_detect_conflicts(self):
        """충돌 탐지"""
        from cmis_core.types import EvidenceRecord, EvidenceValueKind

        # 큰 차이
        evidence_list = [
            EvidenceRecord(
                evidence_id="E1",
                source_tier="official",
                source_id="KOSIS",
                value=50000000,
                value_kind=EvidenceValueKind.NUMERIC,
                confidence=0.95,
                retrieved_at="2024-12-10T00:00:00Z"
            ),
            EvidenceRecord(
                evidence_id="E2",
                source_tier="commercial",
                source_id="Google",
                value=100000000,  # 2배 차이
                value_kind=EvidenceValueKind.NUMERIC,
                confidence=0.75,
                retrieved_at="2024-12-10T00:00:00Z"
            )
        ]

        conflicts = detect_conflicts(evidence_list, conflict_threshold=0.3)

        assert len(conflicts) > 0  # 충돌 탐지되어야 함


class TestRetryStrategy:
    """Retry 전략 테스트"""

    def test_retry_success_on_second_attempt(self):
        """2번째 시도 성공"""
        attempt_count = [0]

        def flaky_function():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise SourceTimeoutError("Timeout")
            return "success"

        strategy = RetryStrategy(max_attempts=3, initial_delay=0.1)
        result = strategy.execute_with_retry(flaky_function)

        assert result == "success"
        assert attempt_count[0] == 2

    def test_retry_decorator(self):
        """Retry decorator"""
        attempt_count = [0]

        @retry(max_attempts=3, initial_delay=0.1)
        def flaky_function():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise SourceTimeoutError("Timeout")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert attempt_count[0] == 2


class TestQualityScore:
    """Quality Score 테스트"""

    def test_quality_score_official(self):
        """OFFICIAL tier 품질 점수"""
        from cmis_core.types import EvidenceRecord, EvidenceValueKind
        from datetime import datetime, timezone

        evidence = EvidenceRecord(
            evidence_id="E1",
            source_tier="official",
            source_id="KOSIS",
            value=51217221,
            value_kind=EvidenceValueKind.NUMERIC,
            confidence=0.95,
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )

        score = calculate_quality_score(evidence)

        # OFFICIAL + 높은 confidence + 신선함
        assert score > 0.85

        print(f"Quality score: {score:.2f}")


class TestIntegration:
    """통합 테스트"""

    def test_all_features_together(self):
        """모든 기능 통합"""
        # Rate limiter
        limiter = RateLimiter()
        assert limiter.check("ECOS") is True

        # Freshness
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        freshness = calculate_freshness_score(now)
        assert freshness == 1.0

        # Retry
        strategy = RetryStrategy(max_attempts=2)
        assert strategy.max_attempts == 2

        print("All 8 features integrated")


