"""Workflow CLI 테스트

CLI 명령어 및 WorkflowOrchestrator v2 검증

2025-12-11: Workflow CLI Phase 1
"""

import pytest
import subprocess
import json
from pathlib import Path
import tempfile

from cmis_core.workflow import WorkflowOrchestrator


class TestWorkflowOrchestrator:
    """WorkflowOrchestrator v2 테스트"""

    def test_load_canonical_workflows(self, project_root):
        """canonical_workflows 로딩"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        workflows = orchestrator.workflows

        assert "structure_analysis" in workflows
        assert "opportunity_discovery" in workflows

        # structure_analysis 정의 확인
        sa = workflows["structure_analysis"]
        assert sa["role_id"] == "structure_analyst"
        assert "steps" in sa

    def test_run_workflow_structure_analysis(self, project_root):
        """Generic run_workflow (structure_analysis)"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        result = orchestrator.run_workflow(
            workflow_id="structure_analysis",
            inputs={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR"
            }
        )

        assert "meta" in result
        assert result["meta"]["workflow_id"] == "structure_analysis"
        assert result["meta"]["role_id"] == "structure_analyst"
        assert result["meta"]["policy_mode"] == "reporting_strict"

    def test_run_workflow_opportunity_discovery(self, project_root):
        """Generic run_workflow (opportunity_discovery)"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        result = orchestrator.run_workflow(
            workflow_id="opportunity_discovery",
            inputs={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR",
                "top_n": 3
            }
        )

        assert "meta" in result
        assert result["meta"]["workflow_id"] == "opportunity_discovery"
        assert result["meta"]["role_id"] == "opportunity_designer"
        assert result["meta"]["policy_mode"] == "exploration_friendly"

    def test_run_workflow_with_role_override(self, project_root):
        """Role override"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        result = orchestrator.run_workflow(
            workflow_id="structure_analysis",
            inputs={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR"
            },
            role_id="numerical_modeler"  # Override
        )

        assert result["meta"]["role_id"] == "numerical_modeler"

    def test_run_workflow_with_policy_override(self, project_root):
        """Policy override"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        result = orchestrator.run_workflow(
            workflow_id="structure_analysis",
            inputs={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR"
            },
            policy_mode="exploration_friendly"  # Override
        )

        assert result["meta"]["policy_mode"] == "exploration_friendly"

    def test_run_workflow_strategy_design_smoke(self, project_root):
        """Generic run_workflow (strategy_design) - step runner smoke"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        result = orchestrator.run_workflow(
            workflow_id="strategy_design",
            inputs={
                "goal_id": "GOL-test",
                "constraints": {
                    "scope": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                    "horizon": "3y",
                },
                "project_context_id": None,
            },
        )

        assert result["meta"]["workflow_id"] == "strategy_design"
        assert "steps" in result
        assert result["steps"][0]["status"] == "ok"
        assert "outputs" in result
        assert "strategy_set_ref" in result["outputs"]
        assert isinstance(result["outputs"].get("strategy_ids"), list)

    def test_run_workflow_reality_monitoring_smoke(self, project_root):
        """Generic run_workflow (reality_monitoring) - auto snapshot + evaluate_metrics smoke"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        result = orchestrator.run_workflow(
            workflow_id="reality_monitoring",
            inputs={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR",
                "outcome_ids": [],
            },
        )

        assert result["meta"]["workflow_id"] == "reality_monitoring"
        assert "steps" in result
        assert len(result["steps"]) >= 1
        assert "outputs" in result
        # evaluate_metrics가 실행되면 value_records가 생김
        if any(s.get("call") == "value_engine.evaluate_metrics" and s.get("status") == "ok" for s in result["steps"]):
            assert "value_records" in result["outputs"]


class TestOpportunityDiscovery:
    """opportunity_discovery 워크플로우 테스트"""

    def test_opportunity_discovery_basic(self, project_root):
        """기본 opportunity discovery"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        result = orchestrator.run_opportunity_discovery(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            top_n=5
        )

        assert "meta" in result
        assert "matched_patterns" in result
        assert "gaps" in result
        assert result["top_n"] == 5

    def test_opportunity_discovery_with_feasibility_filter(self, project_root):
        """Feasibility 필터링"""
        orchestrator = WorkflowOrchestrator(project_root=project_root)

        result = orchestrator.run_opportunity_discovery(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            top_n=10,
            min_feasibility="high"
        )

        # 결과가 있으면 모두 high feasibility
        for gap_info in result["gaps"]:
            gap = gap_info["gap"]
            # high feasibility만 (또는 gap이 없음)
            if hasattr(gap, 'feasibility'):
                assert gap.feasibility in ["high", "unknown"]  # unknown은 허용


class TestCLI:
    """CLI 명령어 테스트"""

    def test_cli_structure_analysis_help(self):
        """structure-analysis --help"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "structure-analysis", "--help"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "--domain" in result.stdout
        assert "--region" in result.stdout
        assert "--role" in result.stdout  # 새로 추가된 옵션

    def test_cli_opportunity_discovery_help(self):
        """opportunity-discovery --help"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "opportunity-discovery", "--help"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "--top-n" in result.stdout
        assert "--domain" in result.stdout
        assert "--role" in result.stdout  # 새로 추가된 옵션

    def test_cli_workflow_run_help(self):
        """workflow run --help"""
        result = subprocess.run(
            ["python3", "-m", "cmis_cli", "workflow", "run", "--help"],
            cwd="/Users/kangmin/v9_dev",
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "workflow_id" in result.stdout


class TestIntegrationCLI:
    """CLI 통합 테스트"""

    def test_structure_analysis_with_output(self, project_root):
        """structure-analysis 실제 실행 + 파일 저장"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "result.json"

            result = subprocess.run(
                [
                    "python3", "-m", "cmis_cli",
                    "structure-analysis",
                    "--domain", "Adult_Language_Education_KR",
                    "--region", "KR",
                    "--output", str(output_file)
                ],
                cwd=str(project_root),
                capture_output=True,
                text=True
            )

            # 성공 확인
            assert result.returncode == 0
            assert output_file.exists()

            # 결과 파일 검증
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert "meta" in data
            assert data["meta"]["domain_id"] == "Adult_Language_Education_KR"
            assert "graph_overview" in data
            assert "pattern_matches" in data

    def test_opportunity_discovery_actual_run(self, project_root):
        """opportunity-discovery 실제 실행"""
        result = subprocess.run(
            [
                "python3", "-m", "cmis_cli",
                "opportunity-discovery",
                "--domain", "Adult_Language_Education_KR",
                "--region", "KR",
                "--top-n", "2"
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )

        # 성공 확인
        assert result.returncode == 0
        assert "opportunity_discovery 완료" in result.stdout or "Opportunity Discovery" in result.stdout



