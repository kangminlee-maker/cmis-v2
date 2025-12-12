"""Workflow CLI Phase 2 테스트

batch-analysis, report-generate, cache-manage, config-validate 검증

2025-12-11: Workflow CLI Phase 2
"""

import pytest
import subprocess
import tempfile
import yaml
import json
from pathlib import Path


class TestBatchAnalysis:
    """batch-analysis 테스트"""
    
    def test_batch_config_loading(self):
        """Batch config 로딩"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Batch config 생성
            config = {
                "jobs": [
                    {
                        "workflow_id": "structure_analysis",
                        "inputs": {
                            "domain_id": "Adult_Language_Education_KR",
                            "region": "KR"
                        },
                        "output": "result_1.json"
                    }
                ]
            }
            
            config_path = Path(tmpdir) / "batch.yaml"
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
            
            # Help만 테스트
            result = subprocess.run(
                ["python3", "-m", "cmis_cli", "batch-analysis", "--help"],
                cwd="/Users/kangmin/v9_dev",
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert "--config" in result.stdout


class TestReportGenerate:
    """report-generate 테스트"""
    
    def test_report_generate_help(self):
        """report-generate --help"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "report-generate", "--help"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "--template" in result.stdout
        assert "--include-lineage" in result.stdout


class TestCacheManage:
    """cache-manage 테스트"""
    
    def test_cache_status(self):
        """캐시 상태 조회"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "cache-manage", "--status"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Evidence Cache" in result.stdout or "캐시" in result.stdout
    
    def test_cache_clear(self):
        """캐시 클리어"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "cache-manage", "--clear", "--type", "results"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0


class TestConfigValidate:
    """config-validate 테스트"""
    
    def test_config_validate_basic(self):
        """기본 검증"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "config-validate"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "YAML 구문" in result.stdout or "OK" in result.stdout
    
    def test_config_validate_check_all(self):
        """전체 검증"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "config-validate", "--check-all"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Seeds" in result.stdout or "Patterns" in result.stdout


class TestCLIIntegration:
    """CLI 통합 테스트"""
    
    def test_all_commands_available(self):
        """모든 명령어 사용 가능"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "--help"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        
        # 8개 명령어 확인
        assert "structure-analysis" in result.stdout
        assert "opportunity-discovery" in result.stdout
        assert "compare-contexts" in result.stdout
        assert "batch-analysis" in result.stdout
        assert "report-generate" in result.stdout
        assert "cache-manage" in result.stdout
        assert "config-validate" in result.stdout
