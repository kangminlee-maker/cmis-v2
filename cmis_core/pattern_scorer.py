"""Pattern Scorer - Pattern 매칭 결과 점수 계산

Structure Fit, Execution Fit, Combined Score 계산

2025-12-10: Phase 1 Core Infrastructure
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional

from .types import PatternSpec, PatternMatch
from .pattern_matcher import calculate_trait_score
from .context_binding import FocalActorContextBinding, resolve_focal_actor_context_binding


class PatternScorer:
    """Pattern Scoring 엔진

    역할:
    1. Structure Fit 계산 (Trait + Graph)
    2. Execution Fit 계산 (Capability + Constraint + Asset)
    3. Combined Score 계산

    Phase 1: Structure Fit
    Phase 2: Execution Fit (FocalActorContext 연동)
    """

    def __init__(self):
        """초기화"""
        pass

    def score_all(
        self,
        match_results: List[Dict],
        focal_actor_context_id: Optional[str] = None,
    ) -> List[PatternMatch]:
        """매칭 결과에 점수 부여

        Args:
            match_results: PatternMatcher.match() 결과
            focal_actor_context_id: FocalActorContext ID (선택)

        Returns:
            PatternMatch 리스트 (점수 포함)
        """
        scored_matches = []

        # FocalActorContext 로딩 (있다면)
        focal_context_binding: Optional[FocalActorContextBinding] = None
        if focal_actor_context_id:
            focal_context_binding = self._resolve_focal_actor_context_binding(focal_actor_context_id)

        for result in match_results:
            pattern = result["pattern"]
            trait_result = result["trait_result"]
            structure_result = result["structure_result"]

            # Structure Fit
            structure_fit = self.calculate_structure_fit(
                pattern,
                trait_result,
                structure_result
            )

            # Execution Fit (FocalActorContext 있을 때만)
            execution_fit = None
            if focal_context_binding:
                execution_fit = self.calculate_execution_fit(
                    pattern,
                    focal_context_binding
                )

            # Combined Score
            combined_score = calculate_combined_score(
                structure_fit,
                execution_fit
            )

            # PatternMatch 생성
            match = PatternMatch(
                pattern_id=pattern.pattern_id,
                description=pattern.description,
                structure_fit_score=structure_fit,
                execution_fit_score=execution_fit,
                combined_score=combined_score,
                evidence={
                    "trait_result": trait_result,
                    "structure_result": structure_result
                },
                anchor_nodes=trait_result.get("anchor_nodes", {}),
                instance_scope=None  # Phase 2에서 구현
            )

            scored_matches.append(match)

        # 정렬: combined_score 기준
        scored_matches.sort(key=lambda m: m.combined_score, reverse=True)

        return scored_matches

    def calculate_structure_fit(
        self,
        pattern: PatternSpec,
        trait_result: Dict,
        structure_result: Dict
    ) -> float:
        """Structure Fit 점수 계산

        점수 = (Trait 점수 × 0.6) + (Graph 구조 점수 × 0.4)

        Args:
            pattern: PatternSpec
            trait_result: check_trait_constraints 결과
            structure_result: check_graph_structure 결과

        Returns:
            Structure Fit 점수 (0.0 ~ 1.0)
        """
        # Trait Score (calculate_trait_score 재사용)
        trait_score = calculate_trait_score(trait_result["trait_match"])

        # Structure Score
        satisfied = structure_result.get("satisfied", [])
        unsatisfied = structure_result.get("unsatisfied", [])
        total = len(satisfied) + len(unsatisfied)

        if total == 0:
            structure_score = 1.0  # 구조 제약 없으면 만점
        else:
            structure_score = len(satisfied) / total

        # Combined
        final_score = (trait_score * 0.6) + (structure_score * 0.4)

        return final_score

    def calculate_execution_fit(
        self,
        pattern: PatternSpec,
        focal_context: FocalActorContextBinding
    ) -> float:
        """Execution Fit 점수 계산 (FocalActorContext binding 기반)

        점수 = (Capability × 0.5) + (Constraint × 0.3) + (Asset × 0.2)

        Args:
            pattern: PatternSpec
            focal_context: FocalActorContextBinding

        Returns:
            Execution Fit 점수 (0.0 ~ 1.0)
        """
        # 1. Capability 매칭 (0.5 가중치)
        capability_score = self._calculate_capability_match(
            pattern.required_capabilities,
            focal_context.capability_traits
        )

        # 2. Constraint 체크 (0.3 가중치)
        constraint_score = self._calculate_constraint_satisfaction(
            pattern.constraint_checks,
            focal_context.hard_constraints
        )

        # 3. Asset 충족도 (0.2 가중치)
        asset_score = self._calculate_asset_sufficiency(
            pattern.required_assets,
            focal_context.assets_profile
        )

        # Combined
        execution_fit = (
            capability_score * 0.5 +
            constraint_score * 0.3 +
            asset_score * 0.2
        )

        return execution_fit

    def _calculate_capability_match(
        self,
        required_capabilities: List[Dict[str, Any]],
        available_capabilities: List[Dict[str, Any]]
    ) -> float:
        """Capability 매칭 점수

        Args:
            required_capabilities: Pattern이 요구하는 capability
            available_capabilities: FocalActorContext의 capability_traits

        Returns:
            매칭 점수 (0.0 ~ 1.0)
        """
        if not required_capabilities:
            return 1.0  # 요구사항 없으면 만점

        if not available_capabilities:
            return 0.0  # 가용 capability 없으면 0점

        matched_count = 0

        for required in required_capabilities:
            # 하나라도 매칭되면 OK
            for available in available_capabilities:
                if self._capability_matches(required, available):
                    matched_count += 1
                    break

        return matched_count / len(required_capabilities)

    def _capability_matches(
        self,
        required: Dict[str, Any],
        available: Dict[str, Any]
    ) -> bool:
        """단일 Capability 매칭 여부

        Args:
            required: 요구하는 capability trait
            available: 가용한 capability trait

        Returns:
            매칭 여부
        """
        # 모든 required key가 available에 있어야 함
        for key, value in required.items():
            if key not in available:
                return False

            # 값 비교 (리스트면 포함 여부, 아니면 정확히 일치)
            if isinstance(value, list):
                if available[key] not in value:
                    return False
            else:
                if available[key] != value:
                    return False

        return True

    def _calculate_constraint_satisfaction(
        self,
        constraint_checks: List[str],
        hard_constraints: List[Dict[str, Any]]
    ) -> float:
        """제약 조건 만족도

        Args:
            constraint_checks: Pattern이 체크하는 제약 조건 ID
            hard_constraints: FocalActorContext의 hard_constraints

        Returns:
            만족도 (0.0 ~ 1.0)
        """
        if not constraint_checks:
            return 1.0  # 체크할 제약 없으면 만점

        # 간단히: 제약이 위반되지 않으면 1.0, 하나라도 위반되면 0.0
        # Phase 3에서 더 정교하게 구현

        # 지금은 항상 통과 (실제 제약 체크는 Phase 3)
        return 1.0

    def _calculate_asset_sufficiency(
        self,
        required_assets: Dict[str, Any],
        assets_profile: Dict[str, Any]
    ) -> float:
        """Asset 충족도

        Args:
            required_assets: Pattern이 요구하는 자산
            assets_profile: FocalActorContext의 assets_profile

        Returns:
            충족도 (0.0 ~ 1.0)
        """
        if not required_assets:
            return 1.0  # 요구 자산 없으면 만점

        total_checks = 0
        satisfied_checks = 0

        # Channels 체크
        if "channels" in required_assets:
            total_checks += 1
            req_channels = required_assets["channels"]
            avail_channels = assets_profile.get("channels", [])

            if self._check_channels(req_channels, avail_channels):
                satisfied_checks += 1

        # Brand awareness 체크
        if "brand_awareness_level" in required_assets:
            total_checks += 1
            req_levels = required_assets["brand_awareness_level"]
            avail_level = assets_profile.get("brand_assets", {}).get("brand_awareness_level")

            if avail_level in req_levels:
                satisfied_checks += 1

        # Organizational assets 체크
        if "organizational_assets" in required_assets:
            total_checks += 1
            req_org = required_assets["organizational_assets"]
            avail_org = assets_profile.get("organizational_assets", {})

            if self._check_organizational_assets(req_org, avail_org):
                satisfied_checks += 1

        # Data assets 체크
        if "data_assets" in required_assets:
            total_checks += 1
            req_data = required_assets["data_assets"]
            avail_data = assets_profile.get("data_assets", {})

            if self._check_data_assets(req_data, avail_data):
                satisfied_checks += 1

        if total_checks == 0:
            return 1.0

        return satisfied_checks / total_checks

    def _check_channels(self, required: Dict, available: List) -> bool:
        """채널 체크"""
        # required: {"online": True, "min_reach": 1000}
        # available: [{"channel_type": "online", "reach": 5000}]

        if not isinstance(available, list):
            return False

        if required.get("online"):
            # Online 채널이 있는지
            has_online = any(
                ch.get("channel_type") == "online"
                for ch in available
            )
            if not has_online:
                return False

            # min_reach 체크
            if "min_reach" in required:
                online_channels = [
                    ch for ch in available
                    if ch.get("channel_type") == "online"
                ]
                max_reach = max(
                    (ch.get("reach", 0) for ch in online_channels),
                    default=0
                )
                if max_reach < required["min_reach"]:
                    return False

        return True

    def _check_organizational_assets(self, required: Dict, available: Dict) -> bool:
        """조직 자산 체크"""
        # min_team_size
        if "min_team_size" in required:
            if available.get("team_size", 0) < required["min_team_size"]:
                return False

        # org_maturity
        if "org_maturity" in required:
            req_maturity = required["org_maturity"]
            avail_maturity = available.get("org_maturity")

            if isinstance(req_maturity, list):
                if avail_maturity not in req_maturity:
                    return False
            else:
                if avail_maturity != req_maturity:
                    return False

        return True

    def _check_data_assets(self, required: Dict, available: Dict) -> bool:
        """데이터 자산 체크"""
        # customer_data_volume
        if "customer_data_volume" in required:
            if available.get("customer_data_volume", 0) < required["customer_data_volume"]:
                return False

        return True

    def _resolve_focal_actor_context_binding(self, focal_actor_context_id: str) -> FocalActorContextBinding:
        """FocalActorContext binding 로딩(Phase 1: 스텁)."""
        return resolve_focal_actor_context_binding(focal_actor_context_id)


def calculate_combined_score(
    structure_fit: float,
    execution_fit: Optional[float]
) -> float:
    """Combined Score 계산 (단일 규칙)

    규칙:
    - FocalActorContext 없음 → combined = structure_fit
    - FocalActorContext 있음 → combined = structure_fit × execution_fit

    Args:
        structure_fit: Structure Fit 점수
        execution_fit: Execution Fit 점수 (None 가능)

    Returns:
        Combined Score (0.0 ~ 1.0)
    """
    if execution_fit is None:
        return structure_fit
    else:
        return structure_fit * execution_fit
