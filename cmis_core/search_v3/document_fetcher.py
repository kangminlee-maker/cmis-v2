"""DocumentFetcher with safety/compliance guardrails (SSV3-05).

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 4)

Production-minimal v1:
- SSRF 방지(DNS/IP 검증, loopback/private/reserved 차단)
- scheme allowlist(http/https), port allowlist(80/443)
- redirect 제한 + redirect 대상도 동일하게 검증
- MIME allowlist(text/html, text/plain, application/pdf)
- timeout/max_bytes 강제
- DOC id: content-addressed (DOC-<short_hash(normalized_text_digest)>)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import ipaddress
import re
import socket
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlsplit

from cmis_core.digest import sha256_digest
from cmis_core.search_v3.url_utils import canonicalize_url
from cmis_core.search_v3.link_selector import LinkSelectionConfig, LinkSelectionPolicyV1
from cmis_core.stores.artifact_store import ArtifactStore


class DocumentFetchError(ValueError):
    """문서 fetch/검증 실패."""


@dataclass(frozen=True)
class DocumentSnapshot:
    doc_id: str  # DOC-*
    url: str
    canonical_url: str
    artifact_id: str  # ART-* (meta JSON; raw/text artifacts are linked inside meta)
    raw_bytes_digest: Optional[str]
    content_digest: str  # sha256:... (normalized_text digest)
    fetched_at: str  # ISO8601
    http_meta: Dict[str, Any] = field(default_factory=dict)
    readability: Dict[str, Any] = field(default_factory=dict)
    # Link-following lineage (SSV3-14)
    depth_from_serp: int = 0
    parent_doc_id: Optional[str] = None
    link_path: List[str] = field(default_factory=list)


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _short_hash_from_sha256_digest(digest: str, *, length: int = 16) -> str:
    s = str(digest or "")
    if s.startswith("sha256:"):
        s = s.split("sha256:", 1)[1]
    s = re.sub(r"[^0-9a-fA-F]", "", s)
    return s[: int(length)]


def _default_dns_resolver(host: str) -> List[str]:
    ips: set[str] = set()
    for family, _socktype, _proto, _canonname, sockaddr in socket.getaddrinfo(host, None):
        try:
            if family == socket.AF_INET:
                ips.add(str(sockaddr[0]))
            elif family == socket.AF_INET6:
                ips.add(str(sockaddr[0]))
        except Exception:
            continue
    return sorted(ips)


def _is_ip_allowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # Block everything that is not globally routable.
    # ipaddress has is_global for both IPv4/IPv6.
    return bool(getattr(ip, "is_global", False))


def _parse_content_type(value: Optional[str]) -> str:
    if not value:
        return ""
    return str(value).split(";", 1)[0].strip().lower()


def _extract_charset(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    m = re.search(r"charset=([A-Za-z0-9._-]+)", str(value), flags=re.IGNORECASE)
    return str(m.group(1)) if m else None


class DocumentFetcher:
    """URL -> DocumentSnapshot (ART 저장 포함)."""

    def __init__(
        self,
        *,
        artifact_store: ArtifactStore,
        dns_resolver: Optional[Callable[[str], List[str]]] = None,
        http_get: Optional[Callable[..., Any]] = None,
        allow_mime_types: Optional[Iterable[str]] = None,
        deny_domains: Optional[List[str]] = None,
        max_redirects: int = 5,
        max_bytes: int = 5_000_000,
        allowed_ports: Optional[Iterable[int]] = None,
    ) -> None:
        self.artifacts = artifact_store
        self.dns_resolver = dns_resolver or _default_dns_resolver
        self.http_get = http_get

        self.allow_mime_types = {str(x).lower() for x in (allow_mime_types or {"text/html", "text/plain", "application/pdf"})}
        self.deny_domains = [str(d).lower() for d in (deny_domains or [])]
        self.max_redirects = int(max_redirects)
        self.max_bytes = int(max_bytes)
        self.allowed_ports = set(int(p) for p in (allowed_ports or {80, 443}))

    def fetch(
        self,
        url: str,
        timeout_sec: int,
        *,
        depth: int = 0,
        parent_doc_id: Optional[str] = None,
        link_path_prefix: Optional[List[str]] = None,
    ) -> Optional[DocumentSnapshot]:
        """문서를 fetch하여 ART로 저장하고 DocumentSnapshot을 반환합니다.

        Args:
            url: 대상 URL
            timeout_sec: HTTP timeout (초)
            depth: SERP 기준 depth (0=SERP hit 문서, 1=1차 링크, ...)
            parent_doc_id: 링크를 따라온 경우, parent 문서의 doc_id
        """

        start_url = str(url)
        current_url = start_url
        redirects = 0

        while True:
            self._validate_url(current_url)
            resp = self._http_get(current_url, timeout=int(timeout_sec))

            status = int(getattr(resp, "status_code", 0) or 0)
            headers = dict(getattr(resp, "headers", {}) or {})

            if status in {301, 302, 303, 307, 308} and "Location" in headers:
                if redirects >= self.max_redirects:
                    raise DocumentFetchError("too many redirects")
                loc = str(headers.get("Location") or "")
                next_url = urljoin(current_url, loc)
                redirects += 1
                current_url = next_url
                continue

            if status != 200:
                raise DocumentFetchError(f"http status {status}")

            content_type_raw = headers.get("Content-Type") or headers.get("content-type")
            mime = _parse_content_type(str(content_type_raw) if content_type_raw is not None else None)
            if mime not in self.allow_mime_types:
                raise DocumentFetchError(f"mime not allowed: {mime}")

            raw_bytes = b"".join(self._iter_bytes(resp))
            raw_digest = sha256_digest(raw_bytes)

            normalized_text, readability = self._extract_and_normalize_text(raw_bytes, mime, content_type=str(content_type_raw or ""))
            # PDF 등에서 텍스트 추출이 실패(빈 문자열)하면 content-addressing 충돌을 방지하기 위해
            # raw_bytes_digest를 기반으로 fallback(결정적) 처리합니다.
            if normalized_text == "":
                readability = dict(readability or {})
                readability["empty_text_fallback"] = True
                normalized_text = raw_digest
            content_digest = sha256_digest(normalized_text.encode("utf-8"))
            doc_id = f"DOC-{_short_hash_from_sha256_digest(content_digest)}"

            canonical_url = canonicalize_url(current_url)

            raw_artifact_id = self.artifacts.put_bytes(
                raw_bytes,
                kind="search_v3_doc_raw",
                mime_type=mime,
                original_filename=_guess_filename_for_mime(current_url, mime),
                meta={"url": current_url, "canonical_url": canonical_url, "doc_id": doc_id, "digest": raw_digest},
                dedupe=False,
            )
            text_artifact_id = self.artifacts.put_text(
                normalized_text,
                kind="search_v3_doc_text",
                meta={"url": current_url, "canonical_url": canonical_url, "doc_id": doc_id, "digest": content_digest},
            )

            depth_i = int(depth)
            parent_id = (str(parent_doc_id) if parent_doc_id is not None else None)
            prefix = [str(x) for x in (link_path_prefix or []) if str(x).strip()]
            if prefix:
                link_path = prefix + [doc_id]
            elif parent_id:
                link_path = [parent_id, doc_id]
            else:
                link_path = [doc_id]

            meta_artifact_id = self.artifacts.put_json(
                {
                    "doc_id": doc_id,
                    "url": current_url,
                    "canonical_url": canonical_url,
                    "depth_from_serp": depth_i,
                    "parent_doc_id": parent_id,
                    "link_path": list(link_path),
                    "fetched_at": _utc_now_iso_z(),
                    "http": {
                        "status_code": status,
                        "content_type": str(content_type_raw or ""),
                        "headers_subset": _headers_subset(headers),
                        "redirects": redirects,
                    },
                    "artifacts": {
                        "raw_bytes_artifact_id": raw_artifact_id,
                        "text_artifact_id": text_artifact_id,
                    },
                    "digests": {
                        "raw_bytes_digest": raw_digest,
                        "normalized_text_digest": content_digest,
                    },
                    "readability": readability,
                },
                kind="search_v3_doc",
            )

            return DocumentSnapshot(
                doc_id=doc_id,
                url=current_url,
                canonical_url=canonical_url,
                artifact_id=meta_artifact_id,
                raw_bytes_digest=raw_digest,
                content_digest=content_digest,
                fetched_at=_utc_now_iso_z(),
                http_meta={
                    "status_code": status,
                    "content_type": str(content_type_raw or ""),
                    "redirects": redirects,
                    "raw_bytes_artifact_id": raw_artifact_id,
                    "text_artifact_id": text_artifact_id,
                },
                readability=readability,
                depth_from_serp=depth_i,
                parent_doc_id=parent_id,
                link_path=list(link_path),
            )

    # --------------------------
    # Guards
    # --------------------------

    def _validate_url(self, url: str) -> None:
        parts = urlsplit(str(url))
        scheme = (parts.scheme or "").lower()
        if scheme not in {"http", "https"}:
            raise DocumentFetchError("scheme not allowed")

        host = (parts.hostname or "").strip()
        if host == "":
            raise DocumentFetchError("missing hostname")

        host_l = host.lower()
        if host_l in {"localhost"}:
            raise DocumentFetchError("ssrf blocked: localhost")

        if any(host_l == d or host_l.endswith(f".{d}") for d in self.deny_domains):
            raise DocumentFetchError("denylisted domain")

        port = int(parts.port or (443 if scheme == "https" else 80))
        if port not in self.allowed_ports:
            raise DocumentFetchError(f"port not allowed: {port}")

        # If hostname is a literal IP, validate it directly
        try:
            ip = ipaddress.ip_address(host_l)
            if not _is_ip_allowed(ip):
                raise DocumentFetchError("ssrf blocked: non-global ip")
            return
        except ValueError:
            pass

        # DNS/IP validation
        ips = self.dns_resolver(host_l)
        if not ips:
            raise DocumentFetchError("dns resolution failed")
        for ip_s in ips:
            try:
                ip = ipaddress.ip_address(ip_s)
            except ValueError:
                raise DocumentFetchError("dns resolution returned invalid ip")
            if not _is_ip_allowed(ip):
                raise DocumentFetchError("ssrf blocked: non-global ip")

    # --------------------------
    # HTTP
    # --------------------------

    def _http_get(self, url: str, *, timeout: int) -> Any:
        if self.http_get is not None:
            return self.http_get(url, timeout=timeout)

        try:
            import requests  # type: ignore
        except Exception as e:  # pragma: no cover
            raise DocumentFetchError(f"requests import failed: {e}")

        return requests.get(url, timeout=timeout, allow_redirects=False, stream=True)

    def _iter_bytes(self, resp: Any) -> Iterable[bytes]:
        total = 0
        # requests.Response.iter_content exists; fake response in tests can implement too.
        if hasattr(resp, "iter_content"):
            it = resp.iter_content(chunk_size=65536)
        else:
            data = getattr(resp, "content", b"") or b""
            it = [bytes(data)]

        for chunk in it:
            b = bytes(chunk or b"")
            total += len(b)
            if total > self.max_bytes:
                raise DocumentFetchError("max_bytes exceeded")
            yield b

    # --------------------------
    # Text extraction
    # --------------------------

    def _extract_and_normalize_text(self, raw: bytes, mime: str, *, content_type: str) -> tuple[str, Dict[str, Any]]:
        if mime == "text/plain":
            charset = _extract_charset(content_type) or "utf-8"
            text = raw.decode(charset, errors="replace")
            return _normalize_text(text), {"format": "text/plain", "charset": charset}

        if mime == "text/html":
            charset = _extract_charset(content_type) or "utf-8"
            html = raw.decode(charset, errors="replace")
            text = _html_to_text(html)
            return _normalize_text(text), {"format": "text/html", "charset": charset}

        if mime == "application/pdf":
            text = _pdf_to_text_best_effort(raw)
            return _normalize_text(text), {"format": "application/pdf"}

        raise DocumentFetchError(f"unsupported mime: {mime}")

    # --------------------------
    # Link following (SSV3-14)
    # --------------------------

    def fetch_with_links(
        self,
        initial_urls: List[str],
        *,
        timeout_sec: int,
        max_depth: int,
        link_extractor: Any,
        link_selector: Optional[Any] = None,
        event_sink: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        request: Any,
        domain_hint: Optional[str] = None,
        max_fetches: int = 20,
        max_links_per_doc: int = 3,
        min_relevance_score: float = 0.6,
        same_domain_only: bool = False,
    ) -> List[DocumentSnapshot]:
        """BFS로 링크를 따라가며 문서를 수집합니다.

        이 메서드는 SSV3-15(LinkSelectionPolicy) 없이도 작동할 수 있도록
        안전한 기본 선택 규칙(top-N + threshold + visited)을 포함합니다.

        Args:
            initial_urls: SERP 결과 URL 목록 (depth=0)
            timeout_sec: 각 fetch의 timeout
            max_depth: 최대 탐색 depth (0이면 initial_urls만 fetch)
            link_extractor: extract_links(doc, request, current_depth=..., domain_hint=..., max_candidates=...)를 제공하는 객체
            request: 링크 relevance scoring에 사용할 request (SearchRequest 등)
            domain_hint: 도메인/키워드 힌트(선택)
            max_fetches: 총 fetch budget (문서 개수 상한)
            max_links_per_doc: 문서 당 따라갈 링크 수 상한
            min_relevance_score: 링크 선택 최소 점수
            same_domain_only: true면 parent 문서와 동일 도메인 링크만 follow
        """

        max_d = max(0, int(max_depth))
        budget = max(0, int(max_fetches))
        per_doc = max(0, int(max_links_per_doc))
        thr = float(min_relevance_score)

        visited: Set[str] = set()
        q: Deque[Tuple[str, int, Optional[str], List[str]]] = deque()
        out: List[DocumentSnapshot] = []
        selected_links_total = 0

        for url in list(initial_urls or []):
            u = str(url or "").strip()
            if not u:
                continue
            canon = canonicalize_url(u)
            if not canon or canon in visited:
                continue
            visited.add(canon)
            q.append((u, 0, None, []))

        while q and len(out) < budget:
            url, depth, parent_doc_id, parent_path = q.popleft()
            if int(depth) > max_d:
                continue

            snap = self.fetch(
                url,
                timeout_sec=int(timeout_sec),
                depth=int(depth),
                parent_doc_id=parent_doc_id,
                link_path_prefix=list(parent_path),
            )
            if snap is None:
                continue
            out.append(snap)

            if int(depth) >= max_d:
                continue

            # extract candidates from HTML only (best-effort)
            try:
                candidates = link_extractor.extract_links(
                    snap,
                    request,
                    current_depth=int(depth) + 1,
                    domain_hint=domain_hint,
                    max_candidates=50,
                )
            except TypeError:
                # compatible fallback for different extractor signatures
                candidates = link_extractor.extract_links(snap, request, current_depth=int(depth) + 1)
            except Exception:
                candidates = []

            # LinkExtracted event: store full candidates as ART, emit only ref/summary
            links_artifact_id = self.artifacts.put_json(
                {
                    "schema_version": 1,
                    "parent_doc_id": snap.doc_id,
                    "parent_canonical_url": snap.canonical_url,
                    "depth_from_serp": int(depth),
                    "candidates": [
                        {
                            "url": str(getattr(c, "url", "") or ""),
                            "canonical_url": str(getattr(c, "canonical_url", "") or ""),
                            "relevance_score": float(getattr(c, "relevance_score", 0.0) or 0.0),
                            "link_type": str(getattr(c, "link_type", "") or ""),
                        }
                        for c in (candidates or [])
                        if c is not None
                    ],
                },
                kind="search_v3_links",
            )
            if event_sink is not None:
                event_sink(
                    "LinkExtracted",
                    {
                        "parent_doc_id": snap.doc_id,
                        "parent_canonical_url": snap.canonical_url,
                        "depth_from_serp": int(depth),
                        "links_artifact_id": links_artifact_id,
                        "candidate_count": (len(candidates) if isinstance(candidates, list) else 0),
                    },
                )

            cfg = LinkSelectionConfig(max_links_per_doc=per_doc, min_relevance_score=thr, same_domain_only=bool(same_domain_only))
            selector = link_selector or LinkSelectionPolicyV1()
            try:
                selected = selector.select_links(candidates, visited=visited, parent_url=str(snap.canonical_url or snap.url), config=cfg)
            except Exception:
                selected = []
            selected_links_total += len(selected)

            for c in selected:
                next_url = str(getattr(c, "url", "") or getattr(c, "canonical_url", "") or "").strip()
                next_canon = str(getattr(c, "canonical_url", "") or "").strip() or canonicalize_url(next_url)
                if not next_url or not next_canon or next_canon in visited:
                    continue
                visited.add(next_canon)
                if event_sink is not None:
                    try:
                        score = float(getattr(c, "relevance_score", 0.0) or 0.0)
                    except Exception:
                        score = 0.0
                    event_sink(
                        "LinkFollowed",
                        {
                            "from_doc_id": snap.doc_id,
                            "to_url": next_url,
                            "to_canonical_url": next_canon,
                            "depth_from_serp": int(depth) + 1,
                            "relevance_score": score,
                            "link_type": str(getattr(c, "link_type", "") or ""),
                        },
                    )
                q.append((next_url, int(depth) + 1, str(snap.doc_id), list(snap.link_path)))

        if event_sink is not None:
            event_sink(
                "DepthExplorationCompleted",
                {
                    "max_depth": int(max_d),
                    "documents_fetched": len(out),
                    "visited_count": len(visited),
                    "selected_links": int(selected_links_total),
                },
            )
        return out


def _headers_subset(headers: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    allow = {"content-type", "content-length", "last-modified", "etag", "cache-control"}
    for k, v in (headers or {}).items():
        k_l = str(k).lower()
        if k_l in allow:
            out[k_l] = str(v)
    return out


def _guess_filename_for_mime(url: str, mime: str) -> str:
    # Use URL path suffix if present, otherwise use mime-based fallback.
    p = urlsplit(str(url)).path or ""
    name = p.rsplit("/", 1)[-1].strip()
    if "." in name and len(name) <= 120:
        return name
    if mime == "text/html":
        return "document.html"
    if mime == "text/plain":
        return "document.txt"
    if mime == "application/pdf":
        return "document.pdf"
    return "document.bin"


def _normalize_text(text: str) -> str:
    s = str(text or "")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


class _HTMLTextExtractor:
    def __init__(self) -> None:
        self.parts: List[str] = []

    def feed(self, html: str) -> None:
        # ultra-minimal HTML "parsing": remove script/style blocks, then strip tags.
        # This is deterministic but not perfect; extractor quality is handled in SSV3-06.
        h = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        h = re.sub(r"(?is)<style.*?>.*?</style>", " ", h)
        # Replace tags with whitespace
        h = re.sub(r"(?is)<[^>]+>", " ", h)
        self.parts.append(h)

    def get_text(self) -> str:
        return " ".join(self.parts)


def _html_to_text(html: str) -> str:
    ex = _HTMLTextExtractor()
    ex.feed(html)
    return ex.get_text()


def _pdf_to_text_best_effort(raw_pdf: bytes) -> str:
    # pypdf는 선택적 의존성으로 유지하되, production에서는 requirements로 pinning 합니다.
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""

    try:
        import io

        reader = PdfReader(io.BytesIO(raw_pdf))
        parts: List[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t:
                parts.append(t)
        return "\n".join(parts)
    except Exception:
        return ""
