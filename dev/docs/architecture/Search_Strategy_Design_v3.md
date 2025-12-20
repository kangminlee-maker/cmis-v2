# Search Strategy v3 — 구현 구체화 (1~6)

> 용어: CMIS에서는 “task ledger” 대신 **project ledger**를 사용합니다.<br>
> 본 설계에서 “검색 오케스트레이션의 상태”는 **SearchProjectLedger(프로젝트 데이터/정본 포인터)** + **SearchProgressLedger(진행/이벤트/예산)** 로 분리합니다.

---

## 1) 클래스/인터페이스 시그니처 (Python-like, 구현 지향)

### 1.0 코어 정합/SSoT 강제 규칙 (반드시 지킨다)

- **타입 단일화**: Search v3는 코어 타입(`cmis_core.types.EvidenceRecord`, `cmis_core.types.SourceTier`)을 재정의하지 않습니다.
  - Search 내부의 phase/provider/adapter 분류(예: authoritative/generic_web, serpapi/tavily 등)는 코어 `EvidenceRecord.metadata["search_v3"]`로 보존합니다.
- **ref-only(원문/대량 데이터 금지)**: SearchProgressLedger 이벤트 및 SearchProjectLedger에는 원문/대량 텍스트를 저장하지 않습니다.
  - 쿼리 텍스트, SERP 원본(title/snippet 포함), 문서 원문/HTML/PDF, 추출 근거(인용/표 위치 등)는 **ArtifactStore(ART-*)** 로만 저장합니다.
  - ledger/event에는 `ART-*` 참조 + digest + 최소 요약(수치/단위/기간 같은 구조화된 값)만 남깁니다.
- **정책 SSoT 단일화**: SearchContext는 egress policy를 “입력”으로 받지 않습니다.
  - `effective_egress = PolicyEngine(policy_ref, request_confidentiality) ∩ tool_and_resource_registry` 로 resolve된 결과만 pin(고정)합니다.
  - trace에는 `policy_digest`, `tool_registry_digest`, `effective_egress_digest`를 남겨 재현성을 확보합니다.

