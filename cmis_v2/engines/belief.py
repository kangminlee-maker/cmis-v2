"""CMIS v2 Belief Engine — DEPRECATED.

This module is replaced by estimation.py (Estimation Engine).
All functions delegate to estimation.py for backward compatibility.

Deprecation reason (8-Agent Panel Review, 2026-03-25):
- Weighted average update is not Bayesian and has confidence monotonic increase
- No interval support, no Fermi decomposition, no constraint propagation
- confidence→sigma conversion approach (접근법 A) rejected by 8/8 panel consensus
- Replaced by pure Interval-based estimation (접근법 B)

See: .claude/sessions/onto-review/20260325-9780126d/philosopher_synthesis.md
"""

from __future__ import annotations

from typing import Any

from cmis_v2.engines.estimation import (
    create_estimate,
    get_estimate,
    list_estimates,
    update_estimate,
)

# ---------------------------------------------------------------------------
# Deprecated API — delegates to Estimation Engine
# ---------------------------------------------------------------------------


def set_prior(
    metric_id: str,
    point_estimate: float,
    confidence: float = 0.3,
    source: str = "expert_guess",
    distribution: dict | None = None,
    project_id: str = "",
) -> dict[str, Any]:
    """[DEPRECATED → create_estimate] Set a prior belief for a metric."""
    # Convert confidence to a rough P10/P90 spread
    spread = 0.5 * (1 - confidence)  # conf=0.3 → ±35%, conf=0.9 → ±5%
    half = abs(point_estimate) * spread if point_estimate != 0 else 1.0

    lo = point_estimate - half
    hi = point_estimate + half

    # Use distribution if provided
    if distribution and distribution.get("min") is not None:
        lo = distribution["min"]
    if distribution and distribution.get("max") is not None:
        hi = distribution["max"]

    result = create_estimate(
        variable_name=metric_id,
        lo=lo,
        hi=hi,
        method=source,
        source=source,
        source_reliability=confidence,
        project_id=project_id,
    )

    # Return in legacy format
    return {
        "belief_id": result.get("estimate_id", ""),
        "metric_id": metric_id,
        "point_estimate": result.get("point_estimate", point_estimate),
        "confidence": confidence,
        "source": source,
        "distribution": {"min": lo, "max": hi},
        "version": 1,
        "updated_at": result.get("created_at", ""),
        "_deprecated": "Use create_estimate() instead",
    }


def get_prior(metric_id: str, project_id: str = "") -> dict[str, Any]:
    """[DEPRECATED → get_estimate] Get the current prior belief."""
    result = get_estimate(metric_id, project_id)
    if "error" in result:
        return result

    # Convert to legacy format
    fused = result.get("fused")
    latest = result["estimates"][-1] if result.get("estimates") else None

    if fused:
        interval = fused["interval"]
    elif latest:
        interval = latest["interval"]
    else:
        return {"error": f"No estimation data for: {metric_id}"}

    return {
        "belief_id": latest.get("estimate_id", "") if latest else "",
        "metric_id": metric_id,
        "point_estimate": interval.get("midpoint", 0),
        "confidence": latest.get("source_reliability", 0.5) if latest else 0.5,
        "source": latest.get("source", "") if latest else "",
        "distribution": {"min": interval.get("lo"), "max": interval.get("hi")},
        "version": result.get("version", 1),
        "updated_at": result.get("updated_at", ""),
        "_deprecated": "Use get_estimate() instead",
    }


def update_belief(
    metric_id: str,
    new_evidence_value: float,
    evidence_confidence: float = 0.5,
    project_id: str = "",
) -> dict[str, Any]:
    """[DEPRECATED → update_estimate] Update belief with new evidence."""
    spread = 0.5 * (1 - evidence_confidence)
    half = abs(new_evidence_value) * spread if new_evidence_value != 0 else 1.0

    result = update_estimate(
        variable_name=metric_id,
        lo=new_evidence_value - half,
        hi=new_evidence_value + half,
        source_reliability=evidence_confidence,
        project_id=project_id,
    )

    if "error" in result:
        return result

    # Get fused result
    me = get_estimate(metric_id, project_id)
    fused = me.get("fused", {})
    interval = fused.get("interval", result.get("interval", {}))

    return {
        "belief_id": result.get("estimate_id", ""),
        "metric_id": metric_id,
        "point_estimate": interval.get("midpoint", new_evidence_value),
        "confidence": evidence_confidence,
        "source": "",
        "distribution": {"min": interval.get("lo"), "max": interval.get("hi")},
        "version": me.get("version", 1),
        "updated_at": me.get("updated_at", ""),
        "_deprecated": "Use update_estimate() instead",
    }


def list_beliefs(project_id: str = "") -> dict[str, Any]:
    """[DEPRECATED → list_estimates] List all current beliefs."""
    result = list_estimates(project_id)
    return {
        "total": result.get("total", 0),
        "beliefs": result.get("estimations", []),
        "_deprecated": "Use list_estimates() instead",
    }
