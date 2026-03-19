"""E2E integration tests for CMIS v2 — 의도 정렬 8개 해결책 (Intent Alignment 8 Solutions).

Verifies that all 8 solutions' core invariants hold:
  1. transition() preconditions
  2. State-based tool guard
  3. User gate info (gate reports)
  4. finding_locked user gate
  5a. evidence_id mandatory in value engine
  5b. Strategy hardcoding removal
  5c. Portfolio pending handling
  6. Ontology expansion (product, segment)
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

# ---------------------------------------------------------------------------
# Fixture: override PROJECTS_DIR to a temp directory for isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_projects_dir(tmp_path: Path):
    """Redirect PROJECTS_DIR to tmp_path so tests don't pollute real data."""
    import cmis_v2.config as cfg
    import cmis_v2.events as ev
    import cmis_v2.engine_store as es
    import cmis_v2.project as proj

    original = cfg.PROJECTS_DIR
    cfg.PROJECTS_DIR = tmp_path
    # The modules cache the import-time value; patch their references too
    ev.PROJECTS_DIR = tmp_path
    es.PROJECTS_DIR = tmp_path
    proj.PROJECTS_DIR = tmp_path

    yield

    cfg.PROJECTS_DIR = original
    ev.PROJECTS_DIR = original
    es.PROJECTS_DIR = original
    proj.PROJECTS_DIR = original


@pytest.fixture(autouse=True)
def _clear_engine_stores():
    """Clear module-level in-memory stores between tests."""
    from cmis_v2.engines.evidence import _EVIDENCE_STORE
    from cmis_v2.engines.world import _SNAPSHOTS
    from cmis_v2.engines.value import _VALUE_STORE
    from cmis_v2.engines.strategy import _STRATEGY_STORE

    _EVIDENCE_STORE.clear()
    _SNAPSHOTS.clear()
    _VALUE_STORE.clear()
    _STRATEGY_STORE.clear()

    yield

    _EVIDENCE_STORE.clear()
    _SNAPSHOTS.clear()
    _VALUE_STORE.clear()
    _STRATEGY_STORE.clear()


# ---------------------------------------------------------------------------
# Helper: create a project and advance it to a given state
# ---------------------------------------------------------------------------


def _create_project(name: str = "test") -> str:
    """Create a project and return its project_id."""
    from cmis_v2.project import create_project
    manifest = create_project(name=name, description="test project", domain_id="TEST_KR")
    return manifest["project_id"]


def _advance_to(project_id: str, target_state: str) -> None:
    """Advance a project from 'requested' through the standard forward path
    to the given *target_state*, satisfying all preconditions along the way.
    """
    from cmis_v2.project import transition, lock_scope
    from cmis_v2.engine_store import save_engine_data

    # State ordering for the standard forward path
    path: list[tuple[str, str]] = [
        ("requested", "project_created"),
        ("discovery", "discovery_completed"),
        ("scope_review", "scope_approved"),
        # scope_locked requires lock_scope() before "auto"
        ("scope_locked", "auto"),
        ("data_collection", "data_quality_passed"),
        ("structure_analysis", "analysis_completed"),
        ("finding_review", "finding_approved"),
        ("finding_locked", "opportunity_included"),
        ("opportunity_discovery", "opportunity_completed"),
        ("opportunity_review", "opportunity_selected"),
        ("strategy_design", "strategy_completed"),
        ("decision_review", "decision_approved"),
        ("synthesis", "deliverable_saved"),
    ]

    for state, trigger in path:
        from cmis_v2.project import get_current_state
        current = get_current_state(project_id)
        if current == target_state:
            return

        # Satisfy preconditions for specific transitions
        if state == "scope_locked" and trigger == "auto":
            lock_scope(project_id, {"domain": "TEST", "notes": "test"})
        elif state == "data_collection" and trigger == "data_quality_passed":
            # Need evidence data in engine_store
            save_engine_data(project_id, "evidence", "EVD-test", {"records": [{"source_tier": "official"}]})
        elif trigger in ("finding_approved", "opportunity_selected", "decision_approved"):
            # Need a passing policy gate result
            save_engine_data(project_id, "policy", "gate-latest", {"passed": True, "overall_passed": True})

        result = transition(project_id, trigger, actor="test")
        assert "error" not in result, f"Unexpected error advancing to {target_state} at trigger {trigger}: {result}"


