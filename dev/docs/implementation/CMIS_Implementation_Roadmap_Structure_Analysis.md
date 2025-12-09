---
**이력**: 2025-12-09 UMIS v9 → CMIS로 브랜드 변경
- Universal Market Intelligence → Contextual Market Intelligence
- v9 핵심 차별점 (Project Context Layer) 반영
---

# UMIS v9: structure_analysis 프로덕션 구현 로드맵

**문서 목적**: structure_analysis 워크플로우를 v7.x 품질 수준으로 프로덕션 구현하기 위한 단계별 작업 계획

**목표 결과물**: v7.x Market Reality Report (548줄) 수준의 완전한 시장 구조 분석 리포트 자동 생성

**작성일**: 2025-12-05

---

## 0. 전체 접근 전략

### 0.1 Bottom-up 구현 순서

```
[Layer 1] 인프라 (Graph/Store/Config)
    ↓
[Layer 2] 데이터 수집 (Evidence Engine)
    ↓
[Layer 3] 세계 모델 구축 (World Engine)
    ↓
[Layer 4] 값 계산 (Value Engine)
    ↓
[Layer 5] 패턴 인식 (Pattern Engine)
    ↓
[Layer 6] 검증 및 리포트 (Policy Engine + Report Generator)
    ↓
[Layer 7] 워크플로우 통합 (Workflow Executor)
    ↓
[검증] End-to-end 테스트 & v7.x 비교
```

### 0.2 품질 기준

**v7.x 대비 목표**:
- 시장규모 정확도: ±30% → **±25%**
- Evidence 추적성: 100% → **100% + 자동 lineage**
- 리포트 생성 시간: 3-5일 (수동) → **2시간 이내 (자동)**
- 재사용성: 낮음 → **R-Graph 재사용으로 다른 질문 즉시 대응**

---

## Layer 1: 인프라 (Week 1, Day 1-2)

### Task 1.1: Graph Store 영속성 구현

**현재**: InMemoryGraph (POC, 메모리만)
**목표**: 실제 DB 기반 영속 그래프 저장소

**작업 내용**:
```python
# umis_v9_core/graph_store.py (신규)
class GraphStore(ABC):
    """Graph 저장소 인터페이스"""
    def upsert_node(self, node_id, node_type, data) -> Node
    def add_edge(self, edge_type, source, target, data) -> Edge
    def query_nodes(self, filters) -> List[Node]
    def query_subgraph(self, node_ids, depth) -> Subgraph

class Neo4jGraphStore(GraphStore):
    """Neo4j 기반 구현"""
    # Cypher 쿼리 기반 구현

class SQLiteGraphStore(GraphStore):
    """SQLite 기반 구현 (개발/테스트용)"""
    # JSON 직렬화 기반 구현
```

**Deliverable**:
- `umis_v9_core/graph_store.py`
- 테스트: 1000개 노드 삽입/조회 성능 (< 1초)

**검증**:
```bash
pytest tests/test_graph_store.py
# - test_upsert_and_query
# - test_persistence (재시작 후 데이터 유지)
# - test_subgraph_query
```

---

### Task 1.2: Evidence/Value/Memory Store 구현

**목표**: Evidence/ValueRecord/Artifact 영속 저장

**작업 내용**:
```python
# umis_v9_core/stores.py (신규)
class EvidenceStore:
    """EVD-* 저장소"""
    def save_evidence(self, evidence: Evidence) -> str
    def get_evidence(self, evidence_id: str) -> Evidence
    def query_by_metadata(self, filters: dict) -> List[Evidence]

class ValueStore:
    """VAL-* 저장소"""
    def save_value_record(self, record: ValueRecord) -> str
    def get_value_record(self, value_id: str) -> ValueRecord
    def query_by_metric(self, metric_id: str, context: dict) -> List[ValueRecord]

class MemoryStore:
    """MEM-*, ART-* 저장소"""
    def save_artifact(self, artifact: Artifact) -> str
    def get_artifact(self, artifact_id: str) -> Artifact
```

**Deliverable**:
- `umis_v9_core/stores.py`
- SQLite 기반 구현 (초기)

**검증**:
```bash
pytest tests/test_stores.py
# - test_evidence_crud
# - test_value_record_lineage
# - test_artifact_retrieval
```

