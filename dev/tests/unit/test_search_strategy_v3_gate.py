"""Search Strategy v3 GatePolicyEnforcer unit tests (SSV3-08)."""

from __future__ import annotations

from cmis_core.search_v3.candidate import CandidateValue, SearchRequest
from cmis_core.search_v3.gate import GatePolicyEnforcerV1
from cmis_core.types import EvidenceRecord, EvidenceValueKind


def _ev() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="EVD-test",
        source_tier="commercial",
        source_id="SearchV3",
        value=123.0,
        value_kind=EvidenceValueKind.NUMERIC,
        schema_ref="search_v3_v1",
        confidence=0.7,
    )


def test_reporting_strict_requires_two_independent_sources_and_quote_and_as_of() -> None:
    gate = GatePolicyEnforcerV1()
    req = SearchRequest(metric_id="MET-TAM", expected_unit="KRW", as_of="2024", min_high_quality_evidence=2, min_independent_sources=2)

    c1 = CandidateValue(
        metric_id="MET-TAM",
        value=1.0,
        unit="KRW",
        as_of="2024",
        independence_key="host:a|sha256:x",
        span_quote_ref={"artifact_id": "ART-q-1", "digest": "sha256:1"},
        provenance={"doc_id": "DOC-1", "doc_artifact_id": "ART-doc-1"},
        confidence=0.8,
    )
    c2 = CandidateValue(
        metric_id="MET-TAM",
        value=2.0,
        unit="KRW",
        as_of="2024",
        independence_key="host:b|sha256:y",
        span_quote_ref={"artifact_id": "ART-q-2", "digest": "sha256:2"},
        provenance={"doc_id": "DOC-2", "doc_artifact_id": "ART-doc-2"},
        confidence=0.8,
    )

    allowed, report = gate.allow_commit_evidence(_ev(), [c1, c2], req, policy_ref="reporting_strict")
    assert allowed is True
    assert report["status"] == "met"


def test_reporting_strict_denies_when_missing_quote_or_independent_sources() -> None:
    gate = GatePolicyEnforcerV1()
    req = SearchRequest(metric_id="MET-TAM", expected_unit="KRW", as_of="2024", min_high_quality_evidence=2, min_independent_sources=2)

    c1 = CandidateValue(
        metric_id="MET-TAM",
        value=1.0,
        unit="KRW",
        as_of="2024",
        independence_key="host:a|sha256:x",
        span_quote_ref=None,  # missing quote
        provenance={"doc_id": "DOC-1", "doc_artifact_id": "ART-doc-1"},
        confidence=0.8,
    )
    c2 = CandidateValue(
        metric_id="MET-TAM",
        value=2.0,
        unit="KRW",
        as_of="2024",
        independence_key="host:a|sha256:x",  # not independent
        span_quote_ref={"artifact_id": "ART-q-2", "digest": "sha256:2"},
        provenance={"doc_id": "DOC-2", "doc_artifact_id": "ART-doc-2"},
        confidence=0.8,
    )

    allowed, report = gate.allow_commit_evidence(_ev(), [c1, c2], req, policy_ref="reporting_strict")
    assert allowed is False
    assert report["status"] == "not_met"
    assert "min_high_quality_evidence" in report["missing"] or "min_independent_sources" in report["missing"]


def test_decision_balanced_allows_with_one_candidate_even_without_quote() -> None:
    gate = GatePolicyEnforcerV1()
    req = SearchRequest(metric_id="MET-TAM", expected_unit="KRW", as_of="2024")

    c1 = CandidateValue(
        metric_id="MET-TAM",
        value=1.0,
        unit="KRW",
        as_of=None,
        independence_key="host:a|sha256:x",
        span_quote_ref=None,
        provenance={"doc_id": "DOC-1", "doc_artifact_id": "ART-doc-1"},
        confidence=0.6,
    )

    allowed, report = gate.allow_commit_evidence(_ev(), [c1], req, policy_ref="decision_balanced")
    assert allowed is True
