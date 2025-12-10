"""Pattern Matcher - Trait 기반 패턴 매칭

R-Graph에서 Pattern을 찾는 핵심 매칭 로직

2025-12-10: Phase 1 Core Infrastructure
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from collections import defaultdict

from .types import PatternSpec, PatternMatch
from .graph import InMemoryGraph


class PatternMatcher:
    """Pattern 매칭 엔진
    
    역할:
    1. Trait 기반 필터링 (빠른 제거)
    2. Graph 구조 검증
    3. Anchor Node 식별
    
    Phase 1: Trait/Graph 매칭
    Phase 2: Scoring (PatternScorer로 분리)
    """
    
    def __init__(self):
        """초기화"""
        pass
    
    def match(
        self,
        graph: InMemoryGraph,
        pattern_candidates: List[PatternSpec]
    ) -> List[Dict[str, Any]]:
        """Pattern 후보에 대해 매칭 수행
        
        Args:
            graph: Reality Graph
            pattern_candidates: 매칭할 Pattern 리스트
        
        Returns:
            매칭 결과 리스트 (아직 점수는 없음, raw 결과)
            [
                {
                    "pattern": PatternSpec,
                    "trait_result": {...},
                    "structure_result": {...}
                }
            ]
        """
        results = []
        
        for pattern in pattern_candidates:
            # Stage 1: Trait Check (빠른 제거)
            trait_result = check_trait_constraints(
                graph,
                pattern.trait_constraints
            )
            
            if not trait_result["is_match"]:
                continue  # 빠른 제거
            
            # Stage 2: Graph Structure Check
            structure_result = check_graph_structure(
                graph,
                pattern.graph_structure
            )
            
            if not structure_result["is_match"]:
                continue
            
            # 매칭 성공
            results.append({
                "pattern": pattern,
                "trait_result": trait_result,
                "structure_result": structure_result
            })
        
        return results


# ========================================
# Trait Constraint Checking
# ========================================

def check_trait_constraints(
    graph: InMemoryGraph,
    trait_constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """Trait 제약 체크 (v1.1 - 2단계)
    
    Args:
        graph: Reality Graph
        trait_constraints: Pattern의 trait_constraints
            {
                "money_flow": {
                    "required_traits": {"revenue_model": "subscription"},
                    "optional_traits": {"recurrence": ["monthly", "yearly"]}
                }
            }
    
    Returns:
        {
            "is_match": bool,
            "trait_match": {
                "money_flow": {
                    "required": {"matched": 2, "total": 2},
                    "optional": {"matched": 1, "total": 3}
                }
            },
            "matched_node_ids": [...],
            "anchor_nodes": {"money_flow": [...]}
        }
    """
    if not trait_constraints:
        return {
            "is_match": True,
            "trait_match": {},
            "matched_node_ids": [],
            "anchor_nodes": {}
        }
    
    trait_match = {}
    all_matched_node_ids = []
    anchor_nodes = defaultdict(list)
    
    for node_type, constraints in trait_constraints.items():
        required_traits = constraints.get("required_traits", {})
        optional_traits = constraints.get("optional_traits", {})
        
        # Node type에 해당하는 노드 조회
        try:
            nodes = graph.nodes_by_type(node_type)
        except Exception:
            # node_type이 그래프에 없음
            nodes = []
        
        req_total = len(required_traits)
        opt_total = len(optional_traits)
        
        # 이 node_type에서 매칭된 노드들
        matched_nodes = []
        opt_match_count = 0
        
        for node in nodes:
            node_traits = node.data.get("traits", {})
            
            # Required traits 체크
            req_match = all(
                _trait_value_match(node_traits.get(k), v)
                for k, v in required_traits.items()
            )
            
            if req_match:
                # Required 모두 만족
                matched_nodes.append(node.id)
                all_matched_node_ids.append(node.id)
                anchor_nodes[node_type].append(node.id)
                
                # Optional traits 체크
                for k, v in optional_traits.items():
                    if _trait_value_match(node_traits.get(k), v):
                        opt_match_count += 1
        
        # 이 node_type의 매칭 결과
        # Required: 노드가 1개 이상 있으면 모든 required traits 만족한 것으로 간주
        req_matched = req_total if len(matched_nodes) > 0 else 0
        
        trait_match[node_type] = {
            "required": {
                "matched": req_matched,  # 노드 있으면 모든 trait 만족
                "total": req_total
            },
            "optional": {
                "matched": opt_match_count,
                "total": opt_total
            },
            "matched_nodes": matched_nodes
        }
    
    # 전체 Required가 모두 만족했는지 확인
    all_required_satisfied = all(
        stats["required"]["matched"] == stats["required"]["total"]
        for stats in trait_match.values()
        if stats["required"]["total"] > 0
    )
    
    return {
        "is_match": all_required_satisfied,
        "trait_match": trait_match,
        "matched_node_ids": all_matched_node_ids,
        "anchor_nodes": dict(anchor_nodes)
    }


def _trait_value_match(node_value: Any, pattern_value: Any) -> bool:
    """Trait 값 매칭 (단일 값 또는 리스트)
    
    Args:
        node_value: 노드의 trait 값
        pattern_value: Pattern이 요구하는 값 (단일 또는 리스트)
    
    Returns:
        매칭 여부
    """
    if pattern_value is None:
        return True  # Pattern이 값을 요구하지 않음
    
    if node_value is None:
        return False  # 노드에 값이 없음
    
    # Pattern이 리스트면 "node_value가 리스트 안에 있으면 OK"
    if isinstance(pattern_value, list):
        return node_value in pattern_value
    
    # 정확히 일치
    return node_value == pattern_value


# ========================================
# Graph Structure Checking
# ========================================

def check_graph_structure(
    graph: InMemoryGraph,
    graph_structure: Dict[str, Any]
) -> Dict[str, Any]:
    """Graph 구조 제약 체크
    
    Args:
        graph: Reality Graph
        graph_structure: Pattern의 graph_structure
            {
                "requires": [
                    {"node_type": "money_flow", "min_count": 1},
                    {"edge_type": "actor_pays_actor", "min_count": 10}
                ]
            }
    
    Returns:
        {
            "is_match": bool,
            "satisfied": [...],
            "unsatisfied": [...]
        }
    """
    if not graph_structure:
        return {
            "is_match": True,
            "satisfied": [],
            "unsatisfied": []
        }
    
    requires = graph_structure.get("requires", [])
    
    if not requires:
        return {
            "is_match": True,
            "satisfied": [],
            "unsatisfied": []
        }
    
    satisfied = []
    unsatisfied = []
    
    for requirement in requires:
        if "node_type" in requirement:
            # Node count 체크
            node_type = requirement["node_type"]
            min_count = requirement.get("min_count", 1)
            required_traits = requirement.get("traits", {})
            
            try:
                nodes = graph.nodes_by_type(node_type)
            except Exception:
                nodes = []
            
            # Trait 필터링 (있다면)
            if required_traits:
                nodes = [
                    n for n in nodes
                    if all(
                        _trait_value_match(n.data.get("traits", {}).get(k), v)
                        for k, v in required_traits.items()
                    )
                ]
            
            if len(nodes) >= min_count:
                satisfied.append(requirement)
            else:
                unsatisfied.append(requirement)
        
        elif "edge_type" in requirement:
            # Edge count 체크
            edge_type = requirement["edge_type"]
            min_count = requirement.get("min_count", 1)
            
            try:
                edges = graph.edges_by_type(edge_type)
            except Exception:
                edges = []
            
            if len(edges) >= min_count:
                satisfied.append(requirement)
            else:
                unsatisfied.append(requirement)
        
        else:
            # Unknown requirement type
            unsatisfied.append(requirement)
    
    return {
        "is_match": len(unsatisfied) == 0,
        "satisfied": satisfied,
        "unsatisfied": unsatisfied
    }


# ========================================
# Trait Score Calculation (v1.1 - 2단계)
# ========================================

def calculate_trait_score(
    trait_match: Dict[str, Any]
) -> float:
    """Trait Score 계산 (2단계)
    
    Args:
        trait_match: check_trait_constraints 결과의 trait_match 부분
    
    Returns:
        Trait Score (0.0 ~ 1.0)
    
    계산:
    1. Required traits 일치율 (핵심)
    2. Optional traits 보너스 (+최대 10%)
    """
    required_total = 0
    required_matched = 0
    optional_total = 0
    optional_matched = 0
    
    for node_type, stats in trait_match.items():
        required_total += stats["required"]["total"]
        required_matched += stats["required"]["matched"]
        optional_total += stats["optional"]["total"]
        optional_matched += stats["optional"]["matched"]
    
    # Required 점수
    if required_total == 0:
        required_score = 1.0  # 필수 trait 없으면 만점
    else:
        required_score = required_matched / required_total
    
    # Optional 보너스
    if optional_total > 0:
        optional_bonus = (optional_matched / optional_total) * 0.1
    else:
        optional_bonus = 0.0
    
    # 최종 점수 (최대 1.0)
    final_score = min(required_score + optional_bonus, 1.0)
    
    return final_score

