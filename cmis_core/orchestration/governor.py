"""Governor/Guardian: budget + stall control.

Phase 1:
- max_iterations/max_time_sec budget 적용
- stall_threshold는 PolicyEngine v2의 orchestration_profile에서 가져옵니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import time

from cmis_core.policy_engine import PolicyEngine

from .ledgers import Ledgers


@dataclass(frozen=True)
class Budget:
    max_iterations: int = 20
    max_time_sec: int = 300


class Governor:
    """실행 제어(예산/스톨/중단 조건)"""

    def __init__(self, policy_engine: PolicyEngine) -> None:
        self.policy_engine = policy_engine

    def should_stop(
        self,
        ledgers: Ledgers,
        *,
        iteration: int,
        start_time: float,
        budget: Budget,
    ) -> Optional[str]:
        """중단해야 하면 reason 반환, 아니면 None"""
        elapsed = time.time() - start_time

        if iteration >= budget.max_iterations:
            return "max_iterations_exceeded"

        if elapsed >= budget.max_time_sec:
            return "max_time_exceeded"

        return None

    def check_stall(
        self,
        ledgers: Ledgers,
        policy_id: str,
        *,
        stall_key: str,
    ) -> Optional[str]:
        """stall_threshold 초과 시 reason 반환"""
        orch = self.policy_engine.get_orchestration_policy(policy_id)
        current = ledgers.progress_ledger.stall_counters.get(stall_key, 0)
        if current >= orch.stall_threshold:
            return f"stall_threshold_reached:{stall_key}"
        return None

