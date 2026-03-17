"""CMIS v2 project lifecycle management.

Each project lives under ``projects/{project_id}/`` and owns a
``manifest.json`` (metadata + current state) together with an ``events.db``
(audit trail managed by :mod:`cmis_v2.events`).

All public functions return plain ``dict`` objects so they can be
exposed as RLM ``custom_tools`` without serialisation gymnastics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from cmis_v2 import events as ev
from cmis_v2 import state_machine as sm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECTS_DIR: Path = Path(__file__).parent.parent / "projects"

# ---------------------------------------------------------------------------
# Trigger → supplementary event type mapping
# ---------------------------------------------------------------------------

_TRIGGER_EVENT_MAP: dict[str, ev.EventType] = {
    "project_created": "project.created",
    "discovery_completed": "discovery.completed",
    "scope_approved": "scope.approved",
    "auto": "data.collection_started",
    "scope_revised": "scope.revised",
    "scope_rejected": "scope.rejected",
    "data_quality_passed": "data.quality_passed",
    "analysis_completed": "analysis.completed",
    "finding_approved": "finding.approved",
    "finding_deepened": "finding.deepened",
    "finding_completed_early": "finding.completed_early",
    "opportunity_included": "opportunity.started",
    "opportunity_completed": "opportunity.completed",
    "opportunity_selected": "opportunity.selected",
    "opportunity_deepened": "opportunity.deepened",
    "opportunity_not_included": "opportunity.completed_early",
    "opportunity_completed_early": "opportunity.completed_early",
    "strategy_completed": "strategy.completed",
    "decision_approved": "decision.approved",
    "decision_revised": "decision.revised",
    "deliverable_saved": "deliverable.saved",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manifest_path(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "manifest.json"


def _read_manifest(project_id: str) -> dict[str, Any]:
    path = _manifest_path(project_id)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


def _write_manifest(project_id: str, manifest: dict[str, Any]) -> None:
    path = _manifest_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_project(
    name: str,
    description: str,
    domain_id: str,
    region: str = "KR",
) -> dict[str, Any]:
    """Create a new project directory, manifest, and initial events.

    Returns the newly created manifest dict.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = uuid4().hex[:6]
    project_id = f"{name}-{date_str}-{short_uuid}"

    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "deliverables").mkdir(exist_ok=True)

    now = _now_iso()
    manifest: dict[str, Any] = {
        "project_id": project_id,
        "name": name,
        "description": description,
        "domain_id": domain_id,
        "region": region,
        "current_state": "requested",
        "scope": None,
        "execution_mode": "autopilot",
        "policy_mode": "decision_balanced",
        "runs": [],
        "ontology_version": "1.0.0",
        "created_at": now,
        "updated_at": now,
    }
    _write_manifest(project_id, manifest)

    # Record the creation event
    ev.emit_event(
        project_id,
        "project.created",
        actor="system",
        payload={
            "name": name,
            "description": description,
            "domain_id": domain_id,
            "region": region,
        },
        state_before=None,
        state_after="requested",
    )

    return manifest


def load_project(project_id: str) -> dict[str, Any]:
    """Load and return the manifest for *project_id*.

    Returns ``{"error": ...}`` if the project does not exist.
    """
    path = _manifest_path(project_id)
    if not path.exists():
        return {"error": f"Project not found: {project_id}"}
    return _read_manifest(project_id)


def get_current_state(project_id: str) -> str:
    """Return the current state string for *project_id*.

    Returns ``"unknown"`` if the project does not exist.
    """
    manifest = load_project(project_id)
    return manifest.get("current_state", "unknown")


