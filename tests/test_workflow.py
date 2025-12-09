"""Tests for Workflow Orchestrator"""

import pytest
from umis_v9_core.workflow import WorkflowOrchestrator, run_structure_analysis
from umis_v9_core.types import StructureAnalysisInput


def test_workflow_orchestrator_init(project_root):
    """Workflow Orchestrator 초기화 테스트"""
    orchestrator = WorkflowOrchestrator(project_root=project_root)
    
    assert orchestrator.world_engine is not None
    assert orchestrator.pattern_engine is not None
    assert orchestrator.value_engine is not None


def test_run_structure_analysis_basic(project_root):
    """기본 structure_analysis 실행 테스트"""
    input_data = StructureAnalysisInput(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    orchestrator = WorkflowOrchestrator(project_root=project_root)
    result = orchestrator.run_structure_analysis(input_data)
    
    # Meta 검증
    assert result.meta["domain_id"] == "Adult_Language_Education_KR"
    assert result.meta["region"] == "KR"
    
    # Graph overview 검증
    assert result.graph_overview["num_actors"] > 0
    assert result.graph_overview["num_money_flows"] > 0
    assert result.graph_overview["total_money_flow_amount"] > 0
    
    # Pattern matches 검증
    assert len(result.pattern_matches) >= 2
    pattern_ids = {p.pattern_id for p in result.pattern_matches}
    assert "PAT-subscription_model" in pattern_ids
    assert "PAT-platform_business_model" in pattern_ids
    
    # Metrics 검증
    assert len(result.metrics) == 3
    metric_ids = {m.metric_id for m in result.metrics}
    assert "MET-N_customers" in metric_ids
    assert "MET-Revenue" in metric_ids
    assert "MET-Avg_price_per_unit" in metric_ids
    
    # 실행 시간
    assert result.execution_time is not None
    assert result.execution_time > 0


def test_run_structure_analysis_convenience_function(project_root):
    """편의 함수 테스트"""
    result = run_structure_analysis(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    assert result is not None
    assert result.meta["domain_id"] == "Adult_Language_Education_KR"
    assert len(result.metrics) == 3


def test_structure_analysis_to_dict(project_root):
    """StructureAnalysisResult.to_dict() 테스트"""
    result = run_structure_analysis(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    result_dict = result.to_dict()
    
    assert "meta" in result_dict
    assert "graph_overview" in result_dict
    assert "pattern_matches" in result_dict
    assert "metrics" in result_dict
    
    # JSON 직렬화 가능 확인
    import json
    json_str = json.dumps(result_dict, ensure_ascii=False, indent=2)
    assert len(json_str) > 0
