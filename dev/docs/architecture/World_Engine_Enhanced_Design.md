# World Engine 고도화 설계

**작성일**: 2025-12-11
**버전**: v2.0 (Enhanced)
**기반**: WORLD_ENGINE_GAP_ANALYSIS.md 피드백 반영
**상태**: 설계 완료

---

## Executive Summary

이 문서는 World Engine의 기존 Gap 분석에 다음을 추가한 고도화 설계입니다:

1. **RealityGraphStore + ProjectOverlay 구조** - 세계 모델과 프로젝트 컨텍스트 분리
2. **ingest_project_context 매핑 규칙** - ProjectContext → R-Graph 변환 명세
3. **as_of/segment 필터링 우선순위 상향** - Priority 4 → 2
4. **서브그래프 추출 규칙** - N-hop, edge 타입 명시
5. **canonical_workflows 연계** - 전체 시스템 내 역할 명확화

---

## 1. World Engine 아키텍처 (Enhanced)

### 1.1 핵심 설계 원칙

**CMIS 철학 준수**:
- **Model-first, Number-second**: R-Graph(구조) → Value(숫자)
- **Evidence-first, Prior-last**: Evidence → R-Graph → Pattern/Value
- **Graph-of-Graphs**: R(Reality) / P(Pattern) / V(Value) / D(Decision) 명확한 분리
- **Greenfield + Brownfield**: 둘 다 자연스럽게 지원

**World Engine의 단일 책임**:
- Reality Graph(R-Graph)의 **단일 소스(Single Source of Truth)**
- Evidence/Seed/ProjectContext → R-Graph 변환 및 업데이트
- snapshot() API를 통한 R-Graph 서브그래프 제공

---

### 1.2 계층 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    World Engine API                          │
│  snapshot(domain, region, segment, as_of, project_context)  │
│  ingest_evidence(evidence_ids)                               │
│  ingest_project_context(project_context_id)                  │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ RealityGraph │  │   Project    │  │  Snapshot    │
│    Store     │  │   Overlay    │  │   Builder    │
│   (Global)   │  │   Store      │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│              Reality Graph (R-Graph)                         │
│  Nodes: Actor, Event, Resource, MoneyFlow, Contract, State  │
│  Edges: actor_pays_actor, actor_competes_with, ...         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. RealityGraphStore + ProjectOverlay 구조

### 2.1 설계 개념

**핵심 아이디어**:
- **RealityGraphStore**: 도메인/지역 기준 "세계 모델" (Global Reality)
- **ProjectOverlayStore**: 프로젝트별 focal_actor + baseline_state (Per-Project)
- **SnapshotBuilder**: 두 저장소를 결합 + 필터링하여 최종 snapshot 생성

### 2.2 RealityGraphStore (Global)

**역할**:
- 시장/산업 전체의 구조적 현실 저장
- seed ingestion, ingest_evidence의 대상
- Domain, Region, Segment별 인덱싱

**저장 내용**:
```python
RealityGraphStore:
  - domain_id: "Adult_Language_Education_KR"
  - region: "KR"
  - nodes:
      - Actor: 회사, 고객 세그먼트, 파트너
      - MoneyFlow: 거래 흐름
      - State: 시장 상태, 규제 환경
      - Resource: 서비스, 상품
  - edges:
      - actor_pays_actor
      - actor_competes_with_actor
      - actor_offers_resource
  - indexes:
      - by domain_id, region, segment
      - by as_of (시간축)
      - by actor.kind
```

**생성 경로**:
1. **seed ingestion**: `_ingest_seed(yaml_path)`
   - Reality seed YAML → RealityGraphStore 초기화
   - seed도 내부적으로 "특수한 Evidence"로 취급 (lineage 기록)

2. **ingest_evidence**: Evidence → RealityGraphStore 업데이트
   - EvidenceEngine 결과를 Actor/MoneyFlow/State로 변환
   - 기존 노드 병합 또는 신규 생성

### 2.3 ProjectOverlayStore (Per-Project)

**역할**:
- 특정 프로젝트/조직의 고유 정보 저장
- Brownfield 분석 시 focal_actor 중심 뷰 제공
- RealityGraphStore와 독립적으로 업데이트 가능

