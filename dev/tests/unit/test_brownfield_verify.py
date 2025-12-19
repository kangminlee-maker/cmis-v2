"""BF-12: verify_prj tests."""

from __future__ import annotations

from pathlib import Path

from cmis_core.brownfield.commit import commit_import_run
from cmis_core.brownfield.csv_ingest import import_csv_file
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.validation import validate_import_run
from cmis_core.brownfield.verify import verify_prj
from cmis_core.stores.artifact_store import ArtifactStore
from cmis_core.stores.focal_actor_context_store import FocalActorContextStore
from cmis_core.types import FocalActorContext


def test_verify_prj_pass_and_fail_cases(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    csv_path = tmp_path / "ok.csv"
    csv_path.write_text("name,revenue\nAlice,1000\n", encoding="utf-8")

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)
    artifact_store = ArtifactStore(project_root=project_root)

    imp_id = import_csv_file(project_root=project_root, file_path=csv_path, brownfield_conn=conn, artifact_store=artifact_store)
    validate_import_run(project_root=project_root, import_run_id=imp_id, policy_mode="reporting_strict", brownfield_conn=conn, artifact_store=artifact_store)
    _, prj_id_v1 = commit_import_run(
        project_root=project_root,
        import_run_id=imp_id,
        policy_mode="reporting_strict",
        focal_actor_context_base_id="PRJ-test",
        brownfield_conn=conn,
        artifact_store=artifact_store,
    )

    ok = verify_prj(project_root=project_root, focal_actor_context_id=prj_id_v1, brownfield_conn=conn)
    assert ok.ok is True

    # create a broken PRJ v2 with wrong digest
    ctx_store = FocalActorContextStore(project_root=project_root)
    broken = FocalActorContext(
        focal_actor_context_id="PRJ-test-v2",
        version=2,
        previous_version_id=prj_id_v1,
        scope={},
        assets_profile={},
        baseline_state={},
        focal_actor_id=None,
        constraints_profile={},
        preference_profile={},
        lineage={
            "primary_source_bundle": {"bundle_id": "CUB-DOES-NOT-MATTER", "bundle_digest": "sha256:wrong", "role": "baseline"},
            "context_builder": {"version": "brownfield_context_builder@0.1.0"},
        },
    )
    ctx_store.save(broken)
    ctx_store.close()

    bad = verify_prj(project_root=project_root, focal_actor_context_id="PRJ-test-v2", brownfield_conn=conn)
    assert bad.ok is False

    conn.close()
    artifact_store.close()
