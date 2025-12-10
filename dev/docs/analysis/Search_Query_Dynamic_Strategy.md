# 검색 쿼리 동적 확장 전략 (재설계)

**작성일**: 2025-12-10  
**핵심 통찰**: Dictionary는 불가능, LLM 동적 생성 + 다국어 필수

---

## 🎯 근본적 문제 인식

### ❌ Dictionary/리스팅 방식의 한계

**문제**:
```yaml
# config/search_synonyms.yaml
synonyms:
  revenue: [sales, income, turnover, earnings, ...]  # 끝이 없음!
  market: [industry, sector, space, ...]
  education: [learning, training, academy, ...]
```

**한계**:
1. ❌ **무한 확장 불가**: 동의어가 끝없이 많음
2. ❌ **Context 무시**: "adult education"과 "education adult"는 다름
3. ❌ **조합 폭발**: N개 단어 × M개 동의어 = 폭발
4. ❌ **도메인 특수성**: 산업마다 용어가 다름
5. ❌ **언어 장벽**: 한국어, 영어, 일본어 모두 다름

**결론**: Dictionary는 근본적으로 불가능 ❌

---

### ✅ 올바른 접근: LLM 동적 생성

**원리**:
```
Context → LLM → 최적 쿼리 동적 생성
- 무한 확장 가능
- Context 이해
- 도메인 적응
- 다국어 자동 처리
```

---

## 🌍 다국어 검색 전략

### 언어별 결과 차이

**한국 시장 예시**:

**한국어 검색**:
```
"성인 어학 교육 시장 규모 2024"
→ 한국 뉴스, 한국 리포트, 정부 통계
→ 한국 특화 데이터 ✅
```

**영어 검색**:
```
"Korea adult language education market size 2024"
→ 글로벌 리포트, 컨설팅 보고서, 해외 분석
→ 국제 비교 데이터 ✅
```

**문제**: 언어에 따라 완전히 다른 결과!

---

### 다국어 전략 필수

**전략**:
```python
def search_multilingual(context):
    """다국어 병렬 검색"""
    
    # 1. 언어별 쿼리 생성 (LLM)
    queries = {
        "ko": llm.generate_query(context, language="korean"),
        "en": llm.generate_query(context, language="english"),
        "ja": llm.generate_query(context, language="japanese")  # 필요시
    }
    
    # 2. 병렬 실행
    results = {
        "ko": search_korean(queries["ko"]),
        "en": search_english(queries["en"])
    }
    
    # 3. 결과 병합 및 선택
    best_result = select_best(results)
    
    return best_result
```

**효과**: 언어별 최적 결과 확보

---

## 🚀 LLM 기반 동적 쿼리 생성 (필수)

### 구현 아키텍처

```
Context
    ↓
LLMQueryGenerator
    ↓
다국어 쿼리 생성 (한/영/일)
    ↓
변형 생성 (각 언어별 3-5개)
    ↓
병렬 실행 (총 10-15개 쿼리)
    ↓
결과 평가 및 선택
    ↓
Best Evidence
```

---

### 핵심 구현

#### 1. LLMQueryGenerator

