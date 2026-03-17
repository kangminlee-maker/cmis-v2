"""CMIS v2 Belief Engine — Prior/belief distribution management.

TODO [FUTURE REVIEW]: Belief engine logic needs review and redesign.
Current implementation provides basic prior storage and simple Bayesian
update. The update formula, confidence propagation, and multi-source
fusion logic should be validated against statistical best practices
before production use.

This module is designed to be called by RLM's LM as a custom_tool.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from cmis_v2.generated.validators import validate_metric_id

# ---------------------------------------------------------------------------
# Module-level store
# ---------------------------------------------------------------------------

_BELIEF_STORE: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def set_prior(
    metric_id: str,
    point_estimate: float,
    confidence: float = 0.3,
    source: str = "expert_guess",
    distribution: dict | None = None,
) -> dict[str, Any]:
    """Set a prior belief for a metric.

    Args:
        metric_id: Must be a valid MetricId.
        point_estimate: Initial estimate.
        confidence: How confident (0.0-1.0, default 0.3 = low).
        source: Where this prior comes from ("expert_guess", "historical", "benchmark").
        distribution: Optional {"min": ..., "max": ...} range.

    Returns:
        Dict with belief_id, metric_id, point_estimate, confidence, source,
        distribution, version, updated_at.
    """
    if not validate_metric_id(metric_id):
        return {"error": f"Invalid metric ID: {metric_id}"}

    valid_sources = ("expert_guess", "historical", "benchmark")
    if source not in valid_sources:
        return {"error": f"Invalid source: {source!r}. Must be one of: {valid_sources}"}

    confidence = max(0.0, min(1.0, confidence))
    now = datetime.now().isoformat()

    belief_id = f"BLF-{uuid4().hex[:6]}"
    dist = distribution if distribution is not None else {"min": None, "max": None}

    belief: dict[str, Any] = {
        "belief_id": belief_id,
        "metric_id": metric_id,
        "point_estimate": point_estimate,
        "confidence": confidence,
        "source": source,
        "distribution": dist,
        "version": 1,
        "updated_at": now,
    }

    _BELIEF_STORE[metric_id] = belief
    return belief


def get_prior(metric_id: str) -> dict[str, Any]:
    """Get the current prior belief for a metric.

    Args:
        metric_id: The metric ID.

    Returns:
        The belief dict, or an error dict.
    """
    if metric_id not in _BELIEF_STORE:
        return {"error": f"No prior belief for metric: {metric_id}"}
    return _BELIEF_STORE[metric_id]


def update_belief(
    metric_id: str,
    new_evidence_value: float,
    evidence_confidence: float = 0.5,
) -> dict[str, Any]:
    """Update belief using simple weighted average (pseudo-Bayesian).

    TODO [FUTURE REVIEW]: Replace with proper Bayesian update.
    Current formula:
        updated = (prior * prior_conf + evidence * evd_conf) / (prior_conf + evd_conf)
        updated_conf = min(1.0, prior_conf + evd_conf * 0.5)

    This is a simplified approximation, not a true Bayesian posterior.

    Args:
        metric_id: The metric ID to update.
        new_evidence_value: New observed/estimated value.
        evidence_confidence: Confidence in the new evidence (0.0-1.0).

    Returns:
        Updated belief dict, or an error dict.
    """
    if metric_id not in _BELIEF_STORE:
        return {"error": f"No prior belief for metric: {metric_id}. Call set_prior() first."}

    evidence_confidence = max(0.0, min(1.0, evidence_confidence))
    belief = _BELIEF_STORE[metric_id]

    prior_val = belief["point_estimate"]
    prior_conf = belief["confidence"]

    # Pseudo-Bayesian weighted average
    denom = prior_conf + evidence_confidence
    if denom == 0:
        updated_val = new_evidence_value
    else:
        updated_val = (prior_val * prior_conf + new_evidence_value * evidence_confidence) / denom

    updated_conf = min(1.0, prior_conf + evidence_confidence * 0.5)
    now = datetime.now().isoformat()

    belief["point_estimate"] = updated_val
    belief["confidence"] = updated_conf
    belief["version"] = belief["version"] + 1
    belief["updated_at"] = now

    return belief


def list_beliefs() -> dict[str, Any]:
    """List all current beliefs.

    Returns:
        Dict with total count and list of all belief records.
    """
    beliefs = list(_BELIEF_STORE.values())
    return {
        "total": len(beliefs),
        "beliefs": beliefs,
    }
