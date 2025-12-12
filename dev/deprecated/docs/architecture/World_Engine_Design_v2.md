# World Engine 설계 문서 v2.0

**작성일**: 2025-12-11
**버전**: 2.0 (피드백 반영 고도화)
**상태**: 설계 완료
**이전 버전**: dev/session_summary/20251211/WORLD_ENGINE_GAP_ANALYSIS.md

---

## 문서 개정 이력

**v2.0 (2025-12-11)**:
- cmis.yaml 스펙과 인터페이스 정합성 확보
- snapshot 시그니처 scope dict 기반으로 변경
- project_context_store와의 관계 명확화
- segment/as_of 필터링을 Phase A로 우선순위 상향
- ingest_evidence 타입별 변환 설계 추가
- Lineage 및 버전 관리 설계 추가

**v1.0 (2025-12-11)**:
- 초기 Gap 분석

---

## 1. World Engine 역할 및 책임

### 1.1 CMIS 아키텍처에서의 위치

```
┌──────────────────────────────────────────────────────┐
│              Cognition Plane                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │ Pattern    │  │ Value      │  │ Strategy   │    │
│  │ Engine     │  │ Engine     │  │ Engine     │    │
│  └────────────┘  └────────────┘  └────────────┘    │
│         │              │                │            │
│         └──────────────┼────────────────┘            │
│                        ▼                              │
│              ┌──────────────────┐                    │
│              │  World Engine    │ ◄─── Evidence     │
│              │  (R-Graph 빌더)  │      Engine       │
│              └──────────────────┘                    │
└──────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│            Substrate Plane                           │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ Reality Graph  │  │ Evidence Store │            │
│  │ (R-Graph)      │  │                │            │
│  └────────────────┘  └────────────────┘            │
└──────────────────────────────────────────────────────┘
```

### 1.2 핵심 책임

**cmis.yaml 정의 기준**:

WorldEngine은 Evidence와 seed를 Reality Graph(R-Graph)로 변환하고 관리하는 엔진입니다.

**구체적 책임**:
1. **R-Graph 구축**: seed YAML → R-Graph 초기 구조 생성
2. **동적 업데이트**: Evidence → R-Graph 노드/엣지 추가/수정
3. **Brownfield 지원**: Project Context → focal_actor 중심 그래프 구성
4. **서브그래프 제공**: 특정 scope/as_of/project_context에 맞는 R-Graph 서브그래프 제공
5. **Lineage 관리**: 모든 노드/엣지의 출처(seed/evidence/project_context) 추적

---

## 2. 현재 구현 상태

### 2.1 구현 완료 항목 (40%)

**✅ snapshot() 기본 기능**:
- Reality seed YAML 로딩
- Actor/MoneyFlow/State 노드 생성
- actor_pays_actor edge 생성
- domain_registry 기반 seed 파일 탐색
- Meta 정보 생성

**현재 시그니처** (v1.0):
```python
def snapshot(
    domain_id: str,
    region: str,
    segment: Optional[str] = None,
    as_of: Optional[str] = None,
    project_context_id: Optional[str] = None
) -> RealityGraphSnapshot
```

**테스트**: 5/5 통과 ✅

### 2.2 cmis.yaml 스펙과의 차이점

**⚠️ 인터페이스 불일치**:

cmis.yaml 정의:
```yaml
snapshot:
  input:
    as_of: "date"
    scope: "dict"  # { domain_id, region, segment, ... }
    project_context_id: "project_context_id (optional)"
```

canonical_workflows 호출 방식:
```yaml
- call: "world_engine.snapshot"
  with:
    as_of: "latest"
    scope:
      domain_id: "@input.domain_id"
      region: "@input.region"
      segment: "@input.segment"
```

**문제점**:
- 현재 구현은 개별 파라미터 방식
- cmis.yaml과 canonical_workflows는 scope dict 방식
- 이대로 가면 워크플로우와 구현이 점차 드리프트

---

## 3. API 설계 (cmis.yaml 정합성 확보)

### 3.1 snapshot() - 공식 스펙