```python
class LLMQueryGenerator:
    """LLM 기반 동적 쿼리 생성
    
    원리:
    - Context 이해
    - 언어별 최적 쿼리 생성
    - 도메인 용어 자동 활용
    """
    
    def generate_multilingual_queries(
        self,
        context: Dict,
        languages: List[str] = ["ko", "en"]
    ) -> Dict[str, List[str]]:
        """다국어 쿼리 생성
        
        Args:
            context: {domain, region, metric, year}
            languages: 생성할 언어 리스트
        
        Returns:
            {
                "ko": ["쿼리1", "쿼리2", ...],
                "en": ["query1", "query2", ...]
            }
        """
        queries = {}
        
        for lang in languages:
            queries[lang] = self._generate_for_language(context, lang)
        
        return queries
    
    def _generate_for_language(
        self,
        context: Dict,
        language: str
    ) -> List[str]:
        """특정 언어로 쿼리 생성
        
        Returns:
            3-5개 변형 쿼리
        """
        prompt = self._build_prompt(context, language)
        
        response = llm_service.call_structured(
            prompt,
            schema={
                "queries": [
                    {
                        "query": str,
                        "rationale": str,
                        "target_source": str
                    }
                ]
            }
        )
        
        return [q["query"] for q in response["queries"]]
    
    def _build_prompt(self, context, language):
        """프롬프트 구성"""
        
        if language == "ko":
            return f"""
            한국 시장 리서치를 위한 최적의 검색 쿼리를 생성하세요.
            
            Context:
            - 산업: {context["domain"]}
            - 지역: {context["region"]}
            - 지표: {context["metric"]}
            - 연도: {context["year"]}
            
            다음을 목표로 5가지 검색 쿼리를 생성하세요:
            1. 시장 규모 리포트
            2. 산업 통계
            3. 경쟁사 매출
            4. 정부 발표 자료
            5. 뉴스/언론 보도
            
            각 쿼리는:
            - 구체적이어야 함 (산업 용어 사용)
            - 숫자 데이터를 포함할 가능성이 높아야 함
            - 서로 다른 각도에서 접근
            
            JSON 배열로 반환하세요.
            """
        
        elif language == "en":
            return f"""
            Generate optimal search queries for market research.
            
            Context:
            - Industry: {context["domain"]}
            - Region: {context["region"]}
            - Metric: {context["metric"]}
            - Year: {context["year"]}
            
            Generate 5 search queries targeting:
            1. Market size reports
            2. Industry statistics
            3. Competitor revenue
            4. Government data
            5. News/press releases
            
            Each query should:
            - Be specific (use industry terminology)
            - Target numeric data
            - Take different approaches
            
            Return as JSON array.
            """
```

---

#### 2. MultilingualSearchEngine

```python
class MultilingualSearchEngine:
    """다국어 검색 엔진
    
    기능:
    - 언어별 쿼리 생성 (LLM)
    - 병렬 검색
    - 결과 병합
    """
    
    def __init__(self):
        self.query_generator = LLMQueryGenerator()
        self.search_engines = {
            "google": GoogleSearchSource(),
            "duckduckgo": DuckDuckGoSource()
        }
    
    def search_multilingual(
        self,
        context: Dict,
        languages: List[str] = None
    ) -> Dict[str, Any]:
        """다국어 검색
        
        Returns:
            {
                "primary_result": EvidenceRecord,
                "all_results": {
                    "ko": [...],
                    "en": [...]
                },
                "best_language": "ko",
                "best_query": "..."
            }
        """
        # 1. 언어 결정
        if languages is None:
            languages = self._determine_languages(context)
        
        # 2. 언어별 쿼리 생성
        multilingual_queries = self.query_generator.generate_multilingual_queries(
            context,
            languages
        )
        
        # 3. 언어별 검색 실행
        all_results = {}
        
        for lang, queries in multilingual_queries.items():
            lang_results = []
            
            for query in queries:
                try:
                    result = self._search_with_query(query)
                    if result:
                        lang_results.append(result)
                except:
                    continue
            
            all_results[lang] = lang_results
        
        # 4. 최상의 결과 선택
        best_result = self._select_best_result(all_results)
        
        return best_result
    
    def _determine_languages(self, context):
        """Context에서 필요한 언어 결정
        
        한국 시장: ["ko", "en"]
        미국 시장: ["en"]
        일본 시장: ["ja", "en"]
        """
        region = context.get("region", "")
        
        if region == "KR":
            return ["ko", "en"]  # 한국어 우선, 영어 보조
        elif region == "JP":
            return ["ja", "en"]
        elif region == "CN":
            return ["zh", "en"]
        else:
            return ["en"]  # 기본: 영어
```

---

#### 3. QueryQualityEvaluator

