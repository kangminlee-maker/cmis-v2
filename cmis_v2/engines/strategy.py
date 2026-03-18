"""CMIS v2 Strategy Engine — Strategy search and portfolio evaluation.

Generates strategy candidates from pattern matches and market analysis,
then evaluates and ranks them as a portfolio.

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

import warnings
from datetime import datetime
from typing import Any
from uuid import uuid4

# ---------------------------------------------------------------------------
# Module-level store
# ---------------------------------------------------------------------------

_STRATEGY_STORE: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_candidates_from_patterns(
    goal: str,
    pattern_matches: list[dict[str, Any]],
    constraints: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate strategy candidates by combining matched patterns.

    Each pattern with a positive fit_score becomes the basis for a candidate.
    Patterns are combined when complementary (different families).

    expected_impact is created as a placeholder structure (null values).
    The LM must fill impact values via set_strategy_impact() with evidence_id.
    """
    candidates: list[dict[str, Any]] = []
    constraints = constraints or {}

    # Individual pattern-based strategies
    for pm in pattern_matches:
        fit_score = pm.get("fit_score", 0.0)
        if fit_score <= 0.0:
            continue

        pattern_id = pm.get("pattern_id", "")
        pattern_name = pm.get("pattern_name", pattern_id)
        missing = pm.get("missing_traits", [])

        # Feasibility decreases with more missing traits
        feasibility = max(0.1, min(1.0, fit_score * 0.9))
        if constraints.get("budget") == "limited":
            feasibility *= 0.8
        if constraints.get("timeline") == "short":
            feasibility *= 0.85

        candidate: dict[str, Any] = {
            "strategy_id": f"STRAT-{uuid4().hex[:6]}",
            "name": f"Strategy based on {pattern_name}",
            "description": (
                f"Leverage the '{pattern_name}' pattern (fit={fit_score:.2f}) "
                f"to achieve: {goal}. "
                + (f"Gaps to fill: {missing}." if missing else "Pattern fully matched.")
            ),
            "based_on_patterns": [pattern_id],
            "expected_impact": {
                "revenue_change": None,
                "market_share_change": None,
                "_status": "pending_evidence",
                "_evidence_id": None,
                "_rationale": "",
            },
            "feasibility_score": round(feasibility, 3),
            "risk_factors": (
                [f"Missing traits: {missing}"] if missing else ["Low risk — pattern already present"]
            ),
            "required_capabilities": (
                [f"Develop: {t}" for t in missing[:3]] if missing else ["Execution capability"]
            ),
            "evidence_lineage": {
                "impact_evidence_ids": [],
                "impact_set_at": None,
                "impact_method": None,
            },
        }
        candidates.append(candidate)

    # If multiple patterns exist, create a combined strategy
    if len(pattern_matches) >= 2:
        top_two = sorted(pattern_matches, key=lambda p: p.get("fit_score", 0), reverse=True)[:2]
        combined_ids = [p.get("pattern_id", "") for p in top_two]
        combined_names = [p.get("pattern_name", p.get("pattern_id", "")) for p in top_two]
        avg_fit = sum(p.get("fit_score", 0) for p in top_two) / 2

        combined: dict[str, Any] = {
            "strategy_id": f"STRAT-{uuid4().hex[:6]}",
            "name": f"Combined: {' + '.join(combined_names)}",
            "description": (
                f"Hybrid strategy combining {combined_names[0]} and {combined_names[1]} "
                f"to achieve: {goal}."
            ),
            "based_on_patterns": combined_ids,
            "expected_impact": {
                "revenue_change": None,
                "market_share_change": None,
                "_status": "pending_evidence",
                "_evidence_id": None,
                "_rationale": "",
            },
            "feasibility_score": round(max(0.1, avg_fit * 0.75), 3),
            "risk_factors": [
                "Integration complexity between patterns",
                "Higher resource requirements",
            ],
            "required_capabilities": ["Cross-pattern integration", "Resource coordination"],
            "evidence_lineage": {
                "impact_evidence_ids": [],
                "impact_set_at": None,
                "impact_method": None,
            },
        }
        candidates.append(combined)

    return candidates


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_strategies(
    goal_description: str,
    snapshot_id: str = "",
    pattern_matches: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
    project_id: str = "",
) -> dict[str, Any]:
    """Search for strategy candidates based on market analysis results.

    Uses pattern matches and market structure to generate strategy options.
    Each strategy is a combination of patterns that address identified gaps.

    Note: expected_impact values are initially null. The LM must call
    set_strategy_impact() with evidence_id to populate them.

    Args:
        goal_description: What the strategy should achieve.
        snapshot_id: Reality snapshot reference (for context).
        pattern_matches: Results from match_patterns() (fit scores, gaps).
        constraints: Business constraints (budget, timeline, capabilities).

    Returns:
        dict with strategy_search_id, goal, candidates, lineage.
    """
    now = datetime.now().isoformat()
    search_id = f"STR-{uuid4().hex[:6]}"

    candidates: list[dict[str, Any]] = []
    if pattern_matches:
        candidates = _generate_candidates_from_patterns(
            goal_description, pattern_matches, constraints
        )

    # Store each candidate
    for c in candidates:
        _STRATEGY_STORE[c["strategy_id"]] = c
        if project_id:
            from cmis_v2.engine_store import save_engine_data
            save_engine_data(project_id, "strategy", c["strategy_id"], c)

    result: dict[str, Any] = {
        "strategy_search_id": search_id,
        "goal": goal_description,
        "candidates": candidates,
        "lineage": {
            "engine": "strategy",
            "function": "search_strategies",
            "snapshot_id": snapshot_id,
            "pattern_count": len(pattern_matches) if pattern_matches else 0,
            "candidates_generated": len(candidates),
            "timestamp": now,
        },
    }
    return result


