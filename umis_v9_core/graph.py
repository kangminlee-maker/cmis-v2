from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class Node:
  id: str
  type: str
  data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
  type: str
  source: str
  target: str
  data: Dict[str, Any] = field(default_factory=dict)


class InMemoryGraph:
  """아주 단순한 인메모리 그래프 구현 (R-Graph POC용).

  - node는 id/type/data만 가진다.
  - edge는 type/source/target/data를 가진다.
  - UMIS v9의 reality_graph 스키마를 전부 구현하지 않고,
    POC에 필요한 최소 기능만 제공한다.
  """

  def __init__(self) -> None:
    self.nodes: Dict[str, Node] = {}
    self.edges: List[Edge] = []

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
  def neighbors(self, node_id: str, edge_type: str | None = None) -> List[Node]:
    """특정 노드에서 나가는 edge를 따라간 이웃 node 목록."""
    result: List[Node] = []
    for e in self.edges:
      if e.source != node_id:
        continue
      if edge_type is not None and e.type != edge_type:
        continue
      node = self.nodes.get(e.target)
      if node is not None:
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

