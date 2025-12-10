# 검색 Evidence 전략 현황 분석

**작성일**: 2025-12-10  
**목적**: 검색 결과 활용 전략 개선

---

## 🔍 현재 구현 상태

### ✅ 이미 구현된 기능

#### 1. Full Page Fetching

**위치**: `base_search_source.py`

```python
class BaseSearchSource:
    def __init__(self, fetch_full_page: bool = False):
        self.fetch_full_page = fetch_full_page
    
    def fetch_page_content(self, url: str) -> Optional[str]:
        """웹 페이지 크롤링 (BeautifulSoup)"""
        # HTML 파싱, 텍스트 추출
```

**사용**:
```python
# Google/DuckDuckGo에서
if self.fetch_full_page:
    results = self._enrich_with_full_content(results)
    # snippet → full page content
```

**상태**: ✅ 구현됨 (기본값: False)

---

#### 2. 숫자 추출

```python
def extract_numbers(self, results: List[Dict]) -> List[float]:
    # 1. snippet 또는 full_content에서 텍스트 추출
    # 2. extract_numbers_from_text() 호출
    # 3. 모든 숫자 반환 (필터링 없음)
```

**상태**: ✅ 구현됨

---

#### 3. Consensus 알고리즘

```python
def calculate_consensus(self, numbers: List[float]):
    # 1. Outlier 제거 (IQR)
    # 2. 중앙값 계산
    # 3. Confidence 계산 (분산 기반)
```

**상태**: ✅ 구현됨

---

## ❌ 부족한 부분

### 문제 1: 데이터 없을 때 포기

**현재**:
```python
numbers = extract_numbers(results)
if not numbers:
    raise DataNotFoundError("No numbers")  # 포기!
```

**문제**:
- snippet에서 숫자 없으면 즉시 실패
- full_page는 기본적으로 시도 안 함
- 관련 데이터도 버림

---

### 문제 2: 관련 숫자 저장 안 함

**현재**:
- 원하는 Metric만 찾음
- 관련 숫자는 추출해도 버림
- 나중에 재활용 불가

**예시**:
```
검색: "Korea adult language education market revenue 2024"
결과: "Education market $4.9B", "Language learning $7.2B"

현재: 두 숫자 중 하나만 반환 (consensus)
문제: 나머지 숫자 버림 (나중에 유용할 수 있음)
```

---

### 문제 3: Evidence Tier 구분 없음

**현재**:
- 모든 Evidence가 동일한 tier
- exact match vs hint 구분 없음

**필요**:
- Primary Evidence: 정확히 요청한 Metric
- Secondary Evidence: 관련 있지만 다른 Metric
- Hint Evidence: 도움이 될 수 있는 숫자

---

## 🎯 개선 방안

### 제안 1: 2-Stage Fetching

**전략**:
```python
# Stage 1: Snippet에서 시도
numbers = extract_numbers(results)

if not numbers:
    # Stage 2: Full page fetching (자동)
    results = enrich_with_full_content(results)
    numbers = extract_numbers(results)
```

**장점**:
- Snippet에서 충분하면 빠름
- 데이터 없으면 자동으로 깊게 탐색

---

### 제안 2: Secondary Evidence 저장

**구조**:
```python
@dataclass
class EvidenceBundle:
    """Evidence 묶음"""
    primary: Optional[EvidenceRecord]  # 요청한 Metric
    secondary: List[EvidenceRecord]    # 관련 Metric
    hints: List[Dict[str, Any]]        # 도움될 수 있는 숫자
```

**저장**:
```python
# 모든 추출된 숫자를 hints로 저장
hints = [
    {
        "value": 4900000000,
        "context": "Education market",
        "snippet": "...USD 4.9 billion...",
        "confidence": 0.6,
        "source_url": "..."
    }
]
```

---

### 제안 3: Evidence Quality Tier

**분류**:
```python
class EvidenceQuality(Enum):
    EXACT_MATCH = "exact"      # 정확히 요청한 것
    RELATED = "related"        # 관련 있음
    HINT = "hint"              # 도움될 수 있음
    WEAK = "weak"              # 약한 연관성
```

**활용**:
- EXACT: 즉시 사용
- RELATED: 보조 증거로 사용
- HINT: EvidenceStore에 저장, 나중에 조회

---

## 🔧 구현 전략

### Phase 1: 자동 Full Page Fetching

