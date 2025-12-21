"""LLM Query Generator - 동적 다국어 쿼리 생성

LLM 기반 검색 쿼리 동적 생성 (한국어, 영어, 일본어 등)

2025-12-10: Search Strategy v2.0
"""

from __future__ import annotations

from typing import Dict, List, Optional

from cmis_core.config import CMISConfig
from cmis_core.types import SearchContext
from cmis_core.llm.service import LLMService, create_llm_service
from cmis_core.llm.types import CMISTaskType


class LLMQueryGenerator:
    """LLM 기반 동적 쿼리 생성

    핵심:
    - Dictionary 아님 (무한 확장)
    - Context 이해
    - 다국어 지원 (한/영/일/중)
    - 도메인 적응
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        *,
        llm_mode: str = "mock",
        config: Optional[CMISConfig] = None,
    ) -> None:
        """
        Args:
            llm_service: LLM 서비스 (None이면 create_llm_service로 생성)
            llm_mode: create_llm_service mode ("mock" 권장: 테스트/무네트워크)
            config: CMISConfig (None이면 기본 로드)
        """
        if llm_service is None:
            llm_service = create_llm_service(config=config, mode=llm_mode)

        self.llm_service = llm_service

    def generate_multilingual_queries(
        self,
        context: SearchContext,
        languages: List[str] = None,
        num_per_language: int = 3
    ) -> Dict[str, List[str]]:
        """다국어 쿼리 동적 생성

        Args:
            context: SearchContext
            languages: 생성할 언어 리스트 (None이면 auto)
            num_per_language: 언어당 쿼리 개수

        Returns:
            {
                "ko": ["쿼리1", "쿼리2", ...],
                "en": ["query1", "query2", ...]
            }
        """
        # 언어 결정
        if languages is None:
            languages = self._determine_languages(context)

        # 언어별 쿼리 생성
        queries = {}

        for lang in languages:
            queries[lang] = self._generate_for_language(
                context,
                lang,
                num_per_language
            )

        return queries

    def _determine_languages(self, context: SearchContext) -> List[str]:
        """Context에서 언어 결정"""
        if context.language != "auto":
            return [context.language]

        # Region 기반
        if context.region in ["KR", "한국"]:
            return ["ko", "en"]  # 한국어 + 영어
        elif context.region in ["JP", "일본"]:
            return ["ja", "en"]
        elif context.region in ["CN", "중국"]:
            return ["zh", "en"]
        else:
            return ["en"]

    def _generate_for_language(
        self,
        context: SearchContext,
        language: str,
        num_queries: int
    ) -> List[str]:
        """특정 언어로 쿼리 생성

        Args:
            context: SearchContext
            language: "ko", "en", "ja", "zh"
            num_queries: 생성할 개수

        Returns:
            쿼리 리스트
        """
        # 프롬프트 구성
        prompt = self._build_prompt(context, language, num_queries)

        response_schema = {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "rationale": {"type": "string"},
                            "target_source": {"type": "string"},
                        },
                    },
                }
            },
        }

        # LLM 호출 (실패/빈 결과 시 fallback)
        try:
            response = self.llm_service.call_structured(
                task_type=CMISTaskType.VALIDATION_SANITY_CHECK,
                prompt=prompt,
                schema=response_schema,
                context={
                    "domain_id": context.domain_id,
                    "region": context.region,
                    "metric_id": context.metric_id,
                    "year": context.year,
                    "language": language,
                },
            )

            queries: List[str] = []
            if isinstance(response, dict):
                raw_queries = response.get("queries", [])
                if isinstance(raw_queries, list):
                    for q in raw_queries:
                        if isinstance(q, dict):
                            qq = q.get("query")
                            if isinstance(qq, str) and qq.strip():
                                queries.append(qq.strip())

            if not queries:
                return [self._build_fallback_query(context, language)]

            cap = max(1, int(num_queries))
            return queries[:cap]

        except Exception as e:
            print(f"LLM query generation failed: {e}")
            return [self._build_fallback_query(context, language)]

    def _build_prompt(
        self,
        context: SearchContext,
        language: str,
        num_queries: int
    ) -> str:
        """프롬프트 구성 (언어별)"""

        if language == "ko":
            return f"""
한국 시장 리서치를 위한 최적의 검색 쿼리를 {num_queries}개 생성하세요.

Context:
- 산업/도메인: {context.domain_id}
- 지역: {context.region}
- 찾는 지표: {context.metric_id}
- 연도: {context.year}

다음 목표로 쿼리를 생성하세요:
1. 시장 조사 리포트
2. 산업 통계 자료
3. 경쟁사 실적
4. 정부 통계/발표
5. 언론 보도

각 쿼리는:
- 구체적이어야 함 (산업 용어 사용)
- 숫자 데이터(매출, 시장 규모, 성장률 등)를 포함할 가능성이 높아야 함
- 서로 다른 각도에서 접근 (시장 전체 vs 경쟁사 vs 정부 통계)

한국어로 자연스럽게 작성하되, 검색 효율을 최대화하세요.

JSON 형식으로 반환:
{{
  "queries": [
    {{"query": "...", "rationale": "...", "target_source": "..."}},
    ...
  ]
}}
"""

        elif language == "en":
            return f"""
Generate {num_queries} optimal search queries for market research.

Context:
- Industry/Domain: {context.domain_id}
- Region: {context.region}
- Target Metric: {context.metric_id}
- Year: {context.year}

Target sources:
1. Market research reports
2. Industry statistics
3. Competitor financials
4. Government data
5. News/press releases

Each query should:
- Be specific (use industry terminology)
- Target numeric data (revenue, market size, growth rates)
- Take different approaches (market-wide vs competitors vs government)

Optimize for search engine effectiveness.

Return as JSON:
{{
  "queries": [
    {{"query": "...", "rationale": "...", "target_source": "..."}},
    ...
  ]
}}
"""

        else:
            # 기타 언어 (ja, zh 등)
            return f"Generate {num_queries} search queries for {context.metric_id} in {context.domain_id}, {context.region}, {context.year}"

    def _build_fallback_query(self, context: SearchContext, language: str) -> str:
        """Fallback 쿼리 (LLM 실패 시)"""

        if language == "ko":
            return f"{context.domain_id} {context.region} 시장 규모 {context.year}"
        else:
            return f"{context.domain_id} {context.region} market size {context.year}"


