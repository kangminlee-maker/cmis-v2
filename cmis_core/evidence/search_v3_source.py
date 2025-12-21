"""Search v3 Evidence Source (SSV3-10).

의도:
- SearchKernelV1(Search Strategy v3)을 EvidenceEngine의 commercial tier source로 연결합니다.
- 기존 BaseDataSource 인터페이스를 유지하기 위해, EvidenceExecutor에서
  `fetch_with_policy(request, policy)`를 지원하도록 확장합니다.
"""

from __future__ import annotations

from pathlib import Path
import os
import re
from typing import Any, Dict, Optional

from cmis_core.evidence_engine import BaseDataSource, DataNotFoundError, SourceNotAvailableError
from cmis_core.search_v3.candidate_extractor import RuleBasedCandidateExtractor
from cmis_core.search_v3.document_fetcher import DocumentFetcher
from cmis_core.search_v3.gate import GatePolicyEnforcerV1
from cmis_core.search_v3.generic_web_search import GoogleCseProvider
from cmis_core.search_v3.link_extractor import LinkExtractorV1
from cmis_core.search_v3.link_selector import LinkSelectionPolicyV1
from cmis_core.search_v3.query_learner import QueryLearnerV1
from cmis_core.search_v3.registry import StrategyRegistryV3
from cmis_core.search_v3.runner import SearchKernelV1
from cmis_core.search_v3.synthesizer import SynthesizerV1
from cmis_core.search_v3.verify import verify_search_v3_trace
from cmis_core.stores import ArtifactStore
from cmis_core.types import EvidencePolicy, EvidenceRecord, SourceTier


class SearchV3Source(BaseDataSource):
    """Search Strategy v3 (GenericWebSearch + DocumentFetcher) source."""

    def __init__(
        self,
        *,
        project_root: Optional[Path] = None,
        kernel: Optional[SearchKernelV1] = None,
    ) -> None:
        super().__init__(
            source_id="SearchV3",
            source_tier=SourceTier.COMMERCIAL,
            capabilities={
                # Production-minimal: capability taxonomy mismatch를 피하기 위해 wildcard로 시작합니다.
                # (세부 taxonomy 정합은 별도 P0로 추진)
                "provides": ["*"],
                "regions": ["*"],
                "data_types": ["numeric"],
            },
        )

        self.project_root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
        self.artifacts = ArtifactStore(project_root=self.project_root)

        if kernel is not None:
            self.kernel = kernel
            return

        # Default kernel wiring (production)
        registry = StrategyRegistryV3(self.project_root / "config" / "search_strategy_registry_v3.yaml")
        registry.compile()

        cfg = registry.get_provider_config("GenericWebSearch")
        api_key = os.getenv(str(cfg.api_key_ref or ""))
        engine_id_ref = str((cfg.notes or {}).get("search_engine_id_ref") or "GOOGLE_SEARCH_ENGINE_ID")
        engine_id = os.getenv(engine_id_ref)

        if not api_key or not engine_id:
            raise SourceNotAvailableError("SearchV3 requires GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID")

        provider = GoogleCseProvider(cfg, api_key=api_key, search_engine_id=engine_id, artifact_store=self.artifacts)
        fetcher = DocumentFetcher(artifact_store=self.artifacts)
        extractor = RuleBasedCandidateExtractor(artifact_store=self.artifacts)
        synthesizer = SynthesizerV1()
        gate = GatePolicyEnforcerV1()
        learner = QueryLearnerV1(artifact_store=self.artifacts)
        link_extractor = LinkExtractorV1(artifact_store=self.artifacts)
        link_selector = LinkSelectionPolicyV1()

        self.kernel = SearchKernelV1(
            registry=registry,
            provider=provider,
            fetcher=fetcher,
            extractor=extractor,
            synthesizer=synthesizer,
            gate=gate,
            learner=learner,
            link_extractor=link_extractor,
            link_selector=link_selector,
        )

    def can_handle(self, request: Any) -> bool:
        # Metric 요청만 처리
        try:
            return bool(getattr(request, "request_type", "") == "metric" and getattr(request, "metric_id", None))
        except Exception:
            return False

    def fetch(self, request: Any) -> EvidenceRecord:
        # policy_ref가 없으면 decision_balanced로 실행
        policy_id = str((getattr(request, "context", {}) or {}).get("policy_ref") or "decision_balanced")
        policy = EvidencePolicy.from_config(policy_id, config=None)  # type: ignore[arg-type]
        return self.fetch_with_policy(request, policy)

    def fetch_with_policy(self, request: Any, policy: EvidencePolicy) -> EvidenceRecord:
        """EvidenceExecutor에서 호출되는 policy-aware entrypoint."""

        ctx = dict(getattr(request, "context", {}) or {})
        metric_id = str(getattr(request, "metric_id", "") or "")
        if not metric_id:
            raise DataNotFoundError("SearchV3 requires metric_id")

        region = str(ctx.get("region") or "KR")
        language = "ko" if region.upper() == "KR" else "en"

        # as_of/year best-effort
        as_of = None
        year = ctx.get("year")
        if isinstance(year, int):
            as_of = str(year)
        elif isinstance(year, str) and year.strip():
            as_of = year.strip()
        else:
            as_of_raw = str(ctx.get("as_of") or "").strip()
            m = re.search(r"(19|20)\d{2}", as_of_raw)
            as_of = m.group(0) if m else None

        expected_unit = ctx.get("expected_unit") or ctx.get("unit")

        # template vars (best-effort)
        template_vars = {
            "domain": ctx.get("domain_id") or ctx.get("domain") or "",
            "year": int(as_of) if (as_of and as_of.isdigit()) else (ctx.get("year") or ""),
        }

        # budgets: v2 spec의 기본값을 v1에 적용
        if str(policy.policy_id) == "reporting_strict":
            max_q = 3
            max_f = 8
        elif str(policy.policy_id) == "exploration_friendly":
            max_q = 10
            max_f = 20
        else:
            max_q = 5
            max_f = 12

        result = self.kernel.fetch_evidence(
            metric_id=metric_id,
            policy_ref=str(policy.policy_id),
            template_vars=template_vars,
            expected_unit=(None if expected_unit is None else str(expected_unit)),
            as_of=as_of,
            language=language,
            region=region,
            budget_max_queries=max_q,
            budget_max_fetches=max_f,
        )

        if not result.evidence_records:
            raise DataNotFoundError("SearchV3 produced no committable evidence")

        best = max(result.evidence_records, key=lambda r: float(getattr(r, "confidence", 0.0) or 0.0))
        # attach minimal trace pinning (ref-only)
        best.lineage = dict(best.lineage or {})
        best.lineage["search_v3"] = {
            "search_run_id": result.search_run_id,
            "initial_plan_digest": result.initial_plan_digest,
            "plan_digest_chain": list(result.plan_digest_chain),
            "trace_envelope_artifact_id": result.trace_envelope_artifact_id,
            "events_artifact_id": result.events_artifact_id,
            "query_learner_artifact_id": result.query_learner_artifact_id,
        }

        # Verifier hook (ref-only SSoT)
        try:
            issues = verify_search_v3_trace(
                self.artifacts,
                trace_envelope_artifact_id=str(result.trace_envelope_artifact_id or ""),
                events_artifact_id=str(result.events_artifact_id or ""),
            )
        except Exception as e:
            raise SourceNotAvailableError(f"SearchV3 trace verification error: {e}")
        if issues:
            raise SourceNotAvailableError(f"SearchV3 trace verification failed: {issues}")
        return best
