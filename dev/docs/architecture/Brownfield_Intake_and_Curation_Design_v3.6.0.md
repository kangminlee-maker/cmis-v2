## Brownfield Intake & Curation Design (v3.6.0)

**작성일**: 2025-12-13
**최종 업데이트**: 2025-12-13
**아키텍처 기준 버전**: CMIS v3.6.0
**상태**: 설계 단계 (Implementation Pending)
**적용 범위**: Brownfield(내부/사용자 제공 데이터) intake/ingest/curation/pack/verify/CLI
**SSoT 우선순위**: `cmis.yaml` > `cmis_core/*`(구현) > 본 문서(설계)
**관련 문서**:
- `CMIS_Architecture_Blueprint_v3.6.0_km.md`
- `cmis_project_context_layer_design.md`
- `CMIS_Orchestration_Kernel_Design.md`
- `LearningEngine_Design_Enhanced.md`

> 목적: CMIS의 Brownfield(우리 조직 관점 분석)에서 **내부/사용자 제공 데이터**를 빠르고 안전하게 수집·정규화·재사용 가능하게 만들고, **SSoT/재현성/감사성**을 유지한 채로 엔진(증거/가치/전략)이 소비할 수 있도록 한다.

---

## 0. 배경

CMIS에서 **Brownfield**란 시장(도메인) 분석을 “우리(클라이언트) 회사/조직”의 기준 상태(baseline), 자산(assets), 제약(constraints), 선호(preferences) 관점에서 수행하는 모드입니다.

Brownfield의 조직/주체 컨텍스트 레코드는 `FocalActorContext(PRJ-*)`를 사용하며, 외부 키는 `focal_actor_context_id (PRJ-*)`로 통일합니다.

Brownfield의 핵심은 다음입니다.

- 사용자의 첫 질문은 목표/산출물이 불명확할 수 있으므로, **목표 구체화 이후에 필요한 데이터를 동적으로 요청**해야 함
- 사용자 데이터는 `txt/docx/xlsx/csv`가 대부분이며, 특히 `xlsx`는 값뿐 아니라 수식/연산 과정이 존재하므로 **decode/migrate**가 필요
- 내부/사용자 제공 정보는 외부 수집 evidence와 성격이 다르므로 **저장소/객체 모델을 분리**해야 함
- 동일 조직에 대해 반복되는 분석을 위해, 특정 Brownfield 데이터 세트를 **묶어서 저장(Brownfield Pack)** 하고 재사용 가능해야 함

---

## 1. 설계 목표 (To-Be)

### 1.1 UX 목표
- 시작이 빠른 Quick-start(목표 구체화 → 필요한 데이터 동적 요청)
- 사용자가 가진 자료를 그대로 업로드(xlsx/csv/docx/txt)
- import 결과를 미리보기/검증/수정(매핑/데이터 override 패치) 가능
- 동일 조직에 대해 다시 분석할 때, 기존 Brownfield 데이터 세트를 빠르게 재사용(Brownfield Pack)

### 1.2 시스템 목표
- **SSoT/재현성**: 원본 파일과 정규화 결과, 컨텍스트 버전의 lineage 연결
- **Determinism(결정성)**: 동일 입력(파일+매핑+정책+추출기 버전) → 동일 정규화 결과
- **안전성**: 민감 데이터가 run_store/ledger/log에 원문으로 흘러가지 않도록
- **분리 저장**: Evidence(외부 수집) vs Curated(User/Internal)
- **버전/업데이트**: 주기적 업데이트를 전제로 vN 누적과 diff 제공

---

## 2. 핵심 설계 원칙 (Contracts / Done Criteria)

> 구현이 “되긴 되는데 운영에서 깨지는” 것을 방지하기 위해, Brownfield는 아래 계약을 만족해야 한다.

### 2.1 Determinism Contract (결정성)
- Ingest 결정성(IMP/CUB/CUR):
  - 동일한 입력 조합:
    - `artifact_id(s)`
    - `mapping_id@version` (MappingPatch가 적용되면 version이 증가)
    - `extractor_version`
    - `ingest_policy_digest`
    - `normalization_defaults` (+ scope/as_of)
    - `patches_digest` (DataOverridePatch가 적용되면 포함)
  → 동일한 `CuratedDatum(CUR)` / `CuratedBundle(CUB)` digest가 생성되어야 함
- Context build 결정성(PRJ):
  - 동일한 입력 조합:
    - (기본/권장) `primary_source_bundle`: `{bundle_id: CUB-..., bundle_digest: sha256:..., role?: ...}`
    - (고급/선택) `source_bundles`: `[{bundle_id: CUB-..., bundle_digest: sha256:..., role: ..., precedence?: ...}, ...]`
      - 멀티 모드에서는 `role`이 사실상 필수이며, `precedence`(또는 merge_rule)를 통해 합성 순서를 결정적으로 고정한다.
      - 기본 규칙: `primary_source_bundle`와 `source_bundles`는 동시에 존재할 수 없다.
    - `context_builder_version`
    - `context_builder_config_digest` (optional)
    - `context_policy_digest` (optional; ingest_policy_digest와 구분)
  → 동일한 `FocalActorContext(PRJ)`(요약/포인터 뷰)가 생성되어야 함
- Import는 기본적으로 **idempotent** 해야 함(같은 ingest 입력이면 동일 결과 재사용)
- 원칙: `PRJ`는 ingest provenance의 정본이 아니다
  - ingest provenance(ART/MAP/extractor/ingest_policy/patch)는 `IMP`/`CUB`(+ 필요 시 `CUR`)에만 존재해야 함
- lineage 강제 기록(SoT):
  - `IMP`/`CUB`/`CUR`: `from_artifact_ids`, `mapping_id@version`, `extractor_version`, `ingest_policy_digest`, `schema_version`, `normalization_defaults`, `patches`
  - `PRJ`: `primary_source_bundle` 또는 `source_bundles(+digests, role, precedence)`, `context_builder_version`, `context_builder_config_digest(optional)`, `context_policy_digest(optional)`

### 2.2 Data Leakage Contract (기밀/누출 방지)
- `run_store`, `events`, `decision_log`, `progress_ledger`에 **원문 데이터/대량 수치**가 포함되지 않는다
- 로그에는 ref와 메타만 기록:
  - `artifact_id`, `hash`, `mime`, `row_count`, `mapping_id`, `digest` 등
- 사람이 보는 결과물(results.md 등)은 기본적으로 **요약 + ref 링크** 중심이며,
  민감 수치 대량 노출은 정책/옵션으로 제한

### 2.3 Schema & Mapping Contract (스키마/매핑)
- 매핑(MAP)은 “컬럼 매칭”을 넘어서 최소 다음을 포함해야 함:
  - 단위/통화/기간(월/분기/연, 누계/당기) 정규화 규칙
  - as_of/period 추출 규칙
  - 타입(수치/범주/ID), 집계 기준(합/평균/누계) 정의