**저장 내용**:
```python
ProjectOverlayStore:
  - project_context_id: "PRJ-my-company"
  - focal_actor_id: "ACT-my-company"
  - overlay_nodes:
      - Actor: focal_actor (회사 자체)
      - State: baseline_state (현재 매출, 고객 수 등)
  - overlay_traits:
      - Actor.traits: assets_profile → capability_traits
  - overlay_edges:
      - focal_actor 관련 연결
```

**생성 경로**:
- **ingest_project_context**: ProjectContext → ProjectOverlayStore
  - focal_actor 생성/업데이트
  - baseline_state → State 노드
  - assets_profile → Actor traits/edges

### 2.4 SnapshotBuilder

**역할**:
- RealityGraphStore + ProjectOverlayStore 결합
- scope, as_of, segment, project_context_id 기반 필터링
- 최종 RealityGraphSnapshot 생성

**프로세스**:
```python
def snapshot(domain, region, segment, as_of, project_context_id):
    # 1. RealityGraphStore에서 기본 그래프 로딩
    base_graph = reality_store.get_graph(
        domain=domain,
        region=region
    )
    
    # 2. as_of 필터링
    filtered_graph = apply_as_of_filter(base_graph, as_of)
    
    # 3. segment 필터링
    if segment:
        filtered_graph = apply_segment_filter(filtered_graph, segment)
    
    # 4. ProjectOverlay 적용 (Brownfield)
    if project_context_id:
        overlay = project_overlay_store.get(project_context_id)
        combined_graph = merge_graphs(filtered_graph, overlay)
        
        # 5. focal_actor 중심 서브그래프 추출
        final_graph = extract_subgraph(
            combined_graph,
            focal_actor=overlay.focal_actor_id,
            n_hops=2
        )
    else:
        final_graph = filtered_graph
    
    return RealityGraphSnapshot(graph=final_graph, meta={...})
```

### 2.5 Greenfield vs Brownfield

**Greenfield** (시장 전체 분석):
```
RealityGraphStore (domain, region)
    ↓ as_of filter
    ↓ segment filter
RealityGraphSnapshot (전체 시장)
```

**Brownfield** (우리 회사 중심):
```
RealityGraphStore (domain, region)
    ↓ as_of filter
    ↓ segment filter
    + ProjectOverlay (focal_actor, baseline_state)
    ↓ subgraph extraction (focal_actor + 2-hop)
RealityGraphSnapshot (우리 회사 중심 뷰)
```

---

## 3. ingest_project_context 매핑 규칙

### 3.1 API 시그니처

```python
def ingest_project_context(
    project_context_id: str
) -> tuple[str, list[str]]:
    """
    ProjectContext → ProjectOverlayStore 투영
    
    Returns:
        (focal_actor_id, updated_node_ids)
    """
```

### 3.2 focal_actor_id 소유권

**규칙**:
1. **ProjectContext가 소유**
   - project_context.focal_actor_id가 이미 정의되어 있으면 사용
   - 없으면 World Engine이 생성 (ACT-{project_context_id})

2. **RealityGraphStore 확인**
   - focal_actor_id가 RealityGraphStore에 이미 존재하면:
     → ProjectOverlay에서 참조만 (중복 생성 안 함)
   - 없으면:
     → ProjectOverlay에 신규 Actor 생성

3. **업데이트 정책**
   - ProjectOverlay의 focal_actor는 RealityGraphStore와 독립적
   - 학습/업데이트 시 ProjectOverlay만 수정

### 3.3 baseline_state → State 노드 매핑

**ProjectContext.baseline_state**:
```yaml
baseline_state:
  current_revenue: 12000000000  # 120억
  current_customers: 150000
  margin_structure:
    gross_margin: 0.65
    operating_margin: 0.15
  as_of: "2025-12-01"
```

**→ R-Graph State 노드**:
```python
State:
  state_id: "STATE-{project_context_id}-baseline"
  target_type: "actor"
  target_id: focal_actor_id
  as_of: "2025-12-01"
  properties:
    revenue: 12000000000
    n_customers: 150000
    gross_margin: 0.65
    operating_margin: 0.15
  traits:
    data_source: "project_context"
  lineage:
    from_project_context_id: project_context_id
```

