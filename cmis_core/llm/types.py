"""CMIS LLM Types

LLM 인프라 타입 정의
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


# ========================================
# CMISTaskType
# ========================================

class CMISTaskType(Enum):
    """CMIS LLM 작업 유형

    v9 Graph-of-Graphs 아키텍처 기반
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Evidence Layer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    EVIDENCE_ACCOUNT_MATCHING = "evidence_account_matching"
    # DART 계정과목 해석
    # Policy: All
    # Model: gpt-4o-mini

    EVIDENCE_NUMBER_EXTRACTION = "evidence_number_extraction"
    # 웹 검색 숫자 추출 (필요 시)
    # Policy: All
    # Model: gpt-4o-mini

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Pattern Layer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    PATTERN_RECOGNITION = "pattern_recognition"
    # R-Graph 패턴 인식
    # Policy: decision_balanced, exploration_friendly
    # Model: gpt-4

    PATTERN_GAP_ANALYSIS = "pattern_gap_analysis"
    # Gap 탐지 및 설명
    # Policy: exploration_friendly
    # Model: gpt-4

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Value Layer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    VALUE_PRIOR_ESTIMATION = "value_prior_estimation"
    # Prior 추정 (Evidence 없을 때)
    # Policy: decision_balanced, exploration_friendly (reporting_strict 금지!)
    # Model: gpt-4.1-nano

    VALUE_FORMULA_DERIVATION = "value_formula_derivation"
    # 공식 유도
    # Policy: All
    # Model: gpt-4o-mini

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Strategy Layer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    STRATEGY_GENERATION = "strategy_generation"
    # 전략 후보 생성
    # Policy: decision_balanced, exploration_friendly
    # Model: claude-3.5-sonnet

    STRATEGY_EVALUATION = "strategy_evaluation"
    # 전략 평가
    # Policy: All
    # Model: gpt-4

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Validation
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    VALIDATION_SANITY_CHECK = "validation_sanity_check"
    # 상식 검증
    # Policy: All
    # Model: gpt-4o-mini


# ========================================
# TaskRoute
# ========================================

@dataclass
class TaskRoute:
    """Task → (Provider, Model, Options) 매핑

    핵심: Task별로 다른 모델/옵션 사용 가능
    """
    task_type: CMISTaskType
    provider_id: str
    model_name: str

    # LLM 옵션
    temperature: float = 0.2
    max_tokens: int = 1024
    mode: str = "chat"  # chat, completion, json

    # Optimization
    enable_cache: bool = True
    cost_weight: float = 1.0

    # 메타
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """직렬화"""
        return {
            "task_type": self.task_type.value if self.task_type else None,
            "provider_id": self.provider_id,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "mode": self.mode,
            "enable_cache": self.enable_cache,
        }


# ========================================
# LLM Trace
# ========================================

@dataclass
class LLMTrace:
    """LLM 호출 추적 (memory_store 연동용)"""
    task_type: str
    provider_id: str
    model_name: str

    prompt_preview: str  # 처음 100자 (보안)
    response_preview: str  # 처음 100자

    cost_usd: float
    tokens_used: int

    timestamp: str

    # 선택
    context_summary: Optional[Dict] = None
    error: Optional[str] = None


# ========================================
# Exceptions
# ========================================

class LLMError(Exception):
    """LLM 기본 오류"""
    pass


class ProviderNotAvailableError(LLMError):
    """Provider 사용 불가"""
    pass


class CostLimitExceededError(LLMError):
    """비용 한도 초과"""
    pass


class RateLimitExceededError(LLMError):
    """Rate limit 초과"""
    pass


