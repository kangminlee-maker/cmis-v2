# 리팩토링 Side-Effect 분석

**작성일**: 2025-12-09
**목적**: 리팩토링 시 발생 가능한 side-effect 사전 분석

---

## 1. 리팩토링 항목별 Side-Effect

### 1.1 BaseSearchSource 추출 (Google + DuckDuckGo 통합)

#### 변경 내용
```python
# Before
google_search_source.py  (566 라인)
  - class GoogleSearchSource
  - _extract_numbers_from_text()
  - _calculate_consensus()
  ...

duckduckgo_source.py (390 라인)
  - class DuckDuckGoSource
  - _extract_numbers_from_text()  # 중복!
  - _calculate_consensus()        # 중복!
  ...

# After
base_search_source.py (200 라인)
  - class BaseSearchSource
  - _extract_numbers_from_text()  # 공통
  - _calculate_consensus()        # 공통

google_search_source.py (150 라인)
  - class GoogleSearchSource(BaseSearchSource)
  - _search_google()  # 고유

duckduckgo_source.py (100 라인)
  - class DuckDuckGoSource(BaseSearchSource)
  - _search_duckduckgo()  # 고유
```

#### Side-Effects

**테스트 깨짐** (높음):
```python
# 영향받는 테스트
dev/tests/unit/test_google_search_source.py
  - 내부 메서드 테스트 (중복 제거 시 위치 이동)

# 수정 필요
- import 경로 유지 (외부 API 동일)
- 내부 메서드 테스트 → BaseSearchSource로 이동
```

**Import 영향** (중간):
```python
# 영향받는 파일
cmis_core/evidence/sources.py
  - from .google_search_source import GoogleSearchSource

dev/tests/integration/test_real_api_sources.py
  - from cmis_core.evidence.google_search_source import ...

# 해결
- Public API 유지 (클래스명 동일)
- import 경로 동일
- 내부 메서드만 BaseSearchSource로 이동
```

**순환 참조 리스크** (낮음):
```python
# BaseSearchSource가 다른 모듈 import 시
# 순환 참조 가능성

# 해결
- BaseSearchSource는 외부 의존 최소화
- BaseDataSource만 상속
```

**예상 수정 범위**:
- 테스트 파일: 2개 (google, duckduckgo)
- Import: 0개 (Public API 동일)
- 기능: 0개 (동작 동일)

---

### 1.2 kosis_connector.py 정리

#### 변경 내용
```python
# Before
kosis_source.py      (386 라인) - BaseDataSource 구현
kosis_connector.py   (301 라인) - 용도 불명

# After
kosis_source.py      (386 라인) - 유지
(kosis_connector.py 삭제 또는 통합)
```

#### Side-Effects

**파일 사용 확인 필요** (최우선):
```bash
# kosis_connector.py가 실제 사용되는지?
grep -r "kosis_connector" cmis_core/
grep -r "kosis_connector" dev/tests/
```

**가능한 시나리오**:

**A. 사용 안 됨** (90% 예상):
- 영향: 없음
- 조치: 삭제만

**B. 내부적으로 사용** (10%):
- 영향: Import 깨짐
- 조치: kosis_source.py로 통합
- 수정 범위: import만

**예상 수정 범위**:
- 파일: 0-1개 (사용 여부에 따라)
- 테스트: 0개
- 기능: 0개

---

### 1.3 evidence_engine.py 분리

#### 변경 내용
```python
# Before (한 파일)
evidence_engine.py (673 라인)
  - BaseDataSource
  - SourceRegistry
  - EvidencePlanner
  - EvidenceExecutor
  - EvidenceEngine
  - Exceptions

# After (분리)
evidence/
  engine/
    __init__.py        - Public API export
    base_source.py     - BaseDataSource
    registry.py        - SourceRegistry
    planner.py         - EvidencePlanner
    executor.py        - EvidenceExecutor
    engine.py          - EvidenceEngine
    exceptions.py      - Exceptions
```

#### Side-Effects

**Import 경로 변경** (높음):
```python
# 영향받는 파일 (많음!)

# Core
cmis_core/value_engine.py
  - from .evidence_engine import EvidenceEngine, SourceRegistry

cmis_core/workflow.py
  - from .evidence_engine import EvidenceEngine

# Evidence Sources
cmis_core/evidence/sources.py
  - from ..evidence_engine import BaseDataSource, DataNotFoundError

cmis_core/evidence/google_search_source.py
  - from ..evidence_engine import BaseDataSource, ...

# 모든 Source 파일
kosis_source.py, duckduckgo_source.py, ...
  - from ..evidence_engine import BaseDataSource

# 테스트 (10+ 파일)
dev/tests/unit/test_evidence_engine.py
dev/tests/integration/test_*.py
  - from cmis_core.evidence_engine import ...
```

**하위 호환성** (높음):
```python
# Public API 유지 필요
from cmis_core.evidence_engine import EvidenceEngine
# → from cmis_core.evidence.engine import EvidenceEngine

# 해결: __init__.py에서 re-export
# cmis_core/evidence/engine/__init__.py
from .engine import EvidenceEngine
from .registry import SourceRegistry
...

# 상위 레벨에서도
# cmis_core/evidence_engine.py (호환 레이어)
from .evidence.engine import *
```