---

### Task 1.3: Config Loader 구현

**목표**: umis_v9.yaml 파싱 및 스펙 인덱싱

**작업 내용**:
```python
# umis_v9_core/config.py (신규)
class UMISConfig:
    """umis_v9.yaml 로더"""
    def __init__(self, config_path: str):
        self.raw_config = yaml.safe_load(...)
        self.validate()
        self.index_metrics()
        self.index_patterns()
        self.index_data_sources()
    
    def get_metric_spec(self, metric_id: str) -> MetricSpec
    def get_pattern_spec(self, pattern_id: str) -> PatternSpec
    def get_data_source(self, source_id: str) -> DataSourceSpec

class MetricSpec:
    """Metric 스펙 클래스"""
    metric_id: str
    category: str
    direct_evidence_sources: List[str]
    derived_paths: List[DerivedPath]
    resolution_protocol: dict
```

**Deliverable**:
- `umis_v9_core/config.py`
- YAML 검증 규칙 (필수 필드, 타입)

**검증**:
```python
config = UMISConfig("umis_v9.yaml")
assert len(config.metrics) >= 20
assert config.get_metric_spec("MET-SAM").resolution_protocol is not None
```

---

## Layer 2: Evidence Engine (Week 1, Day 3-5)

### Task 2.1: DART API 연동

**목표**: 한국 상장사 재무제표 자동 수집

**작업 내용**:
```python
# umis_v9_core/evidence/dart_connector.py (신규)
class DARTConnector:
    """DART 전자공시 API 연동"""
    
    def fetch_financial_statement(
        self,
        company_name: str,
        year: int
    ) -> Evidence:
        # 1. 회사 코드 검색
        corp_code = self._search_company(company_name)
        
        # 2. 재무제표 조회
        fs_data = self._fetch_fs(corp_code, year)
        
        # 3. Evidence 정규화
        return Evidence(
            evidence_id=f"EVD-DART-{corp_code}-{year}",
            source_tier="official",
            content_ref=f"DART 사업보고서 {year}",
            metadata={
                "company": company_name,
                "revenue": fs_data["revenue"],
                "operating_income": fs_data["op_income"],
                # ...
            },
            reliability=95
        )
```

**Deliverable**:
- `umis_v9_core/evidence/dart_connector.py`
- 실제 DART API 호출 성공

**검증**:
```python
dart = DARTConnector(api_key=os.getenv("DART_API_KEY"))
evidence = dart.fetch_financial_statement("YBM넷", 2023)
assert evidence.metadata["revenue"] == 817억원 (±5%)
assert evidence.reliability >= 90
```

---

### Task 2.2: 웹 검색 연동

**목표**: 비상장사 매출 정보 수집

**작업 내용**:
```python
# umis_v9_core/evidence/web_search_connector.py (신규)
class WebSearchConnector:
    """Tavily/Perplexity API 기반 웹 검색"""
    
    def search_company_revenue(
        self,
        company_name: str,
        year: int,
        domain_hint: str = None
    ) -> List[Evidence]:
        # 1. 검색 쿼리 구성
        query = f"{company_name} 매출 {year}"
        
        # 2. Tavily API 호출
        results = self.tavily_client.search(query)
        
        # 3. LLM으로 결과 파싱
        parsed = self._parse_with_llm(results, company_name, year)
        
        # 4. Evidence 생성
        return [
            Evidence(
                evidence_id=f"EVD-WEB-{hash}",
                source_tier="other",
                content_ref=result.url,
                metadata=parsed,
                reliability=self._assess_reliability(result)
            )
            for result in results
        ]
```

**Deliverable**:
- `umis_v9_core/evidence/web_search_connector.py`
- Tavily API 키 설정

**검증**:
```python
search = WebSearchConnector()
evidences = search.search_company_revenue("링글", 2024)
assert len(evidences) >= 1
assert any(e.metadata.get("revenue") for e in evidences)
```

---

### Task 2.3: KOSIS API 연동

**목표**: 통계청 인구/통계 데이터 수집

**작업 내용**:
```python
# umis_v9_core/evidence/kosis_connector.py (신규)
class KOSISConnector:
    """통계청 KOSIS API 연동"""
    
    def fetch_population_stats(
        self,
        year: int,
        age_range: str = "adult"
    ) -> Evidence:
        # KOSIS API 호출
        # 성인 인구, 가구 소득 등
```

