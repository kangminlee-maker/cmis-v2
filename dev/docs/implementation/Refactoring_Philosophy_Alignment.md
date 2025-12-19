# 리팩토링 vs CMIS 철학 정합성 검증

**작성일**: 2025-12-09
**목적**: 리팩토링이 CMIS 철학/아키텍처와 충돌하는지 검증

---

## 1. CMIS 핵심 철학 (재확인)

### cmis.yaml 철학

```yaml
philosophy:
  core_principles:
    - "Model-first, Number-second"
    - "Evidence-first, Prior-last"
    - "Graph-of-Graphs: R/P/V/D"
    - "Trait 기반 패턴/모델 정의로 Ontology lock-in 최소화"
    - "모든 답 = (세계, 변화, 결과, 논증 구조)"
    - "Monotonic Improvability & Re-runnability"
    - "Agent = Persona + Workflow (엔진이 아님)"
```

### 아키텍처 원칙

**4-Plane 구조**:
```
1. Interaction Plane - 인터페이스
2. Role Plane        - Agent/Persona
3. Substrate Plane   - Graphs + Stores
4. Cognition Plane   - Engines
```

**Engine 독립성**:
- 각 Engine은 독립적
- Graph를 통해 소통
- 확장 가능 설계

---

## 2. 리팩토링 vs 철학 검증

### 2.1 BaseSearchSource 추출

**리팩토링 내용**:
```python
# Google + DuckDuckGo 공통 로직 추출
BaseSearchSource
  ├─ GoogleSearchSource
  └─ DuckDuckGoSource
```

**CMIS 철학 확인**:

✅ **Model-first**:
- Source 추상화 강화 (모델 우선)
- 구현 세부사항 숨김
- ✅ 철학 부합

✅ **Trait 기반, Ontology lock-in 최소화**:
- Source를 Trait로 정의 (provides, regions)
- 특정 구현에 종속 안 됨
- ✅ 철학 부합

✅ **확장성**:
- 새 SearchSource 추가 쉬움
- BaseSearchSource 상속만
- ✅ 아키텍처 부합

**결론**: ✅ **충돌 없음, 오히려 철학 강화**

---

### 2.2 evidence_engine.py 분리

**리팩토링 내용**:
```python
# 한 파일 → 여러 파일
evidence_engine.py (673)
  → engine.py
  → planner.py
  → executor.py
  → registry.py
```

**CMIS 철학 확인**:

✅ **책임 분리**:
- Planner: 계획
- Executor: 실행
- Registry: 관리
- ✅ 단일 책임 원칙

⚠️ **Engine 독립성**:
```yaml
# cmis.yaml cognition_plane
engines:
  evidence_engine:
    api:
      - fetch_for_metrics
      - fetch_for_reality_slice
```

**우려**:
- evidence_engine이 하나의 Engine으로 정의됨
- 내부를 너무 쪼개면 "Engine" 개념 흐려짐
- EvidenceEngine이 Facade 역할을 해야 함

**해결**:
```python
# EvidenceEngine을 Facade로 유지
# 내부 구현만 분리 (외부에는 하나의 Engine)

from cmis_core.evidence_engine import EvidenceEngine
# → 여전히 작동 (호환 레이어)

# 내부적으로만 분리
from cmis_core.evidence.engine.planner import ...  # 내부용
```

**결론**: ⚠️ **주의 필요, Facade 패턴 유지 필수**

---

### 2.3 타입 분리

**리팩토링 내용**:
```python
types.py (487)
  → types.py (Core)
  → evidence/types.py (Evidence)
  → llm/types.py (LLM, 이미 분리)
```

**CMIS 철학 확인**:

✅ **Ontology (공통 타입)**:
```yaml
ontology:
  primitives:
    actor:
    event:
    resource:
    ...
```

**우려**:
- Ontology는 "공통 최소 단위"
- 여러 파일로 분산 시 "단일 진실의 원천" 약화
- Graph 간 타입 공유 어려워짐

**CMIS 설계**:
```yaml
# cmis.yaml은 모든 타입을 한 곳에 정의
ontology:
  primitives:  # 한 곳
  quantity_types:  # 한 곳
```

