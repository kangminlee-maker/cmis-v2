# 검색 쿼리 고도화 전략 분석

**작성일**: 2025-12-10
**목적**: 검색 쿼리 확장 및 고도화 방안
**중요도**: ⭐⭐⭐⭐⭐ (리서치 핵심)

---

## 🔍 현재 구현 수준 분석

### 현재 구현 (Level 1: 기본)

#### 1. build_search_query() (base_search_source.py)

**코드**:
```python
def build_search_query(request):
    parts = []

    # domain_id
    if domain_id:
        parts.append(domain_id.replace("_", " "))

    # region
    if region == "KR":
        parts.append("Korea")

    # metric_id - 간단한 키워드 추가
    if "revenue" in metric_id or "tam" in metric_id:
        parts.append("market size")

    if "revenue" in metric_id:
        parts.append("revenue")

    # year
    parts.append(str(year))

    return " ".join(parts)
```

**예시**:
```
Input: MET-Revenue, Adult_Language_Education_KR, KR, 2024
Output: "adult language education kr Korea market size revenue 2024"
```

**평가**:
- ✅ 기본 작동
- ❌ 단순 키워드 나열
- ❌ 최적화 부족
- ❌ 확장 전략 없음

**Level**: 1/5 (기본)

---

#### 2. search_query_templates.yaml

**내용**:
```yaml
templates:
  MET-TAM:
    template: "{domain} {region} total addressable market size {year}"
    keywords: [market size, total addressable market]

  MET-Revenue:
    template: "{domain} {region} market size revenue {year}"
    keywords: [market size, revenue]

default:
  template: "{domain} {region} {metric} {year}"
```

**평가**:
- ✅ 템플릿 기반
- ❌ 1개 쿼리만 생성
- ❌ 변형 없음
- ❌ 활용도 낮음 (현재 미사용)

**Level**: 1/5 (기본 템플릿만)

---

#### 3. 재시도 전략

**현재**: 없음 ❌

**문제**:
- 데이터 없으면 즉시 실패
- 쿼리 변형 재시도 없음

**Level**: 0/5 (미구현)

---

### 현재 수준 종합

| 항목 | Level | 평가 |
|------|-------|------|
| 쿼리 생성 | 1/5 | 기본 (키워드 나열) |
| 쿼리 최적화 | 1/5 | 템플릿만 |
| 쿼리 확장 | 0/5 | 없음 |
| Multi-query | 0/5 | 없음 |
| 재시도 전략 | 0/5 | 없음 |
| LLM 활용 | 0/5 | 없음 |
| 쿼리 학습 | 0/5 | 없음 |

**전체 평균**: **0.4/5** (매우 기초)

---

## 🎯 고도화 로드맵 (Level 1 → Level 5)

### Level 2: 쿼리 변형 (1주)

**목표**: 1개 쿼리 → 3-5개 변형

**구현**:
```python
def generate_query_variations(request):
    """쿼리 변형 생성

    Returns:
        [
            "Korea adult language education market revenue 2024",
            "Korean language learning industry size 2024",
            "Korea education technology market value 2024",
            "language education sector Korea sales 2024"
        ]
    """
    base_query = build_base_query(request)

    variations = [base_query]

    # 1. 동의어 변형
    variations.append(replace_synonyms(base_query))

    # 2. 단어 순서 변경
    variations.append(reorder_keywords(base_query))

    # 3. 도메인 특화 용어
    variations.append(add_domain_terms(base_query, request.domain))

    return variations
```

**예상 코드**: 150-200 라인
**효과**: 검색 성공률 +30%

---

### Level 3: Multi-Query 전략 (2주)

**목표**: 변형 쿼리 병렬 실행 + 결과 병합

**구현**:
```python
def fetch_with_multi_query(request):
    """Multi-query 전략

    1. 3-5개 쿼리 변형 생성
    2. 병렬 실행
    3. 결과 병합 (가장 신뢰도 높은 것 선택)
    """
    queries = generate_query_variations(request)

    # 병렬 실행
    results = []
    for query in queries:
        try:
            result = search(query)
            results.append({
                "query": query,
                "numbers": extract_numbers(result),
                "confidence": calculate_confidence(result)
            })
        except:
            continue

    # 가장 좋은 결과 선택
    best_result = max(results, key=lambda r: r["confidence"])

    return best_result
```

