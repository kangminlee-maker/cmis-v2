"""Search Strategy v3 GenericWebSearch provider unit tests (SSV3-04)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from cmis_core.search_v3.generic_web_search import GoogleCseProvider, ProviderError
from cmis_core.search_v3.query import SearchQueryRequest, finalize_query_request
from cmis_core.search_v3.registry import ProviderConfig
from cmis_core.stores import ArtifactStore


class _FakeResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any], text: str = "") -> None:
        self.status_code = int(status_code)
        self._payload = payload
        self.text = text

    def json(self) -> Dict[str, Any]:
        return self._payload


def _provider_cfg(*, cache_ttl_sec: int = 60, rate_limit_qps: float = 1000.0, burst: int = 10) -> ProviderConfig:
    base = ProviderConfig(
        provider_id="GenericWebSearch",
        adapter="google_cse",
        api_key_ref="GOOGLE_API_KEY",
        default_timeout_sec=10,
        rate_limit_qps=rate_limit_qps,
        burst=burst,
        cache_ttl_sec=cache_ttl_sec,
        cost_model=None,
        locale_mapping={},
        provider_config_digest="",
        notes={"search_engine_id_ref": "GOOGLE_SEARCH_ENGINE_ID"},
    )
    digest = base.compute_digest()
    return ProviderConfig(
        provider_id=base.provider_id,
        adapter=base.adapter,
        api_key_ref=base.api_key_ref,
        default_timeout_sec=base.default_timeout_sec,
        rate_limit_qps=base.rate_limit_qps,
        burst=base.burst,
        cache_ttl_sec=base.cache_ttl_sec,
        cost_model=base.cost_model,
        locale_mapping=base.locale_mapping,
        provider_config_digest=digest,
        notes=base.notes,
    )


def test_google_cse_provider_caches_and_dedupes_hits(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    calls = {"n": 0}

    def http_get(_url: str, *, params: Dict[str, Any], timeout: int) -> _FakeResponse:
        calls["n"] += 1
        assert timeout == 10
        assert params["q"] == "korea edtech revenue 2024"
        return _FakeResponse(
            200,
            {
                "items": [
                    {
                        "title": "T1",
                        "snippet": "S1",
                        "link": "http://Example.com/report?utm_source=x",
                    },
                    {
                        "title": "T2",
                        "snippet": "S2",
                        "link": "https://example.com/report",
                    },
                ]
            },
        )

    cfg = _provider_cfg(cache_ttl_sec=60)
    provider = GoogleCseProvider(
        cfg,
        api_key="test-key",
        search_engine_id="test-cx",
        artifact_store=store,
        http_get=http_get,
    )

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

    a = provider.search(finalized)
    b = provider.search(finalized)
    assert calls["n"] == 1
    assert a.serp_artifact_id == b.serp_artifact_id
    assert a.serp_digest == b.serp_digest
    assert len(a.hits) == 1  # deduped by canonical_url
    assert a.hits[0].canonical_url == "https://example.com/report"

    meta = store.get_meta(a.serp_artifact_id)
    assert meta is not None
    assert meta["kind"] == "search_v3_serp"

    p = Path(meta["file_path"])
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["provider_id"] == "GenericWebSearch"
    assert payload["query_request_digest"] == finalized.request_digest
    assert payload["query_artifact_id"] == finalized.query_artifact_id
    assert payload["raw_response"]["items"][0]["title"] == "T1"

    store.close()


@pytest.mark.parametrize(
    "status,expected_type,expected_retryable",
    [
        (429, "RateLimited", True),
        (401, "AuthFailed", False),
        (500, "UpstreamError", True),
    ],
)
def test_google_cse_provider_error_taxonomy(
    project_root: Path,
    tmp_path: Path,
    monkeypatch,
    status: int,
    expected_type: str,
    expected_retryable: bool,
) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    def http_get(_url: str, *, params: Dict[str, Any], timeout: int) -> _FakeResponse:
        return _FakeResponse(status, {}, text="err")

    cfg = _provider_cfg(cache_ttl_sec=0, rate_limit_qps=1000.0, burst=10)
    provider = GoogleCseProvider(
        cfg,
        api_key="test-key",
        search_engine_id="test-cx",
        artifact_store=store,
        http_get=http_get,
    )

    req = SearchQueryRequest(
        provider_id="GenericWebSearch",
        query="korea edtech revenue 2024",
        language="en",
        region="KR",
        top_k=8,
        timeout_sec=10,
        filters={},
        query_artifact_id="ART-q",
        request_digest="sha256:r",
    )

    with pytest.raises(ProviderError) as e:
        provider.search(req)
    assert e.value.type == expected_type
    assert e.value.retryable is expected_retryable
    assert e.value.http_status == status

    store.close()
