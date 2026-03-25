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


def _build_estimation_guide() -> str:
    """Build Estimation Engine workflow guide.

    Hard-coded text: workflow patterns are domain knowledge that cannot be
    auto-extracted from tool signatures.  Tool names referenced here are
    validated by test_system_prompt_tool_name_consistency.
    """
    return """\
## Estimation Engine Guide

### Key Concepts

- **lo / hi** = P10 / P90 — a subjective 80 % probability range (not a mathematically guaranteed interval).
- **source_reliability** (0.0–1.0): objective quality of the data source. Produced by Evidence Engine only — never invent a value. When no evidence exists, the default 0.5 applies.
- **Free variables**: any name outside METRIC_REGISTRY is accepted (e.g. "korean_household_count"). Free variables persist for the session.
- **Bounds clamping**: metrics with `bounds` in METRIC_REGISTRY are silently clamped. If your estimate is outside bounds, the stored interval will differ from what you passed.
- **Batch fusion**: when 2+ estimates exist for the same variable, they are automatically fused (order-independent). Check `has_conflicts` — if true, disjoint estimates exist; collect more evidence. Use `spread_ratio` to judge precision (lower = better).

### Workflow A — Single Estimate

1. `create_estimate(variable_name, lo, hi, method, source, source_reliability, evidence_id)` — register an initial estimate.
2. `update_estimate(...)` — add a **new** estimate and re-fuse (this does NOT overwrite; it appends then fuses).
3. `get_estimate(variable_name)` — read the fused result. If `has_conflicts` is true, resolve before proceeding.

### Workflow B — Fermi Decomposition

1. `create_fermi_tree(target_variable, operation)` — create a tree (operations: multiply, add, divide, subtract).
2. `add_fermi_leaf(tree_id, variable, lo, hi, source, evidence_id)` — add concrete values. Leaves without `evidence_id` are unverified.
3. `add_fermi_subtree(parent_tree_id, variable, operation)` — nest a sub-decomposition.
4. `evaluate_fermi_tree(tree_id)` — compute the result via interval arithmetic.
5. **Register the result**: call `create_estimate(target_variable, lo, hi, method="fermi", ...)` with the evaluated interval. Fermi results live only in the Fermi store until you do this.

### Workflow C — Constraint Verification

After completing estimates, verify metric-relation consistency:

`check_constraints(metric_intervals)` — belongs to the **Constraint Engine** (not Estimation Engine).

Input format: `{"MET-TAM": {"lo": 1e9, "hi": 5e9}, "MET-SAM": {"lo": 3e8, "hi": 2e9}}`.

### Workflow D — Distribution Analysis

Registered metrics (from METRIC_REGISTRY) automatically get a fitted probability distribution (Beta for ratios, Lognormal for currency/count). Free variables get no distribution.

- `get_distribution(variable_name)` — retrieve percentiles (p10/p25/p50/p75/p90), mode, mean for reporting to the user.
- Fermi tree results include `mc_summary` with Monte Carlo percentiles alongside the primary interval arithmetic result.
- Use distribution info to communicate uncertainty quality: narrow percentile ranges = high confidence, wide = low confidence.

### Connecting Estimates to the Analysis

- **Uncertain quantities** → Estimation Engine tools above.
- **Confirmed values** backed by strong evidence → `set_metric_value` to record the final metric.
- Estimation results can also be recorded as R-Graph node attributes for structural analysis.

### Workflow E — Reference Class Forecasting

Before creating estimates from scratch, check if past outcomes exist:

1. `suggest_estimate_from_reference(metric_id)` — get empirical P10/P90 from past outcomes.
2. If available, use as starting point for `create_estimate`, then refine with `update_estimate`.
3. If insufficient data (< 3 outcomes), proceed with manual estimation.

### Workflow F — Calibration

After completing an analysis cycle, check prediction quality:

1. `get_calibration(metric_id)` — see how past predictions performed per source tier.
2. `get_calibrated_reliability(source_tier)` — get data-driven source_reliability when calling `create_estimate`.
3. Calibration improves automatically as more outcomes are recorded via the Learning Engine.

### Deprecated Tools — Do Not Use

| Old (deprecated) | New replacement | Note |
|---|---|---|
| `set_prior` | `create_estimate` | old `confidence` ≠ new `source_reliability` (subjective certainty vs. objective source quality) |
| `get_prior` | `get_estimate` | |
| `update_belief` | `update_estimate` | |
| `list_beliefs` | `list_estimates` | |
"""


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
    estimation_guide = _build_estimation_guide()
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
- **finding_locked**: User decides whether to explore opportunities. Triggers: opportunity_included, opportunity_not_included.
- **opportunity_review**: User reviews opportunities. Triggers: opportunity_selected, opportunity_deepened, opportunity_completed_early.
- **decision_review**: User reviews strategy decision. Triggers: decision_approved, decision_revised.

{tool_section}

{estimation_guide}

{metric_section}

{workflow_section}

{ontology_reference}

## Execution Rules

1. If running standalone, create a project first. In runner mode, the project is already created — check current state with get_current_state().
2. Collect evidence before building R-Graph snapshots.
3. Build R-Graph (add nodes and edges) before running pattern matching.
4. For uncertain quantities, use Estimation Engine tools (create_estimate, Fermi trees). For confirmed values backed by evidence, use set_metric_value.
5. At each user gate, produce a structured summary and stop via FINAL_VAR().
6. Save final deliverables via save_deliverable before transitioning to completed.

### Error Recovery

7. If a tool returns {{"error": "..."}}, log the error and attempt an alternative approach.
8. If multiple tools fail consecutively, produce a partial report and stop at the current gate.

### Resuming from User Gates

9. When resuming from a user gate, the prompt will include a "Previous User Decision" section
   containing the user's revision_note, selected opportunity, or other feedback.
   You MUST read and incorporate every instruction in that section.
   If a revision_note says "limit scope to B2C", your next analysis phase must reflect that constraint.
   If a selection is provided, focus exclusively on the selected item.
   Do NOT ignore or override user gate decisions.

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
