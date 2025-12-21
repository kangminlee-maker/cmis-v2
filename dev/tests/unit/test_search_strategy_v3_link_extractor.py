"""Search Strategy v3 LinkExtractor unit tests (SSV3-13)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

from cmis_core.search_v3.candidate import SearchRequest
from cmis_core.search_v3.document_fetcher import DocumentFetcher
from cmis_core.search_v3.link_extractor import LinkExtractorV1
from cmis_core.stores import ArtifactStore


class _FakeDocResponse:
    def __init__(self, *, status_code: int, headers: Dict[str, Any], body: bytes) -> None:
        self.status_code = int(status_code)
        self.headers = dict(headers)
        self._body = bytes(body)

    def iter_content(self, chunk_size: int = 65536) -> Iterable[bytes]:
        yield self._body


def _safe_dns(_host: str) -> list[str]:
    return ["93.184.216.34"]


def test_link_extractor_extracts_pdf_and_filters_bad_schemes(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    html = """
    <html><body>
      <p>IR 자료실</p>
      <a href="/ir/report_2024.pdf">2024 Annual Report (PDF)</a>
      <a href="javascript:void(0)">do not include</a>
      <a href="/privacy">Privacy Policy</a>
      <a href="/stats/table.html">통계 테이블 보기</a>
    </body></html>
    """.strip().encode("utf-8")

    def http_get_doc(_url: str, *, timeout: int) -> _FakeDocResponse:
        return _FakeDocResponse(status_code=200, headers={"Content-Type": "text/html; charset=utf-8"}, body=html)

    fetcher = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get_doc)
    doc = fetcher.fetch("https://example.com/news", timeout_sec=5)
    assert doc is not None

    extractor = LinkExtractorV1(artifact_store=store)
    req = SearchRequest(metric_id="MET-TAM", expected_unit=None, as_of="2024")
    cands = extractor.extract_links(doc, req, current_depth=1, domain_hint="edtech", max_candidates=20)

    assert all("javascript:" not in c.url.lower() for c in cands)
    assert all(c.parent_doc_id == doc.doc_id for c in cands)
    assert all(c.depth_from_serp == 1 for c in cands)

    pdfs = [c for c in cands if c.link_type == "pdf" and c.canonical_url.endswith("/ir/report_2024.pdf")]
    assert pdfs, "PDF 링크가 추출되어야 합니다"
    assert float(pdfs[0].relevance_score) >= 0.5

    store.close()