**결론**: ❌ **철학 충돌 가능!**

**이유**:
- CMIS는 "Graph-of-Graphs"
- 모든 Graph가 공통 Ontology 공유
- 타입 분산 시 공유 어려움

**올바른 접근**:
```python
# types.py 유지 (공통 Ontology)
# Engine별 타입은 해당 Engine 내부에만
```

---

## 3. 철학과 충돌하는 리팩토링

### ❌ 충돌 (피해야 함)

**1. 타입 분리**
```
이유: Ontology "공통 최소 단위" 원칙 위배
대안: types.py 유지, 섹션 구분만
```

**2. Engine 과도한 분리**
```
이유: "Engine" 개념 흐려짐
대안: Facade 패턴 유지, 내부만 분리
```

**3. Source를 Engine으로 승격**
```
이유: Source ≠ Engine (CMIS 정의)
대안: DataSource로 유지
```

---

### ✅ 철학 부합 (권장)

**1. BaseSearchSource**
```
이유: Trait 기반 추상화 강화
효과: Ontology lock-in 최소화
```

**2. 중복 제거**
```
이유: DRY, 유지보수
효과: 단순성 (CMIS 선호)
```

**3. 호환 레이어**
```
이유: Re-runnability, 하위 호환
효과: Monotonic Improvability
```

---

## 4. CMIS 아키텍처 vs 리팩토링

### 4.1 Cognition Plane 구조

**CMIS 정의**:
```yaml
cognition_plane:
  engines:
    evidence_engine:      # 하나의 Engine
    world_engine:         # 하나의 Engine
    pattern_engine:       # 하나의 Engine
    value_engine:         # 하나의 Engine
```

**리팩토링 영향**:

✅ **BaseSearchSource**:
- Engine 구조 불변
- Source 내부 개선만
- ✅ 충돌 없음

⚠️ **evidence_engine 분리**:
- Engine을 여러 모듈로 분리
- 외부에서는 하나로 보여야 함
- ⚠️ Facade 패턴 필수

❌ **Engine 계층화**:
```python
# ❌ 이렇게 하면 안 됨
engines/
  evidence/
    planner_engine.py
    executor_engine.py

# ✅ 이렇게
evidence_engine/
  planner.py  # 내부 컴포넌트
  executor.py
```

---

### 4.2 Substrate Plane (Stores)

**CMIS 정의**:
```yaml
substrate_plane:
  stores:
    evidence_store:
    value_store:
    memory_store:
```

**리팩토링 영향**:

✅ **파일 분리**:
- Store 개념 유지
- 구현만 정리
- ✅ 충돌 없음

---

## 5. 충돌 매트릭스

| 리팩토링 | CMIS 원칙 | 충돌 여부 | 해결 방법 |
|---------|----------|----------|----------|
| BaseSearchSource | Trait 기반 | ✅ 부합 | - |
| kosis 정리 | DRY | ✅ 부합 | - |
| engine 분리 | Engine 독립성 | ⚠️ 주의 | Facade 유지 |
| 타입 분리 | Ontology 공통 | ❌ 충돌 | **하지 말 것** |
| Source 계층화 | 확장성 | ✅ 부합 | - |

---

## 6. 올바른 리팩토링 원칙

### CMIS 철학 기반

**1. Ontology 통합 유지**:
```python
# ✅ 올바름
types.py  # 모든 공통 타입

# ❌ 잘못됨
types/
  evidence.py
  pattern.py
  value.py
```

**2. Engine Facade 유지**:
```python
# ✅ 올바름
from cmis_core.evidence_engine import EvidenceEngine
# → 하나의 Engine으로 보임

# ❌ 잘못됨
from cmis_core.evidence.planner_engine import ...
from cmis_core.evidence.executor_engine import ...
# → Engine이 분산됨
```

**3. Trait 기반 확장**:
```python
# ✅ 올바름
BaseSearchSource (Trait: provides, regions)
  ├─ GoogleSearchSource
  └─ DuckDuckGoSource

# ❌ 잘못됨
GoogleSearchSource (하드코딩)
DuckDuckGoSource (하드코딩)
```