```python
class QueryQualityEvaluator:
    """쿼리 품질 평가 (LLM 기반)
    
    기능:
    - 검색 결과 품질 평가
    - 최적 쿼리/언어 선택
    """
    
    def evaluate_result_quality(
        self,
        query: str,
        search_results: List[Dict],
        extracted_numbers: List[float],
        context: Dict
    ) -> float:
        """결과 품질 평가
        
        Returns:
            품질 점수 (0.0 ~ 1.0)
        """
        # 1. 기본 점수
        base_score = 0.0
        
        # 숫자 개수
        if extracted_numbers:
            base_score += 0.3
        
        # 결과 개수
        base_score += min(len(search_results) / 10, 0.2)
        
        # 2. LLM 평가 (선택적)
        if extracted_numbers:
            relevance = self._evaluate_relevance_with_llm(
                query,
                search_results,
                context
            )
            base_score += relevance * 0.5
        
        return min(base_score, 1.0)
    
    def _evaluate_relevance_with_llm(self, query, results, context):
        """LLM으로 관련성 평가
        
        Prompt:
        - Query: "Korea adult language education market revenue 2024"
        - Results: [snippet1, snippet2, ...]
        - Context: Adult Language Education in Korea
        
        → LLM이 관련성 점수 (0-1) 반환
        """
        prompt = f"""
        Evaluate how relevant these search results are for:
        
        Target: {context["metric"]} in {context["domain"]}, {context["region"]}
        Query: {query}
        
        Results:
        {format_results(results[:3])}
        
        Rate relevance (0.0 to 1.0):
        - 1.0: Directly answers the question
        - 0.7: Related and useful
        - 0.5: Tangentially related
        - 0.3: Loosely related
        - 0.0: Not relevant
        
        Return single float score.
        """
        
        score = llm_service.call(prompt)
        return float(score)
```

---

## 🔧 즉시 구현 (Phase 1)

### Week 1: LLM 쿼리 생성 + 다국어

**파일 구조**:
```
cmis_core/
├── query_expansion_llm.py (LLMQueryGenerator)
├── search_multilingual.py (MultilingualSearchEngine)
└── query_quality.py (QueryQualityEvaluator)

config/
└── query_generation_prompts.yaml (프롬프트 템플릿)
```

---

### 1. query_expansion_llm.py (300 라인)

**핵심 기능**:

```python
class LLMQueryGenerator:
    """LLM 기반 동적 쿼리 생성"""
    
    def generate_queries(
        self,
        context: Dict,
        language: str = "auto",
        num_variations: int = 5
    ) -> List[str]:
        """동적 쿼리 생성
        
        Args:
            context: {domain, region, metric, year}
            language: "ko", "en", "auto"
            num_variations: 생성할 쿼리 개수
        
        Returns:
            동적 생성된 쿼리 리스트
        """
        # 언어 자동 결정
        if language == "auto":
            language = self._determine_language(context)
        
        # LLM 프롬프트
        prompt = self._build_generation_prompt(context, language, num_variations)
        
        # LLM 호출
        response = self.llm_service.call_structured(
            prompt,
            schema=QueryListSchema
        )
        
        return [q["query"] for q in response["queries"]]
    
    def _determine_language(self, context):
        """Context에서 언어 결정
        
        한국: ko 우선
        글로벌: en
        """
        region = context.get("region", "")
        
        if region in ["KR", "한국"]:
            return "ko"
        elif region in ["JP", "일본"]:
            return "ja"
        elif region in ["CN", "중국"]:
            return "zh"
        else:
            return "en"
```

---

### 2. 다국어 병렬 검색

```python
class MultilingualSearchEngine:
    """다국어 검색 실행"""
    
    def search(self, context):
        """다국어 검색
        
        Strategy:
        1. 한국 시장: 한국어 3개 + 영어 3개 = 6개 쿼리
        2. 글로벌: 영어 5개
        3. 일본: 일본어 3개 + 영어 3개
        """
        region = context["region"]
        
        # 언어 결정
        if region == "KR":
            languages = ["ko", "en"]
        elif region == "JP":
            languages = ["ja", "en"]
        else:
            languages = ["en"]
        
        # 언어별 쿼리 생성 (LLM)
        all_queries = {}
        for lang in languages:
            all_queries[lang] = self.query_gen.generate_queries(
                context,
                language=lang,
                num_variations=3
            )
        
        # 병렬 실행
        all_results = {}
        for lang, queries in all_queries.items():
            lang_results = []
            
            for query in queries:
                result = self._search_single(query, lang)
                if result:
                    lang_results.append({
                        "query": query,
                        "language": lang,
                        "data": result,
                        "quality": self._evaluate(result)
                    })
            
            all_results[lang] = lang_results
        
        # 최상의 언어/쿼리 선택
        best = self._select_best(all_results)
        
        return best
```