### 1.1 핵심 데이터 모델

    from __future__ import annotations
    from dataclasses import dataclass, field
    from typing import Any, Dict, List, Optional, Literal, Protocol, Iterable, Tuple
    import datetime

    PolicyMode = Literal["reporting_strict", "decision_balanced", "exploration_friendly"]
    LanguagePolicy = Literal["auto", "fixed_ko", "fixed_en", "fixed_ja"]
    RequestConfidentiality = Literal["public", "internal", "confidential"]
    # NOTE: 코어 SourceTier는 `official|curated_internal|commercial`이며, v3는 이를 재정의하지 않습니다.
    EvidenceStatus = Literal["accepted", "rejected", "needs_review"]  # internal only (candidate/evidence gate)

    @dataclass(frozen=True)
    class StrategyRef:
        registry_version: int
        registry_digest: str          # sha256:...
        compiled_at: str              # ISO8601
        notes: Dict[str, Any] = field(default_factory=dict)

    @dataclass(frozen=True)
    class EffectiveEgressPolicy:
        """PolicyEngine/tool registry로 resolve된 '집행용' egress policy."""

        allow_web_search: bool
        allow_official_http_fetch: bool
        allow_commercial_api: bool
        allow_llm_api: bool
        # Optional constraints (resolved)
        allow_domains: Optional[List[str]] = None
        deny_domains: Optional[List[str]] = None

    @dataclass(frozen=True)
    class Budget:
        max_queries: int
        max_fetches: int
        max_time_sec: int
        max_cost_usd: Optional[float]  # 비용을 실측할 수 없는 provider가 있으면 None 허용
        # Optional
        per_domain_qps: Optional[Dict[str, float]] = None

    @dataclass(frozen=True)
    class SearchRequest:
        metric_id: str
        metric_definition: str                 # metric spec의 정의(필수)
        expected_unit: Optional[str]           # "KRW", "USD", "%", ...
        as_of: Optional[str]                   # "2024", "2024-12-31" 등
        required_granularity: Optional[str]    # "yearly"|"quarterly"|"monthly"
        subject_terms: Dict[str, Any]          # domain keywords, company_name, segment ...
        min_high_quality_evidence: int = 2     # stop condition 기본

    @dataclass(frozen=True)
    class SearchContext:
        domain_id: str
        region: str
        language_policy: LanguagePolicy
        # Policy SSoT (input)
        policy_ref: PolicyMode
        request_confidentiality: RequestConfidentiality
        # Policy SSoT (resolved/pinned)
        policy_digest: str                        # sha256:... (resolved policy snapshot)
        tool_registry_digest: str                 # sha256:... (tool_and_resource_registry snapshot)
        effective_egress: EffectiveEgressPolicy   # resolved result
        effective_egress_digest: str              # sha256:... (canonicalized(effective_egress))
        budget: Budget
        strategy_ref: StrategyRef              # 런타임에서 pin(재현성 핵심)
        run_tags: Dict[str, Any] = field(default_factory=dict)

    @dataclass(frozen=True)
    class SearchHitRef:
        url: str
        canonical_url: str
        rank: int
        provider_id: str
        meta: Dict[str, Any] = field(default_factory=dict)

    @dataclass(frozen=True)
    class SearchQueryRequest:
        """Provider에 전달되는 검색 요청.

        - 런타임에서는 query 문자열이 필요하지만,
          ledger/event에는 query_text를 직접 저장하지 않고 artifact/ref로만 저장합니다.
        """

        provider_id: str
        query: str
        language: str
        region: str
        top_k: int
        timeout_sec: int
        filters: Dict[str, Any] = field(default_factory=dict)  # recency_days, allow/deny domains, safe_search...
        query_artifact_id: Optional[str] = None                # ART-* (query text + generator meta)
        request_digest: str = ""                               # sha256:... (canonicalized request)

    @dataclass(frozen=True)
    class SerpSnapshotRef:
        """SERP 원본은 ART로 저장하고, ledger/event에는 ref만 남깁니다."""

        provider_id: str
        serp_artifact_id: str               # ART-* (provider raw response + normalized hits)
        serp_digest: str                    # sha256:... (canonicalized SERP snapshot)
        query_request_digest: str           # sha256:... (SearchQueryRequest digest)
        retrieved_at: str                   # ISO8601
        hits: List[SearchHitRef] = field(default_factory=list)

    @dataclass(frozen=True)
    class DocumentSnapshot:
        doc_id: str                            # DOC-*
        url: str
        canonical_url: str
        artifact_id: str                       # ART-* (본문/HTML/텍스트/메타를 저장)
        # 중복 제거/독립성 판단을 위해 "정규화된 본문" 기준 digest를 기본으로 둡니다.
        # (원본 bytes digest는 선택적으로 추가 가능)
        raw_bytes_digest: Optional[str] = None  # sha256:... (optional)
        content_digest: str                    # sha256:... (normalized_text digest)
        fetched_at: str                        # ISO8601
        http_meta: Dict[str, Any]              # status_code, headers subset ...
        readability: Dict[str, Any] = field(default_factory=dict)

    @dataclass(frozen=True)
    class CandidateValue:
        metric_id: str
        value: float
        unit: str
        as_of: Optional[str]
        # "서로 독립적인 출처" 판정용 키(예: publisher/host + content cluster/digest 조합).
        # reporting_strict에서 min_independent_sources 게이트에 사용합니다.
        independence_key: str
        # 원문/인용은 ART로 저장하고, ledger/event에는 ref만 남깁니다.
        span_quote_ref: Optional[Dict[str, str]]  # {"artifact_id":"ART-*","digest":"sha256:..."}
        provenance: Dict[str, Any]             # url, artifact_id, section, table coords...
        confidence: float                      # extraction confidence (0~1)
        notes: Dict[str, Any] = field(default_factory=dict)

    # NOTE: 최종 산출물은 코어 EvidenceRecord로 반환합니다.
    # - cmis_core.types.EvidenceRecord
    # - cmis_core.types.SourceTier(official|curated_internal|commercial)
    from cmis_core.types import EvidenceRecord as CoreEvidenceRecord

    @dataclass(frozen=True)
    class SearchPhase:
        phase_id: str                          # "authoritative"|"generic_web"|...
        providers: List[str]                   # provider ids
        query_templates: List[str]             # f-string templates
        expansion: Dict[str, Any]              # deterministic/llm flags
        retrieval: Dict[str, Any]              # serp_top_k, fetch_top_k, fetch_depth
        filters: Dict[str, Any]                # deny_domains, recency_days...
        scoring: Dict[str, Any]                # ranking weights
        stop_conditions: Dict[str, Any]        # min_evidence, min_confidence, ...

    @dataclass(frozen=True)
    class SearchPlan:
        metric_id: str
        phases: List[SearchPhase]
        plan_digest: str                       # sha256(canonical_json(plan_input))
        pinned_registry_digest: str            # strategy_ref.registry_digest
        created_at: str                        # ISO8601
        notes: Dict[str, Any] = field(default_factory=dict)


### 1.2 Ledger 모델 (CMIS 용어 반영)

    @dataclass
    class SearchProjectLedger:
        """
        SearchProjectLedger = 검색 프로젝트 데이터(정본 포인터/요약)
        - 재현성 관점에서 '무엇을 pin했는지'와 '무엇을 확보했는지'를 ref 중심으로 보관
        - 원문/대량 데이터는 ArtifactStore(ART)로만, ledger에는 ref만
        """
        search_run_id: str                         # SRCH-*
        metric_id: str
        strategy_ref: StrategyRef
        # Plan pinning (재현성)
        initial_plan_digest: str
        plan_digest: str                           # current/final (latest)
        plan_digest_chain: List[str] = field(default_factory=list)  # optional: [initial, revised1, ..., final]
        # Inputs
        request: SearchRequest
        context: SearchContext
        # Outputs (refs)
        serp_snapshots: List[SerpSnapshotRef] = field(default_factory=list)
        documents: List[DocumentSnapshot] = field(default_factory=list)
        candidates: List[CandidateValue] = field(default_factory=list)
        evidence_records: List[str] = field(default_factory=list)  # CoreEvidenceRecord.evidence_id 리스트
        # Audit refs
        artifacts: List[str] = field(default_factory=list)         # ART-* used/created
        # Optional spill-over: ledger 크기 보호(권장)
        # - documents/candidates/serp_snapshots가 커지면 JSON artifact로 저장하고, ledger에는 ref만 둡니다.
        documents_artifact_id: Optional[str] = None                # ART-* (optional)
        candidates_artifact_id: Optional[str] = None               # ART-* (optional)
        # Determinism helpers
        digests: Dict[str, str] = field(default_factory=dict)      # e.g., {"plan":"sha256:..."}
        created_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

    @dataclass
    class SearchProgressLedger:
        """
        SearchProgressLedger = 진행/이벤트/예산 소비(append-only event log + derived view)
        - 이벤트 스트림을 기본으로 하고, 진행 뷰(remaining budget 등)는 이벤트에서 derive
        """
        search_run_id: str
        events: List[Dict[str, Any]] = field(default_factory=list)
        derived: Dict[str, Any] = field(default_factory=dict)      # budget_remaining, phase_state, ...


