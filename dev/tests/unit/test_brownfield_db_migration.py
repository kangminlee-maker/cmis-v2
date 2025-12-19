"""BF-02a: brownfield.db schema/migration tests."""

from __future__ import annotations

from pathlib import Path

from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db, resolve_brownfield_db_path


def _tables(conn) -> set[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {str(r[0]) for r in cur.fetchall()}


def test_brownfield_db_migration_idempotent(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    db_path = resolve_brownfield_db_path(project_root=project_root)
    assert str(db_path).endswith("brownfield.db")

    conn = open_brownfield_db(project_root=project_root)
    v1 = migrate_brownfield_db(conn)
    assert v1 == 1

    expected = {
        "schema_migrations",
        "artifacts",
        "mappings",
        "import_runs",
        "curated_data",
        "curated_bundles",
        "dop_patches",
        "context_views",
        "packs",
    }
    assert expected.issubset(_tables(conn))

    cur = conn.execute("SELECT COUNT(*) FROM schema_migrations")
    assert int(cur.fetchone()[0]) == 1

    # idempotent
    v2 = migrate_brownfield_db(conn)
    assert v2 == 1
    cur2 = conn.execute("SELECT COUNT(*) FROM schema_migrations")
    assert int(cur2.fetchone()[0]) == 1

    conn.close()
