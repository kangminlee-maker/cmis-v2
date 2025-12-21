"""Runtime storage doctor unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from cmis_core.stores import StoreFactory
from cmis_core.stores.doctor import run_storage_doctor
from cmis_core.brownfield.db import open_brownfield_db, migrate_brownfield_db


def test_storage_doctor_ok_on_fresh_artifact_store(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    factory = StoreFactory(project_root=project_root)
    art = factory.artifact_store()
    try:
        aid = art.put_text("hello", kind="doctor")
        assert art.get_meta(aid) is not None
    finally:
        art.close()

    result = run_storage_doctor(project_root=project_root)
    assert result.ok is True
    assert result.issues == []


def test_storage_doctor_detects_missing_artifact_file(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    factory = StoreFactory(project_root=project_root)
    art = factory.artifact_store()
    try:
        aid = art.put_text("hello", kind="doctor")
        meta = art.get_meta(aid)
        assert meta is not None
        p = Path(str(meta["file_path"]))
        assert p.exists()
        p.unlink()
        assert not p.exists()
    finally:
        art.close()

    result = run_storage_doctor(project_root=project_root)
    assert result.ok is False
    assert any(str(it).startswith("artifact_missing_file:") for it in result.issues)


def test_storage_doctor_detects_missing_brownfield_artifact_ref(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    # 1) ensure artifacts.db exists and has at least 1 artifact_id
    factory = StoreFactory(project_root=project_root)
    art = factory.artifact_store()
    try:
        _ = art.put_text("hello", kind="doctor")
    finally:
        art.close()

    # 2) create brownfield.db row referencing a non-existent artifact id
    conn = open_brownfield_db(project_root=project_root)
    try:
        migrate_brownfield_db(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO import_runs (
                import_run_id, status, created_at, artifact_ids_json, input_fingerprint, preview_report_artifact_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "IMP-test",
                "imported",
                datetime.now(timezone.utc).isoformat(),
                "[]",
                "fp-test",
                "ART-nope",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    result = run_storage_doctor(project_root=project_root)
    assert result.ok is False
    assert any(str(it).startswith("brownfield_missing_artifact_ref:import_runs.preview_report_artifact_id:") for it in result.issues)

