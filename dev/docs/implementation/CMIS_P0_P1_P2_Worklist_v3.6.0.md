# CMIS 실행 구현 작업리스트 (v3.6.0)

**작성일**: 2025-12-13
**범위**: `P0 → P1 → P2` (우선순위) + `20251213_NEXT_SESSION_GUIDE.md`의 A/B/C 포함

---

## 진행 규칙 (기능 단위 운영)

각 기능 단위는 아래 순서로 진행합니다.

- **D (Design 고도화)**
  - contract(`cmis.yaml`/`config/*.yaml`) ↔ 실행 경로(Engine/Kernel/CLI) 정합성 확정
  - 입력/출력 키, 실패 정책, SSoT(어디에 무엇을 기록하는가) 명시
  - 완료 기준(acceptance criteria) 정의

- **I (Implementation + Tests)**
  - 구현 → 단위/통합 테스트 → 정합성 검사 → 회귀 확인

**정합성 체크**:

```bash
python3 -m cmis_cli config-validate --check-registry --check-patterns --check-workflows
```

**핵심 테스트**:

```bash
pytest -q dev/tests/unit/test_cursor_agent_interface_v2.py dev/tests/unit/test_spec_registry_consistency.py
```

---

## P0: 정의=실행 (Workflow Runtime + run_mode)

### P0-1. Workflow Runtime v1 (Step Dispatcher)

- **D**
  - `config/workflows.yaml` step 실행 모델 확정
    - `call` 문자열 → 엔진 API 매핑 규칙
    - `@input.*`, `@prev.*`, `@metric_sets.*` 해석 규칙
    - step output 표준 키(다음 step 참조용) 정의
  - 오류/부분완료 정책 확정 (fail-close vs partial)
  - 최소 스펙: `strategy_design`, `reality_monitoring`까지 실행 가능해야 함

- **v1 스펙(Phase 1, 명시 규칙)**
  - **ref 해석**
    - `@input.<key>`: workflow 입력 dict에서 조회
    - `@prev.<key>`: 이전 step의 raw output에서 조회
    - `@metric_sets.<set_name>`: `CMISConfig.get_metric_set(set_name)`로 확장
  - **call → 실행/출력 키(표준)**
    - `world_engine.snapshot`
      - 입력: `domain_id`, `region`, `segment?`, `as_of?`, `project_context_id?`
      - raw output: `reality_snapshot_ref`
      - json output: `reality_snapshot.meta`
    - `pattern_engine.match_patterns`
      - 입력: `reality_snapshot_ref`, `project_context_id?`
      - 구현: `PatternEngineV2.match_patterns(snapshot.graph, ...)`
      - raw output: `pattern_match_set_ref`, `pattern_matches`
      - json output: `pattern_matches[]`
    - `pattern_engine.discover_gaps`
      - 입력: `reality_snapshot_ref`, `project_context_id?`, `precomputed_matches?`
      - 구현: `PatternEngineV2.discover_gaps(snapshot.graph, ...)`
      - raw output: `gap_set_ref`, `gap_candidates`
      - json output: `gap_candidates[]`
    - `value_engine.evaluate_metrics`
      - 입력: `metric_requests`, `policy_ref?`, `project_context_id?`, `reality_snapshot_ref?`
      - graph 확보 규칙:
        - `reality_snapshot_ref`가 없으면 **이전 snapshot(prev)** 사용
        - 그래도 없으면 `inputs.domain_id + inputs.region`이 있을 때 **auto snapshot** 생성
      - metric_requests 확장:
        - `"@metric_sets.*"` 또는 list 혼합을 metric_id 리스트로 flatten 후 `MetricRequest[]` 생성
      - raw output: `value_bundle_ref`, `value_records`, `value_program`, `metric_evals` (+ auto snapshot 시 `reality_snapshot_ref`)
      - json output: `value_records[]`, `value_program` (+ auto snapshot 시 `reality_snapshot.meta`)
    - `strategy_engine.search_strategies`
      - 구현: `StrategyEngine.search_strategies_api(...)` 호출 후 d_graph의 `strategy_ids`를 함께 노출
      - raw/json output: `strategy_set_ref`, `strategy_ids`
    - `strategy_engine.evaluate_portfolio`
      - raw/json output: `portfolio_eval_ref`
    - `learning_engine.update_from_outcomes`
      - 구현: `LearningEngine.update_from_outcomes_api(outcome_ids)`
      - raw/json output: `learning_results`
  - **직렬화 규칙**
    - Workflow CLI는 `json.dumps()`로 출력하므로, 최종 반환 dict는 **JSON 직렬화 가능**해야 함
    - raw object(snapshot/graph 등)는 `outputs`에 직접 노출하지 않고, meta/summary만 노출