### 1.3 핵심 컴포넌트 인터페이스

    class StrategyRegistry(Protocol):
        """
        versioned registry (YAML -> compiled)
        - 런타임은 registry_digest를 pin하여 재현성 보장
        """
        def get_strategy_ref(self) -> StrategyRef: ...
        def compile(self) -> None: ...
        def resolve_metric_plan_template(self, metric_id: str, policy_ref: PolicyMode) -> Dict[str, Any]: ...
        def get_provider_config(self, provider_id: str) -> Dict[str, Any]: ...


    class SearchPlanner(Protocol):
        """
        입력(metric request + context + registry) -> SearchPlan 생성
        - Phase 기반 전략
        - Budget/Policy/Gates를 plan에 반영
        """
        def build_plan(self, request: SearchRequest, context: SearchContext) -> SearchPlan: ...


    class QueryGenerator(Protocol):
        """
        Phase + templates + deterministic expansion(+ optional LLM) -> queries 생성
        - reporting_strict에서는 LLM 비활성화 등 정책 강제
        - 생성 결과는 trace에 기록(재현성)
        """
        def generate(self, request: SearchRequest, context: SearchContext, phase: SearchPhase) -> List[SearchQueryRequest]:
            """Provider 호출 직전 형태의 요청 리스트를 생성합니다.

            NOTE:
            - query 텍스트 자체는 런타임에서 필요하지만, ledger/event에는 query_text를 직접 저장하지 않습니다.
            - query_artifact_id/request_digest는 SearchRunner가 확정/기록할 수 있습니다.
            """


    class SearchProvider(Protocol):
        """
        SERP provider 추상화(여러 backend 교체 가능)
        """
        provider_id: str

        def search(self, req: SearchQueryRequest) -> SerpSnapshotRef: ...
        def supports(self, capability: str) -> bool: ...


    class DocumentFetcher(Protocol):
        """
        URL -> DocumentSnapshot(artifact 저장 포함)
        - url canonicalization, cache, rate limit, error policy 포함
        """
        def fetch(self, url: str, timeout_sec: int) -> Optional[DocumentSnapshot]: ...


    class CandidateExtractor(Protocol):
        """
        DocumentSnapshot -> CandidateValue list
        - metric-aware extraction(정의/단위/기간 정렬)
        - LLM extraction은 policy/egress에 따라 선택
        """
        extractor_id: str

        def extract(self, doc: DocumentSnapshot, request: SearchRequest, context: SearchContext) -> List[CandidateValue]: ...


    class Synthesizer(Protocol):
        """
        CandidateValue list -> CoreEvidenceRecord(s)
        - consensus, outlier handling, unit normalization, confidence scoring
        """
        def synthesize(self, candidates: List[CandidateValue], request: SearchRequest, context: SearchContext) -> List[CoreEvidenceRecord]: ...


    class GatePolicyEnforcer(Protocol):
        """
        정책/예산/품질 게이트 강제
        - egress policy(웹/공식 fetch/LLM 등)
        - quality gate(reporting_strict 기준)
        - stop condition(충족 시 조기 종료)
        """
        def check_egress(self, action: str, context: SearchContext, meta: Dict[str, Any]) -> None: ...
        def evaluate_candidates(self, candidates: List[CandidateValue], request: SearchRequest, context: SearchContext) -> Dict[str, Any]: ...
        def allow_commit_evidence(self, evidence: CoreEvidenceRecord, request: SearchRequest, context: SearchContext) -> Tuple[bool, Dict[str, Any]]: ...
        def should_stop(self, ledger: SearchProjectLedger, request: SearchRequest, context: SearchContext, phase: SearchPhase) -> bool: ...


    class SearchRunner(Protocol):
        """
        SearchPlan 실행 런타임(작은 orchestration)
        - phases loop
        - budgets/stop/replan
        - project ledger/progress ledger 갱신
        """
        def run(self, plan: SearchPlan, request: SearchRequest, context: SearchContext) -> List[CoreEvidenceRecord]: ...


    class QueryLearner(Protocol):
        """
        학습은 런타임에서 registry를 '즉시 변경'하지 않음.
        - query_trace를 memory_store에 기록
        - 오프라인에서 registry v3 -> v3.1로 승격
        """
        def record_trace(self, trace_event: Dict[str, Any]) -> None: ...
        def propose_registry_update(self, lookback_days: int = 30) -> Dict[str, Any]: ...


    class SearchKernel:
        """
        EvidenceEngine 내부에서 호출되는 Search subsystem의 facade
        """
        def __init__(
            self,
            registry: StrategyRegistry,
            planner: SearchPlanner,
            runner: SearchRunner,
            learner: QueryLearner,
        ):
            self.registry = registry
            self.planner = planner
            self.runner = runner
            self.learner = learner

        def fetch_evidence(self, request: SearchRequest, context: SearchContext) -> List[CoreEvidenceRecord]:
            # (1) registry_ref pin
            # (2) plan build
            # (3) run + gates
            # (4) trace record (learner)
            ...

---

## 2) Events/Trace 스키마 (재현성/감사용) + Ledger 연계

