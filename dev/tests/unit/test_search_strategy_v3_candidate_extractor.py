"""Search Strategy v3 CandidateExtractor unit tests (SSV3-06)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from cmis_core.search_v3.candidate import SearchRequest
from cmis_core.search_v3.candidate_extractor import RuleBasedCandidateExtractor
from cmis_core.search_v3.document_fetcher import DocumentFetcher
from cmis_core.stores import ArtifactStore


class _FakeResponse:
    def __init__(self, *, url: str, status_code: int, headers: Optional[Dict[str, Any]] = None, body: bytes = b"") -> None:
        self.url = url
        self.status_code = int(status_code)
        self.headers = dict(headers or {})
        self._body = bytes(body)

    def iter_content(self, chunk_size: int = 65536) -> Iterable[bytes]:
        yield self._body


def _safe_dns(_host: str) -> list[str]:
    return ["93.184.216.34"]


def test_candidate_extractor_extracts_krw_with_quote_ref(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    html = "<html><body>시장 규모는 2900억원 (2024년 기준)입니다.</body></html>".encode("utf-8")

    def http_get(url: str, *, timeout: int) -> _FakeResponse:
        return _FakeResponse(url=url, status_code=200, headers={"Content-Type": "text/html; charset=utf-8"}, body=html)

    fetcher = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get)
    doc = fetcher.fetch("https://example.com/report", timeout_sec=5)
    assert doc is not None

    extractor = RuleBasedCandidateExtractor(artifact_store=store)
    req = SearchRequest(metric_id="MET-TAM", expected_unit="KRW", as_of="2024")
    cands = extractor.extract(doc, req)

    assert len(cands) >= 1
    c = cands[0]
    assert c.unit == "KRW"
    assert c.value == 290_000_000_000
    assert c.as_of == "2024"
    assert c.independence_key.startswith("host:example.com|sha256:")
    assert c.span_quote_ref is not None
    assert c.span_quote_ref["artifact_id"].startswith("ART-")
    assert c.span_quote_ref["digest"].startswith("sha256:")

    quote_meta = store.get_meta(c.span_quote_ref["artifact_id"])
    assert quote_meta is not None
    quote_text = Path(quote_meta["file_path"]).read_text(encoding="utf-8")
    assert "2900억원" in quote_text

    store.close()


def test_candidate_extractor_extracts_usd_scaled(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    html = "<html><body>The market is worth $500M in 2024.</body></html>".encode("utf-8")

    def http_get(url: str, *, timeout: int) -> _FakeResponse:
        return _FakeResponse(url=url, status_code=200, headers={"Content-Type": "text/html; charset=utf-8"}, body=html)

    fetcher = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get)
    doc = fetcher.fetch("https://example.com/report2", timeout_sec=5)
    assert doc is not None

    extractor = RuleBasedCandidateExtractor(artifact_store=store)
    req = SearchRequest(metric_id="MET-TAM", expected_unit="USD", as_of="2024")
    cands = extractor.extract(doc, req)

    assert len(cands) >= 1
    c = cands[0]
    assert c.unit == "USD"
    assert c.value == 500_000_000
    assert c.as_of == "2024"
    assert c.span_quote_ref is not None

    store.close()