**Deliverable**:
- `umis_v9_core/evidence/kosis_connector.py`

---

### Task 2.4: Evidence Engine 통합

**목표**: 모든 Connector를 통합하는 Evidence Engine

**작업 내용**:
```python
# umis_v9_core/evidence_engine.py (신규)
class EvidenceEngine:
    """Evidence 수집 총괄 엔진"""
    
    def __init__(self, config: UMISConfig):
        self.dart = DARTConnector()
        self.web_search = WebSearchConnector()
        self.kosis = KOSISConnector()
        self.config = config
    
    def fetch_for_metrics(
        self,
        metric_requests: List[MetricRequest],
        policy_ref: str
    ) -> EvidenceBundle:
        """Metric 계산에 필요한 Evidence 수집"""
        
        bundle = EvidenceBundle()
        
        for req in metric_requests:
            metric_spec = self.config.get_metric_spec(req.metric_id)
            
            # Direct Evidence 소스 탐색
            for source_id in metric_spec.direct_evidence_sources:
                if source_id == "KR_DART_filings":
                    evidences = self._fetch_from_dart(req)
                elif source_id == "GenericWebSearch":
                    evidences = self._fetch_from_web(req)
                # ...
                bundle.add_evidences(evidences)
        
        return bundle
```

**Deliverable**:
- `umis_v9_core/evidence_engine.py`
- 3개 Connector 통합

**검증**:
```python
engine = EvidenceEngine(config)
bundle = engine.fetch_for_metrics([
    MetricRequest("MET-Revenue", {"company": "YBM넷", "year": 2023})
])
assert len(bundle.evidences) >= 1
assert bundle.evidences[0].source_tier in ["official", "commercial", "other"]
```

---

## Layer 3: World Engine (Week 2, Day 1-2)

### Task 3.1: Evidence → R-Graph 변환 (LLM 기반)

**목표**: Evidence를 Actor/MoneyFlow/State로 자동 변환

**작업 내용**:
```python
# umis_v9_core/world_engine.py (확장)
class WorldEngine:
    """Evidence → R-Graph 변환 엔진"""
    
    def ingest_evidence(
        self,
        evidence_ids: List[str]
    ) -> List[str]:
        """Evidence를 R-Graph에 반영"""
        
        updated_nodes = []
        
        for eid in evidence_ids:
            evidence = self.evidence_store.get(eid)
            
            # LLM으로 구조 추출
            extracted = self._extract_structure(evidence)
            
            # Actor 생성/업데이트
            for actor_data in extracted.actors:
                actor_id = self.graph.upsert_node(
                    node_id=actor_data["id"],
                    node_type="actor",
                    data=actor_data
                )
                updated_nodes.append(actor_id)
            
            # MoneyFlow 생성
            for mf_data in extracted.money_flows:
                # ...
        
        return updated_nodes
    
    def _extract_structure(self, evidence: Evidence) -> ExtractedStructure:
        """LLM으로 Evidence에서 Actor/MoneyFlow 추출"""
        prompt = f"""
        다음 Evidence에서 시장 구조를 추출하세요:
        
        {evidence.content_ref}
        {evidence.metadata}
        
        추출할 것:
        - Actor (회사/고객 세그먼트)
        - MoneyFlow (누가 누구에게 얼마를)
        - State (시장 집중도/경쟁 강도 등)
        
        YAML 형식으로 반환:
        actors:
          - actor_id: ACT-...
            name: ...
            kind: company/customer_segment
            traits: ...
        """
        # Claude API 호출
```

**Deliverable**:
- `umis_v9_core/world_engine.py` 확장
- LLM 기반 구조 추출 프롬프트

**검증**:
```python
evidence_id = "EVD-DART-YBM-2023"
nodes = world_engine.ingest_evidence([evidence_id])
assert "ACT-YBM_Net" in nodes
actor = graph.get_node("ACT-YBM_Net")
assert actor.data["metadata"]["revenue"] == 817억원
```

---

### Task 3.2: snapshot() 동적 구현

**목표**: domain_registry 기반 on-demand R-Graph 구축

