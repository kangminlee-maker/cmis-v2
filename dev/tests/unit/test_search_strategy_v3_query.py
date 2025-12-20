"""Search Strategy v3 query artifact + request_digest unit tests (SSV3-03)."""

from __future__ import annotations

import json
from pathlib import Path

from cmis_core.search_v3.query import SearchQueryRequest, compute_query_request_digest, finalize_query_request
from cmis_core.stores import ArtifactStore


def test_query_request_digest_stable_for_filter_key_order() -> None:
    a = SearchQueryRequest(
        provider_id="GenericWebSearch",
        query="korea edtech revenue 2024",
        language="en",
        region="KR",
        top_k=8,
        timeout_sec=10,
        filters={"b": 1, "a": 2},
    )
    b = SearchQueryRequest(
        provider_id="GenericWebSearch",
        query="korea edtech revenue 2024",
        language="en",
        region="KR",
        top_k=8,
        timeout_sec=10,
        filters={"a": 2, "b": 1},
    )
    assert compute_query_request_digest(a) == compute_query_request_digest(b)


def test_query_request_digest_does_not_depend_on_query_artifact_id() -> None:
    base = SearchQueryRequest(
        provider_id="GenericWebSearch",
        query="korea edtech revenue 2024",
        language="en",
        region="KR",
        top_k=8,
        timeout_sec=10,
        filters={"recency_days": 365},
    )
    with_art = SearchQueryRequest(
        provider_id=base.provider_id,
        query=base.query,
        language=base.language,
        region=base.region,
        top_k=base.top_k,
        timeout_sec=base.timeout_sec,
        filters=dict(base.filters),
        query_artifact_id="ART-search_v3_query-1234",
        request_digest="sha256:should_not_matter",
    )
    assert compute_query_request_digest(base) == compute_query_request_digest(with_art)


def test_finalize_query_request_persists_query_artifact(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    store = ArtifactStore(project_root=project_root)
    req = SearchQueryRequest(
        provider_id="GenericWebSearch",
        query="korea edtech revenue 2024",
        language="en",
        region="KR",
        top_k=8,
        timeout_sec=10,
        filters={"recency_days": 365},
    )

    finalized = finalize_query_request(store, req, generator_meta={"deterministic": True})
    assert finalized.query_artifact_id is not None
    assert finalized.query_artifact_id.startswith("ART-")
    assert finalized.request_digest.startswith("sha256:")

    meta = store.get_meta(finalized.query_artifact_id)
    assert meta is not None
    p = Path(meta["file_path"])
    assert p.exists()
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["query"] == "korea edtech revenue 2024"
    assert payload["generator"]["deterministic"] is True

    store.close()
