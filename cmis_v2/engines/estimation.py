"""CMIS v2 Estimation Engine — Rational estimation under uncertainty.

Replaces the former Belief Engine (belief.py).  All estimation is
interval-based (P10/P90 ranges), with no sigma/confidence conversion.

Design decisions (3x 8-Agent Panel Review, 2026-03-25):
- Pure Interval (接근법 B): lo/hi = P10/P90
- No confidence→sigma conversion (접근법 A 폐기)
- Batch update for order independence (강한 재현)
- Free variables supported (not limited to METRIC_REGISTRY)
- Stepwise Fermi tree construction

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from cmis_v2.engines.interval import Interval

# ---------------------------------------------------------------------------
# Module-level stores
# ---------------------------------------------------------------------------

_ESTIMATION_STORE: dict[str, dict[str, Any]] = {}  # variable_name -> MetricEstimation
_FERMI_STORE: dict[str, dict[str, Any]] = {}        # tree_id -> FermiTree

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _try_get_bounds(variable_name: str) -> dict[str, float] | None:
    """Try to get bounds from METRIC_REGISTRY if variable is a known metric."""
    try:
        from cmis_v2.generated.types import METRIC_REGISTRY
        entry = METRIC_REGISTRY.get(variable_name, {})
        return entry.get("bounds")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API: Estimates
# ---------------------------------------------------------------------------


def create_estimate(
    variable_name: str,
    lo: float,
    hi: float,
    method: str = "unknown",
    source: str = "",
    source_reliability: float = 0.5,
    evidence_id: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """Create a new estimation for a variable.

    The variable can be a registered metric (MET-TAM) or a free variable
    ("korean_household_count").

    Args:
        variable_name: Metric ID or arbitrary variable name.
        lo: P10 lower bound (10% chance the true value is below this).
        hi: P90 upper bound (10% chance the true value is above this).
        method: Estimation method ("fermi", "top_down", "bottom_up",
                "proxy", "constraint", "expert_guess", "unknown").
        source: Human-readable source description.
        source_reliability: Reliability of the source (0.0-1.0).
            Produced by Evidence Engine only — not generated internally.
        evidence_id: Evidence record ID supporting this estimate.
        project_id: Optional project ID for file-based persistence.

    Returns:
        Estimate dict with estimate_id, variable_name, interval, etc.
    """
    interval = Interval(lo, hi)

    # Clamp to known bounds if available
    bounds = _try_get_bounds(variable_name)
    if bounds:
        interval = interval.clamp(bounds["min"], bounds["max"])

    estimate_id = f"EST-{uuid4().hex[:6]}"
    now = _now_iso()

    estimate: dict[str, Any] = {
        "estimate_id": estimate_id,
        "variable_name": variable_name,
        "interval": interval.to_dict(),
        "point_estimate": interval.midpoint,
        "method": method,
        "source": source,
        "source_reliability": max(0.0, min(1.0, source_reliability)),
        "evidence_id": evidence_id,
        "created_at": now,
    }

    # Store in MetricEstimation
    if variable_name not in _ESTIMATION_STORE:
        _ESTIMATION_STORE[variable_name] = {
            "variable_name": variable_name,
            "estimates": [],
            "fused": None,
            "version": 0,
            "updated_at": now,
        }

    me = _ESTIMATION_STORE[variable_name]
    me["estimates"].append(estimate)
    me["version"] += 1
    me["updated_at"] = now

    # Auto-fuse if multiple estimates exist
    if len(me["estimates"]) >= 2:
        me["fused"] = _batch_fuse(me["estimates"], variable_name)

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "estimation", variable_name, me)

    return estimate


def get_estimate(
    variable_name: str,
    project_id: str = "",
) -> dict[str, Any]:
    """Get the current estimation state for a variable.

    Returns the MetricEstimation dict with all estimates and fused result.
    """
    if variable_name in _ESTIMATION_STORE:
        return _ESTIMATION_STORE[variable_name]
    if project_id:
        from cmis_v2.engine_store import load_engine_data
        data = load_engine_data(project_id, "estimation", variable_name)
        if data is not None:
            _ESTIMATION_STORE[variable_name] = data
            return data
    return {"error": f"No estimation found for: {variable_name}"}


def update_estimate(
    variable_name: str,
    lo: float,
    hi: float,
    method: str = "unknown",
    source: str = "",
    source_reliability: float = 0.5,
    evidence_id: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """Add new evidence-based estimate and re-fuse.

    This is equivalent to create_estimate but semantically indicates
    an update to an existing estimation.
    """
    return create_estimate(
        variable_name=variable_name,
        lo=lo,
        hi=hi,
        method=method,
        source=source,
        source_reliability=source_reliability,
        evidence_id=evidence_id,
        project_id=project_id,
    )


def list_estimates(project_id: str = "") -> dict[str, Any]:
    """List all current estimations."""
    estimations = list(_ESTIMATION_STORE.values())
    return {
        "total": len(estimations),
        "estimations": estimations,
    }


# ---------------------------------------------------------------------------
# Batch fusion (order-independent)
# ---------------------------------------------------------------------------


def _batch_fuse(
    estimates: list[dict[str, Any]],
    variable_name: str,
) -> dict[str, Any]:
    """Fuse multiple estimates into a single interval.

    Order-independent: sorts by source_reliability descending before
    processing, ensuring strong reproducibility regardless of arrival order.

    Algorithm:
    1. Sort estimates by source_reliability (descending).
    2. Start with the most reliable estimate's interval.
    3. For each subsequent estimate:
       - If overlapping → shrink toward intersection (weighted by reliability)
       - If disjoint → expand to convex hull (conflict detected)
    4. Clamp to known bounds.
    """
    if not estimates:
        return {}

    # Sort by reliability descending (deterministic ordering)
    sorted_est = sorted(
        estimates,
        key=lambda e: e.get("source_reliability", 0.5),
        reverse=True,
    )

    # Start with most reliable
    first = sorted_est[0]
    current = Interval.from_dict(first["interval"])
    conflicts: list[dict[str, Any]] = []

    for est in sorted_est[1:]:
        other = Interval.from_dict(est["interval"])
        r = est.get("source_reliability", 0.5)

        overlap = current.intersect(other)
        if overlap is not None:
            # Overlapping: shrink toward intersection, weighted by reliability
            # Higher reliability → current moves more toward overlap
            new_lo = current.lo + (overlap.lo - current.lo) * r
            new_hi = current.hi + (overlap.hi - current.hi) * r
            current = Interval(new_lo, new_hi)
        else:
            # Disjoint: conflict detected — expand to convex hull
            current = current.convex_hull(other)
            conflicts.append({
                "estimate_id": est.get("estimate_id", ""),
                "source": est.get("source", ""),
                "interval": other.to_dict(),
                "type": "disjoint",
            })

    # Clamp to bounds
    bounds = _try_get_bounds(variable_name)
    if bounds:
        current = current.clamp(bounds["min"], bounds["max"])

    return {
        "interval": current.to_dict(),
        "point_estimate": current.midpoint,
        "spread_ratio": round(current.spread_ratio, 3) if current.midpoint != 0 else None,
        "estimates_count": len(estimates),
        "conflicts": conflicts,
        "has_conflicts": len(conflicts) > 0,
        "fused_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API: Fermi Trees (stepwise construction)
# ---------------------------------------------------------------------------


def create_fermi_tree(
    target_variable: str,
    operation: str = "multiply",
    project_id: str = "",
) -> dict[str, Any]:
    """Create a new Fermi decomposition tree.

    Args:
        target_variable: What this tree estimates (e.g., "MET-TAM").
        operation: Root operation ("multiply", "add", "divide", "subtract").

    Returns:
        dict with tree_id, target_variable, operation, children (empty).
    """
    tree_id = f"FERMI-{uuid4().hex[:6]}"

    tree: dict[str, Any] = {
        "tree_id": tree_id,
        "target_variable": target_variable,
        "operation": operation,
        "children": [],
        "evaluated": False,
        "result": None,
        "created_at": _now_iso(),
    }

    _FERMI_STORE[tree_id] = tree
    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "fermi", tree_id, tree)

    return tree


def add_fermi_leaf(
    tree_id: str,
    variable: str,
    lo: float,
    hi: float,
    source: str = "",
    evidence_id: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """Add a leaf node (concrete value) to a Fermi tree.

    Args:
        tree_id: The tree to add to.
        variable: Name of this component (e.g., "korean_household_count").
        lo: P10 lower bound.
        hi: P90 upper bound.
        source: Human-readable source description.
        evidence_id: Optional evidence ID for lineage.
            If not provided, lineage will show "unverified_leaf".

    Returns:
        The new leaf node dict.
    """
    if tree_id not in _FERMI_STORE:
        return {"error": f"Fermi tree not found: {tree_id}"}

    leaf: dict[str, Any] = {
        "type": "leaf",
        "variable": variable,
        "interval": Interval(lo, hi).to_dict(),
        "source": source,
        "evidence_id": evidence_id,
        "lineage_status": "verified" if evidence_id else "unverified_leaf",
    }

    _FERMI_STORE[tree_id]["children"].append(leaf)
    _FERMI_STORE[tree_id]["evaluated"] = False

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "fermi", tree_id, _FERMI_STORE[tree_id])

    return leaf


def add_fermi_subtree(
    parent_tree_id: str,
    variable: str,
    operation: str = "multiply",
    project_id: str = "",
) -> dict[str, Any]:
    """Add a subtree node to a Fermi tree.

    Returns a new tree_id for the subtree. Add leaves to this subtree
    using add_fermi_leaf with the subtree's tree_id.
    """
    if parent_tree_id not in _FERMI_STORE:
        return {"error": f"Fermi tree not found: {parent_tree_id}"}

    subtree_id = f"FERMI-{uuid4().hex[:6]}"

    subtree: dict[str, Any] = {
        "tree_id": subtree_id,
        "target_variable": variable,
        "operation": operation,
        "children": [],
        "evaluated": False,
        "result": None,
        "created_at": _now_iso(),
    }

    _FERMI_STORE[subtree_id] = subtree

    # Add reference in parent
    _FERMI_STORE[parent_tree_id]["children"].append({
        "type": "subtree",
        "variable": variable,
        "subtree_id": subtree_id,
    })
    _FERMI_STORE[parent_tree_id]["evaluated"] = False

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "fermi", subtree_id, subtree)
        save_engine_data(project_id, "fermi", parent_tree_id, _FERMI_STORE[parent_tree_id])

    return {"subtree_id": subtree_id, "variable": variable, "operation": operation}


def evaluate_fermi_tree(
    tree_id: str,
    project_id: str = "",
) -> dict[str, Any]:
    """Evaluate a Fermi tree using interval arithmetic.

    Recursively computes the root interval from all leaves.
    All leaves must be populated before evaluation.

    Returns:
        dict with tree_id, target_variable, result (interval),
        unverified_leaves count, lineage.
    """
    if tree_id not in _FERMI_STORE:
        return {"error": f"Fermi tree not found: {tree_id}"}

    tree = _FERMI_STORE[tree_id]
    children = tree["children"]

    if not children:
        return {"error": f"Fermi tree {tree_id} has no children. Add leaves first."}

    # Check all leaves are populated
    incomplete = [
        c for c in children
        if c["type"] == "leaf" and c.get("interval") is None
    ]
    if incomplete:
        return {
            "error": f"Fermi tree {tree_id} has {len(incomplete)} incomplete leaves.",
            "incomplete": [c["variable"] for c in incomplete],
        }

    # Evaluate recursively
    result_interval, unverified = _evaluate_node(tree)

    tree["evaluated"] = True
    tree["result"] = result_interval.to_dict()

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "fermi", tree_id, tree)

    return {
        "tree_id": tree_id,
        "target_variable": tree["target_variable"],
        "result": result_interval.to_dict(),
        "point_estimate": result_interval.midpoint,
        "spread_ratio": round(result_interval.spread_ratio, 3) if result_interval.midpoint != 0 else None,
        "unverified_leaves": unverified,
        "lineage": {
            "engine": "estimation",
            "function": "evaluate_fermi_tree",
            "tree_id": tree_id,
            "timestamp": _now_iso(),
        },
    }


def _evaluate_node(tree: dict[str, Any]) -> tuple[Interval, int]:
    """Recursively evaluate a Fermi tree node.

    Returns (result_interval, unverified_leaf_count).
    """
    operation = tree["operation"]
    children = tree["children"]
    unverified_total = 0

    child_intervals: list[Interval] = []
    for child in children:
        if child["type"] == "leaf":
            child_intervals.append(Interval.from_dict(child["interval"]))
            if child.get("lineage_status") == "unverified_leaf":
                unverified_total += 1
        elif child["type"] == "subtree":
            subtree = _FERMI_STORE.get(child["subtree_id"])
            if subtree is None:
                raise ValueError(f"Subtree not found: {child['subtree_id']}")
            sub_interval, sub_unverified = _evaluate_node(subtree)
            child_intervals.append(sub_interval)
            unverified_total += sub_unverified

    if not child_intervals:
        raise ValueError(f"No intervals to evaluate in tree {tree.get('tree_id')}")

    result = child_intervals[0]
    for iv in child_intervals[1:]:
        if operation == "multiply":
            result = result * iv
        elif operation == "add":
            result = result + iv
        elif operation == "subtract":
            result = result - iv
        elif operation == "divide":
            result = result / iv
        else:
            raise ValueError(f"Unknown operation: {operation}")

    return result, unverified_total
