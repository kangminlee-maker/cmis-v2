"""BF-11: Commit orchestrator tests (CSV MVP)."""

from __future__ import annotations

from pathlib import Path

from cmis_core.brownfield.commit import commit_import_run
from cmis_core.brownfield.csv_ingest import import_csv_file
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.curated_store import CuratedBundleStore
from cmis_core.brownfield.import_run_store import ImportRunStore
from cmis_core.brownfield.validation import validate_import_run
from cmis_core.stores.artifact_store import ArtifactStore
from cmis_core.stores.focal_actor_context_store import FocalActorContextStore


def test_commit_import_run_creates_cub_and_prj(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("name,revenue\nAlice,1000\n", encoding="utf-8")

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    artifact_store = ArtifactStore(project_root=project_root)

    imp_id = import_csv_file(project_root=project_root, file_path=csv_path, brownfield_conn=conn, artifact_store=artifact_store)
    validate_import_run(project_root=project_root, import_run_id=imp_id, policy_mode="reporting_strict", brownfield_conn=conn, artifact_store=artifact_store)

    cub_id, prj_id = commit_import_run(
        project_root=project_root,
        import_run_id=imp_id,
        policy_mode="reporting_strict",
        focal_actor_context_base_id="PRJ-test",
        brownfield_conn=conn,
        artifact_store=artifact_store,
    )
    assert cub_id.startswith("CUB-")
    assert prj_id == "PRJ-test-v1"

    # IMP 상태 갱신
    rec = ImportRunStore(conn).get(imp_id)
    assert rec is not None
    assert rec.status == "committed"
    assert rec.committed_bundle_id == cub_id

    # CUB 저장 확인
    bundle = CuratedBundleStore(conn).get(cub_id)
    assert bundle is not None
    assert bundle.bundle_id == cub_id

    # PRJ 저장 확인 (contexts.db)
    ctx_store = FocalActorContextStore(project_root=project_root)
    latest = ctx_store.get_latest("PRJ-test")
    assert latest is not None
    assert latest.focal_actor_context_id == prj_id
    assert latest.lineage.get("primary_source_bundle", {}).get("bundle_id") == cub_id
    ctx_store.close()

    conn.close()
    artifact_store.close()
