"""Tests for Config Loader"""

import pytest
from cmis_core.config import CMISConfig, MetricSpec


def test_config_loading(config_path):
    """cmis.yaml 로딩 테스트"""
    config = CMISConfig(config_path)
    
    assert config.cmis is not None
    assert "meta" in config.cmis
    assert "planes" in config.cmis
    assert "ontology" in config.cmis
    assert config.cmis["meta"]["version"] == "9.0.0-alpha"


def test_metrics_indexing(config_path):
    """Metric 스펙 인덱싱 테스트 (전체 umis_v9.yaml)"""
    config = CMISConfig(config_path)
    
    # Metric 개수 확인 (36개)
    assert len(config.metrics) >= 30
    
    # MET-Revenue 확인
    revenue_spec = config.get_metric_spec("MET-Revenue")
    assert revenue_spec is not None
    assert revenue_spec.metric_id == "MET-Revenue"
    assert revenue_spec.category == "market_size"
    
    # MET-N_customers 확인
    customers_spec = config.get_metric_spec("MET-N_customers")
    assert customers_spec is not None
    
    # MET-SAM 확인
    sam_spec = config.get_metric_spec("MET-SAM")
    assert sam_spec is not None
    assert sam_spec.name == "Serviceable Available Market"


def test_metric_sets(config_path):
    """Metric Set 조회 테스트"""
    config = CMISConfig(config_path)
    
    # structure_core_economics set 확인
    core_economics = config.get_metric_set("structure_core_economics")
    assert core_economics is not None
    assert len(core_economics) > 0
    assert "MET-TAM" in core_economics
    assert "MET-SAM" in core_economics
    assert "MET-Revenue" in core_economics


def test_data_sources_indexing(config_path):
    """Data Source 인덱싱 테스트"""
    config = CMISConfig(config_path)
    
    # Data Sources 확인
    assert len(config.data_sources) >= 5
    
    # DART 확인
    dart = config.get_data_source("KR_DART_filings")
    assert dart is not None
    assert dart["type"] == "http_api"
    
    # KOSIS 확인
    kosis = config.get_data_source("KOSIS_population")
    assert kosis is not None


def test_quality_profiles(config_path):
    """Quality Profile 로딩 테스트"""
    config = CMISConfig(config_path)
    
    try:
        policies = config.cmis["policies"]
        quality_profiles = policies.get("quality_profiles", {})
        assert "reporting_strict" in quality_profiles
        assert "decision_balanced" in quality_profiles
        assert "exploration_friendly" in quality_profiles
    except KeyError:
        pytest.skip("policies 섹션 없음 (정상)")