- 매핑은 독립 객체로 버전 관리되어야 함 (`mapping_id`, `mapping_version`)
- 템플릿 기반 입력은 “내장된 매핑 스펙”으로 취급(동일 파이프라인을 타게)
- Patch는 2종류로 분리한다:
  1) **MappingPatch**
     - sheet/column/range/unit/period 규칙 변경
     - `MAP version` up으로 표현
     - 재추출 필요(새 `IMP` → 새 `CUB` 생성)
  2) **DataOverridePatch(`DOP-*`)**
     - 추출 결과(`CUR`/`CUB`)에 대한 값 보정
     - 근거/승인/lineage 기록 필수
     - 보정 적용 결과는 새 `CUB`(또는 `CUR vN`)로 커밋되어 digest/lineage에 반영

### 2.4 Quality Gate Contract (검증/커밋 정책)
- commit 전에 반드시 Validate 단계를 거치며, 결과는 구조화된 report로 저장
- Policy 모드에 따라 동작이 달라야 함:
  - `reporting_strict`: 치명 오류(필수 누락/단위 불일치 등) 시 commit 차단
  - `decision_balanced`: 일부 오류 차단 + 일부 경고
  - `exploration_friendly`: 경고 중심(단, 위험/치명 오류는 정책적으로 조정)
- `reporting_strict`에서 DataOverridePatch는 승인/근거 요건을 강화한다:
  - 권장: `approval_required` run_mode와 결합하여 “승인된 override만 커밋”되도록 강제
  - Validation report에 override 근거(ref) 및 승인자/승인 시각을 남긴다

### 2.5 Versioning & Diff Contract (업데이트/이력)
- Brownfield ingest 업데이트는 항상 vN 누적이 기본(append-only)
- 과거 RUN은 당시 사용한 **repro anchor(기본: `PRJ vN`)** 을 pin하여 재현 가능해야 함 (RUN pinning은 2.6 참고)
- 업데이트 시 “무엇이 바뀌었는지” 요약 diff를 제공해야 함(최소한 핵심 metric/테이블 수준)

### 2.6 Brownfield Repro Anchor Contract (RUN Pinning)
- 분석 RUN은 Brownfield 재현성 기준으로 **단 하나의 앵커만 pin**한다.
- 기본값(권장): `focal_actor_context_id = PRJ-...-vN`
  - PRJ lineage는 최소화하며, “입력 스냅샷(CUB) + 컨텍스트 빌더 버전”만으로 재현 가능해야 한다.
  - PRJ에 **반드시** 남겨야 하는 것(권장 필수):
    - (기본/권장, 단일 모드) `primary_source_bundle`: `{bundle_id, bundle_digest, role?}`
      - 권장: PRJ는 기본적으로 **단일 CUB**만 참조(가장 단순/강건)
      - 단일 모드: `primary_source_bundle`만 허용(= `source_bundles` 금지)
    - (고급/선택, 멀티 모드) `source_bundles`: `[{bundle_id, bundle_digest, role, precedence?}, ...]`
      - 멀티 모드: `role` 필수(권장 role 예: baseline|constraints|assets|preferences|override|other)
      - 멀티 모드: 합성 순서를 결정적으로 고정하기 위해 `precedence`(또는 merge_rule)를 권장
      - (권장 정책) baseline role은 1개만 허용
    - `context_builder_version` (필수에 가깝다)
    - `context_builder_config_digest` (optional; 빌더 설정이 있으면 고정)
    - `context_policy_digest` (optional; ingest 정책이 아니라 “컨텍스트 구성 정책”일 때만)
  - PRJ에 “필수로” 남기지 말아야 하는 것(권장):
    - `from_artifact_ids`, `mapping_id@version`, `extractor_version` (SoT는 `IMP/CUB`에 존재)
- `brownfield_pack_id(BPK-...-vN)`는 재사용/선택 UX를 위한 참조로 기록할 수 있으나, RUN의 재현 단위는 PRJ 1개를 기준으로 한다.
- (선택) PRJ 대신 `CUB`를 앵커로 pin하는 모드도 허용할 수 있으나,
  이 경우 PRJ 생성 규칙/빌더(digest)까지 추가로 고정해야 하므로 기본값은 PRJ를 권장한다.
- PRJ cache/view(derived data)는 정본 오용을 막기 위해 **별도 store**로 분리하는 것을 기본 권장한다:
  - 권장: `ContextViewStore(PRJ_VIEW)` 또는 `prj_views` 테이블(4.1 참고)
  - 단일 모드: view는 `derived_from_bundle_digest == (primary_source_bundle.bundle_digest)`일 때만 사용
  - 멀티 모드: view는 `derived_from_sources_digest == sha256(canonical_json(source_bundles))`일 때만 사용
  - 불일치하면 view를 무시/폐기하고 재생성한다.
- 차선안: PRJ 내부에 cache를 둔다면:
  - PRJ identity/digest 계산에서 cache는 제외(명시)
  - 사용 전 `derived_from_bundle_digest` 검증을 필수화한다.
- PRJ metadata 예시(중첩 코드펜스 없이 표현):
    focal_actor_context:
      focal_actor_context_id: PRJ-EXAMPLE-v3
      metadata:
        lineage:
          primary_source_bundle:
            bundle_id: CUB-EXAMPLE-0001
            bundle_digest: sha256:...
            role: baseline_financials
          # 멀티 모드(선택; primary_source_bundle과 동시 사용 금지):
          # source_bundles:
          #   - bundle_id: CUB-EXAMPLE-0001
          #     bundle_digest: sha256:...
          #     role: baseline
          #     precedence: 100
          #   - bundle_id: CUB-EXAMPLE-0002
          #     bundle_digest: sha256:...
          #     role: constraints
          #     precedence: 50
        context_builder:
          version: "focal_actor_context_builder@0.2.0"
          builder_config_digest: sha256:...
        context_policy_digest: sha256:...

### 2.8 Context Verify Contract (계약 강제; PRJ/CUB/BPK)
- Verify는 유틸이 아니라 **Contract enforcement**이며, 운영 안전성을 위한 Done Criteria로 취급한다.
- `cmis context verify PRJ-...-vN`(권장)에서 최소 다음을 강제한다:
  - PRJ pin:
    - alias(예: latest) 기반 pin 금지, `PRJ-...-vN`만 허용
  - PRJ → CUB digest 일치:
    - 단일 모드: `primary_source_bundle.bundle_digest`가 실제 `CUB.bundle_digest`와 일치
    - 멀티 모드: `source_bundles[*].bundle_digest` 전부가 실제 `CUB.bundle_digest`와 일치
  - builder_version 존재:
    - `context_builder_version`(또는 동등 필드) 누락 금지
  - patch/정책 lineage 누락 금지(간접 검증):
    - PRJ가 참조하는 CUB가 `ingest_policy_digest`, `mapping_id@version`, `extractor_version`, `patch_chain_digests(또는 patches_digest)`를 포함하는지 확인
  - (view/cache가 존재하는 경우) derived_from_bundle_digest 일치 시에만 사용:
    - 단일 모드: `prj_view.derived_from_bundle_digest == (primary_source_bundle.bundle_digest)`가 아니면 view 폐기/재생성
    - 멀티 모드: `prj_view.derived_from_sources_digest == sha256(canonical_json(source_bundles))`가 아니면 view 폐기/재생성
- `cmis brownfield verify BPK-...-vN`(선택)도 제공 가능:
  - pack이 참조하는 PRJ/CUB들이 모두 verify를 통과하는지 일괄 점검
- 이 검증은:
  - run 시작 전 preflight
  - pack 업데이트 전 gate
  - (선택) CI/프리커밋 훅
  로도 연결 가능해야 한다.

