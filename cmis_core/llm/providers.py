"""CMIS LLM Providers

BaseLLM 구현체들
"""

from __future__ import annotations

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

from .interface import BaseLLM
from .types import ProviderNotAvailableError

# Load environment variables
load_dotenv()


# ========================================
# NativeLLM
# ========================================

class NativeLLM(BaseLLM):
    """Native 환경 LLM
    
    개념:
    - Native = 현재 작업 중인 LLM 환경
    - Cursor, IDE 내장 LLM 등
    - 추가 비용 없음 (구독 포함)
    
    v2 구현:
    - Rule-based fallback (LLM 실제 호출 없음)
    - v2.5+: 실제 Cursor API 연동
    """
    
    def __init__(self, fallback_provider: Optional[BaseLLM] = None):
        """
        Args:
            fallback_provider: Native 불가 시 Fallback
        """
        self.provider_id = "native"
        self.model = "native"
        
        self._is_native = self._check_native_env()
        self._fallback = fallback_provider
    
    def call(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """LLM 호출
        
        Native: 현재 환경 LLM 사용
        Fallback: 외부 Provider
        """
        if self._is_native:
            # v2: Rule-based (실제 LLM 없음)
            return self._native_process(prompt, context)
        
        elif self._fallback:
            # Fallback Provider 사용
            return self._fallback.call(prompt, context, model, **kwargs)
        
        else:
            raise ProviderNotAvailableError(
                "Native LLM not available and no fallback provider"
            )
    
    def _check_native_env(self) -> bool:
        """Native 환경 체크 (개선)"""
        # 명시적 환경 변수
        if os.getenv('CMIS_NATIVE_MODE') == 'true':
            return True
        
        # Cursor 체크
        if os.getenv('CURSOR_SESSION'):
            return True
        
        # Interactive Python
        import sys
        if hasattr(sys, 'ps1'):
            return True
        
        return False
    
    def _native_process(self, prompt, context):
        """Native 환경 처리
        
        v2: Rule-based (실제 LLM 없음)
        v2.5+: Cursor API 또는 실제 구현
        """
        # v2: Placeholder
        return f"NATIVE_RESPONSE: {prompt[:50]}..."
    
    def is_available(self):
        """항상 사용 가능 (Fallback 있음)"""
        return self._is_native or (self._fallback is not None)
    
    def get_cost_estimate(self, prompt):
        """비용 추정"""
        if self._is_native:
            return 0.0  # Native 무료
        elif self._fallback:
            return self._fallback.get_cost_estimate(prompt)
        else:
            return 0.0


# ========================================
# OpenAILLM
# ========================================

class OpenAILLM(BaseLLM):
    """OpenAI API LLM"""
    
    # 모델별 가격 (per 1M tokens, USD)
    MODEL_COSTS = {
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gpt-4.1-nano": {"input": 0.03, "output": 0.06},
    }
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None
    ):
        """
        Args:
            model: 모델명
            api_key: API 키 (None이면 환경변수)
        """
        self.provider_id = "openai"
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ProviderNotAvailableError(
                "OPENAI_API_KEY required"
            )
        
        # OpenAI client
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ProviderNotAvailableError(
                "openai package required: pip install openai"
            )
    
    def call(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """OpenAI API 호출
        
        Args:
            model: Model override (None이면 self.model)
        """
        model_to_use = model or self.model
        
        # System prompt (CMIS 특화)
        system_prompt = self._build_system_prompt(context)
        
        # API 호출
        response = self.client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 1024),
        )
        
        return response.choices[0].message.content
    
    def _build_system_prompt(self, context: Optional[Dict]) -> str:
        """System prompt 생성 (CMIS 특화)"""
        base = "You are CMIS (Contextual Market Intelligence System) assistant."
        
        if context and context.get("domain"):
            base += f"\nDomain: {context['domain']}"
        
        return base
    
    def is_available(self):
        """API 키 확인"""
        return bool(self.api_key)
    
    def get_cost_estimate(self, prompt: str) -> float:
        """비용 추정"""
        costs = self.MODEL_COSTS.get(self.model, {"input": 0.001, "output": 0.002})
        
        # 토큰 수 추정
        input_tokens = self.estimate_token_count(prompt)
        output_tokens = input_tokens // 2  # 대략 응답이 절반
        
        # 비용 계산
        cost = (
            (input_tokens / 1_000_000) * costs["input"] +
            (output_tokens / 1_000_000) * costs["output"]
        )
        
        return cost


# ========================================
# MockLLM
# ========================================

class MockLLM(BaseLLM):
    """Mock LLM (테스트용)
    
    실제 API 호출 없이 고정 응답 반환
    """
    
    def __init__(
        self,
        responses: Optional[Dict[str, str]] = None,
        default_response: str = "MOCK_RESPONSE"
    ):
        """
        Args:
            responses: {prompt_pattern: response} 매핑
            default_response: 기본 응답
        """
        self.provider_id = "mock"
        self.model = "mock"
        self.responses = responses or {}
        self.default_response = default_response
        
        # 추적
        self.call_history: list = []
    
    def call(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Mock 응답 반환"""
        # 히스토리 기록
        self.call_history.append({
            "prompt": prompt,
            "context": context,
            "model": model,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # 패턴 매칭
        for pattern, response in self.responses.items():
            if pattern in prompt:
                return response
        
        # 기본 응답
        return self.default_response
    
    def is_available(self):
        """항상 사용 가능"""
        return True
    
    def reset(self):
        """히스토리 초기화 (테스트용)"""
        self.call_history.clear()