**v2.0 시그니처** (cmis.yaml 준수):
```python
def snapshot(
    as_of: str,
    scope: Dict[str, Any],
    project_context_id: Optional[str] = None
) -> RealityGraphSnapshot:
    """R-Graph snapshot 생성
    
    Args:
        as_of: 기준 시점 ("latest" | "YYYY-MM-DD")
        scope: 범위 지정
            - domain_id: str (필수)
            - region: str (필수)
            - segment: Optional[str]
            - sector: Optional[str]  # 향후 확장
            - time_horizon: Optional[str]  # 향후 확장
        project_context_id: Project Context ID (Brownfield용)
    
    Returns:
        RealityGraphSnapshot
        
    Notes:
        - project_context_id가 있으면 focal_actor 중심 서브그래프 반환
        - segment가 있으면 해당 segment Actor만 포함
        - as_of에 맞는 State/MoneyFlow만 포함
    """
```

**backward-compat wrapper**:
```python
def snapshot_for_domain(
    domain_id: str,
    region: str,
    segment: Optional[str] = None,
    as_of: Optional[str] = None,
    project_context_id: Optional[str] = None
) -> RealityGraphSnapshot:
    """Backward compatibility wrapper"""
    scope = {
        "domain_id": domain_id,
        "region": region
    }
    if segment:
        scope["segment"] = segment
    
    return snapshot(
        as_of=as_of or "latest",
        scope=scope,
        project_context_id=project_context_id
    )
```

**설계 근거** (cmis.yaml 기준):
- scope dict 방식으로 향후 확장 용이 (sector, sub_region 등)
- canonical_workflows와 1:1 호환
- 다른 엔진(Evidence/Value)도 scope dict 사용 → 일관성

---

### 3.2 ingest_project_context() - 역할 명확화

**cmis.yaml 스펙**:
```yaml
ingest_project_context:
  input:
    project_context_id: "project_context_id"
  output:
    focal_actor_id: "actor_id"
    updated_node_ids: "list[node_id]"
```

**project_context_store 스키마** (cmis.yaml):
```yaml
project_context:
  fields:
    focal_actor_id:  # ⚠️ required: true, type: actor_id
    scope: dict
    baseline_state: dict
    assets_profile: dict
```

**⚠️ 구조적 모순 발견**:

1. **현재 GAP 문서 v1.0 설명**:
   - "WorldEngine이 focal_actor를 생성"
   
2. **cmis.yaml 스키마**:
   - focal_actor_id가 required → ProjectContext 생성 시 이미 있어야 함

**해결 방안 (선택 1 - 추천)**:

**ProjectContext는 focal_actor_id를 이미 알고 있다고 가정**:

```python
def ingest_project_context(
    project_context_id: str
) -> Dict[str, Any]:
    """Project Context를 R-Graph에 투영
    
    전제:
        - ProjectContext는 이미 focal_actor_id를 알고 있음
        - focal_actor는 seed나 이전 ingest_evidence로 이미 생성되어 있을 수 있음
    
    프로세스:
        1. ProjectContext 로딩 (ProjectContextStore에서)
        2. focal_actor_id 확인
        3. R-Graph에 focal_actor가 없으면:
           - focal_actor 노드 생성 (baseline_state 기반)
        4. baseline_state → State 노드 생성/업데이트
        5. assets_profile → focal_actor traits 업데이트
        6. constraints_profile → State 노드 추가
    
    Returns:
        {
            "focal_actor_id": "ACT-...",
            "updated_node_ids": ["ACT-...", "STA-...", ...]
        }
    """
```

**설계 근거**:
- ProjectContext는 "분석 주체(회사/프로젝트)"의 컨텍스트
- 생성 시점에 "어떤 Actor를 focal로 볼지" 이미 결정되어 있어야 자연스러움
- WorldEngine은 그 focal_actor 주변 그래프를 구성하는 역할에 집중

**해결 방안 (선택 2)**:

**project_context_store 스키마 수정**:
```yaml
focal_actor_id:
  type: "actor_id | null"
  required: false
```

이 경우 ProjectContext 생성 → ingest_project_context → focal_actor_id 채우기 플로우

**권장**: 선택 1 (스키마 변경 최소화, 역할 명확화)

---

### 3.3 ingest_evidence() - 타입별 변환 설계

**cmis.yaml 스펙**:
```yaml
ingest_evidence:
  input:
    evidence_ids: "list[evidence_id]"
  output:
    updated_node_ids: "list[node_id]"
```