# =========================================================================
# Solution 1: transition() preconditions
# =========================================================================


class TestSolution1TransitionPreconditions:
    """transition() must enforce preconditions before certain triggers."""

    def test_data_quality_passed_requires_evidence(self):
        """data_quality_passed from data_collection must fail without evidence data."""
        from cmis_v2.project import transition

        pid = _create_project("s1-evidence")
        _advance_to(pid, "data_collection")

        # No evidence saved — transition should fail
        result = transition(pid, "data_quality_passed", actor="test")
        assert "error" in result
        assert "evidence" in result["error"].lower() or "Precondition" in result["error"]

    def test_data_quality_passed_succeeds_with_evidence(self):
        """data_quality_passed succeeds when evidence exists."""
        from cmis_v2.project import transition
        from cmis_v2.engine_store import save_engine_data

        pid = _create_project("s1-evidence-ok")
        _advance_to(pid, "data_collection")
        save_engine_data(pid, "evidence", "EVD-001", {"records": [{"source_tier": "official"}]})

        result = transition(pid, "data_quality_passed", actor="test")
        assert "error" not in result
        assert result["current_state"] == "structure_analysis"

    def test_scope_locked_auto_requires_lock_scope(self):
        """auto trigger from scope_locked must fail without locked scope."""
        from cmis_v2.project import transition

        pid = _create_project("s1-scope")
        _advance_to(pid, "scope_locked")

        # Manually wipe scope to ensure precondition fails
        from cmis_v2.project import _read_manifest, _write_manifest
        manifest = _read_manifest(pid)
        manifest["scope"] = None
        _write_manifest(pid, manifest)

        result = transition(pid, "auto", actor="test")
        assert "error" in result
        assert "scope" in result["error"].lower() or "Precondition" in result["error"]

    def test_scope_locked_auto_succeeds_with_lock(self):
        """auto trigger from scope_locked succeeds when scope is locked."""
        from cmis_v2.project import transition, lock_scope

        pid = _create_project("s1-scope-ok")
        _advance_to(pid, "scope_locked")
        lock_scope(pid, {"domain": "TEST"})

        result = transition(pid, "auto", actor="test")
        assert "error" not in result
        assert result["current_state"] == "data_collection"

    def test_finding_approved_requires_policy_gate(self):
        """finding_approved from finding_review must fail without policy gate."""
        from cmis_v2.project import transition

        pid = _create_project("s1-policy-finding")
        _advance_to(pid, "finding_review")

        # Clear out any policy data so the precondition fails
        import cmis_v2.config as cfg
        policy_dir = cfg.PROJECTS_DIR / pid / "engine_data" / "policy"
        if policy_dir.exists():
            shutil.rmtree(policy_dir)

        result = transition(pid, "finding_approved", actor="test")
        assert "error" in result
        assert "policy" in result["error"].lower() or "Precondition" in result["error"]

    def test_opportunity_selected_requires_policy_gate(self):
        """opportunity_selected from opportunity_review must fail without policy gate."""
        from cmis_v2.project import transition

        pid = _create_project("s1-policy-opp")
        _advance_to(pid, "opportunity_review")

        import cmis_v2.config as cfg
        policy_dir = cfg.PROJECTS_DIR / pid / "engine_data" / "policy"
        if policy_dir.exists():
            shutil.rmtree(policy_dir)

        result = transition(pid, "opportunity_selected", actor="test")
        assert "error" in result
        assert "policy" in result["error"].lower() or "Precondition" in result["error"]

    def test_decision_approved_requires_policy_gate(self):
        """decision_approved from decision_review must fail without policy gate."""
        from cmis_v2.project import transition

        pid = _create_project("s1-policy-dec")
        _advance_to(pid, "decision_review")

        import cmis_v2.config as cfg
        policy_dir = cfg.PROJECTS_DIR / pid / "engine_data" / "policy"
        if policy_dir.exists():
            shutil.rmtree(policy_dir)

        result = transition(pid, "decision_approved", actor="test")
        assert "error" in result
        assert "policy" in result["error"].lower() or "Precondition" in result["error"]

    def test_policy_gate_passes_when_result_exists(self):
        """Policy-gated transitions succeed when a passing gate result exists."""
        from cmis_v2.project import transition
        from cmis_v2.engine_store import save_engine_data

        pid = _create_project("s1-policy-ok")
        _advance_to(pid, "finding_review")
        save_engine_data(pid, "policy", "gate-check", {"passed": True, "overall_passed": True})

        result = transition(pid, "finding_approved", actor="test")
        assert "error" not in result
        assert result["current_state"] == "finding_locked"


