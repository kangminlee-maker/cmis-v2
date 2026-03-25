"""CMIS v2 Calibration — source_reliability correction from outcomes."""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Default reliabilities (fallback when no calibration data)
# ---------------------------------------------------------------------------

_DEFAULT_RELIABILITY: dict[str, float] = {
    "official": 0.8,
    "curated": 0.7,
    "commercial": 0.6,
    "web": 0.5,
    "estimation_output": 0.4,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_calibration(
    project_id: str = "",
    metric_id: str = "",
) -> dict[str, Any]:
    """Compute calibration data from past outcomes.

    1. Load all outcomes
    2. If metric_id specified, filter by it
    3. Group by source_tier (from the evidence that produced each outcome)
    4. For each group: count accurate/acceptable/poor
    5. Compute calibrated_reliability = accurate_ratio * 0.9 + acceptable_ratio * 0.5

    Returns:
        {"total_outcomes": int, "by_metric": {...}, "by_source_tier": {...},
         "suggested_adjustments": {...}}
    """
    outcomes = _load_all_outcomes(project_id)

    if metric_id:
        outcomes = [o for o in outcomes if o.get("metric_id") == metric_id]

    total = len(outcomes)

    # Group by metric_id
    by_metric: dict[str, dict[str, int]] = {}
    for o in outcomes:
        mid = o.get("metric_id", "unknown")
        rating = o.get("comparison", {}).get("accuracy_rating", "no_prediction")
        bucket = by_metric.setdefault(mid, {"accurate": 0, "acceptable": 0, "poor": 0})
        if rating in bucket:
            bucket[rating] += 1

    # Group by source_tier
    by_source_tier: dict[str, dict[str, int]] = {}
    for o in outcomes:
        tier = _extract_source_tier(o)
        rating = o.get("comparison", {}).get("accuracy_rating", "no_prediction")
        bucket = by_source_tier.setdefault(tier, {"accurate": 0, "acceptable": 0, "poor": 0})
        if rating in bucket:
            bucket[rating] += 1

    # Compute suggested adjustments per source_tier
    suggested_adjustments: dict[str, float] = {}
    for tier, counts in by_source_tier.items():
        tier_total = counts["accurate"] + counts["acceptable"] + counts["poor"]
        if tier_total == 0:
            continue
        accurate_ratio = counts["accurate"] / tier_total
        acceptable_ratio = counts["acceptable"] / tier_total
        calibrated = accurate_ratio * 0.9 + acceptable_ratio * 0.5
        suggested_adjustments[tier] = round(calibrated, 3)

    return {
        "total_outcomes": total,
        "by_metric": by_metric,
        "by_source_tier": by_source_tier,
        "suggested_adjustments": suggested_adjustments,
    }


def calibrated_reliability(
    source_tier: str,
    metric_id: str = "",
    project_id: str = "",
) -> float:
    """Return calibrated source_reliability.

    If calibration data exists and is sufficient (>= 5 outcomes): return calibrated value.
    Otherwise: return default from _DEFAULT_RELIABILITY.
    """
    cal = compute_calibration(project_id=project_id, metric_id=metric_id)

    tier_data = cal.get("by_source_tier", {}).get(source_tier)
    if tier_data is not None:
        tier_total = tier_data["accurate"] + tier_data["acceptable"] + tier_data["poor"]
        if tier_total >= 5:
            adjustment = cal.get("suggested_adjustments", {}).get(source_tier)
            if adjustment is not None:
                return adjustment

    return _DEFAULT_RELIABILITY.get(source_tier, 0.5)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_all_outcomes(project_id: str) -> list[dict[str, Any]]:
    """Load all outcomes from learning engine stores."""
    from cmis_v2.engines.learning import _OUTCOME_STORE

    # Load from engine_store if project_id is given
    if project_id:
        from cmis_v2.engine_store import list_engine_keys, load_engine_data

        keys = list_engine_keys(project_id, "learning")
        for key in keys:
            if key not in _OUTCOME_STORE:
                data = load_engine_data(project_id, "learning", key)
                if data is not None:
                    _OUTCOME_STORE[key] = data

    return list(_OUTCOME_STORE.values())


def _extract_source_tier(outcome: dict[str, Any]) -> str:
    """Extract source_tier from an outcome record.

    The source field in outcome records contains a human-readable description.
    We derive tier from common patterns; default to "unknown".
    """
    source = outcome.get("source", "").lower()

    if not source:
        return "unknown"

    # Match known tier keywords in source string
    tier_keywords: dict[str, list[str]] = {
        "official": ["kosis", "dart", "government", "official", "census"],
        "curated": ["curated", "research", "academic", "journal"],
        "commercial": ["commercial", "paid", "subscription", "gartner", "idc"],
        "web": ["web", "blog", "news", "article", "search"],
        "estimation_output": ["estimation", "fermi", "estimate", "predicted"],
    }

    for tier, keywords in tier_keywords.items():
        for keyword in keywords:
            if keyword in source:
                return tier

    return "unknown"
