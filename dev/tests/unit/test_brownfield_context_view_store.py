"""BF-07: ContextViewStore(PRJ_VIEW) tests."""

from __future__ import annotations

from cmis_core.brownfield.context_view_store import ContextViewStore, is_view_current
from cmis_core.brownfield.curated_store import CuratedBundleStore, CuratedDatumStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.semantic_key import make as make_semantic_key
from cmis_core.stores.artifact_store import ArtifactStore
from cmis_core.stores.focal_actor_context_store import FocalActorContextStore
from cmis_core.types import FocalActorContext


def test_context_view_store_put_and_current_check(project_root, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    datum_store = CuratedDatumStore(conn)
    bundle_store = CuratedBundleStore(conn)
    view_store = ContextViewStore(conn)

    sk = make_semantic_key(datum_type="kv", entity="baseline", name="meta", as_of="2025-12-13")
    _, cur_digest = datum_store.put(datum_type="kv", semantic_key=sk, payload={"x": 1}, lineage={})

    cub_input = {
        "schema_version": 1,
        "normalization_defaults_digest": "sha256:defaults",
        "ingest_policy_digest": "sha256:policy",
        "mapping_ref": {"mapping_id": "MAP-1", "mapping_version": 1},
        "extractor_version": "csv_decoder@0.1.0",
        "patch_chain_digests": [],
        "curated_items": [{"semantic_key": sk, "cur_payload_digest": cur_digest, "cur_schema_version": 1}],
    }
    cub_id, cub_digest = bundle_store.put(
        cub_digest_input=cub_input,
        import_run_id="IMP-1",
        patch_chain_digests=[],
        curated_items=cub_input["curated_items"],
    )

    prj = FocalActorContext(
        focal_actor_context_id="PRJ-viewtest-v1",
        version=1,
        previous_version_id=None,
        scope={},
        assets_profile={},
        baseline_state={},
        focal_actor_id=None,
        constraints_profile={},
        preference_profile={},
        lineage={
            "primary_source_bundle": {"bundle_id": cub_id, "bundle_digest": cub_digest, "role": "baseline"},
            "context_builder": {"version": "brownfield_context_builder@0.1.0"},
        },
    )

    ctx_store = FocalActorContextStore(project_root=project_root)
    ctx_store.save(prj)
    ctx_store.close()

    art = ArtifactStore(project_root=project_root)
    try:
        vid = view_store.put(
            focal_actor_context_id=prj.focal_actor_context_id,
            view_payload={"summary": {"ok": True}},
            derived_from_bundle_digest=cub_digest,
            artifact_store=art,
        )
        assert vid.startswith("PRJ_VIEW-")

        latest = view_store.get_latest(prj.focal_actor_context_id)
        assert latest is not None
        assert latest.view_id == vid
        assert latest.view_payload_ref_artifact_id is not None

        assert is_view_current(prj=prj, view=latest) is True

        # stale if digest mismatched
        stale_vid = view_store.put(
            focal_actor_context_id=prj.focal_actor_context_id,
            view_payload={"summary": {"ok": False}},
            derived_from_bundle_digest="sha256:wrong",
            artifact_store=art,
        )
        stale = view_store.get(stale_vid)
        assert stale is not None
        assert is_view_current(prj=prj, view=stale) is False
    finally:
        art.close()
        conn.close()
