"""Search Strategy v3 SearchKernelV1 runner unit tests (SSV3-09)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

from cmis_core.search_v3.candidate_extractor import RuleBasedCandidateExtractor
from cmis_core.search_v3.document_fetcher import DocumentFetcher
from cmis_core.search_v3.gate import GatePolicyEnforcerV1
from cmis_core.search_v3.generic_web_search import GoogleCseProvider
from cmis_core.search_v3.registry import ProviderConfig, StrategyRegistryV3
from cmis_core.search_v3.runner import SearchKernelV1
from cmis_core.search_v3.synthesizer import SynthesizerV1
from cmis_core.stores import ArtifactStore


class _FakeResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any], text: str = "") -> None:
        self.status_code = int(status_code)
        self._payload = payload
        self.text = text
        self.headers: Dict[str, Any] = {}

    def json(self) -> Dict[str, Any]:
        return self._payload


class _FakeDocResponse:
    def __init__(self, *, url: str, status_code: int, headers: Dict[str, Any], body: bytes) -> None:
        self.url = url
        self.status_code = int(status_code)
        self.headers = dict(headers)
        self._body = bytes(body)

    def iter_content(self, chunk_size: int = 65536) -> Iterable[bytes]:
        yield self._body


def _safe_dns(_host: str) -> list[str]:
    return ["93.184.216.34"]


def _provider_cfg() -> ProviderConfig:
    base = ProviderConfig(
        provider_id="GenericWebSearch",
        adapter="google_cse",
        api_key_ref="GOOGLE_API_KEY",
        default_timeout_sec=10,
        rate_limit_qps=1000.0,
        burst=10,
        cache_ttl_sec=60,
        cost_model=None,
        locale_mapping={},
        provider_config_digest="",
        notes={"search_engine_id_ref": "GOOGLE_SEARCH_ENGINE_ID"},
    )
    d = base.compute_digest()
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
        provider_config_digest=d,
        notes=base.notes,
    )


def test_kernel_reporting_strict_replan_then_gate_met(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    # registry YAML with fetch_top_k=1 to force replan (+1) to fetch the second doc
    reg_yaml = tmp_path / "search_strategy_registry_v3_test.yaml"
    reg_yaml.write_text(
        """---
registry_version: 3
phases_allowed: [generic_web]
providers:
  GenericWebSearch:
    adapter: google_cse
    api_key_ref: GOOGLE_API_KEY
metrics:
  MET-TAM:
    reporting_strict:
      phases:
        - phase_id: generic_web
          providers: [GenericWebSearch]
          query_templates: ["{domain} {region} market size {year}"]
          retrieval:
            serp_top_k: 2
            fetch_top_k: 1
          filters: {}
""",
        encoding="utf-8",
    )

    registry = StrategyRegistryV3(reg_yaml)
    registry.compile()

    def http_get_serp(_url: str, *, params: Dict[str, Any], timeout: int) -> _FakeResponse:
        # always return two hits
        return _FakeResponse(
            200,
            {
                "items": [
                    {"title": "R1", "snippet": "S1", "link": "https://a.example.com/doc1"},
                    {"title": "R2", "snippet": "S2", "link": "https://b.example.com/doc2"},
                ]
            },
        )

    provider = GoogleCseProvider(
        _provider_cfg(),
        api_key="test-key",
        search_engine_id="test-cx",
        artifact_store=store,
        http_get=http_get_serp,
    )

    docs: Dict[str, _FakeDocResponse] = {
        "https://a.example.com/doc1": _FakeDocResponse(
            url="https://a.example.com/doc1",
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=b"<html><body>\xec\x8b\x9c\xec\x9e\xa5 \xea\xb7\x9c\xeb\xaa\xa8 1000\xec\x96\xb5\xec\x9b\x90 (2024)</body></html>",
        ),
        "https://b.example.com/doc2": _FakeDocResponse(
            url="https://b.example.com/doc2",
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=b"<html><body>\xec\x8b\x9c\xec\x9e\xa5 \xea\xb7\x9c\xeb\xaa\xa8 1100\xec\x96\xb5\xec\x9b\x90 (2024)</body></html>",
        ),
    }

    def http_get_doc(url: str, *, timeout: int) -> _FakeDocResponse:
        return docs[url]

    fetcher = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get_doc)
    extractor = RuleBasedCandidateExtractor(artifact_store=store)
    synthesizer = SynthesizerV1()
    gate = GatePolicyEnforcerV1()

    kernel = SearchKernelV1(registry=registry, provider=provider, fetcher=fetcher, extractor=extractor, synthesizer=synthesizer, gate=gate)

    result = kernel.fetch_evidence(
        metric_id="MET-TAM",
        policy_ref="reporting_strict",
        template_vars={"domain": "edtech", "year": 2024},
        expected_unit="KRW",
        as_of="2024",
        language="ko",
        region="KR",
        budget_max_queries=1,
        budget_max_fetches=5,
    )

    assert len(result.evidence_records) == 1
    assert len(result.plan_digest_chain) >= 2  # PlanRevised occurred

    event_types = [e["type"] for e in result.events]
    assert "PlanBuilt" in event_types
    assert "PlanRevised" in event_types
    assert "EvidenceCommitted" in event_types
    assert "RunCompleted" in event_types

    store.close()
