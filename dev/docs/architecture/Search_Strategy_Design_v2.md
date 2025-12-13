# 검색 전략 설계 v2.0 (피드백 반영)

**작성일**: 2025-12-10
**버전**: v2.0 (SearchPlanner 중심)
**기반**: Search_Query_Enhancement_Strategy.md + 피드백

---

## 📋 피드백 반영 사항

### ✅ 추가된 계층

1. **SearchPlanner** - Metric/DataSource/Policy 연계
2. **SearchContext** - 통합 Context 모델
3. **SearchPlan/SearchStep** - 실행 계획
4. **QueryResultQuality** - 품질 평가 구조화
5. **memory_store 연동** - QueryLearner 통합

### ✅ 책임 분리

- SearchPlanner: Plan 생성
- SearchExecutor: Plan 실행
- EvidenceBuilder: EvidenceRecord 조립

---

## 🏗️ 아키텍처 (재설계)

### 전체 구조

```
EvidenceEngine (Facade)
    ↓
SearchPlanner (신규)
  - uses: metric_spec, data_sources, policy
  - outputs: SearchPlan
    ↓
SearchExecutor (개선)
  - uses: SearchPlan, QueryExpansionEngine, LLMQueryGenerator
  - outputs: RawSearchResults
    ↓
EvidenceBuilder (신규)
  - uses: RawSearchResults, MetricRequest
  - outputs: EvidenceRecord(s)
    ↓
QueryLearner
  - uses: memory_store.query_trace
  - updates: SearchStrategySpec
```

---

## 📊 핵심 컴포넌트

### 1. SearchContext (신규)

```python
@dataclass
class SearchContext:
    """검색 Context (통합 모델)"""

    # 기본
    domain_id: str
    region: str
    metric_id: str
    year: int

    # 언어 (다국어 검색)
    language: str  # "ko", "en", "auto"

    # 정책
    policy_mode: str  # "reporting_strict", "decision_balanced", "exploration_friendly"

    # 선택적
    data_source_id: Optional[str] = None
    segment: Optional[str] = None

    # Budget
    max_queries: int = 5
    max_total_time: int = 30  # seconds
    max_cost_per_metric: float = 0.01  # USD
```

---

### 2. SearchPlan & SearchStep (신규)

```python
@dataclass
class SearchStep:
    """검색 단계"""
    data_source_id: str
    base_query_template: str
    use_llm_query: bool
    num_queries: int  # 이 step에서 생성할 쿼리 개수
    languages: List[str]  # ["ko", "en"]
    timeout_sec: int
    priority: int  # Step 우선순위

@dataclass
class SearchPlan:
    """검색 계획"""
    metric_id: str
    context: SearchContext
    steps: List[SearchStep]
    total_budget: Dict[str, Any]  # {"max_queries": 10, "max_time": 30}
```

**예시**:
```python
# MET-TAM, region=KR, exploration_friendly
plan = SearchPlan(
    metric_id="MET-TAM",
    context=SearchContext(...),
    steps=[
        SearchStep(
            data_source_id="Commercial_Market_Research",
            base_query_template="{domain} {region} market size {year}",
            use_llm_query=False,  # 템플릿만
            num_queries=1,
            languages=["en"],
            priority=1
        ),
        SearchStep(
            data_source_id="GenericWebSearch",
            base_query_template="{domain} {region} TAM {year}",
            use_llm_query=True,  # LLM 확장
            num_queries=5,
            languages=["ko", "en"],  # 다국어
            priority=2
        )
    ]
)
```

---

### 3. SearchPlanner (신규)

