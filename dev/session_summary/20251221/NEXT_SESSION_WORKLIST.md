# 다음 세션 작업 목록 (Next Session Worklist)

**작성일**: 2025-12-21
**다음 세션 시작 시 필독**: 이 문서부터 읽으세요
**상태**: 준비 완료

---

## 📚 시스템 온보딩 (새 LLM Agent를 위한 가이드)

### 1단계: 핵심 아키텍처 이해 (필수)

다음 문서들을 **반드시 이 순서대로** 읽어야 CMIS 시스템을 이해할 수 있습니다:

#### A. 전체 시스템 개요
```
📄 dev/docs/architecture/CMIS_Architecture_Blueprint_v3.6.1_km.md
   - CMIS의 전체 구조 (5개 Plane)
   - SSoT (Substrate), Cognition (Engines), Orchestration
   - Graph-of-Graphs (R/P/V/D)
   - 현재 구현 상태 vs 향후 확장
```

**핵심 개념**:
- **Evidence-first, Prior-last**: 가정보다 증거 우선
- **SSoT (Single Source of Truth)**: `.cmis/` 아래 SQLite + 파일
- **Substrate Plane**: 진실이 저장되는 곳 (stores)
- **Cognition Plane**: 9개 엔진 (Evidence/World/Pattern/Value/Strategy/Learning/Belief/Policy/Workflow)
- **Orchestration Plane**: Reconcile Loop 기반 실행 제어

#### B. 최근 주요 설계 문서

**1. Search Strategy v3** (최신, 가장 중요!)
```
📄 dev/docs/architecture/Search_Strategy_Design_v3.md
   - SERP → Document → Synthesis 파이프라인
   - Section 7: Link Following (depth-based exploration) ← 방금 추가됨
   - Phase-based execution (authoritative/generic_web)
   - Budget/Policy/Trace 기반 재현성 확보
```

**2. LLM Model Management** (작업 중)
```
📄 dev/docs/architecture/CMIS_LLM_Model_Management_Design_v1.1.0.md
   - 현재 커서 위치: line 788/809
   - LLM Provider 추상화, Routing, Cost tracking
```

**3. Orchestration Kernel**
```
📄 dev/docs/architecture/CMIS_Orchestration_Kernel_Design.md
   - Reconcile Loop 패턴 (Kubernetes 스타일)
   - Ledgers (Project + Progress)
   - Verifier, Replanner, Governor
```

**4. Brownfield 온보딩**
```
📄 dev/docs/architecture/Brownfield_Intake_and_Curation_Design_v3.6.0.md
   - 내부 데이터 입력 (CSV/XLSX)
   - Preview → Validate → Commit → Verify
   - CUR/CUB/DOP/Pack 개념
```

#### C. NotebookLM 학습 문서 (빠른 이해)

```
📁 dev/docs/notebooklm_export/
   - 00_CMIS_System_Overview.md
   - 01_Core_Types_and_Schemas.md
   - 02_Core_Engines_Implementation.md
   - 03_Evidence_System_Detail.md
   - 04_Orchestration_Implementation.md
   - 05_Search_Strategy_v3.md
   - 06_CLI_Commands_Reference.md
   - 07_Configuration_Reference.md
   - 08_Stores_and_Persistence.md
   - 09_Integration_Guide.md
```

자동 생성된 문서로, 코드 스니펫과 실제 구현이 포함되어 있습니다.

### 2단계: 최근 작업 이력 파악

**2025-12-21 작업 요약**:

1. ✅ **NotebookLM 학습 시스템 구축**
   - Python AST 파싱 기반 자동 문서 생성
   - 10개 마크다운 문서 (3,720줄)
   - 스크립트: `dev/tools/generate_notebooklm_docs.py`

2. ✅ **Search Strategy v3 Link Following 설계 추가**
   - HTML hyperlink를 따라가는 depth-based exploration
   - Section 7 전체 추가 (483줄)
   - LinkExtractor, LinkSelectionPolicy, BFS 알고리즘
   - TODO: SSV3-13~16

3. ✅ **Search Strategy v2 → v3 완전 전환**
   - v2 관련 파일 모두 deprecated로 이동
   - `search_strategy_spec.yaml` (v2) → deprecated
   - `experimental/search_strategy_v2/` → deprecated
   - `search_strategy_registry_v3.yaml` 보완 (fetch_depth 설명 추가)
   - 마이그레이션 문서: `SEARCH_STRATEGY_V2_TO_V3_MIGRATION.md`

