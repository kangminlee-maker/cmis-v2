# cmis_v2.engines - Engine implementations
"""CMIS v2 analysis engines.

Phase 1 MVP engines:
- evidence: Evidence collection and management
- world: Reality Snapshot (R-Graph) construction
- pattern: Business pattern matching
- value: Metric evaluation (4-Method Fusion)

Phase 2 engines:
- strategy: Strategy search and portfolio evaluation
- policy: Policy-driven quality gates

Phase 3 engines:
- belief: Prior/belief distribution management
- learning: Outcome recording and prediction accuracy tracking
"""

from __future__ import annotations

from cmis_v2.engines.belief import get_prior as get_prior
from cmis_v2.engines.belief import list_beliefs as list_beliefs
from cmis_v2.engines.belief import set_prior as set_prior
from cmis_v2.engines.belief import update_belief as update_belief
from cmis_v2.engines.evidence import add_record as add_record
from cmis_v2.engines.evidence import collect_evidence as collect_evidence
from cmis_v2.engines.evidence import get_evidence as get_evidence
from cmis_v2.engines.learning import apply_learnings as apply_learnings
from cmis_v2.engines.learning import get_learning_summary as get_learning_summary
from cmis_v2.engines.learning import record_outcome as record_outcome
from cmis_v2.engines.pattern import discover_gaps as discover_gaps
from cmis_v2.engines.pattern import match_patterns as match_patterns
from cmis_v2.engines.policy import check_all_gates as check_all_gates
from cmis_v2.engines.policy import check_evidence_gate as check_evidence_gate
from cmis_v2.engines.policy import check_value_gate as check_value_gate
from cmis_v2.engines.policy import load_policy as load_policy
from cmis_v2.engines.strategy import evaluate_portfolio as evaluate_portfolio
from cmis_v2.engines.strategy import search_strategies as search_strategies
from cmis_v2.engines.value import evaluate_metrics as evaluate_metrics
from cmis_v2.engines.value import get_metric_value as get_metric_value
from cmis_v2.engines.value import set_metric_value as set_metric_value
from cmis_v2.engines.world import add_edge as add_edge
from cmis_v2.engines.world import add_node as add_node
from cmis_v2.engines.world import build_snapshot as build_snapshot
from cmis_v2.engines.world import get_snapshot as get_snapshot

__all__ = [
    # evidence
    "collect_evidence",
    "add_record",
    "get_evidence",
    # world
    "build_snapshot",
    "add_node",
    "add_edge",
    "get_snapshot",
    # pattern
    "match_patterns",
    "discover_gaps",
    # value
    "evaluate_metrics",
    "set_metric_value",
    "get_metric_value",
    # strategy
    "search_strategies",
    "evaluate_portfolio",
    # policy
    "load_policy",
    "check_evidence_gate",
    "check_value_gate",
    "check_all_gates",
    # belief
    "set_prior",
    "get_prior",
    "update_belief",
    "list_beliefs",
    # learning
    "record_outcome",
    "get_learning_summary",
    "apply_learnings",
]
