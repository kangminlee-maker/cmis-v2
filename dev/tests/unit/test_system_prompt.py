"""Tests for system_prompt module — Estimation Engine guide integration."""

from __future__ import annotations

import re


def test_system_prompt_contains_estimation_guide() -> None:
    """Estimation Engine guide section must be present in the prompt."""
    from cmis_v2.system_prompt import build_system_prompt

    prompt = build_system_prompt()
    assert "## Estimation Engine Guide" in prompt
    assert "Workflow A" in prompt
    assert "Workflow B" in prompt
    assert "Workflow C" in prompt
    assert "Deprecated Tools" in prompt


def test_system_prompt_tool_name_consistency() -> None:
    """Every tool name mentioned in the estimation guide must exist in CMISTools.

    The system prompt is the LLM's only normative document.  If a tool name
    drifts (renamed/removed), the LLM will call a non-existent tool.
    """
    from cmis_v2.system_prompt import _build_estimation_guide
    from cmis_v2.tools import CMISTools

    guide = _build_estimation_guide()
    tools = CMISTools()
    registered_names = set(tools.as_rlm_tools().keys())

    # Extract tool names referenced as `tool_name(` or `tool_name` in code fences
    # Matches: create_estimate, create_fermi_tree, etc.
    mentioned = set(re.findall(r"\b([a-z][a-z_]+)\(", guide))

    # Known non-tool function-like patterns to exclude
    not_tools = {"dict", "check"}

    tool_mentions = mentioned - not_tools
    missing = tool_mentions - registered_names

    assert not missing, (
        f"Estimation guide references tools not in CMISTools: {missing}. "
        f"Either update the guide or register the tool."
    )


def test_rule4_does_not_forbid_set_metric_value() -> None:
    """Rule 4 must distinguish uncertain vs confirmed, not forbid set_metric_value."""
    from cmis_v2.system_prompt import build_system_prompt

    prompt = build_system_prompt()
    assert "instead of set_metric_value" not in prompt.lower()
    assert "set_metric_value" in prompt