### 2.7 External Access Policy Contract (세분화)
- allow_external_web 단일 스위치 대신, 최소 다음으로 분리한다:
  - `allow_web_search`: bool
  - `allow_official_http_fetch`: bool (화이트리스트 기반 직접 fetch)
  - `allow_commercial_api`: bool
  - (선택) `allow_llm_api`: bool
- 최종 허용은 `policy ∩ pack/spec ∩ runtime capability`의 교집합으로 결정한다.
  - `allow_official_http_fetch`의 enforcement는 `source_id allowlist` 또는 `SourceTier.OFFICIAL` 기준으로 강제한다.
  - 결정(deny reason 포함)은 run_store에 meta로 기록하는 것을 권장한다.

---

## 3. 1급 객체 모델 및 ID 규칙

### 3.1 객체/ID 목록
- `ART-*` : 원본 업로드 파일(정본)
- `MAP-*` : 매핑 스펙(버전 관리)
- `IMP-*` : ImportRun(ingest 실행 기록/감사/결정성)
- `CUR-*` : CuratedDatum(정규화된 원자 데이터)
- `CUB-*` : CuratedBundle(한 번의 import 결과 묶음/스냅샷)
- `PRJ-*` : FocalActorContext(조직/주체 컨텍스트의 요약/포인터 뷰)
- `BPK-*` : BrownfieldPack(재사용 가능한 내부 데이터 패키지)
- `DOP-*` : DataOverridePatch(추출 결과 보정; 근거/승인/lineage 필수)
- `OUT-*` : Outcome(실제 결과/학습 입력)
- `RUN-*` : 분석 실행(run), project/case ledger 및 progress ledger가 연결됨

### 3.2 경계/SSoT 규칙(강제)
- 원문은 항상 `ART-*`만 정본
- 정규화 데이터는 `CUR-*` / `CUB-*`가 정본
- `PRJ-*`는 실행/추론을 위한 요약/포인터이며, 대량 데이터는 포함하지 않음(ref로 연결)
- `BPK-*`는 “ref-only 묶음”이며 복제 저장을 하지 않음
- RUN/ledger/log는 원문을 담지 않고 ref만 담음

---

## 4. 저장소(Stores) / 정본(SSoT) 구성

### 4.1 파일/DB 위치(권장)
- 아래는 “논리적 스토어” 기준이며, 물리 DB 배치는 `storage_profile`에 의해 달라질 수 있다(4.2 참고).
- **ArtifactStore**: `.cmis/db/artifacts.db` + `.cmis/artifacts/` (원문/대용량 정본)
- **MappingStore(MAP)**: `.cmis/db/mappings.db` (또는 brownfield.db 내 테이블)
- **ImportRunStore(IMP)**: `.cmis/db/import_runs.db` (또는 brownfield.db 내 테이블)
- **CuratedStore(CUR)**: `.cmis/db/curated.db` (또는 brownfield.db 내 테이블)
- **CuratedBundleStore(CUB)**: `.cmis/db/curated_bundles.db` (또는 brownfield.db 내 테이블)
- **FocalActorContextStore(PRJ)**: `.cmis/db/contexts.db` (또는 brownfield.db 내 테이블)
- **ContextViewStore(PRJ_VIEW)**: `.cmis/db/context_views.db` (또는 brownfield.db 내 테이블)
- **BrownfieldPackStore(BPK)**: `.cmis/db/packs.db` (또는 brownfield.db 내 테이블)
- **DataOverridePatchStore(DOP)**: `.cmis/db/patches.db` (또는 brownfield.db 내 테이블)
- **OutcomeStore**: `.cmis/db/outcomes.db`
- **RunStore/LedgerStore**: `.cmis/db/runs.db`, `.cmis/db/ledgers.db`

> ImportRunStore는 “정본 갱신” 성격의 ingest 실행을 별도로 관리하기 위한 필수 저장소로 간주한다.

> ContextViewStore(PRJ_VIEW)는 “정본이 아닌 derived view”를 저장한다(권장: PRJ에는 cache를 넣지 않음).
> 최소 스키마 예(중첩 코드펜스 없이 표현):
    prj_view:
      focal_actor_context_id: PRJ-...-vN
      derived_from_bundle_digest: sha256:...  # 단일 모드
      # 또는 derived_from_sources_digest: sha256:...  # 멀티 모드
      view_payload_ref: ART-...  # (선택) 대용량 view externalize
      created_at: "..."

### 4.2 Storage Layout (Logical vs Physical; storage_profile)
- 스토어(Artifact/Curated/Pack/Context/ImportRun/Mapping)는 논리적으로 분리하되, 물리 DB 배치는 `storage_profile`로 제공한다.
- 최소 도입 단계(`minimal_local`)에서는 단일 sqlite(`brownfield.db`)에 MAP/IMP/CUR/CUB/BPK/PRJ/PRJ_VIEW/DOP 테이블을 통합해 운영/마이그레이션/원자성을 확보한다.
  - 예: `.cmis/db/brownfield.db`
  - 별도: `.cmis/db/runs.db`, `.cmis/db/ledgers.db` (RUN 감사/스냅샷)
- 보안/배포 요구가 커지면(`hardened`) evidence(외부)와 brownfield(내부)를 물리 분리한다.
  - 예: `.cmis/db/evidence.db` (외부 수집)
  - 예: `.cmis/db/brownfield.db` (내부/사용자 제공)

### 4.3 Large Payload Externalization (권장)
- CUR payload가 커질 수 있으므로, `payload_json`만 고집하지 않는다.
  - 기본: `payload_json` (작은/중간 규모)
  - 대용량: `payload_ref = ART-*`로 externalize하고, DB에는 메타/해시/ref만 저장

---

## 5. End-to-End Flow (권장)

### Phase 0: Goal Clarification (목표 구체화)
- 입력: 사용자 첫 질문
- 출력:
  - 목표/산출물 타입(`decision`/`reporting`/`exploration`)
  - 핵심 metric(필수/선택)
  - 정책 모드(엄격/균형/탐색)
  - prior 허용 범위
  - scope(as_of/horizon, domain/region/segment)

### Phase 1: Mode Decision (Greenfield/Brownfield/Hybrid)
- 질문/판정:
  - 내부 데이터/기준 상태가 필요한가?
  - focal actor(우리 조직/클라이언트)가 명확한가?
- 결과:
  - greenfield: 컨텍스트 없이 진행
  - brownfield/hybrid:
    - `focal_actor_context_id (PRJ-*)`를 생성/선택하여 컨텍스트 경로로 진입
    - `focal_actor_id (ACT-*)`는 WorldEngine overlay ingest 시점에 생성/확정되는 것이 기본(선택적으로 사전 입력 가능)
- 추가 분기(권장): **Brownfield Pack 선택**
  - 기존 `BPK`가 있으면 선택(또는 최신 validated bundle 자동 선택)
  - 없으면 intake/import로 진행 후 Phase 5에서 Pack 생성

### Phase 2: Intake Plan 생성 (동적 Quick-start)
- 입력: 구체화된 목표 + 모드 + (선택) pack
- 출력: `DataRequirementsSpec`
  - required_fields: baseline/assets/constraints/preferences 중 필요한 것
  - required_artifacts / optional_artifacts
  - derive_hints(정확도 향상용)
  - confidentiality/retention(기밀등급/보관/삭제)
  - normalization_defaults(통화/단위/기간/집계 기준)
  - as_of/horizon 명시