# =========================================================================
# Solution 2: State-based tool guard
# =========================================================================


class TestSolution2ToolGuard:
    """is_tool_allowed must enforce state-based tool access."""

    def test_always_allowed_tools_work_in_any_state(self):
        """_ALWAYS_ALLOWED tools are allowed in every state."""
        from cmis_v2.tools import is_tool_allowed, _ALWAYS_ALLOWED, _STATE_ALLOWED_TOOLS

        all_states = list(_STATE_ALLOWED_TOOLS.keys())
        for tool in _ALWAYS_ALLOWED:
            for state in all_states:
                assert is_tool_allowed(tool, state), (
                    f"ALWAYS_ALLOWED tool {tool!r} should be allowed in {state!r}"
                )

    def test_state_specific_tools_allowed_in_correct_state(self):
        """Tools listed for a state are allowed there."""
        from cmis_v2.tools import is_tool_allowed, _STATE_ALLOWED_TOOLS

        for state, tools in _STATE_ALLOWED_TOOLS.items():
            for tool in tools:
                assert is_tool_allowed(tool, state), (
                    f"Tool {tool!r} should be allowed in {state!r}"
                )

    def test_tools_blocked_in_wrong_state(self):
        """Tools NOT in _ALWAYS_ALLOWED and NOT in a state's set should be blocked."""
        from cmis_v2.tools import is_tool_allowed, _ALWAYS_ALLOWED, _STATE_ALLOWED_TOOLS

        # "collect_evidence" is allowed in discovery and data_collection
        # but not in, e.g., strategy_design
        assert not is_tool_allowed("collect_evidence", "strategy_design")
        assert not is_tool_allowed("collect_evidence", "synthesis")
        assert not is_tool_allowed("collect_evidence", "completed")

    def test_create_project_only_in_requested(self):
        """create_project is only in 'requested' state."""
        from cmis_v2.tools import is_tool_allowed

        assert is_tool_allowed("create_project", "requested")
        assert not is_tool_allowed("create_project", "discovery")
        assert not is_tool_allowed("create_project", "structure_analysis")

    def test_search_strategies_only_in_strategy_design(self):
        """search_strategies is only in 'strategy_design' state."""
        from cmis_v2.tools import is_tool_allowed

        assert is_tool_allowed("search_strategies", "strategy_design")
        assert not is_tool_allowed("search_strategies", "discovery")
        assert not is_tool_allowed("search_strategies", "data_collection")

    def test_save_deliverable_only_in_synthesis(self):
        """save_deliverable is only in 'synthesis' state."""
        from cmis_v2.tools import is_tool_allowed

        assert is_tool_allowed("save_deliverable", "synthesis")
        assert not is_tool_allowed("save_deliverable", "discovery")
        assert not is_tool_allowed("save_deliverable", "strategy_design")

    def test_unknown_state_blocks_everything_except_always(self):
        """An unknown state should only allow ALWAYS_ALLOWED tools."""
        from cmis_v2.tools import is_tool_allowed, _ALWAYS_ALLOWED

        assert is_tool_allowed("load_project", "nonexistent_state")
        assert not is_tool_allowed("collect_evidence", "nonexistent_state")
        assert not is_tool_allowed("build_snapshot", "nonexistent_state")

    def test_structure_analysis_tools(self):
        """structure_analysis state allows build_snapshot, add_node, etc."""
        from cmis_v2.tools import is_tool_allowed

        allowed = [
            "build_snapshot", "add_node", "add_edge", "get_snapshot",
            "match_patterns", "evaluate_metrics", "set_metric_value",
        ]
        blocked = ["collect_evidence", "search_strategies", "save_deliverable"]

        for tool in allowed:
            assert is_tool_allowed(tool, "structure_analysis"), f"{tool} should be allowed"
        for tool in blocked:
            assert not is_tool_allowed(tool, "structure_analysis"), f"{tool} should be blocked"


# =========================================================================
# Solution 3: User gate info (gate reports)
# =========================================================================


