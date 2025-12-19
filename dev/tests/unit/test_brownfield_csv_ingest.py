"""BF-09a: CSV ingest + preview tests."""

from __future__ import annotations

from pathlib import Path

from cmis_core.brownfield.csv_ingest import import_csv_file
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.import_run_store import ImportRunStore
from cmis_core.stores.artifact_store import ArtifactStore


def test_csv_ingest_creates_import_run_and_preview_without_row_leak(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    # Prepare sample CSV (contains a value we must not leak into preview)
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("name,revenue\nAlice,1000\nBob,2000\n", encoding="utf-8")

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    artifact_store = ArtifactStore(project_root=project_root)
    imp_id = import_csv_file(project_root=project_root, file_path=csv_path, brownfield_conn=conn, artifact_store=artifact_store)

    imp_store = ImportRunStore(conn)
    rec = imp_store.get(imp_id)
    assert rec is not None
    assert rec.status == "decoded"
    assert rec.preview_report_artifact_id is not None

    preview_path = artifact_store.get_path(rec.preview_report_artifact_id)
    assert preview_path is not None
    text = preview_path.read_text(encoding="utf-8")
    assert "Alice" not in text
    assert "Bob" not in text
    assert "row_count" in text

    conn.close()
    artifact_store.close()
