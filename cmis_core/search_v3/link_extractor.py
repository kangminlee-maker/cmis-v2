"""Search Strategy v3 LinkExtractor v1 (SSV3-13).

목표:
- HTML 문서에서 hyperlink를 추출하고, 규칙 기반 relevance scoring을 수행합니다.
- Link Following(SSV3-14~16)에서 BFS 탐색 대상으로 사용할 LinkCandidate를 생성합니다.

주의:
- 이 모듈은 "온라인 변경"을 하지 않으며, 추출/점수화만 담당합니다.
- ref-only 원칙을 깨지 않도록, 원문 HTML/대량 텍스트는 LinkCandidate에 포함하지 않습니다.
  (필요한 경우 ART로 저장하고 ref로 연결하는 단계는 SSV3-16에서 처리)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlsplit

from cmis_core.search_v3.candidate import SearchRequest
from cmis_core.search_v3.document_fetcher import DocumentSnapshot
from cmis_core.search_v3.url_utils import canonicalize_url
from cmis_core.stores.artifact_store import ArtifactStore


@dataclass(frozen=True)
class LinkCandidate:
    """문서 내에서 발견된 유망한 링크.

    설계 원문: dev/docs/architecture/Search_Strategy_Design_v3.md (Section 7.3.1)
    """

    url: str
    canonical_url: str
    parent_doc_id: str
    anchor_text: str
    context_snippet: str
    relevance_score: float
    link_type: str
    depth_from_serp: int
    extraction_meta: Dict[str, Any] = field(default_factory=dict)


class LinkExtractorV1:
    """규칙 기반 LinkExtractor v1."""

    def __init__(self, *, artifact_store: ArtifactStore, max_snippet_chars: int = 200) -> None:
        self.artifacts = artifact_store
        self.max_snippet_chars = int(max(0, max_snippet_chars))

    def extract_links(
        self,
        doc: DocumentSnapshot,
        request: SearchRequest,
        *,
        current_depth: int,
        domain_hint: Optional[str] = None,
        max_candidates: int = 50,
    ) -> List[LinkCandidate]:
        """DocumentSnapshot에서 링크를 추출하고 score 기준으로 정렬된 후보를 반환합니다.

        Args:
            doc: DocumentSnapshot (meta artifact_id 포함)
            request: SearchRequest (as_of/year 등 일부 힌트에 사용)
            current_depth: SERP로부터의 현재 깊이(0=SERP 결과 문서)
            domain_hint: 도메인/키워드 힌트(선택)
            max_candidates: 반환 후보 수 제한
        """

        raw_html = self._read_raw_html_best_effort(doc)
        if raw_html is None:
            return []

        base_url = str(doc.url)
        parser = _AnchorParser(max_snippet_chars=self.max_snippet_chars)
        parser.feed(raw_html)
        links = parser.links

        # scoring + candidate build
        out: List[LinkCandidate] = []
        for href, anchor_text, snippet in links:
            abs_url = self._resolve_url(base_url, href)
            if not abs_url:
                continue
            canonical = canonicalize_url(abs_url)
            if not canonical:
                continue

            link_type, type_meta = _classify_link_type(abs_url, anchor_text=anchor_text)
            score, reason_codes = _score_relevance(
                url=abs_url,
                anchor_text=anchor_text,
                context_snippet=snippet,
                request=request,
                domain_hint=domain_hint,
            )

            out.append(
                LinkCandidate(
                    url=abs_url,
                    canonical_url=canonical,
                    parent_doc_id=str(doc.doc_id),
                    anchor_text=anchor_text,
                    context_snippet=snippet,
                    relevance_score=score,
                    link_type=link_type,
                    depth_from_serp=int(current_depth),
                    extraction_meta={
                        "reason_codes": reason_codes,
                        **type_meta,
                    },
                )
            )

        # dedupe by canonical_url, keep best score
        best: Dict[str, LinkCandidate] = {}
        for c in out:
            prev = best.get(c.canonical_url)
            if prev is None or float(c.relevance_score) > float(prev.relevance_score):
                best[c.canonical_url] = c

        sorted_cands = sorted(best.values(), key=lambda x: (-float(x.relevance_score), x.canonical_url))
        return sorted_cands[: max(0, int(max_candidates))]

    def _read_raw_html_best_effort(self, doc: DocumentSnapshot) -> Optional[str]:
        """DocumentSnapshot에서 raw HTML을 best-effort로 복원합니다."""

        # Only HTML documents are supported in v1.
        fmt = str((doc.readability or {}).get("format") or "")
        if fmt and fmt != "text/html":
            return None

        meta_path = self.artifacts.get_path(str(doc.artifact_id))
        if meta_path is None or not meta_path.exists():
            return None

        try:
            import json

            meta = json.loads(meta_path.read_text(encoding="utf-8") or "{}")
        except Exception:
            return None
        if not isinstance(meta, dict):
            return None

        raw_id = None
        artifacts = meta.get("artifacts") or {}
        if isinstance(artifacts, dict):
            raw_id = artifacts.get("raw_bytes_artifact_id")
        if not raw_id:
            return None

        raw_path = self.artifacts.get_path(str(raw_id))
        if raw_path is None or not raw_path.exists():
            return None

        raw_bytes = raw_path.read_bytes()
        charset = str((doc.readability or {}).get("charset") or "utf-8")
        try:
            return raw_bytes.decode(charset, errors="replace")
        except Exception:
            return raw_bytes.decode("utf-8", errors="replace")

    @staticmethod
    def _resolve_url(base_url: str, href: str) -> str:
        s = str(href or "").strip()
        if not s:
            return ""

        if s.startswith("#"):
            return ""

        low = s.lower()
        if low.startswith(("javascript:", "mailto:", "tel:")):
            return ""

        abs_url = urljoin(str(base_url), s)
        parts = urlsplit(abs_url)
        if parts.scheme.lower() not in {"http", "https"}:
            return ""
        if not parts.netloc:
            return ""
        return abs_url


class _AnchorParser(HTMLParser):
    """HTML에서 <a href>를 추출하는 최소 파서.

    - anchor_text는 <a> 내부 텍스트만 수집합니다.
    - context_snippet은 <a> 직전 텍스트 버퍼를 기반으로 best-effort로 제공합니다.
    """

    def __init__(self, *, max_snippet_chars: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_snippet_chars = int(max(0, max_snippet_chars))
        self._text_buf: str = ""
        self._in_a: bool = False
        self._a_href: Optional[str] = None
        self._a_text: List[str] = []
        self._a_ctx_before: str = ""
        self.links: List[Tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if str(tag).lower() != "a":
            return
        href = None
        for k, v in attrs:
            if str(k).lower() == "href":
                href = v
                break
        if not href:
            return
        self._in_a = True
        self._a_href = str(href)
        self._a_text = []
        self._a_ctx_before = self._text_buf[-self.max_snippet_chars :] if self.max_snippet_chars else ""

    def handle_endtag(self, tag: str) -> None:
        if str(tag).lower() != "a":
            return
        if not self._in_a or not self._a_href:
            self._in_a = False
            self._a_href = None
            self._a_text = []
            self._a_ctx_before = ""
            return

        anchor_text = _clean_text("".join(self._a_text))
        ctx = _clean_text(self._a_ctx_before)
        snippet = (ctx + (" " if (ctx and anchor_text) else "") + anchor_text).strip()
        if self.max_snippet_chars and len(snippet) > self.max_snippet_chars:
            snippet = snippet[: self.max_snippet_chars]
        self.links.append((self._a_href, anchor_text, snippet))

        self._in_a = False
        self._a_href = None
        self._a_text = []
        self._a_ctx_before = ""

    def handle_data(self, data: str) -> None:
        s = str(data or "")
        if self._in_a:
            self._a_text.append(s)
        else:
            # keep a rolling buffer for context
            self._text_buf = (self._text_buf + s)[-max(2000, self.max_snippet_chars) :]


def _clean_text(text: str) -> str:
    s = str(text or "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _classify_link_type(url: str, *, anchor_text: str) -> tuple[str, Dict[str, Any]]:
    u = str(url or "").lower()
    a = str(anchor_text or "").lower()
    meta: Dict[str, Any] = {"type_reasons": []}

    path = urlsplit(u).path or ""
    if re.search(r"\.pdf$", path):
        meta["type_reasons"].append("ext_pdf")
        return "pdf", meta
    if re.search(r"\.(xlsx?|csv)$", path):
        meta["type_reasons"].append("ext_spreadsheet")
        return "spreadsheet", meta

    if "download" in u or "download" in a:
        meta["type_reasons"].append("contains_download")
        return "download", meta
    if "report" in u or "report" in a or "보고서" in anchor_text:
        meta["type_reasons"].append("contains_report")
        return "report", meta
    if "table" in u or "statistics" in u or "stat" in u or "통계" in anchor_text:
        meta["type_reasons"].append("contains_table_or_stats")
        return "table", meta
    if "detail" in u or "detail" in a or "상세" in anchor_text:
        meta["type_reasons"].append("contains_detail")
        return "detail", meta

    return "general", meta


def _score_relevance(
    *,
    url: str,
    anchor_text: str,
    context_snippet: str,
    request: SearchRequest,
    domain_hint: Optional[str],
) -> tuple[float, List[str]]:
    """규칙 기반 relevance scoring (0~1)."""

    u = str(url or "").lower()
    a = str(anchor_text or "").lower()
    c = str(context_snippet or "").lower()
    reasons: List[str] = []
    score = 0.0

    # URL pattern bonus
    patterns: List[Tuple[str, float, str]] = [
        (r"\.pdf($|\?)", 0.35, "url_pdf"),
        (r"\.(xlsx?|csv)($|\?)", 0.35, "url_spreadsheet"),
        (r"/ir/", 0.2, "url_ir"),
        (r"/investor/", 0.2, "url_investor"),
        (r"/report/", 0.2, "url_report"),
        (r"/annual/", 0.15, "url_annual"),
        (r"/statistics/", 0.15, "url_statistics"),
        (r"download", 0.15, "url_download"),
    ]
    for pat, bonus, code in patterns:
        if re.search(pat, u):
            score += bonus
            reasons.append(code)

    # anchor/context keyword bonus (한국어/영어 혼합 최소 세트)
    kw_bonus: List[Tuple[str, float, str]] = [
        ("ir", 0.12, "kw_ir"),
        ("investor", 0.12, "kw_investor"),
        ("annual", 0.08, "kw_annual"),
        ("report", 0.1, "kw_report"),
        ("보고서", 0.1, "kw_report_ko"),
        ("자료", 0.06, "kw_materials_ko"),
        ("통계", 0.1, "kw_stats_ko"),
        ("다운로드", 0.08, "kw_download_ko"),
    ]
    for kw, bonus, code in kw_bonus:
        if kw in a:
            score += bonus
            reasons.append(f"{code}:anchor")
        if kw in c:
            score += bonus * 0.7
            reasons.append(f"{code}:context")

    # year matching
    year = None
    if request.as_of and str(request.as_of)[:4].isdigit():
        year = str(request.as_of)[:4]
    if year and (year in anchor_text or year in context_snippet):
        score += 0.2
        reasons.append("year_match")

    # domain hint
    if domain_hint:
        dh = str(domain_hint).strip().lower()
        if dh and (dh in a or dh in c or dh in u):
            score += 0.15
            reasons.append("domain_hint_match")

    # quality heuristics
    if len(anchor_text.strip()) >= 10:
        score += 0.08
        reasons.append("anchor_descriptive")

    # penalty: low value links
    if any(x in u for x in ["login", "signup", "register", "privacy", "terms", "cookie"]):
        score -= 0.3
        reasons.append("penalty_low_value")

    score = max(0.0, min(float(score), 1.0))
    return score, reasons


