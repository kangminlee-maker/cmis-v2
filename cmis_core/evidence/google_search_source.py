"""Google Search API Source

Google Custom Search API (v2 리팩토링: BaseSearchSource 활용)
"""

from __future__ import annotations

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

import requests

from ..types import EvidenceRequest, EvidenceRecord, EvidenceValueKind, SourceTier
from ..evidence_engine import DataNotFoundError, SourceNotAvailableError, SourceTimeoutError
from .base_search_source import BaseSearchSource


class GoogleSearchSource(BaseSearchSource):
    """Google Custom Search Source (간결화)"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
        fetch_full_page: bool = False,
        max_results: int = 5,
        timeout: int = 10
    ):
        super().__init__(
            source_id="GoogleSearch",
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
        
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.engine_id = search_engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        
        if not self.api_key or not self.engine_id:
            raise SourceNotAvailableError(
                "Google API credentials required"
            )
    
    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """Evidence 수집"""
        query = self.build_search_query(request)  # Base
        
        try:
            results = self._search(query)  # Google 전용
        except requests.Timeout:
            raise SourceTimeoutError(f"Google timeout")
        except Exception as e:
            raise SourceNotAvailableError(f"Google failed: {e}")
        
        if not results:
            raise DataNotFoundError(f"No results")
        
        numbers = self.extract_numbers(results)  # Base
        
        if not numbers:
            raise DataNotFoundError(f"No numbers")
        
        value, confidence = self.calculate_consensus(numbers)  # Base
        
        return EvidenceRecord(
            evidence_id=f"EVD-GoogleSearch-{uuid.uuid4().hex[:8]}",
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=value,
            value_kind=EvidenceValueKind.NUMERIC,
            schema_ref="google_search_v1",
            confidence=confidence,
            metadata={
                "query": query,
                "num_results": len(results),
                "num_numbers": len(numbers),
            },
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            lineage={"search_engine": "google", "query": query}
        )
    
    def can_handle(self, request: EvidenceRequest) -> bool:
        """처리 가능 여부"""
        if not self.api_key or not self.engine_id:
            return False
        
        return request.request_type == "metric" and bool(request.metric_id)
    
    # ========================================
    # Google 전용: API 호출
    # ========================================
    
    def _search(self, query: str) -> List[Dict[str, Any]]:
        """Google Custom Search API"""
        url = "https://www.googleapis.com/customsearch/v1"
        
        params = {
            'key': self.api_key,
            'cx': self.engine_id,
            'q': query,
            'num': self.max_results,
        }
        
        response = requests.get(url, params=params, timeout=self.timeout)
        
        if response.status_code != 200:
            raise SourceNotAvailableError(f"Google API {response.status_code}")
        
        data = response.json()
        items = data.get('items', [])
        
        # 페이지 크롤링 (optional)
        if self.fetch_full_page:
            items = self._enrich_with_full_content(items)
        
        return items
    
    def _enrich_with_full_content(self, items: List[Dict]) -> List[Dict]:
        """페이지 크롤링 (BaseSearchSource 활용)"""
        enriched = []
        
        for item in items:
            url = item.get('link', '')
            
            if url:
                content = self.fetch_page_content(url)  # Base
                if content:
                    item['full_content'] = content
                    item['crawled'] = True
            
            enriched.append(item)
        
        return enriched
