"""Project Overlay Store - 프로젝트별 고유 정보

Phase A: Brownfield 지원
- ProjectOverlayStore (Per-Project)
- ingest_focal_actor_context 구현
- 서브그래프 추출

2025-12-11: World Engine Phase A
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Set
from datetime import datetime

from .graph import InMemoryGraph, Node, Edge
from .context_binding import FocalActorContextBinding


class ProjectOverlay:
    """단일 프로젝트의 Overlay

    focal_actor + baseline_state + assets_profile
    """

    def __init__(
        self,
        focal_actor_context_id: str,
        focal_actor_id: str
    ):
        """
        Args:
            focal_actor_context_id: FocalActorContext ID
            focal_actor_id: Focal Actor ID
        """
        self.focal_actor_context_id = focal_actor_context_id
        self.focal_actor_id = focal_actor_id

        # Overlay 노드/엣지
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []

    def add_node(self, node: Node) -> None:
        """노드 추가"""
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        """엣지 추가"""
        self.edges.append(edge)

    def to_graph(self) -> InMemoryGraph:
        """Overlay를 InMemoryGraph로 변환"""
        return InMemoryGraph(nodes=self.nodes, edges=self.edges)


class ProjectOverlayStore:
    """Project Overlay 저장소

    프로젝트별 focal_actor + baseline_state 저장
    """

    def __init__(self):
        """초기화"""
        # focal_actor_context_id → ProjectOverlay
        self.overlays: Dict[str, ProjectOverlay] = {}

    def create_overlay(
        self,
        focal_actor_context_id: str,
        focal_actor_id: str
    ) -> ProjectOverlay:
        """새로운 Overlay 생성

        Args:
            focal_actor_context_id: FocalActorContext ID
            focal_actor_id: Focal Actor ID

        Returns:
            ProjectOverlay
        """
        overlay = ProjectOverlay(focal_actor_context_id, focal_actor_id)
        self.overlays[focal_actor_context_id] = overlay
        return overlay

    def get_overlay(self, focal_actor_context_id: str) -> Optional[ProjectOverlay]:
        """Overlay 조회

        Args:
            focal_actor_context_id: FocalActorContext ID

        Returns:
            ProjectOverlay 또는 None
        """
        return self.overlays.get(focal_actor_context_id)

    def has_overlay(self, focal_actor_context_id: str) -> bool:
        """Overlay 존재 여부

        Args:
            focal_actor_context_id: FocalActorContext ID

        Returns:
            존재 여부
        """
        return focal_actor_context_id in self.overlays


def ingest_focal_actor_context(
    focal_context: FocalActorContextBinding,
    overlay_store: ProjectOverlayStore
) -> tuple[str, list[str]]:
    """FocalActorContext(binding) → ProjectOverlay 투영

    Args:
        focal_context: FocalActorContextBinding
        overlay_store: ProjectOverlayStore

    Returns:
        (focal_actor_id, updated_node_ids)
    """
    context_id = focal_context.context_id

    # focal_actor_id 생성
    # TODO: RealityGraphStore에서 기존 Actor 확인 (Phase B)
    focal_actor_id = focal_context.focal_actor_id or f"ACT-{context_id}"

    # Overlay 생성
    overlay = overlay_store.create_overlay(context_id, focal_actor_id)

    updated_node_ids: List[str] = []

    # 1. focal_actor 생성
    focal_actor = Node(
        id=focal_actor_id,
        type="actor",
        data={
            "name": f"Focal Actor ({context_id})",
            "kind": "company",
            "traits": {},
            "created_at": datetime.now().isoformat(),
            "lineage": {
                "from_focal_actor_context_id": context_id,
                "created_at": datetime.now().isoformat()
            }
        }
    )

    # 2. assets_profile → Actor traits 매핑
    assets_profile = focal_context.assets_profile

    # capability_traits → Actor.traits
    capability_traits = assets_profile.get("capability_traits", [])
    for cap in capability_traits:
        for key, value in cap.items():
            trait_key = f"capability_{key}"
            focal_actor.data["traits"][trait_key] = value

    # channels → Actor.traits (간단화)
    channels = assets_profile.get("channels", [])
    for ch in channels:
        channel_type = ch.get("channel_type")
        reach = ch.get("reach", 0)
        if channel_type:
            focal_actor.data["traits"][f"channel_{channel_type}_reach"] = reach

    overlay.add_node(focal_actor)
    updated_node_ids.append(focal_actor_id)

    # 3. baseline_state → State 노드
    baseline_state = focal_context.baseline_state

    if baseline_state:
        baseline_state_id = f"STATE-{context_id}-baseline"

        # baseline_state에서 properties 추출
        properties = {}
        as_of_date = baseline_state.get("as_of", datetime.now().date().isoformat())

        # 매출, 고객수 등
        if "current_revenue" in baseline_state:
            properties["revenue"] = baseline_state["current_revenue"]
        if "current_customers" in baseline_state:
            properties["n_customers"] = baseline_state["current_customers"]

        # margin_structure
        if "margin_structure" in baseline_state:
            for key, value in baseline_state["margin_structure"].items():
                properties[key] = value

        # growth_metrics
        if "growth_metrics" in baseline_state:
            for key, value in baseline_state["growth_metrics"].items():
                properties[key] = value

        # 기타 모든 필드
        for key, value in baseline_state.items():
            if key not in ["as_of", "margin_structure", "growth_metrics"]:
                if key.startswith("current_"):
                    # current_revenue → revenue
                    prop_key = key.replace("current_", "")
                    properties[prop_key] = value
                else:
                    properties[key] = value

        baseline_state_node = Node(
            id=baseline_state_id,
            type="state",
            data={
                "target_type": "actor",
                "target_id": focal_actor_id,
                "as_of": as_of_date,
                "properties": properties,
                "lineage": {
                    "from_focal_actor_context_id": context_id,
                    "created_at": datetime.now().isoformat()
                }
            }
        )
        overlay.add_node(baseline_state_node)
        updated_node_ids.append(baseline_state_id)

    # 4. brand_assets → State
    brand_assets = assets_profile.get("brand_assets", {})
    if brand_assets:
        brand_state_id = f"STATE-{context_id}-brand"
        brand_state = Node(
            id=brand_state_id,
            type="state",
            data={
                "target_type": "actor",
                "target_id": focal_actor_id,
                "as_of": datetime.now().date().isoformat(),
                "properties": brand_assets,
                "lineage": {
                    "from_focal_actor_context_id": context_id
                }
            }
        )
        overlay.add_node(brand_state)
        updated_node_ids.append(brand_state_id)

    # 5. organizational_assets → State
    org_assets = assets_profile.get("organizational_assets", {})
    if org_assets:
        org_state_id = f"STATE-{context_id}-org"
        org_state = Node(
            id=org_state_id,
            type="state",
            data={
                "target_type": "actor",
                "target_id": focal_actor_id,
                "as_of": datetime.now().date().isoformat(),
                "properties": org_assets,
                "lineage": {
                    "from_focal_actor_context_id": context_id
                }
            }
        )
        overlay.add_node(org_state)
        updated_node_ids.append(org_state_id)

    # 6. data_assets → State
    data_assets = assets_profile.get("data_assets", {})
    if data_assets:
        data_state_id = f"STATE-{context_id}-data"
        data_state = Node(
            id=data_state_id,
            type="state",
            data={
                "target_type": "actor",
                "target_id": focal_actor_id,
                "as_of": datetime.now().date().isoformat(),
                "properties": data_assets,
                "lineage": {
                    "from_focal_actor_context_id": context_id
                }
            }
        )
        overlay.add_node(data_state)
        updated_node_ids.append(data_state_id)

    return (focal_actor_id, updated_node_ids)


def merge_graphs(
    base_graph: InMemoryGraph,
    overlay: ProjectOverlay
) -> InMemoryGraph:
    """RealityGraphStore + ProjectOverlay 결합

    Args:
        base_graph: 기본 그래프 (RealityGraphStore)
        overlay: 프로젝트 Overlay

    Returns:
        결합된 그래프
    """
    # 기본 그래프의 노드/엣지 복사
    merged_nodes = list(base_graph.nodes.values())
    merged_edges = list(base_graph.edges)

    # Overlay 노드/엣지 추가
    merged_nodes.extend(overlay.nodes)
    merged_edges.extend(overlay.edges)

    return InMemoryGraph(nodes=merged_nodes, edges=merged_edges)


def extract_subgraph(
    graph: InMemoryGraph,
    focal_actor_id: str,
    n_hops: int = 2,
    included_edge_types: Optional[List[str]] = None
) -> InMemoryGraph:
    """focal_actor 중심 N-hop 서브그래프 추출

    Args:
        graph: 원본 그래프
        focal_actor_id: Focal Actor ID
        n_hops: Hop 수 (기본 2)
        included_edge_types: 포함할 엣지 타입 (None이면 전체)

    Returns:
        서브그래프
    """
    if included_edge_types is None:
        included_edge_types = [
            "actor_pays_actor",
            "actor_competes_with_actor",
            "actor_serves_actor",
            "actor_offers_resource",
            "actor_has_contract_with_actor"
        ]

    # 1. focal_actor의 직접 연결 노드 모두 포함
    subgraph_node_ids: Set[str] = {focal_actor_id}

    # State, MoneyFlow, Contract 모두 포함
    for node_type in ["state", "money_flow", "contract"]:
        for node in graph.nodes_by_type(node_type):
            # State: target_id가 focal_actor
            if node_type == "state":
                if node.data.get("target_id") == focal_actor_id:
                    subgraph_node_ids.add(node.id)

            # MoneyFlow: payer 또는 payee가 focal_actor
            elif node_type == "money_flow":
                if node.data.get("payer_id") == focal_actor_id or node.data.get("payee_id") == focal_actor_id:
                    subgraph_node_ids.add(node.id)

            # Contract: party_ids에 focal_actor 포함
            elif node_type == "contract":
                party_ids = node.data.get("party_ids", [])
                if focal_actor_id in party_ids:
                    subgraph_node_ids.add(node.id)

    # 2. N-hop BFS (Actor만)
    visited_actors: Set[str] = {focal_actor_id}
    current_hop_actors: Set[str] = {focal_actor_id}

    for hop in range(n_hops):
        next_hop_actors: Set[str] = set()

        for actor_id in current_hop_actors:
            # included_edge_types만 따라감
            for edge in graph.edges:
                if edge.type not in included_edge_types:
                    continue

                # Outgoing edges
                if edge.source == actor_id and edge.target not in visited_actors:
                    # target이 Actor인지 확인
                    target_node = graph.get_node(edge.target)
                    if target_node and target_node.type == "actor":
                        next_hop_actors.add(edge.target)
                        subgraph_node_ids.add(edge.target)

                # Incoming edges
                if edge.target == actor_id and edge.source not in visited_actors:
                    # source가 Actor인지 확인
                    source_node = graph.get_node(edge.source)
                    if source_node and source_node.type == "actor":
                        next_hop_actors.add(edge.source)
                        subgraph_node_ids.add(edge.source)

        visited_actors.update(next_hop_actors)
        current_hop_actors = next_hop_actors

        if not next_hop_actors:
            break  # 더 이상 확장할 Actor 없음

    # 3. 확장된 Actor의 MoneyFlow/State도 포함
    for node_type in ["money_flow", "state"]:
        for node in graph.nodes_by_type(node_type):
            if node_type == "money_flow":
                payer_id = node.data.get("payer_id")
                payee_id = node.data.get("payee_id")
                if payer_id in subgraph_node_ids or payee_id in subgraph_node_ids:
                    subgraph_node_ids.add(node.id)

            elif node_type == "state":
                target_id = node.data.get("target_id")
                if target_id in subgraph_node_ids:
                    subgraph_node_ids.add(node.id)

    # 4. 서브그래프 노드/엣지 수집
    subgraph_nodes = [
        node for node in graph.nodes.values()
        if node.id in subgraph_node_ids
    ]

    subgraph_edges = [
        edge for edge in graph.edges
        if edge.source in subgraph_node_ids and edge.target in subgraph_node_ids
    ]

    return InMemoryGraph(nodes=subgraph_nodes, edges=subgraph_edges)