**최근 커밋**:
```
ee5b8ba refactor: Search Strategy v2 → v3 완전 전환 및 정리
921581f docs: Search Strategy v3에 Link Following 설계 추가
f94e728 feat: NotebookLM 학습용 문서 자동 생성 시스템 구축
```

### 3단계: 프로젝트 구조 이해

```
cmis/
├── cmis.yaml                   # 중앙 레지스트리 (계약)
├── schemas/                    # 타입 시스템 (R/P/V/D graphs, ledgers)
├── libraries/                  # 도메인 지식 (patterns, metrics)
├── config/                     # 런타임 설정
│   ├── policies.yaml
│   ├── workflows.yaml
│   ├── search_strategy_registry_v3.yaml  ← v3 활성화
│   ├── archetypes/             # Context archetypes
│   └── sources/                # Evidence sources
├── cmis_core/                  # 9개 엔진 구현
│   ├── search_v3/              # Search v3 구현 (14개 파일)
│   ├── evidence/               # Evidence sources
│   ├── orchestration/          # Orchestration kernel
│   ├── brownfield/             # Brownfield 온보딩
│   ├── stores/                 # Substrate (SQLite)
│   └── llm/                    # LLM 추상화
├── cmis_cli/                   # CLI 인터페이스
└── dev/                        # 개발 전용
    ├── docs/                   # 문서
    ├── tests/                  # 테스트
    ├── deprecated/             # 구버전 (v2 등)
    └── tools/                  # 유틸리티
```

**금지 규칙**:
- 루트에 `test_*.py`, `example_*.py` 생성 금지
- Import는 `import cmis_core` (not umis_v9_core)
- YAML 검증 필수 (들여쓰기, 탭 금지, 특수문자)
- Trailing spaces 금지

---

## 🎯 우선순위별 작업 목록

### P0: 즉시 착수 (이번 주)

#### 1. Search Strategy v3 기반 인프라 구현

**배경**: 설계는 완료되었으나 구현이 필요. 재현성/안전성 확보가 최우선.

```
[ ] SSV3-01: StrategyRegistry v3 구현
    - 목표: YAML registry → compiled → digest pinning
    - 파일: cmis_core/search_v3/registry.py (이미 존재, 확장 필요)
    - 설계: Search_Strategy_Design_v3.md Section 1.3
    - 수용기준: 동일 입력 → 동일 digest, unknown provider 로드 실패
    - 테스트: digest 안정성, schema validation

[ ] SSV3-02: Trace/Event writer (append-only)
    - 목표: events(JSONL) 기록, 원문은 ART에만
    - 파일: cmis_core/search_v3/trace.py (이미 존재, 확장 필요)
    - 설계: Search_Strategy_Design_v3.md Section 2
    - 수용기준: query_text/snippet/html이 ledger에 직접 안 들어감
    - 테스트: ref-only 계약 검증

[ ] SSV3-03: QueryArtifact 생성 규칙
    - 목표: 모든 query에 artifact_id 생성
    - 파일: cmis_core/search_v3/query.py (신규 또는 확장)
    - 설계: Search_Strategy_Design_v3.md Section 5.6
    - 수용기준: deterministic/LLM 모두 artifact 생성
    - 테스트: artifact 누락 없음

[ ] SSV3-04: GenericWebSearch Provider
    - 목표: google_cse adapter + 캐시/레이트리밋
    - 파일: cmis_core/search_v3/generic_web_search.py (이미 존재)
    - 설계: Search_Strategy_Design_v3.md Section 3
    - 수용기준: 표준 에러 taxonomy, SerpSnapshotRef 생성
    - 테스트: HTTP 모킹 (429/timeout/authfail)

[ ] SSV3-05: DocumentFetcher 안전장치
    - 목표: SSRF/MIME/max_bytes/redirect 강제
    - 파일: cmis_core/search_v3/document_fetcher.py (이미 존재)
    - 설계: Search_Strategy_Design_v3.md Section 4
    - 수용기준: SSRF/내부IP 차단, content-addressed DOC-*
    - 테스트: SSRF/redirect loop/max_bytes (필수)
```

#### 2. Brownfield 작업 완료

**배경**: 현재 커밋되지 않은 변경사항이 있음.

```
[ ] Brownfield outbox.py 문서화 및 커밋
    - 파일: cmis_core/brownfield/outbox.py (신규)
    - 관련: commit.py, db.py, import_run_store.py 변경사항
    - 목적: Commit → Outbox → External system 패턴
    - 우선: git status 확인 → 변경사항 검토 → 커밋

[ ] Brownfield CLI 명령어 확장 확인
    - 파일: cmis_cli/commands/brownfield.py
    - 변경사항 검토 및 문서화
```

