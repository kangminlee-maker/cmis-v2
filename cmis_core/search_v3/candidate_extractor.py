"""Rule-based CandidateExtractor (SSV3-06).

Production-minimal v1 목표:
- 문서(정규화 텍스트)에서 수치/단위/기간 후보를 규칙 기반으로 추출
- ref-only: 인용 텍스트는 ART로 저장하고 span_quote_ref로만 참조
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from cmis_core.digest import sha256_digest
from cmis_core.search_v3.candidate import CandidateValue, SearchRequest, compute_independence_key
from cmis_core.search_v3.document_fetcher import DocumentSnapshot
from cmis_core.stores.artifact_store import ArtifactStore


_YEAR_RE = re.compile(r"(19|20)\d{2}")


class RuleBasedCandidateExtractor:
    """규칙 기반 CandidateExtractor (v1)."""

    extractor_id = "RuleBasedCandidateExtractor@v1"

    def __init__(self, *, artifact_store: ArtifactStore) -> None:
        self.artifacts = artifact_store

    def extract(self, doc: DocumentSnapshot, request: SearchRequest) -> List[CandidateValue]:
        """문서에서 CandidateValue 후보를 추출합니다."""

        text = self._load_text(doc)
        if text.strip() == "":
            return []

        candidates: List[CandidateValue] = []
        candidates.extend(self._extract_krw(doc, request, text))
        candidates.extend(self._extract_usd_scaled(doc, request, text))

        # best-effort dedupe: (value, unit, as_of)
        seen: set[tuple[float, str, Optional[str]]] = set()
        out: List[CandidateValue] = []
        for c in candidates:
            key = (float(c.value), str(c.unit), str(c.as_of) if c.as_of is not None else None)
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    def _load_text(self, doc: DocumentSnapshot) -> str:
        text_aid = (doc.http_meta or {}).get("text_artifact_id")
        if not text_aid:
            return ""
        path = self.artifacts.get_path(str(text_aid))
        if path is None:
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _extract_krw(self, doc: DocumentSnapshot, request: SearchRequest, text: str) -> List[CandidateValue]:
        # Examples:
        # - 2900억원 / 1.2조원
        pattern = re.compile(r"(?P<num>[\d,]+(?:\.\d+)?)\s*(?P<unit>억|조)\s*원?")
        return self._extract_with_pattern(
            doc,
            request,
            text,
            pattern=pattern,
            convert=_convert_krw_unit,
            unit_out="KRW",
        )

    def _extract_usd_scaled(self, doc: DocumentSnapshot, request: SearchRequest, text: str) -> List[CandidateValue]:
        # Examples:
        # - $500M / 2.5B / 1T
        pattern = re.compile(r"(?P<currency>\$)?\s*(?P<num>[\d,]+(?:\.\d+)?)\s*(?P<unit>[MBT])\b", re.IGNORECASE)
        return self._extract_with_pattern(
            doc,
            request,
            text,
            pattern=pattern,
            convert=_convert_en_scaled,
            unit_out="USD",
        )

    def _extract_with_pattern(
        self,
        doc: DocumentSnapshot,
        request: SearchRequest,
        text: str,
        *,
        pattern: re.Pattern[str],
        convert: Any,
        unit_out: str,
    ) -> List[CandidateValue]:
        out: List[CandidateValue] = []
        for m in pattern.finditer(text):
            try:
                value = float(convert(m))
            except Exception:
                continue

            as_of = _infer_as_of(text, request.as_of, span=(m.start(), m.end()))
            quote_ref = self._persist_quote(text, doc=doc, span=(m.start(), m.end()))

            expected = (request.expected_unit or "").upper() if request.expected_unit else None
            conf = _score_confidence(expected_unit=expected, unit_out=unit_out, as_of=as_of, requested_as_of=request.as_of, has_quote=(quote_ref is not None))

            out.append(
                CandidateValue(
                    metric_id=request.metric_id,
                    value=value,
                    unit=unit_out,
                    as_of=as_of,
                    independence_key=compute_independence_key(canonical_url=doc.canonical_url, content_digest=doc.content_digest),
                    span_quote_ref=quote_ref,
                    provenance={
                        "doc_id": doc.doc_id,
                        "doc_artifact_id": doc.artifact_id,
                        "url": doc.url,
                        "canonical_url": doc.canonical_url,
                        "text_artifact_id": (doc.http_meta or {}).get("text_artifact_id"),
                        "span": {"start": int(m.start()), "end": int(m.end())},
                    },
                    confidence=conf,
                    notes={"extractor_id": self.extractor_id},
                )
            )
        return out

    def _persist_quote(self, text: str, *, doc: DocumentSnapshot, span: Tuple[int, int], window: int = 160) -> Optional[Dict[str, str]]:
        start, end = span
        lo = max(0, int(start) - int(window))
        hi = min(len(text), int(end) + int(window))
        snippet = text[lo:hi].strip()
        if snippet == "":
            return None

        # store quote snippet in ART (ref-only)
        digest = sha256_digest((snippet + "\n").encode("utf-8"))
        aid = self.artifacts.put_text(
            snippet,
            kind="search_v3_quote",
            meta={
                "doc_id": doc.doc_id,
                "doc_artifact_id": doc.artifact_id,
                "url": doc.url,
                "canonical_url": doc.canonical_url,
                "span": {"start": int(start), "end": int(end)},
                "digest": digest,
            },
        )
        return {"artifact_id": aid, "digest": digest}


def _infer_as_of(text: str, requested_as_of: Optional[str], *, span: Tuple[int, int]) -> Optional[str]:
    # First: local window search
    start, end = span
    lo = max(0, int(start) - 200)
    hi = min(len(text), int(end) + 200)
    window = text[lo:hi]
    years = _YEAR_RE.findall(window)
    if years:
        # _YEAR_RE returns groups; rebuild year from match by re-searching
        m = re.search(r"(19|20)\d{2}", window)
        if m:
            return str(m.group(0))

    # Next: if requested_as_of exists and appears anywhere, accept it.
    if requested_as_of and str(requested_as_of) in text:
        return str(requested_as_of)

    return None


def _score_confidence(
    *,
    expected_unit: Optional[str],
    unit_out: str,
    as_of: Optional[str],
    requested_as_of: Optional[str],
    has_quote: bool,
) -> float:
    conf = 0.55
    if expected_unit and expected_unit == str(unit_out).upper():
        conf += 0.15
    if requested_as_of and as_of and str(as_of) == str(requested_as_of):
        conf += 0.15
    if has_quote:
        conf += 0.10
    return max(0.0, min(1.0, float(conf)))


def _convert_krw_unit(m: re.Match[str]) -> float:
    num_s = str(m.group("num")).replace(",", "")
    unit = str(m.group("unit"))
    n = float(num_s)
    if unit == "억":
        return n * 100_000_000
    if unit == "조":
        return n * 1_000_000_000_000
    return n


def _convert_en_scaled(m: re.Match[str]) -> float:
    num_s = str(m.group("num")).replace(",", "")
    unit = str(m.group("unit")).upper()
    n = float(num_s)
    if unit == "M":
        return n * 1_000_000
    if unit == "B":
        return n * 1_000_000_000
    if unit == "T":
        return n * 1_000_000_000_000
    return n