- **I**
  - `cmis_core/workflow.py`에 generic runner 구현(Phase 1)
  - 단위테스트: ref 해석 + step dispatch + metric_sets flatten

- **완료 기준**
  - `strategy_design`, `reality_monitoring` workflow가 정의대로 실행되고 결과 dict를 반환

### P0-2. RolePlane 최소 enforcement (allowed_workflows)

- **D**
  - role 위반 시 즉시 차단 + 사유 기록(run_store/ledger 중 최소 1곳)

- **I**
  - Kernel 또는 WorkflowOrchestrator 진입점에서 role 기반 workflow 실행 제한
  - 단위테스트: 허용되지 않은 workflow 실행이 차단되는지

### P0-3. Kernel run_mode 반영 (autopilot/manual/approval_required)

- **D**
  - `manual`: 1 task(또는 1 iteration) 실행 후 중단 + next_step_suggestion 기록
  - `approval_required`: plan까지만 생성하고 실행 전 중단(승인 대기)

- **v1 스펙(Phase 1, 명시 규칙)**
  - **autopilot**
    - 현행 루프 유지: verify → replan → execute 반복
  - **approval_required**
    - verify/replan은 수행하되 **task 실행 직전에 중단**
    - `progress_ledger.loop_flags.waiting_approval = True`
    - `progress_ledger.overall_status = "incomplete"`
    - `next_step_suggestion`에 “승인 후 재실행(autopilot/manual)”을 위한 작업 목록 요약 포함
  - **manual**
    - 최대 1 task 실행 후, 다음 verify/replan에서 **추가 task 실행 직전에 중단**
    - `progress_ledger.loop_flags.manual_pause = True`
    - `progress_ledger.overall_status = "incomplete"`
    - `next_step_suggestion`은 replanner가 만든 제안을 우선 사용하고, 없으면 기본 제안 기록

- **I**
  - `cmis_core/orchestration/kernel.py` 실행 루프 분기 구현
  - CLI 옵션 노출(`cursor ask` 또는 `workflow run`)
  - 단위/통합 테스트: run_mode별 실행량 제한 검증

---

## P1: SSoT 구멍 메우기 (Stores + Engine 연결)

### P1-1. StoragePaths/스토리지 루트 통일

- **D**
  - `.cmis/` 하위 store별 경로/파일명 확정
  - `CMIS_STORAGE_ROOT`가 있으면 그 경로를 root로 사용(테스트/격리), 없으면 `project_root`
  - 제안 (Phase 1):
    - `.cmis/db/`
      - `runs.db`, `ledgers.db` (기존)
      - `contexts.db`, `outcomes.db`, `artifacts.db` (추가)
    - `.cmis/runs/` (export view)
    - `.cmis/artifacts/` (파일 기반 object_store)

- **I**
  - store들이 `CMIS_STORAGE_ROOT`를 따르도록 통일

### P1-2. ProjectContextStore (FocalActorContext PRJ-*)

- **D**
  - DB: `.cmis/db/contexts.db`
  - 스키마(최소): `project_context_id`, `version`, `created_at`, `previous_version_id`, `record_json`
  - API: save/get_latest/get_by_version