**테스트 대량 수정** (높음):
```python
# 영향받는 테스트
- test_evidence_engine.py (14 tests)
- test_evidence_store.py (15 tests)
- test_google_search_source.py (14 tests)
- test_value_evidence_integration.py (6 tests)
- test_evidence_cache.py (6 tests)
- test_real_api_sources.py (6 tests)
- test_full_evidence_pipeline.py (4 tests)
- test_dart_multiple_companies.py (6 tests)

# 총 71개 테스트 import 수정 필요
```

**예상 수정 범위**:
- Production 파일: 10+ 개
- 테스트 파일: 8개 (71 tests)
- 수정 라인: ~100 라인 (import만)

---

## 2. 종합 Side-Effect 분석

### 2.1 리스크 매트릭스

| 리팩토링 | 테스트 깨짐 | Import 변경 | 기능 변경 | 리스크 |
|---------|-----------|-----------|----------|--------|
| **BaseSearchSource** | 2개 파일 | 0개 | 없음 | 낮음 |
| **kosis 정리** | 0개 | 0-1개 | 없음 | 낮음 |
| **engine 분리** | 71 tests | 10+ 파일 | 없음 | **높음** |
| **타입 분리** | 많음 | 많음 | 없음 | 높음 |

### 2.2 위험 요소

**1. 순환 참조** (중간):
```python
# 파일 분리 시 발생 가능
engine/planner.py
  from .executor import EvidenceExecutor

engine/executor.py
  from .planner import EvidencePlanner

# 해결: 인터페이스 분리 또는 의존성 제거
```

**2. 테스트 대량 수정** (높음):
```python
# 71개 테스트 import 수정
# 실수 가능성 높음

# 해결: 단계적 수정 + 자동화
# 1. 호환 레이어 추가
# 2. 테스트 실행
# 3. 점진적 마이그레이션
```

**3. 기존 기능 회귀** (중간):
```python
# 리팩토링 중 로직 변경 실수

# 해결: 테스트 주도 리팩토링
# 1. 기존 테스트 모두 통과 확인
# 2. 리팩토링
# 3. 테스트 다시 실행
# 4. 반복
```

---

## 3. 안전한 리팩토링 전략

### 3.1 우선순위 1 (안전)

**BaseSearchSource 추출**:

**Side-Effect**: 낮음
- 테스트: 2개만 영향
- Import: 변경 없음 (Public API 유지)
- 기능: 동일

**전략**:
1. BaseSearchSource 생성
2. Google, DuckDuckGo가 상속
3. 중복 메서드 제거
4. 테스트 실행
5. 통과 확인

**복구 계획**: git revert 즉시 가능

---

**kosis 정리**:

**Side-Effect**: 낮음 (사용 안 되면)
- 테스트: 0개
- Import: 0개
- 기능: 없음

**전략**:
1. 사용 여부 확인 (grep)
2. 사용 안 되면 삭제
3. 사용되면 통합
4. 테스트 실행

**복구 계획**: git restore 즉시

---

### 3.2 우선순위 3 (위험)

**evidence_engine.py 분리**:

**Side-Effect**: **높음**
- 테스트: 71개 영향
- Import: 10+ 파일
- 순환 참조 가능성

**전략** (신중):
1. 호환 레이어 먼저 추가
2. 테스트 통과 확인
3. 파일 분리
4. 테스트 다시 실행
5. Import 점진적 마이그레이션

**복구 계획**: 복잡 (여러 파일)

**권장**: v3로 연기 (안정화 후)

---

### 3.3 타입 분리

**Side-Effect**: **높음**
- 거의 모든 파일 영향
- 수백 개 import 수정

**권장**: v3+ (필수 아님)

---

## 4. 단계별 리팩토링 계획

### Phase 1 (즉시, 안전)

**대상**:
- BaseSearchSource 추출
- kosis_connector.py 정리

**Side-Effect**: 낮음
**테스트 영향**: 2개
**소요**: 2-3시간
**복구**: 쉬움

---

### Phase 2 (v2.5, 중위험)

**대상**:
- evidence_engine.py 분리
- HTML 파싱 공통화

**Side-Effect**: 중간
**테스트 영향**: 71개
**소요**: 3-4시간
**복구**: 중간

**조건**: Phase 1 완료 + 안정화

---

### Phase 3 (v3, 고위험)

**대상**:
- 타입 분리
- Source 계층화
- 공통 유틸리티

**Side-Effect**: 높음
**테스트 영향**: 전체
**소요**: 1주
**복구**: 어려움

**조건**: Phase 2 완료 + 충분한 시간

---

## 5. 위험 완화 전략

### 5.1 호환 레이어

