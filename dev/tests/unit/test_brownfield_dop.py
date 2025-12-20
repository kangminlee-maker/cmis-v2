"""BF-06: DataOverridePatch (DOP) store + apply tests."""

from __future__ import annotations

from cmis_core.brownfield.curated_store import CuratedBundleStore, CuratedDatumStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.dop_store import DataOverridePatchStore, apply_data_override_patches_to_bundle
from cmis_core.brownfield.semantic_key import make as make_semantic_key


def test_dop_store_create_dedupes_by_patch_digest(project_root, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    ds = DataOverridePatchStore(conn)

    p1 = ds.create(
        applies_to_bundle_id="CUB-1",
        applies_to_datum_id="CUR-1",
        operation="set",
        target_path="/a/b",
        value=2,
        reason_ref="ART-foo#validation.item1",
    )
    p2 = ds.create(
        applies_to_bundle_id="CUB-1",
        applies_to_datum_id="CUR-1",
        operation="set",
        target_path="/a/b",
        value=2,
        reason_ref="ART-foo#validation.item1",
    )

    assert p1.patch_id == p2.patch_id
    assert p1.patch_digest == p2.patch_digest

    loaded = ds.get(p1.patch_id)
    assert loaded is not None
    assert loaded.patch_digest == p1.patch_digest

    conn.close()


def test_apply_dop_requires_approval_in_reporting_strict(project_root, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    datum_store = CuratedDatumStore(conn)
    bundle_store = CuratedBundleStore(conn)
    dop_store = DataOverridePatchStore(conn)

    sk = make_semantic_key(datum_type="kv", entity="baseline", name="meta", as_of="2025-12-13")
    payload = {"a": {"b": 1}, "x": 10}
    cur_id, cur_digest = datum_store.put(datum_type="kv", semantic_key=sk, payload=payload, lineage={})

    base_input = {
        "schema_version": 1,
        "normalization_defaults_digest": "sha256:defaults",
        "ingest_policy_digest": "sha256:policy",
        "mapping_ref": {"mapping_id": "MAP-1", "mapping_version": 1},
        "extractor_version": "csv_decoder@0.1.0",
        "patch_chain_digests": [],
        "curated_items": [{"semantic_key": sk, "cur_payload_digest": cur_digest, "cur_schema_version": 1}],
    }
    base_bundle_id, _ = bundle_store.put(
        cub_digest_input=base_input,
        import_run_id="IMP-1",
        patch_chain_digests=[],
        curated_items=base_input["curated_items"],
    )

    # Create an unapproved DOP
    dop = dop_store.create(
        applies_to_bundle_id=base_bundle_id,
        applies_to_datum_id=cur_id,
        operation="set",
        target_path="/a/b",
        value=2,
        reason_ref="ART-foo#validation.item1",
    )

    # Strict mode must deny without approval
    denied = False
    try:
        apply_data_override_patches_to_bundle(
            conn=conn,
            base_bundle_id=base_bundle_id,
            patch_ids=[dop.patch_id],
            policy_mode="reporting_strict",
        )
    except Exception:
        denied = True
    assert denied is True

    # Approve and apply
    dop_store.approve(patch_id=dop.patch_id, approved_by="tester")
    new_bundle_id, new_bundle_digest = apply_data_override_patches_to_bundle(
        conn=conn,
        base_bundle_id=base_bundle_id,
        patch_ids=[dop.patch_id],
        policy_mode="reporting_strict",
    )

    assert new_bundle_id.startswith("CUB-")
    assert new_bundle_digest.startswith("sha256:")
    assert new_bundle_id != base_bundle_id

    new_bundle = bundle_store.get(new_bundle_id)
    assert new_bundle is not None
    assert dop.patch_digest in new_bundle.patch_chain_digests

    # The curated item digest must have changed
    assert new_bundle.curated_items
    assert new_bundle.curated_items[0]["semantic_key"] == sk
    assert new_bundle.curated_items[0]["cur_payload_digest"] != cur_digest

    # determinism: applying again on the same base yields the same new bundle (dedupe by digest)
    new_bundle_id_2, new_bundle_digest_2 = apply_data_override_patches_to_bundle(
        conn=conn,
        base_bundle_id=base_bundle_id,
        patch_ids=[dop.patch_id],
        policy_mode="reporting_strict",
    )
    assert (new_bundle_id_2, new_bundle_digest_2) == (new_bundle_id, new_bundle_digest)

    conn.close()