- **I**
  - `cmis_core/stores/project_context_store.py` 구현 + 테스트
  - `cmis_core/context_binding.py`가 store 우선 로딩하도록 연결

### P1-3. OutcomeStore + LearningEngine 연동

- **D**
  - DB: `.cmis/db/outcomes.db`
  - Outcome 최소 필드/lineage 정책 확정
  - LearningEngine은 `_load_outcome/_load_project_context`에서 store 우선 조회 (없으면 in-memory fallback)

- **I**
  - `cmis_core/stores/outcome_store.py` 구현 + 테스트
  - `learning_engine.update_from_outcomes`가 store를 읽도록 연결

### P1-4. ArtifactStore 통일

- **D**
  - samples/중간산출물은 artifact_store를 정본으로
  - FS: `.cmis/artifacts/`
  - Meta DB(선택): `.cmis/db/artifacts.db` (artifact_id → path/meta/lineage)

- **I**
  - `cmis_core/stores/artifact_store.py` 구현 + 테스트
  - `uncertainty_propagator`의 저장 경로를 artifact_store로 통일

---

## P2: 감사/제약 강화 (Tool/LLM + SearchStrategy 정리)

### P2-1. tool_and_resource_registry enforcement 확장

- **D**
  - 허용/차단/안전등급(safety) 적용 지점 정의
  - 표준 tool_call 이벤트 스키마 정의 (run_store 기록 포함)

- **v1 스펙(Phase 1, 명시 규칙)**
  - **허용/차단(allowlist)**
    - `cmis.yaml planes.orchestration_plane.tool_and_resource_registry.tools[*].id`에 등록된 tool_id만 “허용”으로 간주
    - tool registry 자체가 비어있으면(backward compatibility) allow-all
  - **적용 지점(Phase 1 최소)**
    - EvidenceEngine 소스 구성 시:
      - `web_search` 미허용 → GoogleSearchSource 등록 금지
      - `http_fetch` 미허용 → KOSIS/ECOS/WorldBank/FSC 기업재무정보 등록 금지
    - (Phase 2+) LLM/외부 도구 호출까지 동일한 원칙으로 확장
  - **표준 tool_calls 이벤트 (run_store.events)**
    - event.type = `tool_calls`
    - payload:
      - `task_id`, `task_type`
      - `tool_calls[]`: 요약 레코드
        - `ts`, `tool_id`, `operation`, `count`, `safety`
        - optional: `source_id`, `source_tier`
    - 원칙: raw I/O는 Phase 2+에서(PII/비용) 별도 정책 하에 기록

- **I**
  - Evidence/LLM/tool 호출이 registry 제약을 실제로 반영
  - run_store/ledger에 기록되고 export로 노출

### P2-2. LLM runtime 설정 경로 정렬

- **D**
  - `cognition_plane.llm_runtime`를 단일 정본으로 확정

- **I**
  - `LLMService`가 cmis.yaml의 llm_runtime만 사용하도록 정렬 + 테스트

### P2-3. SearchStrategy v2 결론

- **D**
  - SearchPlanner/Executor/Builder를 EvidenceEngine에 연결 vs experimental 격리 결정
  - 결정(Phase 1): **experimental 격리**
    - 이유: `SearchExecutor._execute_single_query()`가 미구현(항상 None)이며, 현재 EvidenceEngine이 실사용 경로
    - 조치: `cmis_core/experimental/search_strategy_v2/`로 이동(명시적으로 core path에서 분리)

- **I**
  - 선택한 방향으로 구현/정리 + 최소 테스트

### P2-4. EvidenceEngine Tier-1(OFFICIAL) 데이터소스 확장: 금융위원회 기업 재무정보 (data.go.kr)

