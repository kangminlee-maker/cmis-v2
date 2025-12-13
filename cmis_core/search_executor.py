"""Search Executor - SearchPlan 실행

SearchPlan을 실행하여 검색 결과 수집

2025-12-10: Search Strategy v2.0
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .types import SearchPlan, SearchStep, SearchContext
from .query_generator_llm import LLMQueryGenerator


@dataclass
class RawSearchResult:
    """원본 검색 결과"""
    query: str
    language: str
    source_id: str
    content: List[Dict[str, Any]]  # 검색 결과 items
    timestamp: str


class SearchExecutor:
    """SearchPlan 실행자

    역할:
    - SearchStep 순차 실행
    - 쿼리 생성 (LLM 또는 템플릿)
    - 다국어 병렬 검색
    - Raw 결과 수집
    """

    def __init__(self):
        """초기화"""
        self.llm_generator = LLMQueryGenerator()

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
        # 실제 검색은 Source에서 수행
        # 여기서는 구조만 정의

        # Phase 2에서 실제 Source 호출 구현
        return None