### Phase 3: Data Collection (업로드/입력)
- 업로드 파일은 전부 `ArtifactStore`에 저장(정본)
- run_store에는 원문이 아니라 `artifact_id`와 메타(파일명/해시/size/mime)만 기록

### Phase 4: Decode/Migrate (파일 파싱/구조화)
- 타입별 decoder:
  - csv: 표 인식 + 타입/단위 추정
  - docx/txt: 섹션/표/키-값 추출
  - xlsx: 9장 참고(레벨 1/2)
- 결과: curated intermediate 생성(아직 commit 전)

### Phase 4.5: Preview / Validate / Patch (필수 1급 단계)
- Preview:
  - 추출된 테이블/키값/기간 인식 결과를 사용자/에이전트가 확인
- Validate:
  - 단위/통화/기간 일관성, 필수 누락, 중복/불연속 등 검사
  - Policy 모드에 따른 pass/fail/warn 결정
- Patch:
  - MappingPatch:
    - 매핑 수정/추가(컬럼/시트 매칭, 단위/기간 규칙 보강)
    - patch는 새 `MAP version`으로 저장
    - 재추출 필요(새 `IMP` → 새 `CUB`)
  - DataOverridePatch(`DOP-*`):
    - 추출 결과(`CUR`/`CUB`)에 대한 값 보정
    - 근거/승인/lineage 기록 필수
    - 보정 적용 결과는 새 `CUB`(또는 `CUR vN`)로 커밋되어 digest/lineage에 반영
    - `reporting_strict`에서는 승인/근거 요건을 강화(권장: `approval_required` run_mode와 결합)

### Phase 5: Commit (정규화 후 스냅샷/컨텍스트 버전 생성)
- `ImportRun(IMP-*)` 확정(결정성 digest 포함)
- `CuratedBundle(CUB-*)` 생성(이번 import 결과 묶음)
- `CuratedDatum(CUR-*)` 생성(원자 데이터)
- `FocalActorContext(PRJ-*)` 새 버전 생성/업데이트
  - PRJ는 curated 데이터를 직접 포함하지 않고 **ref로 연결**하며,
    `primary_source_bundle(bundle_digest)`(또는 `source_bundles[*].bundle_digest`) + `context_builder_version`을 통해 재현 가능해야 한다(RUN pinning anchor)
- (선택) `BrownfieldPack(BPK-*)` 생성/업데이트(append-only 버전)

---

## 6. DataRequirementsSpec (Quick-start 스펙) — 권장 필수 항목

DataRequirementsSpec는 “필요한 파일 목록”뿐 아니라, 정규화 기준을 합의하기 위한 필수 항목을 포함해야 합니다.

- 목표/산출물:
  - output_type: decision/report/exploration
  - required_metrics / optional_metrics
- 범위:
  - domain/region/segment
  - as_of, horizon
- 정규화 기준(필수):
  - currency (KRW/USD 등)
  - unit (원/천원/백만원 등)
  - period_basis (monthly/quarterly/yearly)
  - aggregation_basis (누계/당기/평균 등)
- 기밀/보관:
  - confidentiality_level
  - retention_days
  - external_access (세분화; 기본 false 권장):
    - allow_web_search
    - allow_official_http_fetch (화이트리스트 기반)
    - allow_commercial_api
    - (선택) allow_llm_api
    - 최종 허용 = policy ∩ pack/spec ∩ runtime capability
- 데이터 요구:
  - required_fields (baseline/assets/constraints/preferences)
  - required_artifacts / optional_artifacts
  - derive_hints
- (선택) 기존 pack 사용:
  - `brownfield_pack_id`
  - as_of_selector(latest_validated/fixed_date/user_select)

---

## 7. Mapping Spec (MAP-*) 설계(최소)

### 7.1 매핑이 담아야 하는 것(권장)
- 입력:
  - artifact_id(ART-*), file_type, extractor_version
- 범위:
  - sheet/range, column mapping
- 필드 매핑:
  - source_column → target_field(CMIS schema field)
- 정규화 규칙:
  - currency/unit 변환
  - period/as_of 추출 규칙
  - 누계/당기/평균 정의
  - 타입 강제(int/float/string/category)
- 검증 규칙:
  - 필수 컬럼 존재
  - 값 범위/단위 체크
  - 기간 중복/누락 체크
- 메타:
  - mapping_version, schema_version, notes

### 7.2 매핑 예시(중첩 코드펜스 없이 표현)
    mapping:
      mapping_id: MAP-20251219-0001
      mapping_version: 3
      artifact_id: ART-...
      extractor_version: "xlsx_decoder@1.2.0"
      normalization_defaults:
        currency: KRW
        unit: "million_KRW"
        period_basis: yearly
        aggregation_basis: "period_value"
      bindings:
        - sheet: "P&L"
          range: "A1:G200"
          columns:
            year: "A"
            revenue: "C"
            cogs: "D"
          target_schema:
            entity: "financial_statement"
            statement_type: "income_statement"
      validations:
        - type: "required_columns"
          columns: ["year", "revenue"]
        - type: "period_monotonic"
          field: "year"

---

## 8. Validate / Report / Commit 정책

### 8.1 Validation Report (구조화)
검증 결과는 사람이 읽는 요약 + 기계가 읽는 구조화 형태로 저장합니다.

- errors:
  - missing_required_field
  - unit_mismatch
  - currency_mismatch
  - period_gap / duplicate_period
  - inconsistent_aggregation
- warnings:
  - low_coverage
  - suspicious_outliers
- suggested_patches:
  - mapping patch 제안(컬럼/기간/단위 규칙)
  - data override patch 제안(근거/승인 포함; `DOP-*`)
- policy_decision:
  - pass / fail / warn_only (mode 별로 다르게)

### 8.2 Commit gating(정책 연결)
- reporting_strict: errors 존재 시 commit 금지
- decision_balanced: 일부 errors 금지, 일부는 승인/대체 경로 허용
- exploration_friendly: warn_only 중심(치명 오류는 정책적으로 조정)

### 8.3 DataOverridePatch (DOP-*) 최소 스키마(권장)
- DataOverridePatch는 “추출 파이프라인을 고치기 어려운 경우”의 최후 수단이며,
  적용 결과는 새 `CUB`(또는 `CUR vN`)로 커밋되어 digest/lineage에 반영되어야 한다.
- 최소 권장 필드:
  - patch_id: `DOP-*`
  - type: `data_override`
  - applies_to:
    - bundle_id: `CUB-*`
    - (선택) datum_id: `CUR-*`
    - scope: field_path / row_key / period_range 등
  - operation: `set` | `add` | `multiply` | `delete` (최소 `set` 권장)
  - value: (정규화된 값)
  - reason_ref: `ART-*#...` (또는 validation report 항목 ref)
  - approved_by / approved_at: (reporting_strict 권장)
  - created_by / created_at

---

## 9. Spreadsheet(xlsx) Decode/Migrate 설계

### 9.1 원칙
- 엑셀은 “문서”이자 “계산 프로그램”
- CMIS는 최소한 다음을 보존해야 함:
  - 계산 결과(value)
  - 계산 근거(provenance, formula hint)

