"""Evidence Retry - 재시도 전략

네트워크 오류 등 일시적 실패 시 재시도

2025-12-10: Evidence Engine v2.2
"""

from __future__ import annotations

import time
from typing import Optional, Callable, Any
from functools import wraps

from .evidence_engine import (
    SourceNotAvailableError,
    SourceTimeoutError,
    DataNotFoundError
)


class RetryStrategy:
    """Retry 전략
    
    기능:
    - 지수 백오프 (Exponential backoff)
    - 재시도 횟수 제한
    - 특정 에러만 재시도
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0
    ):
        """
        Args:
            max_attempts: 최대 시도 횟수
            initial_delay: 초기 대기 시간 (초)
            max_delay: 최대 대기 시간 (초)
            backoff_factor: 백오프 계수
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Retry 포함 실행
        
        Args:
            func: 실행할 함수
            *args, **kwargs: 함수 인자
        
        Returns:
            함수 실행 결과
        
        Raises:
            마지막 시도의 예외
        """
        last_exception = None
        delay = self.initial_delay
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            
            except (SourceTimeoutError, SourceNotAvailableError) as e:
                # 재시도 가능한 에러
                last_exception = e
                
                if attempt < self.max_attempts:
                    print(f"Retry {attempt}/{self.max_attempts} after {delay:.1f}s: {e}")
                    time.sleep(delay)
                    delay = min(delay * self.backoff_factor, self.max_delay)
                else:
                    # 마지막 시도 실패
                    print(f"All retries failed: {e}")
            
            except DataNotFoundError:
                # 재시도해도 소용없는 에러
                raise
            
            except Exception as e:
                # 기타 에러 (재시도 안 함)
                print(f"Non-retryable error: {e}")
                raise
        
        # 모든 재시도 실패
        raise last_exception
    
    def should_retry(self, exception: Exception) -> bool:
        """재시도 여부 판단
        
        Args:
            exception: 발생한 예외
        
        Returns:
            재시도하면 True
        """
        # 재시도 가능한 에러
        retryable = (
            SourceTimeoutError,
            SourceNotAvailableError
        )
        
        return isinstance(exception, retryable)


# ========================================
# Decorator 버전
# ========================================

def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0
):
    """Retry decorator
    
    사용 예시:
    ```python
    @retry(max_attempts=3)
    def fetch_data(source, request):
        return source.fetch(request)
    ```
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            strategy = RetryStrategy(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor
            )
            return strategy.execute_with_retry(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


# ========================================
# Context Manager 버전
# ========================================

class RetryContext:
    """Retry context manager
    
    사용 예시:
    ```python
    with RetryContext(max_attempts=3) as retry:
        record = source.fetch(request)
    ```
    """
    
    def __init__(self, max_attempts: int = 3):
        self.strategy = RetryStrategy(max_attempts=max_attempts)
        self.result = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return True
        
        # 재시도 가능한 에러면 suppres
        if self.strategy.should_retry(exc_val):
            return False  # 재시도 필요
        
        return False  # 에러 전파
