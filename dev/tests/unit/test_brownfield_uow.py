"""BF-02b: UnitOfWork(transaction) tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.uow import UnitOfWork


def test_unit_of_work_commit_and_rollback(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    uow = UnitOfWork(conn)

    with uow.transaction() as c:
        c.execute(
            "INSERT INTO mappings(mapping_id, mapping_version, mapping_digest, created_at) VALUES (?, ?, ?, ?)",
            ("MAP-1", 1, "sha256:aaa", "2025-12-13T00:00:00Z"),
        )

    cur = conn.execute("SELECT COUNT(*) FROM mappings WHERE mapping_id = ? AND mapping_version = 1", ("MAP-1",))
    assert int(cur.fetchone()[0]) == 1

    with pytest.raises(RuntimeError):
        with uow.transaction() as c:
            c.execute(
                "INSERT INTO mappings(mapping_id, mapping_version, mapping_digest, created_at) VALUES (?, ?, ?, ?)",
                ("MAP-2", 1, "sha256:bbb", "2025-12-13T00:00:00Z"),
            )
            raise RuntimeError("boom")

    cur2 = conn.execute("SELECT COUNT(*) FROM mappings WHERE mapping_id = ? AND mapping_version = 1", ("MAP-2",))
    assert int(cur2.fetchone()[0]) == 0

    conn.close()