### 9.2 Level 1: Value-first (빠른 도입 + 최소 근거 보존)
- 표 추출 + 값 정규화
- 수식은 문자열로 저장하되, 최소 provenance를 함께 저장:
  - sheet 이름, range, cell 좌표(원본 위치)
  - named ranges/table objects(가능하면)
  - (가능하면) 참조 범위 힌트(dependency hint)
- Guardrails:
  - Level 1은 수식 계산을 재실행하지 않으며, 가능한 경우 cached result를 활용한다.
  - cached 값이 없는 수식 셀은 정책에 따라 fail/warn 처리한다(필수 필드 여부는 DataRequirementsSpec/Validation에서 결정):
    - reporting_strict: 필수 필드면 fail, 비필수는 warn
    - decision_balanced: warn + 필수 필드면 fail
    - exploration_friendly: warn
  - 지원 범위 밖(또는 별도 처리) 항목을 명시한다:
    - 외부 링크, 매크로, 피벗/파워쿼리 등
  - 기본 메타로 다음을 저장한다:
    - workbook hash
    - 시트별 used range 요약
    - missing cached count
    - cell 좌표 provenance(원본 위치)
- 목표:
  - “이 값이 어디에서 왔는지”는 재현/감사 가능해야 함
  - 완전한 수식 재실행은 목표로 하지 않음

### 9.3 Level 2: Formula-aware (고도화)
- 수식 그래프(셀 의존성)를 추출하여 `CUR(datum_type=model)`로 저장
- 핵심 metric의 derivation path를 “어떤 시트/셀/수식에서 나왔는지”까지 연결
- 재현성/검증 중심으로 단계적 도입(100% 재실행 목표는 범위를 조절)

---

## 10. Curated Store 설계 (Evidence와 분리)

### 10.1 CuratedDatum (CUR-*) 최소 스키마
- datum_id (CUR-*)
- datum_type: table | timeseries | statement | kv | model
- as_of / period
- schema_version
- payload_json (정규화된 데이터; 소형/중형)
- (선택) payload_ref (대용량은 ART-*로 externalize)
- lineage:
  - from_artifact_ids: [ART-*]
  - mapping_id@version
  - extractor_version
  - ingest_policy_digest
  - patches:
    - patch_id: DOP-* (applied overrides)
  - notes
- quality:
  - verified: bool
  - confidence
  - unit_normalized: bool
  - validation_report_ref

### 10.2 CuratedBundle (CUB-*) 역할
- 한 번의 import 결과를 묶는 스냅샷 단위
- pack 업데이트/재사용/롤백의 기준점

### 10.3 CuratedBundle (CUB-*) 최소 스키마(권장) + digest
- 권장 필드(메타/참조):
  - bundle_id: `CUB-*`
  - bundle_digest: `sha256:...`
  - import_run_id: `IMP-*` (링크/감사용 메타; digest 입력에는 기본적으로 포함하지 않음)
  - as_of / period_range
  - curated_datum_refs: [`CUR-*`, ...] (링크 메타; digest 입력에는 기본적으로 포함하지 않음)
  - lineage_summary:
    - from_artifact_ids
    - mapping_id@version
    - extractor_version
    - ingest_policy_digest
    - patch_chain_digests (또는 patches_digest)
  - quality_summary:
    - verified
    - validation_report_ref
- bundle_digest 정의(권장; 결정성):
  - `CUB.bundle_digest = sha256(canonical_json(cub_digest_input))`
  - `cub_digest_input`에 포함 권장(IDs 대신 content digest 중심):
    - schema_version
    - normalization_defaults_digest
    - ingest_policy_digest
    - mapping_ref:
      - mapping_id
      - mapping_version
      - (선택) mapping_digest
    - extractor_version
    - patch_chain_digests:
      - "sha256:patch1..."
      - "sha256:patch2..." (적용 순서 포함)
    - curated_items:
      - semantic_key: "statement:income:2024FY"  # datum_type + entity + period/as_of 등 안정 키
        cur_payload_digest: "sha256:..."
        cur_schema_version: 1  # optional
  - 정렬/정규화 규칙(필수):
    - `curated_items`는 `semantic_key`로 정렬
    - `patch_chain_digests`는 적용 순서(또는 precedence)로 정렬
    - JSON은 키 정렬 + 안정화된 표현(숫자/날짜/공백)
  - 원칙:
    - `import_run_id`, `curated_datum_ids` 같은 비결정적 ID는 digest 입력에서 제외(링크 메타로만 저장)

---

## 11. Brownfield Pack (BPK-*) — 재사용 가능한 Brownfield 묶음

> Pack은 “데이터 복제”가 아니라 “참조 묶음(인덱스)”으로 구현한다.
> Pack은 append-only 버전이며, RUN은 기본적으로 `PRJ vN` 1개만 pin한다. Pack은 UX/선택을 위한 참조로 기록될 수 있다.

- Pack은 조직(focal actor)별 재사용 가능한 내부 데이터 패키지
- 번들(CUB)을 시간 순으로 축적하고, defaults(as_of 선택 규칙)를 제공
- confidentiality/retention/external_access(allow_web_search/allow_official_http_fetch/allow_commercial_api/allow_llm_api) 기본값을 내장해 정책 강제와 결합

(세부 스키마/흐름/저장소/CLI는 본 문서의 14~16절을 기반으로, 후속 구현 문서에서 확정한다.)

---

## 12. EvidenceEngine과의 통합 (소비 인터페이스 통일)

### 12.1 분리 저장 + 통일 소비
- 저장:
  - 외부 evidence → EvidenceStore
  - 내부 curated → CuratedStore(+ Pack/Bundle)
- 소비:
  - EvidenceEngine은 `EvidenceProvider` 계층으로 통일하여 조회
    - WebEvidenceProvider
    - CuratedEvidenceProvider (pack/bundle 기반)

### 12.2 정책 적용
- 최종 허용은 `policy ∩ pack/spec ∩ runtime capability`의 교집합으로 결정한다:
  - allow_web_search: 외부 웹검색
  - allow_official_http_fetch: 화이트리스트 기반 공식 API fetch
  - allow_commercial_api: 상용 API
  - allow_llm_api: LLM API 호출(선택)
- 결과물 노출(요약/원문) 강도 조절은 policy 모드 및 pack confidentiality에 의해 결정된다.

---

## 13. 보안/권한/감사(최소 정책)

- run_store/events/decision_log에는 원문/대량 수치 금지(메타+ref만)
- artifact는 로컬 저장 기준, 접근 권한(팀/개인/프로젝트) 지원
- pack/confidentiality 레벨에 따라 외부 검색/공유 제한
- delete/retention 정책을 pack 및 curated에 적용(보관기간 만료 시 폐기 가능)

---

## 14. CLI/Workflow 제안(최소)

- Ingest (MVP):
  - `cmis brownfield import --file ... [--mapping MAP-...@vN] [--policy-mode ...]`
    - 출력: `IMP-*` (import_run_id)
  - `cmis brownfield preview --import-run IMP-*`
    - 출력: 요약 + `preview_report_artifact_id(ART-*)`
  - `cmis brownfield validate --import-run IMP-*`
    - 출력: 요약 + `validation_report_artifact_id(ART-*)` + policy_decision(pass/fail/warn_only)
  - `cmis brownfield commit --import-run IMP-* [--focal-actor-context-id PRJ-...]`
    - 출력: `CUB-*`, `PRJ-...-vN`
