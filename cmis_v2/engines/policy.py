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

    # Gate: evidence_max_age_days (placeholder — records don't carry age yet)
    if "evidence_max_age_days" in mode_gates:
        gates_checked += 1
        # In MVP, we pass this gate automatically
        gates_passed += 1
        violations.append({
            "gate": "evidence_max_age_days",
            "required": ev_profile.get("max_age_days", 730),
            "actual": "not_checked_in_mvp",
            "passed": True,
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

    # Gate: value_min_confidence
    if "value_min_confidence" in mode_gates:
        gates_checked += 1
        min_conf = val_profile.get("min_confidence", 0.0)
        if not value_records:
            passed = True  # No records to check
        else:
            below = [
                r for r in value_records
                if r.get("confidence", 0.0) < min_conf
            ]
            passed = len(below) == 0

        if passed:
            gates_passed += 1
        violations.append({
            "gate": "value_min_confidence",
            "required": min_conf,
            "actual_below_threshold": (
                [r.get("metric_id", "?") for r in below] if not passed else []
            ) if value_records else [],
            "passed": passed,
        })

    # Gate: value_spread_ratio
    if "value_spread_ratio" in mode_gates:
        gates_checked += 1
        max_spread = val_profile.get("max_spread_ratio", 1.0)
        # In MVP, spread is not computed on records; pass automatically
        gates_passed += 1
        violations.append({
            "gate": "value_spread_ratio",
            "required_max": max_spread,
            "actual": "not_checked_in_mvp",
            "passed": True,
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

    total_gate_groups = 0
    passed_gate_groups = 0
    suggested_actions: list[str] = []

    evidence_gate_result: dict[str, Any] | None = None
    value_gate_result: dict[str, Any] | None = None

    # Evidence gate
    if evidence_result is not None:
        total_gate_groups += 1
        evidence_gate_result = check_evidence_gate(evidence_result, policy_id)
        if evidence_gate_result.get("passed", False):
            passed_gate_groups += 1
        else:
            # Build suggested actions from violations
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

    # Value gate
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
                            "Increase metric confidence by collecting more evidence or using additional estimation methods."
                        )
                    elif gate_name == "value_literal_ratio":
                        suggested_actions.append(
                            "Increase literal ratio by using more evidence-backed estimates."
                        )

    overall_passed = total_gate_groups > 0 and total_gate_groups == passed_gate_groups
    summary = f"{passed_gate_groups}/{total_gate_groups} gates passed"

    if not suggested_actions:
        suggested_actions.append("All gates passed. Analysis quality meets policy requirements.")

    return {
        "policy_id": policy_id,
        "overall_passed": overall_passed,
        "evidence_gate": evidence_gate_result,
        "value_gate": value_gate_result,
        "summary": summary,
        "suggested_actions": suggested_actions,
    }
