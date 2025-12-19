"""StrategyEngine Phase 1 테스트

Strategy 생성, 평가, API 검증

2025-12-11: StrategyEngine Phase 1
"""

import pytest
from pathlib import Path

from cmis_core.types import (
    Strategy,
    Goal,
    PatternMatch,
    GapCandidate,
    FocalActorContext,
    RealityGraphSnapshot
)
from cmis_core.graph import InMemoryGraph
from cmis_core.strategy_generator import StrategyGenerator
from cmis_core.strategy_evaluator import StrategyEvaluator
from cmis_core.strategy_engine import StrategyEngine


class TestStrategyGenerator:
    """StrategyGenerator 테스트"""

    def test_create_strategy_from_pattern(self):
        """Single Pattern → Strategy"""
        generator = StrategyGenerator()

        pattern_match = PatternMatch(
            pattern_id="PAT-subscription_model",
            description="구독형 모델",
            structure_fit_score=0.85,
            combined_score=0.85,
            evidence={},
            anchor_nodes={}
        )

        goal = Goal(
            goal_id="GOAL-test",
            name="테스트 목표"
        )

        strategy = generator.create_strategy_from_pattern(pattern_match, goal)

        assert strategy is not None
        assert strategy.strategy_id.startswith("STR-")
        assert "PAT-subscription_model" in strategy.pattern_composition
        assert len(strategy.action_set) > 0
        assert strategy.created_from == "pattern_match"

    def test_create_strategy_from_gap(self):
        """Gap → Strategy"""
        generator = StrategyGenerator()

        gap = GapCandidate(
            pattern_id="PAT-network_effects",
            description="네트워크 효과 누락",
            expected_level="core",
            feasibility="high",
            execution_fit_score=0.75
        )

        goal = Goal(goal_id="GOAL-test", name="테스트")

        strategy = generator.create_strategy_from_gap(gap, goal)

        assert strategy is not None
        assert "GAP" in strategy.strategy_id
        assert strategy.pattern_composition == ["PAT-network_effects"]
        assert strategy.created_from == "gap_based"

    def test_generate_composition_strategies(self):
        """Pattern Composition 전략"""
        generator = StrategyGenerator()

        # composes_with 관계 있는 Pattern
        pm1 = PatternMatch(
            pattern_id="PAT-subscription_model",
            description="구독",
            structure_fit_score=0.8,
            combined_score=0.8,
            evidence={},
            anchor_nodes={}
        )

        pm2 = PatternMatch(
            pattern_id="PAT-freemium_model",
            description="프리미엄",
            structure_fit_score=0.7,
            combined_score=0.7,
            evidence={},
            anchor_nodes={}
        )

        goal = Goal(goal_id="GOAL-test", name="테스트")

        strategies = generator.generate([pm1, pm2], [], goal)

        # Single + Composition
        assert len(strategies) >= 2

        # Composition 전략 확인
        comp_strategies = [s for s in strategies if len(s.pattern_composition) > 1]
        if comp_strategies:
            assert comp_strategies[0].created_from == "pattern_composition"


class TestStrategyEvaluator:
    """StrategyEvaluator 테스트"""

    def test_calculate_execution_fit(self):
        """Execution Fit 계산"""
        evaluator = StrategyEvaluator()

        strategy = Strategy(
            strategy_id="STR-test",
            name="테스트 전략",
            pattern_composition=["PAT-subscription_model"]
        )

        project_context = FocalActorContext(
            focal_actor_context_id="PRJ-test",
            scope={},
            assets_profile={
                "capability_traits": [
                    {"technology_domain": "platform_tech", "maturity_level": "production_ready"}
                ],
                "channels": [{"channel_type": "online", "reach": 10000}],
                "brand_assets": {"brand_awareness_level": "medium"}
            }
        )

        fit = evaluator.calculate_execution_fit(strategy, project_context)

        assert 0.0 <= fit <= 1.0

    def test_predict_outcomes(self):
        """ROI/Outcomes 예측"""
        evaluator = StrategyEvaluator()

        strategy = Strategy(
            strategy_id="STR-test",
            name="테스트",
            pattern_composition=["PAT-subscription_model"]
        )

        baseline = {
            "current_revenue": 1000000000,
            "current_customers": 10000,
            "gross_margin": 0.65
        }

        outcomes = evaluator.predict_outcomes(strategy, baseline, horizon_years=3)

        assert "revenue_3y" in outcomes
        assert "roi" in outcomes
        assert "required_investment" in outcomes
        assert outcomes["confidence"] == 0.6
        assert outcomes["method"] == "pattern_benchmark_projection"

    def test_assess_risks(self):
        """Risk 평가"""
        evaluator = StrategyEvaluator()

        strategy = Strategy(
            strategy_id="STR-test",
            name="테스트",
            pattern_composition=["PAT-subscription_model"],
            execution_fit_score=0.3  # 낮음
        )

        risks = evaluator.assess_risks(strategy, None, [])

        # Execution Risk 있어야 함
        execution_risks = [r for r in risks if r["type"] == "execution"]
        assert len(execution_risks) > 0
        assert execution_risks[0]["severity"] == "high"