- Template (Post-MVP):
  - `cmis brownfield template --out template.xlsx`
- Pack (Post-MVP):
  - `cmis brownfield pack list/show/create/update`
- Verify:
  - `cmis context verify PRJ-...-vN`
    - alias(latest) pin 금지, PRJ vN pin 강제
    - PRJ → CUB digest 일치(primary_source_bundle 또는 source_bundles)
    - context_builder_version 기록 존재
    - CUB lineage에 ingest_policy/mapping/extractor/patch_chain 정보 누락 금지
    - (view가 있다면) derived_from_bundle_digest 불일치 시 view 무시/재생성
  - (선택) `cmis brownfield verify BPK-...-vN`
    - pack이 참조하는 PRJ/CUB 일괄 verify
- Run:
  - `cmis run start --focal-actor-context-id PRJ-...-vN --as-of ...`
  - (선택) `cmis run start --brownfield-pack BPK-...-vN --as-of ...`
    - 내부적으로 pack에서 PRJ vN(또는 CUB)을 resolve하되, RUN은 PRJ를 pin한다.

---

## 15. 다음 액션(권장 우선순위)

- 본 문서의 “MVP-first 구현/테스트 계획”은 16절(Implementation Plan)을 기준으로 진행합니다.
- Milestone 1 (CSV MVP end-to-end):
  - BF-00 → BF-01 → BF-02a → BF-02b → BF-03 → BF-04 → BF-05a → BF-05 → BF-09a → BF-10 → BF-11 → BF-12 → BF-13 → BF-15
- Milestone 2 (XLSX Level 1 + guardrails):
  - BF-09b + BF-10(룰 확장) + E2E 테스트 추가
- Milestone 3 (운영 기능):
  - BF-06(DOP) → BF-07(PRJ_VIEW) → BF-08(BPK) → BF-14(Provider)

---

## 16. Brownfield Implementation Plan (MVP-first) — aligned with v3.6.0 contracts

### 16.1 목표/범위 (MVP)

#### MVP 목표
- csv/xlsx(Level 1) 업로드 → preview → validate(+report) → patch(최소: MappingPatch, 선택: DataOverridePatch) → commit(IMP/CUR/CUB/PRJ vN 생성) → verify(PRJ/CUB 계약 강제)
- minimal_local(storage_profile) = 단일 `brownfield.db`(sqlite) + `.cmis/artifacts/` 파일 저장을 1차 타겟으로 함
- “깨지지 않게”의 기준은 **Contract enforcement(Verify)** 를 포함하는 것

#### MVP 비목표(후순위)
- CuratedEvidenceProvider로 EvidenceEngine 소비 통합(BF-14) = V2
- BrownfieldPack(BPK) 완성형 UX = V2
- PRJ_VIEW(derived view) = V2(다만 훅/테이블은 최소 형태로 미리 깔아도 됨)

#### DoD(완료 정의) — CI로 고정
- 시나리오 A (CSV):
  1) import → preview → validate(pass) → commit → context verify PASS
- 시나리오 B (XLSX Level 1):
  1) import → preview → validate(warn/fail 규칙 적용) → commit 조건부 → verify PASS(커밋된 경우)
- 시나리오 C (결정성/idempotent):
  - 동일 입력(ART+MAPv+policy+defaults+patches)에서 `CUB.bundle_digest` 동일
- 시나리오 D (누출 방지):
  - CLI stdout / run_store / events / decision_log에 원문/대량 수치 미포함(메타+ref만)

---

### 16.2 Critical Path(최소 성공 경로)

BF-00 ArtifactStore
→ BF-01 Digest/C14N
→ BF-02a Schema/Migration (brownfield.db)
→ BF-02b UnitOfWork/Transaction (원자 커밋)
→ BF-03 Mapping(MAP)
→ BF-04 ImportRun(IMP)
→ BF-05a semantic_key 표준
→ BF-05 CUR/CUB + CUB digest
→ BF-09a CSV ingest + Preview
→ BF-10 Validate/Report + Commit gating
→ BF-11 PRJ Builder + Commit Orchestrator(원자 커밋)
→ BF-12 Verify(Contract enforcement) + CLI
→ BF-13 CLI 통합
→ BF-15 E2E DoD 시나리오 테스트(CI 고정)

(이후) BF-09b XLSX Level1, BF-06 DOP, BF-07 PRJ_VIEW, BF-08 BPK, BF-14 Provider

---

### 16.3 데이터 모델/DB 스키마 (minimal_local: brownfield.db)

#### 기본 원칙
- SoT는 DB(메타) + ART(대용량 payload)로 구성
- digest는 UNIQUE 또는 강한 인덱스로 “중복/드리프트”를 차단
- commit은 한 트랜잭션으로: IMP(커밋) + CUR/CUB 생성 + PRJ vN 생성 (+ 선택: PRJ_VIEW/BPK vN)

#### 테이블(권장 최소)
- artifacts
- mappings
- import_runs
- curated_data
- curated_bundles
- dop_patches (V2 또는 최소 형태)
- focal_actor_contexts (PRJ)
- context_views (PRJ_VIEW, V2)
- packs (BPK, V2)

※ evidence.db 분리(hardened)는 V2(프로파일)에서 수행

---

### 16.4 BF 항목별 스펙 (MVP 중심)

#### BF-00: ArtifactStore(ART) + file hashing + staging
**목표**
- 원본 파일/대용량 리포트(ValidationReport/PreviewReport 포함)를 ART로 저장
- 누출 방지: CLI/log에는 ART ref만

**DB (artifacts)**
- artifact_id TEXT PK  (ART-*)
- sha256 TEXT NOT NULL
- size_bytes INTEGER
- mime TEXT
- original_filename TEXT
- storage_path TEXT NOT NULL  (e.g., .cmis/artifacts/ART-...bin)
- created_at TEXT
- UNIQUE(sha256, size_bytes)  (옵션: 동일 파일 dedupe)

**API**
- ArtifactStore.put_file(path|bytes, mime, filename) -> artifact_id
- ArtifactStore.get_path(artifact_id) -> path
- ArtifactStore.meta(artifact_id) -> meta

**CLI**
- 내부 사용(직접 노출 X) 또는 `cmis artifact show ART-*`(선택)

**Tests**
- 동일 바이트 입력 → 동일 sha256
- 파일 저장 후 경로 존재
- stdout에 원문 바이트 출력 금지(스냅샷 테스트)

---

#### BF-01: Deterministic hashing (canonical_json + sha256) + golden tests
**목표**
- CUB digest / patch digest / defaults digest / view digest 등 결정성의 기반 제공

**API**
- canonical_json(obj, rules=...) -> str/bytes
- sha256_hex(bytes) -> "sha256:..."
- canonical_digest(obj) -> "sha256:..."  (json + sha256)

**Rules(필수 고정)**
- dict key sort
- 숫자/날짜 표준화(예: Decimal/ISO8601)
- list 처리:
  - 순서 의미 없는 리스트는 caller가 정렬(semantic_key 등)
  - 순서 의미 있는 리스트는 그대로(예: patch_chain)