### P1: 다음 스프린트 (2주)

#### 3. Search Strategy v3 추출/합성/게이트

```
[ ] SSV3-06: CandidateExtractor v1
    - 파일: cmis_core/search_v3/candidate_extractor.py (이미 존재)
    - 설계: Search_Strategy_Design_v3.md Section 1.3
    - 구현: 규칙 기반 수치/단위/기간 추출
    - 수용기준: independence_key 생성

[ ] SSV3-07: Synthesizer v1
    - 파일: cmis_core/search_v3/synthesizer.py (이미 존재)
    - 구현: consensus (median) + outlier 완화
    - 수용기준: 결정적 출력 (동일 입력 → 동일 결과)

[ ] SSV3-08: GatePolicyEnforcer v1
    - 파일: cmis_core/search_v3/gate.py (이미 존재)
    - 구현: reporting_strict vs decision_balanced 차등
    - 수용기준: min_independent_sources 강제
```

#### 4. Search Strategy v3 통합

```
[ ] SSV3-09: SearchRunner/SearchKernel
    - 파일: cmis_core/search_v3/runner.py (이미 존재)
    - 구현: phase loop + stop condition + replan
    - 수용기준: budget/egress 위반 없음

[ ] SSV3-10: EvidenceEngine 연결
    - 파일: cmis_core/evidence_engine.py 확장
    - 통합: SearchKernel 호출 → EvidenceRecord 반환
    - 수용기준: 기존 소스와 충돌 없음

[ ] SSV3-11: Run export/검증 연결
    - 검증: trace envelope, ART refs, plan_digest_chain
    - Verifier: 재현 불가능 상태 탐지

[ ] SSV3-12: QueryLearner v1 (선택)
    - 온라인 변경 금지, 오프라인 제안만
```

#### 5. LLM Model Management 구현

**배경**: v1.1.0 설계 문서 완성 (809줄), Phase 1부터 구현 시작 준비 완료.

**설계 요약**:
- LLM-native 자율 컨트롤러 + 최소 커널 패턴
- PolicyEngine 통합 (effective_policy 생성)
- 결정적 선택 + bounded escalation
- 3등급 벤치마크 (Unit/Scenario/Human)

**구현 로드맵** (총 22.5일):

