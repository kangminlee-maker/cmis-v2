"""CMIS v2 RLM tool registry.

Wraps every engine function (evidence, world, pattern, value) and project
management function into RLM ``custom_tools`` format so that the language
model can invoke them during an analysis session.  Each call is automatically
logged as an ``engine.called`` event when a *project_id* is active.
"""

from __future__ import annotations

from typing import Any, Callable

# ---------------------------------------------------------------------------
# State-based tool filtering
# ---------------------------------------------------------------------------

_ALWAYS_ALLOWED: frozenset[str] = frozenset({
    "load_project",
    "get_current_state",
    "get_project_summary",
    "get_project_events",
    "list_projects",
    "load_policy",
    "check_compatibility",
    "get_estimate",
    "list_estimates",
})

_STATE_ALLOWED_TOOLS: dict[str, frozenset[str]] = {
    "requested": frozenset({"create_project", "transition"}),
    "discovery": frozenset({
        "collect_evidence", "add_record", "get_evidence",
        "create_estimate", "get_estimate", "list_estimates",
        "create_fermi_tree", "add_fermi_leaf", "add_fermi_subtree", "evaluate_fermi_tree",
        "set_prior", "get_prior", "list_beliefs",
        "check_evidence_gate", "transition", "lock_scope",
    }),
    "scope_locked": frozenset({"transition"}),
    "data_collection": frozenset({
        "collect_evidence", "add_record", "get_evidence",
        "create_estimate", "get_estimate", "update_estimate", "list_estimates",
        "create_fermi_tree", "add_fermi_leaf", "add_fermi_subtree", "evaluate_fermi_tree",
        "set_prior", "get_prior", "update_belief", "list_beliefs",
        "check_evidence_gate", "transition", "add_run",
    }),
    "structure_analysis": frozenset({
        "build_snapshot", "add_node", "add_edge", "get_snapshot",
        "match_patterns", "evaluate_metrics", "set_metric_value",
        "get_metric_value", "check_value_gate", "check_all_gates",
        "create_estimate", "get_estimate", "update_estimate",
        "create_fermi_tree", "add_fermi_leaf", "add_fermi_subtree", "evaluate_fermi_tree",
        "transition", "get_evidence", "add_run",
    }),
    "finding_locked": frozenset({
        "discover_gaps", "get_snapshot", "match_patterns", "transition",
    }),
    "opportunity_discovery": frozenset({
        "discover_gaps", "get_snapshot", "match_patterns",
        "evaluate_metrics", "set_metric_value", "get_metric_value",
        "transition", "add_run",
    }),
    "strategy_design": frozenset({
        "search_strategies", "evaluate_portfolio", "get_snapshot",
        "get_metric_value", "evaluate_metrics", "set_metric_value",
        "check_value_gate", "check_all_gates", "transition",
        "add_run", "update_belief", "set_strategy_impact",
        "create_estimate", "get_estimate", "update_estimate",
        "create_fermi_tree", "add_fermi_leaf", "add_fermi_subtree", "evaluate_fermi_tree",
    }),
    "synthesis": frozenset({
        "save_deliverable", "get_snapshot", "get_evidence",
        "get_metric_value", "get_project_summary", "get_project_events",
        "transition", "check_all_gates",
    }),
    "completed": frozenset({
        "record_outcome", "get_learning_summary", "apply_learnings",
    }),
    "rejected": frozenset({
        "get_evidence", "get_snapshot", "get_metric_value",
        "get_learning_summary",
    }),
    # User gates — read-only
    "scope_review": frozenset({
        "get_evidence", "get_snapshot", "get_metric_value",
    }),
    "finding_review": frozenset({
        "get_evidence", "get_snapshot", "get_metric_value",
    }),
    "opportunity_review": frozenset({
        "get_evidence", "get_snapshot", "get_metric_value",
    }),
    "decision_review": frozenset({
        "get_evidence", "get_snapshot", "get_metric_value",
    }),
}


def is_tool_allowed(tool_name: str, state: str) -> bool:
    """Return True if *tool_name* is allowed in *state*."""
    if tool_name in _ALWAYS_ALLOWED:
        return True
    state_tools = _STATE_ALLOWED_TOOLS.get(state, frozenset())
    return tool_name in state_tools


