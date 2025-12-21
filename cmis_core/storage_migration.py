"""Runtime storage migration utilities.

This module provides best-effort helpers to migrate CMIS runtime storage located under
`<storage_root>/.cmis/`.

Current migration target:
- Rename legacy keys:
  - project_context_id -> focal_actor_context_id

Notes:
- This is NOT a compatibility alias for runtime APIs.
- It is a one-time migration helper to transform existing SQLite JSON payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Dict, Iterable, Optional, Tuple

from cmis_core.run_exporter import RunExporter
from cmis_core.policy_engine import PolicyEngine
from cmis_core.stores import StoreFactory
from cmis_core.stores.sqlite_base import StoragePaths


_RENAME_MAP = {
    # primary external key
    "project_context_id": "focal_actor_context_id",
    # common plural summaries
    "project_context_ids": "focal_actor_context_ids",
    # lineage fields
    "from_project_context_id": "from_focal_actor_context_id",
}


def _rename_keys_deep(obj: Any, *, rename_map: Dict[str, str]) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            nk = rename_map.get(str(k), str(k))
            out[nk] = _rename_keys_deep(v, rename_map=rename_map)
        return out

    if isinstance(obj, list):
        return [_rename_keys_deep(x, rename_map=rename_map) for x in obj]

    return obj


@dataclass(frozen=True)
class MigrationReport:
    """Migration result summary."""

    updated_rows: int
    touched_tables: Tuple[str, ...]


def _iter_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [str(r[0]) for r in rows]


def _migrate_json_column_rows(
    conn: sqlite3.Connection,
    *,
    table: str,
    id_col: str,
    json_col: str,
    rename_map: Dict[str, str],
) -> int:
    updated = 0

    cur = conn.execute(f'SELECT "{id_col}", "{json_col}" FROM "{table}"')
    rows = cur.fetchall()

    for row_id, raw_json in rows:
        try:
            data = json.loads(raw_json or "{}")
        except Exception:
            continue

        migrated = _rename_keys_deep(data, rename_map=rename_map)
        if migrated == data:
            continue

        conn.execute(
            f'UPDATE "{table}" SET "{json_col}" = ? WHERE "{id_col}" = ?',
            (json.dumps(migrated, ensure_ascii=False), row_id),
        )
        updated += 1

    return updated


def _migrate_json_column_rows_composite_pk(
    conn: sqlite3.Connection,
    *,
    table: str,
    pk_cols: Tuple[str, str],
    json_col: str,
    rename_map: Dict[str, str],
) -> int:
    updated = 0

    pk1, pk2 = pk_cols
    cur = conn.execute(f'SELECT "{pk1}", "{pk2}", "{json_col}" FROM "{table}"')
    rows = cur.fetchall()

    for v1, v2, raw_json in rows:
        try:
            data = json.loads(raw_json or "{}")
        except Exception:
            continue

        migrated = _rename_keys_deep(data, rename_map=rename_map)
        if migrated == data:
            continue

        conn.execute(
            f'UPDATE "{table}" SET "{json_col}" = ? WHERE "{pk1}" = ? AND "{pk2}" = ?',
            (json.dumps(migrated, ensure_ascii=False), v1, v2),
        )
        updated += 1

    return updated


def _column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    try:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [str(c[1]) for c in cols]
    except Exception:
        return []


def _rebuild_table_outcomes(conn: sqlite3.Connection) -> None:
    """Rebuild legacy outcomes table to focal_actor_context_id schema (data-preserving)."""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outcomes_new (
            outcome_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            focal_actor_context_id TEXT,
            related_strategy_id TEXT,
            as_of TEXT,
            record_json TEXT NOT NULL
        )
        """
    )

    cols = _column_names(conn, "outcomes")
    if "project_context_id" in cols and "focal_actor_context_id" not in cols:
        conn.execute(
            """
            INSERT OR REPLACE INTO outcomes_new (
                outcome_id, created_at, focal_actor_context_id, related_strategy_id, as_of, record_json
            )
            SELECT outcome_id, created_at, project_context_id, related_strategy_id, as_of, record_json
            FROM outcomes
            """
        )
    else:
        # best-effort: if focal_actor_context_id already exists, just copy through
        conn.execute(
            """
            INSERT OR REPLACE INTO outcomes_new (
                outcome_id, created_at, focal_actor_context_id, related_strategy_id, as_of, record_json
            )
            SELECT outcome_id, created_at, focal_actor_context_id, related_strategy_id, as_of, record_json
            FROM outcomes
            """
        )

    conn.execute("DROP TABLE IF EXISTS outcomes")
    conn.execute("ALTER TABLE outcomes_new RENAME TO outcomes")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_focal_actor_context_id ON outcomes(focal_actor_context_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_related_strategy_id ON outcomes(related_strategy_id)")


def migrate_runtime_storage(
    *,
    project_root: Optional[Path] = None,
    reexport_runs: bool = True,
) -> Dict[str, Any]:
    """Migrate legacy keys inside `.cmis/db` SQLite payloads.

    This performs in-place updates of JSON columns for:
    - runs.db (runs.context_json, run_events.payload_json, run_decisions.payload_json)
    - ledgers.db (ledger_snapshots.project_ledger_json, progress_ledger_json)
    - contexts.db (focal_actor_contexts.record_json)

    Returns:
        dict: migration summary
    """

    paths = StoragePaths.resolve(project_root)
    db_dir = paths.db_dir

    summary: Dict[str, Any] = {
        "storage_root": str(paths.storage_root),
        "db_dir": str(db_dir),
        "updated": {},
    }

    # ---- contexts.db ----
    contexts_path = db_dir / "contexts.db"
    if contexts_path.exists():
        conn = sqlite3.connect(str(contexts_path))
        try:
            tables = _iter_tables(conn)
            touched = []
            updated_rows = 0

            if "focal_actor_contexts" in tables:
                updated_rows += _migrate_json_column_rows_composite_pk(
                    conn,
                    table="focal_actor_contexts",
                    pk_cols=("context_id", "version"),
                    json_col="record_json",
                    rename_map=_RENAME_MAP,
                )
                touched.append("focal_actor_contexts.record_json")

            conn.commit()
            summary["updated"]["contexts.db"] = MigrationReport(
                updated_rows=updated_rows,
                touched_tables=tuple(touched),
            ).__dict__
        finally:
            conn.close()

    # ---- runs.db ----
    runs_path = db_dir / "runs.db"
    if runs_path.exists():
        conn = sqlite3.connect(str(runs_path))
        try:
            tables = _iter_tables(conn)
            touched = []
            updated_rows = 0

            if "runs" in tables:
                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="runs",
                    id_col="run_id",
                    json_col="context_json",
                    rename_map=_RENAME_MAP,
                )
                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="runs",
                    id_col="run_id",
                    json_col="summary_json",
                    rename_map=_RENAME_MAP,
                )
                touched.append("runs.context_json")
                touched.append("runs.summary_json")

            if "run_events" in tables:
                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="run_events",
                    id_col="id",
                    json_col="payload_json",
                    rename_map=_RENAME_MAP,
                )
                touched.append("run_events.payload_json")

            if "run_decisions" in tables:
                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="run_decisions",
                    id_col="id",
                    json_col="payload_json",
                    rename_map=_RENAME_MAP,
                )
                touched.append("run_decisions.payload_json")

            conn.commit()
            summary["updated"]["runs.db"] = MigrationReport(
                updated_rows=updated_rows,
                touched_tables=tuple(touched),
            ).__dict__
        finally:
            conn.close()

    # ---- ledgers.db ----
    ledgers_path = db_dir / "ledgers.db"
    if ledgers_path.exists():
        conn = sqlite3.connect(str(ledgers_path))
        try:
            tables = _iter_tables(conn)
            touched = []
            updated_rows = 0

            if "ledger_snapshots" in tables:
                # Update both JSON columns
                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="ledger_snapshots",
                    id_col="id",
                    json_col="project_ledger_json",
                    rename_map=_RENAME_MAP,
                )
                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="ledger_snapshots",
                    id_col="id",
                    json_col="progress_ledger_json",
                    rename_map=_RENAME_MAP,
                )
                touched.append("ledger_snapshots.project_ledger_json")
                touched.append("ledger_snapshots.progress_ledger_json")

            conn.commit()
            summary["updated"]["ledgers.db"] = MigrationReport(
                updated_rows=updated_rows,
                touched_tables=tuple(touched),
            ).__dict__
        finally:
            conn.close()

    # ---- outcomes.db ----
    outcomes_path = db_dir / "outcomes.db"
    if outcomes_path.exists():
        conn = sqlite3.connect(str(outcomes_path))
        try:
            tables = _iter_tables(conn)
            touched = []
            updated_rows = 0

            if "outcomes" in tables:
                cols = _column_names(conn, "outcomes")
                if ("project_context_id" in cols) and ("focal_actor_context_id" not in cols):
                    _rebuild_table_outcomes(conn)

                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="outcomes",
                    id_col="outcome_id",
                    json_col="record_json",
                    rename_map=_RENAME_MAP,
                )
                touched.append("outcomes.record_json")

            conn.commit()
            summary["updated"]["outcomes.db"] = MigrationReport(
                updated_rows=updated_rows,
                touched_tables=tuple(touched),
            ).__dict__
        finally:
            conn.close()

    # ---- artifacts.db ----
    artifacts_path = db_dir / "artifacts.db"
    if artifacts_path.exists():
        conn = sqlite3.connect(str(artifacts_path))
        try:
            tables = _iter_tables(conn)
            touched = []
            updated_rows = 0

            if "artifacts" in tables:
                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="artifacts",
                    id_col="artifact_id",
                    json_col="meta_json",
                    rename_map=_RENAME_MAP,
                )
                touched.append("artifacts.meta_json")

            conn.commit()
            summary["updated"]["artifacts.db"] = MigrationReport(
                updated_rows=updated_rows,
                touched_tables=tuple(touched),
            ).__dict__
        finally:
            conn.close()

    # ---- evidence_cache.db (legacy EvidenceStore SQLiteBackend) ----
    evidence_cache_path = paths.cmis_dir / "evidence_cache.db"
    if evidence_cache_path.exists():
        conn = sqlite3.connect(str(evidence_cache_path))
        try:
            tables = _iter_tables(conn)
            touched = []
            updated_rows = 0

            if "evidence_cache" in tables:
                updated_rows += _migrate_json_column_rows(
                    conn,
                    table="evidence_cache",
                    id_col="key",
                    json_col="value",
                    rename_map=_RENAME_MAP,
                )
                touched.append("evidence_cache.value")

            conn.commit()
            summary["updated"]["evidence_cache.db"] = MigrationReport(
                updated_rows=updated_rows,
                touched_tables=tuple(touched),
            ).__dict__
        finally:
            conn.close()

    # ---- value_store/*.json (PriorManager) ----
    value_store_dir = paths.cmis_dir / "value_store"
    if value_store_dir.exists():
        updated_files = 0
        for fp in value_store_dir.glob("*.json"):
            try:
                raw = fp.read_text(encoding="utf-8")
                data = json.loads(raw or "{}")
            except Exception:
                continue

            migrated = _rename_keys_deep(data, rename_map=_RENAME_MAP)
            if migrated == data:
                continue

            fp.write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            updated_files += 1

        summary["updated"]["value_store"] = {"updated_files": updated_files, "dir": str(value_store_dir)}

    # ---- Re-export runs (optional) ----
    if reexport_runs and runs_path.exists() and ledgers_path.exists():
        try:
            factory = StoreFactory(project_root=paths.storage_root)
            run_store = factory.run_store()
            ledger_store = factory.ledger_store()
            # Policy/Config는 storage_root가 아닌 "프로젝트 루트"를 기준으로 로드해야 합니다.
            # (CMIS_STORAGE_ROOT로 런타임 스토리지를 분리하는 경우를 지원)
            policy_root = Path(project_root) if project_root is not None else Path.cwd()
            policy_engine = PolicyEngine(project_root=policy_root)
            exporter = RunExporter(project_root=policy_root)

            cur = run_store.conn.execute("SELECT run_id FROM runs ORDER BY started_at ASC")
            run_ids = [str(r[0]) for r in cur.fetchall()]

            exported: list[str] = []
            for rid in run_ids:
                try:
                    out_dir = exporter.export_run(
                        run_id=rid,
                        run_store=run_store,
                        ledger_store=ledger_store,
                        policy_engine=policy_engine,
                    )
                    exported.append(str(out_dir))
                except Exception:
                    continue

            summary["run_export"] = {"exported": exported, "count": len(exported)}

        finally:
            try:
                run_store.close()
            except Exception:
                pass
            try:
                ledger_store.close()
            except Exception:
                pass

    return summary


