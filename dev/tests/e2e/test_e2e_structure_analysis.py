"""End-to-End Integration Tests for structure_analysis"""

import pytest
from pathlib import Path
from cmis_core.workflow import run_structure_analysis
from cmis_core.report_generator import generate_structure_report


def test_e2e_structure_analysis_adult_language(project_root):
    """E2E: Adult Language 전체 워크플로우"""
    
    # 실행
    result = run_structure_analysis(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    # === 결과 검증 ===
    
    # Meta
    assert result.meta["domain_id"] == "Adult_Language_Education_KR"
    assert result.meta["region"] == "KR"
    
    # Graph Overview
    assert result.graph_overview["num_actors"] == 8
    assert result.graph_overview["num_money_flows"] == 6
    assert result.graph_overview["num_states"] == 1
    
    # Actor 종류
    actor_types = result.graph_overview["actor_types"]
    assert actor_types["customer_segment"] == 2
    assert actor_types["company"] == 5
    assert actor_types["partner"] == 1
    
    # 총 Money Flow
    total_flow = result.graph_overview["total_money_flow_amount"]
    assert total_flow == 325_000_000_000  # 325억 (seed 데이터 기준)
    
    # Patterns
    assert len(result.pattern_matches) == 2
    pattern_ids = {p.pattern_id for p in result.pattern_matches}
    assert pattern_ids == {"PAT-subscription_model", "PAT-platform_business_model"}
    
    # Metrics
    assert len(result.metrics) == 3
    
    metric_dict = {m.metric_id: m.point_estimate for m in result.metrics}
    assert metric_dict["MET-N_customers"] == 3_020_000
    assert metric_dict["MET-Revenue"] == 290_000_000_000
    assert metric_dict["MET-Avg_price_per_unit"] is not None
    
    # 실행 시간
    assert result.execution_time is not None
    assert result.execution_time < 5.0  # 5초 이내


def test_e2e_with_markdown_report(project_root, tmp_path):
    """E2E: Markdown 리포트까지 생성"""
    
    # 1. structure_analysis 실행
    result = run_structure_analysis(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    # 2. Markdown 리포트 생성
    output_path = tmp_path / "Market_Structure_Snapshot.md"
    markdown = generate_structure_report(result, str(output_path))
    
    # 3. 파일 생성 확인
    assert output_path.exists()
    
    # 4. 파일 내용 검증
    content = output_path.read_text(encoding='utf-8')
    
    # 필수 정보 포함
    assert "302만" in content  # N_customers 포맷팅
    assert "2900억" in content or "2,900억" in content  # Revenue
    assert "PAT-subscription_model" in content
    assert "PAT-platform_business_model" in content
    
    # 구조 검증
    assert "## 1. Market Structure Overview" in content
    assert "## 2. 감지된 비즈니스 패턴" in content
    assert "## 3. 핵심 Metric" in content


def test_e2e_json_serialization(project_root):
    """E2E: JSON 직렬화 테스트"""
    import json
    
    result = run_structure_analysis(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    # to_dict() 호출
    result_dict = result.to_dict()
    
    # JSON 직렬화 가능
    json_str = json.dumps(result_dict, ensure_ascii=False, indent=2)
    assert len(json_str) > 100
    
    # 다시 파싱 가능
    parsed = json.loads(json_str)
    assert parsed["meta"]["domain_id"] == "Adult_Language_Education_KR"
    assert len(parsed["metrics"]) == 3


def test_e2e_performance_benchmark(project_root):
    """E2E: 성능 벤치마크 (v1 기준)"""
    
    result = run_structure_analysis(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    # v1 성능 기준
    assert result.execution_time < 1.0  # 1초 이내 (seed 기반)
    
    # 리소스 효율성
    assert result.graph_overview["num_actors"] > 0
    assert len(result.pattern_matches) > 0
    assert len(result.metrics) == 3