**예상 코드**: 200-250 라인
**효과**: 검색 성공률 +50%, 품질 +30%

---

### Level 4: LLM 기반 쿼리 생성 (3주)

**목표**: Context → 최적 쿼리 자동 생성

**구현**:
```python
def generate_query_with_llm(request, context):
    """LLM 기반 쿼리 생성

    Prompt:
    - Domain: Adult Language Education
    - Region: Korea
    - Metric: Total Addressable Market
    - Year: 2024
    - Goal: Find market size revenue data

    → LLM이 최적 검색 쿼리 생성
    """
    prompt = f"""
    Generate 3-5 optimal search queries to find:
    - Metric: {request.metric_id}
    - Domain: {context.domain}
    - Region: {context.region}
    - Year: {context.year}

    Queries should be:
    1. Specific and targeted
    2. Use industry terms
    3. Likely to return numeric data
    4. Varied approaches (top-down, competitor, market research)

    Return as JSON array.
    """

    queries = llm_service.call_structured(prompt, schema=QueryList)

    return queries
```

**예상 코드**: 250-300 라인
**효과**: 검색 품질 +50%, 성공률 +70%

---

### Level 5: 적응형 쿼리 학습 (1개월)

**목표**: 쿼리 성능 학습 및 최적화

**구현**:
```python
class QueryLearner:
    """쿼리 성능 학습

    - 쿼리별 성공률 추적
    - 도메인별 최적 패턴 학습
    - 자동 최적화
    """

    def record_query_result(self, query, metric, success, quality):
        """쿼리 결과 기록"""
        # DB에 저장

    def get_best_queries(self, metric, domain):
        """과거 성공한 쿼리 조회"""
        # 유사 context에서 성공한 쿼리 반환

    def optimize_query(self, base_query, context):
        """학습 기반 최적화"""
        # 과거 패턴 적용
```

**예상 코드**: 400-500 라인
**효과**: 장기적 품질 향상 +100%

---

## 🚀 구현 계획

### Phase 1: 쿼리 변형 (즉시, 1주)

**Week 1: 동의어 및 변형**

**작업**:
1. 동의어 사전 구축
   ```yaml
   # config/search_synonyms.yaml
   synonyms:
     revenue: [sales, income, turnover]
     market: [industry, sector, space]
     size: [value, worth, volume]
   ```

2. QueryVariationGenerator 클래스
   ```python
   class QueryVariationGenerator:
       def generate(self, base_query):
           # 1. 동의어 치환
           # 2. 단어 순서 변경
           # 3. 키워드 추가/제거
   ```

3. Multi-query 실행
   ```python
   def fetch_with_variations(request):
       queries = generator.generate(base_query)

       for query in queries:
           try:
               result = search(query)
               if has_useful_data(result):
                   return result
           except:
               continue
   ```

**예상**:
- 코드: 200 라인
- 테스트: 10개
- 효과: 성공률 +30%

---

### Phase 2: LLM 쿼리 생성 (2주 후)

**Week 3-4: LLM 통합**

**작업**:
1. LLM 프롬프트 설계
   ```python
   prompt = """
   Context:
   - Industry: {domain}
   - Region: {region}
   - Metric: {metric}
   - Year: {year}

   Generate 5 search queries optimized for:
   1. Finding market size data
   2. Competitor revenue
   3. Industry reports
   4. Government statistics
   5. News/announcements

   Each query should target different data sources.
   """
   ```

2. LLMQueryGenerator
   ```python
   class LLMQueryGenerator:
       def generate_queries(self, context):
           # LLM 호출
           # 구조화된 응답
           # 검증
   ```

3. 쿼리 품질 평가
   ```python
   def evaluate_query_quality(query, results):
       # 결과 품질 점수
       # LLM 피드백 루프
   ```

**예상**:
- 코드: 300 라인
- 테스트: 15개
- 비용: ~$0.001/쿼리
- 효과: 품질 +50%

---

### Phase 3: 적응형 학습 (1개월 후)

**Week 5-8: 쿼리 학습**

**작업**:
1. 쿼리 성능 DB
   ```sql
   CREATE TABLE query_performance (
       query TEXT,
       metric_id TEXT,
       domain TEXT,
       success BOOLEAN,
       quality_score FLOAT,
       timestamp DATETIME
   )
   ```

