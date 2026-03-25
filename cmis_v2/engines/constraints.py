"""CMIS v2 Constraint Propagation — Metric relation enforcement.

Loads metric_relations from schemas/ontology.yaml and validates/narrows
estimation intervals against declared identity and inequality constraints.

Design decision (8-Agent Panel Review, 2026-03-25):
- Constraints are declarative (ontology.yaml), not hardcoded.
- Operates on Interval (P10/P90 ranges), not sigma/distributions.
- DAG validation prevents circular constraint chains.

This module is designed to be called by RLM's LM as a custom_tool.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from cmis_v2.engines.interval import Interval

# ---------------------------------------------------------------------------
# Constraint loading
# ---------------------------------------------------------------------------

_ONTOLOGY_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "ontology.yaml"
_RELATIONS_CACHE: list[dict[str, Any]] | None = None


def _load_relations() -> list[dict[str, Any]]:
    """Load metric_relations from ontology.yaml. Cached after first load."""
    global _RELATIONS_CACHE
    if _RELATIONS_CACHE is not None:
        return _RELATIONS_CACHE

    try:
        with open(_ONTOLOGY_PATH, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        relations = raw.get("ontology", {}).get("metric_relations", [])
        _RELATIONS_CACHE = relations if relations else []
    except Exception:
        _RELATIONS_CACHE = []

    return _RELATIONS_CACHE


# ---------------------------------------------------------------------------
# Simple formula parser (identity constraints)
# ---------------------------------------------------------------------------

_METRIC_PATTERN = re.compile(r"MET-\w+")


def _parse_identity(formula: str) -> tuple[str, str, list[str]]:
    """Parse 'A = B * C' style formula.

    Returns (lhs_var, operator_expression, all_variables).
    Only supports: A = B op C, A = (B op C) op D patterns.
    """
    parts = formula.split("=", 1)
    if len(parts) != 2:
        raise ValueError(f"Cannot parse formula: {formula}")

    lhs = parts[0].strip()
    rhs = parts[1].strip()
    variables = _METRIC_PATTERN.findall(formula)
    return lhs, rhs, variables


def _eval_interval_expr(
    expr: str,
    known: dict[str, Interval],
) -> Interval | None:
    """Evaluate an interval expression given known variable intervals.

    Supports: A * B, A / B, A + B, A - B, (A - B) / C patterns.
    Returns None if any required variable is missing.
    """
    # Replace metric IDs with placeholder names for safe eval
    variables = _METRIC_PATTERN.findall(expr)
    for v in variables:
        if v not in known:
            return None

    # Build interval computation
    # Simple 2-operand: "A * B", "A / B", "A + B", "A - B"
    expr_clean = expr.strip()

    # Handle parenthesized: "(A - B) / C"
    paren_match = re.match(
        r"\((\s*MET-\w+\s*[-+*/]\s*MET-\w+\s*)\)\s*([-+*/])\s*(MET-\w+)", expr_clean
    )
    if paren_match:
        inner_expr = paren_match.group(1).strip()
        outer_op = paren_match.group(2).strip()
        outer_var = paren_match.group(3).strip()

        inner_result = _eval_simple_binary(inner_expr, known)
        if inner_result is None or outer_var not in known:
            return None

        return _apply_op(inner_result, outer_op, known[outer_var])

    # Simple binary: "A * B"
    return _eval_simple_binary(expr_clean, known)


def _eval_simple_binary(
    expr: str,
    known: dict[str, Interval],
) -> Interval | None:
    """Evaluate 'A op B' where op is +, -, *, /."""
    for op in ["*", "/", "+", "-"]:
        parts = expr.split(op, 1)
        if len(parts) == 2:
            left_name = parts[0].strip()
            right_name = parts[1].strip()
            if left_name in known and right_name in known:
                return _apply_op(known[left_name], op, known[right_name])
    return None


def _apply_op(a: Interval, op: str, b: Interval) -> Interval:
    """Apply an arithmetic operator to two intervals."""
    if op == "*":
        return a * b
    elif op == "/":
        return a / b
    elif op == "+":
        return a + b
    elif op == "-":
        return a - b
    raise ValueError(f"Unknown operator: {op}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_constraints(
    metric_intervals: dict[str, dict[str, float]],
    project_id: str = "",
) -> dict[str, Any]:
    """Check all declared constraints against provided metric intervals.

    For each constraint:
    - identity: compute RHS from known intervals, check if LHS is consistent.
    - inequality: check if A >= B holds (interval overlap is acceptable).

    Args:
        metric_intervals: Dict of variable_name → {"lo": float, "hi": float}.
            Can include both registered metrics and free variables.

    Returns:
        dict with violations (list), narrowed_intervals (dict),
        constraints_checked count, constraints_passed count.
    """
    relations = _load_relations()

    # Convert input to Interval objects
    known: dict[str, Interval] = {}
    for name, val in metric_intervals.items():
        known[name] = Interval(float(val["lo"]), float(val["hi"]))

    violations: list[dict[str, Any]] = []
    narrowed: dict[str, dict[str, float]] = {}
    checked = 0
    passed = 0

    for rel in relations:
        rel_type = rel.get("type", "")
        variables = rel.get("variables", [])

        # Skip if not enough variables are known
        known_count = sum(1 for v in variables if v in known)
        if known_count < 2:
            continue

        checked += 1

        if rel_type == "inequality":
            result = _check_inequality(rel, known)
            if result["passed"]:
                passed += 1
                # Narrow intervals based on inequality
                for name, interval in result.get("narrowed", {}).items():
                    known[name] = interval
                    narrowed[name] = interval.to_dict()
            else:
                violations.append(result)

        elif rel_type == "identity":
            result = _check_identity(rel, known)
            if result["passed"]:
                passed += 1
                for name, interval in result.get("narrowed", {}).items():
                    known[name] = interval
                    narrowed[name] = interval.to_dict()
            else:
                violations.append(result)

    return {
        "constraints_checked": checked,
        "constraints_passed": passed,
        "violations": violations,
        "narrowed_intervals": narrowed,
        "all_passed": checked == passed,
    }


def _check_inequality(
    rel: dict[str, Any],
    known: dict[str, Interval],
) -> dict[str, Any]:
    """Check and enforce an inequality constraint (A >= B)."""
    constraint_str = rel.get("constraint", "")
    variables = rel.get("variables", [])

    if len(variables) != 2:
        return {"passed": True, "constraint": constraint_str, "note": "skip: not 2 vars"}

    a_name, b_name = variables[0], variables[1]
    if a_name not in known or b_name not in known:
        return {"passed": True, "constraint": constraint_str, "note": "skip: missing vars"}

    a = known[a_name]
    b = known[b_name]

    # Check: is it possible that A >= B?
    # Violation only if A.hi < B.lo (A is entirely below B)
    if a.hi < b.lo:
        return {
            "passed": False,
            "type": "inequality",
            "constraint": constraint_str,
            "detail": f"{a_name}.hi ({a.hi}) < {b_name}.lo ({b.lo})",
            "a": a.to_dict(),
            "b": b.to_dict(),
        }

    # Narrow: A.lo should be at least B.lo, B.hi should be at most A.hi
    narrowed: dict[str, Interval] = {}
    if a.lo < b.lo:
        # A's lower bound can't be below B's lower bound if A >= B
        # But actually A >= B means A's interval should be above B's
        # We narrow: A.lo = max(A.lo, B.lo) is too aggressive
        # Conservative: don't narrow A's lower bound from inequality alone
        pass
    if b.hi > a.hi:
        new_b = Interval(b.lo, min(b.hi, a.hi))
        narrowed[b_name] = new_b

    return {
        "passed": True,
        "type": "inequality",
        "constraint": constraint_str,
        "narrowed": narrowed,
    }


def _check_identity(
    rel: dict[str, Any],
    known: dict[str, Interval],
) -> dict[str, Any]:
    """Check an identity constraint (LHS = RHS expression).

    If LHS is known and RHS can be computed, check consistency.
    If LHS is unknown but RHS can be computed, derive LHS.
    """
    formula = rel.get("formula", "")
    try:
        lhs_name, rhs_expr, _ = _parse_identity(formula)
    except ValueError:
        return {"passed": True, "formula": formula, "note": "skip: parse error"}

    rhs_interval = _eval_interval_expr(rhs_expr, known)

    if rhs_interval is None:
        # Can't compute RHS — skip
        return {"passed": True, "formula": formula, "note": "skip: insufficient data"}

    narrowed: dict[str, Interval] = {}

    if lhs_name in known:
        lhs_interval = known[lhs_name]
        # Check consistency: do the intervals overlap?
        overlap = lhs_interval.intersect(rhs_interval)
        if overlap is None:
            return {
                "passed": False,
                "type": "identity",
                "formula": formula,
                "detail": f"LHS {lhs_name} [{lhs_interval.lo}, {lhs_interval.hi}] "
                          f"does not overlap with computed RHS [{rhs_interval.lo}, {rhs_interval.hi}]",
                "lhs": lhs_interval.to_dict(),
                "computed_rhs": rhs_interval.to_dict(),
            }
        # Narrow LHS to the overlap
        if overlap != lhs_interval:
            narrowed[lhs_name] = overlap
    else:
        # LHS unknown — derive from RHS
        narrowed[lhs_name] = rhs_interval

    return {
        "passed": True,
        "type": "identity",
        "formula": formula,
        "narrowed": narrowed,
    }
