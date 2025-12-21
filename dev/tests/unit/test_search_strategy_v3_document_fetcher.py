"""Search Strategy v3 DocumentFetcher unit tests (SSV3-05)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pytest

from cmis_core.digest import sha256_digest
from cmis_core.search_v3.document_fetcher import DocumentFetchError, DocumentFetcher
from cmis_core.search_v3.link_extractor import LinkExtractorV1
from cmis_core.search_v3.candidate import SearchRequest
from cmis_core.stores import ArtifactStore


class _FakeResponse:
    def __init__(self, *, url: str, status_code: int, headers: Optional[Dict[str, Any]] = None, body: bytes = b"") -> None:
        self.url = url
        self.status_code = int(status_code)
        self.headers = dict(headers or {})
        self._body = bytes(body)

    def iter_content(self, chunk_size: int = 65536) -> Iterable[bytes]:
        # single-chunk is enough for unit tests
        yield self._body


def _safe_dns(_host: str) -> list[str]:
    return ["93.184.216.34"]  # example.com (public)


def test_document_fetcher_blocks_localhost_ssrf(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    f = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=lambda *_a, **_k: None)
    with pytest.raises(DocumentFetchError):
        f.fetch("http://127.0.0.1/", timeout_sec=5)

    store.close()


def test_document_fetcher_blocks_denylisted_domain(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    f = DocumentFetcher(
        artifact_store=store,
        dns_resolver=_safe_dns,
        http_get=lambda *_a, **_k: None,
        deny_domains=["example.com"],
    )
    with pytest.raises(DocumentFetchError):
        f.fetch("https://example.com/report", timeout_sec=5)

    store.close()


def test_document_fetcher_redirect_limit_enforced(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    mapping: Dict[str, _FakeResponse] = {
        "https://example.com/a": _FakeResponse(
            url="https://example.com/a",
            status_code=302,
            headers={"Location": "/b"},
        ),
        "https://example.com/b": _FakeResponse(
            url="https://example.com/b",
            status_code=302,
            headers={"Location": "/c"},
        ),
        "https://example.com/c": _FakeResponse(
            url="https://example.com/c",
            status_code=302,
            headers={"Location": "/d"},
        ),
        "https://example.com/d": _FakeResponse(
            url="https://example.com/d",
            status_code=200,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            body=b"ok",
        ),
    }

    def http_get(url: str, *, timeout: int) -> _FakeResponse:
        return mapping[url]

    f = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get, max_redirects=2)
    with pytest.raises(DocumentFetchError):
        f.fetch("https://example.com/a", timeout_sec=5)

    store.close()


def test_document_fetcher_max_bytes_enforced(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    def http_get(url: str, *, timeout: int) -> _FakeResponse:
        return _FakeResponse(
            url=url,
            status_code=200,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            body=b"x" * 20,
        )

    f = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get, max_bytes=10)
    with pytest.raises(DocumentFetchError):
        f.fetch("https://example.com/large", timeout_sec=5)

    store.close()


def test_document_fetcher_mime_allowlist_enforced(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    def http_get(url: str, *, timeout: int) -> _FakeResponse:
        return _FakeResponse(
            url=url,
            status_code=200,
            headers={"Content-Type": "application/octet-stream"},
            body=b"bin",
        )

    f = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get)
    with pytest.raises(DocumentFetchError):
        f.fetch("https://example.com/bin", timeout_sec=5)

    store.close()


def test_document_fetcher_doc_id_content_addressed(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    html = b"<html><body>Hello 123</body></html>"

    def http_get(url: str, *, timeout: int) -> _FakeResponse:
        return _FakeResponse(
            url=url,
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=html,
        )

    f = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get, max_bytes=1000)
    snap = f.fetch("https://example.com/page", timeout_sec=5)
    assert snap is not None
    assert snap.doc_id.startswith("DOC-")
    assert snap.content_digest.startswith("sha256:")

    # content-addressed: DOC-<first 16 hex of normalized_text_digest>
    expected_doc_id = f"DOC-{snap.content_digest.split('sha256:', 1)[1][:16]}"
    assert snap.doc_id == expected_doc_id

    meta = store.get_meta(snap.artifact_id)
    assert meta is not None
    payload = json.loads(Path(meta["file_path"]).read_text(encoding="utf-8"))
    assert payload["doc_id"] == snap.doc_id
    assert payload["digests"]["normalized_text_digest"] == snap.content_digest
    assert payload["digests"]["raw_bytes_digest"].startswith("sha256:")

    # normalized text digest should match sha256(normalized_text)
    text_aid = payload["artifacts"]["text_artifact_id"]
    text_meta = store.get_meta(text_aid)
    assert text_meta is not None
    text = Path(text_meta["file_path"]).read_text(encoding="utf-8").strip()
    assert text == "Hello 123"
    assert snap.content_digest == sha256_digest(text.encode("utf-8"))

    store.close()


def test_document_fetcher_records_depth_and_parent(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    mapping: Dict[str, _FakeResponse] = {
        "https://example.com/root": _FakeResponse(
            url="https://example.com/root",
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=b"<html><body><a href='/child'>child</a></body></html>",
        ),
        "https://example.com/child": _FakeResponse(
            url="https://example.com/child",
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=b"<html><body>child page</body></html>",
        ),
    }

    def http_get(url: str, *, timeout: int) -> _FakeResponse:
        return mapping[url]

    f = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get, max_bytes=1000)
    root = f.fetch("https://example.com/root", timeout_sec=5, depth=0)
    assert root is not None
    assert root.depth_from_serp == 0
    assert root.parent_doc_id is None
    assert root.link_path == [root.doc_id]

    child = f.fetch("https://example.com/child", timeout_sec=5, depth=1, parent_doc_id=root.doc_id)
    assert child is not None
    assert child.depth_from_serp == 1
    assert child.parent_doc_id == root.doc_id
    assert child.link_path == [root.doc_id, child.doc_id]

    store.close()


def test_document_fetcher_fetch_with_links_bfs_tracks_depth_and_visited(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)

    mapping: Dict[str, _FakeResponse] = {
        "https://example.com/root": _FakeResponse(
            url="https://example.com/root",
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=b"<html><body><a href='/child'>2024 Annual Report (PDF)</a><a href='/root'>self</a></body></html>",
        ),
        "https://example.com/child": _FakeResponse(
            url="https://example.com/child",
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=b"<html><body><a href='/root'>back</a></body></html>",
        ),
    }

    def http_get(url: str, *, timeout: int) -> _FakeResponse:
        return mapping[url]

    f = DocumentFetcher(artifact_store=store, dns_resolver=_safe_dns, http_get=http_get, max_bytes=1000)
    extractor = LinkExtractorV1(artifact_store=store)
    req = SearchRequest(metric_id="MET-TAM", expected_unit=None, as_of="2024")

    docs = f.fetch_with_links(
        ["https://example.com/root"],
        timeout_sec=5,
        max_depth=1,
        link_extractor=extractor,
        request=req,
        max_fetches=10,
        max_links_per_doc=5,
        min_relevance_score=0.0,
        same_domain_only=True,
    )
    assert len(docs) == 2
    root = docs[0]
    child = docs[1]

    assert root.depth_from_serp == 0
    assert root.parent_doc_id is None
    assert root.link_path == [root.doc_id]

    assert child.depth_from_serp == 1
    assert child.parent_doc_id == root.doc_id
    assert child.link_path == [root.doc_id, child.doc_id]

    store.close()
