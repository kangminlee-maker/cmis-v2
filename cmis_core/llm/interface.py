"""CMIS LLM Interface

BaseLLM 추상 인터페이스 (v2 확장)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Iterator
import json


class BaseLLM(ABC):
    """LLM 추상 인터페이스
    
    모든 Provider가 구현해야 할 인터페이스
    
    v2 확장:
    - call_structured() (JSON 응답)
    - stream() (스트리밍)
    - model override 지원
    """
    
    @abstractmethod
    def call(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,  # Model override
        **kwargs
    ) -> str:
        """LLM 호출
        
        Args:
            prompt: 프롬프트
            context: 컨텍스트 (선택)
            model: 모델 override (None이면 기본 모델)
            **kwargs: temperature, max_tokens 등
        
        Returns:
            LLM 응답 텍스트
        """
        pass
    
    def call_structured(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """구조화된 응답 (JSON)
        
        기본 구현: call() + json.loads()
        Provider별 override: OpenAI JSON mode 등
        
        Args:
            prompt: 프롬프트
            schema: JSON schema (선택)
            context: 컨텍스트
        
        Returns:
            JSON dict
        """
        response_text = self.call(prompt, context, **kwargs)
        
        # JSON 추출 (```json``` 코드 블록 처리)
        import re
        
        # ```json ... ``` 패턴 찾기
        json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
        
        if json_match:
            json_text = json_match.group(1)
        else:
            # {} 패턴 찾기
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            json_text = json_match.group() if json_match else response_text
        
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            # Fallback: 원문 반환
            return {"raw": response_text, "error": "json_parse_failed"}
    
    def stream(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Iterator[str]:
        """스트리밍 응답
        
        기본 구현: 전체 응답을 한 번에 yield
        Provider별 override: 실제 streaming
        
        Args:
            prompt: 프롬프트
            context: 컨텍스트
        
        Yields:
            응답 chunk
        """
        response = self.call(prompt, context, **kwargs)
        yield response
    
    @abstractmethod
    def is_available(self) -> bool:
        """사용 가능 여부
        
        Returns:
            API 키, 환경 등이 정상이면 True
        """
        pass
    
    def is_automated(self) -> bool:
        """자동화 가능 여부
        
        Returns:
            True: 완전 자동화 가능
            False: 사람 개입 필요
        """
        return True  # 기본: 자동화 가능
    
    def get_cost_estimate(self, prompt: str) -> float:
        """비용 추정 (USD)
        
        Args:
            prompt: 프롬프트
        
        Returns:
            예상 비용 (USD)
        """
        return 0.0  # 기본: 무료
    
    def estimate_token_count(self, text: str) -> int:
        """토큰 수 추정
        
        Args:
            text: 텍스트
        
        Returns:
            대략적 토큰 수
        """
        # 간단한 휴리스틱 (4자 ≈ 1토큰)
        return len(text) // 4
    
    def get_info(self) -> Dict[str, Any]:
        """Provider 정보
        
        Returns:
            Provider 메타데이터
        """
        return {
            "provider_id": getattr(self, 'provider_id', 'unknown'),
            "model": getattr(self, 'model', 'unknown'),
            "is_available": self.is_available(),
            "is_automated": self.is_automated(),
        }