**작업 내용**:
```python
class WorldEngine:
    
    def snapshot(
        self,
        domain_id: str,
        region: str,
        segment: str = None,
        as_of: str = None,
        project_context_id: str = None
    ) -> RealityGraphSnapshot:
        """동적 R-Graph 스냅샷 생성"""
        
        # 1. 기존 R-Graph 확인
        existing = self._check_existing_graph(domain_id, region, as_of)
        
        if existing and self._is_fresh(existing, max_age_days=7):
            # 기존 그래프 재사용
            return existing
        
        # 2. Evidence 수집 필요
        scope = {"domain_id": domain_id, "region": region}
        evidence_bundle = self.evidence_engine.fetch_for_reality_slice(scope)
        
        # 3. R-Graph 구축
        node_ids = self.ingest_evidence(evidence_bundle.evidence_ids)
        
        # 4. Project Context 있으면 focal_actor 추가
        if project_context_id:
            project_ctx = self.project_context_store.get(project_context_id)
            self._add_focal_actor(project_ctx)
        
        # 5. Snapshot 반환
        return RealityGraphSnapshot(
            graph=self.graph.subgraph(node_ids),
            meta={
                "domain_id": domain_id,
                "as_of": as_of,
                "evidence_count": len(evidence_bundle.evidences)
            }
        )
```

**Deliverable**:
- `world_engine.snapshot()` 완전 구현
- Evidence 부족 시 자동 수집

**검증**:
```python
snapshot = world_engine.snapshot(
    domain_id="Adult_Language_Education_KR",
    region="KR"
)
assert len(snapshot.graph.nodes) >= 10  # 최소 Actor 수
assert len(snapshot.graph.edges) >= 5   # 최소 MoneyFlow 수
```

---

## Layer 4: Value Engine (Week 2, Day 3-5 + Week 3)

### Task 4.1: Metric Resolver Stage 1 (Direct Evidence)

**작업 내용**:
```python
# umis_v9_core/value_engine.py (확장)
class MetricResolver:
    """Metric 해결 4-Stage 파이프라인"""
    
    def resolve(
        self,
        metric_id: str,
        context: dict,
        policy_ref: str
    ) -> ValueRecord:
        """4-Stage로 Metric 해결"""
        
        # Stage 1: Direct Evidence
        direct_result = self._stage_1_direct(metric_id, context)
        if self._meets_quality(direct_result, policy_ref):
            return direct_result
        
        # Stage 2: Derived
        derived_result = self._stage_2_derived(metric_id, context)
        if self._meets_quality(derived_result, policy_ref):
            return derived_result
        
        # Stage 3: Prior (필요 시)
        # Stage 4: Fusion
        # ...
    
    def _stage_1_direct(self, metric_id, context) -> ValueRecord:
        """Direct Evidence에서 직접 값 추출"""
        spec = self.config.get_metric_spec(metric_id)
        
        # Evidence Engine 호출
        bundle = self.evidence_engine.fetch_for_metrics([
            MetricRequest(metric_id, context)
        ])
        
        # Evidence에서 값 추출 (LLM)
        values = self._extract_values_from_evidence(bundle, metric_id)
        
        if values:
            return self._build_value_record(
                metric_id, context, values,
                method="direct_evidence",
                lineage={"from_evidence_ids": bundle.evidence_ids}
            )
        
        return None  # Direct 실패
```

**Deliverable**:
- Stage 1 구현
- LLM 기반 값 추출

**검증**:
```python
resolver = MetricResolver(config, evidence_engine)
value = resolver._stage_1_direct("MET-Revenue", {"company": "YBM넷", "year": 2023})
assert value.point_estimate == 817억원
assert value.quality["method"] == "direct_evidence"
```

---

### Task 4.2: Metric Resolver Stage 2 (Derived - 4 Methods)

**작업 내용**:

**Method 1: Top-down**
```python
def _method_topdown(self, metric_id, context) -> ValueRecord:
    """상위 시장에서 비율로 축소"""
    
    # MET-SAM 예시
    # 1. 상위 시장 규모 찾기
    parent_market = self._find_parent_market(context)
    parent_tam = resolver.resolve(f"MET-TAM_{parent_market}", context)
    
    # 2. 세그먼트 비율 추정
    segment_share = self._estimate_segment_share(context)
    
    # 3. 계산
    sam = parent_tam.point_estimate * segment_share
    
    return ValueRecord(
        metric_id="MET-SAM",
        point_estimate=sam,
        method="top_down"
    )
```