- **D**
  - DART(상장사/대형 중심) 대비 **국내 대부분 법인 커버**를 목표로 하는 Tier-1(OFFICIAL) 소스를 추가
  - 입력 계약(Phase 1):
    - `EvidenceRequest.context.region == "KR"`
    - `corp_reg_no`(법인등록번호) + `year`(재무연도) 필수
  - 출력/매핑(Phase 1 최소):
    - 요약재무제표/손익계산서에서 **`MET-Revenue`(매출액)** 추출을 우선 지원
    - 추가 재무 항목(자산/부채/영업이익/순이익 등)은 우선 `metadata.raw_fields`로 보존(확장 대비)
  - 인증/키:
    - `.env`의 `DATAGOKR_API_KEY`를 사용 (env.example 동기화 유지)
  - Tool registry 연동:
    - `http_fetch`가 미허용이면 source를 registry에 등록하지 않음(P2-1 규칙 준수)
  - lineage/감사:
    - 요청 파라미터(법인등록번호/연도/operation), endpoint, retrieved_at을 `lineage`/`metadata`에 기록

- **v1 스펙(Phase 1, 명시 규칙)**
  - **Source ID(제안)**: `FSC_CorpFinancialInfo`
  - **필수 context 키**
    - `corp_reg_no`: string (하이픈/공백 제거 후 digits-only로 정규화)
    - `year`: int (예: 2024)
  - **지원 오퍼레이션(Phase 1 최소)**
    - 요약 재무정보: `getSummFinaStat_V2` 중심으로 1차 통합
    - (Phase 2+) 재무상태표/손익계산서 상세 오퍼레이션 추가
  - **Metric mapping(Phase 1 최소)**
    - `MET-Revenue` ← `enpSaleAmt` (단위/스케일은 metadata로 보존)
  - **EvidenceRecord 정책**
    - `source_tier="official"`
    - `source_id="FSC_CorpFinancialInfo"`
    - `metadata`: `corp_reg_no`, `year`, `statement`("summary"|"bs"|"is"), `account_name`, `unit`, `raw_fields`
    - `lineage.query`: 호출 파라미터 dict
  - **의존성(후속 제공 예정)**
    - 법인등록번호 자동 해소 API가 아직 없으므로, Phase 1에서는 caller가 `corp_reg_no`를 직접 제공해야 함

- **I**
  - `cmis_core/evidence/fsc_financial_info_source.py` 구현 (connector+source 분리 가능)
    - requests 호출 + timeout + 오류/빈결과 처리(재시도는 최소)
  - `cmis_core/orchestration/executor.py::build_default_source_registry`에 OFFICIAL 소스로 등록(allow_http_fetch 조건 하)
  - 단위 테스트(네트워크 없이):
    - `can_handle()` 필수 필드 검증
    - API 응답 파싱(매출액 추출) - `requests` mocking
  - 통합 테스트(선택, 네트워크 없이):
    - ValueEngine + EvidenceEngine 경로에서 `MET-Revenue`가 `evidence_direct`로 채워지는지 확인(mock)

- **완료 기준**
  - `corp_reg_no`+`year`가 주어졌을 때 EvidenceEngine이 `MET-Revenue`에 대해 Tier-1(OFFICIAL) evidence를 반환
  - `http_fetch` 미허용이면 해당 source가 registry에 등록되지 않음
  - 모든 테스트는 외부 네트워크 없이 재현 가능

