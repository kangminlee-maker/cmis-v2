"""UMIS v9 Pattern Engine v1

패턴 매칭 및 갭 탐지
v1: 코드 기반 2개 패턴 (subscription, platform)
"""

from __future__ import annotations

from typing import List, Dict, Any

from .graph import InMemoryGraph
from .types import PatternMatch, GapCandidate


class PatternEngine:
    """Pattern Engine v1 - 코드 기반 패턴 매칭
    
    v1 지원 패턴:
    - PAT-subscription_model: revenue_model == subscription
    - PAT-platform_business_model: institution_type == online_platform
    
    v2+ 예정:
    - Pattern Graph 로딩
    - 23개 BM Pattern 전체
    - execution_fit_score (Project Context 기반)
    - value_chain_templates 연동
    """
    
    def __init__(self):
        """초기화"""
        pass
    
    def match_patterns(
        self,
        graph: InMemoryGraph,
        project_context_id: str = None
    ) -> List[PatternMatch]:
        """패턴 매칭 (v1: 간단 rule 기반)
        
        Args:
            graph: R-Graph
            project_context_id: 프로젝트 컨텍스트 (v1 미사용)
        
        Returns:
            PatternMatch 목록
        """
        matches = []
        
        # Pattern 1: Subscription Model
        subscription_match = self._match_subscription_model(graph)
        if subscription_match:
            matches.append(subscription_match)
        
        # Pattern 2: Platform Business Model
        platform_match = self._match_platform_model(graph)
        if platform_match:
            matches.append(platform_match)
        
        return matches
    
    def _match_subscription_model(self, graph: InMemoryGraph) -> Optional[PatternMatch]:
        """구독형 BM 패턴 매칭
        
        검출 규칙:
        - money_flow.traits.revenue_model == "subscription"
        """
        evidence_nodes = []
        
        for mf in graph.nodes_by_type("money_flow"):
            traits = mf.data.get("traits", {})
            if traits.get("revenue_model") == "subscription":
                evidence_nodes.append(mf.id)
        
        if evidence_nodes:
            return PatternMatch(
                pattern_id="PAT-subscription_model",
                description="정기 결제 구조를 가지는 구독형 비즈니스 모델",
                structure_fit_score=1.0,
                evidence={
                    "source": "money_flow.traits.revenue_model == subscription",
                    "node_ids": evidence_nodes
                }
            )
        
        return None
    
    def _match_platform_model(self, graph: InMemoryGraph) -> Optional[PatternMatch]:
        """플랫폼 BM 패턴 매칭
        
        검출 규칙:
        - actor.traits.institution_type == "online_platform"
        """
        evidence_nodes = []
        
        for actor in graph.nodes_by_type("actor"):
            traits = actor.data.get("traits", {})
            if traits.get("institution_type") == "online_platform":
                evidence_nodes.append(actor.id)
        
        if evidence_nodes:
            return PatternMatch(
                pattern_id="PAT-platform_business_model",
                description="공급자-플랫폼-수요자 구조의 플랫폼 비즈니스 모델",
                structure_fit_score=1.0,
                evidence={
                    "source": "actor.traits.institution_type == online_platform",
                    "node_ids": evidence_nodes
                }
            )
        
        return None
    
    def discover_gaps(
        self,
        graph: InMemoryGraph,
        project_context_id: str = None
    ) -> List[GapCandidate]:
        """기회/갭 탐지 (v1: state.entry_strategy_clues 기반)
        
        Args:
            graph: R-Graph
            project_context_id: 프로젝트 컨텍스트 (v1 미사용)
        
        Returns:
            GapCandidate 목록
        """
        gaps = []
        
        for state in graph.nodes_by_type("state"):
            props = state.data.get("properties", {})
            clues = props.get("entry_strategy_clues", [])
            
            for clue in clues:
                gaps.append(GapCandidate(
                    description=clue,
                    related_pattern_ids=["PAT-subscription_model", "PAT-platform_business_model"],
                    evidence={
                        "state_id": state.id,
                        "field": "properties.entry_strategy_clues"
                    }
                ))
        
        return gaps


# Optional import (하위 호환)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Optional
