# World Engine 설계 고도화 완료

**작업일**: 2025-12-11
**상태**: ✅ 완료

---

## 작업 요약

### 피드백 반영 및 고도화

**목표**: cmis.yaml 스펙과 정합성 확보, 구조적 문제 해결

**결과**:
- v1.0 → v2.0 고도화 완료
- cmis.yaml과 100% 정합성 확보
- 구조적 모순 해결

---

## 주요 변경 사항

### 1. snapshot 인터페이스 정리 (임팩트: 상)

**v1.0**:
```python
def snapshot(
    domain_id: str,
    region: str,
    segment: Optional[str] = None,
    ...
)
```

**v2.0**:
```python
def snapshot(
    as_of: str,
    scope: Dict[str, Any],  # { domain_id, region, segment, ... }
    project_context_id: Optional[str] = None
)
```

**이유**:
- cmis.yaml 스펙 준수
- canonical_workflows 호환
- 향후 확장성 (sector, sub_region 등)

---

### 2. segment/as_of 필터링 우선순위 상향 (임팩트: 상)

**v1.0**: Priority 4 (낮음)
**v2.0**: Priority 1 (Phase A 포함)

**cmis.yaml 근거**:
- `reality_graph.time_slicing.snapshot_key: ["as_of"]`
- canonical_workflows에서 항상 segment 사용
- 시간 슬라이싱 핵심 기능

---

### 3. project_context 역할 명확화 (임팩트: 상)

**v1.0 모순**:
- GAP 문서: "WorldEngine이 focal_actor 생성"
- cmis.yaml: focal_actor_id required

**v2.0 해결**:
- ProjectContext는 focal_actor_id를 이미 알고 있음
- WorldEngine은 focal_actor 반영/업데이트 역할
- 스키마 변경 최소화

---

### 4. ingest_evidence 구체화 (임팩트: 중)

**v1.0**: 러프한 아이디어만

**v2.0**: EvidenceToWorldMapper 레이어 설계
- DartFilingsMapper
- MarketResearchMapper
- KOSISStatisticsMapper
- ...

**장점**:
- data_sources.mapping.to_evidence_schema 연결
- 확장 용이
- if/else 덩어리 방지

---

### 5. seed → R-Graph 변환 범위 명시 (임팩트: 중)

**v1.0**: 현재 구현만 기술

**v2.0**: 확장 계획 포함
- Phase B: actor_competes_with_actor (경쟁 구조)
- Phase B: actor_offers_resource (가치사슬)
- Phase C: contract, event 노드

**PatternEngine 요구사항 충족**

---

### 6. Lineage 및 버전 관리 추가 (임팩트: 중)

**v2.0 신규**:
- NodeLineage 설계
- WorldUpdate/RealityBuildPlan 개념
- 모든 노드의 출처 추적
- Monotonic Improvability 지원

---

### 7. cmis.yaml 근거 추가 (임팩트: 중)

**v1.0**: 근거 미약

**v2.0**: 모든 우선순위에 cmis.yaml 기준 명시
- canonical_workflows 연결
- reality_graph 스펙 인용
- project_context_store 스키마 참조

---

## 문서 위치

### 신규 문서 (v2.0)
**위치**: `dev/docs/architecture/World_Engine_Design_v2.md`

**내용**:
- cmis.yaml 정합성 확보
- API 설계 (scope dict 기반)
- 타입별 매퍼 설계
- Lineage 관리
- 구현 로드맵

### 아카이브 (v1.0)
**위치**: `dev/docs/architecture/World_Engine_Design_v1.md`

**내용**:
- 초기 Gap 분석
- 기본 우선순위 평가

---

## 구현 로드맵

### Phase A: Brownfield 핵심 (1주)

**작업**:
1. snapshot 인터페이스 정리 (scope dict)
2. segment/as_of 필터링 구현
3. ingest_project_context 구현
4. 서브그래프 추출

**테스트**: 15개

**cmis.yaml 근거**:
- canonical_workflows 직접 지원
- pattern_engine.execution_fit 연동

---

### Phase B: 동적 확장 (1-2주)

**작업**:
1. EvidenceToWorldMapper 인프라
2. 타입별 매퍼 구현
3. ingest_evidence 구현
4. 경쟁 구조 edge 확장

**테스트**: 15개

---

### Phase C: 고급 기능 (1주)

**작업**:
1. 고급 시계열
2. 가치사슬 edge
3. Lineage 완성
4. 성능 최적화

**테스트**: 8개

---

## 피드백 반영 체크리스트

### ✅ 구조적 보강

- [x] snapshot 시그니처 (scope dict)
- [x] project_context 역할 명확화
- [x] segment/as_of 우선순위 재평가
- [x] ingest_evidence 타입별 변환 설계
- [x] seed → R-Graph 변환 범위 명시
- [x] cmis.yaml 근거 추가

### ✅ 신규 설계

- [x] EvidenceToWorldMapper 레이어
- [x] Lineage/버전 관리
- [x] EvidenceEngine 호출 관계
- [x] 성능 고려사항
- [x] 테스트 전략

### ✅ cmis.yaml 정합성

- [x] world_engine.api 스펙 준수
- [x] canonical_workflows 호환
- [x] project_context_store 스키마 정합
- [x] reality_graph edge_types 확장 계획

---

## 다음 단계

### 즉시 착수 가능

**World Engine Phase A** (1주)

**작업**:
1. snapshot 인터페이스 정리
2. segment/as_of 필터링
3. ingest_project_context
4. 서브그래프 추출

**완료 후**:
- Brownfield 분석 완전 지원
- PatternEngine Phase 2와 시너지
- canonical_workflows 실행 가능

---

## 관련 문서

**설계 문서**:
- `dev/docs/architecture/World_Engine_Design_v2.md` (최신)
- `dev/docs/architecture/World_Engine_Design_v1.md` (아카이브)

**참조**:
- `cmis.yaml` - 전체 스펙
- `dev/docs/architecture/cmis_philosophy_concept.md`
- `dev/docs/architecture/cmis_project_context_layer_design.md`

---

**작성**: 2025-12-11
**상태**: 설계 고도화 완료 ✅
**다음**: Phase A 구현 착수