def transition(
    project_id: str,
    trigger: str,
    actor: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a state transition.

    1. Validate via :func:`state_machine.can_transition`.
    2. Update manifest.
    3. Emit ``state.transitioned`` event + trigger-specific event.
    4. Return the updated manifest.

    Returns ``{"error": ...}`` on invalid transitions.
    """
    manifest = load_project(project_id)
    if "error" in manifest:
        return manifest

    current: str = manifest["current_state"]

    # Validate
    if not sm.can_transition(current, trigger):  # type: ignore[arg-type]
        return {
            "error": (
                f"Invalid transition: state={current!r}, trigger={trigger!r}"
            )
        }

    next_st = sm.next_state(current, trigger)  # type: ignore[arg-type]

    # Update manifest
    now = _now_iso()
    manifest["current_state"] = next_st
    manifest["updated_at"] = now
    _write_manifest(project_id, manifest)

    # Emit state.transitioned event
    ev.emit_event(
        project_id,
        "state.transitioned",
        actor=actor,
        payload=payload,
        state_before=current,
        state_after=next_st,
    )

    # Emit trigger-specific supplementary event
    extra_type = _TRIGGER_EVENT_MAP.get(trigger)
    if extra_type is not None:
        ev.emit_event(
            project_id,
            extra_type,
            actor=actor,
            payload=payload,
            state_before=current,
            state_after=next_st,
        )

    # Terminal-state bookkeeping
    if next_st == "completed":
        ev.emit_event(
            project_id,
            "project.completed",
            actor=actor,
            payload=payload,
            state_before=current,
            state_after=next_st,
        )
    elif next_st == "rejected":
        ev.emit_event(
            project_id,
            "project.rejected",
            actor=actor,
            payload=payload,
            state_before=current,
            state_after=next_st,
        )

    return manifest


def lock_scope(
    project_id: str,
    scope_data: dict[str, Any],
) -> dict[str, Any]:
    """Store scope data in the manifest.

    Should be called after the project reaches ``scope_locked`` state.
    Returns the updated manifest or ``{"error": ...}``.
    """
    manifest = load_project(project_id)
    if "error" in manifest:
        return manifest

    scope_data["locked_at"] = _now_iso()
    manifest["scope"] = scope_data
    manifest["updated_at"] = _now_iso()
    _write_manifest(project_id, manifest)
    return manifest


def add_run(
    project_id: str,
    run_id: str,
    query: str,
    workflow_hint: str,
) -> dict[str, Any]:
    """Register a new run under the project.

    Returns the updated manifest or ``{"error": ...}``.
    """
    manifest = load_project(project_id)
    if "error" in manifest:
        return manifest

    run_entry: dict[str, Any] = {
        "run_id": run_id,
        "query": query,
        "workflow_hint": workflow_hint,
        "created_at": _now_iso(),
    }
    manifest["runs"].append(run_entry)
    manifest["updated_at"] = _now_iso()
    _write_manifest(project_id, manifest)
    return manifest


def save_deliverable(
    project_id: str,
    filename: str,
    content: str,
) -> str:
    """Write *content* to ``deliverables/{filename}`` and return the path.

    Returns an error string prefixed with ``"error:"`` on failure.
    """
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return f"error: Project not found: {project_id}"

    deliverables_dir = project_dir / "deliverables"
    deliverables_dir.mkdir(exist_ok=True)
    dest = deliverables_dir / filename
    dest.write_text(content, encoding="utf-8")

    ev.emit_event(
        project_id,
        "deliverable.saved",
        actor="system",
        payload={"filename": filename, "size_bytes": len(content.encode("utf-8"))},
    )

    return str(dest)


def list_projects() -> list[dict[str, Any]]:
    """Return a list of manifest dicts for every project under PROJECTS_DIR."""
    if not PROJECTS_DIR.exists():
        return []
    results: list[dict[str, Any]] = []
    for child in sorted(PROJECTS_DIR.iterdir()):
        manifest_path = child / "manifest.json"
        if manifest_path.is_file():
            with open(manifest_path, "r", encoding="utf-8") as fh:
                results.append(json.load(fh))
    return results


def get_project_summary(project_id: str) -> dict[str, Any]:
    """Return a compact summary: state, run count, event count."""
    manifest = load_project(project_id)
    if "error" in manifest:
        return manifest

    events = ev.list_events(project_id)
    return {
        "project_id": project_id,
        "name": manifest.get("name"),
        "current_state": manifest.get("current_state"),
        "run_count": len(manifest.get("runs", [])),
        "event_count": len(events),
        "created_at": manifest.get("created_at"),
        "updated_at": manifest.get("updated_at"),
    }


def get_project_events(project_id: str) -> list[dict[str, Any]]:
    """Return the full event list for *project_id*."""
    return ev.list_events(project_id)
