"""BF-14: CuratedEvidenceSource ↔ EvidenceEngine integration tests."""

from __future__ import annotations

from cmis_core.brownfield.curated_store import CuratedBundleStore, CuratedDatumStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.pack_store import BrownfieldPackStore
from cmis_core.brownfield.semantic_key import make as make_semantic_key
from cmis_core.config import CMISConfig
from cmis_core.evidence.curated_internal_source import CuratedEvidenceSource
from cmis_core.evidence_engine import EvidenceEngine, SourceRegistry
from cmis_core.stores.focal_actor_context_store import FocalActorContextStore
from cmis_core.types import FocalActorContext, MetricRequest


def _make_prj(project_root, prj_id: str, cub_id: str, cub_digest: str) -> None:
    ctx_store = FocalActorContextStore(project_root=project_root)
    prj = FocalActorContext(
        focal_actor_context_id=prj_id,
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
    ctx_store.save(prj)
    ctx_store.close()


def test_evidence_engine_fetches_from_curated_internal_with_prj(project_root, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    # Prepare curated datum/bundle
    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)
    datum_store = CuratedDatumStore(conn)
    bundle_store = CuratedBundleStore(conn)

    sk = make_semantic_key(datum_type="kv", entity="metric", name="MET-Revenue", period="2024")
    _, cur_digest = datum_store.put(datum_type="kv", semantic_key=sk, payload={"value": 1234.0}, lineage={})

    cub_input = {
        "schema_version": 1,
        "normalization_defaults_digest": "sha256:defaults",
        "ingest_policy_digest": "sha256:policy",
        "mapping_ref": {"mapping_id": "MAP-1", "mapping_version": 1},
        "extractor_version": "curated_kv@0.1.0",
        "patch_chain_digests": [],
        "curated_items": [{"semantic_key": sk, "cur_payload_digest": cur_digest, "cur_schema_version": 1}],
    }
    cub_id, cub_digest = bundle_store.put(
        cub_digest_input=cub_input,
        import_run_id="IMP-curated",
        patch_chain_digests=[],
        curated_items=cub_input["curated_items"],
    )
    conn.commit()

    _make_prj(project_root, "PRJ-curated-v1", cub_id, cub_digest)

    # EvidenceEngine wired with curated source
    config = CMISConfig(project_root / "cmis.yaml")
    registry = SourceRegistry()
    curated = CuratedEvidenceSource(project_root=config.project_root)
    registry.register_source(curated.source_id, curated.source_tier.value, curated)

    engine = EvidenceEngine(config, registry)

    mr = MetricRequest(metric_id="MET-Revenue", context={"year": 2024, "focal_actor_context_id": "PRJ-curated-v1"})
    res = engine.fetch_for_metrics([mr], policy_ref="reporting_strict", use_cache=False)

    bundle = res.bundles.get("MET-Revenue")
    assert bundle is not None
    assert bundle.records
    best = bundle.get_best_record()
    assert best is not None
    assert best.source_tier == "curated_internal"
    assert best.value == 1234.0

    conn.close()


def test_curated_internal_can_resolve_from_pack(project_root, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    datum_store = CuratedDatumStore(conn)
    bundle_store = CuratedBundleStore(conn)

    sk = make_semantic_key(datum_type="kv", entity="metric", name="MET-Revenue", period="2024")
    _, cur_digest = datum_store.put(datum_type="kv", semantic_key=sk, payload={"value": 555.0}, lineage={})

    cub_input = {
        "schema_version": 1,
        "normalization_defaults_digest": "sha256:defaults",
        "ingest_policy_digest": "sha256:policy",
        "mapping_ref": {"mapping_id": "MAP-1", "mapping_version": 1},
        "extractor_version": "curated_kv@0.1.0",
        "patch_chain_digests": [],
        "curated_items": [{"semantic_key": sk, "cur_payload_digest": cur_digest, "cur_schema_version": 1}],
    }
    cub_id, cub_digest = bundle_store.put(
        cub_digest_input=cub_input,
        import_run_id="IMP-curated",
        patch_chain_digests=[],
        curated_items=cub_input["curated_items"],
    )
    conn.commit()

    pack_store = BrownfieldPackStore(conn)
    spec = {
        "bundles": [
            {"bundle_id": cub_id, "bundle_digest": cub_digest, "as_of": "2024-12-31", "status": "validated"}
        ],
        "as_of_selector": {"mode": "latest_validated"},
    }
    pack_id, _ = pack_store.create(spec=spec, pack_id="BPK-curated")
    assert pack_id == "BPK-curated"
    conn.commit()

    config = CMISConfig(project_root / "cmis.yaml")
    registry = SourceRegistry()
    curated = CuratedEvidenceSource(project_root=config.project_root)
    registry.register_source(curated.source_id, curated.source_tier.value, curated)

    engine = EvidenceEngine(config, registry)
    mr = MetricRequest(metric_id="MET-Revenue", context={"year": 2024, "brownfield_pack_id": pack_id})
    res = engine.fetch_for_metrics([mr], policy_ref="reporting_strict", use_cache=False)

    bundle = res.bundles.get("MET-Revenue")
    assert bundle is not None
    assert bundle.records
    best = bundle.get_best_record()
    assert best is not None
    assert best.source_tier == "curated_internal"
    assert best.value == 555.0

    conn.close()
