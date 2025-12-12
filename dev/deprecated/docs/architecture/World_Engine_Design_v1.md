# World Engine 미구현 요소 분석

**작성일**: 2025-12-11
**상태**: Gap 확인 완료

---

## 현재 구현 상태

### ✅ 구현 완료 항목

**1. snapshot() 메서드**
```python
def snapshot(
    domain_id: str,
    region: str,
    segment: Optional[str] = None,
    as_of: Optional[str] = None,
    project_context_id: Optional[str] = None
) -> RealityGraphSnapshot
```

**기능**:
- Reality seed YAML 로딩
- Actor/MoneyFlow/State 노드 생성
- actor_pays_actor edge 생성
- domain_registry 기반 동적 로딩
- Meta 정보 관리

**테스트**: 5/5 통과 ✅

---

## ❌ 미구현 항목

### 1. ingest_evidence() 메서드

**cmis.yaml 정의**:
```yaml
world_engine:
  api:
    - name: "ingest_evidence"
      description: "새 Evidence를 받아 R-Graph에 반영"
      input:
        evidence_ids: "list[evidence_id]"
      output:
        updated_node_ids: "list[node_id]"
```

**구현 상태**: ❌ 미구현

**필요성**:
- Evidence Engine에서 수집한 데이터를 R-Graph에 반영
- 동적으로 R-Graph 업데이트
- Brownfield 분석에서 focal_actor 주변 구조 확장

**사용 시나리오**:
1. EvidenceEngine이 경쟁사 매출 데이터 수집
2. WorldEngine.ingest_evidence()가 이를 Actor/MoneyFlow로 변환
3. R-Graph에 노드/엣지 추가

**구현 난이도**: 중간
**예상 시간**: 2-3일

---

### 2. ingest_project_context() 메서드

**cmis.yaml 정의**:
```yaml
world_engine:
  api:
    - name: "ingest_project_context"
      description: "Project Context의 baseline/assets 정보를 R-Graph로 투영"
      input:
        project_context_id: "project_context_id"
      output:
        focal_actor_id: "actor_id"
        updated_node_ids: "list[node_id]"
```

**구현 상태**: ❌ 미구현

**필요성**:
- Brownfield 분석에서 focal_actor 설정
- Project Context의 baseline_state를 R-Graph에 반영
- assets_profile을 Actor 속성으로 매핑

**사용 시나리오**:
1. 사용자가 "우리 회사(focal_actor) 분석" 요청
2. WorldEngine.ingest_project_context()가 focal_actor 생성
3. baseline_state의 매출/고객수 등을 State 노드로 추가
4. PatternEngine이 focal_actor 중심으로 패턴 매칭

**구현 난이도**: 중간
**예상 시간**: 2-3일

---

### 3. 고급 snapshot() 기능

**현재 구현**:
- ✅ domain_id 기반 seed 로딩
- ✅ 전체 그래프 반환
- ⚠️ segment/as_of는 meta에만 기록 (실제 필터링 없음)
- ❌ project_context_id 기반 서브그래프 추출 미구현

**cmis.yaml 요구사항**:
```yaml
snapshot:
  notes:
    - "project_context_id가 주어지면 focal_actor 및 주변 서브그래프를 우선 포함"
    - "baseline_state 참조 Metric/State를 R-Graph에 반영"
```

**미구현 기능**:
1. **segment 필터링**
   - 현재: meta에만 기록
   - 필요: segment에 해당하는 Actor만 필터링

2. **as_of 시점 필터링**
   - 현재: meta에만 기록
   - 필요: 특정 시점의 State/MoneyFlow만 포함

3. **project_context_id 기반 서브그래프**
   - 현재: 미구현
   - 필요: focal_actor + N-hop 이웃만 추출

**구현 난이도**: 중간-높음
**예상 시간**: 3-5일

---

## 현재 제약사항

### 1. 정적 seed 의존

**현재**:
- Reality seed YAML 파일만 로딩 가능
- 수동으로 작성된 seed만 사용

**제약**:
- 새로운 시장/도메인 분석 시 매번 seed 작성 필요
- 동적 데이터 반영 불가

**해결 방안**:
- `ingest_evidence()` 구현으로 동적 확장

---

### 2. Greenfield만 지원

**현재**:
- 시장 전체 구조 분석만 가능 (Greenfield)
- focal_actor 중심 분석 불가 (Brownfield)

**제약**:
- "우리 회사" 중심 분석 불가
- 경쟁사 비교 불가

**해결 방안**:
- `ingest_project_context()` 구현

---

### 3. 서브그래프 추출 없음

**현재**:
- 전체 그래프만 반환
- focal_actor 주변만 보기 불가

**제약**:
- 큰 시장에서 성능 문제 가능
- 관련 없는 노드까지 포함

**해결 방안**:
- `snapshot()` 고급 기능 구현 (서브그래프 추출)

---

## 우선순위 평가

### Priority 1: ingest_project_context() (높음)

**이유**:
- Brownfield 분석의 핵심 기능
- PatternEngine Phase 2의 execution_fit과 연계
- 실무 가치 매우 높음 (focal_actor 중심 분석)