**⚠️ 구체적 변환 로직 누락**:

현재 GAP 문서 v1.0은 러프한 아이디어만:
- Metric Evidence → State
- Search Evidence → Actor/traits
- API Evidence → MoneyFlow

**v2.0 설계: EvidenceSchema 기반 매퍼 레이어**:

```python
class EvidenceToWorldMapper(ABC):
    """Evidence → R-Graph 변환 추상 클래스"""
    
    @abstractmethod
    def can_handle(self, evidence: EvidenceRecord) -> bool:
        """이 Evidence를 처리할 수 있는지"""
        
    @abstractmethod
    def apply(
        self, 
        evidence: EvidenceRecord, 
        graph: InMemoryGraph
    ) -> List[str]:
        """Evidence를 R-Graph에 반영
        
        Returns:
            updated_node_ids
        """
```

**구체적 매퍼 예시**:

```python
class DartFilingsMapper(EvidenceToWorldMapper):
    """DART 재무제표 → R-Graph"""
    
    def apply(self, evidence, graph):
        # 1. Actor 생성/업데이트 (회사)
        actor_id = f"ACT-{evidence.metadata['corp_code']}"
        graph.upsert_node(actor_id, "actor", {
            "kind": "company",
            "name": evidence.metadata['corp_name'],
            "traits": {
                "institution_type": "public_company"
            }
        })
        
        # 2. State 노드 생성 (재무지표)
        state_id = f"STA-{actor_id}-{evidence.metadata['year']}"
        graph.upsert_node(state_id, "state", {
            "target_type": "actor",
            "target_id": actor_id,
            "as_of": evidence.metadata['year'],
            "properties": {
                "revenue": evidence.data['revenue'],
                "operating_profit": evidence.data['op_profit']
            }
        })
        
        # 3. Edge 생성
        graph.add_edge("state_applies_to_actor", state_id, actor_id)
        
        return [actor_id, state_id]


class MarketResearchMapper(EvidenceToWorldMapper):
    """시장조사 리포트 → R-Graph"""
    
    def apply(self, evidence, graph):
        # 1. State 노드 (시장 규모)
        state_id = f"STA-market-{evidence.metadata['domain_id']}"
        graph.upsert_node(state_id, "state", {
            "target_type": "market_segment",
            "target_id": evidence.metadata['domain_id'],
            "as_of": evidence.metadata['year'],
            "properties": {
                "market_size": evidence.data['market_size'],
                "growth_rate": evidence.data['growth_rate']
            }
        })
        
        # 2. Actor 노드들 (Top-N players)
        actor_ids = []
        for player in evidence.data.get('top_players', []):
            actor_id = f"ACT-{player['company_id']}"
            graph.upsert_node(actor_id, "actor", {
                "kind": "company",
                "name": player['name'],
                "traits": {
                    "market_position": player['rank']
                }
            })
            actor_ids.append(actor_id)
        
        return [state_id] + actor_ids
```

**ingest_evidence 구현**:
```python
def ingest_evidence(
    self,
    evidence_ids: List[str]
) -> Dict[str, Any]:
    """Evidence를 R-Graph에 반영
    
    프로세스:
        1. Evidence 로딩 (EvidenceStore에서)
        2. 각 Evidence의 source_id/schema로 적절한 매퍼 선택
        3. 매퍼.apply() 실행
        4. Lineage 기록
    
    Returns:
        {
            "updated_node_ids": [...],
            "lineage": {
                "from_evidence_ids": [...],
                "applied_at": "...",
                "engine_version": "..."
            }
        }
    """
    mappers = [
        DartFilingsMapper(),
        MarketResearchMapper(),
        KOSISStatisticsMapper(),
        ECOSStatisticsMapper(),
        # ...
    ]
    
    updated_nodes = []
    
    for evidence_id in evidence_ids:
        evidence = self.evidence_store.get(evidence_id)
        
        for mapper in mappers:
            if mapper.can_handle(evidence):
                nodes = mapper.apply(evidence, self.graph)
                updated_nodes.extend(nodes)
                
                # Lineage 기록
                for node_id in nodes:
                    self._add_lineage(node_id, evidence_id)
                break
    
    return {
        "updated_node_ids": list(set(updated_nodes)),
        "lineage": {...}
    }
```