### 2.1 설계 원칙
- **SearchProgressLedger는 이벤트 스트림(append-only)** 을 기본으로 합니다.
- **SearchProjectLedger는 ref 중심의 결과/산출물 포인터**를 유지합니다.
- “학습”은 trace를 남기되, 런타임에서 strategy를 변경하지 않습니다. (run은 registry_digest/initial_plan_digest/plan_digest_chain로 pin)

### 2.2 Trace Envelope (런 전체 메타)

    {
      "trace_version": 1,
      "search_run_id": "SRCH-20251213-000001",
      "metric_id": "MET-TAM",
      "strategy_ref": {
        "registry_version": 3,
        "registry_digest": "sha256:...",
        "compiled_at": "2025-12-13T00:00:00Z"
      },
      "initial_plan_digest": "sha256:...",
      "final_plan_digest": null,
      "plan_digest_chain": ["sha256:..."],
      "policy_ref": "decision_balanced",
      "policy_digest": "sha256:...",
      "tool_registry_digest": "sha256:...",
      "effective_egress_digest": "sha256:...",
      "context_fingerprint": "sha256:...",     // canonicalized(SearchContext without volatile fields)
      "request_fingerprint": "sha256:...",     // canonicalized(SearchRequest)
      "started_at": "2025-12-13T01:02:03Z",
      "ended_at": null,
      "budget_initial": {
        "max_queries": 6,
        "max_fetches": 12,
        "max_time_sec": 20,
        "max_cost_usd": 0.02
      }
    }

### 2.3 Event 공통 스키마

    {
      "event_id": "EVT-...",
      "search_run_id": "SRCH-...",
      "ts": "2025-12-13T01:02:04Z",
      "type": "PlanBuilt | PlanRevised | QueryGenerated | SerpFetched | DocumentFetched | ExtractionDone | CandidateAccepted | CandidateRejected | GateEvaluated | PhaseStopped | EvidenceCommitted | RunCompleted | RunFailed",
      "phase_id": "generic_web",
      "payload": { ... },                      // type별 상세
      "budget_delta": {                        // 소비량(옵션)
        "queries_used": 1,
        "fetches_used": 0,
        "time_used_ms": 532,
        "cost_used_usd": 0.0002               // 비용을 실측할 수 없으면 null 허용
      }
    }

### 2.4 주요 이벤트 타입(필수) — payload 예시

#### PlanBuilt
    {
      "type": "PlanBuilt",
      "payload": {
        "initial_plan_digest": "sha256:...",
        "phases": ["authoritative", "generic_web"],
        "pinned_registry_digest": "sha256:..."
      }
    }

#### PlanRevised
    {
      "type": "PlanRevised",
      "payload": {
        "prev_plan_digest": "sha256:aaa",
        "next_plan_digest": "sha256:bbb",
        "proposed_by": "llm_tactic_controller | heuristic",
        "llm_call_ref": {                     // proposed_by=llm_tactic_controller인 경우에만 필요
          "prompt_artifact_id": "ART-...",
          "response_artifact_id": "ART-..."
        },
        "reason_codes": ["insufficient_high_quality_evidence", "budget_remaining_ok"],
        "delta_summary": {
          "phase_id": "generic_web",
          "fetch_top_k": {"from": 3, "to": 5},
          "llm_query": {"from": false, "to": true}
        }
      }
    }

#### QueryGenerated
    {
      "type": "QueryGenerated",
      "payload": {
        "language": "ko",
        "provider_id": "GenericWebSearch",
        "query_request_digest": "sha256:...",
        "query_artifact_id": "ART-...",       // query text + generator meta (ref-only)
        "generator": {
          "deterministic": true,
          "llm_used": false,
          "templates_used": ["{domain} {region} market size {year}"],
          "expansion_rules": ["synonyms", "reorder_terms"]
        }
      }
    }

#### SerpFetched
    {
      "type": "SerpFetched",
      "payload": {
        "provider_id": "GenericWebSearch",
        "provider_config_digest": "sha256:...",
        "query_request_digest": "sha256:...",
        "serp_artifact_id": "ART-...",        // provider raw response + normalized hits (ref-only)
        "serp_digest": "sha256:...",
        "language": "ko",
        "top_k": 8,
        "hit_count": 8,
        "hits": [
          {
            "url": "https://example.com/report",
            "canonical_url": "https://example.com/report",
            "rank": 1
          }
        ]
      }
    }

#### DocumentFetched
    {
      "type": "DocumentFetched",
      "payload": {
        "url": "https://example.com/report",
        "canonical_url": "https://example.com/report",
        "doc_id": "DOC-...",
        "artifact_id": "ART-...",
        "content_digest": "sha256:...",
        "http_status": 200
      }
    }

#### ExtractionDone
    {
      "type": "ExtractionDone",
      "payload": {
        "doc_id": "DOC-...",
        "extractor_id": "RegexTableExtractor@0.1",
        "candidates_found": 3,
        "candidate_summaries": [
          {
            "value": 1500000000000,
            "unit": "KRW",
            "as_of": "2024",
            "confidence": 0.72,
            "independence_key": "host:example.com|sha256:..."
          }
        ]
      }
    }

#### CandidateAccepted / CandidateRejected
    {
      "type": "CandidateAccepted",
      "payload": {
        "doc_id": "DOC-...",
        "candidate": {
          "metric_id": "MET-TAM",
          "value": 1500000000000,
          "unit": "KRW",
          "as_of": "2024",
          "confidence": 0.72,
          "independence_key": "host:example.com|sha256:..."
        },
        "reason_codes": ["year_match", "unit_match", "has_quote"]
      }
    }

    {
      "type": "CandidateRejected",
      "payload": {
        "doc_id": "DOC-...",
        "candidate": { "...": "..." },
        "reason_codes": ["no_year", "unit_ambiguous", "low_authority"]
      }
    }

