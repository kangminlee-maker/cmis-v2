"""BF-10: Validation + commit gate tests."""

from __future__ import annotations

from pathlib import Path

from cmis_core.brownfield.csv_ingest import import_csv_file
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.import_run_store import ImportRunStore
from cmis_core.brownfield.validation import can_commit, validate_import_run
from cmis_core.stores.artifact_store import ArtifactStore


def test_validate_import_run_sets_status_and_stores_report(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("name,revenue\nAlice,1000\n", encoding="utf-8")

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)
    artifact_store = ArtifactStore(project_root=project_root)

    imp_id = import_csv_file(project_root=project_root, file_path=csv_path, brownfield_conn=conn, artifact_store=artifact_store)

    result = validate_import_run(
        project_root=project_root,
        import_run_id=imp_id,
        policy_mode="reporting_strict",
        brownfield_conn=conn,
        artifact_store=artifact_store,
    )
    assert result.policy_decision == "pass"
    assert can_commit(policy_mode="reporting_strict", validation_decision=result.policy_decision) is True

    rec = ImportRunStore(conn).get(imp_id)
    assert rec is not None
    assert rec.status == "validated"
    assert rec.validation_report_artifact_id is not None

    report_path = artifact_store.get_path(rec.validation_report_artifact_id)
    assert report_path is not None
    report_text = report_path.read_text(encoding="utf-8")
    assert "Alice" not in report_text
    assert "policy_decision" in report_text

    conn.close()
    artifact_store.close()


def test_validate_import_run_can_fail(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("name,revenue\n", encoding="utf-8")  # header only

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)
    artifact_store = ArtifactStore(project_root=project_root)

    imp_id = import_csv_file(project_root=project_root, file_path=csv_path, brownfield_conn=conn, artifact_store=artifact_store)
    result = validate_import_run(
        project_root=project_root,
        import_run_id=imp_id,
        policy_mode="reporting_strict",
        brownfield_conn=conn,
        artifact_store=artifact_store,
    )
    assert result.policy_decision == "fail"
    assert can_commit(policy_mode="reporting_strict", validation_decision=result.policy_decision) is False

    rec = ImportRunStore(conn).get(imp_id)
    assert rec is not None
    assert rec.status == "rejected"

    conn.close()
    artifact_store.close()
