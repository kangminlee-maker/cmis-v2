"""Search Strategy v3 Synthesizer unit tests (SSV3-07)."""

from __future__ import annotations

from cmis_core.search_v3.candidate import CandidateValue, SearchRequest
from cmis_core.search_v3.synthesizer import SynthesizerV1


def test_synthesizer_v1_median_and_outlier_removal() -> None:
    req = SearchRequest(metric_id="MET-TAM", expected_unit="USD", as_of="2024")

    values = [100.0, 105.0, 108.0, 110.0, 1_000_000.0]
    candidates = []
    for i, v in enumerate(values):
        candidates.append(
            CandidateValue(
                metric_id="MET-TAM",
                value=v,
                unit="USD",
                as_of="2024" if i == 0 else None,
                independence_key=f"host:example.com|sha256:{i}",
                span_quote_ref={"artifact_id": f"ART-q-{i}", "digest": f"sha256:{i}"},
                provenance={"doc_id": f"DOC-{i}", "doc_artifact_id": f"ART-doc-{i}", "url": "https://example.com"},
                confidence=0.7,
            )
        )

    syn = SynthesizerV1()
    out = syn.synthesize(candidates, req)

    assert len(out) == 1
    ev = out[0]
    assert ev.source_tier == "commercial"
    assert ev.source_id == "SearchV3"
    assert ev.schema_ref == "search_v3_v1"
    assert ev.as_of == "2024"

    # outlier(1_000_000) 제거 후 median([100,105,108,110]) = (105+108)/2 = 106.5
    assert ev.value == 106.5
    assert 0.0 <= ev.confidence <= 1.0
    assert ev.metadata["search_v3"]["candidate_count"] == 5
