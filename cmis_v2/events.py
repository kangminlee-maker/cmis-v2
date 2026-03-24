"""CMIS v2 unified event system.

All project-level and run-level events are stored in a single SQLite
database per project (``projects/{project_id}/events.db``).  The module
exposes a small functional API — no singleton, no global state.

Architecture Decision 8: project + run events unified.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

# ---------------------------------------------------------------------------
# Event types (exhaustive)
# ---------------------------------------------------------------------------

EventType = Literal[
    # --- Active: emitted by project.py / tools.py ---
    "project.created",
    "project.completed",
    "project.rejected",
    "state.transitioned",
    "discovery.completed",
    "scope.approved",
    "scope.revised",
    "scope.rejected",
    "data.collection_started",
    "data.quality_passed",
    "analysis.completed",
    "finding.approved",
    "finding.deepened",
    "finding.completed_early",
    "opportunity.started",
    "opportunity.completed",
    "opportunity.selected",
    "opportunity.deepened",
    "opportunity.completed_early",
    "opportunity.skipped",
    "strategy.completed",
    "decision.approved",
    "decision.revised",
    "deliverable.saved",
    "engine.called",
    "error.occurred",
    # --- Reserved: declared for future use, not yet emitted ---
    "discovery.started",      # reserved: auto-emit when entering discovery
    "data.quality_failed",    # reserved: emit on evidence gate failure
    "analysis.started",       # reserved: auto-emit when entering structure_analysis
    "strategy.started",       # reserved: auto-emit when entering strategy_design
    "synthesis.started",      # reserved: auto-emit when entering synthesis
    "synthesis.completed",    # reserved: emit before deliverable.saved
]

# ---------------------------------------------------------------------------
# Projects root (single source from config)
# ---------------------------------------------------------------------------

from cmis_v2.config import PROJECTS_DIR

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _db_path(project_id: str) -> Path:
    """Return the SQLite database path for a project."""
    return PROJECTS_DIR / project_id / "events.db"


def _connect(project_id: str) -> sqlite3.Connection:
    """Open (and optionally initialise) the event database for *project_id*.

    Settings: WAL mode, foreign_keys ON, busy_timeout 5 000 ms.
    """
    path = _db_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(
        """\
        CREATE TABLE IF NOT EXISTS events (
            event_id     TEXT PRIMARY KEY,
            project_id   TEXT NOT NULL,
            run_id       TEXT,
            ts           TEXT NOT NULL,
            type         TEXT NOT NULL,
            actor        TEXT NOT NULL,
            state_before TEXT,
            state_after  TEXT,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _next_event_id(conn: sqlite3.Connection) -> str:
    """Generate a unique event ID using uuid4."""
    return f"evt_{uuid4().hex[:12]}"


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a raw SQLite row into a dictionary."""
    keys = (
        "event_id",
        "project_id",
        "run_id",
        "ts",
        "type",
        "actor",
        "state_before",
        "state_after",
        "payload_json",
    )
    d: dict[str, Any] = dict(zip(keys, row))
    d["payload"] = json.loads(d.pop("payload_json"))
    return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_event(
    project_id: str,
    event_type: EventType,
    actor: str,
    payload: dict[str, Any] | None = None,
    *,
    run_id: str | None = None,
    state_before: str | None = None,
    state_after: str | None = None,
) -> dict[str, Any]:
    """Persist a new event and return it as a dict."""
    conn = _connect(project_id)
    try:
        event_id = _next_event_id(conn)
        ts = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        conn.execute(
            """\
            INSERT INTO events
                (event_id, project_id, run_id, ts, type, actor,
                 state_before, state_after, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                project_id,
                run_id,
                ts,
                event_type,
                actor,
                state_before,
                state_after,
                payload_json,
            ),
        )
        conn.commit()
        return {
            "event_id": event_id,
            "project_id": project_id,
            "run_id": run_id,
            "ts": ts,
            "type": event_type,
            "actor": actor,
            "state_before": state_before,
            "state_after": state_after,
            "payload": payload or {},
        }
    finally:
        conn.close()


def list_events(
    project_id: str,
    *,
    run_id: str | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    """Return events for *project_id*, optionally filtered by run / type."""
    db = _db_path(project_id)
    if not db.exists():
        return []

    conn = _connect(project_id)
    try:
        clauses: list[str] = ["project_id = ?"]
        params: list[str] = [project_id]
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if event_type is not None:
            clauses.append("type = ?")
            params.append(event_type)
        where = " AND ".join(clauses)
        cur = conn.execute(
            f"SELECT * FROM events WHERE {where} ORDER BY event_id",
            params,
        )
        return [_row_to_dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


