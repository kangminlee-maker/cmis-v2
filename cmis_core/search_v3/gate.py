"""Gate/Policy enforcement for Search Strategy v3 (SSV3-08).

Production-minimal v1:
- reporting_strict: EvidenceCommitted는 최소 품질/독립성/정합 조건을 만족해야 함
- decision_balanced / exploration_friendly: 완화된 조건(운영 단순화)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from cmis_core.search_v3.candidate import CandidateValue, SearchRequest
from cmis_core.types import EvidenceRecord


@dataclass(frozen=True)
class GateReport:
    policy_ref: str
    min_high_quality_evidence: int
    current_high_quality: int
    min_independent_sources: int
    independent_sources: int
    require_quote: bool
    require_as_of_match: bool
    require_unit_match: bool
    status: str  # "met" | "not_met"
    missing: List[str]
    notes: Dict[str, Any]


class GatePolicyEnforcerV1:
    """Search v3 정책/품질 게이트."""

    enforcer_id = "GatePolicyEnforcerV1@v1"

    def evaluate_candidates(self, candidates: List[CandidateValue], request: SearchRequest, *, policy_ref: str) -> GateReport:
        policy_ref = str(policy_ref)

        require_quote = policy_ref == "reporting_strict"
        require_as_of_match = policy_ref == "reporting_strict" and bool(request.as_of)
        require_unit_match = bool(request.expected_unit)

        min_high_quality = int(request.min_high_quality_evidence) if policy_ref == "reporting_strict" else 1
        min_independent_sources = int(request.min_independent_sources) if policy_ref == "reporting_strict" else 1

        high_quality: List[CandidateValue] = []
        for c in candidates:
            ok, _reasons = self._is_high_quality(c, request, require_quote=require_quote, require_as_of_match=require_as_of_match, require_unit_match=require_unit_match)
            if ok:
                high_quality.append(c)

        independent_keys = sorted({str(c.independence_key) for c in high_quality})
        missing: List[str] = []
        if len(high_quality) < min_high_quality:
            missing.append("min_high_quality_evidence")
        if len(independent_keys) < min_independent_sources:
            missing.append("min_independent_sources")

        status = "met" if not missing else "not_met"
        return GateReport(
            policy_ref=policy_ref,
            min_high_quality_evidence=min_high_quality,
            current_high_quality=len(high_quality),
            min_independent_sources=min_independent_sources,
            independent_sources=len(independent_keys),
            require_quote=require_quote,
            require_as_of_match=require_as_of_match,
            require_unit_match=require_unit_match,
            status=status,
            missing=missing,
            notes={"high_quality_count": len(high_quality)},
        )

    def allow_commit_evidence(
        self,
        evidence: EvidenceRecord,
        candidates: List[CandidateValue],
        request: SearchRequest,
        *,
        policy_ref: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        report = self.evaluate_candidates(candidates, request, policy_ref=policy_ref)
        allowed = report.status == "met" or str(policy_ref) != "reporting_strict"

        # reporting_strict에서는 반드시 met 여야 commit 허용
        if str(policy_ref) == "reporting_strict":
            allowed = report.status == "met"

        return allowed, {
            "policy_ref": report.policy_ref,
            "status": report.status,
            "missing": report.missing,
            "min_high_quality_evidence": report.min_high_quality_evidence,
            "current_high_quality": report.current_high_quality,
            "min_independent_sources": report.min_independent_sources,
            "independent_sources": report.independent_sources,
            "require_quote": report.require_quote,
            "require_as_of_match": report.require_as_of_match,
            "require_unit_match": report.require_unit_match,
            "evidence_id": getattr(evidence, "evidence_id", None),
        }

    def should_stop(self, candidates: List[CandidateValue], request: SearchRequest, *, policy_ref: str) -> bool:
        """stop condition: 게이트 충족 시 phase 종료."""

        report = self.evaluate_candidates(candidates, request, policy_ref=policy_ref)
        return report.status == "met"

    def _is_high_quality(
        self,
        c: CandidateValue,
        request: SearchRequest,
        *,
        require_quote: bool,
        require_as_of_match: bool,
        require_unit_match: bool,
    ) -> Tuple[bool, List[str]]:
        reasons: List[str] = []

        if require_unit_match and request.expected_unit:
            if str(c.unit).upper() != str(request.expected_unit).upper():
                reasons.append("unit_mismatch")

        if require_as_of_match and request.as_of:
            if c.as_of is None or str(c.as_of) != str(request.as_of):
                reasons.append("as_of_mismatch")

        if require_quote:
            if not c.span_quote_ref:
                reasons.append("missing_quote_ref")
            else:
                if not c.span_quote_ref.get("artifact_id") or not c.span_quote_ref.get("digest"):
                    reasons.append("invalid_quote_ref")

        return (len(reasons) == 0), reasons
