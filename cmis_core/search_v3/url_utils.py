"""URL canonicalization utilities (Search Strategy v3).

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 3.4)
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_DROP_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
}


def canonicalize_url(url: str) -> str:
    """URL을 결정적으로 정규화합니다.

    Rules (best-effort):
    - fragment 제거
    - utm_* / known tracking params 제거
    - query params는 (key, value) 정렬 후 재구성
    - scheme: http/https면 https로 승격(가능한 범위)
    - netloc 소문자화
    - trailing slash 규칙 통일(/는 유지, 그 외는 제거)
    """

    s = str(url or "").strip()
    if s == "":
        return ""

    parts = urlsplit(s)
    scheme = parts.scheme.lower()
    if scheme in {"http", "https"}:
        scheme = "https"

    netloc = parts.netloc.lower()
    path = parts.path or ""

    # normalize trailing slash
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    # drop fragment
    fragment = ""

    # normalize query
    q = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        k_lower = str(k).lower()
        if k_lower.startswith("utm_"):
            continue
        if k_lower in _DROP_QUERY_KEYS:
            continue
        q.append((k, v))
    q.sort(key=lambda kv: (kv[0], kv[1]))
    query = urlencode(q, doseq=True)

    return urlunsplit((scheme, netloc, path, query, fragment))