**Method 2: Bottom-up**
```python
def _method_bottomup(self, metric_id, context) -> ValueRecord:
    """R-Graph Actor 집계"""
    
    # 1. R-Graph에서 해당 도메인 Actor 조회
    actors = self.graph.query_nodes({
        "type": "actor",
        "kind": "company",
        "traits.domain_id": context["domain_id"]
    })
    
    # 2. Actor 매출 합산
    total_revenue = sum(
        actor.metadata.get("revenue", 0)
        for actor in actors
    )
    
    # 3. 점유율 역산
    top_n_share = context.get("top_n_share", 0.35)  # 가정
    market_size = total_revenue / top_n_share
    
    return ValueRecord(
        metric_id="MET-SAM",
        point_estimate=market_size,
        method="bottom_up",
        assumptions={"top_n_share": top_n_share}
    )
```

**Method 3: Fermi**
```python
def _method_fermi(self, metric_id, context) -> ValueRecord:
    """Fermi 분해 추정"""
    
    spec = self.config.get_metric_spec(metric_id)
    fermi_hint = spec.resolution_protocol.get("fermi_decomposition")
    
    # LLM으로 Fermi 분해
    prompt = f"""
    {metric_id}를 Fermi 분해로 추정하세요.
    
    힌트: {fermi_hint}
    컨텍스트: {context}
    
    단계별 계산:
    1. 모집단 추정
    2. 참여율 추정
    3. 단가 추정
    4. 최종 계산
    """
    
    # Claude API 호출 + 계산
```

**Method 4: Proxy**
```python
def _method_proxy(self, metric_id, context) -> ValueRecord:
    """유사 시장 비교"""
    
    # 1. 유사 시장 찾기 (일본, 미국 등)
    analog_market = self._find_analog_market(context)
    
    # 2. 조정 계수 계산
    adjustment = self._calculate_adjustment_factor(
        context["region"],
        analog_market["region"]
    )
    
    # 3. 추정
    analog_value = resolver.resolve(metric_id, analog_market)
    estimated = analog_value.point_estimate * adjustment
```

**Deliverable**:
- 4-Method 모두 구현
- 각 Method별 테스트

**검증**:
```python
# Bottom-up 테스트
value = resolver._method_bottomup("MET-SAM", {"domain": "Adult_Language_KR"})
assert 8000억 <= value.point_estimate <= 12000억  # v7.x 범위
```

---

### Task 4.3: Fusion & Validation Stage

**작업 내용**:
```python
class MetricResolver:
    
    def _stage_4_fusion(
        self,
        candidates: List[ValueRecord],
        policy_ref: str
    ) -> ValueRecord:
        """4-Method 가중 평균 및 수렴 검증"""
        
        # 1. 가중 평균
        weights = self.config.get_method_weights(metric_id)
        weighted_avg = sum(
            c.point_estimate * weights[c.method]
            for c in candidates
        )
        
        # 2. 수렴 검증 (±30%)
        convergence_check = self._check_convergence(
            candidates,
            threshold=0.30
        )
        
        if not convergence_check.passed:
            # Outlier 제거
            candidates = self._remove_outliers(candidates)
            weighted_avg = self._recalculate(candidates)
        
        # 3. 최종 ValueRecord 생성
        return ValueRecord(
            metric_id=metric_id,
            point_estimate=weighted_avg,
            distribution={
                "min": min(c.point_estimate for c in candidates),
                "max": max(c.point_estimate for c in candidates)
            },
            quality={
                "method": "4_method_fusion",
                "convergence_passed": convergence_check.passed,
                "literal_ratio": self._calculate_literal_ratio(candidates)
            },
            lineage={
                "from_evidence_ids": [eid for c in candidates for eid in c.lineage["from_evidence_ids"]],
                "from_value_ids": [c.value_id for c in candidates],
                "methods_used": [c.method for c in candidates]
            }
        )
```

**Deliverable**:
- Fusion Stage 완전 구현
- 4-Method Convergence 검증

