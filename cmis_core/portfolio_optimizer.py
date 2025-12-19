"""Portfolio Optimizer - Portfolio 구성 및 최적화

여러 Strategy 조합, Synergy/Conflict 분석

2025-12-11: StrategyEngine Phase 2
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from .types import Strategy, PortfolioEvaluation
from .pattern_library import PatternLibrary


class PortfolioOptimizer:
    """Portfolio 최적화

    역할:
    1. Synergy/Conflict 분석
    2. Portfolio 최적화 (Greedy)
    3. 리소스 요구사항 집계
    """

    def __init__(self, pattern_library: Optional[PatternLibrary] = None):
        """
        Args:
            pattern_library: Pattern 라이브러리
        """
        if pattern_library is None:
            pattern_library = PatternLibrary()
            try:
                pattern_library.load_all()
            except Exception:
                pass

        self.pattern_library = pattern_library

    def analyze_synergy(
        self,
        strategy1: Strategy,
        strategy2: Strategy
    ) -> float:
        """두 Strategy 간 시너지 점수

        점수: -1.0 (강한 충돌) ~ +1.0 (강한 시너지)

        Args:
            strategy1: Strategy 1
            strategy2: Strategy 2

        Returns:
            Synergy 점수
        """
        synergy = 0.0

        # 1. Pattern family 일치 (시너지)
        families1 = self._get_pattern_families(strategy1.pattern_composition)
        families2 = self._get_pattern_families(strategy2.pattern_composition)

        common_families = families1 & families2
        synergy += len(common_families) * 0.2

        # 2. composes_with 관계 (강한 시너지)
        for p1_id in strategy1.pattern_composition:
            for p2_id in strategy2.pattern_composition:
                pattern1 = self.pattern_library.get(p1_id)

                if pattern1 and p2_id in pattern1.composes_with:
                    synergy += 0.3

        # 3. conflicts_with 관계 (충돌)
        for p1_id in strategy1.pattern_composition:
            for p2_id in strategy2.pattern_composition:
                pattern1 = self.pattern_library.get(p1_id)

                if pattern1 and p2_id in pattern1.conflicts_with:
                    synergy -= 0.5

        return max(-1.0, min(1.0, synergy))

    def detect_conflicts(
        self,
        strategy1: Strategy,
        strategy2: Strategy
    ) -> Optional[Dict[str, Any]]:
        """충돌 탐지

        Args:
            strategy1, strategy2: Strategy

        Returns:
            Conflict dict 또는 None
        """
        # 1. Pattern conflicts_with
        for p1_id in strategy1.pattern_composition:
            for p2_id in strategy2.pattern_composition:
                pattern1 = self.pattern_library.get(p1_id)

                if pattern1 and p2_id in pattern1.conflicts_with:
                    return {
                        "type": "pattern_conflict",
                        "strategies": [strategy1.strategy_id, strategy2.strategy_id],
                        "patterns": [p1_id, p2_id],
                        "severity": "high",
                        "description": f"{p1_id} conflicts with {p2_id}"
                    }

        # 2. Resource 충돌
        inv1 = strategy1.expected_outcomes.get("required_investment", 0)
        inv2 = strategy2.expected_outcomes.get("required_investment", 0)

        team1 = strategy1.expected_outcomes.get("required_team_size", 0)
        team2 = strategy2.expected_outcomes.get("required_team_size", 0)

        # 팀 overlap
        if team1 + team2 > 100:  # 임계값
            return {
                "type": "resource_conflict",
                "strategies": [strategy1.strategy_id, strategy2.strategy_id],
                "resource": "team",
                "severity": "medium",
                "description": f"팀 규모 합산 {team1 + team2} 과다"
            }

        return None

    def optimize_portfolio_greedy(
        self,
        strategies: List[Strategy],
        budget_constraint: float,
        max_strategies: int = 5
    ) -> List[str]:
        """Greedy Portfolio 최적화

        Args:
            strategies: Strategy 후보
            budget_constraint: 예산 제약
            max_strategies: 최대 전략 수

        Returns:
            선택된 strategy_ids
        """
        # ROI / (1 + Risk) 정렬
        scored = []

        for s in strategies:
            roi = s.expected_outcomes.get("roi", 0)
            risk_score = len(s.risks) / 10
            score = roi / (1 + risk_score)

            scored.append((s, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Greedy 선택
        selected = []
        total_budget = 0

        for strategy, score in scored:
            if len(selected) >= max_strategies:
                break

            required = strategy.expected_outcomes.get("required_investment", 0)

            if total_budget + required <= budget_constraint:
                selected.append(strategy.strategy_id)
                total_budget += required

        return selected

    def aggregate_resource_requirements(
        self,
        strategies: List[Strategy]
    ) -> Dict[str, Any]:
        """리소스 요구사항 집계

        Args:
            strategies: Strategy 리스트

        Returns:
            통합 리소스
        """
        total_investment = 0
        total_team = 0
        max_timeline = 0

        for strategy in strategies:
            outcomes = strategy.expected_outcomes

            total_investment += outcomes.get("required_investment", 0)
            total_team += outcomes.get("required_team_size", 0)
            max_timeline = max(max_timeline, outcomes.get("required_timeline_months", 0))

        return {
            "budget": total_investment,
            "team_size": total_team,
            "timeline_months": max_timeline
        }

    def _get_pattern_families(
        self,
        pattern_ids: List[str]
    ) -> set:
        """Pattern ID → family 세트

        Args:
            pattern_ids: Pattern ID 리스트

        Returns:
            family 세트
        """
        families = set()

        for pattern_id in pattern_ids:
            pattern = self.pattern_library.get(pattern_id)
            if pattern:
                families.add(pattern.family)

        return families
