"""SearchStrategy v2 (experimental) executor smoke tests.

원칙:
- 외부 네트워크 호출 없이 재현 가능해야 합니다.
- SearchExecutor는 search_backend injection으로 테스트합니다.
"""

from __future__ import annotations

from typing import Any, Dict, List

from cmis_core.experimental.search_strategy_v2.query_generator_llm import LLMQueryGenerator
from cmis_core.experimental.search_strategy_v2.search_executor import SearchExecutor
from cmis_core.types import SearchContext, SearchPlan, SearchStep


def test_llm_query_generator_falls_back_in_mock_mode() -> None:
    gen = LLMQueryGenerator(llm_mode="mock")

    ctx = SearchContext(
        domain_id="adult_language_education",
        region="KR",
        metric_id="MET-Revenue",
        year=2024,
        language="en",
    )

    queries_by_lang = gen.generate_multilingual_queries(ctx, languages=["en"], num_per_language=2)

    assert "en" in queries_by_lang
    assert isinstance(queries_by_lang["en"], list)
    assert len(queries_by_lang["en"]) >= 1
    assert isinstance(queries_by_lang["en"][0], str)
    assert queries_by_lang["en"][0].strip() != ""


def test_search_executor_execute_single_query_with_injected_backend() -> None:
    def backend(query: str, language: str, source_id: str, timeout: int) -> List[Dict[str, Any]]:
        assert query == "korea edtech revenue 2024"
        assert language == "en"
        assert source_id == "GenericWebSearch"
        assert timeout == 10
        return [{"title": "Example", "url": "https://example.com", "snippet": "Revenue 100"}]

    ex = SearchExecutor(search_backend=backend)

    result = ex._execute_single_query(
        query="korea edtech revenue 2024",
        language="en",
        source_id="GenericWebSearch",
        timeout=10,
    )

    assert result is not None
    assert result.query == "korea edtech revenue 2024"
    assert result.language == "en"
    assert result.source_id == "GenericWebSearch"
    assert isinstance(result.timestamp, str)
    assert result.timestamp.strip() != ""
    assert len(result.content) == 1
    assert result.content[0]["title"] == "Example"


def test_search_executor_execute_plan_template_path() -> None:
    def backend(_query: str, _language: str, _source_id: str, _timeout: int) -> List[Dict[str, Any]]:
        return [{"title": "R", "url": "https://example.com"}]

    ctx = SearchContext(
        domain_id="adult_language_education",
        region="KR",
        metric_id="MET-Revenue",
        year=2024,
        language="en",
    )

    step = SearchStep(
        data_source_id="GenericWebSearch",
        base_query_template="{domain} {region} {metric} {year}",
        use_llm_query=False,
        num_queries=1,
        languages=["en"],
        timeout_sec=10,
        priority=1,
    )

    plan = SearchPlan(metric_id="MET-Revenue", context=ctx, steps=[step])

    ex = SearchExecutor(search_backend=backend)
    results = ex.execute(plan)

    assert len(results) == 1
    assert results[0].source_id == "GenericWebSearch"
