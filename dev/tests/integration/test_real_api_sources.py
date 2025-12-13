"""실제 API 호출 테스트

KOSIS, Google Search, DuckDuckGo 실제 API 호출 검증

주의: API 키가 .env에 설정되어 있어야 실행됨
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

# API 키 확인
HAS_GOOGLE_KEY = bool(
    os.getenv("GOOGLE_API_KEY") and
    os.getenv("GOOGLE_SEARCH_ENGINE_ID")
)
HAS_KOSIS_KEY = bool(os.getenv("KOSIS_API_KEY"))
HAS_DUCKDUCKGO = True  # API 키 불필요


# ========================================
# KOSIS Tests (API 키 필요)
# ========================================

@pytest.mark.skipif(not HAS_KOSIS_KEY, reason="KOSIS_API_KEY not found")
def test_kosis_source_real_api():
    """KOSIS 실제 API 호출"""
    from cmis_core.evidence.kosis_source import KOSISSource

    source = KOSISSource()

    request = EvidenceRequest(
        request_id="test-kosis",
        request_type="metric",
        metric_id="MET-N_customers",
        context={"region": "KR", "year": 2024}
    )

    try:
        record = source.fetch(request)

        print(f"\nKOSIS 결과:")
        print(f"  Value: {record.value:,}")
        print(f"  Confidence: {record.confidence}")
        print(f"  Source: {record.source_id}")
        print(f"  Metadata: {record.metadata}")

        assert record.source_id == "KOSIS"
        assert record.source_tier == "official"
        assert record.confidence >= 0.9  # 공식 통계

    except (DataNotFoundError, SourceNotAvailableError) as e:
        pytest.skip(f"KOSIS API unavailable: {e}")


# ========================================
# Google Search Tests (API 키 필요)
# ========================================

@pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="Google API credentials not found")
def test_google_search_real_api():
    """Google Search 실제 API 호출"""
    from cmis_core.evidence.google_search_source import GoogleSearchSource

    source = GoogleSearchSource()

    request = EvidenceRequest(
        request_id="test-google",
        request_type="metric",
        metric_id="MET-Revenue",
        context={
            "domain_id": "Adult_Language_Education_KR",
            "region": "KR",
            "year": 2024
        }
    )

    try:
        record = source.fetch(request)

        print(f"\nGoogle Search 결과:")
        print(f"  Value: {record.value:,}")
        print(f"  Confidence: {record.confidence}")
        print(f"  Query: {record.metadata.get('query')}")
        print(f"  Num results: {record.metadata.get('num_results')}")

        assert record.source_id == "GoogleSearch"
        assert record.source_tier == "commercial"
        assert 0.5 <= record.confidence <= 0.85
        assert record.value > 0

    except (DataNotFoundError, SourceNotAvailableError) as e:
        pytest.skip(f"Google Search failed: {e}")


@pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="Google API credentials not found")
def test_google_search_number_extraction():
    """Google Search 숫자 추출 검증"""
    from cmis_core.evidence.google_search_source import GoogleSearchSource

    source = GoogleSearchSource(max_results=3)

    # 간단한 쿼리로 테스트
    request = EvidenceRequest(
        request_id="test",
        request_type="metric",
        metric_id="MET-TAM",
        context={"region": "KR", "year": 2024}
    )

    try:
        record = source.fetch(request)

        # 메타데이터 확인
        assert "num_numbers" in record.metadata
        assert record.metadata["num_numbers"] > 0

    except (DataNotFoundError, SourceNotAvailableError) as e:
        pytest.skip(f"Google Search unavailable: {e}")


# ========================================
# DuckDuckGo Tests (API 키 불필요)
# ========================================

@pytest.mark.skipif(not HAS_DUCKDUCKGO, reason="duckduckgo-search not installed")
def test_duckduckgo_source_real_search():
    """DuckDuckGo 실제 검색"""
    from cmis_core.evidence.duckduckgo_source import DuckDuckGoSource

    try:
        source = DuckDuckGoSource(max_results=3)
    except SourceNotAvailableError:
        pytest.skip("duckduckgo-search package not installed")

    request = EvidenceRequest(
        request_id="test-ddg",
        request_type="metric",
        metric_id="MET-Revenue",
        context={
            "domain_id": "Adult_Language_Education_KR",
            "region": "KR"
        }
    )

    try:
        record = source.fetch(request)

        print(f"\nDuckDuckGo 결과:")
        print(f"  Value: {record.value:,}")
        print(f"  Confidence: {record.confidence}")
        print(f"  Query: {record.metadata.get('query')}")

        assert record.source_id == "DuckDuckGo"
        assert record.source_tier == "commercial"
        assert 0.45 <= record.confidence <= 0.80
        assert record.value > 0

    except (DataNotFoundError, SourceNotAvailableError) as e:
        pytest.skip(f"DuckDuckGo search failed: {e}")


# ========================================
# 비교 테스트
# ========================================

@pytest.mark.skipif(
    not (HAS_GOOGLE_KEY and HAS_DUCKDUCKGO),
    reason="Both Google and DuckDuckGo required"
)
def test_compare_google_vs_duckduckgo():
    """Google vs DuckDuckGo 비교"""
    from cmis_core.evidence.google_search_source import GoogleSearchSource
    from cmis_core.evidence.duckduckgo_source import DuckDuckGoSource

    request = EvidenceRequest(
        request_id="test-compare",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "year": 2024}
    )

    google_record = None
    ddg_record = None

    try:
        google_source = GoogleSearchSource(max_results=3)
        google_record = google_source.fetch(request)
    except (DataNotFoundError, SourceNotAvailableError):
        pass

    try:
        ddg_source = DuckDuckGoSource(max_results=3)
        ddg_record = ddg_source.fetch(request)
    except (DataNotFoundError, SourceNotAvailableError):
        pass

    if google_record and ddg_record:
        print(f"\n비교 결과:")
        print(f"  Google:      {google_record.value:,} (confidence: {google_record.confidence:.2f})")
        print(f"  DuckDuckGo:  {ddg_record.value:,} (confidence: {ddg_record.confidence:.2f})")

        # 두 소스 모두 작동하면 OK (신뢰도 비교는 query에 따라 다를 수 있음)
        assert google_record.confidence > 0.5
        assert ddg_record.confidence > 0.5

    else:
        pytest.skip("Not enough data for comparison")


# ========================================
# 통합 테스트
# ========================================

def test_api_sources_availability():
    """API Source 가용성 체크"""
    results = {
        "GOOGLE": HAS_GOOGLE_KEY,
        "KOSIS": HAS_KOSIS_KEY,
        "DUCKDUCKGO": HAS_DUCKDUCKGO
    }

    print(f"\nAPI Source 가용성:")
    for name, available in results.items():
        status = "OK" if available else "FAIL"
        print(f"  {name}: {status}")

    # 최소 1개는 사용 가능해야 함
    assert any(results.values()), "No API sources available"