class CMISTools:
    """Wraps all CMIS v2 engines and project management as RLM custom_tools."""

    def __init__(self, project_id: str | None = None) -> None:
        self.project_id = project_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, tool_name: str, args: dict[str, Any], result: dict[str, Any]) -> None:
        """Log an ``engine.called`` event when *project_id* is set."""
        if self.project_id:
            from cmis_v2.events import emit_event

            emit_event(
                project_id=self.project_id,
                event_type="engine.called",
                actor="rlm",
                payload={
                    "tool": tool_name,
                    "args": args,
                    "has_error": "error" in result,
                },
            )

    def _get_current_state_str(self) -> str:
        """Return the current project state, or empty string if unknown."""
        if not self.project_id:
            return ""
        try:
            from cmis_v2.project import get_current_state
            return get_current_state(self.project_id)
        except Exception:
            return ""

    def _safe_call(
        self, tool_name: str, fn: Callable[..., Any], args: dict[str, Any]
    ) -> dict[str, Any]:
        """Call *fn* with *args*, log, and return the result or an error dict."""
        # --- Tool guard: state-based filtering ---
        current_state = self._get_current_state_str()
        if current_state and not is_tool_allowed(tool_name, current_state):
            err: dict[str, Any] = {
                "error": (
                    f"Tool '{tool_name}' is not allowed in state '{current_state}'. "
                    f"Allowed tools: {sorted(_ALWAYS_ALLOWED | _STATE_ALLOWED_TOOLS.get(current_state, frozenset()))}"
                )
            }
            self._log(tool_name, args, err)
            return err
        try:
            result = fn(**args)
            # Normalise to dict for logging (some functions return list/str)
            if isinstance(result, dict):
                self._log(tool_name, args, result)
            else:
                self._log(tool_name, args, {})
            return result
        except Exception as exc:
            err: dict[str, Any] = {"error": str(exc)}
            self._log(tool_name, args, err)
            return err

    # ------------------------------------------------------------------
    # Evidence engine wrappers
    # ------------------------------------------------------------------

    def collect_evidence(
        self,
        query: str,
        domain_id: str = "",
        region: str = "KR",
        metric_ids: list[str] | None = None,
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """Collect evidence for a query. Returns evidence_id, records, sufficiency."""
        from cmis_v2.engines.evidence import collect_evidence

        return self._safe_call(
            "collect_evidence",
            collect_evidence,
            {"query": query, "domain_id": domain_id, "region": region, "metric_ids": metric_ids, "sources": sources, "project_id": self.project_id or ""},
        )

    def add_record(
        self,
        evidence_id: str,
        source_tier: str,
        source_name: str,
        content: str,
        confidence: float = 0.5,
        metric_ids_covered: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add an evidence record to an existing evidence collection."""
        from cmis_v2.engines.evidence import add_record

        return self._safe_call(
            "add_record",
            add_record,
            {
                "evidence_id": evidence_id,
                "source_tier": source_tier,
                "source_name": source_name,
                "content": content,
                "confidence": confidence,
                "metric_ids_covered": metric_ids_covered,
                "project_id": self.project_id or "",
            },
        )

    def get_evidence(self, evidence_id: str) -> dict[str, Any]:
        """Retrieve an evidence collection by ID."""
        from cmis_v2.engines.evidence import get_evidence

        return self._safe_call("get_evidence", get_evidence, {"evidence_id": evidence_id, "project_id": self.project_id or ""})

    # ------------------------------------------------------------------
    # World engine wrappers
    # ------------------------------------------------------------------

    def build_snapshot(
        self,
        domain_id: str,
        region: str = "KR",
        evidence_id: str = "",
        focal_actor_context_id: str = "",
    ) -> dict[str, Any]:
        """Build a Reality Snapshot (R-Graph) for a domain. Returns snapshot_id, nodes, edges."""
        from cmis_v2.engines.world import build_snapshot

        return self._safe_call(
            "build_snapshot",
            build_snapshot,
            {
                "domain_id": domain_id,
                "region": region,
                "evidence_id": evidence_id,
                "focal_actor_context_id": focal_actor_context_id,
                "project_id": self.project_id or "",
            },
        )

    def add_node(
        self,
        snapshot_id: str,
        node_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a node (actor/money_flow/state) to a snapshot. data must include traits dict."""
        from cmis_v2.engines.world import add_node

        return self._safe_call(
            "add_node",
            add_node,
            {"snapshot_id": snapshot_id, "node_type": node_type, "data": data, "project_id": self.project_id or ""},
        )

    def add_edge(
        self,
        snapshot_id: str,
        edge_type: str,
        source: str,
        target: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add an edge between two nodes in a snapshot."""
        from cmis_v2.engines.world import add_edge

        return self._safe_call(
            "add_edge",
            add_edge,
            {"snapshot_id": snapshot_id, "edge_type": edge_type, "source": source, "target": target, "data": data, "project_id": self.project_id or ""},
        )

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Retrieve a snapshot by ID."""
        from cmis_v2.engines.world import get_snapshot

        return self._safe_call("get_snapshot", get_snapshot, {"snapshot_id": snapshot_id, "project_id": self.project_id or ""})

    # ------------------------------------------------------------------
    # Pattern engine wrappers
    # ------------------------------------------------------------------

    def match_patterns(
        self,
        snapshot_id: str,
        top_n: int = 5,
    ) -> dict[str, Any]:
        """Match business patterns against a Reality Snapshot. Use after building an R-Graph."""
        from cmis_v2.engines.pattern import match_patterns

        return self._safe_call(
            "match_patterns",
            match_patterns,
            {"snapshot_id": snapshot_id, "top_n": top_n},
        )

    def discover_gaps(self, snapshot_id: str) -> dict[str, Any]:
        """Find partially matching patterns as potential opportunities."""
        from cmis_v2.engines.pattern import discover_gaps

        return self._safe_call("discover_gaps", discover_gaps, {"snapshot_id": snapshot_id})

    # ------------------------------------------------------------------
    # Value engine wrappers
    # ------------------------------------------------------------------

    def evaluate_metrics(
        self,
        metric_ids: list[str],
        context: dict[str, Any] | None = None,
        snapshot_id: str = "",
        evidence_id: str = "",
        policy_ref: str = "decision_balanced",
    ) -> dict[str, Any]:
        """Create metric evaluation structures. LM fills values via set_metric_value()."""
        from cmis_v2.engines.value import evaluate_metrics

        return self._safe_call(
            "evaluate_metrics",
            evaluate_metrics,
            {
                "metric_ids": metric_ids,
                "context": context,
                "snapshot_id": snapshot_id,
                "evidence_id": evidence_id,
                "policy_ref": policy_ref,
                "project_id": self.project_id or "",
            },
        )

    def set_metric_value(
        self,
        metric_id: str,
        point_estimate: float,
        confidence: float = 0.5,
        method: str = "unknown",
        evidence_summary: str = "",
        evidence_id: str = "",
        force_unverified: bool = False,
    ) -> dict[str, Any]:
        """Set a metric's estimated value after analysis."""
        from cmis_v2.engines.value import set_metric_value

        return self._safe_call(
            "set_metric_value",
            set_metric_value,
            {
                "metric_id": metric_id,
                "point_estimate": point_estimate,
                "confidence": confidence,
                "method": method,
                "evidence_summary": evidence_summary,
                "evidence_id": evidence_id,
                "force_unverified": force_unverified,
                "project_id": self.project_id or "",
            },
        )

    def get_metric_value(self, metric_id: str) -> dict[str, Any]:
        """Retrieve a metric value record by metric ID."""
        from cmis_v2.engines.value import get_metric_value

        return self._safe_call("get_metric_value", get_metric_value, {"metric_id": metric_id, "project_id": self.project_id or ""})

    # ------------------------------------------------------------------
    # Strategy engine wrappers
    # ------------------------------------------------------------------

    def search_strategies(
        self,
        goal_description: str,
        snapshot_id: str = "",
        pattern_matches: list[dict[str, Any]] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Search for strategy candidates based on market analysis results."""
        from cmis_v2.engines.strategy import search_strategies

        return self._safe_call(
            "search_strategies",
            search_strategies,
            {
                "goal_description": goal_description,
                "snapshot_id": snapshot_id,
                "pattern_matches": pattern_matches,
                "constraints": constraints,
                "project_id": self.project_id or "",
            },
        )

    def set_strategy_impact(
        self,
        strategy_id: str,
        revenue_change: str,
        market_share_change: str,
        evidence_id: str,
        rationale: str = "",
    ) -> dict[str, Any]:
        """Set expected impact for a strategy, linked to evidence."""
        from cmis_v2.engines.strategy import set_strategy_impact

        return self._safe_call(
            "set_strategy_impact",
            set_strategy_impact,
            {
                "strategy_id": strategy_id,
                "revenue_change": revenue_change,
                "market_share_change": market_share_change,
                "evidence_id": evidence_id,
                "rationale": rationale,
                "project_id": self.project_id or "",
            },
        )

    def evaluate_portfolio(
        self,
        strategy_ids: list[str],
        value_records: list[dict[str, Any]] | None = None,
        policy_ref: str = "decision_balanced",
        pending_policy: str = "exclude",
    ) -> dict[str, Any]:
        """Evaluate and rank a portfolio of strategy candidates."""
        from cmis_v2.engines.strategy import evaluate_portfolio

        return self._safe_call(
            "evaluate_portfolio",
            evaluate_portfolio,
            {
                "strategy_ids": strategy_ids,
                "value_records": value_records,
                "policy_ref": policy_ref,
                "pending_policy": pending_policy,
                "project_id": self.project_id or "",
            },
        )

    # ------------------------------------------------------------------
    # Policy engine wrappers
    # ------------------------------------------------------------------

    def load_policy(self, policy_id: str = "decision_balanced") -> dict[str, Any]:
        """Load compiled policy configuration."""
        from cmis_v2.engines.policy import load_policy

        return self._safe_call("load_policy", load_policy, {"policy_id": policy_id})

    def check_evidence_gate(
        self,
        evidence_result: dict[str, Any],
        policy_id: str = "decision_balanced",
    ) -> dict[str, Any]:
        """Check if evidence meets policy requirements."""
        from cmis_v2.engines.policy import check_evidence_gate

        return self._safe_call(
            "check_evidence_gate",
            check_evidence_gate,
            {"evidence_result": evidence_result, "policy_id": policy_id},
        )

    def check_value_gate(
        self,
        value_records: list[dict[str, Any]],
        policy_id: str = "decision_balanced",
    ) -> dict[str, Any]:
        """Check if metric values meet policy quality requirements."""
        from cmis_v2.engines.policy import check_value_gate

        return self._safe_call(
            "check_value_gate",
            check_value_gate,
            {"value_records": value_records, "policy_id": policy_id},
        )

    def check_all_gates(
        self,
        evidence_result: dict[str, Any] | None = None,
        value_records: list[dict[str, Any]] | None = None,
        policy_id: str = "decision_balanced",
    ) -> dict[str, Any]:
        """Run all applicable policy gates and return aggregate result."""
        from cmis_v2.engines.policy import check_all_gates

        return self._safe_call(
            "check_all_gates",
            check_all_gates,
            {
                "evidence_result": evidence_result,
                "value_records": value_records,
                "policy_id": policy_id,
            },
        )

    # ------------------------------------------------------------------
    # Project management wrappers
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        description: str,
        domain_id: str,
        region: str = "KR",
    ) -> dict[str, Any]:
        """Create a new CMIS project. Returns manifest with project_id, current_state."""
        from cmis_v2.project import create_project

        return self._safe_call(
            "create_project",
            create_project,
            {"name": name, "description": description, "domain_id": domain_id, "region": region},
        )

    def load_project(self, project_id: str) -> dict[str, Any]:
        """Load and return the manifest for a project."""
        from cmis_v2.project import load_project

        return self._safe_call("load_project", load_project, {"project_id": project_id})

    def get_current_state(self, project_id: str) -> Any:
        """Return the current state string for a project."""
        from cmis_v2.project import get_current_state

        try:
            result = get_current_state(project_id)
            self._log("get_current_state", {"project_id": project_id}, {})
            return result
        except Exception as exc:
            err: dict[str, Any] = {"error": str(exc)}
            self._log("get_current_state", {"project_id": project_id}, err)
            return err

    def transition(
        self,
        project_id: str,
        trigger: str,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a state transition on a project. Returns updated manifest."""
        from cmis_v2.project import transition

        return self._safe_call(
            "transition",
            transition,
            {"project_id": project_id, "trigger": trigger, "actor": actor, "payload": payload},
        )

    def lock_scope(
        self,
        project_id: str,
        scope_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Store scope data in the project manifest after scope_locked state."""
        from cmis_v2.project import lock_scope

        return self._safe_call(
            "lock_scope",
            lock_scope,
            {"project_id": project_id, "scope_data": scope_data},
        )

    def add_run(
        self,
        project_id: str,
        run_id: str,
        query: str,
        workflow_hint: str,
    ) -> dict[str, Any]:
        """Register a new run under a project."""
        from cmis_v2.project import add_run

        return self._safe_call(
            "add_run",
            add_run,
            {"project_id": project_id, "run_id": run_id, "query": query, "workflow_hint": workflow_hint},
        )

    def save_deliverable(
        self,
        project_id: str,
        filename: str,
        content: str,
    ) -> Any:
        """Write content to the project's deliverables directory."""
        from cmis_v2.project import save_deliverable

        try:
            result = save_deliverable(project_id, filename, content)
            self._log("save_deliverable", {"project_id": project_id, "filename": filename}, {})
            return result
        except Exception as exc:
            err: dict[str, Any] = {"error": str(exc)}
            self._log("save_deliverable", {"project_id": project_id, "filename": filename}, err)
            return err

    def list_projects(self) -> list[dict[str, Any]]:
        """Return a list of all project manifests."""
        from cmis_v2.project import list_projects

        try:
            result = list_projects()
            self._log("list_projects", {}, {})
            return result
        except Exception as exc:
            self._log("list_projects", {}, {"error": str(exc)})
            return []

    def get_project_summary(self, project_id: str) -> dict[str, Any]:
        """Return a compact project summary: state, run count, event count."""
        from cmis_v2.project import get_project_summary

        return self._safe_call(
            "get_project_summary",
            get_project_summary,
            {"project_id": project_id},
        )

    def get_project_events(self, project_id: str) -> Any:
        """Return the full event list for a project."""
        from cmis_v2.project import get_project_events

        try:
            result = get_project_events(project_id)
            self._log("get_project_events", {"project_id": project_id}, {})
            return result
        except Exception as exc:
            err: dict[str, Any] = {"error": str(exc)}
            self._log("get_project_events", {"project_id": project_id}, err)
            return err

    # ------------------------------------------------------------------
    # Estimation engine wrappers (new)
    # ------------------------------------------------------------------

    def create_estimate(
        self,
        variable_name: str,
        lo: float,
        hi: float,
        method: str = "unknown",
        source: str = "",
        source_reliability: float = 0.5,
        evidence_id: str = "",
    ) -> dict[str, Any]:
        """Create an estimation for a variable (metric or free variable)."""
        from cmis_v2.engines.estimation import create_estimate

        return self._safe_call(
            "create_estimate",
            create_estimate,
            {
                "variable_name": variable_name,
                "lo": lo, "hi": hi,
                "method": method, "source": source,
                "source_reliability": source_reliability,
                "evidence_id": evidence_id,
                "project_id": self.project_id or "",
            },
        )

    def get_estimate(self, variable_name: str) -> dict[str, Any]:
        """Get the current estimation state for a variable."""
        from cmis_v2.engines.estimation import get_estimate

        return self._safe_call("get_estimate", get_estimate, {"variable_name": variable_name, "project_id": self.project_id or ""})

    def update_estimate(
        self,
        variable_name: str,
        lo: float,
        hi: float,
        method: str = "unknown",
        source: str = "",
        source_reliability: float = 0.5,
        evidence_id: str = "",
    ) -> dict[str, Any]:
        """Add new evidence-based estimate and re-fuse."""
        from cmis_v2.engines.estimation import update_estimate

        return self._safe_call(
            "update_estimate",
            update_estimate,
            {
                "variable_name": variable_name,
                "lo": lo, "hi": hi,
                "method": method, "source": source,
                "source_reliability": source_reliability,
                "evidence_id": evidence_id,
                "project_id": self.project_id or "",
            },
        )

    def list_estimates(self) -> dict[str, Any]:
        """List all current estimations."""
        from cmis_v2.engines.estimation import list_estimates

        return self._safe_call("list_estimates", list_estimates, {"project_id": self.project_id or ""})

    def create_fermi_tree(
        self,
        target_variable: str,
        operation: str = "multiply",
    ) -> dict[str, Any]:
        """Create a Fermi decomposition tree."""
        from cmis_v2.engines.estimation import create_fermi_tree

        return self._safe_call(
            "create_fermi_tree",
            create_fermi_tree,
            {"target_variable": target_variable, "operation": operation, "project_id": self.project_id or ""},
        )

    def add_fermi_leaf(
        self,
        tree_id: str,
        variable: str,
        lo: float,
        hi: float,
        source: str = "",
        evidence_id: str = "",
    ) -> dict[str, Any]:
        """Add a leaf node to a Fermi tree."""
        from cmis_v2.engines.estimation import add_fermi_leaf

        return self._safe_call(
            "add_fermi_leaf",
            add_fermi_leaf,
            {"tree_id": tree_id, "variable": variable, "lo": lo, "hi": hi, "source": source, "evidence_id": evidence_id, "project_id": self.project_id or ""},
        )

    def add_fermi_subtree(
        self,
        parent_tree_id: str,
        variable: str,
        operation: str = "multiply",
    ) -> dict[str, Any]:
        """Add a subtree node to a Fermi tree."""
        from cmis_v2.engines.estimation import add_fermi_subtree

        return self._safe_call(
            "add_fermi_subtree",
            add_fermi_subtree,
            {"parent_tree_id": parent_tree_id, "variable": variable, "operation": operation, "project_id": self.project_id or ""},
        )

    def evaluate_fermi_tree(self, tree_id: str) -> dict[str, Any]:
        """Evaluate a Fermi tree using interval arithmetic."""
        from cmis_v2.engines.estimation import evaluate_fermi_tree

        return self._safe_call("evaluate_fermi_tree", evaluate_fermi_tree, {"tree_id": tree_id, "project_id": self.project_id or ""})

    # ------------------------------------------------------------------
    # Belief engine wrappers (DEPRECATED → Estimation Engine)
    # ------------------------------------------------------------------

    def set_prior(
        self,
        metric_id: str,
        point_estimate: float,
        confidence: float = 0.3,
        source: str = "expert_guess",
        distribution: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """[DEPRECATED → create_estimate] Set a prior belief for a metric."""
        from cmis_v2.engines.belief import set_prior

        return self._safe_call(
            "set_prior",
            set_prior,
            {
                "metric_id": metric_id,
                "point_estimate": point_estimate,
                "confidence": confidence,
                "source": source,
                "distribution": distribution,
                "project_id": self.project_id or "",
            },
        )

    def get_prior(self, metric_id: str) -> dict[str, Any]:
        """[DEPRECATED → get_estimate] Get the current prior belief."""
        from cmis_v2.engines.belief import get_prior

        return self._safe_call("get_prior", get_prior, {"metric_id": metric_id, "project_id": self.project_id or ""})

    def update_belief(
        self,
        metric_id: str,
        new_evidence_value: float,
        evidence_confidence: float = 0.5,
    ) -> dict[str, Any]:
        """[DEPRECATED → update_estimate] Update belief with new evidence."""
        from cmis_v2.engines.belief import update_belief

        return self._safe_call(
            "update_belief",
            update_belief,
            {
                "metric_id": metric_id,
                "new_evidence_value": new_evidence_value,
                "evidence_confidence": evidence_confidence,
                "project_id": self.project_id or "",
            },
        )

    def list_beliefs(self) -> dict[str, Any]:
        """[DEPRECATED → list_estimates] List all current beliefs."""
        from cmis_v2.engines.belief import list_beliefs

        return self._safe_call("list_beliefs", list_beliefs, {})

    # ------------------------------------------------------------------
    # Learning engine wrappers
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        metric_id: str,
        actual_value: float,
        measured_at: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """Record an actual outcome for a metric."""
        from cmis_v2.engines.learning import record_outcome

        return self._safe_call(
            "record_outcome",
            record_outcome,
            {
                "metric_id": metric_id,
                "actual_value": actual_value,
                "measured_at": measured_at,
                "source": source,
                "project_id": self.project_id or "",
            },
        )

    def get_learning_summary(self) -> dict[str, Any]:
        """Get summary of all recorded outcomes and prediction accuracy."""
        from cmis_v2.engines.learning import get_learning_summary

        return self._safe_call("get_learning_summary", get_learning_summary, {"project_id": self.project_id or ""})

    def apply_learnings(self, metric_id: str) -> dict[str, Any]:
        """Apply accumulated learnings to update belief for a metric."""
        from cmis_v2.engines.learning import apply_learnings

        return self._safe_call("apply_learnings", apply_learnings, {"metric_id": metric_id, "project_id": self.project_id or ""})

    # ------------------------------------------------------------------
    # Ontology migration wrappers
    # ------------------------------------------------------------------

    def check_compatibility(self, project_id: str) -> dict[str, Any]:
        """Check if a project's ontology version is compatible with current."""
        from cmis_v2.ontology_migration import check_compatibility

        return self._safe_call("check_compatibility", check_compatibility, {"project_id": project_id})

    def create_migration_map(
        self,
        from_version: str,
        to_version: str,
        renames: dict[str, str] | None = None,
        removals: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a migration map for ontology version changes."""
        from cmis_v2.ontology_migration import create_migration_map

        return self._safe_call(
            "create_migration_map",
            create_migration_map,
            {
                "from_version": from_version,
                "to_version": to_version,
                "renames": renames,
                "removals": removals,
            },
        )

    def migrate_project(self, project_id: str, migration_map_path: str = "") -> dict[str, Any]:
        """Apply migration to a project's data."""
        from cmis_v2.ontology_migration import migrate_project

        return self._safe_call(
            "migrate_project",
            migrate_project,
            {"project_id": project_id, "migration_map_path": migration_map_path},
        )

    # ------------------------------------------------------------------
    # RLM export
    # ------------------------------------------------------------------

    def as_rlm_tools(self) -> dict[str, dict[str, Any]]:
        """Return all tools in RLM custom_tools format.

        Format: ``{"tool_name": {"tool": callable, "description": str}}``
        """
        tools: dict[str, dict[str, Any]] = {
            # --- Evidence engine ---
            "collect_evidence": {
                "tool": self.collect_evidence,
                "description": (
                    "Collect evidence for a given query. "
                    "Args: query (str, required) - search query e.g. '한국 전기차 충전 인프라 시장 규모'; "
                    "domain_id (str) - domain identifier e.g. 'EV_Charging_KR'; "
                    "region (str, default 'KR'); "
                    "metric_ids (list[str] | None) - specific metric IDs to collect for e.g. ['MET-TAM', 'MET-Revenue']; "
                    "sources (list[str] | None) - data sources to query e.g. ['web_search', 'kosis', 'dart']. "
                    "None means auto-select (defaults to web_search). "
                    "Returns: dict with evidence_id, query, records, sufficiency, lineage. "
                    "Use at the start of data_collection to create an evidence container."
                ),
            },
            "add_record": {
                "tool": self.add_record,
                "description": (
                    "Add an evidence record to an existing evidence collection. "
                    "Args: evidence_id (str, required) - from collect_evidence; "
                    "source_tier (str, required) - one of 'official', 'curated', 'commercial'; "
                    "source_name (str, required) - human-readable source name e.g. 'KOSIS 통계'; "
                    "content (str, required) - the evidence content/summary; "
                    "confidence (float, default 0.5) - evidence_confidence: 0.0 to 1.0, "
                    "how reliable this source is (1.0 = official verified data); "
                    "metric_ids_covered (list[str] | None) - which metrics this record covers. "
                    "Returns: the new record dict with record_id. "
                    "Use after collect_evidence to populate evidence."
                ),
            },
            "get_evidence": {
                "tool": self.get_evidence,
                "description": (
                    "Retrieve an evidence collection by ID. "
                    "Args: evidence_id (str, required). "
                    "Returns: dict with evidence_id, records, sufficiency. "
                    "Use to check evidence completeness before proceeding."
                ),
            },
            # --- World engine ---
            "build_snapshot": {
                "tool": self.build_snapshot,
                "description": (
                    "Build a Reality Snapshot (R-Graph) for a domain. "
                    "Args: domain_id (str, required) - e.g. 'EV_Charging_KR'; "
                    "region (str, default 'KR'); "
                    "evidence_id (str) - evidence collection this snapshot is based on; "
                    "focal_actor_context_id (str) - optional focal actor. "
                    "Returns: dict with snapshot_id, nodes (empty), edges (empty), summary, lineage. "
                    "Use after evidence collection to create the R-Graph container, then populate with add_node/add_edge."
                ),
            },
            "add_node": {
                "tool": self.add_node,
                "description": (
                    "Add a node to an existing R-Graph snapshot. "
                    "Args: snapshot_id (str, required); "
                    "node_type (str, required) - one of 'actor', 'money_flow', 'state'; "
                    "data (dict, required) - must include 'traits' key e.g. "
                    "{'name': 'Tesla', 'traits': {'kind': 'company', 'market_position': 'leader'}}. "
                    "Returns: the new node dict with id, type, data. "
                    "Use after build_snapshot to add market actors, money flows, and states."
                ),
            },
            "add_edge": {
                "tool": self.add_edge,
                "description": (
                    "Add an edge between two nodes in a snapshot. "
                    "Args: snapshot_id (str, required); "
                    "edge_type (str, required) - one of 'actor_pays_actor', 'actor_competes_with', "
                    "'actor_serves_actor', 'actor_supplies_actor', 'actor_regulates_actor', 'money_flow_connects'; "
                    "source (str, required) - source node ID; "
                    "target (str, required) - target node ID; "
                    "data (dict | None) - optional edge properties. "
                    "Returns: the new edge dict. "
                    "Use after adding nodes to define relationships."
                ),
            },
            "get_snapshot": {
                "tool": self.get_snapshot,
                "description": (
                    "Retrieve a snapshot by ID. "
                    "Args: snapshot_id (str, required). "
                    "Returns: full snapshot dict with nodes, edges, summary. "
                    "Use to inspect the current R-Graph state."
                ),
            },
            # --- Pattern engine ---
            "match_patterns": {
                "tool": self.match_patterns,
                "description": (
                    "Match 23 business patterns against a Reality Snapshot. "
                    "Args: snapshot_id (str, required); top_n (int, default 5) - max matches to return. "
                    "Returns: dict with matches (pattern_id, fit_score, matched/missing_traits), "
                    "total_patterns_evaluated. "
                    "Use after building an R-Graph and before opportunity discovery."
                ),
            },
            "discover_gaps": {
                "tool": self.discover_gaps,
                "description": (
                    "Find partially matching patterns (0.3 <= fit_score < 0.7) as potential opportunities. "
                    "Args: snapshot_id (str, required). "
                    "Returns: dict with gaps (pattern_id, fit_score, present/missing_traits, opportunity_description). "
                    "Use during opportunity_discovery phase."
                ),
            },
            # --- Value engine ---
            "evaluate_metrics": {
                "tool": self.evaluate_metrics,
                "description": (
                    "Create metric evaluation structures for specified metrics. "
                    "Args: metric_ids (list[str], required) - e.g. ['MET-TAM', 'MET-Revenue', 'MET-ARPU']; "
                    "context (dict | None) - additional context; "
                    "snapshot_id (str) - for graph-based evaluation; "
                    "evidence_id (str) - for evidence-based evaluation; "
                    "policy_ref (str, default 'decision_balanced'). "
                    "Returns: dict with value_records (metric_id, point_estimate=None, value_confidence, method). "
                    "Use to initialise metrics, then fill values with set_metric_value."
                ),
            },
            "set_metric_value": {
                "tool": self.set_metric_value,
                "description": (
                    "Set a metric's estimated value after analysis. "
                    "Args: metric_id (str, required) - e.g. 'MET-TAM'; "
                    "point_estimate (float, required) - the estimated value; "
                    "confidence (float, default 0.5) - value_confidence: 0.0 to 1.0, "
                    "how confident you are in this metric estimate (1.0 = highly certain); "
                    "method (str, default 'unknown') - one of 'top_down', 'bottom_up', 'fermi', 'proxy', 'unknown'; "
                    "evidence_summary (str) - summary of supporting evidence; "
                    "evidence_id (str, required) - ID of evidence record supporting this estimate; "
                    "force_unverified (bool, default False) - set True to bypass evidence_id requirement "
                    "(quality.status will be 'force_unverified'). "
                    "Returns: the updated value record. "
                    "Use after evaluate_metrics to fill in estimated values."
                ),
            },
            "get_metric_value": {
                "tool": self.get_metric_value,
                "description": (
                    "Retrieve a metric value record by metric ID. "
                    "Args: metric_id (str, required) - e.g. 'MET-TAM'. "
                    "Returns: the value record with point_estimate, value_confidence, method, quality. "
                    "Use to check current metric values."
                ),
            },
            # --- Strategy engine ---
            "search_strategies": {
                "tool": self.search_strategies,
                "description": (
                    "Search for strategy candidates based on market analysis results. "
                    "Args: goal_description (str, required) - what the strategy should achieve; "
                    "snapshot_id (str) - reality snapshot reference; "
                    "pattern_matches (list[dict] | None) - results from match_patterns(); "
                    "constraints (dict | None) - business constraints e.g. {'budget': 'limited', 'timeline': 'short'}. "
                    "Returns: dict with strategy_search_id, goal, candidates "
                    "(strategy_id, name, feasibility_score, risk_factors=[{category, severity, score, description}], risk_score). "
                    "risk categories: capability_gap, market_risk, integration_complexity, resource_constraint, competitive_response, execution_risk. "
                    "Use after pattern matching to generate strategy options."
                ),
            },
            "set_strategy_impact": {
                "tool": self.set_strategy_impact,
                "description": (
                    "Set expected impact for a strategy, linked to evidence. "
                    "Args: strategy_id (str, required) - from search_strategies; "
                    "revenue_change (str, required) - e.g. '+15%', '-5%'; "
                    "market_share_change (str, required) - e.g. '+8%'; "
                    "evidence_id (str, required) - evidence record supporting this estimate; "
                    "rationale (str) - explanation of how evidence supports estimate. "
                    "Returns: updated strategy dict with evidence_linked impact. "
                    "Use after search_strategies to set evidence-backed impact estimates."
                ),
            },
            "evaluate_portfolio": {
                "tool": self.evaluate_portfolio,
                "description": (
                    "Evaluate and rank a portfolio of strategy candidates. "
                    "Args: strategy_ids (list[str], required) - strategy IDs from search_strategies; "
                    "value_records (list[dict] | None) - metric values for context; "
                    "policy_ref (str, default 'decision_balanced'); "
                    "pending_policy (str, default 'exclude') - how to handle pending_evidence items: "
                    "'exclude' (skip, is_complete=False), 'fail' (error if any pending), "
                    "'partial' (separate into pending_items). "
                    "Returns: dict with portfolio_id, ranked_strategies (overall_score, recommendation), "
                    "trade_offs, is_complete, pending_items. "
                    "Use after search_strategies to compare and rank options."
                ),
            },
            # --- Policy engine ---
            "load_policy": {
                "tool": self.load_policy,
                "description": (
                    "Load compiled policy configuration. "
                    "Args: policy_id (str, default 'decision_balanced') - one of "
                    "'reporting_strict', 'decision_balanced', 'exploration_friendly'. "
                    "Returns: dict with policy_id, profiles (evidence, value, prior, convergence, orchestration), gates. "
                    "Use to inspect policy settings before or during analysis."
                ),
            },
            "check_evidence_gate": {
                "tool": self.check_evidence_gate,
                "description": (
                    "Check if evidence meets policy requirements. "
                    "Args: evidence_result (dict, required) - output from collect_evidence(); "
                    "policy_id (str, default 'decision_balanced'). "
                    "Returns: dict with passed (bool), gates_checked, gates_passed, violations. "
                    "Use to validate evidence quality before proceeding to analysis."
                ),
            },
            "check_value_gate": {
                "tool": self.check_value_gate,
                "description": (
                    "Check if metric values meet policy quality requirements. "
                    "Args: value_records (list[dict], required) - from evaluate_metrics(); "
                    "policy_id (str, default 'decision_balanced'). "
                    "Returns: dict with passed (bool), gates_checked, gates_passed, violations. "
                    "Use to validate metric quality before synthesis."
                ),
            },
            "check_all_gates": {
                "tool": self.check_all_gates,
                "description": (
                    "Run all applicable policy gates and return aggregate result. "
                    "Args: evidence_result (dict | None) - from collect_evidence(); "
                    "value_records (list[dict] | None) - from evaluate_metrics(); "
                    "policy_id (str, default 'decision_balanced'). "
                    "Returns: dict with overall_passed, evidence_gate, value_gate, summary, suggested_actions. "
                    "Use as a comprehensive quality check before delivering results."
                ),
            },
            # --- Estimation engine (NEW — replaces Belief engine) ---
            "create_estimate": {
                "tool": self.create_estimate,
                "description": (
                    "Create an estimation for any variable (metric or free variable). "
                    "Uses P10/P90 interval: lo = 10% chance true value is below, hi = 10% chance above. "
                    "Args: variable_name (str, required) - metric ID (e.g. 'MET-TAM') or free name (e.g. 'korean_household_count'); "
                    "lo (float, required) - P10 lower bound; "
                    "hi (float, required) - P90 upper bound; "
                    "method (str, default 'unknown') - 'fermi', 'top_down', 'bottom_up', 'proxy', 'expert_guess'; "
                    "source (str) - human-readable source; "
                    "source_reliability (float, default 0.5) - 0.0 to 1.0, data source quality; "
                    "evidence_id (str) - evidence record supporting this estimate. "
                    "Returns: estimate dict with estimate_id, interval {lo, hi, midpoint}, point_estimate. "
                    "Use to register any numerical estimation."
                ),
            },
            "get_estimate": {
                "tool": self.get_estimate,
                "description": (
                    "Get all estimations for a variable (includes all methods + fused result). "
                    "Args: variable_name (str, required). "
                    "Returns: dict with estimates list, fused result (if multiple), version."
                ),
            },
            "update_estimate": {
                "tool": self.update_estimate,
                "description": (
                    "Add a new evidence-based estimate and auto-fuse with existing estimates. "
                    "Same args as create_estimate. Multiple estimates for the same variable are "
                    "fused in batch (order-independent) using source_reliability as weight. "
                    "Returns: the new estimate dict."
                ),
            },
            "list_estimates": {
                "tool": self.list_estimates,
                "description": (
                    "List all current estimations. No args required. "
                    "Returns: dict with total count and list of all estimation states."
                ),
            },
            "create_fermi_tree": {
                "tool": self.create_fermi_tree,
                "description": (
                    "Create a Fermi decomposition tree for estimating an unknown number. "
                    "Args: target_variable (str, required) - what to estimate (e.g. 'MET-TAM', 'pet_food_market'); "
                    "operation (str, default 'multiply') - root operation: 'multiply', 'add', 'divide', 'subtract'. "
                    "Returns: dict with tree_id. Add leaves with add_fermi_leaf, then evaluate with evaluate_fermi_tree."
                ),
            },
            "add_fermi_leaf": {
                "tool": self.add_fermi_leaf,
                "description": (
                    "Add a leaf (concrete P10/P90 range) to a Fermi tree. "
                    "Args: tree_id (str, required) - from create_fermi_tree; "
                    "variable (str, required) - component name (e.g. 'korean_household_count'); "
                    "lo (float, required) - P10 lower bound; "
                    "hi (float, required) - P90 upper bound; "
                    "source (str) - where this value comes from; "
                    "evidence_id (str) - evidence record ID (if absent, marked as 'unverified_leaf'). "
                    "Returns: the new leaf node dict."
                ),
            },
            "add_fermi_subtree": {
                "tool": self.add_fermi_subtree,
                "description": (
                    "Add a sub-operation node to a Fermi tree (for nested decomposition). "
                    "Args: parent_tree_id (str, required); "
                    "variable (str, required) - what this subtree computes; "
                    "operation (str, default 'multiply'). "
                    "Returns: dict with subtree_id. Add leaves to this subtree_id."
                ),
            },
            "evaluate_fermi_tree": {
                "tool": self.evaluate_fermi_tree,
                "description": (
                    "Evaluate a Fermi tree using interval arithmetic. "
                    "All leaves must be populated. "
                    "Args: tree_id (str, required). "
                    "Returns: dict with result interval {lo, hi, midpoint}, point_estimate, "
                    "spread_ratio, unverified_leaves count."
                ),
            },
            # --- Belief engine (DEPRECATED → use Estimation engine above) ---
            "set_prior": {
                "tool": self.set_prior,
                "description": (
                    "[DEPRECATED — use create_estimate instead] "
                    "Set a prior belief for a metric. "
                    "Args: metric_id (str), point_estimate (float), confidence (float, default 0.3), "
                    "source (str, default 'expert_guess'). "
                    "Returns: belief dict. Internally delegates to create_estimate()."
                ),
            },
            "get_prior": {
                "tool": self.get_prior,
                "description": (
                    "[DEPRECATED — use get_estimate instead] "
                    "Get the current prior belief for a metric. "
                    "Args: metric_id (str). Returns: belief dict."
                ),
            },
            "update_belief": {
                "tool": self.update_belief,
                "description": (
                    "[DEPRECATED — use update_estimate instead] "
                    "Update belief with new evidence. "
                    "Args: metric_id (str), new_evidence_value (float), evidence_confidence (float). "
                    "Returns: belief dict. Internally delegates to update_estimate()."
                ),
            },
            "list_beliefs": {
                "tool": self.list_beliefs,
                "description": (
                    "[DEPRECATED — use list_estimates instead] "
                    "List all current beliefs. Returns: belief list."
                ),
            },
            # --- Learning engine ---
            "record_outcome": {
                "tool": self.record_outcome,
                "description": (
                    "Record an actual outcome for a metric and compare against prediction. "
                    "Args: metric_id (str, required); "
                    "actual_value (float, required) - the actual observed value; "
                    "measured_at (str) - ISO timestamp; "
                    "source (str) - where outcome was observed. "
                    "Returns: outcome dict with comparison (predicted_value, error, accuracy_rating). "
                    "Use during reality_monitoring to track prediction accuracy."
                ),
            },
            "get_learning_summary": {
                "tool": self.get_learning_summary,
                "description": (
                    "Get summary of all recorded outcomes and prediction accuracy. "
                    "No args required. "
                    "Returns: dict with total_outcomes, accuracy breakdown, metrics_tracked, suggestions. "
                    "Use to understand system prediction quality."
                ),
            },
            "apply_learnings": {
                "tool": self.apply_learnings,
                "description": (
                    "Apply accumulated learnings to update belief for a metric. "
                    "Args: metric_id (str, required). "
                    "Returns: updated belief or info message if no outcomes exist. "
                    "Use to improve future predictions based on past performance."
                ),
            },
            # --- Ontology migration ---
            "check_compatibility": {
                "tool": self.check_compatibility,
                "description": (
                    "Check if a project's ontology version is compatible with current. "
                    "Args: project_id (str, required). "
                    "Returns: dict with compatible (bool), project_version, current_version, breaking_changes. "
                    "Use to verify project data is compatible before analysis."
                ),
            },
            "create_migration_map": {
                "tool": self.create_migration_map,
                "description": (
                    "Create a migration map for ontology version changes. "
                    "Args: from_version (str, required) - e.g. '1.0.0'; "
                    "to_version (str, required) - e.g. '1.1.0'; "
                    "renames (dict | None) - mapping of old IDs to new IDs; "
                    "removals (list | None) - list of removed IDs. "
                    "Returns: dict with path, from_version, to_version, renames, removals. "
                    "Use when ontology has breaking changes that need a migration path."
                ),
            },
            "migrate_project": {
                "tool": self.migrate_project,
                "description": (
                    "Apply migration to a project's data. "
                    "Args: project_id (str, required); "
                    "migration_map_path (str) - path to migration YAML (auto-detect if empty). "
                    "Returns: dict with migration result details including changes_applied. "
                    "Use to update a project to the current ontology version."
                ),
            },
            # --- Project management ---
            "create_project": {
                "tool": self.create_project,
                "description": (
                    "Create a new CMIS analysis project. "
                    "Args: name (str, required); description (str, required); "
                    "domain_id (str, required) - e.g. 'EV_Charging_KR'; "
                    "region (str, default 'KR'). "
                    "Returns: manifest dict with project_id, current_state='requested'. "
                    "Use at the very start of a new analysis."
                ),
            },
            "load_project": {
                "tool": self.load_project,
                "description": (
                    "Load and return the manifest for a project. "
                    "Args: project_id (str, required). "
                    "Returns: manifest dict or error."
                ),
            },
            "get_current_state": {
                "tool": self.get_current_state,
                "description": (
                    "Return the current state string for a project. "
                    "Args: project_id (str, required). "
                    "Returns: state string e.g. 'discovery', 'scope_review'."
                ),
            },
            "transition": {
                "tool": self.transition,
                "description": (
                    "Execute a state transition on a project. "
                    "Args: project_id (str, required); "
                    "trigger (str, required) - e.g. 'project_created', 'discovery_completed', 'scope_approved'; "
                    "actor (str, required) - 'system', 'rlm', or 'user'; "
                    "payload (dict | None) - optional context. "
                    "Returns: updated manifest or error. "
                    "Use to advance the project through its lifecycle."
                ),
            },
            "lock_scope": {
                "tool": self.lock_scope,
                "description": (
                    "Store scope data in the project manifest. "
                    "Args: project_id (str, required); "
                    "scope_data (dict, required) - scope definition e.g. "
                    "{'target_market': '...', 'boundaries': '...', 'key_questions': [...]}. "
                    "Returns: updated manifest. "
                    "Use after project reaches scope_locked state."
                ),
            },
            "add_run": {
                "tool": self.add_run,
                "description": (
                    "Register a new run under a project. "
                    "Args: project_id (str, required); run_id (str, required); "
                    "query (str, required); workflow_hint (str, required) - one of "
                    "'structure_analysis', 'opportunity_discovery', 'strategy_design', 'reality_monitoring'. "
                    "Returns: updated manifest."
                ),
            },
            "save_deliverable": {
                "tool": self.save_deliverable,
                "description": (
                    "Write content to the project's deliverables directory. "
                    "Args: project_id (str, required); "
                    "filename (str, required) - e.g. 'market_reality_report.md'; "
                    "content (str, required) - the deliverable content. "
                    "Returns: file path string. "
                    "Use at synthesis stage to save final reports."
                ),
            },
            "list_projects": {
                "tool": self.list_projects,
                "description": (
                    "Return a list of all project manifests. "
                    "No args required. "
                    "Returns: list of manifest dicts."
                ),
            },
            "get_project_summary": {
                "tool": self.get_project_summary,
                "description": (
                    "Return a compact project summary. "
                    "Args: project_id (str, required). "
                    "Returns: dict with project_id, name, current_state, run_count, event_count."
                ),
            },
            "get_project_events": {
                "tool": self.get_project_events,
                "description": (
                    "Return the full event list for a project. "
                    "Args: project_id (str, required). "
                    "Returns: list of event dicts with event_id, type, actor, payload, timestamps."
                ),
            },
        }
        return tools