def reset_runtime_storage(
    *,
    project_root: Optional[Path] = None,
    backup: bool = True,
    reset_runs_dir: bool = True,
    reset_extras: bool = True,
) -> Dict[str, Any]:
    """Reset `.cmis/db` (and optionally `.cmis/runs`) by moving them to backup.

    Returns:
        dict: reset summary
    """

    paths = StoragePaths.resolve(project_root)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = paths.cmis_dir / "backups" / ts

    moved: Dict[str, str] = {}

    if backup:
        backup_root.mkdir(parents=True, exist_ok=True)

    if paths.db_dir.exists():
        if backup:
            dst = backup_root / "db"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(paths.db_dir), str(dst))
            moved["db_dir"] = str(dst)
        else:
            shutil.rmtree(paths.db_dir)

    if reset_runs_dir and paths.runs_dir.exists():
        if backup:
            dst = backup_root / "runs"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(paths.runs_dir), str(dst))
            moved["runs_dir"] = str(dst)
        else:
            shutil.rmtree(paths.runs_dir)

    if reset_extras:
        extras: Dict[str, Path] = {
            "evidence_cache_db": paths.cmis_dir / "evidence_cache.db",
        }
        extra_dirs: Dict[str, Path] = {
            "value_store_dir": paths.cmis_dir / "value_store",
            "artifacts_dir": paths.cmis_dir / "artifacts",
            "cache_dir": paths.cmis_dir / "cache",
        }

        for key, fp in extras.items():
            if not fp.exists():
                continue
            if backup:
                dst = backup_root / fp.name
                try:
                    if dst.exists():
                        dst.unlink()
                except Exception:
                    pass
                shutil.move(str(fp), str(dst))
                moved[key] = str(dst)
            else:
                try:
                    fp.unlink()
                except Exception:
                    pass

        for key, dp in extra_dirs.items():
            if not dp.exists():
                continue
            if backup:
                dst = backup_root / dp.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(dp), str(dst))
                moved[key] = str(dst)
            else:
                shutil.rmtree(dp)

    # recreate directories
    paths.db_dir.mkdir(parents=True, exist_ok=True)
    paths.runs_dir.mkdir(parents=True, exist_ok=True)
    (paths.cmis_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (paths.cmis_dir / "value_store").mkdir(parents=True, exist_ok=True)

    return {
        "storage_root": str(paths.storage_root),
        "backup": bool(backup),
        "backup_root": str(backup_root) if backup else None,
        "moved": moved,
        "recreated": {
            "db_dir": str(paths.db_dir),
            "runs_dir": str(paths.runs_dir),
        },
    }
