"""KOSIS API 고도화 테스트

KOSIS API 확장 기능 검증:
- 5개 통계표 (인구, 연앙인구, 가구, 가구원수, 소득)
- 지역별 데이터 (전국 + 17개 시도)
- 시계열 데이터 (2020-2024)
- 동적 파라미터 (objL1, itmId, prdSe)
- JavaScript JSON 파싱 안정성

2025-12-10: KOSIS API 고도화
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

HAS_KOSIS_KEY = bool(os.getenv("KOSIS_API_KEY"))


@pytest.fixture
def kosis_source():
    """KOSIS Source fixture"""
    if not HAS_KOSIS_KEY:
        pytest.skip("KOSIS_API_KEY not found")

    from cmis_core.evidence.kosis_source import KOSISSource
    return KOSISSource()


class TestKOSISStatTables:
    """통계표 매핑 테스트"""

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_population_table(self, kosis_source):
        """인구 통계표 (DT_1B04006)"""
        request = EvidenceRequest(
            request_id="test-pop",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "year": 2024, "stat_type": "population"}
        )

        record = kosis_source.fetch(request)

        assert record.source_id == "KOSIS"
        assert record.value > 50_000_000
        assert record.confidence >= 0.9
        assert record.metadata["stat_type"] == "population"

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_household_table(self, kosis_source):
        """가구 통계표 (DT_1B04005N)"""
        request = EvidenceRequest(
            request_id="test-hh",
            request_type="metric",
            metric_id="MET-household",
            context={"region": "KR", "year": 2024, "stat_type": "household"}
        )

        record = kosis_source.fetch(request)

        assert record.source_id == "KOSIS"
        assert record.value > 20_000_000
        assert record.metadata["stat_type"] == "household"

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_population_2023(self, kosis_source):
        """2023년 인구 통계"""
        request = EvidenceRequest(
            request_id="test-pop-2023",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "year": 2023, "stat_type": "population"}
        )

        record = kosis_source.fetch(request)

        assert record.source_id == "KOSIS"
        assert record.value > 50_000_000
        assert record.metadata["stat_type"] == "population"
        print(f"2023년 인구: {record.value:,.0f}명")


class TestKOSISRegions:
    """지역별 조회 테스트"""

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_nationwide_data(self, kosis_source):
        """전국 데이터 (objL1=00)"""
        request = EvidenceRequest(
            request_id="test-kr",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "area": "전국", "year": 2024}
        )

        record = kosis_source.fetch(request)

        assert record.value > 50_000_000
        print(f"전국 인구: {record.value:,.0f}명")

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_seoul_data(self, kosis_source):
        """서울 데이터 (objL1=11)"""
        request = EvidenceRequest(
            request_id="test-seoul",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "area": "서울", "year": 2024}
        )

        record = kosis_source.fetch(request)

        assert 9_000_000 < record.value < 11_000_000
        print(f"서울 인구: {record.value:,.0f}명")

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_busan_data(self, kosis_source):
        """부산 데이터 (objL1=26)"""
        request = EvidenceRequest(
            request_id="test-busan",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "area": "부산", "year": 2024}
        )

        record = kosis_source.fetch(request)

        assert 3_000_000 < record.value < 4_000_000
        print(f"부산 인구: {record.value:,.0f}명")

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_gyeonggi_data(self, kosis_source):
        """경기 데이터 (objL1=41)"""
        request = EvidenceRequest(
            request_id="test-gyeonggi",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "area": "경기", "year": 2024}
        )

        record = kosis_source.fetch(request)

        assert 13_000_000 < record.value < 15_000_000
        print(f"경기 인구: {record.value:,.0f}명")

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_sejong_data(self, kosis_source):
        """세종 데이터 (objL1=36)"""
        request = EvidenceRequest(
            request_id="test-sejong",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "area": "세종", "year": 2024}
        )

        record = kosis_source.fetch(request)

        assert 300_000 < record.value < 500_000
        print(f"세종 인구: {record.value:,.0f}명")


class TestKOSISTimeSeries:
    """시계열 데이터 테스트"""

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_single_year(self, kosis_source):
        """단일 연도 조회 (2024)"""
        request = EvidenceRequest(
            request_id="test-2024",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "year": 2024}
        )

        record = kosis_source.fetch(request)

        assert isinstance(record.value, (int, float))
        assert record.value > 50_000_000

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_time_series_3years(self, kosis_source):
        """3년 시계열 (2022-2024)"""
        request = EvidenceRequest(
            request_id="test-ts-3y",
            request_type="metric",
            metric_id="MET-population",
            context={
                "region": "KR",
                "start_year": 2022,
                "end_year": 2024
            }
        )

        record = kosis_source.fetch(request)

        assert isinstance(record.value, list)
        assert len(record.value) == 3

        for item in record.value:
            assert 'period' in item
            assert 'value' in item
            assert item['value'] > 50_000_000

        print(f"시계열 데이터: {len(record.value)}개 시점")

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_time_series_5years(self, kosis_source):
        """5년 시계열 (2020-2024)"""
        request = EvidenceRequest(
            request_id="test-ts-5y",
            request_type="metric",
            metric_id="MET-population",
            context={
                "region": "KR",
                "start_year": 2020,
                "end_year": 2024
            }
        )

        record = kosis_source.fetch(request)

        assert isinstance(record.value, list)
        assert len(record.value) >= 4

        print(f"5년 시계열: {len(record.value)}개 시점")


class TestKOSISParameters:
    """파라미터 동적 처리 테스트"""

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_objl1_dynamic_mapping(self, kosis_source):
        """objL1 동적 매핑 (지역 코드)"""
        areas = ["전국", "서울", "부산", "경기"]

        for area in areas:
            request = EvidenceRequest(
                request_id=f"test-{area}",
                request_type="metric",
                metric_id="MET-population",
                context={"region": "KR", "area": area, "year": 2024}
            )

            record = kosis_source.fetch(request)

            assert record.value > 0
            print(f"{area}: {record.value:,.0f}명")

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_itmid_dynamic_mapping(self, kosis_source):
        """itmId 동적 매핑 (통계표별 항목 코드)"""
        stat_types = ["population", "household"]

        for stat_type in stat_types:
            request = EvidenceRequest(
                request_id=f"test-{stat_type}",
                request_type="metric",
                metric_id=f"MET-{stat_type}",
                context={
                    "region": "KR",
                    "year": 2024,
                    "stat_type": stat_type
                }
            )

            record = kosis_source.fetch(request)

            assert record.value > 0
            print(f"{stat_type}: {record.value:,.0f}")


class TestKOSISJSONParsing:
    """JavaScript JSON 파싱 안정성 테스트"""

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_json_parsing_valid_data(self, kosis_source):
        """정상 데이터 파싱"""
        request = EvidenceRequest(
            request_id="test-json",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "year": 2024}
        )

        record = kosis_source.fetch(request)

        assert record.value is not None
        assert isinstance(record.value, (int, float, list))

    def test_json_parsing_empty_response(self, kosis_source):
        """빈 응답 처리"""
        result = kosis_source._parse_javascript_json('[]')
        assert result == []

    def test_json_parsing_error_response(self, kosis_source):
        """에러 응답 처리"""
        with pytest.raises(SourceNotAvailableError):
            kosis_source._parse_javascript_json('{"err":"20","errMsg":"필수 파라미터 누락"}')

    def test_json_parsing_invalid_json(self, kosis_source):
        """잘못된 JSON 처리"""
        with pytest.raises(SourceNotAvailableError):
            kosis_source._parse_javascript_json('invalid json')

    def test_json_parsing_empty_string(self, kosis_source):
        """빈 문자열 처리"""
        with pytest.raises(SourceNotAvailableError):
            kosis_source._parse_javascript_json('')


class TestKOSISCanHandle:
    """can_handle 메서드 테스트"""

    def test_can_handle_kr_region(self, kosis_source):
        """KR 지역 처리 가능"""
        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR"}
        )

        assert kosis_source.can_handle(request) is True

    def test_can_handle_non_kr_region(self, kosis_source):
        """KR 외 지역 처리 불가"""
        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "US"}
        )

        assert kosis_source.can_handle(request) is False

    def test_can_handle_household_metric(self, kosis_source):
        """가구 메트릭 처리 가능"""
        request = EvidenceRequest(
            request_id="test",
            request_type="metric",
            metric_id="MET-household",
            context={"region": "KR"}
        )

        assert kosis_source.can_handle(request) is True


class TestKOSISEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_future_year_request(self, kosis_source):
        """미래 연도 요청 (데이터 없음)"""
        request = EvidenceRequest(
            request_id="test-future",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "year": 2030}
        )

        try:
            record = kosis_source.fetch(request)
            assert record is not None
        except (DataNotFoundError, SourceNotAvailableError) as e:
            # 미래 연도는 데이터 없음 (예상된 동작)
            assert "데이터가 존재하지 않습니다" in str(e) or "not available" in str(e).lower()
            pytest.skip("Future year data not available (expected)")

    @pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
    def test_old_year_request(self, kosis_source):
        """과거 연도 요청 (2010)"""
        request = EvidenceRequest(
            request_id="test-old",
            request_type="metric",
            metric_id="MET-population",
            context={"region": "KR", "year": 2010}
        )

        record = kosis_source.fetch(request)

        assert record.value > 45_000_000
        print(f"2010년 인구: {record.value:,.0f}명")