**매핑 테이블**:
| ProjectContext 필드 | R-Graph | 노드 타입 | 속성 |
|---------------------|---------|----------|------|
| current_revenue | State | State | properties.revenue |
| current_customers | State | State | properties.n_customers |
| margin_structure.* | State | State | properties.gross_margin 등 |
| growth_metrics | State | State | properties.yoy_growth 등 |

### 3.4 assets_profile → Actor traits/edges 매핑

**ProjectContext.assets_profile**:
```yaml
assets_profile:
  capability_traits:
    - technology_domain: "AI_ML"
      maturity_level: "production_ready"
    - deployment_type: "cloud_native"
  
  channels:
    - channel_type: "online"
      reach: 100000
    - channel_type: "mobile_app"
      reach: 50000
  
  brand_assets:
    brand_awareness_level: "medium"
    brand_equity_score: 0.6
  
  organizational_assets:
    team_size: 50
    org_maturity: "scaleup"
  
  data_assets:
    customer_data_volume: 150000
```

**→ R-Graph 매핑**:

**1. capability_traits → Actor.traits**:
```python
Actor (focal_actor):
  traits:
    capability_tech_domain_AI_ML: True
    capability_maturity: "production_ready"
    capability_deployment: "cloud_native"
```

**2. channels → Resource + Edge**:
```python
# Option A: Resource 노드 생성
Resource:
  resource_id: "RES-channel-online"
  kind: "digital_service"
  traits:
    channel_type: "online"
    reach: 100000

Edge (actor_offers_resource):
  source: focal_actor_id
  target: "RES-channel-online"

# Option B: Actor traits로 단순화
Actor (focal_actor):
  traits:
    channel_online_reach: 100000
    channel_mobile_reach: 50000
```

**3. brand_assets → State**:
```python
State:
  state_id: "STATE-{project_context_id}-brand"
  target_type: "actor"
  target_id: focal_actor_id
  as_of: "2025-12-01"
  properties:
    brand_awareness_level: "medium"
    brand_equity_score: 0.6
```

**4. organizational_assets → State**:
```python
State:
  state_id: "STATE-{project_context_id}-org"
  target_type: "actor"
  target_id: focal_actor_id
  properties:
    team_size: 50
    org_maturity: "scaleup"
```

**5. data_assets → State**:
```python
State:
  state_id: "STATE-{project_context_id}-data"
  target_type: "actor"
  target_id: focal_actor_id
  properties:
    customer_data_volume: 150000
```

**매핑 규칙 요약**:
- **동적/기술 속성** → Actor.traits (capability, deployment)
- **현재 자산/상태** → State 노드 (brand, org, data)
- **관계/네트워크** → Edge (channels, partnerships)

---

## 4. snapshot 필터링 및 서브그래프 추출

### 4.1 as_of 필터링 (Priority 2)

**중요도 상향 이유**:
- canonical_workflows의 structure_analysis, opportunity_discovery가 모두 snapshot(as_of="latest")를 사용
- 시점이 섞인 그래프로 Pattern/Value 계산 시 결과 왜곡
- 시계열 분석의 기반

**필터링 규칙**:
```python
def apply_as_of_filter(graph, as_of):
    """
    as_of 시점 기준 필터링
    
    규칙:
    1. State: as_of <= 요청 시점 중 가장 최신만 포함
    2. MoneyFlow: timestamp <= 요청 시점만 포함
    3. Event: timestamp <= 요청 시점만 포함
    4. Actor/Resource/Contract: 생성일 <= 요청 시점
    """
    filtered_nodes = []
    
    for node in graph.nodes:
        if node.type == "state":
            # State는 as_of 기준 최신 버전만
            if node.data["as_of"] <= as_of:
                filtered_nodes.append(node)
        
        elif node.type in ["money_flow", "event"]:
            # 시간 속성 있는 노드
            if node.data.get("timestamp", as_of) <= as_of:
                filtered_nodes.append(node)
        
        else:
            # Actor, Resource, Contract 등
            created_at = node.data.get("created_at", "1900-01-01")
            if created_at <= as_of:
                filtered_nodes.append(node)
    
    return InMemoryGraph(nodes=filtered_nodes, edges=...)
```

