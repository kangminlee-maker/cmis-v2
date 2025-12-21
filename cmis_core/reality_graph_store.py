"""Reality Graph Store - R-Graph의 단일 소스

Phase A: 기본 구조 + 필터링
- RealityGraphStore (Global Reality)
- as_of 필터링
- segment 필터링

2025-12-11: World Engine Phase A
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import yaml

from .graph import InMemoryGraph, Node, Edge
from .types import RealityGraphSnapshot, EvidenceRecord


class RealityGraphStore:
    """Reality Graph 저장소 (Global Reality)

    역할:
    - 시장/산업 전체의 구조적 현실 저장
    - seed ingestion의 대상
    - domain, region, as_of 기준 인덱싱

    Phase A: 인메모리 저장
    Phase C: 파일 시스템 백엔드 + 인덱싱 + 캐싱
    """

    def __init__(
        self,
        use_backend: bool = False,
        storage_dir: Optional[Path] = None,
        *,
        project_root: Optional[Path] = None,
    ):
        """초기화

        Args:
            use_backend: 파일 시스템 백엔드 사용 여부
            storage_dir: 저장 디렉토리 (백엔드 사용 시)
            project_root: 프로젝트 루트(선택). storage_dir 미지정 시 StoragePaths 기준 기본 경로를 사용합니다.
        """
        # domain_id → InMemoryGraph 매핑 (인메모리)
        self.graphs: Dict[str, InMemoryGraph] = {}

        # Meta 정보
        self.meta: Dict[str, Dict[str, Any]] = {}

        # 백엔드 (Phase C)
        self.use_backend = use_backend
        self.backend: Optional[RealityGraphBackend] = None

        if use_backend:
            from .reality_graph_backend import RealityGraphBackend
            self.backend = RealityGraphBackend(storage_dir=storage_dir, project_root=project_root)

    def ingest_seed(self, domain_id: str, seed_path: Path) -> None:
        """Reality seed YAML → RealityGraphStore

        Args:
            domain_id: 도메인 ID
            seed_path: seed YAML 파일 경로

        Raises:
            FileNotFoundError: seed 파일이 없을 때
        """
        if not seed_path.exists():
            raise FileNotFoundError(f"Reality seed not found: {seed_path}")

        with open(seed_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        root = data.get("cmis_reality_seed", {})
        graph = InMemoryGraph()

        # Actors
        for actor in root.get("actors", []):
            actor_id = actor["actor_id"]
            node_data = {k: v for k, v in actor.items() if k != "actor_id"}

            # created_at 추가 (없으면 현재 시간)
            if "created_at" not in node_data:
                node_data["created_at"] = "1900-01-01"

            graph.upsert_node(actor_id, "actor", node_data)

        # Money Flows + Edges
        for mf in root.get("money_flows", []):
            mf_id = mf["money_flow_id"]
            payer_id = mf["payer_id"]
            payee_id = mf["payee_id"]
            quantity = mf.get("quantity", {})
            traits = mf.get("traits", {})
            recurrence = mf.get("recurrence")
            timestamp = mf.get("timestamp")

            node_data = {
                "payer_id": payer_id,
                "payee_id": payee_id,
                "quantity": quantity,
                "traits": traits,
                "recurrence": recurrence,
                "timestamp": timestamp or "1900-01-01",
            }
            graph.upsert_node(mf_id, "money_flow", node_data)

            # actor_pays_actor edge
            graph.add_edge(
                edge_type="actor_pays_actor",
                source=payer_id,
                target=payee_id,
                data={"via": mf_id}
            )

        # States
        for state in root.get("states", []):
            state_id = state["state_id"]
            node_data = {k: v for k, v in state.items() if k != "state_id"}

            # as_of 필수
            if "as_of" not in node_data:
                node_data["as_of"] = "1900-01-01"

            graph.upsert_node(state_id, "state", node_data)

        # Events (선택적)
        for event in root.get("events", []):
            event_id = event["event_id"]
            node_data = {k: v for k, v in event.items() if k != "event_id"}

            # timestamp 필수
            if "timestamp" not in node_data:
                node_data["timestamp"] = "1900-01-01"

            graph.upsert_node(event_id, "event", node_data)

        # Resources (선택적)
        for resource in root.get("resources", []):
            resource_id = resource["resource_id"]
            node_data = {k: v for k, v in resource.items() if k != "resource_id"}

            if "created_at" not in node_data:
                node_data["created_at"] = "1900-01-01"

            graph.upsert_node(resource_id, "resource", node_data)

        # 저장
        self.graphs[domain_id] = graph

        # Meta 정보
        self.meta[domain_id] = {
            "seed_path": str(seed_path),
            "domain_id": root.get("meta", {}).get("domain_id", domain_id),
            "as_of": root.get("meta", {}).get("as_of"),
            "num_actors": len(list(graph.nodes_by_type("actor"))),
            "num_money_flows": len(list(graph.nodes_by_type("money_flow"))),
            "num_states": len(list(graph.nodes_by_type("state"))),
            "lineage": {
                "from_seed": str(seed_path),
                "ingested_at": datetime.now().isoformat()
            }
        }

        # 백엔드에 저장 (Phase C)
        if self.use_backend and self.backend:
            self.backend.save_graph(domain_id, graph, self.meta[domain_id])

    def get_graph(self, domain_id: str) -> Optional[InMemoryGraph]:
        """도메인 ID로 그래프 조회

        Args:
            domain_id: 도메인 ID

        Returns:
            InMemoryGraph 또는 None
        """
        # 인메모리 우선
        if domain_id in self.graphs:
            return self.graphs[domain_id]

        # 백엔드에서 로딩
        if self.use_backend and self.backend:
            result = self.backend.load_graph(domain_id)
            if result:
                graph, meta = result
                # 인메모리에 캐싱
                self.graphs[domain_id] = graph
                self.meta[domain_id] = meta
                return graph

        return None

    def has_domain(self, domain_id: str) -> bool:
        """도메인 존재 여부

        Args:
            domain_id: 도메인 ID

        Returns:
            존재 여부
        """
        return domain_id in self.graphs

    def get_meta(self, domain_id: str) -> Dict[str, Any]:
        """도메인 Meta 정보 조회

        Args:
            domain_id: 도메인 ID

        Returns:
            Meta 정보
        """
        return self.meta.get(domain_id, {})

    def ingest_evidence(
        self,
        domain_id: str,
        evidence_list: List[EvidenceRecord]
    ) -> List[str]:
        """Evidence → R-Graph 반영

        프로세스:
        1. ActorResolver로 Actor 식별/생성
        2. EvidenceMapper로 Evidence → 노드 변환
        3. 기존 노드 업데이트 또는 신규 추가
        4. Lineage 기록

        Args:
            domain_id: 도메인 ID
            evidence_list: Evidence 리스트

        Returns:
            updated_node_ids: 업데이트된 노드 ID 리스트
        """
        from .actor_resolver import ActorResolver
        from .evidence_mapper import EvidenceMapper

        # 그래프 확보
        if not self.has_domain(domain_id):
            # 빈 그래프 생성
            self.graphs[domain_id] = InMemoryGraph()
            self.meta[domain_id] = {
                "domain_id": domain_id,
                "lineage": {
                    "from_evidence": True,
                    "created_at": datetime.now().isoformat()
                }
            }

        graph = self.graphs[domain_id]

        # ActorResolver, EvidenceMapper 초기화
        actor_resolver = ActorResolver(graph)
        evidence_mapper = EvidenceMapper(actor_resolver)

        updated_node_ids: List[str] = []

        for evidence in evidence_list:
            # Evidence → 노드 변환
            result = evidence_mapper.map_evidence(evidence)

            if result is None:
                continue  # 매핑 불가

            # 결과 타입별 처리
            if isinstance(result, list):
                nodes = result
            elif isinstance(result, Node):
                nodes = [result]
            else:
                continue

            # 노드 추가/업데이트
            for node in nodes:
                if node.type == "actor":
                    # Actor: 중복 체크 및 병합
                    existing = graph.get_node(node.id)
                    if existing:
                        # 병합
                        updated = actor_resolver.merge_actor_data(existing, evidence)
                        graph.nodes[node.id] = updated
                    else:
                        # 신규 추가
                        graph.upsert_node(node.id, node.type, node.data)

                    updated_node_ids.append(node.id)

                elif node.type in ["state", "money_flow", "event"]:
                    # State/MoneyFlow/Event: 중복 허용 (시간별 분리)
                    graph.upsert_node(node.id, node.type, node.data)
                    updated_node_ids.append(node.id)

        # Meta 업데이트
        self.meta[domain_id]["num_actors"] = len(list(graph.nodes_by_type("actor")))
        self.meta[domain_id]["num_money_flows"] = len(list(graph.nodes_by_type("money_flow")))
        self.meta[domain_id]["num_states"] = len(list(graph.nodes_by_type("state")))
        self.meta[domain_id]["last_ingested_at"] = datetime.now().isoformat()

        return updated_node_ids


def apply_as_of_filter(
    graph: InMemoryGraph,
    as_of: Optional[str]
) -> InMemoryGraph:
    """as_of 시점 기준 필터링

    규칙:
    1. State: as_of <= 요청 시점 중 가장 최신만 포함
    2. MoneyFlow: timestamp <= 요청 시점만 포함
    3. Event: timestamp <= 요청 시점만 포함
    4. Actor/Resource/Contract: created_at <= 요청 시점

    Args:
        graph: 원본 그래프
        as_of: 기준일 (None이면 필터링 안 함, "latest"면 현재 시점)

    Returns:
        필터링된 그래프
    """
    if as_of is None:
        return graph

    # "latest" 처리
    if as_of == "latest":
        as_of = datetime.now().isoformat()

    filtered_nodes: List[Node] = []
    filtered_edges: List[Edge] = []

    # State: as_of 기준 최신 버전만 (target_id별로 그룹핑)
    state_map: Dict[str, Node] = {}  # target_id → 최신 State

    for node in graph.nodes_by_type("state"):
        node_as_of = node.data.get("as_of", "1900-01-01")

        if node_as_of <= as_of:
            target_id = node.data.get("target_id", "unknown")

            # 더 최신 State가 있는지 확인
            if target_id not in state_map:
                state_map[target_id] = node
            else:
                existing_as_of = state_map[target_id].data.get("as_of", "1900-01-01")
                if node_as_of > existing_as_of:
                    state_map[target_id] = node

    filtered_nodes.extend(state_map.values())

    # MoneyFlow, Event: timestamp 필터링
    for node in graph.nodes_by_type("money_flow"):
        timestamp = node.data.get("timestamp", as_of)
        if timestamp <= as_of:
            filtered_nodes.append(node)

    for node in graph.nodes_by_type("event"):
        timestamp = node.data.get("timestamp", as_of)
        if timestamp <= as_of:
            filtered_nodes.append(node)

    # Actor, Resource, Contract: created_at 필터링
    for node_type in ["actor", "resource", "contract"]:
        for node in graph.nodes_by_type(node_type):
            created_at = node.data.get("created_at", "1900-01-01")
            if created_at <= as_of:
                filtered_nodes.append(node)

    # 필터링된 노드 ID 집합
    filtered_node_ids = {node.id for node in filtered_nodes}

    # Edge 필터링: 양쪽 노드가 모두 포함된 경우만
    for edge in graph.edges:
        if edge.source in filtered_node_ids and edge.target in filtered_node_ids:
            filtered_edges.append(edge)

    # 새 그래프 생성
    return InMemoryGraph(nodes=filtered_nodes, edges=filtered_edges)


def apply_segment_filter(
    graph: InMemoryGraph,
    segment: Optional[str]
) -> InMemoryGraph:
    """세그먼트 기준 필터링

    규칙:
    1. Actor: kind="customer_segment"이고 segment trait 일치
    2. 관련 Actor도 포함 (거래 상대방)
    3. MoneyFlow: payer 또는 payee가 해당 세그먼트
    4. State: target이 관련 Actor

    Args:
        graph: 원본 그래프
        segment: 세그먼트 (None이면 필터링 안 함)

    Returns:
        필터링된 그래프
    """
    if segment is None:
        return graph

    # 1. 해당 세그먼트 Actor 찾기
    segment_actors = []

    for actor in graph.nodes_by_type("actor"):
        # kind가 customer_segment이고 segment trait 일치
        if actor.data.get("kind") == "customer_segment":
            actor_segment = actor.data.get("traits", {}).get("segment")
            if actor_segment == segment:
                segment_actors.append(actor)

        # 또는 name/description에 segment 포함 (유연한 매칭)
        elif segment.lower() in actor.data.get("name", "").lower():
            segment_actors.append(actor)

    if not segment_actors:
        # 세그먼트 Actor가 없으면 전체 반환
        return graph

    segment_actor_ids = {actor.id for actor in segment_actors}

    # 2. 관련 Actor 확장 (거래 상대방)
    related_actor_ids = set(segment_actor_ids)

    for mf in graph.nodes_by_type("money_flow"):
        payer_id = mf.data.get("payer_id")
        payee_id = mf.data.get("payee_id")

        if payer_id in segment_actor_ids:
            related_actor_ids.add(payee_id)
        if payee_id in segment_actor_ids:
            related_actor_ids.add(payer_id)

    # 3. 필터링된 노드 수집
    filtered_nodes: List[Node] = []

    # Actor
    for actor in graph.nodes_by_type("actor"):
        if actor.id in related_actor_ids:
            filtered_nodes.append(actor)

    # MoneyFlow: 관련 Actor 간 거래
    for mf in graph.nodes_by_type("money_flow"):
        payer_id = mf.data.get("payer_id")
        payee_id = mf.data.get("payee_id")

        if payer_id in related_actor_ids or payee_id in related_actor_ids:
            filtered_nodes.append(mf)

    # State: target이 관련 Actor
    for state in graph.nodes_by_type("state"):
        target_id = state.data.get("target_id")
        if target_id in related_actor_ids:
            filtered_nodes.append(state)

    # Event, Resource (전체 포함 - 간단화)
    for node_type in ["event", "resource", "contract"]:
        filtered_nodes.extend(graph.nodes_by_type(node_type))

    # Edge 필터링
    filtered_node_ids = {node.id for node in filtered_nodes}
    filtered_edges = [
        edge for edge in graph.edges
        if edge.source in filtered_node_ids and edge.target in filtered_node_ids
    ]

    return InMemoryGraph(nodes=filtered_nodes, edges=filtered_edges)
