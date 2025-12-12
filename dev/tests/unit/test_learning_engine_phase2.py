"""LearningEngine Phase 2 테스트

ProjectContext 업데이트, 버전 관리, ValueEngine 연동

2025-12-11: LearningEngine Phase 2
"""

import pytest

from cmis_core.types import Outcome, ProjectContext, Strategy
from cmis_core.context_learner import ContextLearner
from cmis_core.learning_engine import LearningEngine


class TestContextLearner:
    """ContextLearner 테스트"""
    
    def test_update_baseline_state(self):
        """baseline_state 업데이트"""
        learner = ContextLearner()
        
        # 기존 Context
        project_context = ProjectContext(
            project_context_id="PRJ-test-v1",
            version=1,
            baseline_state={
                "current_revenue": 1000000000,
                "current_customers": 10000,
                "as_of": "2024-12-31"
            }
        )
        
        # Outcome
        outcome = Outcome(
            outcome_id="OUT-001",
            metrics={
                "MET-Revenue": 1500000000,  # 15억 (50% 성장)
                "MET-N_customers": 15000
            },
            as_of="2025-12-31"
        )
        
        # 업데이트
        updated = learner.update_baseline_state(project_context, outcome)
        
        # 버전 증가
        assert updated.version == 2
        assert updated.previous_version_id == "PRJ-test-v1"
        
        # baseline_state 업데이트
        assert updated.baseline_state["current_revenue"] == 1500000000
        assert updated.baseline_state["current_customers"] == 15000
        assert updated.baseline_state["as_of"] == "2025-12-31"
        
        # Lineage
        assert "from_outcome_ids" in updated.lineage
        assert "OUT-001" in updated.lineage["from_outcome_ids"]
    
    def test_version_management(self):
        """버전 관리"""
        learner = ContextLearner()
        
        # v1
        context_v1 = ProjectContext(
            project_context_id="PRJ-company",
            version=1
        )
        
        outcome1 = Outcome(
            outcome_id="OUT-001",
            metrics={"MET-Revenue": 1000000000},
            as_of="2025-01-31"
        )
        
        # v2
        context_v2 = learner.update_baseline_state(context_v1, outcome1)
        
        assert context_v2.version == 2
        assert context_v2.project_context_id == "PRJ-company-v2"
        assert context_v2.previous_version_id == "PRJ-company"
        
        # v3
        outcome2 = Outcome(
            outcome_id="OUT-002",
            metrics={"MET-Revenue": 1200000000},
            as_of="2025-02-28"
        )
        
        context_v3 = learner.update_baseline_state(context_v2, outcome2)
        
        assert context_v3.version == 3
        assert context_v3.project_context_id == "PRJ-company-v3"
        assert context_v3.previous_version_id == "PRJ-company-v2"


class TestUpdateProjectContextAPI:
    """update_project_context_from_outcome_api 테스트"""
    
    def test_update_project_context_api(self):
        """Public API"""
        engine = LearningEngine()
        
        # ProjectContext 등록
        context = ProjectContext(
            project_context_id="PRJ-api-test",
            version=1,
            baseline_state={
                "current_revenue": 1000000000,
                "as_of": "2024-12-31"
            }
        )
        
        engine.register_project_context(context)
        
        # Outcome 등록
        outcome = Outcome(
            outcome_id="OUT-api",
            project_context_id="PRJ-api-test",
            metrics={"MET-Revenue": 1500000000},
            as_of="2025-12-31"
        )
        
        engine.register_outcome(outcome)
        
        # 업데이트
        updated_ref = engine.update_project_context_from_outcome_api(
            outcome_id="OUT-api",
            project_context_id="PRJ-api-test"
        )
        
        # 새 버전 ID
        assert updated_ref.startswith("PRJ-api-test")
        assert "-v" in updated_ref
    
    def test_baseline_metrics_mapping(self):
        """Metric → baseline_state 매핑"""
        learner = ContextLearner()
        
        context = ProjectContext(
            project_context_id="PRJ-mapping",
            baseline_state={}
        )
        
        outcome = Outcome(
            outcome_id="OUT-mapping",
            metrics={
                "MET-Revenue": 2000000000,
                "MET-N_customers": 20000,
                "MET-Gross_margin": 0.75,
                "MET-Churn_rate": 0.05
            },
            as_of="2025-12-31"
        )
        
        updated = learner.update_baseline_state(context, outcome)
        
        # 매핑 확인
        assert updated.baseline_state["current_revenue"] == 2000000000
        assert updated.baseline_state["current_customers"] == 20000
        
        margin_structure = updated.baseline_state.get("margin_structure", {})
        assert margin_structure.get("gross_margin") == 0.75
        assert margin_structure.get("churn_rate") == 0.05


class TestIntegrationPhase2:
    """Phase 2 통합 테스트"""
    
    def test_full_learning_loop(self):
        """전체 학습 루프"""
        engine = LearningEngine()
        
        # 1. 초기 Context
        context = ProjectContext(
            project_context_id="PRJ-loop",
            version=1,
            baseline_state={
                "current_revenue": 1000000000,
                "as_of": "2024-12-31"
            }
        )
        
        # 2. Strategy
        strategy = Strategy(
            strategy_id="STR-loop",
            name="성장 전략",
            pattern_composition=["PAT-subscription_model"],
            expected_outcomes={"revenue_3y": 1500000000}
        )
        
        # 3. Outcome (전략 실행 1년 후)
        outcome = Outcome(
            outcome_id="OUT-loop",
            related_strategy_id="STR-loop",
            project_context_id="PRJ-loop",
            metrics={"MET-Revenue": 1200000000},  # 실제 1년 후
            as_of="2025-12-31"
        )
        
        engine.register_project_context(context)
        engine.register_strategy(strategy)
        engine.register_outcome(outcome)
        
        # 4. 학습
        learning_result = engine.update_from_outcomes_api(["OUT-loop"])
        
        # 5. Context 업데이트
        updated_context_ref = engine.update_project_context_from_outcome_api(
            "OUT-loop",
            "PRJ-loop"
        )
        
        # 검증
        assert learning_result["learning_quality"]["total_outcomes"] == 1
        assert updated_context_ref.startswith("PRJ-loop")
        
        # 새 버전 확인
        updated_context = engine.project_contexts.get(updated_context_ref)
        if updated_context:
            assert updated_context.version == 2
            assert updated_context.baseline_state["current_revenue"] == 1200000000