**as_of="latest" 처리**:
```python
if as_of == "latest":
    as_of = datetime.now().isoformat()
```

### 4.2 segment 필터링 (Priority 2-3)

**필터링 규칙**:
```python
def apply_segment_filter(graph, segment):
    """
    세그먼트 기준 필터링
    
    규칙:
    1. Actor: kind="customer_segment"이고 segment trait 일치
    2. MoneyFlow: payer 또는 payee가 해당 세그먼트
    3. Event: 관련 Actor가 해당 세그먼트
    """
    segment_actors = [
        actor for actor in graph.nodes_by_type("actor")
        if actor.data.get("kind") == "customer_segment"
        and actor.data.get("traits", {}).get("segment") == segment
    ]
    
    segment_actor_ids = {a.id for a in segment_actors}
    
    # MoneyFlow 필터링
    relevant_money_flows = [
        mf for mf in graph.nodes_by_type("money_flow")
        if mf.data.get("payer_id") in segment_actor_ids
        or mf.data.get("payee_id") in segment_actor_ids
    ]
    
    # ...
```

### 4.3 서브그래프 추출 규칙 (Brownfield)

**기본 설정**:
```python
SUBGRAPH_EXTRACTION_RULES = {
    "n_hops": 2,  # focal_actor로부터 2-hop
    
    "included_edge_types": [
        "actor_pays_actor",
        "actor_competes_with_actor",
        "actor_serves_actor",
        "actor_offers_resource",
        "actor_has_contract_with_actor"
    ],
    
    "excluded_edge_types": [
        # 너무 먼 관계는 제외
    ],
    
    "always_include_for_focal_actor": [
        # focal_actor에 붙은 모든 노드 포함
        "state",      # 모든 State
        "money_flow", # 모든 MoneyFlow
        "contract"    # 모든 Contract
    ]
}
```

**추출 알고리즘**:
```python
def extract_subgraph(graph, focal_actor, n_hops=2):
    """
    focal_actor 중심 N-hop 서브그래프
    
    프로세스:
    1. focal_actor의 직접 연결 노드 모두 포함 (State, MoneyFlow, Contract)
    2. N-hop BFS로 Actor 확장
    3. 각 hop마다 included_edge_types만 따라감
    """
    visited = {focal_actor}
    subgraph_nodes = {focal_actor}
    current_hop = {focal_actor}
    
    # focal_actor의 State/MoneyFlow/Contract 모두 포함
    for node_type in ["state", "money_flow", "contract"]:
        related = graph.get_related_nodes(
            focal_actor,
            node_type=node_type
        )
        subgraph_nodes.update(related)
    
    # N-hop BFS
    for hop in range(n_hops):
        next_hop = set()
        
        for actor_id in current_hop:
            # included_edge_types만 따라감
            for edge_type in RULES["included_edge_types"]:
                neighbors = graph.get_neighbors(
                    actor_id,
                    edge_type=edge_type
                )
                next_hop.update(neighbors - visited)
        
        visited.update(next_hop)
        subgraph_nodes.update(next_hop)
        current_hop = next_hop
    
    return graph.subgraph(subgraph_nodes)
```

**커스터마이즈 옵션**:
```python
# snapshot에서 slice_spec 지원
snapshot(
    domain="...",
    region="...",
    project_context_id="PRJ-001",
    slice_spec={
        "n_hops": 3,  # 기본값 2 대신 3-hop
        "include_competitors": True,
        "include_suppliers": False
    }
)
```

---

## 5. ingest_evidence 구현 설계

### 5.1 Evidence → R-Graph 매핑

**Evidence 타입별 R-Graph primitive 매핑**:

| Evidence 타입 | Source | R-Graph 노드 | 속성 |
|---------------|--------|-------------|------|
| 재무제표 | DART, KR-PSTAT | State | revenue, profit, margin |
| 시장규모 | KOSIS, 리서치 | State (market) | market_size, growth_rate |
| 고객수 | 검색, API | State | n_customers |
| 회사 정보 | 검색, DB | Actor | name, kind, industry |
| 거래 데이터 | 내부 DB | MoneyFlow | quantity, recurrence |
| 경쟁 관계 | 분석 보고서 | Edge (competes) | intensity, scope |