```python
class SearchPlanner:
    """검색 계획 수립

    역할:
    - Metric/DataSource/Policy 기반 SearchPlan 생성
    - 언어 결정
    - Budget 할당
    """

    def __init__(self, config: CMISConfig):
        self.config = config
        self.strategy_spec = self._load_search_strategy_spec()

    def build_plan(
        self,
        metric_request: MetricRequest,
        policy_ref: str
    ) -> SearchPlan:
        """SearchPlan 생성

        Args:
            metric_request: Metric 요청
            policy_ref: 정책

        Returns:
            SearchPlan
        """
        metric_id = metric_request.metric_id
        context_dict = metric_request.context

        # 1. SearchContext 생성
        search_context = SearchContext(
            domain_id=context_dict.get("domain_id", ""),
            region=context_dict.get("region", "KR"),
            metric_id=metric_id,
            year=context_dict.get("year", 2024),
            language=self._determine_language(context_dict),
            policy_mode=policy_ref
        )

        # 2. MetricSpec 조회
        metric_spec = self.config.metrics.get(metric_id)

        if not metric_spec:
            # Fallback
            return self._create_generic_plan(search_context)

        # 3. direct_evidence_sources 기반 SearchStep 생성
        steps = []

        for source_id in metric_spec.direct_evidence_sources:
            step = self._create_search_step(
                source_id,
                metric_id,
                search_context,
                policy_ref
            )
            steps.append(step)

        # 4. Policy 기반 조정
        steps = self._adjust_by_policy(steps, policy_ref)

        return SearchPlan(
            metric_id=metric_id,
            context=search_context,
            steps=steps
        )

    def _determine_language(self, context):
        """언어 결정 (다국어 전략)"""
        region = context.get("region", "")

        # 한국: ko 우선
        if region in ["KR", "한국"]:
            return "auto"  # ko + en 모두
        elif region in ["JP", "일본"]:
            return "auto"  # ja + en
        else:
            return "en"

    def _create_search_step(
        self,
        source_id: str,
        metric_id: str,
        context: SearchContext,
        policy_ref: str
    ) -> SearchStep:
        """Source별 SearchStep 생성"""

        # SearchStrategySpec 조회
        strategy = self.strategy_spec.get(metric_id, {}).get(source_id, {})

        # Policy 기반 LLM 사용 여부
        use_llm = (
            policy_ref in ["exploration_friendly", "decision_balanced"] and
            source_id in ["GenericWebSearch", "Academic_Papers"]
        )

        # 언어 결정
        if context.language == "auto" and source_id == "GenericWebSearch":
            languages = ["ko", "en"]  # 다국어
        else:
            languages = ["en"]

        return SearchStep(
            data_source_id=source_id,
            base_query_template=strategy.get("template", "{domain} {region} {metric} {year}"),
            use_llm_query=use_llm,
            num_queries=3 if use_llm else 1,
            languages=languages,
            timeout_sec=30,
            priority=1
        )

    def _adjust_by_policy(self, steps, policy_ref):
        """Policy 기반 조정"""
        if policy_ref == "reporting_strict":
            # 쿼리 수 제한, LLM 최소화
            for step in steps:
                step.num_queries = min(step.num_queries, 2)
                step.use_llm_query = False

        elif policy_ref == "exploration_friendly":
            # 쿼리 수 증가, LLM 적극 활용
            for step in steps:
                step.num_queries = min(step.num_queries * 2, 10)

        return steps
```

---

### 4. SearchExecutor (개선)

```python
class SearchExecutor:
    """SearchPlan 실행

    역할:
    - SearchStep 순차 실행
    - QueryExpansionEngine/LLMQueryGenerator 조율
    - Raw 결과 수집
    """

    def __init__(self):
        self.query_expansion = QueryExpansionEngine()
        self.llm_generator = LLMQueryGenerator()

    def execute(
        self,
        plan: SearchPlan
    ) -> List[RawSearchResult]:
        """SearchPlan 실행

        Args:
            plan: SearchPlan

        Returns:
            RawSearchResult 리스트
        """
        all_results = []

        for step in plan.steps:
            # 1. 쿼리 생성
            if step.use_llm_query:
                # LLM 동적 생성
                queries = self.llm_generator.generate_multilingual_queries(
                    plan.context,
                    step.languages,
                    step.num_queries
                )
            else:
                # 템플릿 기반
                queries = {
                    "en": [step.base_query_template.format(
                        domain=plan.context.domain_id,
                        region=plan.context.region,
                        metric=plan.context.metric_id,
                        year=plan.context.year
                    )]
                }

            # 2. 언어별 검색 실행
            for lang, lang_queries in queries.items():
                for query in lang_queries:
                    try:
                        result = self._execute_single_query(
                            query,
                            lang,
                            step.data_source_id,
                            step.timeout_sec
                        )

                        if result:
                            all_results.append(result)

                    except Exception as e:
                        print(f"Query failed: {query} - {e}")
                        continue

        return all_results

    def _execute_single_query(
        self,
        query: str,
        language: str,
        source_id: str,
        timeout: int
    ) -> Optional[RawSearchResult]:
        """단일 쿼리 실행"""
        # Source에서 검색
        # RawSearchResult 반환
```