class TestSolution3UserGateInfo:
    """When reaching a user gate state, the system provides gate context."""

    def test_policy_check_all_gates_produces_report(self):
        """check_all_gates produces a report with pass/fail and suggestions."""
        from cmis_v2.engines.policy import check_all_gates

        evidence = {"records": [{"source_tier": "official", "content": "data"}]}
        report = check_all_gates(evidence_result=evidence, policy_id="decision_balanced")

        assert "overall_passed" in report
        assert "evidence_gate" in report
        assert "suggested_actions" in report
        assert isinstance(report["suggested_actions"], list)

    def test_check_all_gates_with_value_records(self):
        """check_all_gates evaluates both evidence and value gates."""
        from cmis_v2.engines.policy import check_all_gates

        evidence = {"records": [{"source_tier": "official"}]}
        values = [{"metric_id": "MET-TAM", "confidence": 0.8}]
        report = check_all_gates(
            evidence_result=evidence,
            value_records=values,
            policy_id="decision_balanced",
        )
        assert "evidence_gate" in report
        assert "value_gate" in report
        assert "summary" in report

    def test_check_evidence_gate_provides_violation_details(self):
        """check_evidence_gate returns per-gate violation info."""
        from cmis_v2.engines.policy import check_evidence_gate

        evidence = {"records": []}
        result = check_evidence_gate(evidence, policy_id="decision_balanced")

        assert "violations" in result
        assert isinstance(result["violations"], list)
        assert "passed" in result


# =========================================================================
# Solution 4: finding_locked user gate
# =========================================================================


class TestSolution4FindingLockedGate:
    """finding_locked is a user gate — user chooses next direction."""

    def test_finding_locked_is_user_gate(self):
        """finding_locked must be in _USER_GATE_STATES."""
        from cmis_v2.state_machine import is_user_gate

        assert is_user_gate("finding_locked") is True

    def test_finding_locked_allows_opportunity_included(self):
        """User can choose opportunity_included from finding_locked."""
        from cmis_v2.state_machine import can_transition, next_state

        assert can_transition("finding_locked", "opportunity_included")
        assert next_state("finding_locked", "opportunity_included") == "opportunity_discovery"

    def test_finding_locked_allows_opportunity_not_included(self):
        """User can choose opportunity_not_included from finding_locked."""
        from cmis_v2.state_machine import can_transition, next_state

        assert can_transition("finding_locked", "opportunity_not_included")
        assert next_state("finding_locked", "opportunity_not_included") == "synthesis"

    def test_finding_locked_full_lifecycle(self):
        """Advance a project to finding_locked and exercise both gate choices."""
        from cmis_v2.project import transition

        # Path A: opportunity_included
        pid_a = _create_project("s4-include")
        _advance_to(pid_a, "finding_locked")
        result = transition(pid_a, "opportunity_included", actor="user")
        assert "error" not in result
        assert result["current_state"] == "opportunity_discovery"

        # Path B: opportunity_not_included (skip to synthesis)
        pid_b = _create_project("s4-skip")
        _advance_to(pid_b, "finding_locked")
        result = transition(pid_b, "opportunity_not_included", actor="user")
        assert "error" not in result
        assert result["current_state"] == "synthesis"


# =========================================================================
# Solution 5a: evidence_id mandatory in value engine
# =========================================================================


class TestSolution5aEvidenceIdMandatory:
    """set_metric_value() enforces evidence_id unless force_unverified."""

    def test_set_metric_value_without_evidence_id_fails(self):
        """Calling set_metric_value without evidence_id should return error."""
        from cmis_v2.engines.value import set_metric_value

        result = set_metric_value(
            metric_id="MET-TAM",
            point_estimate=1_000_000,
            confidence=0.5,
        )
        assert "error" in result
        assert "evidence_id" in result["error"]

    def test_set_metric_value_force_unverified(self):
        """force_unverified=True bypasses evidence_id requirement but marks quality."""
        from cmis_v2.engines.value import set_metric_value

        result = set_metric_value(
            metric_id="MET-TAM",
            point_estimate=1_000_000,
            confidence=0.5,
            force_unverified=True,
        )
        assert "error" not in result
        assert result["quality"]["status"] == "force_unverified"

    def test_set_metric_value_with_evidence_id_ok(self):
        """Providing evidence_id + evidence_summary sets quality to 'ok'."""
        from cmis_v2.engines.value import set_metric_value

        result = set_metric_value(
            metric_id="MET-Revenue",
            point_estimate=5_000_000,
            confidence=0.7,
            evidence_id="EVD-001",
            evidence_summary="From KOSIS data on market revenue.",
        )
        assert "error" not in result
        assert result["quality"]["status"] == "ok"
        assert result["lineage"]["evidence_id"] == "EVD-001"

    def test_set_metric_value_invalid_method(self):
        """Invalid method should return error."""
        from cmis_v2.engines.value import set_metric_value

        result = set_metric_value(
            metric_id="MET-TAM",
            point_estimate=100,
            method="invalid_method",
            evidence_id="EVD-001",
        )
        assert "error" in result