**매핑 코드 예시**:
```python
def map_evidence_to_graph(evidence):
    """
    Evidence → R-Graph 노드/엣지 변환
    """
    if evidence.source_id == "KR_DART_filings":
        # 재무제표 → State
        return create_financial_state(
            actor_id=resolve_actor_id(evidence.context["company_name"]),
            revenue=evidence.value,
            as_of=evidence.context["fiscal_year"]
        )
    
    elif evidence.metric_id.startswith("MET-Market_size"):
        # 시장규모 → State (market segment)
        return create_market_state(
            domain=evidence.context["domain"],
            market_size=evidence.value,
            as_of=evidence.as_of
        )
    
    elif evidence.source_tier == "search":
        # 검색 Evidence → Actor 신규 생성
        return create_or_update_actor(
            name=evidence.context["company_name"],
            traits=extract_traits_from_search(evidence)
        )
```

### 5.2 Actor 식별 및 병합 (ActorResolver)

**문제**:
- 같은 회사에 대한 여러 Evidence (DART, 검색, 리서치)
- 다른 이름/ID로 중복 생성 방지

**해결책: ActorResolver**:
```python
class ActorResolver:
    """
    Actor 동일성 판별 및 병합
    """
    
    def resolve_actor_id(self, evidence_context):
        """
        Evidence context → 기존 Actor ID 또는 신규 ID
        
        우선순위:
        1. 사업자등록번호 (company_registration_number)
        2. 증권코드 (stock_code)
        3. 회사명 fuzzy matching
        """
        # 1. 사업자등록번호
        if "company_registration_number" in evidence_context:
            crn = evidence_context["company_registration_number"]
            existing = reality_store.find_actor_by_crn(crn)
            if existing:
                return existing.id
        
        # 2. 증권코드
        if "stock_code" in evidence_context:
            stock_code = evidence_context["stock_code"]
            existing = reality_store.find_actor_by_stock_code(stock_code)
            if existing:
                return existing.id
        
        # 3. Fuzzy matching
        company_name = evidence_context.get("company_name")
        similar = reality_store.find_similar_actors(company_name, threshold=0.9)
        if similar:
            return similar[0].id
        
        # 4. 신규 생성
        return generate_new_actor_id()
    
    def merge_actor_data(self, existing_actor, new_evidence):
        """
        기존 Actor + 새 Evidence 병합
        
        규칙:
        - traits: 합집합 (conflict 시 최신 우선)
        - state: 시간별 분리 (as_of 다르면 별도 State)
        """
        # traits 병합
        updated_traits = {**existing_actor.traits}
        new_traits = extract_traits_from_evidence(new_evidence)
        
        for key, value in new_traits.items():
            if key not in updated_traits:
                updated_traits[key] = value
            else:
                # Conflict: 최신 Evidence 우선
                if new_evidence.as_of > existing_actor.last_updated:
                    updated_traits[key] = value
        
        # State는 시간별 분리
        if new_evidence.as_of != existing_actor.state_as_of:
            create_new_state(actor_id, new_evidence)
        else:
            update_existing_state(actor_id, new_evidence)
```

### 5.3 Lineage 및 as_of 처리

**모든 ingest_evidence로 생성된 노드/엣지에 lineage 기록**:
```python
Actor/State/MoneyFlow:
  lineage:
    from_evidence_ids: ["EVD-001", "EVD-123"]
    created_at: "2025-12-11T10:00:00Z"
    updated_at: "2025-12-11T12:00:00Z"
    source_tiers: ["official", "research"]
```

**Evidence.as_of → State.as_of 반영**:
```python
if evidence.as_of:
    state.as_of = evidence.as_of
else:
    state.as_of = evidence.timestamp or datetime.now()
```

---

## 6. canonical_workflows와의 연계

### 6.1 structure_analysis 워크플로우

