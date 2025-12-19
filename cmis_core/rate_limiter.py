"""Rate Limiter - API 호출 제한 관리

Source별 Rate Limiting (Token Bucket 알고리즘)

2025-12-10: Evidence Engine v2.2
"""

from __future__ import annotations

import time
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from collections import defaultdict


class RateLimiter:
    """Rate Limiter (Token Bucket)

    Source별 호출 제한 관리:
    - ECOS: 100 calls/min
    - KOSIS: 1000 calls/day
    - Google: 100 calls/day
    - 기타: 제한 없음
    """

    # YAML에서 로딩 (하드코딩 제거)
    _limits_cache = None

    @classmethod
    def _load_limits(cls) -> Dict[str, Dict[str, Any]]:
        """config/sources/rate_limits.yaml 로딩"""
        if cls._limits_cache is not None:
            return cls._limits_cache

        config_path = Path(__file__).parent.parent / "config" / "sources" / "rate_limits.yaml"

        if not config_path.exists():
            # Fallback: 기본값
            return {
                "ECOS": {"calls": 100, "period": 60, "burst": 10}
            }

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 리스트 → 딕셔너리 변환
        limits = {}
        for limit in data.get("limits", []):
            source_id = limit.pop("source_id")
            limit.pop("note", None)  # note 제거
            limits[source_id] = limit

        cls._limits_cache = limits
        return limits

    @property
    def LIMITS(self):
        """동적 로딩"""
        return self._load_limits()

    def __init__(self):
        """초기화"""
        # Source별 token bucket (초기 토큰 full로 시작)
        self.buckets: Dict[str, Dict] = {}

        # 초기화: 모든 Source에 full tokens
        for source_id, limit in self.LIMITS.items():
            self.buckets[source_id] = {
                "tokens": float(limit["calls"]),  # Full로 시작
                "last_update": time.time()
            }

    def check(self, source_id: str) -> bool:
        """호출 가능 여부 체크

        Args:
            source_id: Source ID

        Returns:
            호출 가능하면 True (token 소비)
        """
        # 제한 없는 Source
        if source_id not in self.LIMITS:
            return True

        limit = self.LIMITS[source_id]
        bucket = self.buckets[source_id]

        # Token 보충 (시간 경과에 따라)
        now = time.time()
        elapsed = now - bucket["last_update"]

        # 초당 token 보충률
        refill_rate = limit["calls"] / limit["period"]
        tokens_to_add = elapsed * refill_rate

        # Token 추가 (최대 calls + burst)
        max_tokens = limit["calls"] + limit["burst"]
        bucket["tokens"] = min(
            bucket["tokens"] + tokens_to_add,
            max_tokens
        )
        bucket["last_update"] = now

        # Token 있으면 소비
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True

        return False

    def wait_time(self, source_id: str) -> float:
        """대기 시간 계산

        Args:
            source_id: Source ID

        Returns:
            대기 시간 (초), 제한 없으면 0
        """
        if source_id not in self.LIMITS:
            return 0.0

        limit = self.LIMITS[source_id]
        bucket = self.buckets[source_id]

        # 현재 token
        now = time.time()
        elapsed = now - bucket["last_update"]
        refill_rate = limit["calls"] / limit["period"]
        tokens_to_add = elapsed * refill_rate
        current_tokens = min(
            bucket["tokens"] + tokens_to_add,
            limit["calls"] + limit["burst"]
        )

        if current_tokens >= 1.0:
            return 0.0

        # 1 token 보충에 걸리는 시간
        time_per_token = limit["period"] / limit["calls"]
        tokens_needed = 1.0 - current_tokens

        return tokens_needed * time_per_token

    def reset(self, source_id: Optional[str] = None):
        """Rate limiter 초기화

        Args:
            source_id: Source ID (None이면 전체)
        """
        if source_id:
            if source_id in self.buckets:
                del self.buckets[source_id]
        else:
            self.buckets.clear()

    def get_stats(self, source_id: str) -> Dict[str, Any]:
        """Rate limiter 통계

        Args:
            source_id: Source ID

        Returns:
            {
                "current_tokens": float,
                "max_tokens": int,
                "calls_per_period": int,
                "period": int,
                "can_call": bool
            }
        """
        if source_id not in self.LIMITS:
            return {
                "limited": False,
                "can_call": True
            }

        limit = self.LIMITS[source_id]
        bucket = self.buckets[source_id]

        # 현재 token 계산
        now = time.time()
        elapsed = now - bucket["last_update"]
        refill_rate = limit["calls"] / limit["period"]
        tokens_to_add = elapsed * refill_rate
        current_tokens = min(
            bucket["tokens"] + tokens_to_add,
            limit["calls"] + limit["burst"]
        )

        return {
            "limited": True,
            "current_tokens": current_tokens,
            "max_tokens": limit["calls"] + limit["burst"],
            "calls_per_period": limit["calls"],
            "period_seconds": limit["period"],
            "can_call": current_tokens >= 1.0,
            "wait_time": self.wait_time(source_id)
        }