**Tests**
- golden vector: 동일 객체 digest 동일
- 키 순서/공백 변형에도 digest 동일
- float edge(1 vs 1.0) 규칙 고정 테스트

---

#### BF-02a: storage_profile(minimal_local) + schema/migrations
**목표**
- brownfield.db 단일 DB에서 스키마/마이그레이션 관리
- 스키마 마이그레이션 가능(버전 테이블)

**DB**
- schema_version(table) or migrations(table)

**API**
- DB.open(profile="minimal_local") -> conn
- migrate_if_needed(conn)

**Tests**
- migration idempotent

---

#### BF-02b: UnitOfWork(Transaction) — 원자 커밋
**목표**
- commit은 한 트랜잭션으로: IMP(커밋) + CUR/CUB 생성 + PRJ vN 생성 (+ 선택: PRJ_VIEW/BPK vN)
- 실패 시 rollback(불완전 상태 방지)

**API**
- UnitOfWork(conn).transaction(): commit/rollback

**Tests**
- commit 중 예외 발생 시 rollback(중간 객체 생성 금지)

---

#### BF-03: MappingSpec(MAP) + MappingStore + MappingPatch=MAP version up
**목표**
- MAP을 독립 객체로 저장/버전 관리
- MappingPatch는 MAP version up으로만 표현(재추출 필요)

**DB (mappings)**
- mapping_id TEXT
- mapping_version INTEGER
- mapping_digest TEXT NOT NULL
- artifact_id TEXT NULL  (템플릿/일반 매핑 공용을 위해 optional)
- extractor_version TEXT
- schema_version INTEGER
- spec_json TEXT or spec_ref ART-*
- created_at TEXT
- PRIMARY KEY(mapping_id, mapping_version)
- UNIQUE(mapping_digest)

**API**
- MappingStore.create(spec) -> (mapping_id, version, digest)
- MappingStore.get(mapping_id, version) -> spec
- MappingStore.bump_version(mapping_id, new_spec) -> new_version

**Tests**
- 동일 spec → 동일 mapping_digest
- bump_version 시 version 증가 + digest 변경

---

#### BF-04: ImportRun(IMP) + ImportRunStore (staged/validated/committed)
**목표**
- ingest 실행 단위를 상태 머신으로 관리
- idempotent는 “결과(CUB/CUR) 재사용”을 기본으로, IMP는 새로 생성 가능(정책 선택)

**DB (import_runs)**
- import_run_id TEXT PK (IMP-*)
- status TEXT  (staged|decoded|validated|committed|rejected)
- created_at TEXT
- artifact_ids_json TEXT  (list of ART refs)
- mapping_ref_json TEXT   (mapping_id+version)
- extractor_version TEXT
- ingest_policy_digest TEXT
- normalization_defaults_digest TEXT
- patches_digest TEXT NULL
- input_fingerprint TEXT NOT NULL  (결정성 입력 fingerprint; UNIQUE는 정책)
- validation_report_artifact_id TEXT NULL
- preview_report_artifact_id TEXT NULL
- committed_bundle_id TEXT NULL (CUB-*)
- notes TEXT

**API**
- ImportRunStore.create_staged(inputs...) -> IMP
- ImportRunStore.attach_preview(IMP, ART)
- ImportRunStore.attach_validation(IMP, ART, decision)
- ImportRunStore.mark_committed(IMP, CUB)
- ImportRunStore.get(IMP)

**Tests**
- 상태 전이 규칙 강제(staged→validated→committed)
- 동일 input_fingerprint 처리 정책 테스트(재사용/새생성)

---

#### BF-05a: semantic_key 표준(규약 + 생성기)
**목표**
- CUB digest의 결정성 축인 semantic_key 규약을 고정한다.
- 대표 datum_type(statement/timeseries/kv 등)별 key 구성요소를 표준화한다.

**API**
- semantic_key.make(datum_type, entity, period/as_of, ...) -> str

**Tests**
- 동일 입력이면 동일 semantic_key
- 대표 케이스에서 충돌/흔들림 없이 안정적으로 생성

---

#### BF-05: CuratedDatum(CUR) / CuratedBundle(CUB) + CUB digest
**목표**
- CUR는 원자 데이터(표/시계열/statement/kv/model)
- CUB는 스냅샷 묶음(커밋 단위), digest가 재현성의 중심
- digest 입력은 ID가 아니라 content digest 중심

**DB (curated_data)**
- datum_id TEXT PK (CUR-*)
- datum_type TEXT
- semantic_key TEXT NOT NULL
- as_of TEXT NULL
- period_range TEXT NULL
- schema_version INTEGER
- payload_json TEXT NULL
- payload_ref_artifact_id TEXT NULL
- cur_payload_digest TEXT NOT NULL
- lineage_json TEXT  (from_artifact_ids, mapping_ref, extractor_version, ingest_policy_digest, patches...)
- created_at TEXT
- UNIQUE(cur_payload_digest, semantic_key, schema_version)  (권장)
- INDEX(semantic_key)

**DB (curated_bundles)**
- bundle_id TEXT PK (CUB-*)
- bundle_digest TEXT NOT NULL UNIQUE
- import_run_id TEXT NULL  (링크 메타; digest 입력 기본 제외)
- as_of TEXT NULL
- schema_version INTEGER
- normalization_defaults_digest TEXT
- ingest_policy_digest TEXT
- mapping_ref_json TEXT
- extractor_version TEXT
- patch_chain_digests_json TEXT
- curated_items_json TEXT  (list of {semantic_key, cur_payload_digest, cur_schema_version?})
- quality_summary_json TEXT
- created_at TEXT

**API**
- semantic_key.make(datum_type, entity, period/as_of, ...) -> str (BF-05a 규약)
- CuratedStore.put_cur(...)-> CUR
- CuratedBundleStore.put_cub(cub_digest_input)-> CUB (dedupe by bundle_digest)
- compute_cub_digest(cub_digest_input)-> bundle_digest

**Tests**
- curated_items 정렬(semantic_key)로 digest 안정화
- 동일 입력이면 동일 bundle_digest
- ID가 달라도 content 동일이면 bundle_digest 동일

---

#### BF-09a: CSV Level 1 ingest + Preview (MVP 먼저)
**목표**
- csv → curated intermediate 생성 → preview report(ART 저장)까지
- 원문/대량 출력 금지(요약만)

**API**
- CsvDecoder.decode(artifact_id, mapping_ref?, defaults)-> decoded_intermediate
- PreviewBuilder.build(decoded_intermediate)-> preview_summary_json
- PreviewReport.save_as_artifact(preview_summary)-> ART

**CLI**
- `cmis brownfield import --file data.csv [--mapping MAP-...@vN] [--mode ...]`
  - returns IMP-*
- `cmis brownfield preview --import-run IMP-*`
  - prints summary + preview_report ART ref

**Tests**
- 샘플 csv로 preview 생성
- stdout에 원문 행 덤프 금지(요약만)

---

#### BF-09b: XLSX Level 1 ingest + Guardrails + Preview (MVP 확장)
**목표**
- xlsx value-first + provenance 최소 보존 + guardrails(캐시 부재/지원범위 밖)
- missing cached count / used range / workbook hash 등 메타 저장

