"""CMIS v2 Reference Class Forecasting — empirical P10/P90 from past outcomes."""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_reference_class(metric_id: str, project_id: str = "") -> dict[str, Any]:
    """Build a reference class from past outcomes for a metric.

    1. Load all outcomes from learning engine (_OUTCOME_STORE + engine_store)
    2. Filter by metric_id
    3. Extract actual_value from each outcome
    4. Compute statistics: count, min, max, mean, p10, p50, p90

    Returns:
        {"metric_id": str, "outcome_count": int, "values": list[float],
         "statistics": {"min", "max", "mean", "p10", "p50", "p90"} | None,
         "sufficient": bool (count >= 3)}
    """
    outcomes = _load_outcomes_for_metric(metric_id, project_id)
    values = [o["actual_value"] for o in outcomes]
    count = len(values)
    sufficient = count >= 3

    statistics: dict[str, float] | None = None
    if sufficient:
        sorted_vals = sorted(values)
        statistics = {
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "mean": round(sum(sorted_vals) / count, 4),
            "p10": sorted_vals[int(count * 0.1)],
            "p50": sorted_vals[int(count * 0.5)],
            "p90": sorted_vals[int(count * 0.9)],
        }

    return {
        "metric_id": metric_id,
        "outcome_count": count,
        "values": values,
        "statistics": statistics,
        "sufficient": sufficient,
    }


def suggest_estimate(metric_id: str, project_id: str = "") -> dict[str, Any]:
    """Suggest initial P10/P90 interval based on reference class.

    If >= 3 outcomes: return {"suggested_lo": p10, "suggested_hi": p90, ...}
    If < 3: return {"sufficient": False, "reason": "Insufficient outcomes (N < 3)"}
    """
    ref = build_reference_class(metric_id, project_id)

    if not ref["sufficient"]:
        return {
            "metric_id": metric_id,
            "sufficient": False,
            "reason": f"Insufficient outcomes (N={ref['outcome_count']} < 3)",
        }

    stats = ref["statistics"]
    # stats is guaranteed non-None when sufficient is True
    assert stats is not None
    return {
        "metric_id": metric_id,
        "sufficient": True,
        "suggested_lo": stats["p10"],
        "suggested_hi": stats["p90"],
        "outcome_count": ref["outcome_count"],
        "statistics": stats,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_outcomes_for_metric(
    metric_id: str,
    project_id: str,
) -> list[dict[str, Any]]:
    """Load all outcomes matching metric_id from learning engine stores."""
    from cmis_v2.engines.learning import list_outcomes_by_metric

    return list_outcomes_by_metric(metric_id, project_id)
