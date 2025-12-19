"""BF-04: ImportRunStore tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.import_run_store import ImportRunStore


def test_import_run_store_state_machine(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    store = ImportRunStore(conn)
    imp = store.create_staged(
        artifact_ids=["ART-1"],
        mapping_ref={"mapping_id": "MAP-1", "mapping_version": 1},
        extractor_version="csv_decoder@0.1.0",
        ingest_policy_digest="sha256:policy",
        normalization_defaults_digest="sha256:defaults",
    )
    rec = store.get(imp)
    assert rec is not None
    assert rec.status == "staged"
    assert rec.preview_report_artifact_id is None
    assert rec.validation_report_artifact_id is None

    store.attach_preview(imp, "ART-preview-1")
    rec2 = store.get(imp)
    assert rec2 is not None
    assert rec2.status == "decoded"
    assert rec2.preview_report_artifact_id == "ART-preview-1"

    store.attach_validation(imp, "ART-validation-1", "pass")
    rec3 = store.get(imp)
    assert rec3 is not None
    assert rec3.status == "validated"
    assert rec3.validation_decision == "pass"

    store.mark_committed(imp, "CUB-1")
    rec4 = store.get(imp)
    assert rec4 is not None
    assert rec4.status == "committed"
    assert rec4.committed_bundle_id == "CUB-1"

    # invalid transition: cannot commit unless validated
    imp2 = store.create_staged(artifact_ids=["ART-2"])
    with pytest.raises(ValueError):
        store.mark_committed(imp2, "CUB-2")

    conn.close()