#### GateEvaluated
    {
      "type": "GateEvaluated",
      "payload": {
        "policy_ref": "reporting_strict",
        "min_high_quality_evidence": 2,
        "current_high_quality": 1,
        "require_quote": true,
        "status": "not_met",
        "notes": { "missing": ["second_independent_source"] }
      }
    }

#### PhaseStopped
    {
      "type": "PhaseStopped",
      "payload": {
        "phase_id": "generic_web",
        "stop_reason": "gate_met | budget_exceeded | no_progress | time_exceeded",
        "evidence_count": 2
      }
    }

#### EvidenceCommitted
    {
      "type": "EvidenceCommitted",
      "payload": {
        "evidence_id": "EVD-...",
        "metric_id": "MET-TAM",
        "value": 1500000000000,
        "unit": "KRW",
        "as_of": "2024",
        "confidence": 0.81,
        "source_refs": {
          "doc_ids": ["DOC-...", "DOC-..."],
          "artifact_ids": ["ART-...", "ART-..."],
          "urls": ["...", "..."]
        }
      }
    }

#### RunCompleted / RunFailed
    {
      "type": "RunCompleted",
      "payload": {
        "status": "success",
        "final_plan_digest": "sha256:...",
        "plan_digest_chain": ["sha256:...", "sha256:..."],
        "evidence_ids": ["EVD-...", "EVD-..."],
        "summary": {
          "queries_used": 6,
          "fetches_used": 10,
          "time_used_ms": 18750,
          "cost_used_usd": 0.012
        }
      }
    }

    {
      "type": "RunFailed",
      "payload": {
        "status": "failed",
        "error_class": "EgressDenied | BudgetExceeded | ProviderError | ExtractionError",
        "message": "..."
      }
    }

### 2.5 Ledger 연계 규칙(강제)
- SearchProgressLedger.events = 위 이벤트 스트림 전체(append-only)
- SearchProjectLedger에는 다음만 기록(정본 포인터/요약)
  - pinned registry_ref
  - initial_plan_digest / (latest) plan_digest / plan_digest_chain
  - serp snapshots/doc snapshots/candidates/evidence_ids (ref 중심)
  - artifacts(ART) refs
- 원문/대량 데이터는 **ArtifactStore**에만 저장
- verify(계약 강제)에서 다음을 확인:
  - trace envelope의 registry_digest / plan_digest_chain / final_plan_digest가 일관적인지
  - policy_digest / tool_registry_digest / effective_egress_digest가 pin(고정)되어 있는지
  - QueryGenerated에서 LLM 사용 시 query_artifact_id가 존재하는지(재현성)
  - SerpFetched에서 serp_artifact_id/serp_digest가 존재하는지(재현성)
  - PlanRevised에서 proposed_by=llm_tactic_controller인 경우 llm_call_ref가 존재하는지(재현성)
  - EvidenceCommitted의 source_refs에 artifact_id가 존재하는지(재현성)
  - reporting_strict에서 gate 조건 미충족 EvidenceCommitted가 없는지(정책 강제)

---

## 3) GenericWebSearch Provider 추상화 (serpapi / tavily / google_cse 교체 가능)

### 3.1 Provider Registry / Adapter 구조

    @dataclass(frozen=True)
    class ProviderConfig:
        provider_id: str
        adapter: str                      # "serpapi" | "tavily" | "google_cse" ...
        api_key_ref: Optional[str]        # secret manager key
        default_timeout_sec: int = 10
        rate_limit_qps: float = 1.0
        burst: int = 2
        cache_ttl_sec: int = 86400
        cost_model: Optional[Dict[str, Any]] = None   # 없으면 비용 측정/게이트는 optional
        locale_mapping: Dict[str, str] = field(default_factory=dict)
        provider_config_digest: str = ""   # sha256:... (canonicalized ProviderConfig)
        notes: Dict[str, Any] = field(default_factory=dict)

    class ProviderRegistry(Protocol):
        def get(self, provider_id: str) -> SearchProvider: ...
        def get_config(self, provider_id: str) -> ProviderConfig: ...


### 3.2 SearchProvider 표준 인터페이스(교체 가능)

    class SearchProvider(Protocol):
        provider_id: str

        def search(self, req: SearchQueryRequest) -> SerpSnapshotRef: ...

        def supports(self, capability: str) -> bool:
            """
            capabilities examples:
              - "web_search"
              - "news_search"
              - "site_filter"
              - "time_filter"
              - "safe_search"
            """
            ...

### 3.3 Adapter별 구현 스켈레톤(예시)

#### SerpAPI Adapter

    class SerpApiProvider:
        provider_id = "GenericWebSearch"

        def __init__(self, cfg: ProviderConfig, http_client, cache, rate_limiter):
            self.cfg = cfg
            self.http = http_client
            self.cache = cache
            self.rate = rate_limiter

        def search(self, req: SearchQueryRequest) -> SerpSnapshotRef:
            # 1) egress policy는 상위 Gate에서 이미 체크(또는 여기서도 방어)
            # 2) cache key: (adapter, req.region, req.language, req.query, req.top_k, req.filters)
            # 3) rate limit
            # 4) request build
            # 5) response normalize -> SerpSnapshotRef + serp_artifact_id 생성(원본은 ART에 저장)
            ...

        def supports(self, capability: str) -> bool:
            return capability in {"web_search", "time_filter", "site_filter"}

