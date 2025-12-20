"""SearchRunner/SearchKernel v1 (SSV3-09).

Production-minimal v1:
- phase loop (registry plan template 기반)
- query -> serp -> document fetch -> extraction -> gate -> synthesize -> commit
- replan(heuristic): gate_not_met 이고 hit 여유가 있으면 fetch_top_k를 증가시키는 1회성 수정
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from cmis_core.digest import canonical_digest
from cmis_core.search_v3.candidate import CandidateValue, SearchRequest
from cmis_core.search_v3.candidate_extractor import RuleBasedCandidateExtractor
from cmis_core.search_v3.document_fetcher import DocumentFetcher, DocumentSnapshot
from cmis_core.search_v3.gate import GatePolicyEnforcerV1
from cmis_core.search_v3.generic_web_search import GoogleCseProvider
from cmis_core.search_v3.query import SearchQueryRequest, finalize_query_request
from cmis_core.search_v3.registry import StrategyRegistryV3
from cmis_core.search_v3.serp import SerpSnapshotRef
from cmis_core.search_v3.synthesizer import SynthesizerV1
from cmis_core.search_v3.trace import SearchTraceWriter
from cmis_core.types import EvidenceRecord


@dataclass
class SearchRunResult:
    search_run_id: str
    initial_plan_digest: str
    plan_digest_chain: List[str] = field(default_factory=list)
    evidence_records: List[EvidenceRecord] = field(default_factory=list)
    candidates: List[CandidateValue] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    trace_envelope_artifact_id: Optional[str] = None
    events_artifact_id: Optional[str] = None


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SearchKernelV1:
    """EvidenceEngine에서 호출되는 Search v3 facade."""

    def __init__(
        self,
        *,
        registry: StrategyRegistryV3,
        provider: GoogleCseProvider,
        fetcher: DocumentFetcher,
        extractor: RuleBasedCandidateExtractor,
        synthesizer: SynthesizerV1,
        gate: GatePolicyEnforcerV1,
    ) -> None:
        self.registry = registry
        self.provider = provider
        self.fetcher = fetcher
        self.extractor = extractor
        self.synthesizer = synthesizer
        self.gate = gate

    def fetch_evidence(
        self,
        *,
        metric_id: str,
        policy_ref: str,
        template_vars: Dict[str, Any],
        expected_unit: Optional[str],
        as_of: Optional[str],
        language: str,
        region: str,
        budget_max_queries: int = 5,
        budget_max_fetches: int = 10,
    ) -> SearchRunResult:
        search_run_id = f"SRCH-{uuid.uuid4().hex[:8]}"
        trace = SearchTraceWriter(search_run_id=search_run_id)
        started_at = _utc_now_iso_z()

        req = SearchRequest(metric_id=str(metric_id), expected_unit=expected_unit, as_of=as_of)

        plan_tpl = self.registry.resolve_metric_plan_template(metric_id=str(metric_id), policy_ref=str(policy_ref))
        phases = list(plan_tpl.get("phases") or [])

        plan_obj = {
            "metric_id": str(metric_id),
            "policy_ref": str(policy_ref),
            "phases": phases,
            "pinned_registry_digest": self.registry.get_strategy_ref().registry_digest,
        }
        initial_plan_digest = canonical_digest(plan_obj)
        plan_digest_chain: List[str] = [initial_plan_digest]

        trace.emit(
            "PlanBuilt",
            payload={
                "initial_plan_digest": initial_plan_digest,
                "phases": [p.get("phase_id") for p in phases if isinstance(p, dict)],
                "pinned_registry_digest": self.registry.get_strategy_ref().registry_digest,
            },
        )

        candidates: List[CandidateValue] = []
        queries_used = 0
        fetches_used = 0
        replan_done = False

        for phase in phases:
            if not isinstance(phase, dict):
                continue

            phase_id = str(phase.get("phase_id") or "")
            providers = list(phase.get("providers") or [])
            provider_id = str(providers[0]) if providers else self.provider.provider_id

            query_templates = list(phase.get("query_templates") or [])
            retrieval = dict(phase.get("retrieval") or {})
            serp_top_k = int(retrieval.get("serp_top_k", 8))
            fetch_top_k = int(retrieval.get("fetch_top_k", 3))

            for tpl in query_templates:
                if queries_used >= int(budget_max_queries):
                    break

                query_text = _format_query_template(str(tpl), template_vars=template_vars, metric_id=str(metric_id), region=str(region))
                q_req = SearchQueryRequest(
                    provider_id=provider_id,
                    query=query_text,
                    language=str(language),
                    region=str(region),
                    top_k=serp_top_k,
                    timeout_sec=int(phase.get("timeout_sec", 10) or 10),
                    filters=dict(phase.get("filters") or {}),
                )
                q_final = finalize_query_request(self.fetcher.artifacts, q_req, generator_meta={"deterministic": True})
                queries_used += 1

                trace.emit(
                    "QueryGenerated",
                    phase_id=phase_id,
                    payload={
                        "language": q_final.language,
                        "provider_id": q_final.provider_id,
                        "query_request_digest": q_final.request_digest,
                        "query_artifact_id": q_final.query_artifact_id,
                        "generator": {"deterministic": True, "llm_used": False, "templates_used": [str(tpl)]},
                    },
                )

                serp: SerpSnapshotRef = self.provider.search(q_final)
                trace.emit(
                    "SerpFetched",
                    phase_id=phase_id,
                    payload={
                        "provider_id": serp.provider_id,
                        "provider_config_digest": serp.provider_config_digest,
                        "query_request_digest": serp.query_request_digest,
                        "serp_artifact_id": serp.serp_artifact_id,
                        "serp_digest": serp.serp_digest,
                        "language": q_final.language,
                        "top_k": q_final.top_k,
                        "hit_count": len(serp.hits),
                        "hits": [{"url": h.url, "canonical_url": h.canonical_url, "rank": h.rank} for h in serp.hits],
                    },
                )

                fetched_docs: List[DocumentSnapshot] = []
                docs_to_fetch = list(serp.hits)[: min(fetch_top_k, len(serp.hits))]
                for hit in docs_to_fetch:
                    if fetches_used >= int(budget_max_fetches):
                        break
                    doc = self.fetcher.fetch(hit.url, timeout_sec=int(phase.get("timeout_sec", 10) or 10))
                    fetches_used += 1
                    if doc is None:
                        continue
                    fetched_docs.append(doc)
                    trace.emit(
                        "DocumentFetched",
                        phase_id=phase_id,
                        payload={
                            "url": hit.url,
                            "canonical_url": hit.canonical_url,
                            "doc_id": doc.doc_id,
                            "artifact_id": doc.artifact_id,
                            "content_digest": doc.content_digest,
                            "http_status": (doc.http_meta or {}).get("status_code"),
                        },
                    )

                for doc in fetched_docs:
                    new_cands = self.extractor.extract(doc, req)
                    candidates.extend(new_cands)
                    trace.emit(
                        "ExtractionDone",
                        phase_id=phase_id,
                        payload={
                            "doc_id": doc.doc_id,
                            "extractor_id": self.extractor.extractor_id,
                            "candidates_found": len(new_cands),
                            "candidate_summaries": [
                                {
                                    "value": c.value,
                                    "unit": c.unit,
                                    "as_of": c.as_of,
                                    "confidence": c.confidence,
                                    "independence_key": c.independence_key,
                                }
                                for c in new_cands
                            ],
                        },
                    )

                report = self.gate.evaluate_candidates(candidates, req, policy_ref=str(policy_ref))
                trace.emit(
                    "GateEvaluated",
                    phase_id=phase_id,
                    payload={
                        "policy_ref": report.policy_ref,
                        "min_high_quality_evidence": report.min_high_quality_evidence,
                        "current_high_quality": report.current_high_quality,
                        "require_quote": report.require_quote,
                        "status": report.status,
                        "missing": report.missing,
                        "independent_sources": report.independent_sources,
                    },
                )

                if report.status == "met":
                    break

                # heuristic replan: fetch_top_k 증가 (1회)
                if (not replan_done) and str(policy_ref) == "reporting_strict" and len(serp.hits) > fetch_top_k:
                    prev = plan_digest_chain[-1]
                    new_fetch_top_k = min(len(serp.hits), fetch_top_k + 1)
                    next_plan = dict(plan_obj)
                    next_plan["phases"] = list(phases)
                    next_digest = canonical_digest(next_plan | {"replan": {"fetch_top_k": new_fetch_top_k}})
                    plan_digest_chain.append(next_digest)
                    replan_done = True

                    trace.emit(
                        "PlanRevised",
                        phase_id=phase_id,
                        payload={
                            "prev_plan_digest": prev,
                            "next_plan_digest": next_digest,
                            "proposed_by": "heuristic",
                            "reason_codes": ["gate_not_met", "budget_remaining_ok"],
                            "delta_summary": {"phase_id": phase_id, "fetch_top_k": {"from": fetch_top_k, "to": new_fetch_top_k}},
                        },
                    )

                    # Fetch additional docs and re-evaluate (no additional query)
                    for hit in list(serp.hits)[fetch_top_k:new_fetch_top_k]:
                        if fetches_used >= int(budget_max_fetches):
                            break
                        doc = self.fetcher.fetch(hit.url, timeout_sec=int(phase.get("timeout_sec", 10) or 10))
                        fetches_used += 1
                        if doc is None:
                            continue
                        trace.emit(
                            "DocumentFetched",
                            phase_id=phase_id,
                            payload={
                                "url": hit.url,
                                "canonical_url": hit.canonical_url,
                                "doc_id": doc.doc_id,
                                "artifact_id": doc.artifact_id,
                                "content_digest": doc.content_digest,
                                "http_status": (doc.http_meta or {}).get("status_code"),
                            },
                        )
                        new_cands = self.extractor.extract(doc, req)
                        candidates.extend(new_cands)
                        trace.emit(
                            "ExtractionDone",
                            phase_id=phase_id,
                            payload={
                                "doc_id": doc.doc_id,
                                "extractor_id": self.extractor.extractor_id,
                                "candidates_found": len(new_cands),
                                "candidate_summaries": [
                                    {
                                        "value": c.value,
                                        "unit": c.unit,
                                        "as_of": c.as_of,
                                        "confidence": c.confidence,
                                        "independence_key": c.independence_key,
                                    }
                                    for c in new_cands
                                ],
                            },
                        )
                    report2 = self.gate.evaluate_candidates(candidates, req, policy_ref=str(policy_ref))
                    trace.emit(
                        "GateEvaluated",
                        phase_id=phase_id,
                        payload={
                            "policy_ref": report2.policy_ref,
                            "min_high_quality_evidence": report2.min_high_quality_evidence,
                            "current_high_quality": report2.current_high_quality,
                            "require_quote": report2.require_quote,
                            "status": report2.status,
                            "missing": report2.missing,
                            "independent_sources": report2.independent_sources,
                        },
                    )
                    if report2.status == "met":
                        break

            if self.gate.should_stop(candidates, req, policy_ref=str(policy_ref)):
                break

        evidence_records = self.synthesizer.synthesize(candidates, req)
        committed: List[EvidenceRecord] = []
        for ev in evidence_records:
            allowed, rep = self.gate.allow_commit_evidence(ev, candidates, req, policy_ref=str(policy_ref))
            if allowed:
                committed.append(ev)
                trace.emit(
                    "EvidenceCommitted",
                    payload={
                        "evidence_id": ev.evidence_id,
                        "metric_id": req.metric_id,
                        "value": ev.value,
                        "unit": req.expected_unit,
                        "as_of": ev.as_of,
                        "confidence": ev.confidence,
                        "source_refs": (ev.metadata or {}).get("search_v3", {}).get("source_refs", {}),
                    },
                )

        trace.emit(
            "RunCompleted",
            payload={
                "status": "success",
                "final_plan_digest": plan_digest_chain[-1],
                "plan_digest_chain": list(plan_digest_chain),
                "evidence_ids": [e.evidence_id for e in committed],
                "summary": {"queries_used": queries_used, "fetches_used": fetches_used},
            },
        )

        # Persist trace artifacts (ref-only SSoT)
        events_artifact_id = trace.flush_events_jsonl(self.fetcher.artifacts)
        envelope_artifact_id = self.fetcher.artifacts.put_json(
            {
                "trace_version": 1,
                "search_run_id": search_run_id,
                "metric_id": str(metric_id),
                "strategy_ref": {
                    "registry_version": self.registry.get_strategy_ref().registry_version,
                    "registry_digest": self.registry.get_strategy_ref().registry_digest,
                    "compiled_at": self.registry.get_strategy_ref().compiled_at,
                },
                "initial_plan_digest": initial_plan_digest,
                "final_plan_digest": plan_digest_chain[-1],
                "plan_digest_chain": list(plan_digest_chain),
                "policy_ref": str(policy_ref),
                "started_at": started_at,
                "ended_at": _utc_now_iso_z(),
                "budget_initial": {"max_queries": int(budget_max_queries), "max_fetches": int(budget_max_fetches)},
                "summary": {"queries_used": queries_used, "fetches_used": fetches_used, "evidence_ids": [e.evidence_id for e in committed]},
                "events_artifact_id": events_artifact_id,
            },
            kind="search_v3_trace_envelope",
        )

        return SearchRunResult(
            search_run_id=search_run_id,
            initial_plan_digest=initial_plan_digest,
            plan_digest_chain=plan_digest_chain,
            evidence_records=committed,
            candidates=candidates,
            events=[{"type": e.type, "payload": e.payload, "phase_id": e.phase_id} for e in trace.events],
            trace_envelope_artifact_id=envelope_artifact_id,
            events_artifact_id=events_artifact_id,
        )


def _format_query_template(template: str, *, template_vars: Dict[str, Any], metric_id: str, region: str) -> str:
    # Conservative formatter: only known placeholders
    vars_safe = dict(template_vars or {})
    vars_safe.setdefault("metric", metric_id)
    vars_safe.setdefault("region", region)
    try:
        return template.format(**vars_safe)
    except Exception:
        # fallback: return template as-is
        return template
