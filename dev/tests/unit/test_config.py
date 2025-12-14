"""Tests for Config Loader"""

import pytest
from cmis_core.config import CMISConfig


def test_config_loading(config_path):
    """cmis.yaml 로딩 테스트"""
    config = CMISConfig(config_path)

    assert config.cmis is not None
    assert "meta" in config.cmis
    assert "planes" in config.cmis
    assert "modules" in config.cmis
    assert config.cmis["meta"]["version"] == "3.6.0"


def test_metrics_indexing(config_path):
    """Metric 스펙 인덱싱 테스트 (metrics_spec.yaml)"""
    config = CMISConfig(config_path)

    # Metric 개수 확인 (Phase 1: 최소 스펙)
    assert len(config.metrics) >= 6

    # MET-Revenue 확인
    revenue_spec = config.get_metric_spec("MET-Revenue")
    assert revenue_spec is not None
    assert revenue_spec.metric_id == "MET-Revenue"
    assert revenue_spec.category == "structure_core_economics"

    # MET-N_customers 확인
    customers_spec = config.get_metric_spec("MET-N_customers")
    assert customers_spec is not None

    # MET-SAM 확인
    sam_spec = config.get_metric_spec("MET-SAM")
    assert sam_spec is not None
    assert sam_spec.name == "Serviceable Available Market (SAM)"


def test_metric_sets(config_path):
    """Metric Set 조회 테스트"""
    config = CMISConfig(config_path)

    # structure_core_economics set 확인
    core_economics = config.get_metric_set("structure_core_economics")
    assert core_economics is not None
    assert len(core_economics) > 0
    assert "MET-N_customers" in core_economics
    assert "MET-Revenue" in core_economics
    assert "MET-Avg_price_per_unit" in core_economics


def test_tool_registry_indexing(config_path):
    """Tool registry 인덱싱 테스트 (cmis.yaml contract)"""
    config = CMISConfig(config_path)

    tool_ids = config.list_tool_ids()
    assert "web_search" in tool_ids
    assert "python_runtime" in tool_ids

    web_search = config.get_tool("web_search")
    assert web_search is not None
    assert web_search["class"] == "tool"
    assert web_search["safety"] == "restricted"

def test_quality_profiles(config_path):
    """Policy pack 로딩 테스트 (config/policies.yaml)"""
    config = CMISConfig(config_path)

    try:
        policies_path = config.cmis["modules"]["config"]["policies"]
        policies_doc = config._load_yaml_file(policies_path)
        policy_pack = policies_doc.get("policy_pack", {}) or {}
        modes = policy_pack.get("modes", {}) or {}
        assert "reporting_strict" in modes
        assert "decision_balanced" in modes
        assert "exploration_friendly" in modes
    except KeyError:
        pytest.skip("policies 섹션 없음 (정상)")
