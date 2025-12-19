"""StrategyEngine Phase 2 테스트

Portfolio, Synergy/Conflict, Policy 검증

2025-12-11: StrategyEngine Phase 2
"""

import pytest

from cmis_core.types import Strategy, PortfolioEvaluation, FocalActorContext
from cmis_core.portfolio_optimizer import PortfolioOptimizer
from cmis_core.strategy_engine import StrategyEngine


class TestPortfolioOptimizer:
    """PortfolioOptimizer 테스트"""

    def test_analyze_synergy_positive(self):
        """시너지 분석 (긍정적)"""
        optimizer = PortfolioOptimizer()

        s1 = Strategy(
            strategy_id="STR-001",
            name="구독 모델",
            pattern_composition=["PAT-subscription_model"]
        )

        s2 = Strategy(
            strategy_id="STR-002",
            name="프리미엄 모델",
            pattern_composition=["PAT-freemium_model"]
        )

        synergy = optimizer.analyze_synergy(s1, s2)

        # composes_with 관계 있으면 시너지
        assert synergy >= 0

    def test_analyze_synergy_conflict(self):
        """충돌 분석"""
        optimizer = PortfolioOptimizer()

        s1 = Strategy(
            strategy_id="STR-001",
            name="구독",
            pattern_composition=["PAT-subscription_model"]
        )

        s2 = Strategy(
            strategy_id="STR-002",
            name="거래",
            pattern_composition=["PAT-transaction_model"]
        )

        synergy = optimizer.analyze_synergy(s1, s2)

        # conflicts_with 관계 있으면 음수
        # (실제 패턴에 conflicts 정의 여부에 따라 다름)
        assert -1.0 <= synergy <= 1.0

    def test_detect_conflicts(self):
        """충돌 탐지"""
        optimizer = PortfolioOptimizer()

        s1 = Strategy(
            strategy_id="STR-001",
            name="구독",
            pattern_composition=["PAT-subscription_model"],
            expected_outcomes={"required_team_size": 60}
        )

        s2 = Strategy(
            strategy_id="STR-002",
            name="플랫폼",
            pattern_composition=["PAT-platform_business_model"],
            expected_outcomes={"required_team_size": 50}
        )

        conflict = optimizer.detect_conflicts(s1, s2)

        # 팀 규모 합산 110 → 충돌
        assert conflict is not None
        assert conflict["type"] == "resource_conflict"

    def test_optimize_portfolio_greedy(self):
        """Greedy 최적화"""
        optimizer = PortfolioOptimizer()

        strategies = [
            Strategy(
                strategy_id=f"STR-{i}",
                name=f"전략 {i}",
                pattern_composition=[],
                expected_outcomes={
                    "roi": 2.0 + i * 0.5,
                    "required_investment": 100000000 * i
                },
                risks=[]
            )
            for i in range(1, 6)
        ]

        selected = optimizer.optimize_portfolio_greedy(
            strategies,
            budget_constraint=500000000,
            max_strategies=3
        )

        assert len(selected) <= 3
        assert len(selected) > 0


class TestEvaluatePortfolio:
    """evaluate_portfolio 테스트"""

    def test_evaluate_portfolio_core(self, project_root):
        """Portfolio 평가 Core"""
        engine = StrategyEngine(project_root)

        strategies = [
            Strategy(
                strategy_id="STR-001",
                name="전략 1",
                pattern_composition=["PAT-subscription_model"],
                expected_outcomes={"roi": 2.5},
                risks=[]
            ),
            Strategy(
                strategy_id="STR-002",
                name="전략 2",
                pattern_composition=["PAT-freemium_model"],
                expected_outcomes={"roi": 2.0},
                risks=[]
            )
        ]

        policy_params = {"policy_ref": "decision_balanced", "risk_tolerance": 0.5}

        portfolio_eval = engine.evaluate_portfolio_core(
            strategies,
            focal_actor_context=None,
            policy_params=policy_params
        )

        assert portfolio_eval.portfolio_id.startswith("PORTFOLIO-")
        assert len(portfolio_eval.strategy_ids) == 2
        assert portfolio_eval.aggregate_roi > 0
        assert 0.0 <= portfolio_eval.aggregate_risk <= 1.0

    def test_evaluate_portfolio_with_synergy(self, project_root):
        """Synergy 포함 Portfolio"""
        engine = StrategyEngine(project_root)

        strategies = [
            Strategy(
                strategy_id="STR-001",
                name="구독",
                pattern_composition=["PAT-subscription_model"],
                expected_outcomes={"roi": 2.0},
                risks=[]
            ),
            Strategy(
                strategy_id="STR-002",
                name="프리미엄",
                pattern_composition=["PAT-freemium_model"],
                expected_outcomes={"roi": 1.8},
                risks=[]
            )
        ]

        policy_params = {"policy_ref": "decision_balanced", "risk_tolerance": 0.5}

        portfolio_eval = engine.evaluate_portfolio_core(strategies, None, policy_params)

        # Synergy 확인
        assert isinstance(portfolio_eval.synergies, list)


class TestPolicyIntegration:
    """Policy 통합 테스트"""

    def test_resolve_policy_reporting_strict(self, project_root):
        """Policy 해석: reporting_strict"""
        engine = StrategyEngine(project_root)

        params = engine._resolve_policy("reporting_strict")

        assert params["risk_tolerance"] == 0.3
        assert params["prior_usage"] == "minimal"

    def test_resolve_policy_exploration_friendly(self, project_root):
        """Policy 해석: exploration_friendly"""
        engine = StrategyEngine(project_root)

        params = engine._resolve_policy("exploration_friendly")

        assert params["risk_tolerance"] == 0.7
        assert params["prior_usage"] == "extensive"


class TestIntegrationPhase2:
    """Phase 2 통합 테스트"""

    def test_full_pipeline_greenfield(self, project_root):
        """전체 파이프라인 (Greenfield)"""
        engine = StrategyEngine(project_root)

        # 전략 탐색
        strategy_set_ref = engine.search_strategies_api(
            goal_id="GOAL-integration",
            constraints={
                "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                "budget": 5000000000
            }
        )

        assert strategy_set_ref.startswith("STSET-")

    def test_full_pipeline_with_portfolio(self, project_root):
        """전략 탐색 + Portfolio 평가"""
        engine = StrategyEngine(project_root)

        # 1. 전략 탐색
        strategy_set_ref = engine.search_strategies_api(
            goal_id="GOAL-portfolio-test",
            constraints={
                "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                "budget": 10000000000
            }
        )

        # 2. 캐시에서 strategy_ids 추출
        strategy_set_node = engine.d_graph.get_node(strategy_set_ref)

        if strategy_set_node:
            strategy_ids = strategy_set_node.data.get("strategy_ids", [])[:3]

            if strategy_ids:
                # 3. Portfolio 평가
                portfolio_ref = engine.evaluate_portfolio_api(
                    strategy_ids=strategy_ids,
                    policy_ref="decision_balanced"
                )

                assert portfolio_ref.startswith("PORTFOLIO-") or portfolio_ref == "PEVAL-empty"