# =========================================================================
# Solution 5b: Strategy hardcoding removal
# =========================================================================


class TestSolution5bStrategyHardcodingRemoval:
    """search_strategies() derives candidates from pattern matches, not hardcoded data."""

    def test_search_strategies_uses_pattern_matches(self):
        """Strategies are generated from pattern_matches, not hardcoded."""
        from cmis_v2.engines.strategy import search_strategies

        patterns = [
            {"pattern_id": "P-001", "pattern_name": "Subscription Platform", "fit_score": 0.8, "missing_traits": []},
            {"pattern_id": "P-002", "pattern_name": "Marketplace", "fit_score": 0.6, "missing_traits": ["scale_tier"]},
        ]

        result = search_strategies(
            goal_description="Increase market share",
            pattern_matches=patterns,
        )

        assert "candidates" in result
        candidates = result["candidates"]
        # At least 2 individual + 1 combined = 3
        assert len(candidates) >= 3

        # Each candidate references its source patterns
        for c in candidates:
            assert "based_on_patterns" in c
            assert len(c["based_on_patterns"]) >= 1
            # expected_impact starts as pending (not hardcoded)
            assert c["expected_impact"]["_status"] == "pending_evidence"
            assert c["expected_impact"]["revenue_change"] is None

    def test_search_strategies_no_patterns_no_candidates(self):
        """Without pattern matches, no candidates are generated."""
        from cmis_v2.engines.strategy import search_strategies

        result = search_strategies(
            goal_description="Increase market share",
            pattern_matches=[],
        )
        assert result["candidates"] == []

    def test_search_strategies_lineage_info(self):
        """Strategies carry lineage info (not hardcoded)."""
        from cmis_v2.engines.strategy import search_strategies

        patterns = [
            {"pattern_id": "P-001", "pattern_name": "Sub", "fit_score": 0.9, "missing_traits": []},
        ]
        result = search_strategies(
            goal_description="test",
            pattern_matches=patterns,
        )
        assert result["lineage"]["engine"] == "strategy"
        assert result["lineage"]["pattern_count"] == 1


# =========================================================================
# Solution 5c: Portfolio pending handling
# =========================================================================