2. 패턴 학습
   ```python
   def learn_query_patterns(domain, metric):
       # 과거 성공 쿼리 분석
       # 패턴 추출
       # 새 쿼리 생성 시 적용
   ```

3. A/B 테스트
   ```python
   # 쿼리 A vs B 성능 비교
   # 더 나은 것 선택
   ```

---

## 📊 현재 vs 목표

### 현재 (Level 1)

```python
# 단순 키워드 나열
query = "adult language education Korea revenue 2024"

# 1개 쿼리만
# 실패 시 포기
```

**성공률**: ~70%
**품질**: 중간

---

### 목표 (Level 5)

```python
# LLM 기반 최적 쿼리 생성
queries = [
    "Korea adult language learning market size revenue 2024",
    "Korean language education industry market value 2024",
    "language education sector Korea 2024 sales revenue",
    "adult education language programs Korea market 2024",
    "Korea EdTech language learning market revenue 2024"
]

# Multi-query 병렬 실행
# 결과 병합 및 검증
# 쿼리 성능 학습
```

**성공률**: ~95%+
**품질**: 높음

---

## 🎯 우선 구현 (Phase 1)

### 핵심 기능 3가지

#### 1. 동의어 기반 쿼리 확장 ⭐⭐⭐⭐⭐

**구현**:
```yaml
# config/search_synonyms.yaml
domain_synonyms:
  education:
    - learning
    - training
    - teaching
    - academy
    - school

  language:
    - linguistic
    - tongues
    - communication

metric_synonyms:
  revenue:
    - sales
    - income
    - turnover
    - earnings

  market size:
    - market value
    - industry size
    - market worth
    - total market

region_synonyms:
  Korea:
    - Korean
    - South Korea
    - Republic of Korea
    - ROK
```

```python
def expand_with_synonyms(base_query, synonyms):
    """동의어로 쿼리 확장

    Returns:
        [
            "Korea adult language education market revenue 2024",
            "Korean adult linguistic learning industry sales 2024",
            "South Korea language training market income 2024"
        ]
    """
```

**효과**: 쿼리 변형 3-5개 → 성공률 +30%

---

#### 2. Multi-Query 병렬 실행 ⭐⭐⭐⭐⭐

**구현**:
```python
def fetch_with_multi_query(request):
    """여러 쿼리 변형 시도

    Strategy:
    1. 기본 쿼리
    2. 동의어 변형 2-3개
    3. 순서 변경 1-2개

    → 각각 실행, 가장 좋은 결과 선택
    """
    queries = generate_variations(request)

    results = []
    for query in queries:
        try:
            result = search(query)
            if has_numbers(result):
                results.append({
                    "query": query,
                    "data": result,
                    "quality": evaluate_quality(result)
                })
        except:
            continue

    if not results:
        raise DataNotFoundError()

    # 최고 품질 선택
    best = max(results, key=lambda r: r["quality"])
    return best["data"]
```

**효과**: 성공률 +50%

---

#### 3. 도메인별 쿼리 최적화 ⭐⭐⭐⭐

**구현**:
```yaml
# config/domain_query_strategies.yaml
domains:
  education:
    preferred_terms:
      - EdTech
      - e-learning
      - online education
      - education market

    data_sources:
      - education ministry
      - industry reports
      - market research

    query_patterns:
      - "{domain} {region} EdTech market size {year}"
      - "{region} online education industry revenue {year}"

  healthcare:
    preferred_terms:
      - HealthTech
      - medical services
      - healthcare industry
```

```python
def build_domain_optimized_query(request, domain):
    """도메인별 최적화 쿼리"""
    strategy = load_domain_strategy(domain)

    # 도메인 특화 용어 사용
    # 산업별 best practices
```

**효과**: 도메인별 품질 +40%

---

## 🔧 구현 상세

### 1. QueryExpansionEngine (신규)

```python
class QueryExpansionEngine:
    """쿼리 확장 엔진

    기능:
    1. 동의어 확장
    2. 순서 변형
    3. 키워드 추가/제거
    4. 도메인 최적화
    """

    def __init__(self):
        self.synonyms = self._load_synonyms()
        self.domain_strategies = self._load_domain_strategies()

    def expand(self, base_query, context, max_variations=5):
        """쿼리 확장

        Returns:
            최대 5개 변형
        """
        variations = [base_query]

        # 동의어
        variations.extend(
            self._synonym_variations(base_query, max=2)
        )

        # 순서 변경
        variations.append(
            self._reorder_variation(base_query)
        )

        # 도메인 최적화
        if context.get("domain"):
            variations.append(
                self._domain_optimized(base_query, context["domain"])
            )

        return variations[:max_variations]
```

