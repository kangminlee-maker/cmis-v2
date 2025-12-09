# 코드 리뷰 및 리팩토링 계획

**작성일**: 2025-12-09
**대상**: 이번 세션 작성 코드 (~9,500 라인)

---

## 1. 코드 현황 분석

### 주요 파일 (라인 수)

```
Evidence Engine:
  evidence_engine.py              673 라인
  evidence_store.py               524 라인
  
Evidence Sources:
  google_search_source.py         566 라인
  duckduckgo_source.py            390 라인
  kosis_source.py                 386 라인
  kosis_connector.py              301 라인  ← 중복?
  dart_connector.py               497 라인
  sga_extractor.py                315 라인
  account_matcher.py              191 라인
  sources.py                      255 라인

LLM Infrastructure:
  llm/service.py                  626 라인
  llm/providers.py                274 라인
  llm/types.py                    173 라인
  llm/interface.py                120 라인

Core:
  types.py                        487 라인 (+337 추가)
  value_engine.py                 526 라인 (+136 추가)
  config.py                       182 라인 (+11 추가)
```

**총**: ~7,756 라인 (cmis_core만)

---

## 2. 중복 코드 발견

### 2.1 GoogleSearchSource vs DuckDuckGoSource

**중복 메서드** (80% 동일):
```python
# 둘 다 동일
_build_search_query()
_extract_numbers()
_extract_numbers_from_text()
_calculate_consensus()
_remove_outliers()
_calculate_confidence()
_fetch_page_content()
```

**차이점**:
- 검색 API 호출부만 다름 (Google vs DuckDuckGo)
- Confidence 계산 약간 다름

**리팩토링**: BaseSearchSource 추출
```python
class BaseSearchSource(BaseDataSource):
    """웹 검색 공통 로직"""
    
    def _extract_numbers_from_text(text): ...
    def _calculate_consensus(numbers): ...
    def _remove_outliers(numbers): ...
    # ...

class GoogleSearchSource(BaseSearchSource):
    def _search(self, query):
        # Google API 호출만
    
class DuckDuckGoSource(BaseSearchSource):
    def _search(self, query):
        # DuckDuckGo API 호출만
```

**절감**: ~300 라인

---

### 2.2 kosis_source.py vs kosis_connector.py

**문제**: 2개 파일 존재
```
kosis_source.py      (386 라인) - BaseDataSource 구현
kosis_connector.py   (301 라인) - ??? 용도 불명
```

**확인 필요**: kosis_connector.py가 실제 사용되는지

**리팩토링**: 하나로 통합 또는 삭제

**절감**: ~300 라인

---

### 2.3 Evidence 타입 vs types.py 중복

**types.py**:
```python
# Evidence 관련 타입이 많음 (350 라인 추가)
EvidenceRequest
EvidenceRecord
EvidenceBundle
EvidenceMultiResult
EvidenceSufficiency
...
```

**별도 파일 제안**:
```
types.py               - Core 타입만
evidence/types.py      - Evidence 전용
llm/types.py          - LLM 전용 (이미 분리됨)
```

**효과**: 가독성 향상, 파일 크기 적정화

---

## 3. 불필요한 복잡성

### 3.1 evidence_engine.py (673 라인)

**구조**:
```python
# 한 파일에 모두
class BaseDataSource: ...
class SourceRegistry: ...
class EvidencePlan: ...
class EvidencePlanner: ...
class EvidenceExecutor: ...
class EvidenceEngine: ...
```

**문제**: 단일 파일이 너무 큼

**리팩토링**:
```
evidence/
  engine.py          - EvidenceEngine (Facade)
  planner.py         - EvidencePlanner
  executor.py        - EvidenceExecutor
  registry.py        - SourceRegistry
  base_source.py     - BaseDataSource
```

**효과**: 파일당 100-150 라인, 유지보수 용이

---

### 3.2 SG&A + AccountMatcher 분리

**현재**:
```
account_matcher.py  - 계정과목 매칭
sga_extractor.py    - SG&A 추출 (내부에서 HTML 파싱)
```

**개선**:
```
dart/
  account_matcher.py    - 계정과목 (LLM)
  sga_extractor.py      - SG&A (LLM)
  html_parser.py        - HTML 파싱 공통 (재사용)
```

**효과**: HTML 파싱 로직 재사용

---

## 4. 개선 가능한 구조

### 4.1 Evidence Source 계층

**현재** (평탄):
```
evidence/
  google_search_source.py
  duckduckgo_source.py
  kosis_source.py
  dart_connector.py
```

