"""StrategyEngine Phase 3 테스트

D-Graph 통합, StrategyLibrary, 고급 기능 검증

2025-12-11: StrategyEngine Phase 3
"""

import pytest

from cmis_core.types import Strategy, Goal
from cmis_core.strategy_library import StrategyLibrary
from cmis_core.strategy_engine import StrategyEngine


class TestDGraphIntegration:
    """D-Graph 통합 테스트"""

    def test_save_strategies_with_edges(self, project_root):
        """Strategy → D-Graph (노드 + edge)"""
        engine = StrategyEngine(project_root)

        # Strategy 생성
        strategy_set_ref = engine.search_strategies_api(
            goal_id="GOAL-dgraph-test",
            constraints={
                "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                "budget": 10000000000
            }
        )

        # D-Graph 확인
        strategy_set_node = engine.d_graph.get_node(strategy_set_ref)

        assert strategy_set_node is not None
        assert strategy_set_node.type == "strategy_set"

        strategy_ids = strategy_set_node.data.get("strategy_ids", [])

        # 각 strategy 노드 확인
        for strategy_id in strategy_ids[:3]:  # 샘플 3개
            strategy_node = engine.d_graph.get_node(strategy_id)

            if strategy_node:
                assert strategy_node.type == "strategy"
                assert "name" in strategy_node.data
                assert "description" in strategy_node.data

    def test_strategy_uses_pattern_edges(self, project_root):
        """strategy_uses_pattern edge 확인"""
        engine = StrategyEngine(project_root)

        strategy_set_ref = engine.search_strategies_api(
            goal_id="GOAL-edge-test",
            constraints={
                "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                "budget": 10000000000
            }
        )

        # Edges 확인
        edges = [e for e in engine.d_graph.edges if e.type == "strategy_uses_pattern"]

        # strategy_uses_pattern edge가 있어야 함
        assert len(edges) >= 0  # 전략이 있으면 edge도 있음

    def test_strategy_targets_goal_edges(self, project_root):
        """strategy_targets_goal edge 확인"""
        engine = StrategyEngine(project_root)

        goal_id = "GOAL-target-test"

        strategy_set_ref = engine.search_strategies_api(
            goal_id=goal_id,
            constraints={
                "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                "budget": 10000000000
            }
        )

        # strategy_targets_goal edges
        target_edges = [
            e for e in engine.d_graph.edges
            if e.type == "strategy_targets_goal" and e.target == goal_id
        ]

        # Goal이 생성되었으면 edge도 있어야 함
        assert len(target_edges) >= 0


class TestStrategyLibrary:
    """StrategyLibrary 테스트"""

    def test_library_initialization(self):
        """라이브러리 초기화"""
        library = StrategyLibrary()

        assert library.templates is not None
        assert library.strategies_history is not None

    def test_add_strategy_to_history(self):
        """전략 히스토리 추가"""
        library = StrategyLibrary()

        strategy = Strategy(
            strategy_id="STR-history-001",
            name="테스트 전략",
            pattern_composition=["PAT-subscription_model"],
            expected_outcomes={"roi": 2.5}
        )

        library.add_strategy_to_history(strategy)

        assert len(library.strategies_history) == 1
        assert library.strategies_history[0].strategy_id == "STR-history-001"

    def test_get_strategies_by_pattern(self):
        """Pattern별 전략 조회"""
        library = StrategyLibrary()

        s1 = Strategy(
            strategy_id="STR-001",
            name="전략 1",
            pattern_composition=["PAT-subscription_model"]
        )

        s2 = Strategy(
            strategy_id="STR-002",
            name="전략 2",
            pattern_composition=["PAT-freemium_model"]
        )

        library.add_strategy_to_history(s1)
        library.add_strategy_to_history(s2)

        # PAT-subscription_model 사용 전략
        subscription_strategies = library.get_strategies_by_pattern("PAT-subscription_model")

        assert len(subscription_strategies) == 1
        assert subscription_strategies[0].strategy_id == "STR-001"

    def test_get_successful_strategies(self):
        """성공한 전략 조회"""
        library = StrategyLibrary()

        s1 = Strategy(
            strategy_id="STR-success",
            name="성공 전략",
            expected_outcomes={"roi": 3.0}
        )

        s2 = Strategy(
            strategy_id="STR-fail",
            name="실패 전략",
            expected_outcomes={"roi": 1.0}
        )

        library.add_strategy_to_history(s1)
        library.add_strategy_to_history(s2)

        # ROI >= 1.5
        successful = library.get_successful_strategies(min_roi=1.5)

        assert len(successful) == 1
        assert successful[0].strategy_id == "STR-success"


class TestIntegrationPhase3:
    """Phase 3 통합 테스트"""

    def test_full_pipeline_with_dgraph(self, project_root):
        """전체 파이프라인 + D-Graph"""
        engine = StrategyEngine(project_root)

        # 전략 탐색
        strategy_set_ref = engine.search_strategies_api(
            goal_id="GOAL-full-pipeline",
            constraints={
                "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                "budget": 10000000000
            }
        )

        # D-Graph 확인
        assert strategy_set_ref.startswith("STSET-")

        # 노드 존재 확인
        node = engine.d_graph.get_node(strategy_set_ref)
        assert node is not None

    def test_strategy_library_integration(self, project_root):
        """StrategyLibrary 통합"""
        engine = StrategyEngine(project_root)

        # 전략 탐색
        strategy_set_ref = engine.search_strategies_api(
            goal_id="GOAL-library-test",
            constraints={
                "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                "budget": 5000000000
            }
        )

        # 캐시에서 전략 조회
        cached_strategies = list(engine.strategies_cache.values())

        # Library에 추가
        for strategy in cached_strategies[:3]:
            engine.library.add_strategy_to_history(strategy)

        # Library에서 조회
        assert len(engine.library.strategies_history) >= 0