**API**
- XlsxDecoderL1.decode(artifact_id, mapping_ref, defaults)-> decoded_intermediate(+meta)
- GuardrailEvaluator.evaluate(decoded_meta)-> warnings/errors
- PreviewBuilder.build(...)-> preview_summary_json

**Tests**
- cached value 없는 수식 셀 케이스에서 strict 모드 fail/warn 판정
- 외부 링크/매크로/피벗은 “unsupported”로 표기

---

#### BF-10: ValidationReport + commit gating ruleset
**목표**
- Validate는 “저장”이 아니라 “결정(pass/fail/warn_only)”과 “suggested patches”가 핵심
- ValidationReport는 ART로 저장(원문 포함 금지)

**API**
- Validator.validate(decoded_intermediate, requirements_spec, policy_mode)-> ValidationResult
  - errors[], warnings[], suggested_mapping_patches[], suggested_data_override_patches[]
  - policy_decision(pass/fail/warn_only)
- ValidationReport.save_as_artifact(result_summary)-> ART
- CommitGate.check(validation_result, policy_mode)-> allow/deny

**CLI**
- `cmis brownfield validate --import-run IMP-*`
- validate 결과를 IMP에 attach

**Tests**
- 필수 누락/단위 불일치/기간 중복 등 룰 테스트
- 모드별 gating matrix 테스트

---

#### BF-06: DataOverridePatch(DOP) + patch chain digest + apply (V2 또는 XLSX 이후)
**목표**
- mapping은 맞는데 값만 보정해야 하는 운영 현실 대응
- 적용 결과는 새 CUB 생성(append-only), lineage/승인/근거 강제

**DB (dop_patches)**
- patch_id TEXT PK (DOP-*)
- applies_to_bundle_id TEXT (CUB-*)
- applies_to_datum_id TEXT NULL (CUR-*)
- operation TEXT (set/add/multiply/delete)
- target_path TEXT (field_path/row_key/period_range 등)
- value_json TEXT
- reason_ref TEXT (ART-*#...)
- approved_by TEXT NULL
- approved_at TEXT NULL
- patch_digest TEXT NOT NULL UNIQUE
- created_at TEXT

**API**
- DOPStore.create(...) -> DOP
- PatchChain.compute_digest([patch_digest...]) -> patches_digest
- PatchApplier.apply(bundle_id, patches)-> new_cub_digest_input -> new CUB

**Tests**
- DOP 적용 시 bundle_digest 변경 + lineage patches 반영
- strict 모드에서 승인 누락이면 deny

---

#### BF-11: PRJ Builder (CUB → FocalActorContext PRJ vN) + Commit Orchestrator
**목표**
- RUN pinning anchor는 PRJ 1개(문서 2.6)
- PRJ는 ingest provenance 정본이 아니므로, CUB(및 digest)만 참조 + builder_version 고정
- commit은 원자적으로: IMP committed + CUR/CUB + PRJ vN 생성

**DB (focal_actor_contexts)**
- focal_actor_context_id TEXT PK (PRJ-...-vN)
- focal_actor_id TEXT NULL (옵션)
- prj_version INTEGER (또는 id에 내장)
- primary_source_bundle_json TEXT  ({bundle_id, bundle_digest, role?})
- source_bundles_json TEXT NULL (멀티 모드)
- context_builder_version TEXT NOT NULL
- context_builder_config_digest TEXT NULL
- context_policy_digest TEXT NULL
- context_payload_json TEXT (요약/포인터; 대량 데이터 금지)
- created_at TEXT

**API**
- ContextBuilder.build_from_cub(cub_id, builder_version, config)-> prj_payload
- PRJStore.create_new_version(...)-> PRJ vN
- CommitOrchestrator.commit(IMP):
  - (txn) validate decision OK?
  - upsert CUR, upsert CUB(dedupe by digest)
  - create PRJ vN(anchors to CUB digest)
  - mark IMP committed -> committed_bundle_id

**Tests**
- 동일 CUB+builder_version이면 동일 PRJ payload(결정성)
- commit 중간 실패 시 rollback
- PRJ에 artifact/mapping/extractor “필수” 중복 금지(문서 준수)

---

#### BF-12: Verify Contract enforcement + CLI
**목표**
- verify는 유틸이 아니라 gate(문서 2.8)
- PRJ pin은 alias 금지, PRJ vN만

**API**
- ContextVerifier.verify_prj(prj_id)-> PASS/FAIL + reasons
  - PRJ id 형식 검증(vN)
  - PRJ.primary_source_bundle.bundle_digest == CUB.bundle_digest
  - builder_version 존재
  - (간접) CUB에 ingest_policy/mapping/extractor/patch_chain 존재
- BrownfieldVerifier.verify_pack(bpk_id)-> (V2)

**CLI**
- `cmis context verify PRJ-...-vN`
- (선택) `cmis brownfield verify BPK-...-vN`

**Tests**
- digest 불일치 시 FAIL
- builder_version 누락 시 FAIL
- alias 입력 시 FAIL

---

#### BF-13: Brownfield CLI 그룹 통합 + 테스트
**목표**
- import/preview/validate/commit/verify를 한 CLI 그룹으로 제공
- stdout는 항상 요약 + ref, 상세는 ART 열람

**CLI commands (MVP)**
- `cmis brownfield import --file ... [--mapping ...] [--policy-mode ...]`
- `cmis brownfield preview --import-run IMP-*`
- `cmis brownfield validate --import-run IMP-*`
- `cmis brownfield commit --import-run IMP-*`
- `cmis context verify PRJ-...-vN`

**Tests**
- E2E integration test: csv 흐름 1회로 PASS
- 누출 방지: stdout snapshot test(원문/대량 숫자 없음)

---

#### BF-15: E2E DoD 시나리오 테스트(CI 고정)
**목표**
- 16.1의 DoD(시나리오 A~D)를 통합 테스트로 고정해 회귀/드리프트를 방지한다.

**Tests**
- 시나리오 A (CSV): import → preview → validate(pass) → commit → context verify PASS
- 시나리오 C (결정성/idempotent): 동일 입력에서 bundle_digest 동일 + dedupe 정책대로 중복 생성 방지
- 시나리오 D (누출 방지): CLI stdout 및 run_store/events/decision_log에 원문/대량 수치 미포함(메타+ref만)

---

### 16.5 V2 확장 항목 (안정화 이후)

- BF-07: ContextViewStore(PRJ_VIEW) — derived view 분리 저장 + derived_from_digest 검증
- BF-08: BrownfieldPack(BPK) — append-only + as_of_selector + pack verify
- BF-14: CuratedEvidenceProvider — EvidenceEngine 소비 통합

---

### 16.6 구현 순서(현실적인 3개 마일스톤)

#### Milestone 1 (CSV MVP end-to-end)
BF-00 → BF-01 → BF-02a → BF-02b → BF-03 → BF-04 → BF-05a → BF-05 → BF-09a → BF-10 → BF-11 → BF-12 → BF-13 → BF-15

#### Milestone 2 (XLSX Level 1 + guardrails)
BF-09b + BF-10 룰 확장(수식 캐시/unsupported) + E2E 테스트 추가

#### Milestone 3 (운영 기능)
BF-06(DOP) → BF-07(PRJ_VIEW) → BF-08(BPK) → BF-14(Provider)

---