def set_strategy_impact(
    strategy_id: str,
    revenue_change: str,
    market_share_change: str,
    evidence_id: str,
    rationale: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """Set the expected impact for a strategy, linked to evidence.

    This function exists because expected_impact must not be derived from
    hardcoded coefficients. The LM analyzes evidence and provides impact
    estimates with an explicit link to the supporting evidence record.

    Args:
        strategy_id: The strategy to update.
        revenue_change: Expected revenue change (e.g., "+15%", "-5%").
        market_share_change: Expected market share change (e.g., "+8%").
        evidence_id: ID of the evidence record supporting this estimate.
            Required. The function returns an error if empty.
        rationale: Explanation of how the evidence supports this estimate.
        project_id: Optional project ID for file-based persistence.

    Returns:
        The updated strategy dict, or an error dict.
    """
    if not evidence_id:
        return {
            "error": (
                "evidence_id is required for set_strategy_impact. "
                "Impact estimates must be traceable to evidence."
            )
        }

    candidate = _STRATEGY_STORE.get(strategy_id)
    if candidate is None:
        if project_id:
            from cmis_v2.engine_store import load_engine_data
            candidate = load_engine_data(project_id, "strategy", strategy_id)
            if candidate is not None:
                _STRATEGY_STORE[strategy_id] = candidate
        if candidate is None:
            return {"error": f"Strategy not found: {strategy_id}"}

    now = datetime.now().isoformat()

    candidate["expected_impact"] = {
        "revenue_change": revenue_change,
        "market_share_change": market_share_change,
        "_status": "evidence_linked",
        "_evidence_id": evidence_id,
        "_rationale": rationale,
    }

    # Update evidence lineage
    lineage = candidate.setdefault("evidence_lineage", {
        "impact_evidence_ids": [],
        "impact_set_at": None,
        "impact_method": None,
    })
    if evidence_id not in lineage.get("impact_evidence_ids", []):
        lineage.setdefault("impact_evidence_ids", []).append(evidence_id)
    lineage["impact_set_at"] = now
    lineage["impact_method"] = "lm_evidence_based"

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "strategy", strategy_id, candidate)

    return candidate


