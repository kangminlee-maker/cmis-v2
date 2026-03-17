"""CMIS v2 Learning Engine — Outcome recording and prediction accuracy tracking.

Records actual outcomes, compares them against predictions (from the value
engine or belief engine), and provides feedback loops for system improvement.

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from cmis_v2.generated.validators import validate_metric_id

# ---------------------------------------------------------------------------
# Module-level store
# ---------------------------------------------------------------------------

_OUTCOME_STORE: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_predicted_value(metric_id: str, project_id: str = "") -> float | None:
    """Try to get a predicted value from value engine or belief engine."""
    # Try value engine first
    try:
        from cmis_v2.engines.value import get_metric_value

        val_record = get_metric_value(metric_id, project_id=project_id)
        if "error" not in val_record and val_record.get("point_estimate") is not None:
            return val_record["point_estimate"]
    except Exception:
        pass

    # Try belief engine
    try:
        from cmis_v2.engines.belief import get_prior

        belief = get_prior(metric_id, project_id=project_id)
        if "error" not in belief and belief.get("point_estimate") is not None:
            return belief["point_estimate"]
    except Exception:
        pass

    return None


def _accuracy_rating(error_pct: float) -> str:
    """Classify prediction accuracy based on absolute error percentage."""
    abs_err = abs(error_pct)
    if abs_err < 10.0:
        return "accurate"
    elif abs_err < 30.0:
        return "acceptable"
    else:
        return "poor"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_outcome(
    metric_id: str,
    actual_value: float,
    measured_at: str = "",
    source: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """Record an actual outcome for a metric.

    Compares the actual value against the predicted value (from the value
    engine or belief engine) and computes error metrics.

    Args:
        metric_id: Must be a valid MetricId.
        actual_value: The actual observed value.
        measured_at: ISO timestamp of measurement (defaults to now).
        source: Where this outcome was observed.
        project_id: Optional project ID for file-based persistence.

    Returns:
        Dict with outcome_id, metric_id, actual_value, measured_at, source,
        and comparison against predicted value.
    """
    if not validate_metric_id(metric_id):
        return {"error": f"Invalid metric ID: {metric_id}"}

    now = datetime.now().isoformat()
    if not measured_at:
        measured_at = now

    outcome_id = f"OUT-{uuid4().hex[:6]}"

    # Build comparison
    predicted = _get_predicted_value(metric_id, project_id=project_id)
    comparison: dict[str, Any]
    if predicted is not None:
        error = actual_value - predicted
        if predicted != 0:
            error_pct = (error / predicted) * 100.0
        else:
            error_pct = 0.0 if actual_value == 0 else 100.0
        comparison = {
            "predicted_value": predicted,
            "error": error,
            "error_pct": round(error_pct, 2),
            "accuracy_rating": _accuracy_rating(error_pct),
        }
    else:
        comparison = {
            "predicted_value": None,
            "error": None,
            "error_pct": None,
            "accuracy_rating": "no_prediction",
        }

    outcome: dict[str, Any] = {
        "outcome_id": outcome_id,
        "metric_id": metric_id,
        "actual_value": actual_value,
        "measured_at": measured_at,
        "source": source,
        "comparison": comparison,
        "recorded_at": now,
    }

    # Store keyed by outcome_id; also track by metric_id for lookups
    _OUTCOME_STORE[outcome_id] = outcome
    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "learning", outcome_id, outcome)
    return outcome


def get_learning_summary(project_id: str = "") -> dict[str, Any]:
    """Get summary of all recorded outcomes and prediction accuracy.

    Args:
        project_id: Optional project ID. If provided, loads persisted
                     outcomes from disk when in-memory store is empty.

    Returns:
        Dict with total_outcomes, accuracy breakdown, metrics_tracked, and
        suggestions for improving predictions.
    """
    # If project_id given, load persisted outcomes into memory
    if project_id:
        from cmis_v2.engine_store import list_engine_keys, load_engine_data
        keys = list_engine_keys(project_id, "learning")
        for key in keys:
            if key not in _OUTCOME_STORE:
                data = load_engine_data(project_id, "learning", key)
                if data is not None:
                    _OUTCOME_STORE[key] = data

    outcomes = list(_OUTCOME_STORE.values())
    total = len(outcomes)

    accuracy: dict[str, int] = {"accurate": 0, "acceptable": 0, "poor": 0}
    metrics_tracked: set[str] = set()
    metric_errors: dict[str, list[float]] = {}

    for o in outcomes:
        metrics_tracked.add(o["metric_id"])
        rating = o["comparison"].get("accuracy_rating", "no_prediction")
        if rating in accuracy:
            accuracy[rating] += 1

        error_pct = o["comparison"].get("error_pct")
        if error_pct is not None:
            metric_errors.setdefault(o["metric_id"], []).append(error_pct)

    # Generate suggestions based on systematic errors
    suggestions: list[str] = []
    for mid, errors in metric_errors.items():
        if len(errors) >= 1:
            avg_error = sum(errors) / len(errors)
            if abs(avg_error) > 10.0:
                direction = "overestimate" if avg_error < 0 else "underestimate"
                suggestions.append(
                    f"{mid} predictions tend to {direction} by {abs(avg_error):.0f}%"
                )

    return {
        "total_outcomes": total,
        "accuracy": accuracy,
        "metrics_tracked": sorted(metrics_tracked),
        "suggestions": suggestions,
    }


def apply_learnings(metric_id: str, project_id: str = "") -> dict[str, Any]:
    """Apply accumulated learnings to update belief for a metric.

    If outcomes exist for this metric, updates the belief using the
    average actual value from outcomes.

    Args:
        metric_id: The metric ID to apply learnings for.
        project_id: Optional project ID for persistence.

    Returns:
        Updated belief dict, or info message if no outcomes exist.
    """
    if not validate_metric_id(metric_id):
        return {"error": f"Invalid metric ID: {metric_id}"}

    # Load from disk if needed (same pattern as get_learning_summary)
    if project_id and not _OUTCOME_STORE:
        from cmis_v2.engine_store import list_engine_keys, load_engine_data

        for key in list_engine_keys(project_id, "learning"):
            if key not in _OUTCOME_STORE:
                loaded = load_engine_data(project_id, "learning", key)
                if loaded is not None:
                    _OUTCOME_STORE[key] = loaded

    # Gather outcomes for this metric
    metric_outcomes = [
        o for o in _OUTCOME_STORE.values() if o["metric_id"] == metric_id
    ]

    if not metric_outcomes:
        return {"info": "no outcomes for this metric"}

    # Compute average actual value
    avg_actual = sum(o["actual_value"] for o in metric_outcomes) / len(metric_outcomes)

    # Update belief with the average actual value as new evidence
    from cmis_v2.engines.belief import get_prior, update_belief

    prior = get_prior(metric_id, project_id=project_id)
    if "error" in prior:
        # No prior exists; cannot update
        return {"info": f"No prior belief for {metric_id}. Set a prior first."}

    updated = update_belief(
        metric_id=metric_id,
        new_evidence_value=avg_actual,
        evidence_confidence=0.7,  # outcomes are high-confidence evidence
        project_id=project_id,
    )

    return {
        "metric_id": metric_id,
        "outcomes_used": len(metric_outcomes),
        "average_actual": avg_actual,
        "updated_belief": updated,
    }