#### Tavily Adapter

    class TavilyProvider:
        provider_id = "GenericWebSearch"

        def __init__(self, cfg: ProviderConfig, http_client, cache, rate_limiter):
            ...

        def search(self, req: SearchQueryRequest) -> SerpSnapshotRef:
            # tavily 결과 스키마를 SearchHitRef/SerpSnapshotRef로 normalize
            ...

        def supports(self, capability: str) -> bool:
            return capability in {"web_search"}

#### Google Custom Search Adapter

    class GoogleCseProvider:
        provider_id = "GenericWebSearch"

        def __init__(self, cfg: ProviderConfig, http_client, cache, rate_limiter):
            ...

        def search(self, req: SearchQueryRequest) -> SerpSnapshotRef:
            # cse params: cx, key, lr/hl/gl 등 locale mapping
            ...

        def supports(self, capability: str) -> bool:
            return capability in {"web_search", "site_filter"}

### 3.4 URL Canonicalization / 중복 제거(필수 유틸)

    def canonicalize_url(url: str) -> str:
        """
        - utm_*, fbclid, gclid 등 tracking params 제거
        - http -> https 정규화(가능한 범위)
        - trailing slash 규칙 통일
        - fragment(#...) 제거
        """
        ...

    def dedupe_hits(hits: List[SearchHitRef]) -> List[SearchHitRef]:
        """
        - canonical_url 기준 중복 제거
        - rank는 가장 높은(작은) 값 유지
        """
        ...

### 3.5 Provider 실행 정책(권장)
- Provider는 “검색(SERP)”까지만 담당
- 문서 획득(fetch)은 **DocumentFetcher**가 전담(캐시/스냅샷/아티팩트 저장 포함)
- Provider 교체는 config(registry)로만 가능해야 하며, 런에는 provider_config_digest를 trace로 남김

### 3.6 Provider Error Taxonomy(운영 안정성)
- Provider는 예외를 표준화된 에러로 래핑해 상위(SearchRunner/Gate)가 정책적으로 처리

    ProviderError = {
      "type": "RateLimited | Timeout | AuthFailed | BadRequest | UpstreamError | Unknown",
      "retryable": true/false,
      "http_status": 429/500/...
    }

권장 처리:
- retryable이면 exponential backoff(예산 내)
- 반복 실패 시 phase degrade(다른 provider로 fallback) 또는 stop

---

## 4) DocumentFetcher 안전/컴플라이언스 가드레일 (필수)

DocumentFetcher는 “URL에서 문서를 가져와 ART로 저장”하기 때문에 보안/법적 리스크가 큽니다.
따라서 아래 항목은 **구현 시 반드시 강제(하드 가드레일)** 해야 합니다.

### 4.1 네트워크/SSRF 안전장치(필수)

- **URL 스킴 allowlist**: `http`/`https`만 허용
- **DNS/IP 검증(SSRF 방어)**: loopback/사설/예약 대역 차단 + DNS rebinding 방어
- **포트 제한**: 기본은 80/443만 허용(정책으로 확장 가능하더라도 기본은 deny)
- **redirect 제한**: 최대 횟수/도메인 변경 정책(예: denylist로 막기)
- **timeout/max_bytes**: 문서 종류별 최대 바이트/시간 제한(대형 파일/무한 스트림 방지)

### 4.2 콘텐츠/MIME 정책(필수)

- **MIME allowlist**(예시): `text/html`, `application/pdf`, `text/plain`
- **실행 가능/바이너리 파일 차단**: 예) `application/octet-stream`, `application/x-msdownload` 등
- **HTML 정규화/텍스트 추출 시**: script/style/iframe 제거, PII/민감정보 정책(필요 시) 적용

### 4.3 저장/노출(SSoT) 원칙(필수)

- 문서 원문/대량 텍스트는 **ArtifactStore(ART-*)** 에만 저장
- ledger/event에는 **artifact_id + digest + 최소 요약만** 저장(ref-only 유지)
- 보관/공유 정책(예: retention 기간, 외부 노출 금지)은 정책(PolicyEngine)으로 제어

### 4.4 최소 테스트 체크리스트(필수)

- SSRF(내부 IP/localhost/metadata endpoint) 차단
- redirect loop/too-many-redirects 차단
- max_bytes 초과 차단
- denylist 도메인 차단
- MIME allowlist 외 차단

---

## 5) LLM 전술(자율 컨트롤러) 레이어 — 결과를 만드는 부분 (Production-minimal v1)

이 설계의 목적은 “파이프라인을 촘촘히 통제하는 시스템”이 아니라,
**LLM이 다양한 상황에 맞춰 전술을 바꾸며 성과를 내되**, 최소 커널이 안전/예산/감사/재현성을 보장하는 것입니다.

### 5.1 핵심 원칙(저복잡도)

- **LLM은 ‘행동을 실행’하지 않고 ‘행동을 제안’합니다.**
  - 실행은 항상 SearchRunner가 하며, GatePolicyEnforcer가 최종 허용/거부합니다.
- **LLM 호출은 “막혔을 때만”**(no_progress, gate_not_met, budget_remaining_ok) 수행합니다.
  - 기본은 deterministic rules + phase 설계로 먼저 진행하고, 필요 시 LLM이 확장/재계획을 제안합니다.

### 5.2 LLM 입력 계약: SearchStateSummary (ref-only)