```
[✅] v1.1.0 설계 문서 완성 (2025-12-21 완료)
    - 파일: dev/docs/architecture/CMIS_LLM_Model_Management_Design_v1.1.0.md
    - 상태: 커밋 완료 (83604f6)
    - 보완사항 반영: Phase별 공수, 단계적 구현 경로, 최소 TaskSpec, 캐싱 전략

[ ] Phase 1: 정책 단일화 + 결정적 선택 커널 (7일)
    ├─ [ ] LLM-01: ModelRegistry 구현
    │   - 파일: config/llm/model_registry.yaml (YAML)
    │   - 파일: cmis_core/llm/model_registry.py (로더)
    │   - 목표: 모델 메타데이터 로드 + registry_digest 산출
    │   - 수용기준: capabilities/cost/limits 검증, digest 안정성
    │   - 공수: 1일
    │
    ├─ [ ] LLM-02: TaskSpecRegistry 구현
    │   - 파일: config/llm/task_specs_minimal.yaml (Phase 1용)
    │   - 파일: cmis_core/llm/task_spec_registry.py
    │   - 목표: 핵심 3개 Task 스펙 정의 (나머지는 _default)
    │   - 수용기준: required_capabilities, quality_gates 검증
    │   - 공수: 1일
    │
    ├─ [ ] LLM-03: PolicyEngine 확장
    │   - 파일: cmis_core/policy_engine.py
    │   - 파일: config/policy_extensions/llm_routing.yaml (신규)
    │   - 목표: effective_policy.llm 생성 + digest 캐싱
    │   - 수용기준: policy_ref → effective_policy 결정적 변환
    │   - 공수: 1.5일
    │
    ├─ [ ] LLM-04: ModelSelector 구현
    │   - 파일: cmis_core/llm/model_selector.py (신규)
    │   - 목표: SelectionRequest → SelectionDecision (결정적)
    │   - 알고리즘: 정책 허용 → capability 체크 → 예산/지연 → 정렬
    │   - 수용기준: 동일 입력 → 동일 선택, rationale_codes 기록
    │   - 공수: 2일
    │
    ├─ [ ] LLM-05: run_store 통합
    │   - 파일: cmis_core/stores/run_store.py 확장
    │   - 목표: selection_decision trace 저장
    │   - 저장 항목: policy_ref, effective_policy_digest, registry_digest,
    │                model_id, rationale_codes, estimated_cost
    │   - 공수: 0.5일
    │
    └─ [ ] LLM-06: Phase 1 단위 테스트
        - 파일: dev/tests/unit/test_llm_model_selector.py
        - 테스트: digest 안정성, 결정적 선택, fallback chain
        - 공수: 1일

    **Phase 1 완료 후 → v1.1.0-alpha 태깅**

[ ] Phase 2: 품질 게이트 + bounded escalation (6일)
    ├─ [ ] LLM-07: QualityGate 실행기
    │   - 파일: cmis_core/llm/quality_gate.py (신규)
    │   - 목표: TaskSpec quality_gates 검증
    │   - Gates: json_parseable, schema_valid, has_claims 등
    │   - 공수: 1.5일
    │
    ├─ [ ] LLM-08: Escalation ladder 지원
    │   - 파일: cmis_core/llm/model_selector.py 확장
    │   - 목표: gate 실패 시 자동 에스컬레이션
    │   - 수용기준: failure_codes 기반 next model 선택
    │   - 공수: 1.5일
    │
    ├─ [ ] LLM-09: Prompt profile 레지스트리
    │   - 파일: config/llm/prompt_profiles.yaml (신규)
    │   - 목표: 프롬프트 버전 관리 + pinning
    │   - 공수: 1일
    │
    ├─ [ ] LLM-10: 전체 TaskSpec 확장
    │   - 파일: config/llm/task_specs.yaml (전체 버전)
    │   - 목표: 10개 Task 전체 스펙 정의
    │   - 공수: 1일
    │
    ├─ [ ] LLM-11: execution_profile 강제
    │   - 목표: prod에서 mock 금지, dev/test만 허용
    │   - 공수: 0.5일
    │
    └─ [ ] LLM-12: Phase 2 통합 테스트
        - 에스컬레이션 시나리오 테스트
        - 공수: 0.5일

    **Phase 2 완료 후 → v1.1.0-beta 태깅**

[ ] Phase 3: 벤치마크 프레임워크 (7.5일)
    ├─ [ ] LLM-13: BenchmarkRunner 구현
    │   - 파일: cmis_core/llm/benchmark.py
    │   - 공수: 2일
    │
    ├─ [ ] LLM-14: Unit bench 실행/저장
    │   - 저장: .cmis/benchmarks/runs/
    │   - 공수: 1일
    │
    ├─ [ ] LLM-15: Scenario bench + judge pinning
    │   - judge trace 저장
    │   - 공수: 1.5일
    │
    ├─ [ ] LLM-16: BenchmarkStore 시계열 + 회귀 감지
    │   - 공수: 1일
    │
    ├─ [ ] LLM-17: CLI 명령 추가
    │   - cmis llm benchmark run/report
    │   - 공수: 1일
    │
    └─ [ ] LLM-18: 초기 벤치마크 스위트
        - evidence/pattern/value 스위트
        - 공수: 1일

    **Phase 3 완료 후 → v1.1.0-stable 태깅**

[ ] Phase 4: 자동화/관측 (선택, 2일)
    - CI/CD 통합
    - 회귀 알림
    - (대시보드는 선택사항)
```

**설계 문서 참조**:
- 전체: `dev/docs/architecture/CMIS_LLM_Model_Management_Design_v1.1.0.md`
- Section 12: 구현 로드맵 (Phase별 상세)
- Section 13: 단계적 구현 경로 (alpha/beta/stable)

### P2: Link Following 구현 (2~3주)

```
[ ] SSV3-13: LinkExtractor v1
    - 파일: cmis_core/search_v3/link_extractor.py (신규)
    - 설계: Search_Strategy_Design_v3.md Section 7.4.1
    - 구현: 규칙 기반 relevance scoring
    - 수용기준: LinkCandidate 생성, link_type 분류

[ ] SSV3-14: DocumentFetcher depth-based exploration
    - 파일: cmis_core/search_v3/document_fetcher.py 확장
    - 구현: BFS 알고리즘 + visited tracking
    - 수용기준: depth_from_serp, parent_doc_id 기록

[ ] SSV3-15: LinkSelectionPolicy
    - 파일: cmis_core/search_v3/link_selector.py (신규)
    - 구현: max_links_per_doc, min_relevance_score
    - 수용기준: budget 내 선택, same_domain_only 강제

[ ] SSV3-16: Link events/trace
    - 이벤트: LinkExtracted, LinkFollowed, DepthExplorationCompleted
    - Config: search_strategy_registry_v3.yaml link_selection 활성화
```

