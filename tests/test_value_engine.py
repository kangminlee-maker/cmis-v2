"""Tests for Value Engine"""

import pytest
from cmis_core.world_engine import WorldEngine
from cmis_core.value_engine import ValueEngine
from cmis_core.types import MetricRequest


def test_value_engine_init():
    """Value Engine 초기화 테스트"""
    engine = ValueEngine()
    
    assert engine.config is not None
    assert engine.metrics is not None


def test_compute_n_customers(project_root, seed_path):
    """N_customers 계산 테스트"""
    # R-Graph 로드
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    # Value Engine
    value_engine = ValueEngine()
    
    # N_customers 계산
    n_customers = value_engine._compute_n_customers(snapshot.graph, {})
    
    # Adult Language seed 기준
    # - 성인 개인 학습자: 3,000,000
    # - 기업 고객: 20,000
    # = 3,020,000
    assert n_customers == 3_020_000


def test_compute_revenue(project_root, seed_path):
    """Revenue 계산 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    value_engine = ValueEngine()
    
    revenue = value_engine._compute_total_revenue(snapshot.graph, {})
    
    # Adult Language seed 기준
    # - 개인 → 오프라인: 150B
    # - 개인 → 온라인: 100B
    # - 기업 → 교육업체: 40B
    # = 290B
    assert revenue == 290_000_000_000


def test_compute_avg_price(project_root, seed_path):
    """Avg_price_per_unit 계산 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    value_engine = ValueEngine()
    
    avg_price = value_engine._compute_avg_price_per_unit(snapshot.graph, {})
    
    # 290B / 3.02M ≈ 96,026
    assert avg_price is not None
    assert 90_000 <= avg_price <= 100_000


def test_evaluate_metrics_single(project_root, seed_path):
    """단일 Metric 평가 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    value_engine = ValueEngine()
    
    requests = [MetricRequest("MET-N_customers", {})]
    records, program = value_engine.evaluate_metrics(snapshot.graph, requests)
    
    assert len(records) == 1
    assert records[0].metric_id == "MET-N_customers"
    assert records[0].point_estimate == 3_020_000
    assert records[0].quality["status"] == "ok"
    assert records[0].quality["method"] == "r_graph_aggregation"


def test_evaluate_metrics_multiple(project_root, seed_path):
    """여러 Metric 평가 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    value_engine = ValueEngine()
    
    requests = [
        MetricRequest("MET-N_customers", {}),
        MetricRequest("MET-Revenue", {}),
        MetricRequest("MET-Avg_price_per_unit", {}),
    ]
    
    records, program = value_engine.evaluate_metrics(snapshot.graph, requests)
    
    assert len(records) == 3
    assert all(r.quality["status"] == "ok" for r in records)
    
    # Metric별 확인
    n_customers_record = next(r for r in records if r.metric_id == "MET-N_customers")
    assert n_customers_record.point_estimate == 3_020_000
    
    revenue_record = next(r for r in records if r.metric_id == "MET-Revenue")
    assert revenue_record.point_estimate == 290_000_000_000
    
    avg_price_record = next(r for r in records if r.metric_id == "MET-Avg_price_per_unit")
    assert avg_price_record.point_estimate is not None


def test_evaluate_metrics_not_implemented(project_root, seed_path):
    """미구현 Metric 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    value_engine = ValueEngine()
    
    requests = [MetricRequest("MET-TAM", {})]  # v1에서 미구현
    records, program = value_engine.evaluate_metrics(snapshot.graph, requests)
    
    assert len(records) == 1
    assert records[0].metric_id == "MET-TAM"
    assert records[0].point_estimate is None
    assert records[0].quality["status"] == "not_implemented"