**설계 근거** (cmis.yaml 기준):
- data_sources.mapping.to_evidence_schema와 자연스럽게 연결
- 새 source 추가 시 매퍼 하나 추가로 확장 용이
- ingest_evidence가 거대한 if/else 덩어리로 커지는 것 방지

---

## 4. 고급 기능 설계

### 4.1 segment/as_of 필터링 (우선순위 상향)

**⚠️ 기존 GAP v1.0 평가**: Priority 4 (낮음)

**v2.0 재평가**: **Priority 1 (Phase A 포함)**

**cmis.yaml 근거**:
- `reality_graph.time_slicing.snapshot_key: ["as_of"]` → 시간 슬라이싱 핵심 기능
- canonical_workflows에서 모든 snapshot 호출 시 segment 포함
- world_engine.snapshot notes: "baseline_state 참조 Metric/State를 R-Graph에 반영"

**최소 구현 (Phase A)**:

```python
def _filter_by_segment(
    self,
    graph: InMemoryGraph,
    segment: str
) -> InMemoryGraph:
    """segment 필터링
    
    로직:
        1. Actor.traits.segment == segment인 Actor만 포함
        2. 그 Actor와 직접 연결된 MoneyFlow/State만 포함
        3. 해당 Actor 간의 edge만 포함
    """
    filtered_graph = InMemoryGraph()
    
    # 1. segment에 해당하는 Actor 찾기
    for actor in graph.nodes_by_type("actor"):
        if actor.data.get("traits", {}).get("segment") == segment:
            filtered_graph.upsert_node(actor.id, "actor", actor.data)
    
    # 2. 연결된 MoneyFlow/State 추가
    for actor_id in [n.id for n in filtered_graph.nodes_by_type("actor")]:
        # MoneyFlow (payer/payee가 filtered actor인 경우)
        for mf in graph.nodes_by_type("money_flow"):
            if mf.data.get("payer_id") in actor_ids or \
               mf.data.get("payee_id") in actor_ids:
                filtered_graph.upsert_node(mf.id, "money_flow", mf.data)
        
        # State
        for state in graph.nodes_by_type("state"):
            if state.data.get("target_id") == actor_id:
                filtered_graph.upsert_node(state.id, "state", state.data)
    
    return filtered_graph


def _filter_by_as_of(
    self,
    graph: InMemoryGraph,
    as_of: str
) -> InMemoryGraph:
    """as_of 시점 필터링
    
    로직:
        1. State: state.as_of <= as_of 중 가장 최근 값만
        2. MoneyFlow: recurrence 기준 (연 단위 매핑)
        3. Actor: 시점 무관 (모두 포함)
    """
    filtered_graph = InMemoryGraph()
    
    as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date()
    
    # 1. Actor (시점 무관)
    for actor in graph.nodes_by_type("actor"):
        filtered_graph.upsert_node(actor.id, "actor", actor.data)
    
    # 2. State (as_of 이전, target별 최신값만)
    states_by_target = {}
    for state in graph.nodes_by_type("state"):
        state_date = datetime.strptime(state.data["as_of"], "%Y-%m-%d").date()
        
        if state_date <= as_of_date:
            target_id = state.data["target_id"]
            
            if target_id not in states_by_target or \
               state_date > states_by_target[target_id]["date"]:
                states_by_target[target_id] = {
                    "state": state,
                    "date": state_date
                }
    
    for item in states_by_target.values():
        state = item["state"]
        filtered_graph.upsert_node(state.id, "state", state.data)
    
    # 3. MoneyFlow (연도 기준 필터링)
    # 구현...
    
    return filtered_graph
```

**Phase C (고급 시계열)**:
- 여러 as_of 비교
- 시계열 변화 추적
- State 이력 관리

---

### 4.2 project_context 기반 서브그래프 추출

**cmis.yaml 근거**:
- world_engine.snapshot notes: "project_context_id가 주어지면 focal_actor 및 주변 서브그래프를 우선 포함"
- 대규모 시장에서 성능 최적화 핵심

**설계**:

```python
def _extract_subgraph_focal(
    self,
    graph: InMemoryGraph,
    focal_actor_id: str,
    n_hops: int = 2,
    edge_types: Optional[List[str]] = None
) -> InMemoryGraph:
    """focal_actor 중심 N-hop 서브그래프 추출
    
    Args:
        graph: 전체 R-Graph
        focal_actor_id: 중심 Actor
        n_hops: 탐색 깊이 (기본 2)
        edge_types: 포함할 edge 타입 (None이면 전부)
            예: ["actor_pays_actor", "actor_competes_with_actor"]
    
    Returns:
        서브그래프
    
    알고리즘:
        BFS로 focal_actor에서 n_hops만큼 탐색
        각 hop별로 edge_type 필터링
    """
    if edge_types is None:
        edge_types = [
            "actor_pays_actor",
            "actor_competes_with_actor",
            "actor_offers_resource",
            "actor_serves_actor"
        ]
    
    subgraph = InMemoryGraph()
    visited = set()
    queue = [(focal_actor_id, 0)]  # (node_id, depth)
    
    while queue:
        node_id, depth = queue.pop(0)
        
        if node_id in visited or depth > n_hops:
            continue
        
        visited.add(node_id)
        
        # 노드 추가
        node = graph.get_node(node_id)
        subgraph.upsert_node(node.id, node.type, node.data)
        
        if depth < n_hops:
            # 이웃 탐색
            for edge in graph.incident_edges(node_id):
                if edge.type in edge_types:
                    # Edge 추가
                    subgraph.add_edge(edge.type, edge.source, edge.target, edge.data)
                    
                    # 이웃 큐 추가
                    neighbor_id = edge.target if edge.source == node_id else edge.source
                    queue.append((neighbor_id, depth + 1))
        
        # 연결된 MoneyFlow/State 추가
        for mf in graph.nodes_by_type("money_flow"):
            if mf.data.get("payer_id") == node_id or \
               mf.data.get("payee_id") == node_id:
                subgraph.upsert_node(mf.id, "money_flow", mf.data)
        
        for state in graph.nodes_by_type("state"):
            if state.data.get("target_id") == node_id:
                subgraph.upsert_node(state.id, "state", state.data)
    
    return subgraph
```

**성능 고려사항**:
- N-hop 기본값: 2~3
- 최대 노드 수 budget: 1000개
- 최대 엣지 수 budget: 5000개
- Budget 초과 시 중요도 순 (MoneyFlow 금액, Actor 규모 등)

---

## 5. seed → R-Graph 변환 범위 확대

### 5.1 현재 범위 (v1.0)

**구현 완료**:
- Actor 노드
- MoneyFlow 노드
- State 노드
- actor_pays_actor edge

**cmis.yaml reality_graph 정의**:
```yaml
edge_types:
  - actor_pays_actor
  - actor_competes_with_actor
  - actor_offers_resource
  - actor_serves_actor
  - actor_has_contract_with_actor
  - event_triggers_money_flow
  - ...
```

**⚠️ Gap**: PatternEngine이 기대하는 구조의 일부만 구현

### 5.2 확장 계획

**Phase B (경쟁 구조)**:
- `actor_competes_with_actor` edge 생성
- 입력: 시장조사 리포트, 브로커리지 리서치
- PatternEngine 경쟁 구조 패턴 지원

**Phase B (가치사슬)**:
- `actor_offers_resource` edge
- `resource` 노드
- 입력: domain seed 확장

**Phase C (계약/채널)**:
- `contract` 노드
- `actor_has_contract_with_actor` edge
- `event` 노드
- `event_triggers_money_flow` edge

**설계 근거** (cmis.yaml 기준):
- PatternEngine Phase 2/3에서 value chain, competition, channel 패턴 매칭 필요
- reality_graph 스펙에 이미 정의된 primitive/edge 타입 활용

---

## 6. Lineage 및 버전 관리

### 6.1 Lineage 설계

**cmis.yaml lineage_schema 준수**:

```python
@dataclass
class NodeLineage:
    """노드 생성 출처 추적"""
    node_id: str
    created_from: str  # "seed" | "evidence" | "project_context"
    source_ids: List[str]  # seed_id, evidence_id, project_context_id
    created_at: datetime
    engine_version: str  # "world_engine_v1.0"
    confidence: Optional[float] = None


@dataclass
class RealityGraphSnapshot:
    """R-Graph Snapshot with Lineage"""
    graph: InMemoryGraph
    meta: Dict[str, Any]
    lineage: Dict[str, NodeLineage]  # node_id → lineage
```