```python
# cmis_core/evidence_engine.py (호환)
"""
Compatibility layer for backward compatibility
"""

# Re-export from new location
from .evidence.engine import (
    EvidenceEngine,
    SourceRegistry,
    BaseDataSource,
    # ...
)

__all__ = [
    "EvidenceEngine",
    "SourceRegistry",
    ...
]
```

**효과**: 기존 import 그대로 작동

---

### 5.2 점진적 마이그레이션

```python
# Step 1: 호환 레이어 추가
# Step 2: 새 import로 하나씩 변경
# Step 3: 호환 레이어에 deprecation 경고
# Step 4: 호환 레이어 제거 (v3)
```

**효과**: 리스크 분산, 안전

---

### 5.3 테스트 주도

```python
# 각 단계마다
1. 현재 테스트 모두 통과 확인
2. 리팩토링
3. 테스트 실행
4. 실패 시 즉시 복구
5. 통과 시 다음 단계
```

**효과**: 회귀 방지

---

## 6. 구체적 Side-Effect 예시

### 6.1 BaseSearchSource 추출

**영향받는 코드**:
```python
# test_google_search_source.py
def test_extract_numbers_korean():
    source = GoogleSearchSource()
    numbers = source._extract_numbers_from_text(text)
    # → BaseSearchSource._extract_numbers_from_text()로 이동

# 수정 후
def test_extract_numbers_korean():
    from cmis_core.evidence.base_search_source import BaseSearchSource
    source = BaseSearchSource()  # 또는 GoogleSearchSource 유지
    numbers = source._extract_numbers_from_text(text)
```

**영향**: 2개 테스트 파일만

---

### 6.2 evidence_engine.py 분리

**영향받는 코드** (많음):
```python
# value_engine.py
from .evidence_engine import EvidenceEngine, SourceRegistry
# → from .evidence.engine import EvidenceEngine
# → from .evidence.registry import SourceRegistry

# workflow.py
from .evidence_engine import EvidenceEngine
# → from .evidence.engine import EvidenceEngine

# 모든 Source 파일 (8개)
from ..evidence_engine import BaseDataSource
# → from ..evidence.base_source import BaseDataSource

# 모든 테스트 (71개)
from cmis_core.evidence_engine import ...
# → from cmis_core.evidence.engine import ...
```

**영향**: 15+ 파일, 100+ 라인

---

### 6.3 순환 참조 예시

```python
# planner.py
from .executor import EvidenceExecutor  # ❌

class EvidencePlanner:
    def build_plan(...) -> EvidencePlan:
        # EvidenceExecutor 참조
        ...

# executor.py
from .planner import EvidencePlanner  # ❌

class EvidenceExecutor:
    def run(plan: EvidencePlan):
        # EvidencePlanner 참조
        ...

# 결과: ImportError (circular import)
```

**해결**:
```python
# 1. TYPE_CHECKING 사용
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .executor import EvidenceExecutor

# 2. 의존성 제거 (더 좋음)
# Planner와 Executor는 서로 의존 안 하게 설계
```

---

## 7. 최종 권장사항

### 즉시 리팩토링 (안전)

**대상**:
- ✅ BaseSearchSource 추출
- ✅ kosis_connector.py 정리

**Side-Effect**: 낮음
**테스트 영향**: 2개
**복구**: 쉬움

**권장**: ✅ 즉시 진행

---

### 연기 (위험)

**대상**:
- ⏭️ evidence_engine.py 분리
- ⏭️ 타입 분리
- ⏭️ Source 계층화

**Side-Effect**: 높음
**테스트 영향**: 71+
**복구**: 어려움

**권장**: v2.5+ (안정화 후)

---

## 8. 리팩토링 체크리스트

### 시작 전

- [ ] Git 상태 clean 확인
- [ ] 현재 테스트 100% 통과 확인
- [ ] 백업 브랜치 생성

### 리팩토링 중

- [ ] 한 번에 하나씩
- [ ] 각 단계마다 테스트
- [ ] Import 경로 확인
- [ ] 호환 레이어 유지

### 완료 후

- [ ] 전체 테스트 통과
- [ ] Linter 확인
- [ ] Import 정리
- [ ] 문서 업데이트

---

## 9. 결론

### 안전한 리팩토링

**즉시 가능**:
- BaseSearchSource (낮은 리스크)
- kosis 정리 (낮은 리스크)

**예상 효과**:
- ~600 라인 절감
- 중복 제거
- Side-effect 최소

---

### 위험한 리팩토링

**연기 권장**:
- evidence_engine 분리 (높은 리스크)
- 타입 분리 (높은 리스크)

**이유**:
- 71+ 테스트 영향
- 10+ 파일 수정
- 순환 참조 리스크

---

**최종 권장**:

1. ✅ **즉시**: BaseSearchSource + kosis 정리 (안전)
2. ⏭️ **v2.5**: evidence_engine 분리 (신중)
3. ⏭️ **v3**: 전체 구조 개선 (안정화 후)

**현재 우선순위**: 커밋 > 안전한 리팩토링 > 위험한 리팩토링

---

**작성**: 2025-12-09
**결론**: 즉시 리팩토링은 안전, 대규모는 연기