**정의** (cmis.yaml):
```yaml
structure_analysis:
  steps:
    - call: world_engine.snapshot
      with:
        as_of: "latest"
        scope:
          domain_id: "@input.domain_id"
          region: "@input.region"
          segment: "@input.segment"
    
    - call: pattern_engine.match_patterns
      with:
        graph_slice_ref: "@prev.graph_slice_ref"
    
    - call: value_engine.evaluate_metrics
      with:
        metric_requests: "@metric_sets.structure_core_economics"
```

**World Engine 역할**:
1. **snapshot() 제공**
   - domain/region/segment로 필터링된 R-Graph
   - as_of="latest"로 최신 시점 데이터
   - Greenfield: 전체 시장 구조

2. **PatternEngine 입력**
   - R-Graph의 Actor/MoneyFlow/State 구조
   - PatternEngine은 이 그래프에서 trait 기반 패턴 매칭

3. **ValueEngine 입력**
   - ValueEngine의 derived stage에서 R-Graph 참조
   - Actor 개수, MoneyFlow 총합 등 계산

**as_of 필터링이 중요한 이유**:
- structure_analysis는 "현재 시점" 구조 분석
- as_of 필터링 없으면 과거+현재 데이터가 섞임
- Pattern 매칭 시 "과거 패턴"이 현재로 오인될 수 있음

### 6.2 opportunity_discovery 워크플로우

**정의** (cmis.yaml):
```yaml
opportunity_discovery:
  steps:
    - call: world_engine.snapshot
      with:
        as_of: "latest"
        scope:
          domain_id: "@input.domain_id"
          region: "@input.region"
    
    - call: pattern_engine.discover_gaps
      with:
        graph_slice_ref: "@prev.graph_slice_ref"
```

**World Engine 역할**:
1. **snapshot() 제공** (structure_analysis와 동일)
2. **Gap Discovery 기반**
   - Context Archetype 결정 시 R-Graph의 Actor/Resource traits 사용
   - Expected Pattern vs Matched Pattern 비교

**project_context_id 지원**:
```yaml
# Brownfield 기회 발굴
opportunity_discovery:
  with:
    project_context_id: "PRJ-my-company"
```
- focal_actor 중심 서브그래프에서 Gap 탐지
- Execution Fit 계산 시 ProjectContext 활용

### 6.3 strategy_design 워크플로우 (미래)

**예상 정의**:
```yaml
strategy_design:
  steps:
    - call: world_engine.snapshot
      with:
        project_context_id: "@input.project_context_id"  # 필수
    
    - call: strategy_engine.search_strategies
      with:
        goal_id: "@input.goal_id"
        constraints: {}
```

**World Engine 역할**:
- **Brownfield 전용**
- focal_actor + baseline_state 기반 전략 설계
- ingest_project_context가 필수

**우선순위 재확인**:
- strategy_design는 ingest_project_context 없으면 작동 불가
- → ingest_project_context는 Priority 1

---

## 7. 우선순위 재조정

### 7.1 기존 우선순위 (Gap Analysis)

| Priority | 항목 | 이유 |
|----------|------|------|
| 1 | ingest_project_context | Brownfield 핵심 |
| 2 | snapshot 서브그래프 추출 | 성능 최적화 |
| 3 | ingest_evidence | 동적 확장 |
| 4 | segment/as_of 필터링 | 시급성 낮음 |

### 7.2 재조정된 우선순위

| Priority | 항목 | 이유 |
|----------|------|------|
| **1** | **ingest_project_context** | **Brownfield 핵심, strategy_design 필수** |
| **2** | **as_of 필터링** | **canonical_workflows 필수, 시계열 정합성** |
| **2.5** | **segment 필터링** | **세그먼트별 분석 지원** |
| **2.5** | **snapshot 서브그래프 추출** | **Brownfield 성능, ingest_project_context와 세트** |
| **3** | **ingest_evidence** | **동적 확장, 장기적 필수** |

### 7.3 재조정 근거

**as_of 필터링 Priority 4 → 2**:
- canonical_workflows의 모든 워크플로우가 snapshot(as_of)를 사용
- as_of 없으면 시점 섞인 그래프로 Pattern/Value 계산 → 결과 왜곡
- 시계열 분석의 기본 전제