**활용**:
- ValueEngine: "이 Metric은 어떤 Evidence 기반인가?"
- PatternEngine: "이 패턴 매칭은 어떤 현실 버전 기반인가?"
- LearningEngine: "예측과 실제 차이는 어떤 Evidence 업데이트 때문인가?"

### 6.2 R-Graph 버전 관리

**WorldUpdate 개념**:
```python
@dataclass
class WorldUpdate:
    """R-Graph 업데이트 기록"""
    update_id: str  # "UPD-..."
    kind: Literal["seed_import", "evidence_ingest", "project_context"]
    payload_id: str
    applied_at: datetime
    updated_node_ids: List[str]


@dataclass
class RealityBuildPlan:
    """Snapshot 빌드 계획"""
    as_of: str
    scope: Dict[str, Any]
    project_context_id: Optional[str]
    included_updates: List[WorldUpdate]
```

**장점**:
- "이 snapshot은 어떤 업데이트들로 만들어졌나?" 추적
- as_of 시점 재계산(replay) 가능
- Monotonic Improvability 지원

---

## 7. EvidenceEngine과의 호출 관계

### 7.1 cmis.yaml notes

```yaml
world_engine.snapshot:
  notes:
    - "필요시 EvidenceEngine 호출"
```

### 7.2 호출 패턴 결정

**Option 1: 명시적 orchestration (추천)**:
```python
# orchestrator/workflow에서
evidence_bundle = evidence_engine.fetch_for_reality_slice(scope, as_of)
world_engine.ingest_evidence(evidence_bundle.evidence_ids)
snapshot = world_engine.snapshot(as_of, scope)
```

**Option 2: snapshot이 직접 호출**:
```python
def snapshot(as_of, scope, auto_fetch_evidence=False):
    if auto_fetch_evidence:
        evidence_bundle = self.evidence_engine.fetch(...)
        self.ingest_evidence(evidence_bundle.evidence_ids)
    
    # snapshot 생성...
```

**권장**: Option 1

**이유**:
- WorldEngine이 EvidenceEngine에 강하게 의존하지 않음
- 테스트/분리도 향상
- Workflow orchestration에서 명시적 제어

---

## 8. 우선순위 및 구현 로드맵

### 8.1 Phase A: Brownfield 핵심 (1주)

**목표**: focal_actor 중심 분석 가능

**작업**:
1. **snapshot 인터페이스 정리** (1일)
   - scope dict 기반 시그니처 변경
   - backward-compat wrapper 추가
   - 테스트 업데이트

2. **segment/as_of 필터링 최소 구현** (2일)
   - _filter_by_segment() 구현
   - _filter_by_as_of() 구현
   - 테스트 5개

3. **ingest_project_context() 구현** (2일)
   - ProjectContextStore 연동
   - focal_actor 반영/생성
   - baseline_state → State 노드
   - assets_profile → Actor traits
   - 테스트 5개

4. **서브그래프 추출** (2일)
   - _extract_subgraph_focal() 구현
   - N-hop BFS 알고리즘
   - Budget 관리
   - 테스트 5개

**cmis.yaml 근거**:
- canonical_workflows.structure_analysis/opportunity_discovery 직접 지원
- pattern_engine.execution_fit 연동
- project_context_store 스키마 준수

---

### 8.2 Phase B: 동적 확장 (1-2주)

**목표**: Evidence → R-Graph 동적 반영

**작업**:
1. **EvidenceToWorldMapper 인프라** (2일)
   - 추상 클래스 정의
   - 매퍼 레지스트리

2. **타입별 매퍼 구현** (5일)
   - DartFilingsMapper
   - KOSISStatisticsMapper
   - ECOSStatisticsMapper
   - MarketResearchMapper
   - 테스트 각 2개

3. **ingest_evidence() 구현** (2일)
   - 매퍼 선택 로직
   - Lineage 기록
   - 테스트 5개