class TestSolution5cPortfolioPending:
    """evaluate_portfolio() handles pending strategies via pending_policy."""

    def _setup_strategies(self):
        """Create one complete and one pending strategy."""
        from cmis_v2.engines.strategy import search_strategies, set_strategy_impact

        patterns = [
            {"pattern_id": "P-A", "pattern_name": "A", "fit_score": 0.8, "missing_traits": []},
            {"pattern_id": "P-B", "pattern_name": "B", "fit_score": 0.6, "missing_traits": ["x"]},
        ]
        result = search_strategies(goal_description="test", pattern_matches=patterns)
        candidates = result["candidates"]

        # Set impact on first individual candidate only
        complete_id = candidates[0]["strategy_id"]
        set_strategy_impact(
            strategy_id=complete_id,
            revenue_change="+15%",
            market_share_change="+5%",
            evidence_id="EVD-impact",
            rationale="Based on evidence",
        )

        # Second individual candidate has no impact set (pending)
        pending_id = candidates[1]["strategy_id"]

        return complete_id, pending_id

    def test_pending_policy_exclude(self):
        """pending_policy='exclude' skips incomplete strategies."""
        from cmis_v2.engines.strategy import evaluate_portfolio

        complete_id, pending_id = self._setup_strategies()

        result = evaluate_portfolio(
            strategy_ids=[complete_id, pending_id],
            pending_policy="exclude",
        )
        assert "error" not in result
        # Only the complete one should be in ranked
        ranked_ids = [r["strategy_id"] for r in result["ranked_strategies"]]
        assert complete_id in ranked_ids
        assert pending_id not in ranked_ids
        # Pending should be in pending_items
        pending_ids = [p["strategy_id"] for p in result["pending_items"]]
        assert pending_id in pending_ids
        assert result["is_complete"] is False

    def test_pending_policy_fail(self):
        """pending_policy='fail' returns error on pending strategies."""
        from cmis_v2.engines.strategy import evaluate_portfolio

        complete_id, pending_id = self._setup_strategies()

        result = evaluate_portfolio(
            strategy_ids=[complete_id, pending_id],
            pending_policy="fail",
        )
        assert "error" in result

    def test_pending_policy_partial(self):
        """pending_policy='partial' separates pending into pending_items."""
        from cmis_v2.engines.strategy import evaluate_portfolio

        complete_id, pending_id = self._setup_strategies()

        result = evaluate_portfolio(
            strategy_ids=[complete_id, pending_id],
            pending_policy="partial",
        )
        assert "error" not in result
        # Both should appear in ranked (partial includes pending at score 0)
        ranked_ids = [r["strategy_id"] for r in result["ranked_strategies"]]
        assert complete_id in ranked_ids
        assert pending_id in ranked_ids
        # Pending items list should also contain the pending one
        pending_item_ids = [p["strategy_id"] for p in result["pending_items"]]
        assert pending_id in pending_item_ids

    def test_pending_policy_invalid(self):
        """Invalid pending_policy returns error."""
        from cmis_v2.engines.strategy import evaluate_portfolio

        result = evaluate_portfolio(strategy_ids=[], pending_policy="invalid")
        assert "error" in result

    def test_all_complete_is_complete_true(self):
        """When all strategies have impact set, is_complete is True."""
        from cmis_v2.engines.strategy import (
            search_strategies, set_strategy_impact, evaluate_portfolio,
        )

        patterns = [{"pattern_id": "P-X", "pattern_name": "X", "fit_score": 0.9, "missing_traits": []}]
        result = search_strategies(goal_description="test", pattern_matches=patterns)
        sid = result["candidates"][0]["strategy_id"]

        set_strategy_impact(sid, "+10%", "+3%", evidence_id="EVD-ok", rationale="ok")

        portfolio = evaluate_portfolio(strategy_ids=[sid])
        assert portfolio["is_complete"] is True
        assert len(portfolio["pending_items"]) == 0


# =========================================================================
# Solution 6: Ontology expansion (product, segment)
# =========================================================================


class TestSolution6OntologyExpansion:
    """ontology.yaml and generated types must include product and segment."""

    def test_ontology_yaml_has_product_and_segment(self):
        """ontology.yaml must define product and segment as node types."""
        ontology_path = Path(__file__).parent.parent / "schemas" / "ontology.yaml"
        with open(ontology_path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)

        node_types = doc["ontology"]["node_types"]
        assert "product" in node_types
        assert "segment" in node_types

    def test_generated_types_include_product_and_segment(self):
        """Generated NodeType Literal must include 'product' and 'segment'."""
        from cmis_v2.generated.types import NodeType
        import typing

        # Extract the literal values
        args = typing.get_args(NodeType)
        assert "product" in args
        assert "segment" in args

    def test_product_node_creation(self):
        """A product node can be added to a snapshot."""
        from cmis_v2.engines.world import build_snapshot, add_node

        snap = build_snapshot(domain_id="TEST")
        node = add_node(
            snap["snapshot_id"],
            "product",
            {"name": "TestProduct", "traits": {"category": "digital_service"}},
        )
        assert "error" not in node
        assert node["type"] == "product"

    def test_segment_node_creation(self):
        """A segment node can be added to a snapshot."""
        from cmis_v2.engines.world import build_snapshot, add_node

        snap = build_snapshot(domain_id="TEST")
        node = add_node(
            snap["snapshot_id"],
            "segment",
            {"name": "Adults 25-40", "traits": {"segment_type": "b2c"}},
        )
        assert "error" not in node
        assert node["type"] == "segment"

    def test_product_segment_edges(self):
        """product_targets_segment and actor_offers_product edges work."""
        from cmis_v2.engines.world import build_snapshot, add_node, add_edge

        snap = build_snapshot(domain_id="TEST")
        actor = add_node(snap["snapshot_id"], "actor", {"traits": {"kind": "company"}})
        product = add_node(snap["snapshot_id"], "product", {"traits": {}})
        segment = add_node(snap["snapshot_id"], "segment", {"traits": {}})

        edge1 = add_edge(snap["snapshot_id"], "actor_offers_product", actor["id"], product["id"])
        assert "error" not in edge1

        edge2 = add_edge(snap["snapshot_id"], "product_targets_segment", product["id"], segment["id"])
        assert "error" not in edge2

    def test_snapshot_summary_counts_product_segment(self):
        """Snapshot summary tracks product_count and segment_count."""
        from cmis_v2.engines.world import build_snapshot, add_node, get_snapshot

        snap = build_snapshot(domain_id="TEST")
        sid = snap["snapshot_id"]

        add_node(sid, "product", {"traits": {}})
        add_node(sid, "product", {"traits": {}})
        add_node(sid, "segment", {"traits": {"segment_type": "b2b"}})

        updated = get_snapshot(sid)
        assert updated["summary"]["product_count"] == 2
        assert updated["summary"]["segment_count"] == 1

    def test_validators_accept_product_segment_traits(self):
        """validate_node_traits accepts product and segment node types."""
        from cmis_v2.generated.validators import validate_node_traits

        assert validate_node_traits("product", {"category": "saas"}) == []
        assert validate_node_traits("segment", {"segment_type": "b2c", "growth_potential": "high"}) == []

    def test_validators_reject_unknown_trait_for_product(self):
        """validate_node_traits rejects unknown traits for product."""
        from cmis_v2.generated.validators import validate_node_traits

        errors = validate_node_traits("product", {"nonexistent_trait": "x"})
        assert len(errors) > 0


