"""BF-08: BrownfieldPackStore(BPK) tests."""

from __future__ import annotations

from cmis_core.brownfield.curated_store import CuratedBundleStore, CuratedDatumStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.pack_store import BrownfieldPackStore, select_bundle_from_pack_spec, verify_pack
from cmis_core.brownfield.semantic_key import make as make_semantic_key


def test_pack_store_append_only_and_selectors(project_root, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    datum_store = CuratedDatumStore(conn)
    bundle_store = CuratedBundleStore(conn)

    sk = make_semantic_key(datum_type="kv", entity="baseline", name="meta", as_of="2025-12-13")
    _, d1 = datum_store.put(datum_type="kv", semantic_key=sk, payload={"x": 1}, lineage={})
    _, d2 = datum_store.put(datum_type="kv", semantic_key=sk, payload={"x": 2}, lineage={})

    cub_input_1 = {
        "schema_version": 1,
        "normalization_defaults_digest": "sha256:defaults",
        "ingest_policy_digest": "sha256:policy",
        "mapping_ref": {"mapping_id": "MAP-1", "mapping_version": 1},
        "extractor_version": "csv_decoder@0.1.0",
        "patch_chain_digests": [],
        "curated_items": [{"semantic_key": sk, "cur_payload_digest": d1, "cur_schema_version": 1}],
    }
    cub_id_1, cub_digest_1 = bundle_store.put(
        cub_digest_input=cub_input_1,
        import_run_id="IMP-1",
        patch_chain_digests=[],
        curated_items=cub_input_1["curated_items"],
    )

    cub_input_2 = {
        **cub_input_1,
        "curated_items": [{"semantic_key": sk, "cur_payload_digest": d2, "cur_schema_version": 1}],
    }
    cub_id_2, cub_digest_2 = bundle_store.put(
        cub_digest_input=cub_input_2,
        import_run_id="IMP-2",
        patch_chain_digests=[],
        curated_items=cub_input_2["curated_items"],
    )

    store = BrownfieldPackStore(conn)

    spec_v1 = {
        "bundles": [
            {"bundle_id": cub_id_1, "bundle_digest": cub_digest_1, "as_of": "2024-12-31", "status": "validated"},
            {"bundle_id": cub_id_2, "bundle_digest": cub_digest_2, "as_of": "2025-12-31", "status": "validated"},
        ],
        "as_of_selector": {"mode": "latest_validated"},
    }

    pack_id, v1 = store.create(spec=spec_v1)
    assert pack_id.startswith("BPK-")
    assert v1 == 1

    # append v2
    spec_v2 = {**spec_v1, "notes": "updated"}
    _, v2 = store.append_version(pack_id=pack_id, spec=spec_v2)
    assert v2 == 2
    assert store.list_versions(pack_id) == [1, 2]

    latest = store.get_latest(pack_id)
    assert latest is not None
    assert latest.pack_version == 2

    # selector: latest_validated
    picked = select_bundle_from_pack_spec(pack_spec=spec_v1, as_of_selector="latest_validated")
    assert picked["bundle_id"] == cub_id_2

    # selector: user_select -> closest <= pivot
    picked2 = select_bundle_from_pack_spec(pack_spec=spec_v1, as_of_selector="user_select", as_of="2025-01-01")
    assert picked2["bundle_id"] == cub_id_1

    # verify pack (latest)
    ok = verify_pack(project_root=project_root, pack_id=pack_id, brownfield_conn=conn)
    assert ok.ok is True

    conn.close()
