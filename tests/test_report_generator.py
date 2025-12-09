"""Tests for Report Generator"""

import pytest
from pathlib import Path
from umis_v9_core.workflow import run_structure_analysis
from umis_v9_core.report_generator import generate_structure_report


def test_generate_structure_report(project_root):
    """Markdown 리포트 생성 테스트"""
    result = run_structure_analysis(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    markdown = generate_structure_report(result)
    
    # 기본 검증
    assert markdown is not None
    assert len(markdown) > 0
    
    # 필수 섹션 포함
    assert "# Market Structure Snapshot" in markdown
    assert "## 1. Market Structure Overview" in markdown
    assert "## 2. 감지된 비즈니스 패턴" in markdown
    assert "## 3. 핵심 Metric" in markdown
    
    # 도메인 정보
    assert "Adult_Language_Education_KR" in markdown
    assert "KR" in markdown
    
    # Pattern 정보
    assert "PAT-subscription_model" in markdown
    assert "PAT-platform_business_model" in markdown
    
    # Metric 정보
    assert "MET-N_customers" in markdown
    assert "MET-Revenue" in markdown


def test_generate_report_with_file_save(project_root, tmp_path):
    """파일 저장 테스트"""
    result = run_structure_analysis(
        domain_id="Adult_Language_Education_KR",
        region="KR"
    )
    
    output_path = tmp_path / "test_report.md"
    markdown = generate_structure_report(result, str(output_path))
    
    # 파일 생성 확인
    assert output_path.exists()
    
    # 파일 내용 확인
    content = output_path.read_text(encoding='utf-8')
    assert content == markdown
    assert len(content) > 500