LLM에게는 원문/대량 데이터가 아니라, **현 상태를 요약한 구조화 신호**만 제공합니다.
(문서 원문/쿼리 텍스트가 필요하면 ART로 제공하고, LLM 입력에는 ART 참조만 포함)

    {
      "trace_version": 1,
      "metric_id": "MET-TAM",
      "policy_ref": "decision_balanced",
      "phase_id": "generic_web",
      "plan_digest_chain_tail": "sha256:...",
      "budget_remaining": {"queries": 3, "fetches": 6, "time_ms": 12000, "cost_usd": 0.01},
      "progress": {
        "queries_generated": 6,
        "serp_snapshots": 2,
        "documents_fetched": 5,
        "candidates_total": 4,
        "high_quality_candidates": 1,
        "independent_sources": 1
      },
      "gate_latest": {
        "status": "not_met",
        "missing": ["second_independent_source", "year_match"]
      },
      "recent_failures": [
        {"stage": "DocumentFetcher", "error_type": "Timeout", "count": 2},
        {"stage": "Extractor", "error_type": "NoUnit", "count": 3}
      ],
      "refs": {
        "query_artifact_ids": ["ART-..."],
        "serp_artifact_ids": ["ART-..."],
        "document_artifact_ids": ["ART-..."]
      }
    }

### 5.3 LLM 출력 계약: TacticProposal (PlanRevised로 귀결)

LLM은 “다음 행동”을 **Plan delta**로 제안합니다.
제안은 PlanRevised 이벤트로 기록되며(재현성), SearchRunner는 이를 정책/예산/게이트로 검증 후 적용합니다.

    {
      "proposed_actions": [
        {
          "action": "increase_fetch_top_k",
          "phase_id": "generic_web",
          "from": 3,
          "to": 5,
          "expected_gain": "more_independent_sources",
          "risk": "higher_fetch_cost"
        },
        {
          "action": "enable_llm_query_expansion",
          "phase_id": "generic_web",
          "expected_gain": "better_query_diversity",
          "risk": "llm_cost"
        }
      ],
      "stop_recommendation": {
        "should_stop": false,
        "reason": "budget_remaining_ok"
      }
    }

### 5.4 GatePolicyEnforcer가 강제해야 하는 것(LLM 제안 검증)

- **egress/budget 위반 제안은 즉시 거부**
- **reporting_strict**에서 아래 중 하나라도 충족하지 못하면 EvidenceCommitted를 금지
  - 최소 독립 출처 수(min_independent_sources)
  - 연도/기간 정합(year/as_of match)
  - 단위 정합(unit match)
  - 근거 ref 존재(artifact_id + span_quote_ref)

### 5.5 구현 최소 단위(Production-minimal v1) 확정

- **Provider**: GenericWebSearch 1개만 “제품 기준”으로 먼저 구현(권장: `google_cse`)
  - provider 교체 가능성(serpapi/tavily)은 인터페이스/레지스트리로 열어두되, v1에서 동시 다중 구현은 지양(운영 복잡도↑)
- **Fetcher**: HTML/PDF 최소 지원 + 강제 가드레일(SSRF/MIME/max_bytes/timeout/redirect)
- **Extractor**: 규칙 기반 1개(우선) + (선택) LLM aligner 1개(정책 허용 시에만)
- **Synthesizer/Gate**: `independence_key` 기반 최소 gate + consensus(median) + outlier 완화(간단한 기준)
- **LLM 전술 호출**: `gate_not_met` + `budget_remaining_ok` + `no_progress` 중 일부 조건에서만 PlanRevised 제안

### 5.6 Production-minimal v1 확정 결정사항(복잡도↓/운영 안정성↑)

아래 항목은 “구현 선택지”가 아니라 **v1에서 고정하는 규칙**입니다. (문서/코드/테스트의 기준)

- **ID 스코프(운영 추적)**:
  - **`SRCH-*`**: 전역 유니크 ID (run 단위 검색 실행 추적용)
  - **`DOC-*`**: 전역 유니크이되 **content-addressed** (정규화 본문 digest 기반)
    - 권장: `doc_id = "DOC-" + short_hash(content_digest)`<br>
      (`content_digest` = normalized_text_digest, `raw_bytes_digest`는 optional)
- **SSoT 경계(재현/감사)**:
  - **정본(SSoT) = events + ART(artifact)**<br>
    SearchProgressLedger의 이벤트 스트림과, 그 이벤트가 참조하는 아티팩트(쿼리/SERP/문서/인용)가 정본입니다.
  - **ledger_store는 derived cache(폐기 가능)**<br>
    SearchProjectLedger/SearchProgressLedger 스냅샷을 저장하더라도, 이는 UI/조회 성능용 캐시이며 정본이 아닙니다.
- **Query 재현성(조건 분기 제거)**:
  - **실행된 모든 query는 항상 `query_artifact_id`를 생성/저장**합니다.
    - deterministic template로 만든 쿼리도 예외 없이 ART로 저장(운영/디버깅 단순화)
- **독립성 키(`independence_key`)의 v1 정의(단순/강력)**:
  - 기본 규칙: `publisher_or_host + content_digest`
    - 예: `publisher:McKinsey|sha256:<content_digest>`<br>
      (publisher 추출 실패 시) `host:example.com|sha256:<content_digest>`
  - v1에서는 near-duplicate clustering(simhash/minhash 등)은 하지 않습니다. (v2 후보)

---

## 6) 구현 TODO (Production-minimal v1)

아래 TODO는 “낮은 복잡도 + 프로덕션 안정성”을 목표로, **커널부터 안전하게 닫고(SSoT/정책/가드레일)** 그 위에 전술(LLM)을 얹는 순서로 구성합니다.

