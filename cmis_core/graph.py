"""CMIS In-Memory Graph Implementation

Simple in-memory graph for R-Graph POC and v1 implementation.
Based on umis_v9.yaml#substrate_plane.graphs.reality_graph schema.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Literal

# Import from types.py (v9 공통 타입)
from .types import Node, Edge


class InMemoryGraph:
  """아주 단순한 인메모리 그래프 구현 (R-Graph POC용).

  - node는 id/type/data만 가진다.
  - edge는 type/source/target/data를 가진다.
  - CMIS의 reality_graph 스키마를 전부 구현하지 않고,
    POC에 필요한 최소 기능만 제공한다.
  """

  def __init__(self, nodes: Optional[List[Node]] = None, edges: Optional[List[Edge]] = None) -> None:
    """
    Args:
        nodes: 초기 노드 리스트 (선택)
        edges: 초기 엣지 리스트 (선택)
    """
    self.nodes: Dict[str, Node] = {}
    self.edges: List[Edge] = []
    
    # 초기 노드/엣지 추가
    if nodes:
      for node in nodes:
        self.nodes[node.id] = node
    
    if edges:
      self.edges = list(edges)

  # --- node operations ---
  def upsert_node(self, node_id: str, node_type: str, data: Dict[str, Any] | None = None) -> Node:
    if data is None:
      data = {}
    if node_id in self.nodes:
      # 간단히 data를 병합(덮어쓰기)하는 방식
      existing = self.nodes[node_id]
      existing.data.update(data)
      return existing
    node = Node(id=node_id, type=node_type, data=data)
    self.nodes[node_id] = node
    return node

  def get_node(self, node_id: str) -> Node | None:
    return self.nodes.get(node_id)

  # --- edge operations ---
  def add_edge(self, edge_type: str, source: str, target: str, data: Dict[str, Any] | None = None) -> Edge:
    if data is None:
      data = {}
    edge = Edge(type=edge_type, source=source, target=target, data=data)
    self.edges.append(edge)
    return edge

  # --- simple queries ---
  def neighbors(
      self,
      node_id: str,
      edge_type: Optional[str] = None,
      direction: Literal["out", "in", "both"] = "out"
  ) -> List[Node]:
    """특정 노드의 이웃 노드 목록 (v1: direction 파라미터 추가)
    
    Args:
        node_id: 조회할 노드 ID
        edge_type: Edge 타입 필터 (None이면 모든 타입)
        direction: "out" (나가는), "in" (들어오는), "both" (양방향)
    
    Returns:
        이웃 노드 목록
    """
    result: List[Node] = []
    
    for e in self.edges:
      # outgoing edges
      if direction in ("out", "both") and e.source == node_id:
        if edge_type is None or e.type == edge_type:
          node = self.nodes.get(e.target)
          if node is not None and node not in result:
            result.append(node)
      
      # incoming edges
      if direction in ("in", "both") and e.target == node_id:
        if edge_type is None or e.type == edge_type:
          node = self.nodes.get(e.source)
          if node is not None and node not in result:
            result.append(node)
    
    return result

  def incident_edges(self, node_id: str, edge_type: str | None = None) -> List[Edge]:
    """특정 노드와 연결된 edge 목록 (source 또는 target)."""
    result: List[Edge] = []
    for e in self.edges:
      if e.source == node_id or e.target == node_id:
        if edge_type is not None and e.type != edge_type:
          continue
        result.append(e)
    return result

  def nodes_by_type(self, node_type: str) -> List[Node]:
    return [n for n in self.nodes.values() if n.type == node_type]
  
  def edges_by_type(self, edge_type: str) -> List[Edge]:
    """특정 타입의 edge 목록"""
    return [e for e in self.edges if e.type == edge_type]

