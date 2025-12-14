"""LLM runtime contract alignment tests (P2-2).

목표:
- LLMService/TaskRouter/LLMRegistry가 cmis.yaml의
  `planes.cognition_plane.llm_runtime`를 정본으로 사용하도록 보장합니다.

주의:
- 외부 네트워크/API 호출 없이 재현 가능해야 합니다.
"""

from __future__ import annotations

from cmis_core.config import CMISConfig
from cmis_core.llm.service import LLMRegistry, TaskRouter
from cmis_core.llm.types import CMISTaskType


def _expected_default_provider_id(config: CMISConfig) -> str:
    llm_runtime = config.get_llm_runtime()
    providers = llm_runtime.get("providers", []) or []

    for p in providers:
        if isinstance(p, dict) and p.get("id"):
            return str(p.get("id"))

    return "mock"


def test_task_router_default_route_uses_llm_runtime() -> None:
    config = CMISConfig()
    expected = _expected_default_provider_id(config)

    router = TaskRouter(config)
    route = router.get_route(CMISTaskType.VALIDATION_SANITY_CHECK)

    assert route is not None
    assert route.provider_id == expected


def test_llm_registry_has_default_provider_even_without_keys() -> None:
    config = CMISConfig()
    registry = LLMRegistry(config)

    default_provider = registry.get_provider("__default__")
    assert default_provider is not None
    assert default_provider.is_available()
