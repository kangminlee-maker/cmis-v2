"""CMIS v2 system prompt builder.

Dynamically generates the system prompt from ontology-generated types
(METRIC_REGISTRY, VALID_METRIC_IDS) and workflow definitions loaded from
``schemas/ontology.yaml``.  No hard-coded metric or workflow lists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ONTOLOGY_PATH: Path = Path(__file__).parent.parent / "schemas" / "ontology.yaml"

# ---------------------------------------------------------------------------
# Ontology loader (cached)
# ---------------------------------------------------------------------------

_ONTOLOGY_CACHE: dict[str, Any] | None = None


def _load_ontology() -> dict[str, Any]:
    """Load and cache the ontology YAML."""
    global _ONTOLOGY_CACHE
    if _ONTOLOGY_CACHE is not None:
        return _ONTOLOGY_CACHE
    with open(_ONTOLOGY_PATH, "r", encoding="utf-8") as fh:
        _ONTOLOGY_CACHE = yaml.safe_load(fh)
    return _ONTOLOGY_CACHE  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Dynamic section builders
# ---------------------------------------------------------------------------


def _build_metric_section() -> str:
    """Build the metric ID list from METRIC_REGISTRY (generated/types.py)."""
    from cmis_v2.generated.types import METRIC_REGISTRY

    lines: list[str] = ["## Available Metrics", ""]
    for mid, info in sorted(METRIC_REGISTRY.items()):
        unit = info.get("unit", "")
        desc = info.get("description", "")
        lines.append(f"- **{mid}** ({unit}): {desc}")
    lines.append("")
    return "\n".join(lines)


def _build_workflow_section() -> str:
    """Build workflow keyword mapping from ontology.yaml workflow_schema."""
    onto = _load_ontology()
    ws = onto.get("ontology", {}).get("workflow_schema", {})
    canonical = ws.get("canonical_workflows", [])

    lines: list[str] = ["## Workflow Keyword Mapping", ""]
    for wf_id in canonical:
        wf = ws.get(wf_id, {})
        desc = wf.get("description", "")
        keywords = wf.get("keywords", [])
        default_policy = wf.get("default_policy", "")
        lines.append(f"### {wf_id}")
        lines.append(f"- Description: {desc}")
        lines.append(f"- Keywords: {', '.join(keywords)}")
        lines.append(f"- Default policy: {default_policy}")
        lines.append("")
    return "\n".join(lines)


def _build_tool_section() -> str:
    """Build the tool list section from CMISTools descriptions."""
    from cmis_v2.tools import CMISTools

    tools = CMISTools()
    rlm_tools = tools.as_rlm_tools()

    lines: list[str] = ["## Available Tools", ""]
    for name, spec in sorted(rlm_tools.items()):
        desc = spec.get("description", "")
        lines.append(f"### {name}")
        lines.append(desc)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _build_ontology_reference() -> str:
    """Build ontology reference section with node/edge types from ontology.yaml."""
    onto = _load_ontology()
    ontology = onto.get("ontology", {})

    node_types = list(ontology.get("node_types", {}).keys())
    edge_types = list(ontology.get("edge_types", {}).keys())

    lines: list[str] = [
        "## State Transitions (Complete Trigger Reference)",
        "",
        "Each state transition requires calling `transition(project_id, trigger, actor)`.",
        "Available triggers per state:",
        '- requested: "project_created" -> discovery',
        '- discovery: "discovery_completed" -> scope_review',
        '- scope_review: "scope_approved" -> scope_locked, "scope_revised" -> discovery, "scope_rejected" -> rejected',
        '- scope_locked: "auto" -> data_collection',
        '- data_collection: "data_quality_passed" -> structure_analysis',
        '- structure_analysis: "analysis_completed" -> finding_review',
        '- finding_review: "finding_approved" -> finding_locked, "finding_deepened" -> structure_analysis, "finding_completed_early" -> synthesis',
        '- finding_locked: "opportunity_included" -> opportunity_discovery, "opportunity_not_included" -> synthesis',
        '- opportunity_discovery: "opportunity_completed" -> opportunity_review',
        '- opportunity_review: "opportunity_selected" -> strategy_design, "opportunity_deepened" -> opportunity_discovery, "opportunity_completed_early" -> synthesis',
        '- strategy_design: "strategy_completed" -> decision_review',
        '- decision_review: "decision_approved" -> synthesis, "decision_revised" -> strategy_design',
        '- synthesis: "deliverable_saved" -> completed',
        "",
        "## Ontology Reference",
        "",
        f"Valid node types: {', '.join(node_types)}",
        f"Valid edge types: {', '.join(edge_types)}",
        "Valid source tiers (for add_record): official, curated, commercial",
        "Valid data sources (for collect_evidence): web_search, kosis, dart",
        "",
    ]
    return "\n".join(lines)


def build_system_prompt() -> str:
    """Build the system prompt dynamically from ontology-generated types.

    Includes: role description, state flow, user gates, tools, metrics,
    workflow keywords, execution rules, and policy modes.
    """
    metric_section = _build_metric_section()
    workflow_section = _build_workflow_section()
    tool_section = _build_tool_section()
    ontology_reference = _build_ontology_reference()

    prompt = f"""\