**수정**: `base_search_source.py`

```python
def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
    query = self.build_search_query(request)
    results = self._search(query)
    
    # Stage 1: Snippet에서 시도
    numbers = self.extract_numbers(results)
    
    # Stage 2: 데이터 없으면 Full page (자동)
    if not numbers and not self.fetch_full_page:
        print(f"No numbers in snippets, fetching full pages...")
        results = self._enrich_with_full_content(results)
        numbers = self.extract_numbers(results)
    
    if not numbers:
        raise DataNotFoundError("No numbers")
    
    ...
```

**효과**:
- Snippet 부족 시 자동으로 페이지 크롤링
- 사용자가 fetch_full_page=True 설정 불필요

---

### Phase 2: Secondary Evidence 수집

**수정**: `base_search_source.py`

```python
def extract_all_evidence(self, results: List[Dict]) -> Dict[str, Any]:
    """모든 Evidence 추출 (primary + hints)"""
    
    all_numbers = self.extract_numbers(results)
    
    # Primary (consensus)
    primary_value, primary_confidence = self.calculate_consensus(all_numbers)
    
    # Hints (개별 숫자들)
    hints = []
    for i, result in enumerate(results):
        text = result.get('snippet', '') or result.get('body', '')
        result_numbers = self.extract_numbers_from_text(text)
        
        for num in result_numbers:
            hints.append({
                "value": num,
                "context": result.get('title', ''),
                "snippet": text[:200],
                "source_url": result.get('link', ''),
                "confidence": 0.5,  # Hint 기본 신뢰도
                "extracted_from": f"result_{i}"
            })
    
    return {
        "primary": {"value": primary_value, "confidence": primary_confidence},
        "hints": hints
    }
```

---

### Phase 3: EvidenceStore 통합

**저장**:
```python
# Primary Evidence
primary_record = EvidenceRecord(...)
evidence_store.store(primary_record)

# Hint Evidence (별도 tier)
for hint in hints:
    hint_record = EvidenceRecord(
        ...,
        source_tier="hint",  # 새 tier
        confidence=hint["confidence"],
        metadata={
            "quality": "hint",
            "related_metric": request.metric_id,
            "original_query": query
        }
    )
    evidence_store.store(hint_record)
```

**조회**:
```python
# 나중에 관련 Metric 계산 시
hints = evidence_store.query_hints(
    domain_id="Adult_Language_Education_KR",
    region="KR"
)
# → 이전 검색에서 저장한 hints 활용
```

---

## 📊 비교

### Before (현재)

```
검색 → Snippet 숫자 추출 → 없으면 실패 ❌
- 페이지 크롤링: 수동 (fetch_full_page=True)
- 관련 숫자: 버림
- 재활용: 불가
```

### After (개선안)

```
검색 → Snippet 시도 → 없으면 Full page → 모든 숫자 저장
- 페이지 크롤링: 자동
- 관련 숫자: Hint로 저장
- 재활용: EvidenceStore에서 조회
```

---

## 🎯 우선순위

### Priority 1: 자동 Full Page (즉시)

**목표**: snippet 부족 시 자동 크롤링

**작업**:
- base_search_source.py 수정
- 테스트 추가

**효과**: 검색 성공률 2-3배 향상

---

### Priority 2: Hint Evidence 저장 (Phase 4)

**목표**: 관련 숫자 저장 및 재활용

**작업**:
- EvidenceRecord에 quality tier 추가
- EvidenceStore에 query_hints() API
- Secondary evidence 수집 로직

**효과**: Evidence 재활용률 향상

---

### Priority 3: Smart Query Retry (Phase 4)

**목표**: 검색 실패 시 쿼리 변형 재시도

**작업**:
- 쿼리 변형 전략 (단어 순서, 동의어 등)
- 최대 3회 재시도
- 각 시도의 결과 모두 저장

**효과**: 검색 성공률 추가 향상

---

## 📝 권장 조치

### 즉시 (Priority 1)

✅ **자동 Full Page Fetching 구현**
- 10분 작업
- 즉시 효과

### Short-term (1-2일)

⏳ **Secondary Evidence 저장**
- EvidenceStore 확장
- Hint tier 추가

### Long-term (1주)

⏳ **Smart Retry + Evidence Lineage**
- 쿼리 최적화
- Evidence 추적

---

**작성**: 2025-12-10  
**결론**: Priority 1 즉시 구현 권장

