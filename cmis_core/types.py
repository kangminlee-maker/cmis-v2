"""CMIS Core Types

Common dataclasses used across all v9 modules.
Based on umis_v9.yaml ontology and graph schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


# ========================================
# Graph Primitives
# ========================================

@dataclass
class Node:
    """Graph node (Actor/Event/Resource/MoneyFlow/Contract/State)"""
    id: str
    type: str  # "actor", "money_flow", "state", etc.
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """Graph edge (actor_pays_actor, event_triggers_money_flow, etc.)"""
    type: str
    source: str
    target: str
    data: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Metric & Value
# ========================================

@dataclass
class MetricRequest:
    """Metric 평가 요청"""
    metric_id: str  # "MET-Revenue", "MET-N_customers", etc.
    context: Dict[str, Any] = field(default_factory=dict)
    # context 예: {"domain_id": "Adult_Language_KR", "year": 2024}


@dataclass
class ValueRecord:
    """Metric 계산 결과 (V-Graph의 value_record 노드)"""
    metric_id: str
    context: Dict[str, Any]
    point_estimate: Optional[float] = None
    distribution: Optional[Dict[str, Any]] = None  # {"min": ..., "max": ...}
    quality: Dict[str, Any] = field(default_factory=dict)
    # quality 예: {"status": "ok", "method": "direct", "literal_ratio": 1.0}
    lineage: Dict[str, Any] = field(default_factory=dict)
    # lineage 예: {"from_evidence_ids": [...], "engine_ids": ["value_engine"]}


# ========================================
# Pattern Matching
# ========================================

@dataclass
class PatternMatch:
    """패턴 매칭 결과"""
    pattern_id: str  # "PAT-subscription_model", etc.
    description: str
    structure_fit_score: float  # 0.0 ~ 1.0
    execution_fit_score: Optional[float] = None  # project_context 있을 때만
    evidence: Dict[str, Any] = field(default_factory=dict)
    # evidence 예: {"source": "money_flow.traits.revenue_model", "node_ids": [...]}


@dataclass
class GapCandidate:
    """기회/갭 후보"""
    description: str
    related_pattern_ids: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Workflow Input/Output
# ========================================

@dataclass
class StructureAnalysisInput:
    """structure_analysis 워크플로우 입력"""
    domain_id: str
    region: str
    segment: Optional[str] = None
    as_of: Optional[str] = None
    project_context_id: Optional[str] = None  # Brownfield 모드 시


@dataclass
class StructureAnalysisResult:
    """structure_analysis 워크플로우 출력"""
    
    meta: Dict[str, Any] = field(default_factory=dict)
    # meta 예: {"domain_id": ..., "region": ..., "as_of": ...}
    
    graph_overview: Dict[str, Any] = field(default_factory=dict)
    # graph_overview 예:
    # {
    #   "num_actors": 7,
    #   "num_money_flows": 6,
    #   "actor_types": {"customer_segment": 2, "company": 5},
    #   "total_money_flow_amount": 290000000000
    # }
    
    pattern_matches: List[PatternMatch] = field(default_factory=list)
    
    metrics: List[ValueRecord] = field(default_factory=list)
    
    execution_time: Optional[float] = None  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용"""
        return {
            "meta": self.meta,
            "graph_overview": self.graph_overview,
            "pattern_matches": [
                {
                    "pattern_id": pm.pattern_id,
                    "description": pm.description,
                    "structure_fit_score": pm.structure_fit_score,
                    "execution_fit_score": pm.execution_fit_score,
                }
                for pm in self.pattern_matches
            ],
            "metrics": [
                {
                    "metric_id": vr.metric_id,
                    "point_estimate": vr.point_estimate,
                    "quality": vr.quality,
                }
                for vr in self.metrics
            ],
            "execution_time": self.execution_time,
        }


# ========================================
# Reality Graph Snapshot
# ========================================

@dataclass
class RealityGraphSnapshot:
    """World Engine snapshot 결과 (R-Graph 서브그래프)"""
    graph: Any  # InMemoryGraph (circular import 회피)
    meta: Dict[str, Any] = field(default_factory=dict)
    # meta 예: {"domain_id": ..., "seed_path": ..., "as_of": ...}
