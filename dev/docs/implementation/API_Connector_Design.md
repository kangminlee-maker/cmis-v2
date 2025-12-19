# 실제 API Connector 구현 설계

**작성일**: 2025-12-09
**목적**: KOSIS, Google Search API를 BaseDataSource로 구현

---

## 1. v7 코드 분석 결과

### 1.1 발견한 구현

| API | v7 파일 | 구현 상태 | 활용 가능성 |
|-----|---------|----------|-----------|
| **DART** | `dart_api.py`, `dart_connector.py` | ✅ 완전 구현 | ✅ 이미 통합 완료 |
| **Google Search** | `validator.py`, `value.py` | ✅ 완전 구현 | ✅ 활용 가능 |
| **DuckDuckGo** | `value.py` | ✅ 완전 구현 | ✅ 활용 가능 |
| **KOSIS** | `validator.py` (api_key만) | ⚠️ 스텁만 | 🔨 신규 구현 필요 |

### 1.2 v7 Google Search 구현 분석

**파일**: `value.py` WebSearchSource 클래스

**핵심 기능**:
```python
# 1. Google Custom Search API
base_url = "https://www.googleapis.com/customsearch/v1"
params = {
    'key': google_api_key,
    'cx': google_search_engine_id,
    'q': query,
    'num': 5
}

# 2. 페이지 크롤링 (optional)
if fetch_full_page:
    full_content = _fetch_page_content(url)

# 3. 숫자 추출 + Consensus
numbers = _extract_numbers_from_results(results)
consensus = _find_consensus(numbers)
```

**장점**:
- Google Custom Search API 사용 (고품질)
- DuckDuckGo fallback (무료)
- 페이지 크롤링 지원
- Consensus 알고리즘

**단점**:
- LLM 의존적 (숫자 추출)
- v9 Evidence 스키마와 불일치

---

## 2. v9 구현 전략

### 2.1 설계 원칙

```
1. v7 API 호출 로직 재사용
   - Google Custom Search
   - DuckDuckGo Search
   - 페이지 크롤링

2. v9 BaseDataSource 인터페이스 준수
   - fetch() → EvidenceRecord
   - can_handle()
   - capabilities

3. LLM 의존성 제거
   - 숫자 추출: 정규식 기반
   - Consensus: 통계 기반

4. Graceful Degradation
   - Google 실패 → DuckDuckGo
   - API 키 없음 → DataNotFoundError
```

### 2.2 구현 우선순위

| 순위 | Connector | 난이도 | 가치 | v7 기반 |
|------|-----------|--------|------|---------|
| 1 | **GoogleSearchSource** | 하 | 상 | ✅ 95% 재사용 |
| 2 | **KOSISSource** | 중 | 상 | ❌ 신규 구현 |
| 3 | **DuckDuckGoSource** | 하 | 중 | ✅ 95% 재사용 |

---

## 3. GoogleSearchSource 설계

### 3.1 클래스 구조

```python
class GoogleSearchSource(BaseDataSource):
    """Google Custom Search API Source

    v7 WebSearchSource 기반, v9 Evidence 스키마로 변환
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None
    ):
        """
        Args:
            api_key: Google API Key
            search_engine_id: Custom Search Engine ID
        """
        super().__init__(
            source_id="GoogleSearch",
            source_tier=SourceTier.COMMERCIAL,  # 유료 서비스
            capabilities={
                "provides": ["market_data", "company_info", "recent_news"],
                "regions": ["*"],
                "data_types": ["numeric", "raw_document"]
            }
        )

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.engine_id = search_engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        if not self.api_key or not self.engine_id:
            raise SourceNotAvailableError(
                "Google API credentials required"
            )

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """Evidence 수집

        프로세스:
        1. Context에서 검색 쿼리 구성
        2. Google Custom Search API 호출
        3. 결과에서 숫자 추출 (정규식)
        4. EvidenceRecord 생성
        """
        # 1. 쿼리 구성
        query = self._build_search_query(request)

        # 2. API 호출
        results = self._search_google(query)

        if not results:
            raise DataNotFoundError(f"No Google results for: {query}")

        # 3. 숫자 추출
        numbers = self._extract_numbers(results, request)

        if not numbers:
            raise DataNotFoundError(f"No numeric data in results")

        # 4. Consensus (중앙값 사용)
        value = self._calculate_consensus(numbers)
        confidence = self._calculate_confidence(numbers)

        # 5. EvidenceRecord 생성
        return EvidenceRecord(
            evidence_id=f"EVD-GoogleSearch-{uuid.uuid4().hex[:8]}",
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=value,
            value_kind=EvidenceValueKind.NUMERIC,
            confidence=confidence,
            metadata={
                "query": query,
                "num_results": len(results),
                "num_numbers": len(numbers),
                "sources": [r.get("link") for r in results[:3]]
            },
            lineage={
                "search_engine": "google",
                "api": "custom_search_v1"
            }
        )

    def can_handle(self, request: EvidenceRequest) -> bool:
        """처리 가능 여부

        조건:
        - API 키 있음
        - 수치 질문 (metric_id 또는 context에 숫자 관련 힌트)
        """
        if not self.api_key or not self.engine_id:
            return False

        # Metric 요청은 처리 가능
        if request.metric_id:
            return True

        # Reality slice는 처리 안 함
        if request.request_type == "reality_slice":
            return False

        return True
```