4. **경쟁 구조 edge 확장** (2일)
   - actor_competes_with_actor edge
   - seed 스키마 확장
   - 테스트 3개

**cmis.yaml 근거**:
- data_sources.mapping.to_evidence_schema 활용
- reality_graph.edge_types 확대

---

### 8.3 Phase C: 고급 기능 (1주)

**목표**: 시계열, 가치사슬, Lineage

**작업**:
1. **고급 시계열** (2일)
   - 여러 as_of 비교
   - State 이력 관리

2. **가치사슬 edge** (2일)
   - actor_offers_resource
   - resource 노드
   - contract 노드

3. **Lineage 완성** (1일)
   - NodeLineage 전체 필드
   - RealityBuildPlan 활용

4. **성능 최적화** (2일)
   - 서브그래프 인덱싱
   - 캐싱 전략

---

## 9. 테스트 전략

### 9.1 단위 테스트

**Phase A (15개)**:
- snapshot scope dict: 3개
- segment 필터링: 3개
- as_of 필터링: 3개
- ingest_project_context: 5개
- 서브그래프 추출: 5개

### 9.2 통합 테스트

**Phase B (10개)**:
- 매퍼별 테스트: 8개
- ingest_evidence 통합: 5개

### 9.3 E2E 테스트

**시나리오**:
```python
def test_brownfield_full_pipeline():
    # 1. seed 로딩
    world_engine = WorldEngine()
    
    # 2. project_context 반영
    world_engine.ingest_project_context("PRJ-001")
    
    # 3. evidence 추가
    world_engine.ingest_evidence(["EVI-DART-001", "EVI-KOSIS-002"])
    
    # 4. snapshot 생성 (focal_actor 중심, segment 필터링, as_of)
    snapshot = world_engine.snapshot(
        as_of="2025-12-01",
        scope={
            "domain_id": "Adult_Language_Education_KR",
            "region": "KR",
            "segment": "office_worker"
        },
        project_context_id="PRJ-001"
    )
    
    # 5. PatternEngine 연동
    patterns = pattern_engine.match_patterns(
        snapshot.graph,
        project_context_id="PRJ-001"
    )
    
    assert len(patterns) > 0
    assert snapshot.meta["focal_actor_id"] is not None
```

---

## 10. 주요 보강 사항 요약

### 10.1 v1.0 → v2.0 변경 사항

| 항목 | v1.0 | v2.0 | 임팩트 |
|------|------|------|--------|
| snapshot 시그니처 | 개별 파라미터 | scope dict | 상 (cmis.yaml 정합성) |
| segment/as_of 우선순위 | Priority 4 (낮음) | Phase A (높음) | 상 (시간 슬라이싱 핵심) |
| project_context 역할 | focal_actor 생성 | focal_actor 반영 | 상 (스키마 정합성) |
| ingest_evidence 설계 | 러프 아이디어 | 매퍼 레이어 | 중 (확장성) |
| seed 변환 범위 | 일부만 명시 | 확장 계획 | 중 (PatternEngine 지원) |
| Lineage | 미언급 | 상세 설계 | 중 (추적성) |
| cmis.yaml 근거 | 미약함 | 모든 항목 연결 | 중 (정당성) |

### 10.2 cmis.yaml 정합성 확보

**수정 필요 사항**:
1. ✅ snapshot 시그니처 (scope dict)
2. ✅ segment/as_of 필터링 (Phase A)
3. ✅ project_context_store 역할 명확화

**추가 설계**:
1. ✅ EvidenceToWorldMapper 레이어
2. ✅ Lineage/버전 관리
3. ✅ EvidenceEngine 호출 관계

---

## 11. 다음 단계

### 즉시 착수 (Phase A)

**1주 목표**: Brownfield 분석 완전 지원

**작업 순서**:
1. snapshot 인터페이스 정리 (scope dict)
2. segment/as_of 필터링 구현
3. ingest_project_context 구현
4. 서브그래프 추출
5. 테스트 15개 작성

**완료 후**:
- Brownfield 분석 가능
- PatternEngine execution_fit 연동
- canonical_workflows 호환

---

**작성**: 2025-12-11
**상태**: 설계 완료 (피드백 반영)
**다음**: Phase A 구현 착수
**cmis.yaml 정합성**: ✅ 확보