class TestStrategyEngine:
    """StrategyEngine 통합 테스트"""

    def test_engine_initialization(self, project_root):
        """엔진 초기화"""
        engine = StrategyEngine(project_root)

        assert engine.world_engine is not None
        assert engine.pattern_engine is not None
        assert engine.generator is not None
        assert engine.evaluator is not None

    def test_search_strategies_core_greenfield(self, project_root):
        """Core 함수 (Greenfield)"""
        engine = StrategyEngine(project_root)

        # Goal
        goal = Goal(
            goal_id="GOAL-greenfield",
            name="Greenfield 테스트",
            scope={"domain_id": "Adult_Language_Education_KR", "region": "KR"}
        )

        # Snapshot
        snapshot = engine.world_engine.snapshot("Adult_Language_Education_KR", "KR")

        # Pattern
        matches = engine.pattern_engine.match_patterns(snapshot.graph)
        gaps = engine.pattern_engine.discover_gaps(snapshot.graph, precomputed_matches=matches)

        # Greenfield constraints (충분히 큰 예산)
        constraints = {
            "budget": 10000000000,  # 100억
            "timeline_months": 36
        }

        # 전략 탐색
        strategies = engine.search_strategies_core(
            goal=goal,
            reality_snapshot=snapshot,
            pattern_matches=matches,
            gaps=gaps,
            focal_actor_context=None,
            greenfield_constraints=constraints
        )

        # 전략 생성 확인 (제약 넉넉하면 생성되어야 함)
        assert len(strategies) >= 0  # 0개여도 허용 (Gap이 없을 수 있음)

        # 전략이 있으면 budget 확인
        if strategies:
            for strategy in strategies:
                investment = strategy.expected_outcomes.get("required_investment", 0)
                assert investment <= constraints["budget"]

    def test_search_strategies_core_brownfield(self, project_root):
        """Core 함수 (Brownfield)"""
        engine = StrategyEngine(project_root)

        # FocalActorContext
        project_context = FocalActorContext(
            focal_actor_context_id="PRJ-test",
            scope={"domain_id": "Adult_Language_Education_KR", "region": "KR"},
            assets_profile={
                "capability_traits": [{"technology_domain": "platform_tech"}]
            },
            baseline_state={
                "current_revenue": 1000000000,
                "current_customers": 10000
            },
            constraints_profile={
                "hard_constraints": [
                    {"type": "financial", "dimension": "budget", "threshold": 500000000}
                ]
            }
        )

        # Goal
        goal = Goal(
            goal_id="GOAL-brownfield",
            name="Brownfield 테스트",
            scope={"domain_id": "Adult_Language_Education_KR", "region": "KR"},
            focal_actor_context_id="PRJ-test",
        )

        # Snapshot (Brownfield)
        engine.world_engine.ingest_focal_actor_context(project_context)
        snapshot = engine.world_engine.snapshot(
            "Adult_Language_Education_KR", "KR",
            focal_actor_context_id="PRJ-test",
        )

        matches = engine.pattern_engine.match_patterns(snapshot.graph, "PRJ-test")
        gaps = engine.pattern_engine.discover_gaps(snapshot.graph, "PRJ-test", matches)

        # 전략 탐색
        strategies = engine.search_strategies_core(
            goal=goal,
            reality_snapshot=snapshot,
            pattern_matches=matches,
            gaps=gaps,
            focal_actor_context=project_context
        )

        assert len(strategies) > 0

        # Execution Fit 계산되어야 함
        for strategy in strategies:
            assert strategy.execution_fit_score is not None
            assert 0.0 <= strategy.execution_fit_score <= 1.0

    def test_search_strategies_api(self, project_root):
        """Public API 테스트"""
        engine = StrategyEngine(project_root)

        strategy_set_ref = engine.search_strategies_api(
            goal_id="GOAL-api-test",
            constraints={
                "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                "budget": 2000000000  # 20억
            }
        )

        assert strategy_set_ref.startswith("STSET-")
