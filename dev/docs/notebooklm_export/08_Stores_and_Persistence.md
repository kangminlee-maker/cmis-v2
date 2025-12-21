# CMIS Stores 및 영속화

**생성일**: 2025-12-21 11:28:56
**목적**: 데이터 저장 및 관리 시스템

---

## artifact_store

### 모듈 설명

```
ArtifactStore (local object_store + SQLite meta).

Artifact(ART-*)는 리포트/차트/샘플/중간 산출물 등 "대용량/파일 기반" 결과를 저장합니다.

Phase 1 목표:
- 파일은 `.cmis/artifacts/`에 저장
- 메타데이터는 `.cmis/db/artifacts.db`에 저장

주의:
- Phase 1에서는 로컬 파일 백엔드를 object_store로 취급합니다.

BF-00 목표(확장):
- 업로드 파일 및 대용량 산출물(ValidationReport/PreviewReport)을 ART로 저장
- sha256/size/mime/original_filename 메타를 저장하여 결정성/감사를 지원
- CLI/log에는 원문/대량 데이터가 아니라 ART ref만 남기도록 설계(누출 방지)
```

### 주요 클래스

#### `ArtifactStore`

Artifact 저장소.

**Public 메서드**:

```python
def put_file(self, file_path: Path) -> str
```
파일을 Artifact로 저장합니다(원문/대용량 산출물용).

```python
def put_bytes(self, data: bytes) -> str
```
bytes를 Artifact로 저장합니다.

```python
def put_json(self, data: Any) -> str
```
JSON artifact 저장.

---

## doctor

### 모듈 설명

```
Runtime storage doctor (local-first).

목표:
- 실제 인프라(Postgres/S3 등) 전환 전에도, 현재 런타임 스토리지(`.cmis/`)의
  무결성과 참조 관계가 깨지지 않았는지 빠르게 점검할 수 있어야 합니다.

주의:
- 이 모듈은 기본적으로 "빠른 모드"만 제공합니다.
  - SQLite는 `PRAGMA quick_check`로 최소 무결성 검사
  - Artifact는 메타(DB) ↔ 파일 존재 여부/크기만 점검(sha256 재계산은 하지 않음)
```

### 주요 클래스

#### `StorageDoctorResult`

스토리지 점검 결과.

---

## factory

### 모듈 설명

```
Stores factory (local backend).

목표:
- Store 생성/경로 결정을 한 곳으로 모아, 이후 인프라(Postgres/S3 등) 전환 시 변경 지점을 최소화합니다.
- 현재는 local-first( SQLite + 파일 ) 구현만 제공합니다.
```

### 주요 클래스

#### `StoreFactory`

스토어 생성 팩토리.

설계 의도:
- project_root를 중심으로 StoragePaths를 고정하고,
  그 경로 규칙 하에서 각 store 인스턴스를 생성합니다.

NOTE:
- 반환되는 store 인스턴스는 각각 SQLite 연결을 생성합니다.
- 호출자가 close() 책임을 갖습니다.

**Public 메서드**:

```python
def paths(self) -> StoragePaths
```

```python
def run_store(self) -> RunStore
```

```python
def ledger_store(self) -> LedgerStore
```

---

## focal_actor_context_store

### 모듈 설명

```
FocalActorContextStore (SQLite).

cmis.yaml의 store key는 `focal_actor_context_store`이며,
`FocalActorContext`(PRJ-*)를 저장합니다.

Phase 1 목표:
- PRJ 컨텍스트를 sqlite에 저장/조회(최신/버전)
- context_binding/learning 경로에서 "store 우선, 없으면 fallback"을 가능하게 함

저장 규칙(Phase 1):
- `context_id`는 base PRJ id로 취급합니다.
  - 예: PRJ-abc-v2 → context_id=PRJ-abc, version=2
- `record_json`은 dataclass 전체를 저장합니다.
```

### 주요 클래스

#### `FocalActorContextStore`

FocalActorContext(PRJ-*) 버전 관리 스토어.

**Public 메서드**:

```python
def save(self, record: FocalActorContext) -> None
```
컨텍스트 레코드를 저장(UPSERT)합니다.

```python
def get_latest(self, focal_actor_context_id: str) -> Optional[FocalActorContext]
```
base id 기준 최신 버전을 조회합니다.

```python
def get_by_version(self, focal_actor_context_id: str, version: int) -> Optional[FocalActorContext]
```
base id + version으로 특정 버전을 조회합니다.

---

## ledger_store

### 모듈 설명

```
LedgerStore (SQLite).

정본(ledger_store)은 run_id별로 ProjectLedger/ProgressLedger 스냅샷을 저장합니다.
Cursor UX는 이 스냅샷을 `.cmis/runs/<run_id>/`로 export(view)하여 소비합니다.
```

### 주요 클래스

#### `LedgerStore`

SQLite 기반 LedgerStore

**Public 메서드**:

```python
def save_snapshot(self, run_id: str, project_ledger: Dict[(str, Any)], progress_ledger: Dict[(str, Any)]) -> None
```

```python
def get_latest_snapshot(self, run_id: str) -> Optional[Dict[(str, Any)]]
```

```python
def close(self) -> None
```

---

## outcome_store

### 모듈 설명

```
OutcomeStore (SQLite).

Outcome(OUT-*)는 LearningEngine이 참조하는 실행 결과 레코드입니다.

Phase 1 목표:
- Outcome 레코드를 sqlite에 저장/조회
- LearningEngine이 store 우선으로 로딩할 수 있도록 최소 API 제공
```

### 주요 클래스

#### `OutcomeStore`

Outcome(OUT-*) 저장소.