### 6.1 P0 — 커널/SSoT/정책 핀닝(가장 먼저)

- [ ] **SSV3-01 StrategyRegistry v3 구현(버전/다이제스트 pinning)**
  - **목표**: YAML registry → compiled registry → `StrategyRef(registry_digest)` 고정
  - **수용기준**: 동일 입력이면 digest가 항상 동일, unknown provider/phase는 로드 단계에서 실패
  - **테스트**: digest 안정성(스냅샷), 잘못된 스키마/누락키 validation

- [ ] **SSV3-02 Trace/Event writer(append-only) + “ref-only” 계약 검증**
  - **목표**: trace envelope + events(JSONL) 기록, 원문/대량 텍스트는 ART에만 저장
  - **수용기준**: 이벤트/ledger에 query_text/snippet/html/pdf 원문이 직접 들어가지 않음
  - **테스트**: 이벤트 payload에 금지 필드가 들어오면 실패(계약 테스트)

- [ ] **SSV3-03 QueryArtifact 생성 규칙(항상 저장) + request_digest 정규화**
  - **목표**: 실행된 모든 query에 대해 `query_artifact_id` 생성, `SearchQueryRequest.request_digest` 계산
  - **수용기준**: LLM/비LLM 관계없이 QueryGenerated 이벤트는 `query_artifact_id` 포함
  - **테스트**: deterministic query에도 artifact 생성됨을 검증

- [ ] **SSV3-04 GenericWebSearch Provider(google_cse) + 캐시/레이트리밋/에러 표준화**
  - **목표**: provider → `SerpSnapshotRef` + `serp_artifact_id` 생성(원본은 ART)
  - **수용기준**: provider 오류가 표준 taxonomy로 래핑되어 상위에서 정책적으로 처리 가능
  - **테스트**: HTTP 모킹으로 정상/429/timeout/authfail 케이스, 캐시 hit 동작

- [ ] **SSV3-05 DocumentFetcher (SSRF/MIME/max_bytes/redirect) 강제 + DOC(content-addressed)**
  - **목표**: URL → `DocumentSnapshot(doc_id, content_digest, artifact_id)` 생성(원문은 ART)
  - **수용기준**: SSRF/내부 IP/redirect 과다/MIME 비허용/max_bytes 초과는 차단
  - **테스트**: SSRF/redirect loop/max_bytes/MIME deny 케이스(필수)

### 6.2 P1 — 추출/합성/게이트(품질을 닫는다)

- [ ] **SSV3-06 CandidateExtractor v1(규칙 기반) + span_quote_ref(ART)**
  - **목표**: 문서에서 수치/단위/기간 후보 추출, 인용은 ART로 저장 후 ref만 유지
  - **수용기준**: `CandidateValue.independence_key`가 v1 정의를 따름
  - **테스트**: 샘플 문서 텍스트(HTML/PDF 추출본)로 단위/연도 매칭 케이스

- [ ] **SSV3-07 Synthesizer v1(consensus + outlier 완화) → CoreEvidenceRecord**
  - **목표**: 후보 → `cmis_core.types.EvidenceRecord` 생성(메타에 search_v3 남김)
  - **수용기준**: consensus가 결정적이고, 입력 후보가 같으면 출력 EvidenceRecord도 결정적
  - **테스트**: outlier 포함 케이스에서 median 기반 결과가 안정적으로 선택

- [ ] **SSV3-08 GatePolicyEnforcer v1(reporting_strict/decision_balanced 차등)**
  - **목표**: `min_independent_sources`, unit/year/quote 조건 등 핵심 게이트 강제
  - **수용기준**: reporting_strict에서 게이트 미충족 시 EvidenceCommitted 금지
  - **테스트**: policy_ref별 허용/거부 케이스

### 6.3 P2 — EvidenceEngine 통합/회귀 방지/운영

- [ ] **SSV3-09 SearchRunner/SearchKernel v1 구현(phase loop + stop/replan)**
  - **목표**: phases 실행, 이벤트 기록, stop condition, (조건부) PlanRevised
  - **수용기준**: budget/egress 위반 없이 종료하며, plan_digest_chain이 일관됨
  - **테스트**: “gate_not_met → replan → gate_met” 시나리오

- [ ] **SSV3-10 EvidenceEngine 연결(기존 소스/정책과 공존)**
  - **목표**: EvidenceEngine에서 SearchKernel을 호출해 EvidenceRecord를 반환/캐시에 저장
  - **수용기준**: 기존 소스 체계와 충돌 없이 선택적으로 작동(설정/정책으로 on/off)
  - **테스트**: 기존 테스트 회귀 없이 통과 + Search v3 경로 신규 단위 테스트

- [ ] **SSV3-11 Run export/검증(Verifier) 연결**
  - **목표**: trace envelope/ART refs/plan_digest_chain/policy digest pinning 검증
  - **수용기준**: verifier가 “재현 불가능 상태(ART 누락 등)”를 탐지하고 diff 보고
  - **테스트**: ART 누락/plan_digest_chain 불일치/egress 위반 시 실패

- [ ] **SSV3-12 (선택) QueryLearner v1: trace 적재 + 오프라인 registry update 제안**
  - **목표**: 런타임 무음 변경 금지(온라인 변경 0), 오프라인에서만 승격 제안
  - **수용기준**: learner는 제안만 생성하고, 런타임 registry를 직접 수정하지 않음
  - **테스트**: lookback 기반 제안 생성 스모크 테스트
