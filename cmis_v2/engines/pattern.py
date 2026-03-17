"""CMIS v2 Pattern Engine — Business pattern matching against R-Graph.

Loads 23 pattern definitions from libraries/patterns/*.yaml and evaluates
trait constraints against a Reality Snapshot's nodes.

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Pattern loading and cache
# ---------------------------------------------------------------------------

_PATTERNS_DIR: Path = Path(__file__).parent.parent.parent / "libraries" / "patterns"
_PATTERN_CACHE: list[dict[str, Any]] | None = None


def _load_patterns() -> list[dict[str, Any]]:
    """Load all pattern YAML files from the patterns directory.

    Results are cached after first load.
    """
    global _PATTERN_CACHE
    if _PATTERN_CACHE is not None:
        return _PATTERN_CACHE

    patterns: list[dict[str, Any]] = []
    if not _PATTERNS_DIR.is_dir():
        _PATTERN_CACHE = patterns
        return patterns

    for yaml_path in sorted(_PATTERNS_DIR.glob("*.yaml")):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                doc = yaml.safe_load(f)
            if doc and "pattern" in doc:
                patterns.append(doc["pattern"])
        except Exception:
            # Skip malformed files silently in MVP
            continue

    _PATTERN_CACHE = patterns
    return patterns


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _evaluate_trait_match(
    pattern: dict[str, Any],
    nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate how well a snapshot's nodes match a pattern's trait_constraints.

    Returns a dict with fit_score, matched_traits, missing_traits.
    """
    constraints = pattern.get("trait_constraints", {})
    if not constraints:
        return {
            "fit_score": 0.0,
            "matched_traits": [],
            "missing_traits": [],
        }

    total_required = 0
    matched_required = 0
    matched_trait_names: list[str] = []
    missing_trait_names: list[str] = []

    for node_type, constraint in constraints.items():
        required_traits = constraint.get("required_traits", {})
        if not required_traits:
            continue

        # Find nodes of this type in the snapshot
        type_nodes = [n for n in nodes if n.get("type") == node_type]

        for trait_name, expected_value in required_traits.items():
            total_required += 1
            trait_found = False

            for node in type_nodes:
                node_traits = node.get("data", {}).get("traits", {})
                actual_value = node_traits.get(trait_name)
                if actual_value is not None and actual_value == expected_value:
                    trait_found = True
                    break

            if trait_found:
                matched_required += 1
                matched_trait_names.append(trait_name)
            else:
                missing_trait_names.append(trait_name)

    fit_score = matched_required / total_required if total_required > 0 else 0.0

    return {
        "fit_score": round(fit_score, 3),
        "matched_traits": matched_trait_names,
        "missing_traits": missing_trait_names,
    }


# ---------------------------------------------------------------------------
# Snapshot accessor (avoid circular import by importing lazily)
# ---------------------------------------------------------------------------


def _get_snapshot_nodes(snapshot_id: str) -> list[dict[str, Any]] | None:
    """Retrieve nodes from a snapshot. Returns None if not found."""
    from cmis_v2.engines.world import get_snapshot

    snap = get_snapshot(snapshot_id)
    if "error" in snap:
        return None
    return snap.get("nodes", [])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match_patterns(
    snapshot_id: str,
    top_n: int = 5,
) -> dict[str, Any]:
    """Match business patterns against a Reality Snapshot.

    Loads pattern definitions from libraries/patterns/*.yaml and evaluates
    trait constraints against the snapshot's nodes.

    Args:
        snapshot_id: The snapshot to match patterns against.
        top_n: Maximum number of top matches to return (default 5).

    Returns:
        dict with snapshot_id, matches, total_patterns_evaluated, lineage.
    """
    now = datetime.now().isoformat()

    nodes = _get_snapshot_nodes(snapshot_id)
    if nodes is None:
        return {"error": f"Snapshot not found: {snapshot_id}"}

    patterns = _load_patterns()
    all_results: list[dict[str, Any]] = []

    for pat in patterns:
        evaluation = _evaluate_trait_match(pat, nodes)
        all_results.append({
            "pattern_id": pat.get("pattern_id", ""),
            "pattern_name": pat.get("name", ""),
            "family": pat.get("family", ""),
            "fit_score": evaluation["fit_score"],
            "matched_traits": evaluation["matched_traits"],
            "missing_traits": evaluation["missing_traits"],
            "evidence": "",
        })

    # Sort by fit_score descending, take top_n
    all_results.sort(key=lambda r: r["fit_score"], reverse=True)
    top_matches = all_results[:top_n]

    return {
        "snapshot_id": snapshot_id,
        "matches": top_matches,
        "total_patterns_evaluated": len(patterns),
        "lineage": {
            "engine": "pattern",
            "snapshot_id": snapshot_id,
            "timestamp": now,
        },
    }


def discover_gaps(
    snapshot_id: str,
) -> dict[str, Any]:
    """Find patterns that partially match -- potential opportunities.

    Returns patterns with 0.3 <= fit_score < 0.7 (partially present).

    Args:
        snapshot_id: The snapshot to analyze.

    Returns:
        dict with snapshot_id, gaps, lineage.
    """
    now = datetime.now().isoformat()

    nodes = _get_snapshot_nodes(snapshot_id)
    if nodes is None:
        return {"error": f"Snapshot not found: {snapshot_id}"}

    patterns = _load_patterns()
    gaps: list[dict[str, Any]] = []

    for pat in patterns:
        evaluation = _evaluate_trait_match(pat, nodes)
        score = evaluation["fit_score"]

        if 0.3 <= score < 0.7:
            gaps.append({
                "pattern_id": pat.get("pattern_id", ""),
                "pattern_name": pat.get("name", ""),
                "fit_score": score,
                "present_traits": evaluation["matched_traits"],
                "missing_traits": evaluation["missing_traits"],
                "opportunity_description": (
                    f"Pattern '{pat.get('name', '')}' is partially present "
                    f"(score={score:.2f}). Missing traits: "
                    f"{evaluation['missing_traits']}. "
                    f"Filling these gaps may unlock this pattern."
                ),
            })

    gaps.sort(key=lambda g: g["fit_score"], reverse=True)

    return {
        "snapshot_id": snapshot_id,
        "gaps": gaps,
        "lineage": {
            "engine": "pattern",
            "function": "discover_gaps",
            "snapshot_id": snapshot_id,
            "timestamp": now,
        },
    }
