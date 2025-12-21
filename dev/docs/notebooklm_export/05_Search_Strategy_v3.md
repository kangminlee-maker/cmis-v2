# Search Strategy v3 구현

**생성일**: 2025-12-21 11:28:56
**목적**: 3단계 검색 전략 (SERP → Document → Synthesis)

---

## 1. Search v3 아키텍처

```
Query → SERP Search → Candidate Extract → Document Fetch → Synthesize → Evidence
```

---

## candidate

### 모듈 설명

```
Search Strategy v3 candidate models (SSV3-06).

ref-only:
- CandidateValue는 원문/인용 텍스트를 직접 포함하지 않습니다.
- 인용은 ArtifactStore(ART)로 저장하고 span_quote_ref로만 참조합니다.
```

### 주요 클래스

#### `SearchRequest`

v3 search request의 최소 단위(추출 단계에 필요한 필드만).

#### `CandidateValue`

---

## candidate_extractor

### 모듈 설명

```
Rule-based CandidateExtractor (SSV3-06).

Production-minimal v1 목표:
- 문서(정규화 텍스트)에서 수치/단위/기간 후보를 규칙 기반으로 추출
- ref-only: 인용 텍스트는 ART로 저장하고 span_quote_ref로만 참조
```

### 주요 클래스

#### `RuleBasedCandidateExtractor`

규칙 기반 CandidateExtractor (v1).

**Public 메서드**:

```python
def extract(self, doc: DocumentSnapshot, request: SearchRequest) -> List[CandidateValue]
```
문서에서 CandidateValue 후보를 추출합니다.

---

## document_fetcher

### 모듈 설명

```
DocumentFetcher with safety/compliance guardrails (SSV3-05).

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 4)

Production-minimal v1:
- SSRF 방지(DNS/IP 검증, loopback/private/reserved 차단)
- scheme allowlist(http/https), port allowlist(80/443)
- redirect 제한 + redirect 대상도 동일하게 검증
- MIME allowlist(text/html, text/plain, application/pdf)
- timeout/max_bytes 강제
- DOC id: content-addressed (DOC-<short_hash(normalized_text_digest)>)
```

### 주요 클래스

#### `DocumentFetchError`

문서 fetch/검증 실패.

#### `DocumentSnapshot`

---

## gate

### 모듈 설명

```
Gate/Policy enforcement for Search Strategy v3 (SSV3-08).

Production-minimal v1:
- reporting_strict: EvidenceCommitted는 최소 품질/독립성/정합 조건을 만족해야 함
- decision_balanced / exploration_friendly: 완화된 조건(운영 단순화)
```

### 주요 클래스

#### `GateReport`

#### `GatePolicyEnforcerV1`

Search v3 정책/품질 게이트.

**Public 메서드**:

```python
def evaluate_candidates(self, candidates: List[CandidateValue], request: SearchRequest) -> GateReport
```

```python
def allow_commit_evidence(self, evidence: EvidenceRecord, candidates: List[CandidateValue], request: SearchRequest) -> Tuple[(bool, Dict[str, Any])]
```

```python
def should_stop(self, candidates: List[CandidateValue], request: SearchRequest) -> bool
```
stop condition: 게이트 충족 시 phase 종료.

---

## generic_web_search

### 모듈 설명

```
GenericWebSearch provider abstraction (SSV3-04).

Production-minimal v1:
- adapter: google_cse (Google Custom Search)
- caching: in-memory TTL cache (provider instance scope)
- rate limiting: token bucket (qps/burst)
- error taxonomy: ProviderError(type/retryable/http_status)

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 3, 3.6)
```

### 주요 클래스

#### `ProviderError`

Provider 표준 오류.

type:
  - RateLimited | Timeout | AuthFailed | BadRequest | UpstreamError | Unknown

#### `_TTLCache`

간단한 in-memory TTL cache.

**Public 메서드**:

```python
def get(self, key: str) -> Optional[Any]
```

```python
def set(self, key: str, value: Any) -> None
```

---

## query

### 모듈 설명

