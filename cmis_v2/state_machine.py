"""CMIS v2 project state machine.

Defines the 14 project states (13 workflow + 1 terminal) and all valid
transitions between them.  Every function is pure — no I/O, no side-effects.
"""

from __future__ import annotations

from typing import Literal

# ---------------------------------------------------------------------------
# State type
# ---------------------------------------------------------------------------

State = Literal[
    "requested",
    "discovery",
    "scope_review",
    "scope_locked",
    "data_collection",
    "structure_analysis",
    "finding_review",
    "finding_locked",
    "opportunity_discovery",
    "opportunity_review",
    "strategy_design",
    "decision_review",
    "synthesis",
    "completed",
    "rejected",
]

# ---------------------------------------------------------------------------
# Trigger type
# ---------------------------------------------------------------------------

Trigger = Literal[
    # Forward flow
    "project_created",
    "discovery_completed",
    "scope_approved",
    "auto",
    "data_quality_passed",
    "analysis_completed",
    "finding_approved",
    "opportunity_included",
    "opportunity_completed",
    "opportunity_selected",
    "strategy_completed",
    "decision_approved",
    "deliverable_saved",
    # Revision flow
    "scope_revised",
    "finding_deepened",
    "opportunity_deepened",
    "decision_revised",
    # Shortcut flow
    "scope_rejected",
    "finding_completed_early",
    "opportunity_not_included",
    "opportunity_completed_early",
]

# ---------------------------------------------------------------------------
# Transition table:  (current_state, trigger) -> next_state
# ---------------------------------------------------------------------------

TRANSITIONS: dict[tuple[State, Trigger], State] = {
    # Forward flow
    ("requested", "project_created"): "discovery",
    ("discovery", "discovery_completed"): "scope_review",
    ("scope_review", "scope_approved"): "scope_locked",
    ("scope_locked", "auto"): "data_collection",
    ("data_collection", "data_quality_passed"): "structure_analysis",
    ("structure_analysis", "analysis_completed"): "finding_review",
    ("finding_review", "finding_approved"): "finding_locked",
    ("finding_locked", "opportunity_included"): "opportunity_discovery",
    ("opportunity_discovery", "opportunity_completed"): "opportunity_review",
    ("opportunity_review", "opportunity_selected"): "strategy_design",
    ("strategy_design", "strategy_completed"): "decision_review",
    ("decision_review", "decision_approved"): "synthesis",
    ("synthesis", "deliverable_saved"): "completed",
    # Revision flow
    ("scope_review", "scope_revised"): "discovery",
    ("finding_review", "finding_deepened"): "structure_analysis",
    ("opportunity_review", "opportunity_deepened"): "opportunity_discovery",
    ("decision_review", "decision_revised"): "strategy_design",
    # Shortcut flow
    ("scope_review", "scope_rejected"): "rejected",
    ("finding_review", "finding_completed_early"): "synthesis",
    ("finding_locked", "opportunity_not_included"): "synthesis",
    ("opportunity_review", "opportunity_completed_early"): "synthesis",
}

# ---------------------------------------------------------------------------
# Terminal states
# ---------------------------------------------------------------------------

_TERMINAL_STATES: frozenset[State] = frozenset({"completed", "rejected"})

# ---------------------------------------------------------------------------
# User-gate states (require explicit user approval to leave)
# ---------------------------------------------------------------------------

_USER_GATE_STATES: frozenset[State] = frozenset({
    "scope_review",
    "finding_review",
    "finding_locked",
    "opportunity_review",
    "decision_review",
})

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def can_transition(current: State, trigger: Trigger) -> bool:
    """Return True if *trigger* is valid from *current* state."""
    return (current, trigger) in TRANSITIONS


def next_state(current: State, trigger: Trigger) -> State:
    """Return the target state for *trigger* from *current*.

    Raises ``ValueError`` if the transition is not allowed.
    """
    key = (current, trigger)
    if key not in TRANSITIONS:
        raise ValueError(
            f"Invalid transition: state={current!r}, trigger={trigger!r}"
        )
    return TRANSITIONS[key]


def is_terminal(state: State) -> bool:
    """Return True if *state* is a terminal (final) state."""
    return state in _TERMINAL_STATES


def is_user_gate(state: State) -> bool:
    """Return True if *state* requires explicit user approval to proceed."""
    return state in _USER_GATE_STATES