**검증**:
```python
# Adult Language 시장규모 테스트
value = resolver.resolve("MET-SAM", {"domain": "Adult_Language_KR"})
assert 7000억 <= value.point_estimate <= 13000억
assert value.quality["convergence_passed"] == True
assert len(value.lineage["from_evidence_ids"]) >= 3
```

---

### Task 4.4: 핵심 Metric 15개 구현

**우선순위 Metric**:

**Tier 1 (필수, Week 3)**:
1. MET-Revenue
2. MET-N_customers
3. MET-SAM
4. MET-TAM
5. MET-Top3_revenue_share
6. MET-HHI_revenue

**Tier 2 (중요, Week 4)**:
7. MET-Gross_margin
8. MET-Operating_margin
9. MET-ARPU
10. MET-Personnel_expenses

**Tier 3 (보조, Week 5)**:
11. MET-CAC
12. MET-LTV
13. MET-Churn_rate
14. MET-OPEX
15. MET-SOM

**각 Metric별 구현**:
- Direct Evidence 경로
- Derived 경로 (최소 2개)
- R-Graph 집계 로직
- Prior/Fermi 힌트

**Deliverable**:
- Metric별 계산 로직
- 단위 테스트

---

## Layer 5: Pattern Engine (Week 4, Day 1-2)

### Task 5.1: Pattern Graph 로딩

**작업 내용**:
```python
# umis_v9_core/pattern_engine.py (신규)
class PatternEngine:
    """패턴 인식 및 갭 탐지 엔진"""
    
    def __init__(self, config: UMISConfig):
        self.config = config
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, PatternSpec]:
        """23개 BM Pattern 로드"""
        patterns = {}
        
        # umis_v9_strategic_frameworks.yaml 등에서 로드
        # 또는 코드로 직접 정의
        
        patterns["PAT-subscription_model"] = PatternSpec(
            pattern_id="PAT-subscription_model",
            constraints={
                "required_traits": {
                    "revenue_model": ["subscription"],
                    "payment_recurs": True
                }
            }
        )
        
        # 23개 패턴 정의...
        
        return patterns
```

**Deliverable**:
- 23개 BM Pattern 정의
- PatternSpec 클래스

---

### Task 5.2: Trait 기반 패턴 매칭

**작업 내용**:
```python
class PatternEngine:
    
    def match_patterns(
        self,
        graph: InMemoryGraph,
        project_context_id: str = None
    ) -> List[PatternMatch]:
        """R-Graph에서 패턴 매칭"""
        
        matches = []
        
        for pattern_id, pattern_spec in self.patterns.items():
            # Structure Fit Score 계산
            structure_fit = self._calculate_structure_fit(
                graph,
                pattern_spec
            )
            
            # Execution Fit Score (project_context 있을 때만)
            execution_fit = None
            if project_context_id:
                project_ctx = self.project_context_store.get(project_context_id)
                execution_fit = self._calculate_execution_fit(
                    pattern_spec,
                    project_ctx
                )
            
            matches.append(PatternMatch(
                pattern_id=pattern_id,
                structure_fit_score=structure_fit,
                execution_fit_score=execution_fit,
                combined_score=structure_fit * (execution_fit or 1.0)
            ))
        
        return sorted(matches, key=lambda m: m.combined_score, reverse=True)
    
    def _calculate_structure_fit(
        self,
        graph: InMemoryGraph,
        pattern: PatternSpec
    ) -> float:
        """R-Graph Trait와 Pattern 제약 비교"""
        
        required = pattern.constraints["required_traits"]
        score = 0.0
        
        # MoneyFlow에서 revenue_model 확인
        for mf in graph.nodes_by_type("money_flow"):
            traits = mf.data.get("traits", {})
            if traits.get("revenue_model") in required.get("revenue_model", []):
                score += 1.0
        
        # 정규화
        return min(score / len(required), 1.0)
```

**Deliverable**:
- structure_fit_score 계산 로직
- 23개 패턴 매칭 테스트

**검증**:
```python
matches = pattern_engine.match_patterns(adult_language_graph)
subscription_match = next(m for m in matches if m.pattern_id == "PAT-subscription_model")
assert subscription_match.structure_fit_score >= 0.7
```

---

