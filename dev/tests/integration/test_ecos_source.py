"""ECOS (한국은행) Source 테스트

2025-12-10: OFFICIAL Tier 확장
"""

import pytest
import os
from dotenv import load_dotenv

from cmis_core.types import EvidenceRequest
from cmis_core.evidence_engine import (
    DataNotFoundError,
    SourceNotAvailableError,
)

load_dotenv()

HAS_ECOS_KEY = bool(os.getenv("ECOS_API_KEY"))


@pytest.fixture
def ecos_source():
    """ECOS Source fixture"""
    if not HAS_ECOS_KEY:
        pytest.skip("ECOS_API_KEY not found")

    from cmis_core.evidence.ecos_source import ECOSSource
    return ECOSSource()


class TestECOSStatTables:
    """통계표 매핑 테스트"""

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_gdp_nominal(self, ecos_source):
        """GDP (명목) 조회"""
        request = EvidenceRequest(
            request_id="test-gdp",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR", "year": 2023, "stat_type": "gdp"}
        )

        record = ecos_source.fetch(request)

        assert record.source_id == "ECOS"
        assert record.source_tier == "official"
        assert record.confidence == 0.95
        assert record.value > 600000  # 600조원 (십억원 단위) 이상

        print(f"GDP (명목): {record.value:,.1f} {record.metadata['unit']}")

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_gdp_growth(self, ecos_source):
        """경제성장률 조회"""
        request = EvidenceRequest(
            request_id="test-growth",
            request_type="metric",
            metric_id="MET-GDP_growth",
            context={"region": "KR", "year": 2023, "stat_type": "gdp_growth"}
        )

        record = ecos_source.fetch(request)

        assert record.source_id == "ECOS"
        assert -5.0 < record.value < 10.0  # 성장률 -5% ~ 10% 범위

        print(f"2023년 경제성장률: {record.value:.2f}%")

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_cpi(self, ecos_source):
        """소비자물가지수 조회"""
        request = EvidenceRequest(
            request_id="test-cpi",
            request_type="metric",
            metric_id="MET-CPI",
            context={"region": "KR", "year": 2023, "stat_type": "cpi"}
        )

        record = ecos_source.fetch(request)

        assert record.source_id == "ECOS"
        assert 80 < record.value < 150  # 지수 80~150 범위

        print(f"2023년 CPI: {record.value:.2f}")


class TestECOSAPI:
    """ECOS API 호출 테스트"""

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_api_response_structure(self, ecos_source):
        """API 응답 구조 확인"""
        data = ecos_source._fetch_key_statistic(
            "GDP(명목, 계절조정)",
            {"year": 2023}
        )

        assert isinstance(data, list)
        assert len(data) > 0

        # 첫 번째 row 구조 확인
        row = data[0]
        assert "DATA_VALUE" in row
        assert "KEYSTAT_NAME" in row
        assert "UNIT_NAME" in row

        print(f"ECOS API response: {len(data)} rows")

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_multiple_stats(self, ecos_source):
        """여러 통계 조회"""
        data = ecos_source._fetch_key_statistic(
            "GDP",
            {}
        )

        assert data is not None
        assert len(data) > 0

        # GDP 관련 지표 확인
        for row in data[:3]:
            print(f"  {row['KEYSTAT_NAME']}: {row['DATA_VALUE']}")


class TestECOSCanHandle:
    """can_handle 메서드 테스트"""

    def test_can_handle_kr_gdp(self, ecos_source):
        """KR GDP 처리 가능"""
        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR"}
        )

        assert ecos_source.can_handle(request) is True

    def test_can_handle_kr_cpi(self, ecos_source):
        """KR CPI 처리 가능"""
        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-CPI",
            context={"region": "KR"}
        )

        assert ecos_source.can_handle(request) is True

    def test_cannot_handle_non_kr(self, ecos_source):
        """KR 외 지역 처리 불가"""
        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "US"}
        )

        assert ecos_source.can_handle(request) is False


class TestECOSConfidence:
    """신뢰도 테스트"""

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_official_tier(self, ecos_source):
        """OFFICIAL tier 확인"""
        assert ecos_source.source_tier.value == "official"

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_high_confidence(self, ecos_source):
        """높은 신뢰도 (0.95)"""
        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR", "year": 2023}
        )

        record = ecos_source.fetch(request)

        assert record.confidence == 0.95  # OFFICIAL tier 고정 신뢰도


class TestECOSEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_old_year(self, ecos_source):
        """과거 연도 (2010)"""
        request = EvidenceRequest(
            request_id="test-old",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR", "year": 2010}
        )

        # 100대 통계는 최신 데이터만 제공 (year 파라미터 무시)
        record = ecos_source.fetch(request)

        # 최신 GDP 값 확인
        assert record.value > 600000  # 600조원 이상

        print(f"GDP (최신): {record.value:,.1f}")

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_future_year(self, ecos_source):
        """미래 연도 (데이터 없음)"""
        request = EvidenceRequest(
            request_id="test-future",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR", "year": 2030}
        )

        try:
            record = ecos_source.fetch(request)
            # 데이터 있으면 통과
            assert record is not None
        except DataNotFoundError:
            # 데이터 없으면 예상된 동작
            pytest.skip("Future data not available (expected)")


class TestECOSMetadata:
    """메타데이터 테스트"""

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_metadata_complete(self, ecos_source):
        """메타데이터 완전성"""
        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR", "year": 2023}
        )

        record = ecos_source.fetch(request)

        # 메타데이터 필드 확인
        assert "stat_type" in record.metadata
        assert "keyword" in record.metadata
        assert "stat_name" in record.metadata
        assert "unit" in record.metadata

        print(f"Metadata: {record.metadata['stat_name']}")
        print(f"  Unit: {record.metadata['unit']}")


class TestECOSIntegration:
    """통합 테스트"""

    @pytest.mark.skipif(not HAS_ECOS_KEY, reason="ECOS_API_KEY not found")
    def test_multiple_stats(self, ecos_source):
        """여러 통계 조회"""
        stat_types = ["gdp", "gdp_growth", "cpi"]

        for stat_type in stat_types:
            request = EvidenceRequest(
                request_id=f"test-{stat_type}",
                request_type="metric",
                metric_id=f"MET-{stat_type.upper()}",
                context={"region": "KR", "year": 2023, "stat_type": stat_type}
            )

            try:
                record = ecos_source.fetch(request)
                print(f"{stat_type}: {record.value:,.2f} {record.metadata.get('unit', '')}")
            except DataNotFoundError:
                print(f"{stat_type}: 데이터 없음")


