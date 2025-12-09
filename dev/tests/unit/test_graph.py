"""Tests for InMemoryGraph"""

import pytest
from cmis_core.graph import InMemoryGraph
from cmis_core.types import Node, Edge


def test_node_upsert():
    """노드 추가 및 업데이트 테스트"""
    graph = InMemoryGraph()
    
    # 새 노드 추가
    node1 = graph.upsert_node("ACT-001", "actor", {"name": "TestCo"})
    assert node1.id == "ACT-001"
    assert node1.type == "actor"
    assert node1.data["name"] == "TestCo"
    
    # 같은 ID로 업데이트
    node2 = graph.upsert_node("ACT-001", "actor", {"revenue": 1000})
    assert node2.id == "ACT-001"
    assert node2.data["name"] == "TestCo"  # 기존 유지
    assert node2.data["revenue"] == 1000  # 새로 추가
    
    # 노드 개수 확인
    assert len(graph.nodes) == 1


def test_edge_add():
    """엣지 추가 테스트"""
    graph = InMemoryGraph()
    
    graph.upsert_node("ACT-001", "actor", {})
    graph.upsert_node("ACT-002", "actor", {})
    
    edge = graph.add_edge("actor_pays_actor", "ACT-001", "ACT-002", {"amount": 1000})
    
    assert edge.type == "actor_pays_actor"
    assert edge.source == "ACT-001"
    assert edge.target == "ACT-002"
    assert edge.data["amount"] == 1000
    assert len(graph.edges) == 1


def test_neighbors_outgoing():
    """이웃 노드 조회 (outgoing) 테스트"""
    graph = InMemoryGraph()
    
    graph.upsert_node("ACT-001", "actor", {})
    graph.upsert_node("ACT-002", "actor", {})
    graph.upsert_node("ACT-003", "actor", {})
    
    graph.add_edge("actor_pays_actor", "ACT-001", "ACT-002", {})
    graph.add_edge("actor_pays_actor", "ACT-001", "ACT-003", {})
    graph.add_edge("actor_competes_with", "ACT-002", "ACT-003", {})
    
    # ACT-001의 outgoing neighbors
    neighbors = graph.neighbors("ACT-001", direction="out")
    assert len(neighbors) == 2
    assert {n.id for n in neighbors} == {"ACT-002", "ACT-003"}
    
    # edge_type 필터
    neighbors_pays = graph.neighbors("ACT-001", edge_type="actor_pays_actor", direction="out")
    assert len(neighbors_pays) == 2


def test_neighbors_incoming():
    """이웃 노드 조회 (incoming) 테스트"""
    graph = InMemoryGraph()
    
    graph.upsert_node("ACT-001", "actor", {})
    graph.upsert_node("ACT-002", "actor", {})
    graph.upsert_node("ACT-003", "actor", {})
    
    graph.add_edge("actor_pays_actor", "ACT-001", "ACT-003", {})
    graph.add_edge("actor_pays_actor", "ACT-002", "ACT-003", {})
    
    # ACT-003의 incoming neighbors
    neighbors = graph.neighbors("ACT-003", direction="in")
    assert len(neighbors) == 2
    assert {n.id for n in neighbors} == {"ACT-001", "ACT-002"}


def test_neighbors_both():
    """이웃 노드 조회 (both) 테스트"""
    graph = InMemoryGraph()
    
    graph.upsert_node("ACT-001", "actor", {})
    graph.upsert_node("ACT-002", "actor", {})
    graph.upsert_node("ACT-003", "actor", {})
    
    graph.add_edge("actor_pays_actor", "ACT-001", "ACT-002", {})
    graph.add_edge("actor_pays_actor", "ACT-002", "ACT-003", {})
    
    # ACT-002의 all neighbors (양방향)
    neighbors = graph.neighbors("ACT-002", direction="both")
    assert len(neighbors) == 2
    assert {n.id for n in neighbors} == {"ACT-001", "ACT-003"}


def test_nodes_by_type():
    """타입별 노드 조회 테스트"""
    graph = InMemoryGraph()
    
    graph.upsert_node("ACT-001", "actor", {"kind": "company"})
    graph.upsert_node("ACT-002", "actor", {"kind": "customer"})
    graph.upsert_node("MFL-001", "money_flow", {})
    graph.upsert_node("STA-001", "state", {})
    
    actors = graph.nodes_by_type("actor")
    assert len(actors) == 2
    
    money_flows = graph.nodes_by_type("money_flow")
    assert len(money_flows) == 1
    
    states = graph.nodes_by_type("state")
    assert len(states) == 1


def test_incident_edges():
    """연결된 엣지 조회 테스트"""
    graph = InMemoryGraph()
    
    graph.upsert_node("ACT-001", "actor", {})
    graph.upsert_node("ACT-002", "actor", {})
    
    graph.add_edge("actor_pays_actor", "ACT-001", "ACT-002", {})
    graph.add_edge("actor_competes_with", "ACT-001", "ACT-002", {})
    graph.add_edge("actor_serves_actor", "ACT-002", "ACT-001", {})
    
    # ACT-001 관련 모든 엣지
    edges = graph.incident_edges("ACT-001")
    assert len(edges) == 3
    
    # edge_type 필터
    pays_edges = graph.incident_edges("ACT-001", edge_type="actor_pays_actor")
    assert len(pays_edges) == 1