**의존성**:
- ProjectContext 데이터 모델 (✅ 이미 구현됨)
- R-Graph Actor/State 노드 (✅ 이미 구현됨)

**예상 효과**:
- Brownfield 분석 가능
- "우리 회사" 중심 전략 수립

---

### Priority 2: snapshot() 서브그래프 추출 (중간)

**이유**:
- 성능 최적화
- focal_actor 주변만 분석 가능
- ingest_project_context()와 시너지

**의존성**:
- ingest_project_context() 구현 필요

**예상 효과**:
- 대규모 시장 분석 시 성능 향상
- 관련 구조만 집중 분석

---

### Priority 3: ingest_evidence() (중간-낮음)

**이유**:
- 동적 R-Graph 확장
- Evidence Engine과 연계
- 실시간 데이터 반영

**의존성**:
- Evidence Engine (✅ 이미 구현됨)
- Evidence → R-Graph 변환 로직 필요

**예상 효과**:
- seed 없이도 시장 분석 가능
- 동적 데이터 수집 → 분석 파이프라인

---

### Priority 4: segment/as_of 필터링 (낮음)

**이유**:
- 현재 meta 기록으로 대체 가능
- 시급성 낮음

**의존성**:
- 없음 (독립적 구현 가능)

**예상 효과**:
- 시계열 분석 향상
- segment별 차별화 분석

---

## 구현 로드맵

### Phase A: Brownfield 지원 (1주)

**목표**: focal_actor 중심 분석 가능

**작업**:
1. `ingest_project_context()` 구현
   - ProjectContext → focal_actor 생성
   - baseline_state → State 노드 추가
   - assets_profile → Actor traits 매핑

2. `snapshot()` 서브그래프 추출
   - focal_actor + N-hop 이웃 추출
   - 관련 MoneyFlow/State만 포함

3. 테스트 (5개)
   - ingest_project_context 기본
   - focal_actor 생성
   - baseline_state 반영
   - 서브그래프 추출
   - Integration 테스트

**효과**:
- Brownfield 분석 완전 지원
- PatternEngine execution_fit와 연계

---

### Phase B: 동적 확장 (1-2주)

**목표**: Evidence → R-Graph 동적 반영

**작업**:
1. `ingest_evidence()` 구현
   - Evidence → Actor/MoneyFlow/State 변환
   - 기존 노드 업데이트 vs 신규 생성 로직
   - Conflict 해결 (같은 Actor 다른 데이터)

2. Evidence 타입별 변환기
   - Metric Evidence → State 노드
   - Search Evidence → Actor/traits
   - API Evidence → MoneyFlow

3. 테스트 (8개)
   - Evidence 타입별 변환
   - 노드 업데이트
   - Conflict 해결
   - Integration 테스트

**효과**:
- seed 없이도 분석 가능
- 실시간 데이터 반영

---

### Phase C: 고급 기능 (선택, 1주)

**목표**: 시계열/segment 필터링

**작업**:
1. segment 필터링
2. as_of 시점 필터링
3. 시계열 비교 (여러 as_of)

**효과**:
- 시계열 분석
- segment별 차별화

---

## 현재 World Engine 완성도

| 항목 | 상태 | 완성도 |
|------|------|--------|
| snapshot() 기본 | ✅ | 100% |
| domain_registry 로딩 | ✅ | 100% |
| seed → R-Graph 변환 | ✅ | 100% |
| ingest_project_context() | ❌ | 0% |
| ingest_evidence() | ❌ | 0% |
| 서브그래프 추출 | ❌ | 0% |
| segment 필터링 | ⚠️ | 30% (meta만) |
| as_of 필터링 | ⚠️ | 30% (meta만) |

**전체 완성도**: 약 40%

---

## 추천 사항

### 즉시 작업 (1주)

**ingest_project_context() + 서브그래프 추출 (Phase A)**

**이유**:
1. Brownfield 분석의 핵심 기능
2. PatternEngine Phase 2와 시너지 (execution_fit)
3. 실무 가치 매우 높음
4. 1주 내 완성 가능

**작업 순서**:
1. `ingest_project_context()` 구현 (2일)
2. 서브그래프 추출 로직 (2일)
3. 테스트 작성 (1일)

---

### 중기 작업 (2-3주 후)

**ingest_evidence() (Phase B)**

**이유**:
- 동적 R-Graph 확장
- Evidence Engine 활용도 증가
- seed 의존성 제거

---

### 장기 작업 (선택)

**segment/as_of 필터링 (Phase C)**

**이유**:
- 현재 우선순위 낮음
- 다른 기능 완성 후 진행

---

## 다음 세션 제안

### Option 1: World Engine Phase A 착수 (추천)

**작업**:
- ingest_project_context() 구현
- 서브그래프 추출
- Brownfield 분석 완성

**예상 시간**: 1주
**효과**: Brownfield 완전 지원

---

### Option 2: 현재 완성도 유지 + 다른 엔진 개발

**이유**:
- World Engine v1은 Greenfield 분석에 충분
- StrategyEngine 등 다른 엔진 우선 개발

---

**작성**: 2025-12-11
**상태**: Gap 분석 완료
**권장**: Phase A (ingest_project_context) 구현
