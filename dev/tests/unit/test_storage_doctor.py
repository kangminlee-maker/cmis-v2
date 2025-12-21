"""Runtime storage doctor unit tests."""

from __future__ import annotations

from pathlib import Path

from cmis_core.stores import StoreFactory
from cmis_core.stores.doctor import run_storage_doctor


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