def evaluate_portfolio(
    strategy_ids: list[str],
    value_records: list[dict[str, Any]] | None = None,
    policy_ref: str = "decision_balanced",
    pending_policy: str = "exclude",
    project_id: str = "",
) -> dict[str, Any]:
    """Evaluate and rank a portfolio of strategy candidates.

    Ranks strategies by feasibility_score. Impact and risk scores are
    derived from the stored candidate data.

    Strategies whose expected_impact has not been set via
    set_strategy_impact() (i.e., _status is "pending_evidence") receive
    an impact_score of 0.0 and a lineage warning.

    Args:
        strategy_ids: List of strategy IDs to evaluate.
        value_records: Optional metric value records for context.
        policy_ref: Policy mode for evaluation thresholds.
        pending_policy: How to handle pending_evidence items.
            - "exclude": skip pending items from ranking, is_complete=False.
            - "fail": return error if any pending items exist.
            - "partial": include pending items separately in pending_items.

    Returns:
        dict with portfolio_id, ranked_strategies, trade_offs, is_complete,
        pending_items, lineage.
    """
    if pending_policy not in ("exclude", "fail", "partial"):
        return {"error": f"Invalid pending_policy: {pending_policy!r}. Must be one of: exclude, fail, partial"}

    now = datetime.now().isoformat()
    portfolio_id = f"PORT-{uuid4().hex[:6]}"

    ranked: list[dict[str, Any]] = []
    pending_items: list[dict[str, Any]] = []
    missing_ids: list[str] = []
    lineage_warnings: list[str] = []

    for sid in strategy_ids:
        candidate = _STRATEGY_STORE.get(sid)
        if candidate is None:
            if project_id:
                from cmis_v2.engine_store import load_engine_data
                candidate = load_engine_data(project_id, "strategy", sid)
                if candidate is not None:
                    _STRATEGY_STORE[sid] = candidate
        if candidate is None:
            missing_ids.append(sid)
            continue

        feasibility = candidate.get("feasibility_score", 0.5)

        # --- Impact score from evidence-linked expected_impact ---
        expected_impact = candidate.get("expected_impact", {})
        impact_status = expected_impact.get("_status", "pending_evidence")

        is_pending = (
            impact_status == "pending_evidence"
            or expected_impact.get("revenue_change") is None
        )

        if is_pending:
            # Handle according to pending_policy
            if pending_policy == "fail":
                return {
                    "error": (
                        f"Strategy '{sid}' has pending_evidence impact. "
                        f"Set impact via set_strategy_impact() before evaluating, "
                        f"or use pending_policy='exclude' or 'partial'."
                    )
                }

            pending_entry: dict[str, Any] = {
                "strategy_id": sid,
                "name": candidate.get("name", ""),
                "impact_evidence_status": "pending_evidence",
                "feasibility_score": round(feasibility, 3),
            }

            if pending_policy == "exclude":
                pending_items.append(pending_entry)
                lineage_warnings.append(
                    f"Strategy '{sid}': excluded from ranking (pending_evidence). "
                    f"Call set_strategy_impact() with evidence_id first."
                )
                continue
            elif pending_policy == "partial":
                pending_items.append(pending_entry)
                lineage_warnings.append(
                    f"Strategy '{sid}': expected_impact not set via "
                    f"set_strategy_impact(). Impact score defaults to 0.0."
                )

            impact_score = 0.0
        else:
            impact_str = expected_impact.get("revenue_change", "+0%")
            try:
                impact_pct = int(str(impact_str).replace("+", "").replace("%", ""))
            except (ValueError, AttributeError):
                impact_pct = 0
            impact_score = min(1.0, abs(impact_pct) / 40.0)

        # Risk-adjusted = feasibility weighted by risk factor count
        risk_count = len(candidate.get("risk_factors", []))
        risk_penalty = min(0.3, risk_count * 0.1)
        risk_adjusted = max(0.0, feasibility - risk_penalty)

        overall = round((impact_score * 0.4 + feasibility * 0.35 + risk_adjusted * 0.25), 3)

        recommendation: str
        if overall >= 0.6:
            recommendation = "proceed"
        elif overall >= 0.35:
            recommendation = "consider"
        else:
            recommendation = "defer"

        entry: dict[str, Any] = {
            "strategy_id": sid,
            "name": candidate.get("name", ""),
            "overall_score": overall,
            "scores": {
                "impact": round(impact_score, 3),
                "feasibility": round(feasibility, 3),
                "risk_adjusted": round(risk_adjusted, 3),
            },
            "recommendation": recommendation,
            "impact_evidence_status": impact_status,
        }

        # Attach evidence lineage if available
        evidence_lineage = candidate.get("evidence_lineage", {})
        if evidence_lineage.get("impact_evidence_ids"):
            entry["impact_evidence_ids"] = evidence_lineage["impact_evidence_ids"]

        ranked.append(entry)

    # Sort by overall_score descending
    ranked.sort(key=lambda r: r["overall_score"], reverse=True)

    # Determine completeness
    is_complete = len(pending_items) == 0

    # Generate trade-off observations
    trade_offs: list[str] = []
    if len(ranked) >= 2:
        top = ranked[0]
        second = ranked[1]
        if top["scores"]["feasibility"] < second["scores"]["feasibility"]:
            trade_offs.append(
                f"'{top['name']}' has higher impact but lower feasibility than '{second['name']}'."
            )
        if top["scores"]["risk_adjusted"] < second["scores"]["risk_adjusted"]:
            trade_offs.append(
                f"'{top['name']}' carries more risk than '{second['name']}'."
            )
    if not trade_offs:
        trade_offs.append("No significant trade-offs detected among candidates.")

    result: dict[str, Any] = {
        "portfolio_id": portfolio_id,
        "ranked_strategies": ranked,
        "trade_offs": trade_offs,
        "is_complete": is_complete,
        "pending_items": pending_items,
        "_lineage_warnings": lineage_warnings,
        "lineage": {
            "engine": "strategy",
            "function": "evaluate_portfolio",
            "policy_ref": policy_ref,
            "pending_policy": pending_policy,
            "strategies_evaluated": len(ranked),
            "missing_ids": missing_ids,
            "timestamp": now,
        },
    }
    return result
