"""Context Learner - ProjectContext 업데이트

Outcome 기반 baseline_state 업데이트 및 버전 관리

2025-12-11: LearningEngine Phase 2
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .types import ProjectContext, Outcome


class ContextLearner:
    """ProjectContext 학습기
    
    역할:
    - baseline_state 업데이트
    - 버전 관리 (version, previous_version_id)
    - Lineage 추적
    """
    
    def __init__(self):
        """초기화"""
        pass
    
    def update_baseline_state(
        self,
        project_context: ProjectContext,
        outcome: Outcome
    ) -> ProjectContext:
        """baseline_state 업데이트 (버전 관리)
        
        Args:
            project_context: 기존 ProjectContext
            outcome: 실제 Outcome
        
        Returns:
            새 버전 ProjectContext
        """
        # 새 baseline_state
        updated_baseline = dict(project_context.baseline_state)
        
        # Outcome.metrics → baseline_state 매핑
        for metric_id, value in outcome.metrics.items():
            if metric_id == "MET-Revenue":
                # Phase 2: quantity_ref 형식
                updated_baseline["current_revenue"] = value
            
            elif metric_id == "MET-N_customers":
                updated_baseline["current_customers"] = value
            
            elif metric_id == "MET-Gross_margin":
                if "margin_structure" not in updated_baseline:
                    updated_baseline["margin_structure"] = {}
                updated_baseline["margin_structure"]["gross_margin"] = value
            
            elif metric_id == "MET-Churn_rate":
                if "margin_structure" not in updated_baseline:
                    updated_baseline["margin_structure"] = {}
                updated_baseline["margin_structure"]["churn_rate"] = value
        
        # as_of 업데이트
        updated_baseline["as_of"] = outcome.as_of
        
        # 새 버전 ID
        new_version = project_context.version + 1
        new_version_id = f"{project_context.project_context_id.split('-v')[0]}-v{new_version}"
        
        # Lineage 업데이트
        from_outcome_ids = project_context.lineage.get("from_outcome_ids", [])
        from_outcome_ids.append(outcome.outcome_id)
        
        updated_lineage = {
            **project_context.lineage,
            "from_outcome_ids": from_outcome_ids,
            "updated_at": datetime.now().isoformat(),
            "updated_by": "learning_engine"
        }
        
        # 새 ProjectContext
        updated_context = ProjectContext(
            project_context_id=new_version_id,
            version=new_version,
            previous_version_id=project_context.project_context_id,
            scope=project_context.scope,
            assets_profile=project_context.assets_profile,
            baseline_state=updated_baseline,
            constraints_profile=project_context.constraints_profile,
            preference_profile=project_context.preference_profile,
            focal_actor_id=project_context.focal_actor_id,
            lineage=updated_lineage
        )
        
        return updated_context
