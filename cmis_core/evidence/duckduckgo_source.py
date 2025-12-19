"""DuckDuckGo Search Source

DuckDuckGo 검색 (v2 리팩토링: BaseSearchSource 활용)
"""

from __future__ import annotations

import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone

from ..types import EvidenceRequest, EvidenceRecord, EvidenceValueKind, SourceTier
from ..evidence_engine import DataNotFoundError, SourceNotAvailableError
from .base_search_source import BaseSearchSource


class DuckDuckGoSource(BaseSearchSource):
    """DuckDuckGo Search Source (간결화)"""

    def __init__(
        self,
        fetch_full_page: bool = False,
        max_results: int = 5,
        timeout: int = 10
    ):
        super().__init__(
            source_id="DuckDuckGo",
            source_tier=SourceTier.COMMERCIAL,
            capabilities={
                "provides": ["market_data", "company_info", "recent_news"],
                "regions": ["*"],
                "data_types": ["numeric"]
            },
            fetch_full_page=fetch_full_page,
            max_results=max_results,
            timeout=timeout
        )

        # DuckDuckGo 초기화
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            self.ddgs = DDGS()
        except ImportError:
            raise SourceNotAvailableError(
                "ddgs package required: pip install ddgs"
            )

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """Evidence 수집 (2-Stage Fetching)"""
        query = self.build_search_query(request)  # Base

        try:
            results = self._search(query)  # DuckDuckGo 전용
        except Exception as e:
            raise SourceNotAvailableError(f"DuckDuckGo failed: {e}")

        if not results:
            raise DataNotFoundError(f"No results")

        # Stage 1: Snippet에서 시도
        numbers = self.extract_numbers(results)  # Base

        # Stage 2: 데이터 없으면 Full page 자동 시도
        if not numbers and not self.fetch_full_page:
            print(f"No numbers in snippets, fetching full pages...")
            results = self._enrich_with_full_content(results)
            numbers = self.extract_numbers(results)

        if not numbers:
            raise DataNotFoundError(f"No numbers")

        # Primary + Hints 추출
        evidence_data = self.extract_all_evidence_with_hints(results, request)

        value = evidence_data["primary"]["value"]
        confidence = evidence_data["primary"]["confidence"]
        hints = evidence_data["hints"]

        if value is None:
            raise DataNotFoundError(f"No numbers")

        # DuckDuckGo는 Google보다 신뢰도 약간 낮음
        confidence = max(0.5, confidence - 0.05)

        # web_search 결과라도, 특정 도메인(컨설팅/증권사 등)에서 온 문서는 상대적으로 신뢰도를 높게 평가합니다.
        trust_scores = [
            float(h.get("source_trust", 0.0))
            for h in (hints or [])
            if isinstance(h, dict)
        ]
        trust_max = max(trust_scores) if trust_scores else 0.0
        if trust_max > 0.0:
            confidence = min(self.get_max_confidence(), confidence + (0.10 * trust_max))

        return EvidenceRecord(
            evidence_id=f"EVD-DuckDuckGo-{uuid.uuid4().hex[:8]}",
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=value,
            value_kind=EvidenceValueKind.NUMERIC,
            schema_ref="duckduckgo_search_v1",
            confidence=confidence,
            metadata={
                "query": query,
                "num_results": len(results),
                "num_numbers": len(evidence_data["all_numbers"]),
                "hints": hints,  # 모든 관련 숫자 저장
                "hints_count": len(hints),
                "source_trust_max": trust_max,
            },
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            lineage={"search_engine": "duckduckgo", "query": query}
        )

    def can_handle(self, request: EvidenceRequest) -> bool:
        """처리 가능 여부"""
        return request.request_type == "metric" and request.metric_id

    # ========================================
    # DuckDuckGo 전용: 검색 API
    # ========================================

    def _search(self, query: str) -> List[Dict[str, Any]]:
        """DuckDuckGo 검색"""
        try:
            results = list(self.ddgs.text(
                query,
                max_results=self.max_results
            ))

            if not results:
                return []

            # 페이지 크롤링 (optional)
            if self.fetch_full_page:
                results = self._enrich_with_full_content(results)

            return results

        except Exception as e:
            raise SourceNotAvailableError(f"DuckDuckGo error: {e}")

    def _enrich_with_full_content(self, results: List[Dict]) -> List[Dict]:
        """페이지 크롤링 (BaseSearchSource 활용)"""
        enriched = []

        for result in results:
            url = result.get('href', '')

            if url:
                content = self.fetch_page_content(url)  # Base
                if content:
                    result['body'] = content
                    result['crawled'] = True

            enriched.append(result)

        return enriched

    # ========================================
    # Override: Confidence 조정
    # ========================================

    def get_base_confidence(self) -> float:
        """DuckDuckGo 기본 confidence (Google보다 낮음)"""
        return 0.45

    def get_max_confidence(self) -> float:
        """최대 confidence"""
        return 0.80
