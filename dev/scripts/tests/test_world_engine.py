"""Tests for World Engine"""

import pytest
from pathlib import Path
from cmis_core.world_engine import WorldEngine


def test_world_engine_init(project_root):
    """World Engine 초기화 테스트"""
    engine = WorldEngine(project_root)
    
    assert engine.project_root == project_root
    assert engine.seeds_dir == project_root / "seeds"
    assert engine.domain_registry is not None


def test_load_reality_seed(project_root, seed_path):
    """Reality seed 로딩 테스트"""
    engine = WorldEngine(project_root)
    
    snapshot = engine.load_reality_seed(seed_path)
    
    # 기본 검증
    assert snapshot.graph is not None
    assert snapshot.meta is not None
    assert snapshot.meta["domain_id"] == "Adult_Language_Education_KR"
    
    # 노드 개수 검증
    assert snapshot.meta["num_actors"] > 0
    assert snapshot.meta["num_money_flows"] > 0
    
    # Actor 노드 확인
    actors = snapshot.graph.nodes_by_type("actor")
    assert len(actors) >= 5  # 최소 5개 Actor
    
    # MoneyFlow 노드 확인
    money_flows = snapshot.graph.nodes_by_type("money_flow")
    assert len(money_flows) >= 3  # 최소 3개 MoneyFlow
    
    # Edge 확인 (actor_pays_actor)
    edges = [e for e in snapshot.graph.edges if e.type == "actor_pays_actor"]
    assert len(edges) >= 3


def test_snapshot_adult_language(project_root):
    """Adult Language 도메인 snapshot 테스트"""
    engine = WorldEngine(project_root)
    
    snapshot = engine.snapshot(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    # Meta 검증
    assert snapshot.meta["domain_id"] == "Adult_Language_Education_KR"
    assert snapshot.meta["region"] == "KR"
    
    # Graph 검증
    assert snapshot.graph is not None
    assert len(snapshot.graph.nodes) > 0


def test_snapshot_nonexistent_domain(project_root):
    """존재하지 않는 도메인 snapshot 시도"""
    engine = WorldEngine(project_root)
    
    with pytest.raises(FileNotFoundError) as exc_info:
        engine.snapshot(
            domain_id="NonExistent_Domain",
            region="KR"
        )
    
    # 에러 메시지에 도메인 정보 포함
    assert "NonExistent_Domain" in str(exc_info.value)
    assert "Registered domains" in str(exc_info.value)


def test_snapshot_with_segment_and_as_of(project_root):
    """segment, as_of 파라미터 포함 snapshot 테스트"""
    engine = WorldEngine(project_root)
    
    snapshot = engine.snapshot(
        domain_id="Adult_Language_Education_KR",
        region="KR",
        segment="office_worker",
        as_of="2025-12-05"
    )
    
    # v1에서는 meta에만 기록
    assert snapshot.meta["segment"] == "office_worker"
    assert snapshot.meta["as_of"] == "2025-12-05"
    
    # 실제 필터링은 v2+
    # v1에서는 전체 그래프 반환
    assert len(snapshot.graph.nodes) > 0