- **참고**
  - 스펙: [공공데이터포털 API 명세(getIncoStat_V2)](https://www.data.go.kr/data/15043459/openapi.do#/API%20%EB%AA%A9%EB%A1%9D/getIncoStat_V2)
  - 메타데이터: [DCAT 15043459](https://www.data.go.kr/dcat/metadata/15043459)

## P3: Production Hardening (Phase 1.5 백로그)

P0~P2의 “동작 가능한 최소 구현” 이후, 아래 항목들은 **미구현(실패/스텁/항상 None)** 또는 **프로덕션 품질(신뢰성/관측성/일관성) 미달**로 판정된 영역입니다.
이 섹션은 이를 해결하기 위한 추가 개발 작업리스트입니다.

### P3-1. 레거시/스텁/POC 코드 격리 및 중복 정리

- **문제**
  - `cmis_core/*_poc.py`가 core 패키지에 존재(구 `umis_v9` 스펙 의존/POC 성격)
  - `cmis_core/evidence/sources.py` 내 일부 Source가 “스텁(항상 not implemented)”로 남아 있어 실제 구현(`cmis_core/evidence/kosis_source.py` 등)과 혼동 가능

- **D**
  - core 패키지(`cmis_core/`)에는 “프로덕션 경로”만 남기고, POC/레거시/실험 코드는 `dev/deprecated/` 또는 `cmis_core/experimental/`로 격리
  - `cmis_core/evidence/sources.py`는 다음 원칙으로 정리
    - 테스트 유틸(StubSource 등) + 호환 wrapper만 유지
    - 실제 구현이 있는 소스(KOSIS 등)는 **실제 구현을 re-export**하여 동일 import가 동작하도록 정합성 유지
    - 미구현 소스는 명확히 `experimental` 또는 `not_implemented`로 라벨링

- **I**
  - `cmis_core/*_poc.py` 이동/격리 및 문서 참조 정리(필요 시)
  - `cmis_core/evidence/sources.py`의 스텁/중복 제거 및 re-export 정리
  - 단위 테스트: `cmis_core.evidence.sources`의 호환 import(StubSource/DARTSource 등) 깨지지 않음을 확인

- **완료 기준**
  - core 패키지에서 POC/레거시 파일이 제거되거나 `experimental/deprecated`로 격리됨
  - `cmis_core.evidence.sources`에서 “동일 이름인데 동작이 다른” 중복/스텁이 제거됨(또는 호환 re-export로 일원화)

### P3-2. SearchStrategy v2 실행 스텁 제거(Experimental 유지)

- **문제**
  - `cmis_core/experimental/search_strategy_v2/search_executor.py::_execute_single_query()`가 `return None` 스텁이라 SearchStrategy v2는 사실상 동작하지 않음

- **D**
  - SearchStrategy v2는 **experimental 유지**하되, 최소 실행 가능 경로를 제공
  - `SearchStep.data_source_id` → (GoogleSearch/DuckDuckGo 등) 실제 검색 소스 매핑 규칙 정의
  - 외부 네트워크는 테스트에서 차단하고, `requests`/검색 클라이언트를 mocking하여 파서/흐름만 검증

- **I**
  - `_execute_single_query()`에 최소 실행 구현(소스별 adapter) + RawSearchResult 생성
  - 단위 테스트: `_execute_single_query()`가 stub이 아니고 결과를 생성함(mocking)

- **완료 기준**
  - SearchStrategy v2가 “항상 None” 상태가 아니며, 최소 1개 소스로 RawSearchResult를 생성 가능

### P3-3. Evidence 소스 실행 품질 표준화 (RateLimit/Retry/Timeout/관측성)

- **문제**
  - 소스들이 `requests.get()` 등을 개별 호출하며 rate limit/backoff/retry 정책이 분산됨
  - 운영 시 일시적 장애/429/timeout에 취약, 동일 정책/로그 포맷으로 관측하기 어려움

- **D**
  - 공통 HTTP Client 유틸 도입(Phase 1.5)
    - timeout 기본값, retry/backoff(429/5xx/timeout), error taxonomy 통일
    - `config/sources/rate_limits.yaml` 기반 `RateLimiter`를 공통 경로로 적용
  - tool_calls 이벤트/lineage에 source별 호출 요약을 일관된 스키마로 기록

- **I**
  - 공통 유틸 구현 후, 주요 소스부터 순차 마이그레이션(KOSIS/ECOS/WorldBank/FSC/GoogleSearch 등)
  - 단위 테스트: rate limit/재시도 분기(HTTP status/timeout mocking)

- **완료 기준**
  - 최소 2개 이상의 HTTP 기반 소스가 공통 유틸을 사용
  - 429/timeout/5xx에 대한 retry/backoff가 작동하고, 관측 가능한 lineage가 남음

### P3-4. Prior/Belief 영속화 및 재현성 강화 (PriorManager 고도화)

- **문제**
  - PriorManager가 파일 스캔 기반(value_store/*.json) + 관측치 복원 제한 등으로 규모/동시성/재현성에 취약

- **D**
  - 분포(distribution)와 `distribution_ref`를 “정본 store”로 영속화(SSoT)하고 조회를 인덱스로 수행
  - (Phase 1.5) 최소 요구: (metric_id, context_hash) 기반 최신 prior 조회가 O(1)~O(log n)

- **I**
  - Prior 저장/조회용 sqlite store(또는 기존 store 확장) 설계/구현
  - PriorManager를 store-first로 전환 + 회귀 테스트 추가

- **완료 기준**
  - 파일 전체 스캔 없이 최신 prior를 조회 가능
  - 동일 입력(metric_id+context)에 대해 재현 가능한 distribution_ref를 제공

### P3-5. NativeLLM 프로덕션화 또는 비활성화 정책 확정

- **문제**
  - `NativeLLM`이 placeholder 응답으로 남아 있어, 프로덕션 경로에서 사용되면 품질/신뢰성 문제가 발생

- **D**
  - 선택지:
    - (A) NativeLLM을 실제 실행 환경(Cursor/IDE) 연동으로 구현
    - (B) 프로덕션에서는 native provider를 기본 providers 리스트에서 제외(옵션으로만 사용)

- **I**
  - 선택한 정책에 따라 구현/비활성화 및 테스트(“placeholder가 프로덕션에서 기본 사용되지 않음”을 강제)

- **완료 기준**
  - 프로덕션 기본 경로에서 placeholder 응답이 사용되지 않음(명시적으로만 사용 가능)

---

## 가이드 A/B/C 직접 항목 (추적)

### A. GoalGraph/Success Predicates 정교화 (D-Graph 연동)

- **D**
  - goal_graph ↔ decision_graph 저장/참조(SSoT) 경로 정의

- **Phase 1 방향(결정)**
  - `schemas/decision_graph.yaml`이 placeholder인 상태이므로, Phase 1에서는 **D-Graph를 goal_graph에 포함된 “Goal-centric D-Graph view”로 취급**합니다.
  - **정본(SSoT)**: `ledger_store`의 `project_ledger.goal_graph` 스냅샷(= run 단위 재현 가능한 D-view).
  - **이벤트 소싱**: `run_store.run_decisions`(decision_log.jsonl)는 D-Graph의 event stream으로 유지합니다.

- **v1 스펙(Phase 1, goal_graph 확장 규칙)**
  - **node_types (goal_graph.nodes[].type)**
    - `goal`, `predicate`, `metric` (기존)
    - `task` (추가): TaskQueue에 enqueue 되는 task를 노드로 기록
  - **edge_types (goal_graph.edges[].type)**
    - `requires` (기존: goal → predicate → metric)
    - `plans` (추가: goal → task)
    - `depends_on` (추가: task → task, dependency 표현)
    - `produces` (추가: task → metric, compute/collect 대상 연결)
  - **갱신 시점**
    - initial_plan / replanned 에서 enqueue된 task를 goal_graph에 upsert
    - task status 변화(PENDING/RUNNING/COMPLETED/FAILED)는 task 노드 data에 반영
  - **idempotent**
    - 동일 task_id는 중복 추가하지 않고 data만 갱신
    - 동일 edge(from,to,type)는 중복 추가하지 않음

- **I**
  - Phase 1 최소 구현: decision 노드/엣지 생성 및 export 연결

### B. Eval Harness (회귀 차단)

- **점검**
  - prior 사용률 / policy gate 실패율 / evidence hit rate 지표가 end-to-end로 산출되는지
  - run_store 기록 및 threshold 위반 시 FAIL 차단이 충분한지

### C. Prior 안전 강제

- **점검**
  - distribution_ref
  - prior 채택/기각 정책 근거가 decision log에 강제 기록
  - export 산출물에 prior 기반 값은 추정 표기 강제