---

### 2. MultiQuerySearchSource (개선)

```python
class MultiQuerySearchSource(BaseSearchSource):
    """Multi-query 검색 (개선)"""

    def __init__(self):
        super().__init__(...)
        self.query_engine = QueryExpansionEngine()

    def fetch(self, request):
        """Multi-query로 수집"""
        base_query = self.build_search_query(request)

        # 1. 쿼리 확장
        queries = self.query_engine.expand(base_query, request.context)

        # 2. 각 쿼리 시도
        all_results = []

        for query in queries:
            try:
                results = self._search(query)
                numbers = self.extract_numbers(results)

                if numbers:
                    all_results.append({
                        "query": query,
                        "numbers": numbers,
                        "results": results,
                        "quality": self._evaluate_quality(results, numbers)
                    })
            except:
                continue

        if not all_results:
            raise DataNotFoundError("No data from any query variation")

        # 3. 최고 품질 선택
        best = max(all_results, key=lambda r: r["quality"])

        # 4. EvidenceRecord 생성 (metadata에 시도한 쿼리들 기록)
        return EvidenceRecord(
            ...,
            metadata={
                "primary_query": best["query"],
                "alternative_queries": [q["query"] for q in all_results],
                "total_attempts": len(queries),
                "successful_queries": len(all_results)
            }
        )
```

---

### 3. LLMQueryGenerator (고급)

```python
class LLMQueryGenerator:
    """LLM 기반 쿼리 생성"""

    def generate(self, request, context):
        """LLM으로 최적 쿼리 생성"""
        prompt = self._build_prompt(request, context)

        response = llm_service.call_structured(
            prompt,
            schema={
                "queries": [
                    {
                        "query": str,
                        "rationale": str,
                        "expected_source_type": str
                    }
                ]
            }
        )

        return [q["query"] for q in response["queries"]]

    def _build_prompt(self, request, context):
        """프롬프트 구성"""
        return f"""
        Generate optimal search queries for market research.

        Context:
        - Industry: {context.domain}
        - Region: {context.region}
        - Target Metric: {request.metric_id}
        - Year: {context.year}

        Generate 5 queries targeting:
        1. Market size reports
        2. Competitor revenue
        3. Industry statistics
        4. Government data
        5. News/press releases

        Each query should be:
        - Specific (include industry terms)
        - Targeted (likely to return numbers)
        - Varied (different angles)

        Return as structured JSON.
        """
```

---

## 📊 예상 효과

### Level별 개선

| Level | 쿼리 수 | 성공률 | 품질 | 비용 |
|-------|---------|--------|------|------|
| **L1 (현재)** | 1 | 70% | 중간 | $0 |
| **L2 (변형)** | 3-5 | 85% | 중상 | $0 |
| **L3 (Multi)** | 3-5 | 90% | 높음 | $0 |
| **L4 (LLM)** | 5-10 | 95% | 매우높음 | ~$0.001 |
| **L5 (학습)** | 최적화 | 97%+ | 최고 | ~$0.001 |

---

## 💡 즉시 구현 권장 (Phase 1)

### Week 1: 쿼리 변형 엔진

**파일**:
- `cmis_core/query_expansion.py` (200 라인)
- `config/search_synonyms.yaml` (100 라인)
- `config/domain_query_strategies.yaml` (200 라인)

**기능**:
1. 동의어 기반 확장
2. Multi-query 실행
3. 결과 품질 평가

**효과**:
- 성공률: 70% → 90% (+20%p)
- 품질: 중간 → 높음

---

## 🎯 권장 실행 순서

### 즉시 (Week 1)

1. ✅ 동의어 사전 (search_synonyms.yaml)
2. ✅ QueryExpansionEngine 구현
3. ✅ Multi-query 전략

### 중기 (Week 2-3)

4. ⏳ 도메인별 최적화
5. ⏳ 쿼리 품질 평가

### 장기 (Week 4+)

6. ⏳ LLM 쿼리 생성
7. ⏳ 쿼리 학습

---

**작성**: 2025-12-10
**현재**: Level 1/5 (기초)
**권장**: Phase 1 즉시 착수 (Level 2-3 달성)


