"""Search Planner - 검색 계획 수립

Metric/DataSource/Policy 기반 SearchPlan 생성

2025-12-10: Search Strategy v2.0
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from cmis_core.types import MetricRequest, SearchContext, SearchPlan, SearchStep
from cmis_core.config import CMISConfig


class SearchPlanner:
    """검색 계획 수립자

    역할:
    - Metric/DataSource/Policy 연계
    - SearchPlan 생성 (언어, 쿼리 수, Source 등)
    - Budget 할당
    """

    def __init__(self, config: CMISConfig):
        """
        Args:
            config: CMIS 설정
        """
        self.config = config
        self.strategy_spec = self._load_search_strategy_spec()

    def _load_search_strategy_spec(self) -> Dict:
        """search_strategy_spec.yaml 로딩"""
        config_path = self.config.project_root / "config" / "search_strategy_spec.yaml"

        if not config_path.exists():
            return {}

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def build_plan(
        self,
        metric_request: MetricRequest,
        policy_ref: str = "decision_balanced"
    ) -> SearchPlan:
        """SearchPlan 생성

        Args:
            metric_request: Metric 요청
            policy_ref: 정책 모드

        Returns:
            SearchPlan
        """
        metric_id = metric_request.metric_id
        context_dict = metric_request.context

        # 1. SearchContext 생성
        search_context = SearchContext(
            domain_id=context_dict.get("domain_id", ""),
            region=context_dict.get("region", "KR"),
            metric_id=metric_id,
            year=context_dict.get("year", 2024),
            language=self._determine_language(context_dict),
            policy_mode=policy_ref,
            segment=context_dict.get("segment")
        )

        # 2. Policy 기본 설정 적용
        policy_defaults = self.strategy_spec.get("policy_defaults", {}).get(policy_ref, {})

        search_context.max_queries = policy_defaults.get("max_queries_per_metric", 5)
        search_context.max_total_time = policy_defaults.get("max_time", 20)

        # 3. Metric 전략 조회
        metric_strategies = self.strategy_spec.get("strategies", {}).get(metric_id, {})

        if not metric_strategies:
            # Fallback: 기본 전략
            return self._create_generic_plan(search_context)

        # 4. Source별 SearchStep 생성
        steps = []

        per_source = metric_strategies.get("per_source", {})

        for source_id, source_strategy in per_source.items():
            step = self._create_search_step(
                source_id,
                source_strategy,
                search_context,
                policy_ref
            )
            steps.append(step)

        # 5. SearchPlan 생성
        plan = SearchPlan(
            metric_id=metric_id,
            context=search_context,
            steps=steps,
            total_budget={
                "max_queries": search_context.max_queries,
                "max_time": search_context.max_total_time
            }
        )

        return plan

    def _determine_language(self, context: Dict) -> str:
        """언어 결정 (다국어 전략)"""
        region = context.get("region", "")

        # language_strategy에서 조회
        lang_strategy = self.strategy_spec.get("language_strategy", {})

        region_lang = lang_strategy.get(region, {})

        if region_lang:
            # 다국어 지원 지역
            return "auto"  # ko + en 등

        # 기본: 영어
        return "en"

    def _create_search_step(
        self,
        source_id: str,
        source_strategy: Dict,
        context: SearchContext,
        policy_ref: str
    ) -> SearchStep:
        """Source별 SearchStep 생성"""

        # 전략에서 파라미터 추출
        template = source_strategy.get("template", "{domain} {region} {metric} {year}")
        use_llm = source_strategy.get("use_llm", False)
        num_queries = source_strategy.get("num_queries", 1)
        languages = source_strategy.get("languages", ["en"])

        # Policy 기반 조정
        if policy_ref == "reporting_strict":
            # 보수적: LLM 최소화, 쿼리 수 제한
            use_llm = False
            num_queries = min(num_queries, 2)

        elif policy_ref == "exploration_friendly":
            # 공격적: LLM 활용, 쿼리 수 증가
            num_queries = min(num_queries * 2, 10)

        return SearchStep(
            data_source_id=source_id,
            base_query_template=template,
            use_llm_query=use_llm,
            num_queries=num_queries,
            languages=languages,
            timeout_sec=30,
            priority=1
        )

    def _create_generic_plan(self, context: SearchContext) -> SearchPlan:
        """기본 SearchPlan (Fallback)"""

        # GenericWebSearch만 사용
        step = SearchStep(
            data_source_id="GenericWebSearch",
            base_query_template="{domain} {region} {metric} {year}",
            use_llm_query=True,
            num_queries=3,
            languages=["ko", "en"] if context.region == "KR" else ["en"],
            timeout_sec=20,
            priority=1
        )

        return SearchPlan(
            metric_id=context.metric_id,
            context=context,
            steps=[step]
        )


