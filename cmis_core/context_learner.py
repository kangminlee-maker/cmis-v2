"""Context Learner - FocalActorContext 업데이트

Outcome 기반 baseline_state 업데이트 및 버전 관리

2025-12-11: LearningEngine Phase 2
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from .types import FocalActorContext, Outcome


class ContextLearner:
    """FocalActorContext 학습기

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
        focal_actor_context: FocalActorContext,
        outcome: Outcome
    ) -> FocalActorContext:
        """baseline_state 업데이트 (버전 관리)

        Args:
            focal_actor_context: 기존 FocalActorContext
            outcome: 실제 Outcome

        Returns:
            새 버전 FocalActorContext
        """
        # 새 baseline_state
        updated_baseline = dict(focal_actor_context.baseline_state)

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
        new_version = focal_actor_context.version + 1
        new_version_id = f"{focal_actor_context.focal_actor_context_id.split('-v')[0]}-v{new_version}"

        # Lineage 업데이트
        from_outcome_ids = focal_actor_context.lineage.get("from_outcome_ids", [])
        from_outcome_ids.append(outcome.outcome_id)

        updated_lineage = {
            **focal_actor_context.lineage,
            "from_outcome_ids": from_outcome_ids,
            "updated_at": datetime.now().isoformat(),
            "updated_by": "learning_engine"
        }

        # 새 FocalActorContext
        updated_context = FocalActorContext(
            focal_actor_context_id=new_version_id,
            version=new_version,
            previous_version_id=focal_actor_context.focal_actor_context_id,
            scope=focal_actor_context.scope,
            assets_profile=focal_actor_context.assets_profile,
            baseline_state=updated_baseline,
            constraints_profile=focal_actor_context.constraints_profile,
            preference_profile=focal_actor_context.preference_profile,
            focal_actor_id=focal_actor_context.focal_actor_id,
            lineage=updated_lineage
        )

        return updated_context
