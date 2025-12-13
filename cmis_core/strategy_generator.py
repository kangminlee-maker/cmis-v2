"""Strategy Generator - Pattern 조합 기반 전략 생성

Pattern 매칭/Gap 결과 → Strategy 후보 생성

2025-12-11: StrategyEngine Phase 1
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .types import Strategy, Goal, PatternMatch, GapCandidate
from .pattern_library import PatternLibrary


class StrategyGenerator:
    """전략 생성기

    역할:
    1. Single Pattern → Strategy
    2. Pattern Composition → Strategy
    3. Gap-based → Strategy
    4. Goal 필터링
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

    def generate(
        self,
        pattern_matches: List[PatternMatch],
        gaps: List[GapCandidate],
        goal: Goal
    ) -> List[Strategy]:
        """전략 생성

        프로세스:
        1. Single Pattern 전략
        2. Pattern Composition 전략
        3. Gap-based 전략
        4. Goal 필터링

        Args:
            pattern_matches: 매칭된 Pattern
            gaps: Gap 후보
            goal: 목표

        Returns:
            Strategy 리스트
        """
        strategies = []

        # 1. Single Pattern 전략
        for pm in pattern_matches:
            strategy = self.create_strategy_from_pattern(pm, goal)
            if strategy:
                strategies.append(strategy)

        # 2. Pattern Composition 전략
        composition_strategies = self._generate_composition_strategies(
            pattern_matches,
            goal
        )
        strategies.extend(composition_strategies)

        # 3. Gap-based 전략
        for gap in gaps:
            if gap.feasibility in ["high", "medium"]:
                strategy = self.create_strategy_from_gap(gap, goal)
                if strategy:
                    strategies.append(strategy)

        # 4. Goal 필터링 (간단한 필터)
        strategies = self._filter_by_goal(strategies, goal)

        return strategies

    def create_strategy_from_pattern(
        self,
        pattern_match: PatternMatch,
        goal: Goal
    ) -> Optional[Strategy]:
        """Single Pattern → Strategy

        Args:
            pattern_match: Pattern 매칭 결과
            goal: 목표

        Returns:
            Strategy
        """
        pattern = self.pattern_library.get(pattern_match.pattern_id)

        if not pattern:
            return None

        strategy_id = f"STR-{pattern_match.pattern_id}-{uuid.uuid4().hex[:8]}"

        # Action set 생성 (Pattern traits 기반)
        action_set = self._generate_actions_from_pattern(pattern)

        strategy = Strategy(
            strategy_id=strategy_id,
            name=f"{pattern.name} 전략",
            description=f"{pattern.description} 기반 전략",
            pattern_composition=[pattern_match.pattern_id],
            action_set=action_set,
            expected_outcomes={},  # StrategyEvaluator에서 계산
            created_from="pattern_match",
            source_patterns=[pattern_match.pattern_id],
            lineage={
                "created_at": datetime.now().isoformat(),
                "created_by": "strategy_generator",
                "pattern_match_score": pattern_match.combined_score
            }
        )

        return strategy

    def create_strategy_from_gap(
        self,
        gap: GapCandidate,
        goal: Goal
    ) -> Optional[Strategy]:
        """Gap → Strategy

        Args:
            gap: Gap 후보
            goal: 목표

        Returns:
            Strategy
        """
        pattern = self.pattern_library.get(gap.pattern_id)

        if not pattern:
            return None

        strategy_id = f"STR-GAP-{gap.pattern_id}-{uuid.uuid4().hex[:8]}"

        action_set = self._generate_actions_from_pattern(pattern)

        strategy = Strategy(
            strategy_id=strategy_id,
            name=f"{pattern.name} 구축 전략",
            description=f"Missing {pattern.description} 구축",
            pattern_composition=[gap.pattern_id],
            action_set=action_set,
            expected_outcomes={},
            created_from="gap_based",
            source_patterns=[gap.pattern_id],
            lineage={
                "created_at": datetime.now().isoformat(),
                "created_by": "strategy_generator",
                "gap_feasibility": gap.feasibility,
                "gap_expected_level": gap.expected_level,
                "gap_execution_fit": gap.execution_fit_score
            }
        )

        return strategy

    def _generate_composition_strategies(
        self,
        pattern_matches: List[PatternMatch],
        goal: Goal
    ) -> List[Strategy]:
        """Pattern Composition 전략

        composes_with 관계 기반 조합

        Args:
            pattern_matches: 매칭된 Pattern
            goal: 목표

        Returns:
            조합 전략 리스트
        """
        compositions = []
        matched_ids = {pm.pattern_id for pm in pattern_matches}

        for pm in pattern_matches:
            pattern = self.pattern_library.get(pm.pattern_id)

            if not pattern:
                continue

            # composes_with 확인
            for compose_id in pattern.composes_with:
                if compose_id in matched_ids:
                    # 조합 전략 생성
                    strategy = self._create_composition_strategy(
                        [pm.pattern_id, compose_id],
                        goal
                    )

                    if strategy:
                        compositions.append(strategy)

        return compositions

    def _create_composition_strategy(
        self,
        pattern_ids: List[str],
        goal: Goal
    ) -> Optional[Strategy]:
        """Pattern 조합 전략 생성

        Args:
            pattern_ids: Pattern ID 리스트
            goal: 목표

        Returns:
            Strategy
        """
        patterns = [self.pattern_library.get(pid) for pid in pattern_ids]

        if not all(patterns):
            return None

        strategy_id = f"STR-COMP-{'-'.join(pattern_ids)}-{uuid.uuid4().hex[:8]}"

        # 조합 이름
        pattern_names = [p.name for p in patterns]
        name = " + ".join(pattern_names)

        # Action set (모든 Pattern 통합)
        action_set = []
        for pattern in patterns:
            actions = self._generate_actions_from_pattern(pattern)
            action_set.extend(actions)

        strategy = Strategy(
            strategy_id=strategy_id,
            name=name,
            description=f"{name} 조합 전략",
            pattern_composition=pattern_ids,
            action_set=action_set,
            expected_outcomes={},
            created_from="pattern_composition",
            source_patterns=pattern_ids,
            lineage={
                "created_at": datetime.now().isoformat(),
                "created_by": "strategy_generator",
                "composition_type": "composes_with"
            }
        )

        return strategy

    def _generate_actions_from_pattern(
        self,
        pattern
    ) -> List[Dict[str, Any]]:
        """Pattern → Action set

        Phase 1: 간단한 매핑
        Phase 2: StrategyTemplate 활용

        Args:
            pattern: PatternSpec

        Returns:
            Action 리스트
        """
        actions = []

        # Pattern traits 기반 Action 생성
        trait_constraints = pattern.trait_constraints

        # Money flow traits
        if "money_flow" in trait_constraints:
            mf_traits = trait_constraints["money_flow"].get("required_traits", {})

            # revenue_model
            if "revenue_model" in mf_traits:
                revenue_model = mf_traits["revenue_model"]

                actions.append({
                    "action_type": "설계_가격_모델",
                    "params": {
                        "model": revenue_model,
                        "source_pattern": pattern.pattern_id
                    },
                    "priority": "high"
                })

            # payment_recurs
            if mf_traits.get("payment_recurs"):
                actions.append({
                    "action_type": "구축_결제_인프라",
                    "params": {
                        "recurring": True,
                        "source_pattern": pattern.pattern_id
                    },
                    "priority": "high"
                })

        # 기본 Action (pattern별)
        if not actions:
            actions.append({
                "action_type": f"구현_{pattern.family}",
                "params": {"pattern_id": pattern.pattern_id},
                "priority": "medium"
            })

        return actions

    def _filter_by_goal(
        self,
        strategies: List[Strategy],
        goal: Goal
    ) -> List[Strategy]:
        """Goal 기반 필터링

        Phase 1: 모두 통과
        Phase 2: target_metrics 기반 필터링

        Args:
            strategies: 전략 리스트
            goal: 목표

        Returns:
            필터링된 전략 리스트
        """
        # Phase 1: 간단한 필터
        # 모든 전략 통과 (Evaluator에서 평가)
        return strategies


