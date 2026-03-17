"""CMIS v2 runner — user entry point for analysis sessions.

Provides CLI commands to start new analyses, resume from user gates,
and manage execution parameters.  Bridges the CMIS v2 project lifecycle
with the RLM completion engine.

Usage examples::

    # New analysis
    python -m cmis_v2.runner "한국 전기차 충전 인프라 시장 분석"

    # Resume after user gate
    python -m cmis_v2.runner --resume PROJECT_ID --approve
    python -m cmis_v2.runner --resume PROJECT_ID --revise "시장 범위를 B2C로 한정"
    python -m cmis_v2.runner --resume PROJECT_ID --select "PAT-subscription_model"
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from cmis_v2.project import (
    create_project,
    get_current_state,
    get_project_events,
    load_project,
    transition,
)
from cmis_v2.state_machine import is_terminal, is_user_gate
from cmis_v2.system_prompt import build_prompt, build_system_prompt
from cmis_v2.tools import CMISTools

# ---------------------------------------------------------------------------
# State -> prompt strategy mapping
# ---------------------------------------------------------------------------

_STATE_PROMPTS: dict[str, str] = {
    "requested": (
        "Analysis target: {target}. "
        "Create the project, transition to discovery, and perform initial market discovery. "
        "Identify the domain, key actors, and preliminary market scope."
    ),
    "discovery": (
        "Continue discovery for: {target}. "
        "Collect initial evidence, identify the domain structure, and prepare a scope proposal. "
        "When ready, transition to scope_review with a summary."
    ),
    "scope_locked": (
        "Scope: {scope}. "
        "Collect detailed data (collect_evidence, add_record), "
        "then build the R-Graph (build_snapshot, add_node, add_edge), "
        "evaluate key metrics (evaluate_metrics, set_metric_value), "
        "and perform structure analysis (match_patterns). "
        "When complete, transition through data_collection and structure_analysis to finding_review."
    ),
    "data_collection": (
        "Scope: {scope}. "
        "Collect evidence using collect_evidence and add_record. "
        "When data quality is sufficient, transition to structure_analysis."
    ),
    "structure_analysis": (
        "Scope: {scope}. "
        "Build the R-Graph (build_snapshot, add_node, add_edge), "
        "run match_patterns, and evaluate_metrics. "
        "When analysis is complete, transition to finding_review with a structured summary."
    ),
    "finding_locked": (
        "Market Reality Report is ready. "
        "Use discover_gaps to find partially matching patterns. "
        "Identify opportunities and transition to opportunity_discovery, "
        "then produce an opportunity review summary."
    ),
    "opportunity_discovery": (
        "Discover opportunities using discover_gaps and pattern analysis. "
        "When complete, transition to opportunity_review with ranked opportunities."
    ),
    "strategy_design": (
        "Selected opportunity: {selected}. "
        "Design a strategy: define the business model, go-to-market plan, "
        "key metrics, and risk assessment. "
        "When complete, transition to decision_review with the strategy proposal."
    ),
    "synthesis": (
        "All analysis stages complete. "
        "Compile the final comprehensive report. "
        "Save deliverables via save_deliverable, then transition to completed."
    ),
}

# ---------------------------------------------------------------------------
# User gate -> trigger mapping
# ---------------------------------------------------------------------------

_GATE_ACTION_MAP: dict[str, dict[str, str]] = {
    "scope_review": {
        "approve": "scope_approved",
        "revise": "scope_revised",
        "reject": "scope_rejected",
    },
    "finding_review": {
        "approve": "finding_approved",
        "revise": "finding_deepened",
        "complete": "finding_completed_early",
    },
    "opportunity_review": {
        "approve": "opportunity_selected",
        "select": "opportunity_selected",
        "revise": "opportunity_deepened",
        "complete": "opportunity_completed_early",
    },
    "decision_review": {
        "approve": "decision_approved",
        "revise": "decision_revised",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_context(project_id: str, manifest: dict[str, Any]) -> dict[str, str]:
    """Extract context variables from project state for prompt building."""
    context: dict[str, str] = {}

    # Target from description
    context["target"] = manifest.get("description", manifest.get("name", ""))

    # Scope
    scope = manifest.get("scope")
    if scope:
        context["scope"] = json.dumps(scope, ensure_ascii=False)[:500]
    else:
        context["scope"] = "(not yet defined)"

    # Selected opportunity from events
    events = get_project_events(project_id)
    for evt in reversed(events):
        if evt.get("type") == "opportunity.selected":
            payload = evt.get("payload", {})
            context["selected"] = json.dumps(payload, ensure_ascii=False)[:300]
            break
    if "selected" not in context:
        context["selected"] = "(none)"

    return context


def _build_state_prompt(
    project_id: str,
    manifest: dict[str, Any],
    policy_mode: str,
    execution_mode: str,
) -> str:
    """Build a prompt appropriate for the current project state."""
    state = manifest.get("current_state", "requested")
    context = _extract_context(project_id, manifest)

    # Get state-specific instruction
    template = _STATE_PROMPTS.get(state, "Continue the analysis from state: {state}.")
    # Add state to context for fallback template
    context["state"] = state
    state_instruction = template.format(**context)

    # Build full prompt
    system = build_system_prompt()
    return (
        f"{system}\n"
        f"## Current Session\n\n"
        f"- **Project ID**: {project_id}\n"
        f"- **Current state**: {state}\n"
        f"- **Policy mode**: {policy_mode}\n"
        f"- **Execution mode**: {execution_mode}\n\n"
        f"## Task\n\n"
        f"{state_instruction}\n\n"
        f"When you reach a user gate or terminal state, produce the result as FINAL_VAR().\n"
    )


# ---------------------------------------------------------------------------
# RLM builder
# ---------------------------------------------------------------------------


def build_rlm(
    tools: CMISTools,
    execution_mode: str = "autopilot",
    backend: str = "openai",
    model_name: str = "gpt-4o",
) -> Any:
    """Create an RLM instance with CMIS tools registered.

    Args:
        tools: CMISTools instance with project_id set.
        execution_mode: One of "autopilot", "review", "manual".
        backend: LLM backend - "openai" or "anthropic".
        model_name: Model name e.g. "gpt-4o".

    Returns:
        Configured RLM instance.
    """
    from rlm import RLM
    from rlm.logger import RLMLogger

    return RLM(
        backend=backend,
        backend_kwargs={"model_name": model_name},
        custom_tools=tools.as_rlm_tools(),
        max_depth=2,
        max_iterations=30,
        max_budget=15.0,
        max_timeout=600.0,
        verbose=True,
        logger=RLMLogger(log_dir="./logs"),
    )


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def run_new(
    target: str,
    policy_mode: str = "decision_balanced",
    execution_mode: str = "autopilot",
    backend: str = "openai",
    model_name: str = "gpt-4o",
) -> dict[str, Any]:
    """Start a new analysis project.

    1. Create a project.
    2. Transition to discovery.
    3. Build prompt from target + execution_mode + policy_mode.
    4. Create RLM with project_id.
    5. Run rlm.completion().
    6. Return result.
    """
    # 1. Create project
    domain_id = target.replace(" ", "_")[:60]
    manifest = create_project(
        name=domain_id[:30],
        description=target,
        domain_id=domain_id,
    )
    project_id: str = manifest["project_id"]

    # 2. Transition to discovery
    transition(project_id, "project_created", "system")

    # 3. Build prompt
    prompt = build_prompt(target, execution_mode=execution_mode, policy_mode=policy_mode)

    # 4. Build RLM
    tools = CMISTools(project_id=project_id)
    rlm = build_rlm(tools, execution_mode=execution_mode, backend=backend, model_name=model_name)

    # 5. Run completion
    result = rlm.completion(prompt)

    return {
        "project_id": project_id,
        "final_state": get_current_state(project_id),
        "result": result,
    }


def resume(
    project_id: str,
    action: str,
    action_data: str = "",
    policy_mode: str = "decision_balanced",
    execution_mode: str = "autopilot",
    backend: str = "openai",
    model_name: str = "gpt-4o",
) -> dict[str, Any]:
    """Resume a project from a user gate.

    1. Load project manifest and verify current state.
    2. Map action to the appropriate trigger and execute transition.
    3. If resulting state is not terminal/gate, build prompt and run next segment.

    Args:
        project_id: The project to resume.
        action: One of "approve", "revise", "reject", "complete", "select".
        action_data: Additional data for the action (e.g. revision note, selection ID).
        policy_mode: Policy mode override.
        execution_mode: Execution mode.
        backend: LLM backend.
        model_name: Model name.

    Returns:
        dict with project_id, final_state, result.
    """
    # 1. Load and verify
    manifest = load_project(project_id)
    if "error" in manifest:
        return manifest

    current_state: str = manifest["current_state"]

    if not is_user_gate(current_state):  # type: ignore[arg-type]
        return {"error": f"Project is not at a user gate. Current state: {current_state}"}

    # 2. Determine trigger
    gate_actions = _GATE_ACTION_MAP.get(current_state, {})
    trigger = gate_actions.get(action)
    if trigger is None:
        valid = list(gate_actions.keys())
        return {"error": f"Invalid action '{action}' for state '{current_state}'. Valid: {valid}"}

    # Build payload
    payload: dict[str, Any] = {}
    if action_data:
        payload["action_data"] = action_data
    if action == "revise":
        payload["revision_note"] = action_data
    elif action == "select":
        payload["selected"] = action_data

    # Execute transition
    manifest = transition(project_id, trigger, "user", payload=payload)
    if "error" in manifest:
        return manifest

    new_state: str = manifest["current_state"]

    # 3. If terminal or gate, stop
    if is_terminal(new_state) or is_user_gate(new_state):  # type: ignore[arg-type]
        return {
            "project_id": project_id,
            "final_state": new_state,
            "result": f"Project transitioned to {new_state}. "
            + ("Project complete." if is_terminal(new_state) else "Awaiting user action."),  # type: ignore[arg-type]
        }

    # 4. Build prompt for next automatic segment
    manifest = load_project(project_id)
    prompt = _build_state_prompt(project_id, manifest, policy_mode, execution_mode)

    # 5. Run RLM
    tools = CMISTools(project_id=project_id)
    rlm = build_rlm(tools, execution_mode=execution_mode, backend=backend, model_name=model_name)
    result = rlm.completion(prompt)

    return {
        "project_id": project_id,
        "final_state": get_current_state(project_id),
        "result": result,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for CMIS v2 runner."""
    parser = argparse.ArgumentParser(
        description="CMIS v2 Market Intelligence Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # New analysis
  python -m cmis_v2.runner "한국 전기차 충전 인프라 시장 분석"

  # Resume with approval
  python -m cmis_v2.runner --resume PROJECT_ID --approve

  # Resume with revision
  python -m cmis_v2.runner --resume PROJECT_ID --revise "시장 범위를 B2C로 한정"

  # Resume with selection
  python -m cmis_v2.runner --resume PROJECT_ID --select "PAT-subscription_model"
""",
    )

    # Positional: analysis target (for new runs)
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Analysis target description (for new analysis)",
    )

    # Resume mode
    parser.add_argument(
        "--resume",
        metavar="PROJECT_ID",
        default=None,
        help="Resume an existing project from a user gate",
    )

    # User gate actions (mutually exclusive)
    gate_group = parser.add_mutually_exclusive_group()
    gate_group.add_argument("--approve", action="store_true", help="Approve at current gate")
    gate_group.add_argument("--revise", metavar="NOTE", default=None, help="Revise with note")
    gate_group.add_argument("--reject", action="store_true", help="Reject (scope_review only)")
    gate_group.add_argument("--complete", action="store_true", help="Complete early")
    gate_group.add_argument("--select", metavar="ID", default=None, help="Select an opportunity")

    # Options
    parser.add_argument(
        "--policy",
        choices=["reporting_strict", "decision_balanced", "exploration_friendly"],
        default="decision_balanced",
        help="Policy mode (default: decision_balanced)",
    )
    parser.add_argument(
        "--mode",
        choices=["autopilot", "review", "manual"],
        default="autopilot",
        help="Execution mode (default: autopilot)",
    )
    parser.add_argument(
        "--backend",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM backend (default: openai)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="Model name (default: gpt-4o)",
    )

    args = parser.parse_args()

    # Determine operation mode
    if args.resume:
        # Resume mode — determine action
        if args.approve:
            action, action_data = "approve", ""
        elif args.revise is not None:
            action, action_data = "revise", args.revise
        elif args.reject:
            action, action_data = "reject", ""
        elif args.complete:
            action, action_data = "complete", ""
        elif args.select is not None:
            action, action_data = "select", args.select
        else:
            parser.error("--resume requires one of: --approve, --revise, --reject, --complete, --select")
            return

        result = resume(
            project_id=args.resume,
            action=action,
            action_data=action_data,
            policy_mode=args.policy,
            execution_mode=args.mode,
            backend=args.backend,
            model_name=args.model,
        )
    elif args.target:
        # New analysis mode
        result = run_new(
            target=args.target,
            policy_mode=args.policy,
            execution_mode=args.mode,
            backend=args.backend,
            model_name=args.model,
        )
    else:
        parser.error("Provide an analysis target or use --resume PROJECT_ID")
        return

    # Output result
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