```
Search Strategy v3 query request + query artifact (SSV3-03).

핵심 규칙(Production-minimal v1):
- 실행된 모든 query는 항상 query_artifact_id(ART-*)로 저장합니다. (LLM/비LLM 분기 없음)
- request_digest는 query 내용/파라미터에 대해 결정적으로 계산합니다.
- digest 계산에는 query_artifact_id 같은 런타임 생성 ID를 포함하지 않습니다.
```

### 주요 클래스

#### `SearchQueryRequest`

Provider에 전달되는 검색 요청.

NOTE:
- 런타임에서는 query 문자열이 필요하지만,
  ledger/event에는 query_text를 직접 저장하지 않고 artifact/ref로만 저장합니다.

---

## registry

### 모듈 설명

```
Search Strategy v3 registry (SSV3-01).

목표:
- YAML 기반 전략 레지스트리를 로드/검증하고, 결정적(deterministic) digest를 pinning 합니다.
- 런타임은 registry_digest를 pin하여 재현성을 확보합니다.

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 1.3 StrategyRegistry, 5.6 확정 결정)
```

### 주요 클래스

#### `StrategyRegistryError`

Search Strategy v3 registry validation/compile 오류.

#### `StrategyRef`

Versioned registry reference pinned to a digest.

---

## runner

### 모듈 설명

```
SearchRunner/SearchKernel v1 (SSV3-09).

Production-minimal v1:
- phase loop (registry plan template 기반)
- query -> serp -> document fetch -> extraction -> gate -> synthesize -> commit
- replan(heuristic): gate_not_met 이고 hit 여유가 있으면 fetch_top_k를 증가시키는 1회성 수정
```

### 주요 클래스

#### `SearchRunResult`

#### `SearchKernelV1`

EvidenceEngine에서 호출되는 Search v3 facade.

**Public 메서드**:

```python
def fetch_evidence(self) -> SearchRunResult
```

---

## serp

### 모듈 설명

```
Search Strategy v3 SERP models (SSV3-04 base types).

ref-only 원칙:
- SearchHitRef에는 title/snippet 같은 원문을 포함하지 않습니다.
- SERP 원본(title/snippet 포함)은 ArtifactStore(ART-*)에 저장하고,
  ledger/event에는 serp_artifact_id + serp_digest + SearchHitRef만 남깁니다.
```

### 주요 클래스

#### `SearchHitRef`

#### `SerpSnapshotRef`

---

## synthesizer

### 모듈 설명

```
Synthesizer (CandidateValue -> Core EvidenceRecord) (SSV3-07).

Production-minimal v1:
- consensus: median (after best-effort outlier removal)
- confidence: candidate_confidence + variance + count 기반 간단 산정
```

### 주요 클래스

#### `SynthesizerV1`

CandidateValue list를 EvidenceRecord로 합성합니다.

**Public 메서드**:

```python
def synthesize(self, candidates: List[CandidateValue], request: SearchRequest) -> List[EvidenceRecord]
```

---

## trace

### 모듈 설명

```
Search Strategy v3 trace/event writer (SSV3-02).

설계 원칙:
- SearchProgressLedger는 append-only 이벤트 스트림을 기본으로 합니다.
- ledger/event에는 원문/대량 텍스트를 저장하지 않습니다(ref-only).
- 원문(쿼리 텍스트, SERP raw, 문서 본문/HTML/PDF, 인용)은 ArtifactStore(ART-*)로만 저장합니다.

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 2, 1.0 ref-only 규칙)
```

### 주요 클래스

#### `RefOnlyViolationError`

ref-only 계약 위반(원문/대량 데이터가 event/ledger payload에 포함됨).

#### `SearchEvent`

SearchProgressLedger event (append-only).

---

## url_utils

### 모듈 설명

```
URL canonicalization utilities (Search Strategy v3).

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 3.4)
```

---

## verify

### 모듈 설명

```
Search Strategy v3 trace verifier (SSV3-11).

목표:
- trace envelope + events.jsonl(ART) 기반으로 최소 재현성/정합성을 검증합니다.
- ref-only 원칙에 따라, 검증 대상은 모두 ART 참조/다이제스트입니다.
```

---
