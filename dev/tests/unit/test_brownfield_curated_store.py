"""BF-05: CuratedDatumStore/CuratedBundleStore tests."""

from __future__ import annotations

from pathlib import Path

from cmis_core.brownfield.curated_store import CuratedBundleStore, CuratedDatumStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.semantic_key import make as make_semantic_key


def test_curated_datum_put_dedupes_by_digest_and_semantic_key(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    ds = CuratedDatumStore(conn)
    sk = make_semantic_key(datum_type="table", entity="baseline", name="financials", as_of="2025-12-13")

    payload = {"revenue": 1000, "currency": "KRW"}
    cur1, digest1 = ds.put(datum_type="table", semantic_key=sk, payload=payload, lineage={"from": "ART-1"})
    cur2, digest2 = ds.put(datum_type="table", semantic_key=sk, payload=payload, lineage={"from": "ART-1"})

    assert cur1 == cur2
    assert digest1 == digest2

    rec = ds.get(cur1)
    assert rec is not None
    assert rec.semantic_key == sk
    assert rec.payload_json == payload

    conn.close()


def test_curated_bundle_put_dedupes_by_bundle_digest(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    ds = CuratedDatumStore(conn)
    bs = CuratedBundleStore(conn)

    sk_a = make_semantic_key(datum_type="kv", entity="baseline", name="meta", as_of="2025-12-13")
    sk_b = make_semantic_key(datum_type="table", entity="baseline", name="financials", as_of="2025-12-13")

    _, digest_a = ds.put(datum_type="kv", semantic_key=sk_a, payload={"x": 1}, lineage={})
    _, digest_b = ds.put(datum_type="table", semantic_key=sk_b, payload={"revenue": 1000}, lineage={})

    items_unsorted = [
        {"semantic_key": sk_b, "cur_payload_digest": digest_b, "cur_schema_version": 1},
        {"semantic_key": sk_a, "cur_payload_digest": digest_a, "cur_schema_version": 1},
    ]
    cub_input = {
        "schema_version": 1,
        "normalization_defaults_digest": "sha256:defaults",
        "ingest_policy_digest": "sha256:policy",
        "mapping_ref": {"mapping_id": "MAP-1", "mapping_version": 1},
        "extractor_version": "csv_decoder@0.1.0",
        "patch_chain_digests": ["sha256:patch1"],
        "curated_items": items_unsorted,
    }

    b1, d1 = bs.put(
        cub_digest_input=cub_input,
        import_run_id="IMP-1",
        patch_chain_digests=["sha256:patch1"],
        curated_items=items_unsorted,
    )
    assert b1.startswith("CUB-")
    assert d1.startswith("sha256:")

    # same content but different order -> same digest/id
    items_reversed = list(reversed(items_unsorted))
    b2, d2 = bs.put(
        cub_digest_input={**cub_input, "curated_items": items_reversed},
        import_run_id="IMP-2",
        patch_chain_digests=["sha256:patch1"],
        curated_items=items_reversed,
    )
    assert (b2, d2) == (b1, d1)

    loaded = bs.get(b1)
    assert loaded is not None
    assert loaded.bundle_digest == d1
    # stored curated_items are sorted by semantic_key
    keys = [it.get("semantic_key") for it in loaded.curated_items]
    assert keys == sorted(keys)

    conn.close()
