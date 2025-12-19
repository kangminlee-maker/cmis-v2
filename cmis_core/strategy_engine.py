"""Strategy Engine - 전략 설계 엔진

Goal/Pattern/Reality/Value 기반 전략 탐색 및 평가

Phase 1: Core Infrastructure + Public API
2025-12-11: StrategyEngine Phase 1
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .types import (
    Strategy,
    Goal,
    PortfolioEvaluation,
    PatternMatch,
    GapCandidate,
    RealityGraphSnapshot,
    FocalActorContext
)
from .graph import InMemoryGraph
from .world_engine import WorldEngine
from .pattern_engine_v2 import PatternEngineV2
from .value_engine import ValueEngine
from .strategy_generator import StrategyGenerator
from .strategy_evaluator import StrategyEvaluator
from .portfolio_optimizer import PortfolioOptimizer
from .strategy_library import StrategyLibrary
from .stores.focal_actor_context_store import FocalActorContextStore


class StrategyEngine:
    """Strategy Engine v1

    역할:
    - Pattern 조합 → Strategy 생성
    - Execution Fit/ROI/Risk 평가
    - Portfolio 최적화

    Phase 1: Core + Public API
    Phase 2: D-Graph 통합, Portfolio 고도화
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Args:
            project_root: 프로젝트 루트
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = Path(project_root)

        # Engines
        self.world_engine = WorldEngine(project_root)
        self.pattern_engine = PatternEngineV2()
        self.value_engine = ValueEngine()

        # D-Graph (Phase 1: 인메모리)
        self.d_graph = InMemoryGraph()

        # Core 컴포넌트
        self.generator = StrategyGenerator()
        self.evaluator = StrategyEvaluator(value_engine=self.value_engine)
        self.optimizer = PortfolioOptimizer()

        # Strategy 저장소
        self.strategies_cache: Dict[str, Strategy] = {}

        # Strategy Library (Phase 3)
        self.library = StrategyLibrary()
        try:
            self.library.load_templates()
        except Exception:
            pass

    def search_strategies_api(
        self,
        goal_id: str,
        constraints: Dict[str, Any],
        focal_actor_context_id: Optional[str] = None,
    ) -> str:
        """Public API (cmis.yaml 대응)

        프로세스:
        1. Goal 로딩 (D-Graph 또는 생성)
        2. FocalActorContext 로딩 (있으면)
        3. World/Pattern Engine 호출
        4. Core search_strategies() 호출
        5. D-Graph 저장
        6. strategy_set_ref 반환

        Args:
            goal_id: Goal ID
            constraints: 제약 조건 (Greenfield용)
            focal_actor_context_id: FocalActorContext ID (Brownfield)

        Returns:
            strategy_set_ref: "STSET-{uuid}"
        """
        # 1. Goal 로딩 (Phase 1: 간단한 생성)
        goal = self._load_or_create_goal(goal_id, constraints)

        # 2. FocalActorContext 로딩 (store-first)
        focal_actor_context: Optional[FocalActorContext] = None
        if focal_actor_context_id:
            focal_actor_context = self._load_focal_actor_context(focal_actor_context_id)

        # 3. World/Pattern Engine 호출
        scope = goal.scope

        snapshot = self.world_engine.snapshot(
            domain_id=scope.get("domain_id", "Unknown"),
            region=scope.get("region", "KR"),
            focal_actor_context_id=focal_actor_context_id,
        )

        matches = self.pattern_engine.match_patterns(
            snapshot.graph,
            focal_actor_context_id=focal_actor_context_id,
        )

        gaps = self.pattern_engine.discover_gaps(
            snapshot.graph,
            focal_actor_context_id=focal_actor_context_id,
            precomputed_matches=matches
        )

        # 4. Core 함수
        greenfield_constraints = constraints if not focal_actor_context else None

        strategies = self.search_strategies_core(
            goal=goal,
            reality_snapshot=snapshot,
            pattern_matches=matches,
            gaps=gaps,
            focal_actor_context=focal_actor_context,
            greenfield_constraints=greenfield_constraints
        )

        # 5. D-Graph 저장 + 캐시
        strategy_set_ref = self._save_strategies_to_d_graph(
            strategies,
            goal_id,
            focal_actor_context_id,
        )

        # 캐시에 저장
        for strategy in strategies:
            self.strategies_cache[strategy.strategy_id] = strategy

        return strategy_set_ref

    def search_strategies_core(
        self,
        goal: Goal,
        reality_snapshot: RealityGraphSnapshot,
        pattern_matches: List[PatternMatch],
        gaps: List[GapCandidate],
        focal_actor_context: Optional[FocalActorContext] = None,
        greenfield_constraints: Optional[Dict[str, Any]] = None
    ) -> List[Strategy]:
        """Core 전략 탐색 (내부 함수)

        Args:
            goal: 목표
            reality_snapshot: R-Graph
            pattern_matches: 매칭된 Pattern
            gaps: Gap 후보
            focal_actor_context: FocalActorContext (Brownfield)
            greenfield_constraints: Greenfield 제약

        Returns:
            Strategy 리스트
        """
        # 1. Strategy 생성
        strategies = self.generator.generate(
            pattern_matches=pattern_matches,
            gaps=gaps,
            goal=goal
        )

        # 2. 평가 먼저 (Constraint 필터링 전에 outcomes 필요)
        for strategy in strategies:
            # Outcomes (필터링에 필요)
            baseline = focal_actor_context.baseline_state if focal_actor_context else {}
            strategy.expected_outcomes = self.evaluator.predict_outcomes(
                strategy,
                baseline_state=baseline,
                horizon_years=int(goal.target_horizon[:-1]) if goal.target_horizon.endswith('y') else 3
            )

        # 3. Constraint 필터링 (outcomes 계산 후)
        if focal_actor_context:
            # Brownfield
            strategies = self._filter_by_brownfield_constraints(
                strategies,
                focal_actor_context.constraints_profile
            )
        elif greenfield_constraints:
            # Greenfield
            strategies = self._filter_by_greenfield_constraints(
                strategies,
                greenfield_constraints
            )

        # 4. 추가 평가 (Execution Fit, Risk, Preference)
        for strategy in strategies:
            # Execution Fit (Brownfield만)
            if focal_actor_context:
                strategy.execution_fit_score = self.evaluator.calculate_execution_fit(
                    strategy,
                    focal_actor_context
                )

            # Risk
            strategy.risks = self.evaluator.assess_risks(
                strategy,
                focal_actor_context,
                pattern_matches
            )

            # Preference (Brownfield만)
            if focal_actor_context and focal_actor_context.preference_profile:
                strategy.adjusted_score = self._adjust_by_preferences(
                    strategy,
                    focal_actor_context.preference_profile
                )

        # 4. 정렬
        if focal_actor_context:
            # Brownfield: Execution Fit × adjusted_score
            strategies.sort(
                key=lambda s: (s.execution_fit_score or 0) * (s.adjusted_score or s.execution_fit_score or 1),
                reverse=True
            )
        else:
            # Greenfield: ROI
            strategies.sort(
                key=lambda s: s.expected_outcomes.get("roi", 0),
                reverse=True
            )

        return strategies

    def _filter_by_greenfield_constraints(
        self,
        strategies: List[Strategy],
        greenfield_constraints: Dict[str, Any]
    ) -> List[Strategy]:
        """Greenfield 제약 필터링"""
        filtered = []

        budget = greenfield_constraints.get("budget")
        timeline = greenfield_constraints.get("timeline_months")

        for strategy in strategies:
            outcomes = strategy.expected_outcomes

            # Budget
            if budget and outcomes.get("required_investment", 0) > budget:
                continue

            # Timeline
            if timeline and outcomes.get("required_timeline_months", 36) > timeline:
                continue

            filtered.append(strategy)

        return filtered

    def _filter_by_brownfield_constraints(
        self,
        strategies: List[Strategy],
        constraints_profile: Dict[str, Any]
    ) -> List[Strategy]:
        """Brownfield 제약 필터링"""
        filtered = []

        hard_constraints = constraints_profile.get("hard_constraints", [])

        for strategy in strategies:
            violates = False

            for constraint in hard_constraints:
                ctype = constraint.get("type")
                dimension = constraint.get("dimension", "")
                threshold = constraint.get("threshold")

                # financial + budget
                if ctype == "financial" and "budget" in dimension:
                    if strategy.expected_outcomes.get("required_investment", 0) > threshold:
                        violates = True
                        break

                # temporal + timeline
                elif ctype == "temporal" and "timeline" in dimension:
                    if strategy.expected_outcomes.get("required_timeline_months", 36) > threshold:
                        violates = True
                        break

            if not violates:
                filtered.append(strategy)

        return filtered

    def _adjust_by_preferences(
        self,
        strategy: Strategy,
        preference_profile: Dict[str, Any]
    ) -> float:
        """Preference 반영 점수 조정"""
        score = strategy.execution_fit_score or 0.5

        soft_preferences = preference_profile.get("soft_preferences", [])

        for pref in soft_preferences:
            dimension = pref.get("dimension")
            value = pref.get("value")
            weight = pref.get("weight", 0.5)

            if dimension == "prefer_patterns":
                for pattern_id in strategy.pattern_composition:
                    if pattern_id in value:
                        score += 0.1 * weight

            elif dimension == "avoid_patterns":
                for pattern_id in strategy.pattern_composition:
                    if pattern_id in value:
                        score -= 0.2 * weight

        return max(0.0, min(1.0, score))

    def _load_or_create_goal(
        self,
        goal_id: str,
        constraints: Dict[str, Any]
    ) -> Goal:
        """Goal 로딩 또는 생성

        Phase 1: 간단한 생성
        Phase 2: D-Graph에서 로딩
        """
        # Phase 1: 간단한 Goal 생성
        return Goal(
            goal_id=goal_id,
            name=f"Goal {goal_id}",
            scope=constraints.get("scope", {}),
            target_horizon=constraints.get("horizon", "3y")
        )

    def _load_focal_actor_context(
        self,
        focal_actor_context_id: str,
    ) -> Optional[FocalActorContext]:
        """FocalActorContext 로딩 (store-first).

        - `.cmis/db/contexts.db`의 focal_actor_contexts 테이블을 정본으로 사용합니다.
        - 존재하지 않으면 None을 반환합니다. (호출부에서 Greenfield로 취급 가능)
        """

        store: Optional[FocalActorContextStore] = None
        try:
            store = FocalActorContextStore(project_root=self.project_root)
            return store.get_latest(focal_actor_context_id)
        except Exception:
            return None
        finally:
            if store is not None:
                store.close()

    def _save_strategies_to_d_graph(
        self,
        strategies: List[Strategy],
        goal_id: str,
        focal_actor_context_id: Optional[str],
    ) -> str:
        """D-Graph에 Strategy 저장

        Phase 3: strategy 노드 + edge 상세 저장
        """
        strategy_set_ref = f"STSET-{uuid.uuid4().hex[:8]}"

        # 1. strategy_set 노드
        self.d_graph.upsert_node(
            strategy_set_ref,
            "strategy_set",
            {
                "goal_id": goal_id,
                "strategy_ids": [s.strategy_id for s in strategies],
                "count": len(strategies),
                "created_at": datetime.now().isoformat(),
                "focal_actor_context_id": focal_actor_context_id,
            }
        )

        # 2. 각 strategy 노드 생성 (Phase 3)
        for strategy in strategies:
            # strategy 노드 (cmis.yaml 스키마)
            self.d_graph.upsert_node(
                strategy.strategy_id,
                "strategy",
                {
                    "name": strategy.name,
                    "description": strategy.description,
                    "traits": {
                        "execution_fit_score": strategy.execution_fit_score,
                        "adjusted_score": strategy.adjusted_score,
                        "created_from": strategy.created_from
                    },
                    "metadata": {
                        "action_set": strategy.action_set,
                        "expected_outcomes": strategy.expected_outcomes,
                        "risks": strategy.risks,
                        "lineage": strategy.lineage
                    }
                }
            )

            # 3. strategy_targets_goal edge
            self.d_graph.add_edge(
                "strategy_targets_goal",
                source=strategy.strategy_id,
                target=goal_id
            )

            # 4. strategy_uses_pattern edges
            for pattern_id in strategy.pattern_composition:
                self.d_graph.add_edge(
                    "strategy_uses_pattern",
                    source=strategy.strategy_id,
                    target=pattern_id,  # P-Graph pattern 노드
                    data={"pattern_id": pattern_id}
                )

        return strategy_set_ref

    def evaluate_portfolio_api(
        self,
        strategy_ids: List[str],
        policy_ref: str = "decision_balanced",
        focal_actor_context_id: Optional[str] = None,
    ) -> str:
        """Public API: Portfolio 평가"""
        strategies = [self._load_strategy(sid) for sid in strategy_ids]
        strategies = [s for s in strategies if s is not None]

        if not strategies:
            return "PEVAL-empty"

        focal_actor_context: Optional[FocalActorContext] = None
        if focal_actor_context_id:
            focal_actor_context = self._load_focal_actor_context(focal_actor_context_id)

        policy_params = self._resolve_policy(policy_ref)

        portfolio_eval = self.evaluate_portfolio_core(strategies, focal_actor_context, policy_params)

        portfolio_eval_ref = self._save_portfolio_to_d_graph(portfolio_eval, strategy_ids, focal_actor_context_id)

        return portfolio_eval_ref

    def evaluate_portfolio_core(self, strategies, focal_actor_context, policy_params):
        """Core: Portfolio 평가"""
        portfolio_id = f"PORTFOLIO-{uuid.uuid4().hex[:8]}"

        synergies = []
        for i, s1 in enumerate(strategies):
            for j, s2 in enumerate(strategies):
                if i < j:
                    score = self.optimizer.analyze_synergy(s1, s2)
                    if score > 0.2:
                        synergies.append({"strategies": [s1.strategy_id, s2.strategy_id], "synergy_score": score})

        conflicts = []
        for i, s1 in enumerate(strategies):
            for j, s2 in enumerate(strategies):
                if i < j:
                    conflict = self.optimizer.detect_conflicts(s1, s2)
                    if conflict:
                        conflicts.append(conflict)

        aggregate_roi = sum(s.expected_outcomes.get("roi", 0) for s in strategies) / len(strategies)
        aggregate_risk = sum(len(s.risks) for s in strategies) / (len(strategies) * 10)
        combined_score = aggregate_roi / (1 + aggregate_risk)

        resources = self.optimizer.aggregate_resource_requirements(strategies)

        return PortfolioEvaluation(
            portfolio_id=portfolio_id,
            strategy_ids=[s.strategy_id for s in strategies],
            aggregate_roi=aggregate_roi,
            aggregate_risk=aggregate_risk,
            combined_score=combined_score,
            synergies=synergies,
            conflicts=conflicts,
            resource_requirements=resources,
            policy_ref=policy_params.get("policy_ref", "decision_balanced"),
            focal_actor_context_id=focal_actor_context.focal_actor_context_id if focal_actor_context else None,
        )

    def _resolve_policy(self, policy_ref):
        """Policy 해석"""
        policies = {
            "reporting_strict": {
                "policy_ref": policy_ref,
                "risk_tolerance": 0.3,
                "prior_usage": "minimal",
                "min_evidence_ratio": 0.8
            },
            "decision_balanced": {
                "policy_ref": policy_ref,
                "risk_tolerance": 0.5,
                "prior_usage": "balanced",
                "min_evidence_ratio": 0.5
            },
            "exploration_friendly": {
                "policy_ref": policy_ref,
                "risk_tolerance": 0.7,
                "prior_usage": "extensive",
                "min_evidence_ratio": 0.3
            }
        }
        return policies.get(policy_ref, policies["decision_balanced"])

    def _load_strategy(self, strategy_id):
        """Strategy 로딩"""
        return self.strategies_cache.get(strategy_id)

    def _save_portfolio_to_d_graph(self, portfolio_eval, strategy_ids, focal_actor_context_id):
        """Portfolio D-Graph 저장"""
        self.d_graph.upsert_node(
            portfolio_eval.portfolio_id,
            "portfolio_eval",
            {
                "strategy_ids": strategy_ids,
                "aggregate_roi": portfolio_eval.aggregate_roi,
                "focal_actor_context_id": focal_actor_context_id,
                "created_at": datetime.now().isoformat()
            }
        )
        return portfolio_eval.portfolio_id
