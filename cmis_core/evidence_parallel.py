"""Evidence Parallel Fetching - 병렬 수집

동일 Tier 내 Source를 병렬로 호출하여 성능 향상

2025-12-10: Evidence Engine v2.2
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

from .types import EvidenceRequest, EvidenceRecord, EvidencePolicy
from .evidence_engine import BaseDataSource


class ParallelFetcher:
    """병렬 Evidence 수집
    
    기능:
    - 같은 Tier 내 Source 병렬 호출
    - ThreadPoolExecutor 사용
    - Early Return 지원
    """
    
    def __init__(self, max_workers: int = 5):
        """
        Args:
            max_workers: 최대 병렬 worker 수
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def fetch_parallel(
        self,
        sources: List[BaseDataSource],
        request: EvidenceRequest,
        policy: EvidencePolicy
    ) -> List[EvidenceRecord]:
        """병렬 수집
        
        Args:
            sources: Source 리스트 (같은 Tier)
            request: Evidence 요청
            policy: 정책
        
        Returns:
            EvidenceRecord 리스트
        """
        # 병렬 호출
        futures = []
        
        for source in sources:
            future = self.executor.submit(
                self._safe_fetch,
                source,
                request
            )
            futures.append((source, future))
        
        # 결과 수집
        results = []
        
        for source, future in futures:
            try:
                record = future.result(timeout=policy.timeout if hasattr(policy, 'timeout') else 30)
                if record:
                    results.append(record)
            except Exception as e:
                print(f"Warning: {source.source_id} failed: {e}")
                continue
        
        return results
    
    def _safe_fetch(
        self,
        source: BaseDataSource,
        request: EvidenceRequest
    ) -> Optional[EvidenceRecord]:
        """안전한 fetch (예외 처리)"""
        try:
            return source.fetch(request)
        except Exception:
            return None
    
    def shutdown(self):
        """Executor 종료"""
        self.executor.shutdown(wait=True)


# ========================================
# Async 버전 (선택적)
# ========================================

class AsyncFetcher:
    """Async Evidence 수집 (고급)
    
    asyncio 기반 비동기 수집
    """
    
    async def fetch_async(
        self,
        sources: List[BaseDataSource],
        request: EvidenceRequest
    ) -> List[EvidenceRecord]:
        """비동기 수집
        
        Args:
            sources: Source 리스트
            request: Evidence 요청
        
        Returns:
            EvidenceRecord 리스트
        """
        # Async tasks 생성
        tasks = [
            self._fetch_task(source, request)
            for source in sources
        ]
        
        # 병렬 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 성공한 것만 필터링
        valid_results = [
            r for r in results
            if isinstance(r, EvidenceRecord)
        ]
        
        return valid_results
    
    async def _fetch_task(
        self,
        source: BaseDataSource,
        request: EvidenceRequest
    ) -> Optional[EvidenceRecord]:
        """단일 fetch task"""
        loop = asyncio.get_event_loop()
        
        # Sync fetch를 async로 실행
        try:
            record = await loop.run_in_executor(
                None,  # Default executor
                source.fetch,
                request
            )
            return record
        except Exception:
            return None