---

### 5. EvidenceBuilder (신규)

```python
class EvidenceBuilder:
    """Raw 검색 결과 → EvidenceRecord 변환

    역할:
    - 숫자 추출
    - 품질 평가
    - EvidenceRecord 조립
    """

    def from_search_results(
        self,
        raw_results: List[RawSearchResult],
        metric_request: MetricRequest
    ) -> List[EvidenceRecord]:
        """RawSearchResult → EvidenceRecord

        Args:
            raw_results: 검색 결과들
            metric_request: Metric 요청

        Returns:
            EvidenceRecord 리스트
        """
        evidence_records = []

        for result in raw_results:
            # 1. 숫자 추출
            numbers = self.extract_numbers(result.content)

            if not numbers:
                continue

            # 2. 품질 평가
            quality = self.evaluate_quality(
                result,
                numbers,
                metric_request
            )

            # 3. Consensus
            value, confidence = self.calculate_consensus(numbers)

            # 4. EvidenceRecord 생성
            record = EvidenceRecord(
                evidence_id=f"EVD-Search-{uuid.uuid4().hex[:8]}",
                source_tier="commercial",
                source_id=result.source_id,
                value=value,
                confidence=confidence,
                metadata={
                    "query": result.query,
                    "language": result.language,
                    "quality": quality,
                    "hints": self._extract_hints(result, numbers)
                }
            )

            evidence_records.append(record)

        return evidence_records
```

---

### 6. QueryResultQuality (신규)

```python
@dataclass
class QueryResultQuality:
    """쿼리 결과 품질 평가"""
    score: float  # 0.0 ~ 1.0

    # 기본 지표
    has_numbers: bool
    num_numbers: int
    year_match: bool

    # Source
    source_tier: str
    source_id: str

    # 언어
    language: str
    query: str

    # 평가 상세
    metric_relevance: float  # LLM 평가
    temporal_relevance: float  # 연도 일치도
    numeric_confidence: float  # 숫자 신뢰도

    # 메타
    notes: Dict[str, Any] = field(default_factory=dict)
```

---

### 7. SearchStrategySpec (YAML)

```yaml
# config/search_strategy_spec.yaml
# Metric별 × DataSource별 검색 전략

strategies:
  MET-TAM:
    per_source:
      Commercial_Market_Research:
        template: "{domain} {region} total addressable market {year}"
        use_llm: false
        num_queries: 1
        languages: [en]

      GenericWebSearch:
        template: "{domain} {region} market size {year}"
        use_llm: true  # LLM 확장
        num_queries: 5
        languages: [ko, en]  # 다국어

      Academic_Papers:
        template: "{domain} market analysis {year}"
        use_llm: true
        num_queries: 3
        languages: [en]

  MET-Revenue:
    per_source:
      KR_DART_filings:
        template: "{company_name} {year} revenue"
        use_llm: false
        num_queries: 1

      GenericWebSearch:
        template: "{domain} {region} revenue {year}"
        use_llm: true
        num_queries: 3
        languages: [ko, en]

# Policy별 기본 전략
policy_defaults:
  reporting_strict:
    max_queries_per_metric: 3
    use_llm: false
    max_time: 10

  decision_balanced:
    max_queries_per_metric: 5
    use_llm: true
    max_time: 20

  exploration_friendly:
    max_queries_per_metric: 10
    use_llm: true
    max_time: 30
```

---

