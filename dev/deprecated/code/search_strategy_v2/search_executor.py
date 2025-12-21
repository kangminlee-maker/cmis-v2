"""Search Executor - SearchPlan 실행

SearchPlan을 실행하여 검색 결과 수집

2025-12-10: Search Strategy v2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from cmis_core.types import SearchPlan, SearchStep, SearchContext
from .query_generator_llm import LLMQueryGenerator


@dataclass
class RawSearchResult:
    """원본 검색 결과"""
    query: str
    language: str
    source_id: str
    content: List[Dict[str, Any]]  # 검색 결과 items
    timestamp: str


SearchBackend = Callable[[str, str, str, int], List[Dict[str, Any]]]


class SearchExecutor:
    """SearchPlan 실행자

    역할:
    - SearchStep 순차 실행
    - 쿼리 생성 (LLM 또는 템플릿)
    - 다국어 병렬 검색
    - Raw 결과 수집
    """

    def __init__(
        self,
        llm_generator: Optional[LLMQueryGenerator] = None,
        *,
        search_backend: Optional[SearchBackend] = None,
        max_results: int = 5,
    ) -> None:
        """초기화.

        NOTE:
        - SearchStrategy v2는 experimental 상태입니다.
        - 네트워크 호출은 테스트에서 mocking으로 대체할 수 있도록 search_backend injection을 지원합니다.
        """

        self.llm_generator = llm_generator or LLMQueryGenerator()
        self.search_backend = search_backend
        self.max_results = int(max_results)

    def execute(self, plan: SearchPlan) -> List[RawSearchResult]:
        """SearchPlan 실행

        Args:
            plan: SearchPlan

        Returns:
            RawSearchResult 리스트
        """
        all_results = []

        for step in plan.steps:
            # Step별 쿼리 생성 및 실행
            step_results = self._execute_step(step, plan.context)
            all_results.extend(step_results)

        return all_results

    def _execute_step(
        self,
        step: SearchStep,
        context: SearchContext
    ) -> List[RawSearchResult]:
        """단일 SearchStep 실행"""

        results = []

        # 1. 쿼리 생성
        if step.use_llm_query:
            # LLM 동적 생성
            queries_by_lang = self.llm_generator.generate_multilingual_queries(
                context,
                step.languages,
                step.num_queries
            )
        else:
            # 템플릿 기반
            queries_by_lang = self._generate_from_template(step, context)

        # 2. 언어별 검색 실행
        for language, queries in queries_by_lang.items():
            for query in queries:
                try:
                    result = self._execute_single_query(
                        query,
                        language,
                        step.data_source_id,
                        step.timeout_sec
                    )

                    if result:
                        results.append(result)

                except Exception as e:
                    print(f"Query failed: {query[:50]}... - {e}")
                    continue

        return results

    def _generate_from_template(
        self,
        step: SearchStep,
        context: SearchContext
    ) -> Dict[str, List[str]]:
        """템플릿 기반 쿼리 생성"""

        # 템플릿 포매팅
        query = step.base_query_template.format(
            domain=context.domain_id.replace("_", " "),
            region=context.region,
            metric=context.metric_id.replace("MET-", "").replace("_", " "),
            year=context.year
        )

        # 언어별 반환
        result = {}
        for lang in step.languages:
            result[lang] = [query]

        return result

    def _execute_single_query(
        self,
        query: str,
        language: str,
        source_id: str,
        timeout: int
    ) -> Optional[RawSearchResult]:
        """단일 쿼리 실행

        Args:
            query: 검색 쿼리
            language: 언어
            source_id: Data source ID
            timeout: Timeout (초)

        Returns:
            RawSearchResult or None
        """
        ts = datetime.now(timezone.utc).isoformat()

        backend = self.search_backend or self._default_search_backend
        items = backend(query, language, source_id, timeout)
        if not items:
            return None

        return RawSearchResult(
            query=query,
            language=language,
            source_id=source_id,
            content=items,
            timestamp=ts,
        )

    def _default_search_backend(
        self,
        query: str,
        language: str,
        source_id: str,
        timeout: int,
    ) -> List[Dict[str, Any]]:
        """최소 검색 backend (Phase 1.5).

        - ddgs(또는 duckduckgo_search) 설치 시 DuckDuckGo 텍스트 검색을 지원합니다.
        - 그 외/미설치 환경에서는 빈 결과를 반환합니다.
        """

        _ = (language, timeout)  # reserved (future)

        if source_id not in {"GenericWebSearch", "DuckDuckGo", "DuckDuckGoSearch"}:
            return []

        try:
            try:
                from ddgs import DDGS  # type: ignore
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore
        except ImportError:
            return []

        try:
            ddgs = DDGS()
            results = list(ddgs.text(query, max_results=self.max_results))
        except Exception:
            return []

        return [r for r in results if isinstance(r, dict)]