---

## 7. 수정된 리팩토링 계획

### 우선순위 1 (안전 + 철학 부합) ✅

**BaseSearchSource**:
- ✅ Trait 기반 추상화
- ✅ Ontology lock-in 최소화
- ✅ 확장성 향상
- ✅ 즉시 진행 가능

**kosis 정리**:
- ✅ DRY
- ✅ 단순성
- ✅ 즉시 진행 가능

---

### 우선순위 2 (주의 + Facade 필수) ⚠️

**evidence_engine 분리**:
- ⚠️ Facade 패턴 필수
- ⚠️ 외부 API 불변
- ⚠️ 호환 레이어 필수
- 📝 v2.5로 연기 (신중)

---

### 우선순위 3 (철학 충돌) ❌

**타입 분리**:
- ❌ Ontology 공통 원칙 위배
- ❌ Graph 간 타입 공유 어려움
- ❌ **하지 말 것**

**대안**: types.py 내부 섹션 구분만
```python
# types.py
# ========================================
# Ontology Primitives (Core)
# ========================================

# ========================================
# Evidence Types
# ========================================

# ========================================
# Pattern Types
# ========================================
```

---

## 8. 최종 검증 결과

### ✅ 철학 부합 리팩토링

**즉시 진행 가능**:
1. BaseSearchSource 추출
   - Trait 기반 ✅
   - 확장성 ✅
   - Ontology lock-in 최소화 ✅

2. kosis 중복 정리
   - DRY ✅
   - 단순성 ✅

**효과**: ~600 라인 절감
**충돌**: 없음
**리스크**: 낮음

---

### ⚠️ 주의 필요 리팩토링

**v2.5 신중 진행**:
3. evidence_engine 분리
   - Facade 패턴 유지 필수
   - Engine 독립성 유지
   - 외부 API 불변

**조건**:
- 호환 레이어
- Engine 개념 유지
- 테스트 주도

---

### ❌ 철학 충돌 리팩토링

**하지 말 것**:
4. 타입 분리 (evidence/types.py, pattern/types.py)
   - Ontology 공통 원칙 위배
   - Graph-of-Graphs 약화

**대안**:
- types.py 섹션 구분
- 주석으로 명확화
- 한 파일 유지

---

## 9. 최종 권장사항

### 즉시 리팩토링 (철학 부합) ✅

**대상**:
- BaseSearchSource
- kosis 정리

**근거**:
- ✅ Trait 기반 (CMIS 철학)
- ✅ 확장성 (아키텍처 원칙)
- ✅ DRY (모범 사례)
- ✅ 충돌 없음

**진행**: 권장

---

### 연기/수정 필요

**evidence_engine 분리**:
- ⚠️ Facade 패턴으로만
- Engine 개념 유지
- v2.5로 연기

**타입 분리**:
- ❌ 철학 충돌
- **하지 말 것**
- types.py 섹션만

---

## 10. 결론

### 철학 정합성 검증

| 리팩토링 | 철학 | 아키텍처 | 검증 결과 |
|---------|------|----------|----------|
| BaseSearchSource | ✅ Trait | ✅ 확장성 | ✅ 진행 |
| kosis 정리 | ✅ DRY | ✅ 단순성 | ✅ 진행 |
| engine 분리 | ⚠️ Engine 개념 | ⚠️ Facade | ⚠️ 신중 |
| 타입 분리 | ❌ Ontology | ❌ Graph 공유 | ❌ 금지 |

---

### 최종 결론

**즉시 리팩토링**: ✅ 안전 + 철학 부합
- BaseSearchSource
- kosis 정리

**연기**: evidence_engine (Facade 패턴으로만)
**금지**: 타입 분리 (철학 충돌)

---

**검증 완료**: 즉시 리팩토링은 CMIS 철학과 충돌 없음

**권장**: 커밋 후 즉시 리팩토링 진행

---

**작성**: 2025-12-09
**검증**: 철학 정합성 OK
**승인**: ✅ 리팩토링 진행 가능