# CMIS v2 Analysis Agent

You are a CMIS v2 market intelligence analysis agent. Your role is to perform
structured market analysis by driving the project through its lifecycle states,
collecting evidence, building Reality Snapshots (R-Graphs), matching patterns,
evaluating metrics, and producing deliverables.

## State Transition Flow

The project follows this lifecycle:

  requested -> discovery -> scope_review -> scope_locked -> data_collection
  -> structure_analysis -> finding_review -> finding_locked
  -> opportunity_discovery -> opportunity_review -> strategy_design
  -> decision_review -> synthesis -> completed

Terminal states: completed, rejected.

## User Gates

The following states require explicit user approval before proceeding.
When you reach a user gate, produce a summary report as FINAL_VAR() and stop.

- **scope_review**: User reviews the proposed scope. Triggers: scope_approved, scope_revised, scope_rejected.
- **finding_review**: User reviews findings. Triggers: finding_approved, finding_deepened, finding_completed_early.
- **opportunity_review**: User reviews opportunities. Triggers: opportunity_selected, opportunity_deepened, opportunity_completed_early.
- **decision_review**: User reviews strategy decision. Triggers: decision_approved, decision_revised.

{tool_section}

{metric_section}

{workflow_section}

{ontology_reference}

## Execution Rules

1. If running standalone, create a project first. In runner mode, the project is already created — check current state with get_current_state().
2. Collect evidence before building R-Graph snapshots.
3. Build R-Graph (add nodes and edges) before running pattern matching.
4. Evaluate metrics after evidence collection — use set_metric_value to fill in estimates.
5. At each user gate, produce a structured summary and stop via FINAL_VAR().
6. Save final deliverables via save_deliverable before transitioning to completed.

### Error Recovery

7. If a tool returns {{"error": "..."}}, log the error and attempt an alternative approach.
8. If multiple tools fail consecutively, produce a partial report and stop at the current gate.

## Policy Modes

- **reporting_strict**: High evidence thresholds, conservative estimates, prioritise accuracy.
- **decision_balanced**: Balanced evidence and speed, suitable for most analyses.
- **exploration_friendly**: Lower thresholds, accept proxy data, encourage breadth of exploration.
"""
    return prompt


def build_prompt(
    target: str,
    execution_mode: str = "autopilot",
    policy_mode: str = "decision_balanced",
) -> str:
    """Build complete prompt for RLM.completion().

    Combines the system prompt with the user's analysis target and
    execution parameters.

    Args:
        target: The analysis target description, e.g. "한국 전기차 충전 인프라 시장 분석".
        execution_mode: One of "autopilot", "review", "manual".
        policy_mode: One of "reporting_strict", "decision_balanced", "exploration_friendly".

    Returns:
        Complete prompt string.
    """
    system_prompt = build_system_prompt()

    user_section = f"""\

## Analysis Request

- **Target**: {target}
- **Execution mode**: {execution_mode}
- **Policy mode**: {policy_mode}

## Instructions

The project has already been created and is in the discovery state.
Perform a thorough market analysis following the state transition flow.
When you reach a user gate (scope_review, finding_review, opportunity_review,
decision_review), produce a summary report as FINAL_VAR() and stop.

Use the {policy_mode} policy mode for all quality thresholds and evidence requirements.
"""

    return system_prompt + user_section