### 8. QueryLearner ↔ memory_store 연동

```python
class QueryLearner:
    """쿼리 성능 학습

    memory_store 활용:
    - query_trace → 쿼리 성능 기록
    - 학습 결과 → SearchStrategySpec 업데이트
    """

    def record_query_result(
        self,
        query: str,
        language: str,
        metric_id: str,
        domain: str,
        success: bool,
        quality: QueryResultQuality
    ):
        """쿼리 결과 기록 (memory_store)"""

        memory_record = {
            "memory_type": "query_trace",
            "related_ids": {
                "metric_id": metric_id,
                "domain_id": domain
            },
            "content": {
                "query": query,
                "language": language,
                "success": success,
                "quality_score": quality.score,
                "timestamp": datetime.now().isoformat()
            }
        }

        # memory_store에 저장
        self.memory_store.save(memory_record)

    def learn_patterns(
        self,
        metric_id: str,
        domain: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """성공 패턴 학습

        Args:
            metric_id: Metric ID
            domain: Domain
            lookback_days: 학습 기간

        Returns:
            {
                "best_language": "ko",
                "best_query_patterns": [...],
                "avg_success_rate": 0.85
            }
        """
        # memory_store에서 query_trace 조회
        traces = self.memory_store.query(
            memory_type="query_trace",
            related_metric_id=metric_id,
            since=lookback_days
        )

        # 패턴 분석
        # ...
```

---

## 🎯 통합 플로우 (최종)

### EvidenceEngine.fetch_for_metrics() 내부

```python
def fetch_for_metrics(metric_requests, policy_ref):
    """
    1. SearchPlanner → SearchPlan 생성
       - metric_spec 참조
       - data_sources 참조
       - policy 반영
       - 언어 결정

    2. SearchExecutor → SearchPlan 실행
       - QueryExpansionEngine (동의어, 순서)
       - LLMQueryGenerator (동적 생성, 다국어)
       - 언어별 병렬 검색
       - RawSearchResults 수집

    3. EvidenceBuilder → EvidenceRecord 조립
       - 숫자 추출
       - QueryResultQuality 평가
       - Hints 저장
       - EvidenceRecord 생성

    4. QueryLearner → 성능 기록
       - memory_store에 query_trace 저장
       - 주기적 학습 → SearchStrategySpec 개선
    """
```

---

## 📊 개선 효과

### Before (v1.0)

```
EvidenceEngine
  └ BaseSearchSource
      └ build_search_query() (단순)
          → 1개 쿼리, 영어만
```

**문제**:
- Metric/Policy 무시
- 1개 쿼리만
- 책임 과다

---

### After (v2.0)

```
EvidenceEngine
  └ SearchPlanner (신규)
      ├ SearchContext (신규)
      ├ SearchPlan (신규)
      └ SearchStrategySpec (YAML)
  └ SearchExecutor
      ├ QueryExpansionEngine
      ├ LLMQueryGenerator (다국어)
      └ 병렬 실행
  └ EvidenceBuilder (신규)
      ├ 숫자 추출
      ├ QueryResultQuality (신규)
      └ EvidenceRecord 조립
  └ QueryLearner
      └ memory_store 연동 (신규)
```

**개선**:
- ✅ Metric/DataSource/Policy 연계
- ✅ 10-15개 쿼리 (다국어)
- ✅ 책임 분리
- ✅ 학습 가능

---

## 🔧 구현 우선순위

### Phase 1: 핵심 구조 (1주)

1. **SearchContext** dataclass
2. **SearchPlan/SearchStep** dataclass
3. **SearchPlanner** (기본)
4. **search_strategy_spec.yaml**

### Phase 2: 동적 확장 (1주)

5. **LLMQueryGenerator** (다국어)
6. **SearchExecutor** (병렬)
7. **EvidenceBuilder** (분리)

### Phase 3: 학습 (1주)

8. **QueryResultQuality** 구조화
9. **QueryLearner** ↔ memory_store

---

**작성**: 2025-12-10
**결론**: SearchPlanner 중심 재설계 완료
**다음**: Phase 1 구현 착수?


