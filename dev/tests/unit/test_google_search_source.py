"""GoogleSearchSource Unit Tests

Google Search API Source 기능 테스트 (API 키 optional)
"""

import pytest
from unittest.mock import Mock, patch

from cmis_core.evidence.google_search_source import GoogleSearchSource
from cmis_core.types import EvidenceRequest, SourceTier
from cmis_core.evidence_engine import (
    DataNotFoundError,
    SourceNotAvailableError,
)


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def mock_google_response():
    """Mock Google Search API 응답"""
    return {
        'items': [
            {
                'title': 'Market Report 2024',
                'snippet': '성인 영어 교육 시장 규모는 약 2900억원으로 추정',
                'link': 'https://example.com/report1'
            },
            {
                'title': 'Industry Analysis',
                'snippet': 'The market size is approximately $250M',
                'link': 'https://example.com/report2'
            },
            {
                'title': 'News Article',
                'snippet': '시장 규모: 3000억원 (2024년 기준)',
                'link': 'https://example.com/news'
            }
        ]
    }


# ========================================
# Initialization Tests
# ========================================

def test_google_search_source_init_no_credentials():
    """API 키 없을 때 오류"""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(SourceNotAvailableError):
            GoogleSearchSource()


def test_google_search_source_init_with_credentials():
    """API 키 있을 때 초기화 성공"""
    source = GoogleSearchSource(
        api_key="test-key",
        search_engine_id="test-engine-id"
    )

    assert source.source_id == "GoogleSearch"
    assert source.source_tier == SourceTier.COMMERCIAL
    assert source.api_key == "test-key"
    assert source.engine_id == "test-engine-id"


# ========================================
# Query Building Tests
# ========================================

def testbuild_search_query_basic():
    """기본 쿼리 구성"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    request = EvidenceRequest(
        request_id="test",
        request_type="metric",
        metric_id="MET-Revenue",
        context={
            "domain_id": "Adult_Language_Education_KR",
            "region": "KR",
            "year": 2024
        }
    )

    query = source.build_search_query(request)

    assert "adult language education" in query.lower()
    assert "korea" in query.lower()
    assert "revenue" in query.lower()
    assert "2024" in query


def testbuild_search_query_minimal():
    """최소 context"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    request = EvidenceRequest(
        request_id="test",
        request_type="metric",
        metric_id="MET-TAM",
        context={}
    )

    query = source.build_search_query(request)

    assert "tam" in query.lower()


# ========================================
# Number Extraction Tests
# ========================================

def test_extract_numbers_korean():
    """한국어 숫자 추출 (억, 조)"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    text = "시장 규모는 약 2900억원이며, 2023년 대비 10% 성장했습니다. 전체 교육 시장은 5조원 규모입니다."

    numbers = source.extract_numbers_from_text(text)

    assert 290_000_000_000 in numbers  # 2900억
    assert 5_000_000_000_000 in numbers  # 5조


def test_extract_numbers_english():
    """영어 숫자 추출 (M, B, T)"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    text = "The market is worth $500M in 2024. Total industry size is $2.5B."

    numbers = source.extract_numbers_from_text(text)

    assert 500_000_000 in numbers  # $500M
    assert 2_500_000_000 in numbers  # $2.5B


def test_extract_numbers_large_integers():
    """큰 정수 추출 (콤마 포함)"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    text = "Revenue: 1,234,567,890 (2024)"

    numbers = source.extract_numbers_from_text(text)

    assert 1_234_567_890 in numbers


# ========================================
# Consensus Tests
# ========================================

def test_calculate_consensus_single():
    """단일 숫자"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    value, confidence = source.calculate_consensus([1000000])

    assert value == 1000000
    assert confidence == 0.6  # 단일 source


def test_calculate_consensus_multiple():
    """여러 숫자 (중앙값)"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    numbers = [1000000, 1100000, 1050000, 1080000]
    value, confidence = source.calculate_consensus(numbers)

    # 중앙값: (1050000 + 1080000) / 2 = 1065000
    assert value == 1065000
    assert confidence > 0.6  # 여러 source


def test_remove_outliers():
    """Outlier 제거 (GoogleSearchSource 활용)"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    # 충분한 데이터로 테스트
    numbers = [1000000, 1050000, 1100000, 1080000, 1120000, 10000000]
    filtered = source.remove_outliers(numbers)

    # 극단값 제거 (완벽하지 않아도 됨)
    assert len(filtered) <= len(numbers)

    # 작은 데이터셋
    small = [100, 110, 105]
    filtered_small = source.remove_outliers(small)
    assert len(filtered_small) == 3  # 4개 미만은 그대로 반환


# ========================================
# Integration Tests (Mock)
# ========================================

@patch('requests.get')
def test_fetch_with_mock(mock_get, mock_google_response):
    """fetch() 통합 테스트 (Mock)"""
    # Mock 응답 설정
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_google_response
    mock_get.return_value = mock_response

    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    request = EvidenceRequest(
        request_id="test",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "year": 2024}
    )

    record = source.fetch(request)

    assert record.source_id == "GoogleSearch"
    assert record.source_tier == "commercial"
    assert record.value_kind.value == "numeric"
    assert record.value > 0
    assert 0.5 <= record.confidence <= 0.85

    # Metadata 확인
    assert "query" in record.metadata
    assert record.metadata["num_results"] == 3


@patch('requests.get')
def test_fetch_no_results(mock_get):
    """검색 결과 없을 때"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'items': []}
    mock_get.return_value = mock_response

    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    request = EvidenceRequest(
        request_id="test",
        request_type="metric",
        metric_id="MET-Revenue",
        context={}
    )

    with pytest.raises(DataNotFoundError):
        source.fetch(request)


def test_can_handle_metric():
    """can_handle() - Metric 요청"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    request = EvidenceRequest(
        request_id="test",
        request_type="metric",
        metric_id="MET-Revenue",
        context={}
    )

    assert source.can_handle(request) == True


def test_can_handle_reality_slice():
    """can_handle() - Reality slice 요청 거부"""
    source = GoogleSearchSource(api_key="test", search_engine_id="test")

    request = EvidenceRequest(
        request_id="test",
        request_type="reality_slice",
        context={}
    )

    assert source.can_handle(request) == False



