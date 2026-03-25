"""CMIS v2 Policy Engine — Policy-driven quality gates.

Loads policy definitions from config/policies.yaml and validates analysis
results against configured thresholds (evidence gates, value gates, etc.).

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Policy loading and cache
# ---------------------------------------------------------------------------

_POLICIES_PATH: Path = Path(__file__).parent.parent.parent / "config" / "policies.yaml"
_POLICY_CACHE: dict[str, Any] | None = None


def _load_policy_pack() -> dict[str, Any]:
    """Load and cache the full policy pack from policies.yaml."""
    global _POLICY_CACHE
    if _POLICY_CACHE is not None:
        return _POLICY_CACHE

    if not _POLICIES_PATH.is_file():
        _POLICY_CACHE = {}
        return _POLICY_CACHE

    with open(_POLICIES_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    _POLICY_CACHE = raw.get("policy_pack", {})
    return _POLICY_CACHE


def _resolve_mode(policy_id: str) -> dict[str, Any] | None:
    """Resolve a policy_id (mode name) to its full mode definition."""
    pack = _load_policy_pack()
    modes = pack.get("modes", {})
    return modes.get(policy_id)


def _get_profile(profile_type: str, profile_name: str) -> dict[str, Any]:
    """Get a specific profile by type and name."""
    pack = _load_policy_pack()
    profiles = pack.get("profiles", {})
    type_profiles = profiles.get(f"{profile_type}_profiles", {})
    return type_profiles.get(profile_name, {})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_spread(record: dict) -> float:
    """Compute spread_ratio from a value record.

    Works with both legacy (value + range_low/range_high) and
    Interval-based (interval.lo/hi) records.
    """
    # Interval-based
    interval = record.get("interval")
    if interval and isinstance(interval, dict):
        lo = interval.get("lo", 0)
        hi = interval.get("hi", 0)
        mid = (lo + hi) / 2
        return (hi - lo) / abs(mid) if mid != 0 else float("inf")

    # Legacy: value + range_low/range_high
    value = record.get("value") or record.get("point_estimate")
    lo = record.get("range_low") or record.get("low")
    hi = record.get("range_high") or record.get("high")
    if value and lo is not None and hi is not None:
        try:
            v = float(value)
            return (float(hi) - float(lo)) / abs(v) if v != 0 else float("inf")
        except (ValueError, TypeError):
            pass
    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_policy(policy_id: str = "decision_balanced") -> dict[str, Any]:
    """Load compiled policy configuration.

    Returns the full policy with profiles (evidence, value, prior,
    convergence, orchestration).

    Args:
        policy_id: One of 'reporting_strict', 'decision_balanced',
                   'exploration_friendly'.

    Returns:
        dict with policy_id, description, profiles, gates, or error.
    """
    mode = _resolve_mode(policy_id)
    if mode is None:
        return {"error": f"Policy not found: {policy_id}"}

    profile_refs = mode.get("profiles", {})
    resolved_profiles: dict[str, Any] = {}

    for profile_type, profile_name in profile_refs.items():
        resolved_profiles[profile_type] = _get_profile(profile_type, profile_name)

    return {
        "policy_id": policy_id,
        "description": mode.get("description", ""),
        "profiles": resolved_profiles,
        "gates": mode.get("gates", []),
        "use_cases": mode.get("use_cases", []),
    }


def check_evidence_gate(
    evidence_result: dict[str, Any],
    policy_id: str = "decision_balanced",
) -> dict[str, Any]:
    """Check if evidence meets policy requirements.

    Gates checked:
    - evidence_min_sources: Minimum number of evidence records.
    - evidence_require_official: At least one official source (strict only).
    - evidence_max_age_days: Evidence freshness (placeholder — not enforced in MVP).

    Args:
        evidence_result: Output from collect_evidence() or similar dict
                         with 'records' key.
        policy_id: Policy mode to check against.

    Returns:
        dict with passed, gates_checked, gates_passed, violations, policy_id.
    """
    mode = _resolve_mode(policy_id)
    if mode is None:
        return {"error": f"Policy not found: {policy_id}"}

    evidence_profile_name = mode.get("profiles", {}).get("evidence", "")
    ev_profile = _get_profile("evidence", evidence_profile_name)

    records = evidence_result.get("records", [])
    total_records = len(records)
    mode_gates = mode.get("gates", [])

    violations: list[dict[str, Any]] = []
    gates_checked = 0
    gates_passed = 0

    # Gate: evidence_min_sources
    if "evidence_min_sources" in mode_gates:
        gates_checked += 1
        min_sources = ev_profile.get("min_sources", 0)
        passed = total_records >= min_sources
        if passed:
            gates_passed += 1
        violations.append({
            "gate": "evidence_min_sources",
            "required": min_sources,
            "actual": total_records,
            "passed": passed,
        })

    # Gate: evidence_require_official_if_configured
    if "evidence_require_official_if_configured" in mode_gates:
        gates_checked += 1
        require_official = ev_profile.get("require_official_sources", False)
        if require_official:
            official_count = sum(
                1 for r in records if r.get("source_tier") == "official"
            )
            passed = official_count >= 1
        else:
            passed = True
            official_count = sum(
                1 for r in records if r.get("source_tier") == "official"
            )
        if passed:
            gates_passed += 1
        violations.append({
            "gate": "evidence_require_official",
            "required": require_official,
            "actual_official_count": official_count if require_official or True else 0,
            "passed": passed,
        })

    # Gate: evidence_max_age_days
    if "evidence_max_age_days" in mode_gates:
        gates_checked += 1
        max_age_days = ev_profile.get("max_age_days", 730)
        stale_records: list[str] = []

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        for r in records:
            collected_at = r.get("collected_at") or r.get("timestamp") or r.get("date")
            if not collected_at:
                continue
            try:
                if isinstance(collected_at, str):
                    # Support ISO format and date-only
                    dt = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    age_days = (now - dt).days
                    if age_days > max_age_days:
                        source_name = r.get("source_name", r.get("source", "unknown"))
                        stale_records.append(f"{source_name} ({age_days}d)")
            except (ValueError, TypeError):
                continue

        passed = len(stale_records) == 0
        if passed:
            gates_passed += 1
        violations.append({
            "gate": "evidence_max_age_days",
            "required_max_days": max_age_days,
            "stale_records": stale_records,
            "passed": passed,
        })

    overall_passed = gates_checked == gates_passed

    return {
        "passed": overall_passed,
        "gates_checked": gates_checked,
        "gates_passed": gates_passed,
        "violations": violations,
        "policy_id": policy_id,
    }


def check_value_gate(
    value_records: list[dict[str, Any]],
    policy_id: str = "decision_balanced",
) -> dict[str, Any]:
    """Check if metric values meet policy quality requirements.

    Gates checked:
    - value_min_confidence: Minimum confidence threshold per record.
    - value_spread_ratio: Maximum spread ratio (placeholder in MVP).

    Args:
        value_records: List of value records from evaluate_metrics().
        policy_id: Policy mode to check against.

    Returns:
        dict with passed, gates_checked, gates_passed, violations, policy_id.
    """
    mode = _resolve_mode(policy_id)
    if mode is None:
        return {"error": f"Policy not found: {policy_id}"}

    value_profile_name = mode.get("profiles", {}).get("value", "")
    val_profile = _get_profile("value", value_profile_name)

    mode_gates = mode.get("gates", [])

    violations: list[dict[str, Any]] = []
    gates_checked = 0
    gates_passed = 0

    # Gate: value_min_confidence — DEPRECATED (replaced by value_spread_ratio)
    # Estimation Engine uses Interval (P10/P90) instead of confidence.
    # Kept for backward compatibility: if declared, uses spread_ratio as proxy.
    if "value_min_confidence" in mode_gates:
        gates_checked += 1
        max_spread = val_profile.get("max_spread_ratio", 1.0)
        if not value_records:
            passed = True
        else:
            # Use spread_ratio as confidence proxy: low spread = high confidence
            exceeded = [
                r for r in value_records
                if _compute_spread(r) > max_spread
            ]
            passed = len(exceeded) == 0

        if passed:
            gates_passed += 1
        violations.append({
            "gate": "value_min_confidence",
            "note": "deprecated — using spread_ratio as proxy",
            "required_max_spread": max_spread,
            "exceeded": [r.get("metric_id", "?") for r in exceeded] if not passed and value_records else [],
            "passed": passed,
        })

    # Gate: value_spread_ratio
    if "value_spread_ratio" in mode_gates:
        gates_checked += 1
        max_spread = val_profile.get("max_spread_ratio", 1.0)
        exceeded: list[dict[str, Any]] = []

        for r in value_records:
            value = r.get("value")
            low = r.get("range_low") or r.get("low")
            high = r.get("range_high") or r.get("high")
            if value and low is not None and high is not None:
                try:
                    v, lo, hi = float(value), float(low), float(high)
                    if v != 0:
                        spread = (hi - lo) / abs(v)
                        if spread > max_spread:
                            exceeded.append({
                                "metric_id": r.get("metric_id", "?"),
                                "spread_ratio": round(spread, 3),
                            })
                except (ValueError, TypeError, ZeroDivisionError):
                    continue

        passed = len(exceeded) == 0
        if passed:
            gates_passed += 1
        violations.append({
            "gate": "value_spread_ratio",
            "required_max": max_spread,
            "exceeded_metrics": exceeded,
            "passed": passed,
        })

    # Gate: value_literal_ratio
    if "value_literal_ratio" in mode_gates:
        gates_checked += 1
        min_literal = val_profile.get("min_literal_ratio", 0.0)
        if not value_records:
            passed = True
        else:
            below = [
                r for r in value_records
                if r.get("quality", {}).get("literal_ratio", 0.0) < min_literal
            ]
            passed = len(below) == 0

        if passed:
            gates_passed += 1
        violations.append({
            "gate": "value_literal_ratio",
            "required": min_literal,
            "actual_below_threshold": (
                [r.get("metric_id", "?") for r in below] if not passed else []
            ) if value_records else [],
            "passed": passed,
        })

    overall_passed = gates_checked == gates_passed

    return {
        "passed": overall_passed,
        "gates_checked": gates_checked,
        "gates_passed": gates_passed,
        "violations": violations,
        "policy_id": policy_id,
    }


def check_all_gates(
    evidence_result: dict[str, Any] | None = None,
    value_records: list[dict[str, Any]] | None = None,
    policy_id: str = "decision_balanced",
) -> dict[str, Any]:
    """Run all applicable policy gates and return aggregate result.

    Args:
        evidence_result: Output from collect_evidence() (optional).
        value_records: List of value records (optional).
        policy_id: Policy mode to check against.

    Returns:
        dict with policy_id, overall_passed, evidence_gate, value_gate,
        summary, suggested_actions.
    """
    mode = _resolve_mode(policy_id)
    if mode is None:
        return {"error": f"Policy not found: {policy_id}"}

    mode_gates = mode.get("gates", [])
    total_gate_groups = 0
    passed_gate_groups = 0
    suggested_actions: list[str] = []
    skipped_gates: list[dict[str, Any]] = []

    evidence_gate_result: dict[str, Any] | None = None
    value_gate_result: dict[str, Any] | None = None

    # Determine which input groups are required by declared gates
    _EVIDENCE_GATES = {"evidence_min_sources", "evidence_require_official_if_configured", "evidence_max_age_days"}
    _VALUE_GATES = {"value_min_confidence", "value_spread_ratio", "value_literal_ratio"}

    declared_evidence_gates = [g for g in mode_gates if g in _EVIDENCE_GATES]
    declared_value_gates = [g for g in mode_gates if g in _VALUE_GATES]

    # Evidence gate
    if declared_evidence_gates:
        if evidence_result is not None:
            total_gate_groups += 1
            evidence_gate_result = check_evidence_gate(evidence_result, policy_id)
            if evidence_gate_result.get("passed", False):
                passed_gate_groups += 1
            else:
                for v in evidence_gate_result.get("violations", []):
                    if not v.get("passed", True):
                        gate_name = v.get("gate", "")
                        if gate_name == "evidence_min_sources":
                            suggested_actions.append(
                                f"Collect more evidence sources (need {v['required']}, have {v['actual']})."
                            )
                        elif gate_name == "evidence_require_official":
                            suggested_actions.append(
                                "Collect at least one official source (e.g., KOSIS, DART)."
                            )
        else:
            total_gate_groups += 1
            skipped_gates.append({
                "group": "evidence",
                "declared_gates": declared_evidence_gates,
                "reason": "evidence_result not provided",
            })
            suggested_actions.append(
                f"Evidence gates declared ({', '.join(declared_evidence_gates)}) but evidence_result not provided. "
                "Pass evidence_result to check_all_gates()."
            )
    elif evidence_result is not None:
        # No evidence gates declared but data provided — run anyway as informational
        total_gate_groups += 1
        evidence_gate_result = check_evidence_gate(evidence_result, policy_id)
        if evidence_gate_result.get("passed", False):
            passed_gate_groups += 1

    # Value gate
    if declared_value_gates:
        if value_records is not None:
            total_gate_groups += 1
            value_gate_result = check_value_gate(value_records, policy_id)
            if value_gate_result.get("passed", False):
                passed_gate_groups += 1
            else:
                for v in value_gate_result.get("violations", []):
                    if not v.get("passed", True):
                        gate_name = v.get("gate", "")
                        if gate_name == "value_min_confidence":
                            suggested_actions.append(
                                "Reduce estimation spread_ratio by narrowing interval bounds (more evidence or tighter Fermi decomposition)."
                            )
                        elif gate_name == "value_literal_ratio":
                            suggested_actions.append(
                                "Increase literal ratio by using more evidence-backed estimates."
                            )
        else:
            total_gate_groups += 1
            skipped_gates.append({
                "group": "value",
                "declared_gates": declared_value_gates,
                "reason": "value_records not provided",
            })
            suggested_actions.append(
                f"Value gates declared ({', '.join(declared_value_gates)}) but value_records not provided. "
                "Pass value_records to check_all_gates()."
            )
    elif value_records is not None:
        # No value gates declared but data provided — run anyway as informational
        total_gate_groups += 1
        value_gate_result = check_value_gate(value_records, policy_id)
        if value_gate_result.get("passed", False):
            passed_gate_groups += 1

    # Prior ratio gate
    prior_gate_result: dict[str, Any] | None = None
    if "prior_ratio_limit" in mode_gates:
        total_gate_groups += 1
        prior_profile_name = mode.get("profiles", {}).get("prior", "")
        prior_profile = _get_profile("prior", prior_profile_name)
        max_prior_ratio = prior_profile.get("max_prior_ratio", 1.0)
        allow_prior = prior_profile.get("allow_prior", True)

        if not allow_prior:
            # prior_none: no prior allowed at all — gate passes if no prior-based values exist
            # We check value_records for prior-sourced values
            prior_count = 0
            total_count = 0
            if value_records:
                for r in value_records:
                    total_count += 1
                    method = r.get("method", "")
                    if method in ("prior", "expert_guess"):
                        prior_count += 1
            passed = prior_count == 0
            actual_ratio = prior_count / total_count if total_count > 0 else 0.0
        else:
            # Check ratio of prior-based values
            prior_count = 0
            total_count = 0
            if value_records:
                for r in value_records:
                    total_count += 1
                    method = r.get("method", "")
                    if method in ("prior", "expert_guess"):
                        prior_count += 1
            actual_ratio = prior_count / total_count if total_count > 0 else 0.0
            passed = actual_ratio <= max_prior_ratio

        if passed:
            passed_gate_groups += 1

        prior_gate_result = {
            "gate": "prior_ratio_limit",
            "required_max": max_prior_ratio,
            "allow_prior": allow_prior,
            "actual_ratio": round(actual_ratio, 3),
            "passed": passed,
        }

        if not passed:
            suggested_actions.append(
                f"Reduce prior-based estimates (current ratio: {actual_ratio:.1%}, max: {max_prior_ratio:.1%}). "
                "Use more evidence-backed estimation methods."
            )

    # Convergence gate
    convergence_gate_result: dict[str, Any] | None = None
    if "convergence_methods_required" in mode_gates:
        total_gate_groups += 1
        conv_profile_name = mode.get("profiles", {}).get("convergence", "")
        conv_profile = _get_profile("convergence", conv_profile_name)
        default_methods_required = conv_profile.get("default_methods_required", 1)

        if value_records:
            methods_used: set[str] = set()
            for r in value_records:
                method = r.get("method", "unknown")
                if method != "unknown":
                    methods_used.add(method)
            actual_methods = len(methods_used)
            passed = actual_methods >= default_methods_required
        else:
            actual_methods = 0
            passed = default_methods_required <= 1

        if passed:
            passed_gate_groups += 1

        convergence_gate_result = {
            "gate": "convergence_methods_required",
            "required": default_methods_required,
            "actual_methods": actual_methods,
            "passed": passed,
        }

        if not passed:
            suggested_actions.append(
                f"Use more estimation methods (need {default_methods_required}, have {actual_methods}). "
                "Try top_down, bottom_up, fermi, or proxy methods."
            )

    overall_passed = (
        total_gate_groups > 0
        and total_gate_groups == passed_gate_groups
        and len(skipped_gates) == 0
    )
    skipped_count = len(skipped_gates)
    summary = f"{passed_gate_groups}/{total_gate_groups} gates passed"
    if skipped_count:
        summary += f" ({skipped_count} skipped due to missing input)"

    if not suggested_actions:
        suggested_actions.append("All gates passed. Analysis quality meets policy requirements.")

    result: dict[str, Any] = {
        "policy_id": policy_id,
        "overall_passed": overall_passed,
        "evidence_gate": evidence_gate_result,
        "value_gate": value_gate_result,
        "prior_gate": prior_gate_result,
        "convergence_gate": convergence_gate_result,
        "summary": summary,
        "suggested_actions": suggested_actions,
    }
    if skipped_gates:
        result["skipped_gates"] = skipped_gates
    return result


# ---------------------------------------------------------------------------
# Declaration–implementation sync validation
# ---------------------------------------------------------------------------

# All gate identifiers that have actual implementation in this module
_IMPLEMENTED_GATES: frozenset[str] = frozenset({
    "evidence_min_sources",
    "evidence_require_official_if_configured",
    "evidence_max_age_days",
    "value_spread_ratio",
    "value_literal_ratio",
    "prior_ratio_limit",
    "convergence_methods_required",
})
# Note: value_min_confidence code is kept for backward compatibility
# but removed from declared gates (replaced by value_spread_ratio).


def validate_gate_sync() -> dict[str, Any]:
    """Check that every gate declared in policies.yaml is implemented, and vice versa.

    Returns:
        dict with 'in_sync' (bool), 'declared_only' (gates declared but not
        implemented), 'implemented_only' (gates implemented but not declared
        in any mode).
    """
    pack = _load_policy_pack()
    modes = pack.get("modes", {})

    declared: set[str] = set()
    for mode_def in modes.values():
        for gate in mode_def.get("gates", []):
            declared.add(gate)

    declared_only = sorted(declared - _IMPLEMENTED_GATES)
    implemented_only = sorted(_IMPLEMENTED_GATES - declared)

    return {
        "in_sync": len(declared_only) == 0 and len(implemented_only) == 0,
        "declared_gates": sorted(declared),
        "implemented_gates": sorted(_IMPLEMENTED_GATES),
        "declared_only": declared_only,
        "implemented_only": implemented_only,
    }