## Layer 6: 검증 및 리포트 (Week 5)

### Task 6.1: Policy Engine - 검증 게이트

**작업 내용**:
```python
# umis_v9_core/policy_engine.py (신규)
class PolicyEngine:
    """검증 게이트 실행 엔진"""
    
    def validate_mece(self, classification: dict) -> ValidationResult:
        """MECE 검증"""
        # Mutually Exclusive
        # Collectively Exhaustive (합계 100%)
    
    def validate_4method_convergence(
        self,
        methods: List[ValueRecord]
    ) -> ValidationResult:
        """4-Method ±30% 수렴 검증"""
        avg = statistics.mean(m.point_estimate for m in methods)
        deviations = [abs(m.point_estimate - avg) / avg for m in methods]
        
        return ValidationResult(
            passed=all(d <= 0.30 for d in deviations),
            details={"deviations": deviations}
        )
```

**Deliverable**:
- 5개 검증 게이트 구현
- umis_v9_validation_gates.yaml 기반

---

### Task 6.2: Report Generator

**작업 내용**:
```python
# umis_v9_core/report_generator.py (신규)
class ReportGenerator:
    """Markdown 리포트 생성"""
    
    def generate_market_reality_report(
        self,
        domain_id: str,
        artifacts: List[Artifact],
        value_records: List[ValueRecord],
        evidences: List[Evidence]
    ) -> str:
        """v7.x 포맷 리포트 생성"""
        
        template = self.jinja_env.get_template(
            "market_reality_report.md.j2"
        )
        
        return template.render(
            domain_id=domain_id,
            executive_summary=self._build_executive_summary(...),
            market_size=self._build_market_size_section(...),
            players=self._build_players_section(...),
            value_chain=self._build_value_chain_section(...),
            competition=self._build_competition_section(...),
            evidence_registry=self._build_evidence_registry(...),
            # 10개 섹션...
        )
```

**템플릿 작성**:
```jinja2
{# templates/market_reality_report.md.j2 #}
# Market Reality Report: {{ domain_name }}

## Executive Summary

### 핵심 수치

| 항목 | 수치 | 신뢰도 |
|------|------|--------|
| **전체 시장 규모** | **{{ market_size.total }}** | {{ market_size.reliability }}% |
{% for domain in market_size.by_domain %}
| {{ domain.name }} | {{ domain.size }} | {{ domain.reliability }}% |
{% endfor %}

## 2. 시장 규모 분석

### 2.1 4-Method Convergence

| Method | 추정치 | 신뢰도 | 가중치 |
|--------|--------|--------|--------|
{% for method in methods %}
| {{ method.name }} | {{ method.value }} | {{ method.reliability }}% | {{ method.weight }} |
{% endfor %}

**근거**:
{% for evidence in evidences %}
- {{ evidence.id }}: {{ evidence.description }}
{% endfor %}

...
```

**Deliverable**:
- Jinja2 템플릿 엔진
- v7.x 포맷 템플릿 (10개 섹션)

---

## Layer 7: 워크플로우 통합 (Week 6)

### Task 7.1: Workflow Executor

**작업 내용**:
```python
# umis_v9_core/workflow_executor.py (신규)
class WorkflowExecutor:
    """Phase 1-14 오케스트레이션"""
    
    def execute_structure_analysis(
        self,
        domain_id: str,
        region: str,
        output_path: str
    ) -> WorkflowResult:
        """structure_analysis 전체 실행"""
        
        print("Phase 1: 시장 정의...")
        ph01_output = self._execute_phase_01(domain_id, region)
        
        print("Phase 2: 도메인 분류...")
        ph02_output = self._execute_phase_02(ph01_output)
        
        # ...
        
        print("Phase 7: 시장규모 추정...")
        ph07_output = self._execute_phase_07(snapshot, metric_requests)
        
        # ...
        
        print("Phase 14: 리포트 생성...")
        report = self.report_generator.generate_market_reality_report(...)
        
        with open(output_path, "w") as f:
            f.write(report)
        
        return WorkflowResult(
            success=True,
            output_path=output_path,
            evidence_count=len(evidences),
            value_records_count=len(value_records)
        )
```

**Deliverable**:
- Workflow Executor
- Phase별 실행 로직

---

## 검증 단계 (Week 7)