# =========================================================================
# Additional cross-cutting integration tests
# =========================================================================


class TestCrossCuttingIntegration:
    """Tests that verify multiple solutions work together."""

    def test_full_forward_path(self):
        """A project can traverse the entire forward path to completed."""
        from cmis_v2.project import get_current_state, transition, save_deliverable

        pid = _create_project("full-path")
        _advance_to(pid, "synthesis")

        # Save deliverable and complete
        save_deliverable(pid, "report.md", "# Final Report")
        result = transition(pid, "deliverable_saved", actor="test")
        assert "error" not in result
        assert result["current_state"] == "completed"

        from cmis_v2.state_machine import is_terminal
        assert is_terminal("completed")

    def test_user_gate_states_are_correct(self):
        """All 5 user gate states are properly declared."""
        from cmis_v2.state_machine import is_user_gate

        gates = ["scope_review", "finding_review", "finding_locked",
                 "opportunity_review", "decision_review"]
        for g in gates:
            assert is_user_gate(g), f"{g} should be a user gate"

        non_gates = ["requested", "discovery", "data_collection",
                     "structure_analysis", "synthesis", "completed"]
        for ng in non_gates:
            assert not is_user_gate(ng), f"{ng} should NOT be a user gate"

    def test_event_system_records_transitions(self):
        """Events are recorded for each transition."""
        from cmis_v2.project import get_project_events

        pid = _create_project("events-test")
        _advance_to(pid, "discovery")

        events = get_project_events(pid)
        assert len(events) >= 2  # project.created + state.transitioned
        types = [e["type"] for e in events]
        assert "project.created" in types
        assert "state.transitioned" in types

    def test_set_strategy_impact_requires_evidence_id(self):
        """set_strategy_impact must fail without evidence_id."""
        from cmis_v2.engines.strategy import search_strategies, set_strategy_impact

        patterns = [{"pattern_id": "P-1", "pattern_name": "A", "fit_score": 0.7, "missing_traits": []}]
        result = search_strategies(goal_description="test", pattern_matches=patterns)
        sid = result["candidates"][0]["strategy_id"]

        err_result = set_strategy_impact(
            strategy_id=sid,
            revenue_change="+10%",
            market_share_change="+5%",
            evidence_id="",  # empty!
        )
        assert "error" in err_result

    def test_invalid_transition_returns_error(self):
        """An impossible transition returns an error dict, not an exception."""
        from cmis_v2.project import transition

        pid = _create_project("invalid-trans")
        _advance_to(pid, "discovery")

        # Can't do "deliverable_saved" from discovery
        result = transition(pid, "deliverable_saved", actor="test")
        assert "error" in result
