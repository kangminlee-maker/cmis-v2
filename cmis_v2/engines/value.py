"""CMIS v2 Value Engine — Metric evaluation (4-Method Fusion).

MVP scope: Creates metric structures with placeholder values that the LM
can populate via set_metric_value().  Actual 4-Method Fusion (top-down,
bottom-up, fermi, proxy) computation is deferred to subsequent phases.

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from cmis_v2.generated.types import METRIC_REGISTRY
from cmis_v2.generated.validators import validate_metric_id

# ---------------------------------------------------------------------------
# Module-level store
# ---------------------------------------------------------------------------

_VALUE_STORE: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Valid methods
# ---------------------------------------------------------------------------

_VALID_METHODS = frozenset({"top_down", "bottom_up", "fermi", "proxy", "unknown"})

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_metrics(
    metric_ids: list[str],
    context: dict[str, Any] | None = None,
    snapshot_id: str = "",
    evidence_id: str = "",
    policy_ref: str = "decision_balanced",
    project_id: str = "",
) -> dict[str, Any]:
    """Evaluate metrics using available evidence and snapshot data.

    MVP: Returns metric structure with placeholder values (point_estimate=None).
    The LM fills in estimates via set_metric_value().

    Args:
        metric_ids: List of metric IDs to evaluate.
        context: Optional additional context for evaluation.
        snapshot_id: Optional snapshot ID for graph-based evaluation.
        evidence_id: Optional evidence ID for evidence-based evaluation.
        policy_ref: Policy reference for quality thresholds (default "decision_balanced").

    Returns:
        dict with value_records, policy_ref, lineage.
    """
    # Validate metric_ids
    invalid = [m for m in metric_ids if not validate_metric_id(m)]
    if invalid:
        return {"error": f"Invalid metric IDs: {invalid}"}

    now = datetime.now().isoformat()
    value_records: list[dict[str, Any]] = []

    for mid in metric_ids:
        registry_entry = METRIC_REGISTRY.get(mid, {})

        record: dict[str, Any] = {
            "metric_id": mid,
            "point_estimate": None,
            "distribution": {"min": None, "max": None},
            "confidence": 0.0,
            "method": "unknown",
            "quality": {
                "status": "insufficient",
                "literal_ratio": 0.0,
                "evidence_count": 0,
            },
            "lineage": {
                "engine": "value",
                "evidence_id": evidence_id,
                "snapshot_id": snapshot_id,
                "method_details": "",
            },
            "metadata": {
                "description": registry_entry.get("description", ""),
                "unit": registry_entry.get("unit", ""),
                "aggregation": registry_entry.get("aggregation", ""),
            },
        }

        _VALUE_STORE[mid] = record
        if project_id:
            from cmis_v2.engine_store import save_engine_data
            save_engine_data(project_id, "value", mid, record)
        value_records.append(record)

    return {
        "value_records": value_records,
        "policy_ref": policy_ref,
        "lineage": {
            "engine": "value",
            "snapshot_id": snapshot_id,
            "evidence_id": evidence_id,
            "timestamp": now,
        },
    }


def set_metric_value(
    metric_id: str,
    point_estimate: float,
    confidence: float = 0.5,
    method: str = "unknown",
    evidence_summary: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """Manually set a metric value (used by LM after analysis).

    Args:
        metric_id: The metric ID to set.
        point_estimate: The estimated value.
        confidence: Confidence score 0.0-1.0 (default 0.5).
        method: Estimation method used ("top_down", "bottom_up", "fermi", "proxy", "unknown").
        evidence_summary: Summary of evidence supporting this estimate.

    Returns:
        The updated value record, or an error dict.
    """
    if not validate_metric_id(metric_id):
        return {"error": f"Invalid metric ID: {metric_id}"}

    if method not in _VALID_METHODS:
        return {"error": f"Invalid method: {method!r}. Must be one of: {sorted(_VALID_METHODS)}"}

    confidence = max(0.0, min(1.0, confidence))

    if metric_id not in _VALUE_STORE:
        # Create a new record if one doesn't exist
        registry_entry = METRIC_REGISTRY.get(metric_id, {})
        _VALUE_STORE[metric_id] = {
            "metric_id": metric_id,
            "point_estimate": None,
            "distribution": {"min": None, "max": None},
            "confidence": 0.0,
            "method": "unknown",
            "quality": {
                "status": "insufficient",
                "literal_ratio": 0.0,
                "evidence_count": 0,
            },
            "lineage": {
                "engine": "value",
                "evidence_id": "",
                "snapshot_id": "",
                "method_details": "",
            },
            "metadata": {
                "description": registry_entry.get("description", ""),
                "unit": registry_entry.get("unit", ""),
                "aggregation": registry_entry.get("aggregation", ""),
            },
        }

    record = _VALUE_STORE[metric_id]
    record["point_estimate"] = point_estimate
    record["confidence"] = confidence
    record["method"] = method
    record["quality"]["status"] = "ok" if confidence >= 0.3 else "unverified"
    record["lineage"]["method_details"] = evidence_summary

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "value", metric_id, record)

    return record


def get_metric_value(metric_id: str, project_id: str = "") -> dict[str, Any]:
    """Retrieve a metric value record by ID.

    Args:
        metric_id: The metric ID.
        project_id: Optional project ID for file-based lookup.

    Returns:
        The value record dict, or an error dict.
    """
    if metric_id in _VALUE_STORE:
        return _VALUE_STORE[metric_id]
    if project_id:
        from cmis_v2.engine_store import load_engine_data
        data = load_engine_data(project_id, "value", metric_id)
        if data is not None:
            _VALUE_STORE[metric_id] = data
            return data
    return {"error": f"Metric value not found: {metric_id}"}
