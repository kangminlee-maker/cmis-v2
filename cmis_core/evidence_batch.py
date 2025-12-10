"""Evidence Batch Fetching - 일괄 수집

여러 Metric을 Source별로 그룹화하여 일괄 수집

2025-12-10: Evidence Engine v2.2
"""

from __future__ import annotations

from typing import List, Dict, Any
from collections import defaultdict

from .types import EvidenceRequest, EvidenceRecord, EvidenceBundle
from .evidence_engine import BaseDataSource, SourceRegistry


class BatchFetcher:
    """Batch Evidence 수집
    
    기능:
    - Source별 요청 그룹화
    - Batch API 지원 Source는 1번 호출
    - 미지원 Source는 순차 호출
    """
    
    def __init__(self, source_registry: SourceRegistry):
        """
        Args:
            source_registry: Source 레지스트리
        """
        self.registry = source_registry
    
    def fetch_batch(
        self,
        requests: List[EvidenceRequest]
    ) -> Dict[str, List[EvidenceRecord]]:
        """일괄 수집
        
        Args:
            requests: EvidenceRequest 리스트
        
        Returns:
            {request_id: [EvidenceRecord, ...]}
        """
        # 1. Source별 그룹화
        grouped = self._group_by_source(requests)
        
        # 2. Source별 수집
        all_results = {}
        
        for source_id, source_requests in grouped.items():
            source = self.registry.get_source_by_id(source_id)
            
            if not source:
                continue
            
            # Batch API 지원 확인
            if hasattr(source, 'fetch_batch'):
                # Batch 호출
                results = source.fetch_batch(source_requests)
            else:
                # 개별 호출
                results = []
                for req in source_requests:
                    try:
                        record = source.fetch(req)
                        results.append((req.request_id, record))
                    except Exception:
                        continue
            
            # 결과 저장
            for req_id, record in results:
                if req_id not in all_results:
                    all_results[req_id] = []
                all_results[req_id].append(record)
        
        return all_results
    
    def _group_by_source(
        self,
        requests: List[EvidenceRequest]
    ) -> Dict[str, List[EvidenceRequest]]:
        """Source별 요청 그룹화
        
        Args:
            requests: EvidenceRequest 리스트
        
        Returns:
            {source_id: [EvidenceRequest, ...]}
        """
        grouped = defaultdict(list)
        
        for request in requests:
            # 각 request에 적합한 source 찾기
            capable_sources = self.registry.find_capable_sources(request)
            
            # 최우선 source 선택 (tier 기준)
            if capable_sources:
                best_source = capable_sources[0]
                grouped[best_source.source_id].append(request)
        
        return dict(grouped)
    
    def estimate_api_calls(
        self,
        requests: List[EvidenceRequest]
    ) -> Dict[str, int]:
        """예상 API 호출 횟수
        
        Args:
            requests: EvidenceRequest 리스트
        
        Returns:
            {
                "without_batch": int,
                "with_batch": int,
                "savings": int
            }
        """
        grouped = self._group_by_source(requests)
        
        without_batch = len(requests)  # 모두 개별 호출
        
        with_batch = 0
        for source_id, source_requests in grouped.items():
            source = self.registry.get_source_by_id(source_id)
            
            if source and hasattr(source, 'fetch_batch'):
                # Batch 지원: 1번 호출
                with_batch += 1
            else:
                # 미지원: 개별 호출
                with_batch += len(source_requests)
        
        return {
            "without_batch": without_batch,
            "with_batch": with_batch,
            "savings": without_batch - with_batch,
            "savings_percent": ((without_batch - with_batch) / without_batch * 100) if without_batch > 0 else 0
        }