### P3: 중장기 (1~2개월)

```
[ ] Orchestration Kernel 고도화
    - D-Graph 계획 그래프 고정
    - Diff 기반 자동 재계획

[ ] 프로덕션 운영 준비
    - PostgreSQL + S3/GCS 전환
    - Evidence cache 영속화
    - HTTP API 서버

[ ] Brownfield 운영 UX
    - Pack CLI 고도화
    - DOP 승인 워크플로
    - PRJ_VIEW 자동 재생성
```

---

## 🔧 개발 환경 체크리스트

### 시작 전 확인사항

```bash
# 1. 환경 점검
python3 -m cmis_cli cursor doctor

# 2. 의존성 확인
pip install -r requirements.txt

# 3. 현재 브랜치/커밋 확인
git status
git log --oneline -5

# 4. 미완성 작업 확인
git diff
git diff --cached

# 5. 테스트 실행
pytest dev/tests/unit/test_search_strategy_v3_*.py -v
```

### 주요 경로

```bash
# 설정 파일
config/search_strategy_registry_v3.yaml
config/policies.yaml
cmis.yaml

# 구현 파일
cmis_core/search_v3/
cmis_core/evidence/
cmis_core/orchestration/

# 테스트
dev/tests/unit/
dev/tests/integration/

# 문서
dev/docs/architecture/
dev/docs/notebooklm_export/
```

---

## 📝 작업 진행 시 주의사항

### 1. 코딩 규칙

- **Type hints + Docstrings 필수**
- **YAML 검증 필수** (들여쓰기 spaces only, 특수문자 주의)
- **Trailing spaces 제거**
- **Import**: `import cmis_core` (not umis_v9_core)

### 2. 파일 생성 규칙

- **루트에 test/example 파일 생성 금지**
- **700+ 라인 파일**: write → search_replace로 분할
- **문서**: 비개발자도 이해 가능하도록 작성

### 3. 커밋 규칙

- **커밋 메시지**: 한글, feat/fix/docs/refactor 등
- **원자적 커밋**: 하나의 논리적 변경만
- **Force push 금지** (main/master)
- **Hook 스킵 금지** (--no-verify)

### 4. 설계 우선

- **구현 전 설계 문서 확인**
- **Section 참조 명시**
- **Trade-off 문서화**

---

## 🚨 알려진 이슈/제약사항

### 1. Search Strategy v3

- **현재 상태**: 설계 완료, 구현 대기
- **Link Following**: 설계만 완료 (Section 7)
- **fetch_depth**: 모두 0으로 설정됨 (비활성화)

### 2. Brownfield

- **커밋되지 않은 변경사항 있음**:
  - outbox.py (신규)
  - commit.py, db.py, import_run_store.py (수정)
- **우선 검토 필요**

### 3. LLM Model Management

- **설계 문서 완성** (v1.1.0, 809줄, 커밋 완료)
- **Phase 1 구현 준비 완료** (7일 예상)
- **다음 단계**: ModelRegistry, TaskSpecRegistry 구현

---

## 📚 참고 자료

### 핵심 문서 (읽기 순서)

1. `CMIS_Architecture_Blueprint_v3.6.1_km.md` - 전체 시스템
2. `Search_Strategy_Design_v3.md` - Search v3 (최신)
3. `CMIS_Orchestration_Kernel_Design.md` - Orchestration
4. `Brownfield_Intake_and_Curation_Design_v3.6.0.md` - Brownfield
5. `CMIS_LLM_Model_Management_Design_v1.1.0.md` - LLM (v1.1.0 완성, 2025-12-21)

### 마이그레이션 문서

- `SEARCH_STRATEGY_V2_TO_V3_MIGRATION.md` - v2→v3 전환 내역

### 자동 생성 도구

- `dev/tools/generate_notebooklm_docs.py` - NotebookLM 문서 생성

---

## ✅ 다음 세션 시작 시 체크리스트

```
[ ] 이 문서(NEXT_SESSION_WORKLIST.md) 읽기
[ ] CMIS_Architecture_Blueprint_v3.6.1_km.md 리뷰
[ ] Search_Strategy_Design_v3.md Section 1-7 리뷰
[ ] git status로 미완성 작업 확인
[ ] 우선순위 P0 작업부터 시작
[ ] 의문사항은 설계 문서부터 확인
```

---

**작성자**: 2025-12-21 세션
**다음 업데이트**: 다음 세션 종료 시
**문서 위치**: `dev/session_summary/20251221/NEXT_SESSION_WORKLIST.md`

