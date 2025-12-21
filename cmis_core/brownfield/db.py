"""Brownfield DB (minimal_local) schema + migrations (BF-02a).

목표:
- `.cmis/db/brownfield.db` 단일 SQLite에 Brownfield 관련 테이블을 제공
- schema_migrations 기반으로 idempotent migration 지원

주의:
- 본 DB는 "Brownfield ingest/curation"의 SoT(메타)로 사용됩니다.
- 파일/대용량 payload는 ArtifactStore(`.cmis/artifacts/`)에 externalize할 수 있습니다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Optional

from cmis_core.stores.sqlite_base import StoragePaths, connect_sqlite


BROWNFIELD_SCHEMA_VERSION = 1


def resolve_brownfield_db_path(*, project_root: Optional[Path] = None, db_path: Optional[Path] = None) -> Path:
    """brownfield.db 경로를 결정합니다."""

    if db_path is not None:
        return Path(db_path)
    paths = StoragePaths.resolve(project_root)
    return paths.db_dir / "brownfield.db"


def open_brownfield_db(*, project_root: Optional[Path] = None, db_path: Optional[Path] = None) -> sqlite3.Connection:
    """brownfield.db 연결을 생성합니다."""

    path = resolve_brownfield_db_path(project_root=project_root, db_path=db_path)
    return connect_sqlite(path)


def migrate_brownfield_db(conn: sqlite3.Connection) -> int:
    """brownfield.db를 최신 스키마로 마이그레이션합니다.

    Returns:
        적용 후 schema version
    """

    _ensure_migrations_table(conn)
    current = _current_version(conn)
    if current < 1:
        _apply_v1(conn)
        _record_version(conn, 1)
        current = 1

    _ensure_v1_columns(conn)
    _ensure_outbox_table(conn)
    conn.commit()
    return int(current)


def _ensure_v1_columns(conn: sqlite3.Connection) -> None:
    """v1 스키마에서 누락되기 쉬운 컬럼을 best-effort로 보강합니다."""

    _ensure_column(conn, table="import_runs", col="validation_decision", typ="TEXT")
    # Brownfield commit의 외부 publish(예: contexts.db) 멱등/복구를 위해 계획/결과를 기록합니다.
    _ensure_column(conn, table="import_runs", col="focal_actor_context_base_id", typ="TEXT")
    _ensure_column(conn, table="import_runs", col="focal_actor_context_version", typ="INTEGER")
    _ensure_column(conn, table="import_runs", col="published_focal_actor_context_id", typ="TEXT")


def _ensure_outbox_table(conn: sqlite3.Connection) -> None:
    """외부(side-effect) 작업을 위한 outbox 테이블을 보장합니다."""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox (
            outbox_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            processed_at TEXT
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_idempotency_unique ON outbox(idempotency_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_created_at ON outbox(created_at)")


def _ensure_column(conn: sqlite3.Connection, *, table: str, col: str, typ: str) -> None:
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        cols = {str(r[1]) for r in cur.fetchall()}
        if col in cols:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    except Exception:
        # best-effort: do not fail migration for optional column
        return


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )


def _current_version(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
    row = cur.fetchone()
    if not row:
        return 0
    try:
        return int(row[0] or 0)
    except Exception:
        return 0


def _record_version(conn: sqlite3.Connection, version: int) -> None:
    applied_at = datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (int(version), applied_at))


def _apply_v1(conn: sqlite3.Connection) -> None:
    """Initial schema for Brownfield MVP."""

    # Artifacts meta (same schema as ArtifactStore)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            kind TEXT,
            mime_type TEXT,
            file_path TEXT NOT NULL,
            sha256 TEXT,
            size_bytes INTEGER,
            original_filename TEXT,
            meta_json TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_sha256 ON artifacts(sha256)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_sha256_size ON artifacts(sha256, size_bytes)")

    # Mapping specs
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mappings (
            mapping_id TEXT NOT NULL,
            mapping_version INTEGER NOT NULL,
            mapping_digest TEXT NOT NULL,
            artifact_id TEXT,
            extractor_version TEXT,
            schema_version INTEGER,
            spec_json TEXT,
            spec_ref_artifact_id TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (mapping_id, mapping_version)
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mappings_digest_unique ON mappings(mapping_digest)")

    # Import runs (state machine)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS import_runs (
            import_run_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            artifact_ids_json TEXT NOT NULL,
            mapping_ref_json TEXT,
            extractor_version TEXT,
            ingest_policy_digest TEXT,
            normalization_defaults_digest TEXT,
            patches_digest TEXT,
            input_fingerprint TEXT NOT NULL,
            validation_report_artifact_id TEXT,
            validation_decision TEXT,
            preview_report_artifact_id TEXT,
            committed_bundle_id TEXT,
            focal_actor_context_base_id TEXT,
            focal_actor_context_version INTEGER,
            published_focal_actor_context_id TEXT,
            notes TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_import_runs_status ON import_runs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_import_runs_fingerprint ON import_runs(input_fingerprint)")

    # Curated datum (atomic normalized data)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS curated_data (
            datum_id TEXT PRIMARY KEY,
            datum_type TEXT NOT NULL,
            semantic_key TEXT NOT NULL,
            as_of TEXT,
            period_range TEXT,
            schema_version INTEGER,
            payload_json TEXT,
            payload_ref_artifact_id TEXT,
            cur_payload_digest TEXT NOT NULL,
            lineage_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_curated_data_semantic_key ON curated_data(semantic_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_curated_data_digest ON curated_data(cur_payload_digest)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_curated_data_dedupe ON curated_data(cur_payload_digest, semantic_key, schema_version)"
    )

    # Curated bundle (commit unit)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS curated_bundles (
            bundle_id TEXT PRIMARY KEY,
            bundle_digest TEXT NOT NULL,
            import_run_id TEXT,
            as_of TEXT,
            schema_version INTEGER,
            normalization_defaults_digest TEXT,
            ingest_policy_digest TEXT,
            mapping_ref_json TEXT,
            extractor_version TEXT,
            patch_chain_digests_json TEXT,
            curated_items_json TEXT,
            quality_summary_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_curated_bundles_digest_unique ON curated_bundles(bundle_digest)")

    # Data override patches (V2; kept as table stub for forward compatibility)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dop_patches (
            patch_id TEXT PRIMARY KEY,
            applies_to_bundle_id TEXT NOT NULL,
            applies_to_datum_id TEXT,
            operation TEXT NOT NULL,
            target_path TEXT NOT NULL,
            value_json TEXT NOT NULL,
            reason_ref TEXT,
            approved_by TEXT,
            approved_at TEXT,
            patch_digest TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_dop_patches_digest_unique ON dop_patches(patch_digest)")

    # PRJ_VIEW (V2; table stub)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS context_views (
            view_id TEXT PRIMARY KEY,
            focal_actor_context_id TEXT NOT NULL,
            derived_from_bundle_digest TEXT,
            derived_from_sources_digest TEXT,
            view_payload_ref_artifact_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_context_views_prj ON context_views(focal_actor_context_id)")

    # BPK (V2; table stub)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS packs (
            pack_id TEXT NOT NULL,
            pack_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            spec_json TEXT,
            PRIMARY KEY (pack_id, pack_version)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_packs_pack_id ON packs(pack_id)")