### Task 8.1: End-to-end 테스트

**실행**:
```bash
python run_structure_analysis.py \
  --domain Adult_Language_Education_KR \
  --region KR \
  --output output/Market_Reality_Report_v9.md
```

**예상 출력**:
```
Phase 1: 시장 정의... ✓ (1분)
Phase 2: 도메인 분류... ✓ (30초)
Phase 3-4: BM 분류... ✓ (2분)
Phase 5: 플레이어 식별...
  - DART API: YBM넷 817억 수집 ✓
  - 웹 검색: 링글 200억 수집 ✓
  - 웹 검색: 야나두 430억 수집 ✓
  - Total: 25개 Evidence ✓ (5분)
Phase 6: 가치사슬... ✓ (2분)
Phase 7: 시장규모 추정...
  - Method 1 (Top-down): 1,500억
  - Method 2 (Bottom-up): 10,000억
  - Method 3 (Fermi): 13,000억
  - Method 4 (Proxy): 18,000억
  - Convergence: PASS (±30%)
  - Final: 10,000억 ✓ (10분)
Phase 8-11: 경쟁구조... ✓ (5분)
Phase 12: MECE 검증... ✓
Phase 13: 3자 검증... ✓
Phase 14: 리포트 생성... ✓

총 소요 시간: 30분
출력: output/Market_Reality_Report_v9.md (520줄)
```

---

### Task 8.2: v7.x 비교 검증

**비교 항목**:

| 항목 | v7.x | v9 목표 | 검증 방법 |
|------|------|---------|----------|
| 시장규모 정확도 | ±30% | ±25% | 수치 범위 비교 |
| Evidence 개수 | 25개 | 25개+ | Evidence Store 카운트 |
| 추적성 | 100% (수동 ID) | 100% (자동 lineage) | lineage 필드 검증 |
| Top 플레이어 커버 | 50+ | 50+ | Actor 노드 개수 |
| 리포트 길이 | 548줄 | 500줄+ | Markdown 라인 수 |
| 소요 시간 | 3-5일 | 2시간 이내 | 실행 시간 측정 |

**검증 스크립트**:
```python
# tests/test_v7_comparison.py
def test_market_size_accuracy():
    v7_sam = 10000억
    v9_sam = run_structure_analysis("Adult_Language_KR").get_metric("MET-SAM")
    
    deviation = abs(v9_sam - v7_sam) / v7_sam
    assert deviation <= 0.25  # ±25%

def test_traceability():
    report = run_structure_analysis("Adult_Language_KR")
    
    for value_record in report.value_records:
        assert len(value_record.lineage["from_evidence_ids"]) >= 1
        # 모든 숫자에 근거 존재
```

---

## 작업 순서 요약 (7주 계획)

**Week 1**: 인프라 + Evidence Engine
- Day 1-2: Graph/Store 영속성
- Day 3-5: DART/웹검색/KOSIS 연동

**Week 2**: World Engine
- Day 1-2: Evidence → R-Graph 변환
- Day 3-5: snapshot() 동적 구현

**Week 3**: Value Engine (Tier 1 Metric)
- Day 1-2: Stage 1-2 (Direct + Derived)
- Day 3-5: Stage 3-4 (Fusion + Validation) + Tier 1 Metric 6개

**Week 4**: Value Engine (Tier 2-3) + Pattern Engine
- Day 1-2: Tier 2-3 Metric 9개
- Day 3-5: Pattern Engine (23개 패턴 매칭)

**Week 5**: 검증 및 리포트
- Day 1-2: Policy Engine (검증 게이트)
- Day 3-5: Report Generator (Jinja2 템플릿)

**Week 6**: 워크플로우 통합
- Day 1-5: Workflow Executor (Phase 1-14 오케스트레이션)

**Week 7**: 검증 및 개선
- Day 1-3: End-to-end 테스트
- Day 4-5: v7.x 비교 및 품질 개선

---

## 다음 단계

**지금 시작할 수 있는 것**:
1. Task 1.1 (Graph Store 영속성) 구현 시작
2. requirements.txt에 의존성 추가 (neo4j, sqlite3, jinja2, tavily-python 등)
3. 테스트 프레임워크 설정 (pytest)

**시작하시겠습니까?**