---

### 3. 프롬프트 템플릿 (YAML)

```yaml
# config/query_generation_prompts.yaml

korean_prompt_template: |
  {context["domain"]} 산업의 {context["metric"]} 데이터를 찾기 위한 
  최적의 검색 쿼리를 {num_variations}개 생성하세요.
  
  Context:
  - 산업: {context["domain"]}
  - 지역: {context["region"]}
  - 지표: {context["metric"]}
  - 연도: {context["year"]}
  
  다음 목표로 쿼리를 생성하세요:
  1. 시장 조사 리포트
  2. 산업 통계 자료
  3. 경쟁사 실적
  4. 정부 통계/발표
  5. 언론 보도
  
  각 쿼리는:
  - 구체적 (산업 용어 사용)
  - 숫자 데이터 포함 가능성 높게
  - 서로 다른 각도
  
  JSON 형식으로 반환:
  [
    {"query": "...", "target": "market report"},
    {"query": "...", "target": "government stats"},
    ...
  ]

english_prompt_template: |
  Generate {num_variations} optimal search queries to find 
  {context["metric"]} data for {context["domain"]} industry.
  
  Context:
  - Industry: {context["domain"]}
  - Region: {context["region"]}
  - Metric: {context["metric"]}
  - Year: {context["year"]}
  
  Target sources:
  1. Market research reports
  2. Industry statistics
  3. Competitor financials
  4. Government data
  5. News/press releases
  
  Requirements:
  - Use industry-specific terminology
  - Optimize for numeric data retrieval
  - Vary approach (top-down, bottom-up, peer comparison)
  
  Return as JSON array.
```

---

## 📊 예상 효과

### 쿼리 개수

```
Before: 1개 (고정)
After:  10-15개 (동적)
- 한국어: 3-5개
- 영어: 3-5개
- 기타: 필요시
```

### 성공률

```
Before: 70% (1개 쿼리)
After:  95%+ (10개 쿼리 중 최소 1개 성공)

개선: +25%p
```

### 품질

```
Before: 중간 (단순 키워드)
After:  높음-매우높음 (LLM 최적화 + 다국어)

개선: +50%
```

---

## 🎯 구현 우선순위

### 즉시 (Week 1)

**1. LLMQueryGenerator** (최우선)
- 동적 쿼리 생성
- 다국어 지원 (한/영)
- 코드: 300 라인

**2. MultilingualSearchEngine**
- 언어별 병렬 검색
- 결과 병합
- 코드: 200 라인

**3. 통합 테스트**
- 한국어 vs 영어 비교
- 품질 검증
- 테스트: 15개

**예상 효과**:
- 성공률: 70% → 90%+
- 품질: +50%
- 비용: ~$0.002/쿼리

---

## 💡 핵심 통찰

### Dictionary 방식의 근본적 한계

```
동의어 사전 = 정적 = 한계
  ↓
LLM 동적 생성 = 무한 확장
  ↓
Context 이해 + 도메인 적응
  ↓
언어별 최적화
```

### 다국어의 중요성

```
한국 시장:
- 한국어 검색 → 한국 특화 데이터
- 영어 검색 → 글로벌 비교 데이터
→ 둘 다 필요!

결과:
- 한국어: 정확한 한국 시장 데이터
- 영어: 국제 벤치마크
→ Cross-validation 가능
```

---

## 🚀 권장 실행 계획

### 즉시 착수

**LLM 쿼리 생성 + 다국어 검색**

**이유**:
1. ⭐⭐⭐⭐⭐ 리서치의 핵심
2. Dictionary는 근본적 한계
3. 다국어는 필수 (언어별 결과 다름)
4. LLM 인프라 이미 있음

**예상**:
- 시간: 1주
- 효과: 성공률 +25%, 품질 +50%
- ROI: 매우 높음

---

**지금 LLM 기반 동적 쿼리 생성을 구현하시겠습니까?**

이것은 리서치 품질을 근본적으로 향상시킬 핵심 기능입니다!