**segment 필터링 Priority 4 → 2.5**:
- structure_analysis(segment="office_worker") 등 세그먼트별 분석 필요
- Brownfield만큼은 아니지만 실용성 높음

**서브그래프 추출 Priority 2 → 2.5**:
- ingest_project_context와 항상 같이 쓰임
- 우선순위 동일하게 유지

---

## 8. 구현 로드맵 (재조정)

### 8.1 Phase A: Brownfield + 필터링 (1.5주)

**목표**: Brownfield 분석 + canonical_workflows 완전 지원

**작업**:

**Week 1**:
1. **RealityGraphStore 구조 설계** (1일)
   - 인메모리 + 파일 시스템 백엔드
   - domain/region/as_of 인덱싱

2. **as_of 필터링 구현** (1일)
   - State, MoneyFlow, Event 시간 필터링
   - "latest" 처리

3. **segment 필터링 구현** (1일)
   - Actor.kind + segment trait 기반
   - MoneyFlow/Event 연쇄 필터링

4. **ingest_project_context 구현** (2일)
   - focal_actor_id 생성/조회
   - baseline_state → State 매핑
   - assets_profile → traits/State 매핑

**Week 2**:
5. **ProjectOverlayStore 구현** (1일)
   - ProjectContext 저장
   - Overlay 적용 로직

6. **서브그래프 추출 구현** (1.5일)
   - N-hop BFS
   - Edge 타입 필터링
   - focal_actor 중심 추출

7. **통합 테스트** (0.5일)
   - structure_analysis (Greenfield)
   - structure_analysis (Brownfield)
   - opportunity_discovery (Brownfield)

**테스트**: 15개
- as_of 필터링: 3개
- segment 필터링: 3개
- ingest_project_context: 4개
- 서브그래프 추출: 3개
- 통합: 2개

**효과**:
- ✅ canonical_workflows 완전 작동
- ✅ Brownfield 분석 가능
- ✅ strategy_design 준비 완료

---

### 8.2 Phase B: Evidence 동적 확장 (1.5주)

**목표**: EvidenceEngine → R-Graph 연동

**작업**:
1. **ActorResolver 구현** (2일)
   - 사업자등록번호/증권코드 기반 식별
   - Fuzzy matching
   - 병합 전략

2. **Evidence 타입별 매핑** (3일)
   - 재무제표 → State
   - 시장규모 → State (market)
   - 검색 → Actor 신규 생성
   - 거래 데이터 → MoneyFlow

3. **ingest_evidence 구현** (2일)
   - Evidence → R-Graph 변환
   - Conflict 해결
   - Lineage 기록

4. **통합 테스트** (1일)
   - Evidence 수집 → ingest_evidence → snapshot
   - 여러 소스 병합

**테스트**: 12개
- ActorResolver: 4개
- Evidence 매핑: 5개
- ingest_evidence: 3개

**효과**:
- ✅ seed 의존성 제거
- ✅ 실시간 데이터 반영
- ✅ Evidence-first 철학 구현

---

### 8.3 Phase C: 성능 및 고급 기능 (1주)

**목표**: 성능 최적화 및 고급 기능

**작업**:
1. **RealityGraphStore 인덱싱** (2일)
   - domain_id, region, as_of 인덱스
   - Actor.kind 인덱스
   - 쿼리 최적화

2. **slice_spec 커스터마이즈** (1일)
   - n_hops 조정
   - Edge 타입 선택

3. **시계열 지원** (2일)
   - 여러 as_of 비교
   - State 버전 관리

4. **문서화** (1일)
   - API 문서
   - 사용 예시

**테스트**: 8개

**효과**:
- ✅ 대규모 그래프 처리
- ✅ 유연한 서브그래프
- ✅ 시계열 분석

---

## 9. 설계 검증 체크리스트

### 9.1 CMIS 철학 부합성

- [x] **Model-first, Number-second**: R-Graph(구조) → Value(숫자)
- [x] **Evidence-first, Prior-last**: Evidence → R-Graph → Pattern/Value
- [x] **Graph-of-Graphs**: R/P/V/D 명확한 분리
- [x] **Greenfield + Brownfield**: 둘 다 자연스럽게 지원
- [x] **Monotonic Improvability**: Evidence 추가 → R-Graph 업데이트

