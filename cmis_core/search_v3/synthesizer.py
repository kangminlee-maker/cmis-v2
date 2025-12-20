"""Synthesizer (CandidateValue -> Core EvidenceRecord) (SSV3-07).

Production-minimal v1:
- consensus: median (after best-effort outlier removal)
- confidence: candidate_confidence + variance + count 기반 간단 산정
"""

from __future__ import annotations

import statistics
import uuid
from typing import Any, Dict, List, Optional

from cmis_core.types import EvidenceRecord, EvidenceValueKind, SourceTier
from cmis_core.search_v3.candidate import CandidateValue, SearchRequest


class SynthesizerV1:
    """CandidateValue list를 EvidenceRecord로 합성합니다."""

    synthesizer_id = "SynthesizerV1@v1"

    def synthesize(self, candidates: List[CandidateValue], request: SearchRequest) -> List[EvidenceRecord]:
        if not candidates:
            return []

        metric_id = str(request.metric_id)
        expected_unit = (request.expected_unit or "").upper() if request.expected_unit else None

        # filter by metric
        filtered = [c for c in candidates if str(c.metric_id) == metric_id]
        if expected_unit:
            filtered = [c for c in filtered if str(c.unit).upper() == expected_unit]
        if not filtered:
            return []

        # choose as_of: prefer exact match to requested_as_of (if any), else most common non-null
        chosen_as_of = _choose_as_of(filtered, requested_as_of=request.as_of)

        values = [float(c.value) for c in filtered if isinstance(c.value, (int, float))]
        if not values:
            return []

        values_for_consensus = _remove_outliers_iqr(values) if len(values) >= 5 else values
        value = statistics.median(values_for_consensus)

        confidence = _calculate_confidence(filtered, values_for_consensus)

        evidence = EvidenceRecord(
            evidence_id=f"EVD-SearchV3-{uuid.uuid4().hex[:8]}",
            source_tier=SourceTier.COMMERCIAL.value,
            source_id="SearchV3",
            value=value,
            value_kind=EvidenceValueKind.NUMERIC,
            schema_ref="search_v3_v1",
            confidence=confidence,
            metadata=_build_metadata(filtered, chosen_as_of=chosen_as_of),
            as_of=chosen_as_of,
            lineage={
                "engine_id": self.synthesizer_id,
                "from_doc_ids": sorted({str(c.provenance.get("doc_id") or "") for c in filtered if c.provenance}),
                "from_artifact_ids": sorted({str(c.provenance.get("doc_artifact_id") or "") for c in filtered if c.provenance}),
            },
        )
        return [evidence]


def _choose_as_of(candidates: List[CandidateValue], *, requested_as_of: Optional[str]) -> Optional[str]:
    if requested_as_of:
        for c in candidates:
            if c.as_of is not None and str(c.as_of) == str(requested_as_of):
                return str(requested_as_of)

    as_ofs = [str(c.as_of) for c in candidates if c.as_of is not None]
    if not as_ofs:
        return None
    return max(set(as_ofs), key=as_ofs.count)


def _remove_outliers_iqr(values: List[float]) -> List[float]:
    if len(values) < 5:
        return values
    sorted_vals = sorted(values)
    q1 = statistics.median(sorted_vals[: len(sorted_vals) // 2])
    q3 = statistics.median(sorted_vals[len(sorted_vals) // 2 :])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    filtered = [v for v in values if lower <= v <= upper]
    return filtered if filtered else values


def _calculate_confidence(candidates: List[CandidateValue], values: List[float]) -> float:
    if not values:
        return 0.0

    cand_conf = [float(c.confidence) for c in candidates if isinstance(c.confidence, (int, float))]
    mean_cand = statistics.mean(cand_conf) if cand_conf else 0.55

    # count bonus
    count_score = min(len(values) / 10.0, 0.2)

    # variance bonus (lower CV => higher score)
    if len(values) >= 2:
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        cv = stdev / mean if mean != 0 else 1.0
        variance_score = max(0.0, 0.25 * (1.0 - cv))
    else:
        variance_score = 0.05

    base = 0.55
    conf = (base + count_score + variance_score + mean_cand) / 2.0
    return max(0.0, min(0.95, float(conf)))


def _build_metadata(candidates: List[CandidateValue], *, chosen_as_of: Optional[str]) -> Dict[str, Any]:
    doc_ids = sorted({str(c.provenance.get("doc_id") or "") for c in candidates if c.provenance})
    doc_ids = [d for d in doc_ids if d]
    urls = sorted({str(c.provenance.get("canonical_url") or c.provenance.get("url") or "") for c in candidates if c.provenance})
    urls = [u for u in urls if u]

    quote_artifacts = []
    for c in candidates:
        if c.span_quote_ref and c.span_quote_ref.get("artifact_id"):
            quote_artifacts.append(str(c.span_quote_ref["artifact_id"]))
    quote_artifacts = sorted(set(quote_artifacts))

    return {
        "search_v3": {
            "as_of": chosen_as_of,
            "candidate_count": len(candidates),
            "independence_keys": sorted({str(c.independence_key) for c in candidates}),
            "source_refs": {
                "doc_ids": doc_ids,
                "quote_artifact_ids": quote_artifacts,
                "urls": urls,
            },
        }
    }
