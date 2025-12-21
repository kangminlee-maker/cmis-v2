"""CMIS LLM Infrastructure

중앙 LLM 관리 인프라

v2 설계:
- TaskRoute 기반 (Task → Provider + Model + Options)
- Config-driven
- Optimization hooks (cache, rate limit, cost guard)
"""

from .types import CMISTaskType, TaskRoute
from .interface import BaseLLM
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # NOTE: 런타임에서의 import cycle(PolicyEngine ↔ LLMService)을 피하기 위해
    # 타입체크 시점에만 service를 import 합니다.
    from .service import LLMService  # noqa: F401

__all__ = [
    "CMISTaskType",
    "TaskRoute",
    "BaseLLM",
    "LLMService",
]


def __getattr__(name: str) -> Any:
    """Lazy import for heavy modules.

    배경:
    - `cmis_core.policy_engine`가 `cmis_core.llm.policy_types`를 import할 때,
      패키지 초기화(`cmis_core.llm.__init__`)에서 `LLMService`를 즉시 import하면
      PolicyEngine ↔ LLMService 순환 참조가 발생할 수 있습니다.
    """

    if name == "LLMService":
        from .service import LLMService as _LLMService

        return _LLMService
    raise AttributeError(name)
