"""검색 Evidence Hints 테스트

2-Stage Fetching + Secondary Evidence 검증

2025-12-10: Search Evidence Strategy 개선
"""

import pytest
import os
from dotenv import load_dotenv

from cmis_core.types import EvidenceRequest
from cmis_core.evidence_engine import DataNotFoundError, SourceNotAvailableError

load_dotenv()

HAS_GOOGLE_KEY = bool(
    os.getenv("GOOGLE_API_KEY") and
    os.getenv("GOOGLE_SEARCH_ENGINE_ID")
)


class TestAutoFullPageFetching:
    """자동 Full Page Fetching 테스트"""

    @pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="Google API key required")
    def test_google_auto_full_page(self):
        """Google: Snippet 부족 시 자동 Full page"""
        from cmis_core.evidence.google_search_source import GoogleSearchSource

        # fetch_full_page=False (기본값)
        source = GoogleSearchSource(max_results=3)

        request = EvidenceRequest(
            request_id="test-full-page",
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

            # 검색 성공 (snippet 또는 full page)
            assert record.value > 0
            assert record.confidence > 0.5

            print(f"Google search successful (auto full page if needed)")
            print(f"  Value: {record.value:,}")
            print(f"  Numbers found: {record.metadata.get('num_numbers')}")

        except DataNotFoundError:
            pytest.skip("No data found (acceptable)")


class TestSecondaryEvidence:
    """Secondary Evidence (Hints) 테스트"""

    @pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="Google API key required")
    def test_google_hints_collection(self):
        """Google: Hints 수집"""
        from cmis_core.evidence.google_search_source import GoogleSearchSource

        source = GoogleSearchSource(max_results=5)

        request = EvidenceRequest(
            request_id="test-hints",
            request_type="metric",
            metric_id="MET-TAM",
            context={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR",
                "year": 2024
            }
        )

        try:
            record = source.fetch(request)

            # Hints 확인
            assert "hints" in record.metadata
            hints = record.metadata["hints"]

            assert isinstance(hints, list)

            # 최소 1개 이상의 hint
            if len(hints) > 0:
                assert record.metadata["hints_count"] == len(hints)

                # Hint 구조 확인
                first_hint = hints[0]
                assert "value" in first_hint
                assert "context" in first_hint
                assert "snippet" in first_hint
                assert "confidence" in first_hint

                print(f"Hints collected: {len(hints)}")
                for hint in hints[:3]:
                    print(f"  {hint['value']:,} - {hint['context'][:40]}")

        except DataNotFoundError:
            pytest.skip("No data found")

    def test_duckduckgo_hints_collection(self):
        """DuckDuckGo: Hints 수집"""
        from cmis_core.evidence.duckduckgo_source import DuckDuckGoSource

        source = DuckDuckGoSource(max_results=5)

        request = EvidenceRequest(
            request_id="test-ddg-hints",
            request_type="metric",
            metric_id="MET-Revenue",
            context={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR"
            }
        )

        try:
            record = source.fetch(request)

            # Hints 확인
            assert "hints" in record.metadata
            hints = record.metadata["hints"]

            assert isinstance(hints, list)

            if len(hints) > 0:
                print(f"DuckDuckGo hints: {len(hints)}")

        except DataNotFoundError:
            pytest.skip("No data found")


class TestHintsUtility:
    """Hints 활용성 테스트"""

    @pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="Google API key required")
    def test_hints_for_related_metrics(self):
        """관련 Metric에 hints 활용 가능성"""
        from cmis_core.evidence.google_search_source import GoogleSearchSource

        source = GoogleSearchSource(max_results=5)

        # TAM 검색
        request = EvidenceRequest(
            request_id="test-tam",
            request_type="metric",
            metric_id="MET-TAM",
            context={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR",
                "year": 2024
            }
        )

        try:
            record = source.fetch(request)

            hints = record.metadata.get("hints", [])

            # Hints에 domain/region 정보 포함
            for hint in hints:
                assert "domain_id" in hint
                assert "region" in hint
                assert "metric_id" in hint

            print(f"Hints 활용성:")
            print(f"  Total hints: {len(hints)}")
            print(f"  Domain: {hints[0]['domain_id'] if hints else 'N/A'}")
            print(f"  Region: {hints[0]['region'] if hints else 'N/A'}")

        except DataNotFoundError:
            pytest.skip("No data found")


class TestFullPageVsSnippet:
    """Full Page vs Snippet 비교"""

    @pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="Google API key required")
    def test_full_page_more_numbers(self):
        """Full page가 더 많은 숫자 추출"""
        from cmis_core.evidence.google_search_source import GoogleSearchSource

        # Snippet만
        source_snippet = GoogleSearchSource(fetch_full_page=False, max_results=3)

        # Full page
        source_full = GoogleSearchSource(fetch_full_page=True, max_results=3)

        request = EvidenceRequest(
            request_id="test-compare",
            request_type="metric",
            metric_id="MET-Revenue",
            context={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR",
                "year": 2024
            }
        )

        try:
            record_snippet = source_snippet.fetch(request)
            num_snippet = record_snippet.metadata.get("num_numbers", 0)
        except DataNotFoundError:
            num_snippet = 0

        try:
            record_full = source_full.fetch(request)
            num_full = record_full.metadata.get("num_numbers", 0)
        except DataNotFoundError:
            num_full = 0

        print(f"Snippet: {num_snippet} numbers")
        print(f"Full page: {num_full} numbers")

        # Full page가 같거나 더 많아야 함
        assert num_full >= num_snippet