**개선** (계층화):
```
evidence/
  sources/
    __init__.py
    base/
      search_source.py       - BaseSearchSource
      official_source.py     - BaseOfficialSource
    
    search/
      google.py
      duckduckgo.py
    
    official/
      kosis.py
      dart.py
```

**효과**: 구조 명확, 확장 용이

---

### 4.2 LLM 중복 import

**발견**: 여러 파일에서 중복
```python
# 여러 파일에서
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import json
import re
```

**개선**: 공통 유틸리티
```python
# cmis_core/utils/common.py
# 자주 쓰는 import, 헬퍼 함수
```

---

## 5. 리팩토링 우선순위

### 우선순위 1 (높음)

**1. GoogleSearch + DuckDuckGo 중복 제거**
- 절감: ~300 라인
- 소요: 1-2시간
- 효과: 유지보수 50% 절감

**2. kosis_connector.py 정리**
- 절감: ~300 라인
- 소요: 30분
- 효과: 혼란 제거

**3. evidence_engine.py 분리**
- 절감: 0 라인 (구조 개선)
- 소요: 2-3시간
- 효과: 가독성, 유지보수

---

### 우선순위 2 (중간)

**4. Evidence 타입 분리**
- types.py → evidence/types.py
- 소요: 1시간
- 효과: 가독성

**5. HTML 파싱 공통화**
- sga_extractor에서 추출
- 소요: 1시간
- 효과: 재사용

---

### 우선순위 3 (낮음)

**6. Source 계층화**
- 구조 재배치
- 소요: 2-3시간
- 효과: 장기 유지보수

**7. 공통 유틸리티**
- utils/common.py
- 소요: 1시간
- 효과: import 정리

---

## 6. 즉시 리팩토링 vs 점진적

### 즉시 리팩토링 (권장)

**대상**: 우선순위 1
- GoogleSearch + DuckDuckGo 중복
- kosis_connector.py 정리

**소요**: 2-3시간
**효과**: ~600 라인 절감

### 점진적 리팩토링

**대상**: 우선순위 2-3
**시기**: v2.5, v3
**이유**: 기능 추가하면서 자연스럽게

---

## 7. 현재 코드 품질 평가

### 장점 ✅

1. **명확한 책임 분리**
   - Evidence Engine: 수집
   - LLM Service: LLM 관리
   - 각 Source: 독립적

2. **테스트 커버리지**
   - 131개 테스트 (100%)
   - 실제 API 검증

3. **확장성**
   - BaseDataSource
   - BaseLLM
   - Config-driven

### 단점 ⚠️

1. **중복 코드**
   - Google vs DuckDuckGo (~300 라인)
   - kosis 중복 (~300 라인)

2. **파일 크기**
   - evidence_engine.py (673 라인)
   - llm/service.py (626 라인)

3. **구조**
   - 평탄한 폴더 구조
   - 타입 분산

---

## 8. 리팩토링 계획

### Phase 1: 즉시 (2-3시간)

**작업**:
1. BaseSearchSource 추출
2. GoogleSearch, DuckDuckGo 리팩토링
3. kosis_connector.py 정리

**효과**:
- ~600 라인 절감
- 중복 제거
- 유지보수 개선

### Phase 2: v2.5 (1-2주)

**작업**:
1. evidence_engine.py 분리
2. Evidence 타입 분리
3. HTML 파싱 공통화

**효과**:
- 구조 개선
- 파일 크기 적정화

### Phase 3: v3 (장기)

**작업**:
1. Source 계층화
2. 공통 유틸리티
3. 문서 자동 생성

---

## 9. 최종 권장사항

### 즉시 리팩토링 ✅

**대상**:
- GoogleSearch + DuckDuckGo 중복
- kosis_connector.py 정리

**이유**:
- 효과 큼 (~600 라인)
- 리스크 낮음
- 빠름 (2-3시간)

### 점진적 개선

**대상**:
- 나머지 (우선순위 2-3)

**이유**:
- 리스크 관리
- 기능 추가하면서 자연스럽게

---

**결론**: 

**현재 코드 품질**: 양호 (테스트 100%, 작동 검증)
**리팩토링 필요성**: 중간 (중복 제거 권장)
**권장 타이밍**: 커밋 후 즉시 (2-3시간)

---

**다음 단계**:
1. 현재 상태 커밋 (v2.0)
2. 즉시 리팩토링 (중복 제거)
3. 재커밋 (v2.1)

어떻게 진행할까요?