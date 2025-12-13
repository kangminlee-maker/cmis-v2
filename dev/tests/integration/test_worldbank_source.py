"""World Bank Source 테스트

2025-12-10: OFFICIAL Tier 확장 (글로벌)
"""

import pytest

from cmis_core.types import EvidenceRequest
from cmis_core.evidence_engine import DataNotFoundError


class TestWorldBankIndicators:
    """World Bank 지표 테스트"""

    def test_gdp(self):
        """GDP 조회"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        request = EvidenceRequest(
            request_id="test-gdp",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR", "year": "2023"}
        )

        record = source.fetch(request)

        assert record.source_id == "WorldBank"
        assert record.source_tier == "official"
        assert record.confidence == 0.95
        assert record.value > 1_000_000_000_000  # > $1T

        print(f"Korea GDP (2023): ${record.value:,.0f}")

    def test_population(self):
        """인구 조회"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        request = EvidenceRequest(
            request_id="test-pop",
            request_type="metric",
            metric_id="MET-N_customers",
            context={"region": "KR", "year": "2023", "stat_type": "population"}
        )

        record = source.fetch(request)

        assert record.value > 50_000_000  # > 5천만

        print(f"Korea Population: {record.value:,.0f}")

    def test_gdp_growth(self):
        """GDP 성장률"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        request = EvidenceRequest(
            request_id="test-growth",
            request_type="metric",
            metric_id="MET-GDP_growth",
            context={"region": "KR", "year": "2023"}
        )

        record = source.fetch(request)

        assert -10.0 < record.value < 20.0  # -10% ~ 20% 범위

        print(f"GDP Growth: {record.value:.2f}%")


class TestWorldBankAPI:
    """API 호출 테스트"""

    def test_api_response_structure(self):
        """API 응답 구조"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        data = source._fetch_indicator_data(
            "KOR",
            "NY.GDP.MKTP.CD",
            {"year": "2023"}
        )

        assert isinstance(data, list)
        assert len(data) > 0

        # 첫 번째 item 구조
        item = data[0]
        assert "value" in item
        assert "date" in item
        assert "country" in item

    def test_multiple_countries(self):
        """여러 국가 조회"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        countries = ["KR", "US", "JP"]

        for region in countries:
            request = EvidenceRequest(
                request_id=f"test-{region}",
                request_type="metric",
                metric_id="MET-GDP",
                context={"region": region, "year": "2023"}
            )

            try:
                record = source.fetch(request)
                print(f"{region} GDP: ${record.value:,.0f}")
            except DataNotFoundError:
                print(f"{region}: 데이터 없음")


class TestWorldBankCanHandle:
    """can_handle 테스트"""

    def test_can_handle_gdp(self):
        """GDP 처리 가능"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR"}
        )

        assert source.can_handle(request) is True

    def test_can_handle_population(self):
        """인구 처리 가능"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-N_customers",
            context={"region": "US"}
        )

        assert source.can_handle(request) is True


class TestWorldBankConfidence:
    """신뢰도 테스트"""

    def test_official_tier(self):
        """OFFICIAL tier 확인"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        assert source.source_tier.value == "official"

    def test_high_confidence(self):
        """높은 신뢰도 (0.95)"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR", "year": "2023"}
        )

        record = source.fetch(request)

        assert record.confidence == 0.95


class TestWorldBankMetadata:
    """메타데이터 테스트"""

    def test_metadata_complete(self):
        """메타데이터 완전성"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-GDP",
            context={"region": "KR", "year": "2023"}
        )

        record = source.fetch(request)

        assert "stat_type" in record.metadata
        assert "indicator_code" in record.metadata
        assert "country_code" in record.metadata
        assert "unit" in record.metadata


class TestWorldBankIntegration:
    """통합 테스트"""

    def test_multiple_indicators(self):
        """여러 지표 조회"""
        from cmis_core.evidence.worldbank_source import WorldBankSource

        source = WorldBankSource()

        indicators = [
            ("MET-GDP", "gdp"),
            ("MET-N_customers", "population"),
            ("MET-GDP_growth", "gdp_growth")
        ]

        for metric_id, stat_type in indicators:
            request = EvidenceRequest(
                request_id=f"test-{stat_type}",
                request_type="metric",
                metric_id=metric_id,
                context={"region": "KR", "year": "2023", "stat_type": stat_type}
            )

            try:
                record = source.fetch(request)
                print(f"{stat_type}: {record.value:,.2f} {record.metadata.get('unit', '')}")
            except DataNotFoundError:
                print(f"{stat_type}: 데이터 없음")


