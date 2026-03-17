# cmis_v2.engines - Engine implementations
"""CMIS v2 analysis engines.

Phase 1 MVP engines:
- evidence: Evidence collection and management
- world: Reality Snapshot (R-Graph) construction
- pattern: Business pattern matching
- value: Metric evaluation (4-Method Fusion)
"""

from __future__ import annotations

from cmis_v2.engines.evidence import add_record as add_record
from cmis_v2.engines.evidence import collect_evidence as collect_evidence
from cmis_v2.engines.evidence import get_evidence as get_evidence
from cmis_v2.engines.pattern import discover_gaps as discover_gaps
from cmis_v2.engines.pattern import match_patterns as match_patterns
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
]