### 3.2 핵심 메서드

**_build_search_query()**:
```python
def _build_search_query(self, request: EvidenceRequest) -> str:
    """검색 쿼리 구성

    Context 기반:
    - metric_id: "MET-Revenue" → "market revenue"
    - domain_id: "Adult_Language_Education_KR"
    - region: "KR" → "Korea"
    - year: 2024

    Example:
        "adult language education Korea market revenue 2024"
    """
```

**_search_google()**:
```python
def _search_google(self, query: str) -> List[Dict]:
    """Google Custom Search API 호출

    v7 로직 재사용:
    - requests 라이브러리
    - timeout 처리
    - error handling
    """
```

**_extract_numbers()**:
```python
def _extract_numbers(
    self,
    results: List[Dict],
    request: EvidenceRequest
) -> List[float]:
    """결과에서 숫자 추출

    v7 대비 개선:
    - LLM 제거 → 정규식 기반
    - 패턴: "100억", "1.2 trillion", "$500M"
    - 단위 변환: 억/조 → 숫자
    """
```

---

## 4. KOSISSource 설계

### 4.1 KOSIS OpenAPI 조사

**API 문서**: https://kosis.kr/openapi/index/index.jsp

**주요 기능**:
- 통계표 조회
- 인구/가구/소득 통계
- 산업별 통계

**필요 정보**:
- API Key
- 통계표 ID (orgId, tblId)
- 항목 코드 (itmId, objL1, objL2 등)

### 4.2 클래스 구조 (초안)

```python
class KOSISSource(BaseDataSource):
    """KOSIS (통계청) API Source

    신규 구현 (v7에 없음)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: KOSIS API Key
        """
        super().__init__(
            source_id="KOSIS",
            source_tier=SourceTier.OFFICIAL,
            capabilities={
                "provides": ["population_stats", "macro_indicators"],
                "regions": ["KR"],
                "data_types": ["numeric", "table"]
            }
        )

        self.api_key = api_key or os.getenv("KOSIS_API_KEY")
        self.base_url = "https://kosis.kr/openapi"

        if not self.api_key:
            raise SourceNotAvailableError("KOSIS_API_KEY required")

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """Evidence 수집

        v1: 기본 통계표만 지원
        - 인구 통계 (101)
        - 가구 통계 (102)
        """
        # TODO: 실제 API 호출 로직
        # v7에 구현 없으므로 신규 개발 필요

        raise DataNotFoundError("KOSIS integration not yet implemented")

    def can_handle(self, request: EvidenceRequest) -> bool:
        """처리 가능 여부"""
        # KR region만 지원
        return request.context.get("region") == "KR"
```

---

## 5. 구현 계획

### 5.1 Phase 1: GoogleSearchSource (1-2일)

**작업**:
- [x] v7 코드 분석 완료
- [ ] GoogleSearchSource 구현 (v7 로직 재사용)
- [ ] 정규식 기반 숫자 추출
- [ ] Consensus 알고리즘
- [ ] 테스트 (optional API key)

**난이도**: 하 (v7 코드 95% 재사용)

### 5.2 Phase 2: DuckDuckGoSource (0.5일)

**작업**:
- [ ] DuckDuckGoSource 구현
- [ ] Graceful fallback 로직
- [ ] 테스트

**난이도**: 하 (v7 코드 재사용)

### 5.3 Phase 3: KOSISSource (2-3일)

**작업**:
- [ ] KOSIS OpenAPI 조사
- [ ] 인구 통계표 매핑
- [ ] API 호출 로직
- [ ] 테스트 (optional API key)

**난이도**: 중 (신규 구현)

### 5.4 Phase 4: 통합 테스트 (1일)

**작업**:
- [ ] End-to-end 테스트
- [ ] 실제 API 호출 (optional)
- [ ] ValueEngine 연동 검증

---

## 6. v7 vs v9 차이점

### 6.1 v7 WebSearchSource

**장점**:
- Google + DuckDuckGo 지원
- 페이지 크롤링
- Consensus 알고리즘

**단점**:
- LLM 의존 (숫자 추출)
- ValueEstimate 타입 (v9 호환 안 됨)

### 6.2 v9 GoogleSearchSource (개선)

**개선점**:
- LLM 제거 → 정규식 기반
- EvidenceRecord 스키마
- BaseDataSource 인터페이스
- SourceRegistry 통합

**유지**:
- Google Custom Search API
- 페이지 크롤링
- Timeout/Retry 로직

---

## 7. 다음 단계

### 즉시 시작
1. GoogleSearchSource 구현 (v7 기반)
2. 숫자 추출 로직 (정규식)
3. 테스트 (API key optional)

### 중기 (1-2주)
4. DuckDuckGoSource
5. KOSISSource (기본 통계표)

### 장기 (1개월)
6. KOSIS 고도화 (다양한 통계표)
7. 추가 Official Source (한국은행 등)

---

**다음 작업**: GoogleSearchSource 구현 시작

---

**변경 이력**:
- 2025-12-09: 초안 작성 (v7 코드 분석 기반)