**Public 메서드**:

```python
def save(self, outcome: Outcome) -> None
```

```python
def get(self, outcome_id: str) -> Optional[Outcome]
```

```python
def list_by_focal_actor_context(self, focal_actor_context_id: str) -> List[str]
```
특정 FocalActorContext에 연결된 outcome_id 목록.

---

## run_store

### 모듈 설명

```
RunStore (SQLite).

정본(run_store)은 다음을 보관합니다.
- run 메타(request 스냅샷 요약)
- events stream
- decision log stream
```

### 주요 클래스

#### `RunStore`

SQLite 기반 RunStore

**Public 메서드**:

```python
def create_run(self, run: Dict[(str, Any)]) -> None
```

```python
def append_event(self, run_id: str, event: Dict[(str, Any)]) -> None
```

```python
def append_decision(self, run_id: str, decision: Dict[(str, Any)]) -> None
```

---

## sqlite_base

### 모듈 설명

```
SQLite store base utilities.

저장 경로 규칙:
- 기본: <project_root>/.cmis/
- 테스트/격리: 환경변수 `CMIS_STORAGE_ROOT`가 있으면 그 경로를 root로 사용
```

### 주요 클래스

#### `StoragePaths`

스토리지 경로 집합.

기본 규칙:
- storage_root 아래에 `.cmis/`를 생성하고, 그 하위에 DB/아티팩트/캐시/런 뷰를 저장합니다.
- 테스트/격리: 환경변수 `CMIS_STORAGE_ROOT`가 있으면 이를 storage_root로 사용합니다.

**Public 메서드**:

```python
def evidence_cache_db_path(self) -> Path
```
legacy evidence_cache.db 위치.

```python
def resolve(project_root: Optional[Path]) -> StoragePaths
```

---

## Brownfield Stores

### context_view_store

ContextViewStore (PRJ_VIEW) — derived view cache (BF-07).

ContextView(PRJ_VIEW-*)는 FocalActorContext(PRJ-...-vN)에서 파생된 "derived view"를 저장합니다.

원칙:
- PRJ_VIEW는 정본(SoT)이 아닙니다. 언제든 폐기/재생성 가능합니다.
- PRJ_VIEW는 PRJ의 입력(=CUB digest 등)에 대한 파생 결과이므로,
  `derived_from_*_digest`를 기록해 드리프트를 감지합니다.

검증 계약(최소):
- 단일 모드: view.derived_from_bundle_digest == PRJ.lineage.primary_source_bundle.bundle_digest
- 멀티 모드(선택): view.derived_from_sources_digest == sha256(canonical_json(source_bundles))

주의:
- view payload는 ArtifactStore(ART-*)로 externalize하고, DB에는 ref만 저장합니다.

### curated_store

Curated stores (BF-05).

CUR( CuratedDatum ) / CUB( CuratedBundle )는 Brownfield 내부 데이터의 정본(SSoT)입니다.

원칙:
- CUR: 원자 데이터(테이블/시계열/statement/kv/model)
- CUB: 커밋 스냅샷 단위(여러 CUR를 묶음)
- digest는 ID가 아니라 content digest 중심으로 계산

### dop_store

DataOverridePatch store + applier (BF-06).

DataOverridePatch(DOP-*)는 "추출 파이프라인을 고치기 어려운 경우"를 위한 최후 수단입니다.

핵심 계약:
- Patch는 append-only(새 CUB 생성)로 반영되어야 하며, digest/lineage에 반영됩니다.
- reporting_strict 모드에서는 DOP 적용 시 승인(approved_by/approved_at) 요건을 강제합니다.
- patch_digest는 patch_id/created_at/승인 메타에 의존하지 않고 결정적으로 계산됩니다.

주의:
- 본 모듈은 "값의 의미"(row_key/period_range 등)를 해석하지 않습니다.
  target_path는 JSON Pointer(RFC 6901)로 해석되며, payload_json에 직접 적용합니다.

### import_run_store

ImportRunStore (BF-04).

ImportRun(IMP)은 Brownfield ingest 실행 단위를 나타내며, 상태 머신으로 관리합니다.

상태(권장):
- staged: 파일/입력 수집 완료
- decoded: decode 완료(preview 생성 가능)
- validated: validate 완료(결정 pass/warn_only 포함)
- rejected: validate 결과 fail
- committed: CUR/CUB/PRJ 생성 완료

### mapping_store

MappingStore (BF-03).

Mapping(MAP)은 "업로드 파일(ART) → 정규화 스키마"로의 변환 규칙을 정의합니다.

원칙:
- MappingPatch는 새로운 mapping_version을 생성하는 것으로만 표현합니다.
- mapping_digest는 spec payload(=id/version 제외) 기반 결정적 digest입니다.

### pack_store

BrownfieldPackStore (BPK) — append-only pack index (BF-08).

BrownfieldPack(BPK-...-vN)는 Brownfield 내부 데이터(CUB/PRJ 등)의 "참조 묶음"입니다.

원칙:
- Pack은 데이터 복제를 하지 않습니다. bundle/prj의 (id,digest,as_of) 같은 ref만 포함합니다.
- Pack은 append-only 버전입니다. 업데이트는 새 pack_version을 생성합니다.
- RUN의 pinning anchor는 PRJ vN이지만, Pack은 "선택 UX"와 "재사용"을 지원합니다.

MVP 범위(BF-08):
- packs 테이블에 spec_json 저장
- append-only versioning
- as_of_selector 기반으로 bundle 선택(최소 latest_validated/fixed_date/user_select)
- verify_pack: pack이 참조하는 CUB digest 검증
