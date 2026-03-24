"""CMIS v2 World Engine — Reality Snapshot (R-Graph) construction.

Builds and manages a graph of actors, money flows, states, and their
relationships.  Uses OntologyNode / OntologyEdge types from the KBD-generated
type system for validation.

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from cmis_v2.generated.types import OntologyEdge, OntologyNode
from cmis_v2.generated.validators import validate_node_traits

# ---------------------------------------------------------------------------
# Module-level store
# ---------------------------------------------------------------------------

_SNAPSHOTS: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# ID prefix helpers — derived from generated NodeType
# ---------------------------------------------------------------------------

def _derive_node_prefix(node_type: str) -> str:
    """Derive a 3-letter ID prefix from a node_type string.

    Rules: split by '_', take first letter of each part, uppercase.
    Single-word types use first 3 letters. Pad to 3 chars if needed.
    """
    parts = node_type.split("_")
    if len(parts) >= 2:
        prefix = "".join(p[0] for p in parts[:3]).upper()
    else:
        prefix = node_type[:3].upper()
    return prefix.ljust(3, "X")


# Build prefix map from generated NodeType at import time
from cmis_v2.generated.types import NodeType as _NodeType
import typing as _typing

# Legacy overrides for backward compatibility with existing node IDs
_PREFIX_OVERRIDES: dict[str, str] = {
    "money_flow": "MFL",
    "state": "STT",
}

_NODE_PREFIX: dict[str, str] = {}
for _nt in _typing.get_args(_NodeType):
    _NODE_PREFIX[_nt] = _PREFIX_OVERRIDES.get(_nt, _derive_node_prefix(_nt))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_snapshot(
    domain_id: str,
    region: str = "KR",
    evidence_id: str = "",
    focal_actor_context_id: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """Build a Reality Snapshot (R-Graph) for the given domain.

    Creates an empty graph structure that the LM can populate via
    add_node() and add_edge().

    Args:
        domain_id: Domain identifier (e.g., "Adult_Language_Education_KR").
        region: Region code (default "KR").
        evidence_id: Optional evidence collection ID this snapshot is based on.
        focal_actor_context_id: Optional focal actor for the analysis.

    Returns:
        dict with snapshot_id, domain_id, nodes, edges, summary, lineage.
    """
    snapshot_id = f"SNAP-{uuid4().hex[:6]}"
    now = datetime.now().isoformat()

    snapshot: dict[str, Any] = {
        "snapshot_id": snapshot_id,
        "domain_id": domain_id,
        "region": region,
        "nodes": [],
        "edges": [],
        "summary": {
            "actor_count": 0,
            "money_flow_count": 0,
            "state_count": 0,
            "product_count": 0,
            "segment_count": 0,
            "edge_count": 0,
        },
        "lineage": {
            "engine": "world",
            "evidence_id": evidence_id,
            "focal_actor_context_id": focal_actor_context_id,
            "timestamp": now,
        },
    }

    _SNAPSHOTS[snapshot_id] = snapshot
    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "world", snapshot_id, snapshot)
    return snapshot


def add_node(
    snapshot_id: str,
    node_type: str,
    data: dict[str, Any],
    project_id: str = "",
) -> dict[str, Any]:
    """Add a node to an existing snapshot.

    Validates traits using OntologyNode (Pydantic model) and the
    generated validate_node_traits() function.

    Args:
        snapshot_id: The snapshot to add the node to.
        node_type: One of "actor", "money_flow", "state".
        data: Node data including traits. The "traits" key holds trait values;
              other keys (e.g., "name", "description") are stored as-is.

    Returns:
        The new node dict, or an error dict.
    """
    if snapshot_id not in _SNAPSHOTS:
        if project_id:
            from cmis_v2.engine_store import load_engine_data
            loaded = load_engine_data(project_id, "world", snapshot_id)
            if loaded is not None:
                _SNAPSHOTS[snapshot_id] = loaded
        if snapshot_id not in _SNAPSHOTS:
            return {"error": f"Snapshot not found: {snapshot_id}"}

    # Extract traits from data for validation
    traits = data.get("traits", {})

    # Validate using generated validator
    errors = validate_node_traits(node_type, traits)
    if errors:
        return {"error": f"Trait validation failed: {errors}"}

    # Validate via Pydantic model
    prefix = _NODE_PREFIX.get(node_type, "NOD")
    node_id = f"{prefix}-{uuid4().hex[:6]}"

    try:
        OntologyNode(node_id=node_id, node_type=node_type, traits=traits)  # type: ignore[arg-type]
    except Exception as e:
        return {"error": f"OntologyNode validation failed: {e}"}

    node: dict[str, Any] = {
        "id": node_id,
        "type": node_type,
        "data": data,
    }

    snap = _SNAPSHOTS[snapshot_id]
    snap["nodes"].append(node)

    # Update summary counts
    count_key = f"{node_type}_count"
    if count_key in snap["summary"]:
        snap["summary"][count_key] += 1

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "world", snapshot_id, snap)

    return node


def add_edge(
    snapshot_id: str,
    edge_type: str,
    source: str,
    target: str,
    data: dict[str, Any] | None = None,
    project_id: str = "",
) -> dict[str, Any]:
    """Add an edge to an existing snapshot.

    Validates using OntologyEdge (Pydantic model).

    Args:
        snapshot_id: The snapshot to add the edge to.
        edge_type: One of the valid EdgeType literals.
        source: Source node ID.
        target: Target node ID.
        data: Optional edge properties.

    Returns:
        The new edge dict, or an error dict.
    """
    if snapshot_id not in _SNAPSHOTS:
        if project_id:
            from cmis_v2.engine_store import load_engine_data
            loaded = load_engine_data(project_id, "world", snapshot_id)
            if loaded is not None:
                _SNAPSHOTS[snapshot_id] = loaded
        if snapshot_id not in _SNAPSHOTS:
            return {"error": f"Snapshot not found: {snapshot_id}"}

    edge_id = f"EDG-{uuid4().hex[:6]}"

    try:
        OntologyEdge(
            edge_id=edge_id,
            edge_type=edge_type,  # type: ignore[arg-type]
            source_node_id=source,
            target_node_id=target,
            properties=data or {},
        )
    except Exception as e:
        return {"error": f"OntologyEdge validation failed: {e}"}

    edge: dict[str, Any] = {
        "type": edge_type,
        "source": source,
        "target": target,
        "data": data or {},
    }

    snap = _SNAPSHOTS[snapshot_id]
    snap["edges"].append(edge)
    snap["summary"]["edge_count"] += 1

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "world", snapshot_id, snap)

    return edge


def get_snapshot(snapshot_id: str, project_id: str = "") -> dict[str, Any]:
    """Retrieve a snapshot by ID.

    Args:
        snapshot_id: The snapshot ID.
        project_id: Optional project ID for file-based lookup.

    Returns:
        The snapshot dict, or an error dict.
    """
    if snapshot_id in _SNAPSHOTS:
        return _SNAPSHOTS[snapshot_id]
    if project_id:
        from cmis_v2.engine_store import load_engine_data
        data = load_engine_data(project_id, "world", snapshot_id)
        if data is not None:
            _SNAPSHOTS[snapshot_id] = data
            return data
    return {"error": f"Snapshot not found: {snapshot_id}"}