### 9.2 cmis.yaml API 일치성

- [x] `snapshot(as_of, scope, project_context_id)` 시그니처
- [x] `ingest_evidence(evidence_ids)` 시그니처
- [x] `ingest_project_context(project_context_id)` 시그니처
- [x] RealityGraph 노드/엣지 타입
- [x] canonical_workflows 지원

### 9.3 다른 엔진과의 연계

- [x] **EvidenceEngine**: evidence_store → ingest_evidence
- [x] **PatternEngine**: R-Graph → trait 기반 매칭
- [x] **ValueEngine**: R-Graph → derived Metric 계산
- [x] **StrategyEngine**: ProjectContext + R-Graph → 전략 설계 (미래)
- [x] **LearningEngine**: Outcome → ProjectContext 업데이트 (미래)

### 9.4 성능/확장성

- [x] 인덱싱 전략
- [x] 서브그래프 추출
- [x] 캐싱 (snapshot 결과)
- [x] 병렬 처리 (ingest_evidence)

---

## 10. 리스크 및 완화 전략

### 10.1 RealityGraphStore 설계 복잡도

**리스크**:
- 저장소/인덱스/버전 관리 복잡도 증가

**완화**:
- Phase A에서는 인메모리 + 단순 파일 저장만 구현
- Phase C에서 본격적인 인덱싱 도입
- 초기 버전은 "세션별 휘발성" 허용

### 10.2 ActorResolver 정확도

**리스크**:
- Fuzzy matching 오류로 중복 Actor 생성 또는 잘못된 병합

**완화**:
- 우선순위 높은 식별자 (사업자등록번호, 증권코드) 우선 사용
- Fuzzy matching threshold 보수적 설정 (0.9+)
- 수동 검증 UI 제공 (Phase C)

### 10.3 as_of 필터링 누락

**리스크**:
- 초기 구현에서 as_of 필터링 누락 시 결과 재현성 깨짐

**완화**:
- Phase A에서 as_of 필터링 필수 구현
- 테스트에서 시점 섞인 그래프 시나리오 포함

---

## 11. 다음 단계

### 우선순위 1: Phase A 구현 (즉시)

**작업**:
- RealityGraphStore 설계
- as_of/segment 필터링
- ingest_project_context
- 서브그래프 추출

**예상 시간**: 1.5주

### 우선순위 2: Phase B 구현 (중기)

**작업**:
- ActorResolver
- ingest_evidence
- Evidence 타입별 매핑

**예상 시간**: 1.5주

### 우선순위 3: Phase C (장기)

**작업**:
- 성능 최적화
- 고급 기능

**예상 시간**: 1주

---

## 12. 부록: 설계 결정 사항 (ADR)

### ADR-1: RealityGraphStore + ProjectOverlay 구조

**결정**: 세계 모델과 프로젝트 컨텍스트를 별도 저장소로 분리

**이유**:
- 세계 모델(Global Reality)과 프로젝트별 정보를 논리적으로 분리
- LearningEngine이 ProjectContext 업데이트 시 RealityGraphStore 영향 최소화
- 성능 및 버전 관리 이점

**대안**:
- 단일 R-Graph에 모든 정보 저장 (복잡도 증가)
- stateless SnapshotBuilder (매번 계산 비용)

### ADR-2: as_of 필터링 우선순위 상향

**결정**: Priority 4 → 2로 상향

**이유**:
- canonical_workflows 필수 기능
- 시계열 정합성 유지
- PatternEngine/ValueEngine 결과 정확도

### ADR-3: ActorResolver 식별 우선순위

**결정**: 사업자등록번호 > 증권코드 > Fuzzy matching

**이유**:
- 공식 식별자가 가장 신뢰도 높음
- Fuzzy matching은 최후 수단

---

**작성**: 2025-12-11
**상태**: 설계 완료 (Enhanced)
**기반**: WORLD_ENGINE_GAP_ANALYSIS.md + 피드백 반영
**다음**: Phase A 구현 착수

