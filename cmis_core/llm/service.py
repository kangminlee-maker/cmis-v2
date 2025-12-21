"""CMIS LLM Service

LLM 중앙 관리 서비스 (v2)
"""

from __future__ import annotations

import os
import time
import hashlib
import json
import uuid
from datetime import datetime, timezone, date
from typing import Dict, Any, Optional, List
import logging
from dotenv import load_dotenv

from ..config import CMISConfig
from ..policy_engine import PolicyEngine
from ..stores.run_store import RunStore
from .model_registry import ModelRegistry
from .model_selector import ModelSelector, SelectionDecision, SelectionRequest
from .task_spec_registry import TaskSpecRegistry
from .types import (
    CMISTaskType,
    TaskRoute,
    LLMTrace,
    CostLimitExceededError,
    RateLimitExceededError,
    ProviderNotAvailableError,
)
from .interface import BaseLLM

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


# ========================================
# RateLimiter
# ========================================

class RateLimiter:
    """Rate limiting (Token Bucket)"""

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.tokens = max_per_minute
        self.last_refill = time.time()

    def check_or_wait(self):
        """Rate limit 체크 (대기)"""
        self._refill()

        if self.tokens <= 0:
            # 대기
            wait_time = 60 - (time.time() - self.last_refill)

            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                self._refill()

        self.tokens -= 1

    def _refill(self):
        """토큰 리필"""
        now = time.time()
        elapsed = now - self.last_refill

        if elapsed >= 60:
            self.tokens = self.max_per_minute
            self.last_refill = now


# ========================================
# TaskRouter
# ========================================

class TaskRouter:
    """Task → Route 매핑 관리"""

    def __init__(self, config: CMISConfig):
        self.config = config
        self.routes: Dict[str, TaskRoute] = {}
        self._init_from_config()

    def register_route(self, route: TaskRoute):
        """Route 등록"""
        if route.task_type:
            self.routes[route.task_type.value] = route
        else:
            # Default route
            self.routes["__default__"] = route

    def get_route(self, task_type: CMISTaskType) -> Optional[TaskRoute]:
        """Task → Route 조회

        Fallback chain:
        1. 정확한 매칭
        2. Default route
        3. None
        """
        # 정확한 매칭
        route = self.routes.get(task_type.value)

        if route:
            return route

        # Default route
        default_route = self.routes.get("__default__")

        if default_route:
            logger.warning(
                f"No route for {task_type}, using default"
            )
            return default_route

        return None

    def _init_from_config(self):
        """Config에서 Route 로드.

        v3.6.0 contract:
        - cmis.planes.cognition_plane.llm_runtime

        Phase 1 최소 규칙:
        - llm_runtime에 task별 route 정의가 없으면, providers[0]을 기본 route로 사용합니다.
        """

        llm_runtime = self.config.get_llm_runtime()
        providers = llm_runtime.get("providers", []) or []

        default_provider_id = "mock"
        for p in providers:
            if isinstance(p, dict) and p.get("id"):
                default_provider_id = str(p.get("id"))
                break

        default_model_by_provider = {
            "openai": "gpt-4o-mini",
            "native": "native",
            "mock": "mock",
        }
        default_model = default_model_by_provider.get(default_provider_id, "mock")

        # (선택) llm_runtime.routes를 지원: contract에는 없지만 내부 테스트/확장용으로 허용
        routes_config = llm_runtime.get("routes", {}) or {}
        if not isinstance(routes_config, dict):
            routes_config = {}

        # Task별 route 등록
        for task_str, route_config in routes_config.items():
            try:
                task_type = CMISTaskType(task_str)

                route = TaskRoute(
                    task_type=task_type,
                    provider_id=route_config.get("provider", default_provider_id),
                    model_name=route_config.get("model", default_model),
                    temperature=route_config.get("temperature", 0.2),
                    max_tokens=route_config.get("max_tokens", 1024),
                    mode=route_config.get("mode", "chat"),
                    enable_cache=route_config.get("enable_cache", True),
                )

                self.register_route(route)
                logger.info(f"Route registered: {task_str} → {route.provider_id}/{route.model_name}")

            except ValueError:
                # TaskType 오타 → 경고
                logger.warning(f"Unknown CMISTaskType in config: {task_str}")
                continue

        # Default route (Phase 1: always ensure one exists)
        if "__default__" not in self.routes:
            default_route = TaskRoute(
                task_type=None,
                provider_id=default_provider_id,
                model_name=default_model,
                temperature=0.2,
            )
            self.register_route(default_route)
            logger.info(f"Default route: {default_route.provider_id}/{default_route.model_name}")


# ========================================
# LLMRegistry
# ========================================

class LLMRegistry:
    """Provider 관리 (개정)"""

    def __init__(self, config: CMISConfig):
        self.config = config
        self._providers: Dict[str, BaseLLM] = {}
        self._init_from_config()

    def register_provider(self, provider_id: str, provider: BaseLLM):
        """Provider 등록"""
        self._providers[provider_id] = provider
        logger.info(f"Provider registered: {provider_id}")

    def get_provider(self, provider_id: str) -> Optional[BaseLLM]:
        """Provider 조회"""
        return self._providers.get(provider_id)

    def _init_from_config(self):
        """Config에서 Provider 생성"""
        llm_runtime = self.config.get_llm_runtime()
        providers = llm_runtime.get("providers", []) or []

        declared_provider_ids: List[str] = []
        for p in providers:
            if isinstance(p, dict) and p.get("id"):
                declared_provider_ids.append(str(p.get("id")))

        # Provider 생성 및 등록 (declarative allowlist)
        for pid in declared_provider_ids:
            provider_config: Dict[str, Any] = {"enabled": True}

            # Phase 1: openai/native/mock만 지원 (추가 provider는 후속 작업)
            if pid == "openai":
                provider_config.update(
                    {
                        "api_key_env": "OPENAI_API_KEY",
                        "default_model": "gpt-4o-mini",
                    }
                )

            provider = self._create_provider(pid, provider_config)
            if provider:
                self.register_provider(pid, provider)

        # Default provider: llm_runtime.providers[0] 우선, 없으면 mock
        default_provider_id = declared_provider_ids[0] if declared_provider_ids else "mock"
        if default_provider_id in self._providers:
            self._providers["__default__"] = self._providers[default_provider_id]
            logger.info(f"Default provider set: {default_provider_id}")
            return

        # Fallback: MockLLM
        from .providers import MockLLM

        mock_llm = MockLLM()
        self.register_provider("mock", mock_llm)
        self._providers["__default__"] = mock_llm
        logger.warning("Default provider not available, using mock")

    def _create_provider(self, provider_id: str, config: Dict) -> Optional[BaseLLM]:
        """Provider 생성"""
        from .providers import NativeLLM, OpenAILLM, MockLLM

        try:
            if provider_id == "native":
                return NativeLLM()

            elif provider_id == "openai":
                api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
                api_key = os.getenv(api_key_env)

                default_model = config.get("default_model", "gpt-4o-mini")

                return OpenAILLM(model=default_model, api_key=api_key)

            elif provider_id == "mock":
                return MockLLM()

            else:
                logger.warning(f"Unknown provider: {provider_id}")
                return None

        except ProviderNotAvailableError as e:
            logger.warning(f"Provider {provider_id} not available: {e}")
            return None


# ========================================
# LLMService
# ========================================

class LLMService:
    """LLM 중앙 관리 서비스 (v2)

    책임:
    - TaskType 기반 LLM 호출
    - Route 기반 모델 선택
    - (옵션) Model Management(Phase 1): PolicyEngine의 effective_policy.llm → ModelSelector 선택
    - Optimization (cache, rate limit, cost)
    - Trace 기록
    """

    def __init__(
        self,
        config: CMISConfig,
        *,
        policy_engine: Optional[PolicyEngine] = None,
        run_store: Optional[RunStore] = None,
        model_registry: Optional[ModelRegistry] = None,
        task_specs: Optional[TaskSpecRegistry] = None,
        model_selector: Optional[ModelSelector] = None,
    ) -> None:
        self.config = config

        # 핵심 컴포넌트
        self.registry = LLMRegistry(config)
        self.router = TaskRouter(config)

        # Model Management (Phase 1) — best-effort / opt-in
        self.policy_engine = policy_engine
        self.run_store = run_store
        self.model_registry = model_registry
        self.task_specs = task_specs
        self.model_selector = model_selector

        # Optimization/Guardrails 설정 로드 (llm_runtime)
        llm_runtime = config.get_llm_runtime()
        opt_config = llm_runtime.get("optimization", {}) or {}
        if not isinstance(opt_config, dict):
            opt_config = {}

        guardrails = llm_runtime.get("guardrails", {}) or {}
        self.guardrails: Dict[str, Any] = guardrails if isinstance(guardrails, dict) else {}

        # Cache
        self.enable_caching = opt_config.get("enable_caching", False)
        self.cache: Dict[str, str] = {}

        # Rate limiter
        rate_limit = opt_config.get("rate_limit_per_minute", 0)
        self.rate_limiter = RateLimiter(rate_limit) if rate_limit > 0 else None

        # Cost guard
        self.max_cost_per_day = opt_config.get("max_cost_per_day", float('inf'))
        self.daily_cost = 0.0
        self.daily_reset_date = date.today()

        # 추적
        self.total_cost = 0.0
        self.call_count = 0
        self.traces: List[LLMTrace] = []

    # -----------------------------
    # Model Management (Phase 1)
    # -----------------------------

    def _ensure_model_management(self) -> None:
        """Model Management(Phase 1) 의존성을 준비합니다.

        목적(비개발자 설명):
        - 기존 TaskRouter 기반 호출은 유지하면서,
          policy_ref를 제공하는 경우에만 "정책+레지스트리 기반 선택"을 수행할 수 있게 합니다.
        """

        if self.policy_engine is None:
            self.policy_engine = PolicyEngine(project_root=self.config.project_root)

        if self.model_registry is None:
            self.model_registry = ModelRegistry(self.config.project_root / "config" / "llm" / "model_registry.yaml")
            self.model_registry.compile()
        else:
            # defensive: external injection이 compile 전일 수 있음
            try:
                _ = self.model_registry.get_ref()
            except Exception:
                self.model_registry.compile()

        if self.task_specs is None:
            self.task_specs = TaskSpecRegistry(self.config.project_root / "config" / "llm" / "task_specs_minimal.yaml")
            self.task_specs.compile()
        else:
            try:
                _ = self.task_specs.get_ref()
            except Exception:
                self.task_specs.compile()

        if self.model_selector is None:
            self.model_selector = ModelSelector(model_registry=self.model_registry, task_specs=self.task_specs)

    def _select_managed(
        self,
        *,
        task_type: CMISTaskType,
        policy_ref: str,
        call_intent: str,
        quality_target: str,
        confidentiality: str,
        budget_remaining_usd: float,
        max_latency_ms: Optional[int],
        attempt_index: int,
        failure_codes: Optional[List[str]] = None,
    ) -> tuple[SelectionDecision, Any]:
        """policy_ref 기반으로 결정적 모델 선택을 수행하고 (decision, effective_policy)를 반환합니다."""

        self._ensure_model_management()
        assert self.policy_engine is not None
        assert self.model_selector is not None

        effective = self.policy_engine.resolve_effective_policy(str(policy_ref))

        req = SelectionRequest(
            task_type=str(task_type.value),
            policy_ref=str(policy_ref),
            effective_policy_digest=str(effective.effective_policy_digest),
            call_intent=str(call_intent),
            quality_target=str(quality_target),
            confidentiality=str(confidentiality),
            budget_remaining_usd=float(budget_remaining_usd),
            max_latency_ms=max_latency_ms,
            attempt_index=int(attempt_index),
            failure_codes=list(failure_codes or []),
        )

        decision = self.model_selector.select(request=req, effective_policy=effective)
        return decision, effective

    @staticmethod
    def _apply_prompt_profile(prompt: str, *, prompt_profile: str) -> str:
        """prompt_profile을 적용합니다(Phase 1: 최소 구현).

        NOTE:
        - Phase 1에서는 prompt_profile을 "강제 출력 규칙" 정도로만 반영합니다.
        - 본격적인 프롬프트 버전 관리는 Phase 2 (Prompt profile registry)에서 수행합니다.
        """

        p = str(prompt or "")
        prof = str(prompt_profile or "default").strip().lower()
        if prof == "strict_json":
            return (
                "중요: 반드시 JSON만 출력하세요. 설명/코드블록/여분 텍스트를 포함하지 마세요.\n"
                "JSON 외의 문자가 섞이면 실패로 처리됩니다.\n\n"
                + p
            )
        return p

    def call(
        self,
        task_type: CMISTaskType,
        prompt: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """LLM 호출 (중앙 진입점)

        알고리즘:
        1. (옵션) ModelSelector 선택(policy_ref 제공 시)
        2. Route 조회 (fallback)
        2. Cache 확인
        3. Rate limit
        4. Cost 체크
        5. Provider 호출
        6. Trace 기록
        """
        # (옵션) model management
        # NOTE: use_model_management는 "명시적으로 사용"을 의미하지만,
        # policy_ref가 제공되면 기본적으로 model management 경로를 우선 시도합니다.
        _ = kwargs.pop("use_model_management", False)
        policy_ref = kwargs.pop("policy_ref", None) or (context or {}).get("policy_ref") or (context or {}).get("policy_id")
        run_id = kwargs.pop("run_id", None) or (context or {}).get("run_id")

        call_intent = str(kwargs.pop("call_intent", "draft") or "draft")
        quality_target = str(kwargs.pop("quality_target", "medium") or "medium")
        confidentiality = str(kwargs.pop("confidentiality", "public") or "public")
        budget_remaining_usd = float(kwargs.pop("budget_remaining_usd", 1.0) or 1.0)
        max_latency_ms = kwargs.pop("max_latency_ms", None)
        attempt_index = int(kwargs.pop("attempt_index", 0) or 0)
        failure_codes = kwargs.pop("failure_codes", None)

        decision: Optional[SelectionDecision] = None
        effective_policy: Optional[Any] = None
        if policy_ref:
            try:
                decision, effective_policy = self._select_managed(
                    task_type=task_type,
                    policy_ref=str(policy_ref),
                    call_intent=call_intent,
                    quality_target=quality_target,
                    confidentiality=confidentiality,
                    budget_remaining_usd=budget_remaining_usd,
                    max_latency_ms=(None if max_latency_ms is None else int(max_latency_ms)),
                    attempt_index=attempt_index,
                    failure_codes=(None if failure_codes is None else list(failure_codes)),
                )
            except Exception:
                # best-effort: 정책/레지스트리 경로가 실패하면 기존 라우팅으로 fallback
                decision = None
                effective_policy = None

        # 1) Route 조회 (fallback 포함)
        route = self.router.get_route(task_type)

        if not route:
            raise ValueError(f"No route for {task_type}")

        # 결정적 선택이 있으면 route를 override(호출/trace 기준)
        if decision is not None:
            route = TaskRoute(
                task_type=task_type,
                provider_id=str(decision.provider),
                model_name=str(decision.model_id),
                temperature=float(route.temperature),
                max_tokens=int(route.max_tokens),
                mode=str(route.mode),
                enable_cache=bool(route.enable_cache),
            )

        # 2. Cache 확인
        if self.enable_caching and route.enable_cache:
            cache_key = self._build_cache_key(task_type, prompt, context, model_name=str(route.model_name))

            if cache_key in self.cache:
                logger.debug(f"Cache hit: {task_type.value}")
                return self.cache[cache_key]

        # 3. Rate limit
        if self.rate_limiter:
            self.rate_limiter.check_or_wait()

        # 4. Cost 체크
        self._check_daily_cost_reset()

        # 5. Provider 조회
        provider = self.registry.get_provider(route.provider_id)

        if not provider:
            # Fallback: default provider
            provider = self.registry.get_provider("__default__")

        if not provider:
            raise ProviderNotAvailableError(
                f"No provider for {route.provider_id}"
            )

        # 6. 비용 추정
        cost = float(decision.estimated_cost_usd) if (decision is not None and decision.estimated_cost_usd is not None) else provider.get_cost_estimate(prompt)

        if self.daily_cost + cost > self.max_cost_per_day:
            raise CostLimitExceededError(
                f"Daily cost limit: {self.daily_cost:.2f} + {cost:.2f} > {self.max_cost_per_day}"
            )

        # 7. LLM 호출
        start_time = time.time()

        # prompt_profile 적용(Phase 1 minimal)
        prompt_to_send = self._apply_prompt_profile(prompt, prompt_profile=(decision.prompt_profile if decision is not None else "default"))

        response = provider.call(
            prompt_to_send,
            context=context,
            model=route.model_name,  # ← Model override!
            temperature=route.temperature,
            max_tokens=route.max_tokens,
            **kwargs
        )

        elapsed = time.time() - start_time

        # 8. 비용 기록
        self.daily_cost += cost
        self.total_cost += cost
        self.call_count += 1

        # 9. Cache 저장
        if self.enable_caching and route.enable_cache:
            self.cache[cache_key] = response

        # 10. Trace 기록 (실제 사용 provider 기준)
        provider_info = provider.get_info()
        used_provider_id = str(provider_info.get("provider_id") or route.provider_id)
        used_model_name = str(route.model_name or provider_info.get("model") or "unknown")
        if used_provider_id != str(route.provider_id):
            used_model_name = str(provider_info.get("model") or used_model_name)

        # (옵션) run_store selection decision 기록
        if decision is not None and run_id and (self.run_store is not None):
            try:
                self.run_store.append_llm_selection_decision(
                    str(run_id),
                    {
                        "task_type": str(task_type.value),
                        "policy_ref": str(policy_ref),
                        "effective_policy_digest": str(decision.effective_policy_digest),
                        "model_registry_digest": str(decision.registry_digest),
                        "task_spec_digest": str(decision.task_spec_digest),
                        "decision": decision.to_dict(),
                        "call_intent": str(call_intent),
                        "quality_target": str(quality_target),
                        "confidentiality": str(confidentiality),
                    },
                )
            except Exception:
                pass

        trace = LLMTrace(
            task_type=task_type.value,
            provider_id=used_provider_id,
            model_name=used_model_name,
            prompt_preview=prompt[:100],
            response_preview=response[:100],
            cost_usd=cost,
            tokens_used=provider.estimate_token_count(prompt + response),
            timestamp=datetime.now(timezone.utc).isoformat(),
            context_summary=self._summarize_context(context)
        )

        self.traces.append(trace)

        logger.info(
            f"LLM call: {task_type.value} → {used_provider_id}/{used_model_name} "
            f"(${cost:.4f}, {elapsed:.2f}s)"
        )

        return response

    def call_structured(
        self,
        task_type: CMISTaskType,
        prompt: str,
        schema: Optional[Dict] = None,
        context: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """구조화된 응답 (JSON)

        Args:
            task_type: Task 유형
            prompt: 프롬프트
            schema: JSON schema (선택)
            context: 컨텍스트

        Returns:
            JSON dict
        """
        # (옵션) model management
        _ = kwargs.pop("use_model_management", False)
        policy_ref = kwargs.pop("policy_ref", None) or (context or {}).get("policy_ref") or (context or {}).get("policy_id")
        run_id = kwargs.pop("run_id", None) or (context or {}).get("run_id")

        call_intent = str(kwargs.pop("call_intent", "extract") or "extract")
        quality_target = str(kwargs.pop("quality_target", "medium") or "medium")
        confidentiality = str(kwargs.pop("confidentiality", "public") or "public")
        budget_remaining_usd = float(kwargs.pop("budget_remaining_usd", 1.0) or 1.0)
        max_latency_ms = kwargs.pop("max_latency_ms", None)
        attempt_index = int(kwargs.pop("attempt_index", 0) or 0)
        failure_codes = kwargs.pop("failure_codes", None)

        decision: Optional[SelectionDecision] = None
        effective_policy: Optional[Any] = None
        if policy_ref:
            try:
                decision, effective_policy = self._select_managed(
                    task_type=task_type,
                    policy_ref=str(policy_ref),
                    call_intent=call_intent,
                    quality_target=quality_target,
                    confidentiality=confidentiality,
                    budget_remaining_usd=budget_remaining_usd,
                    max_latency_ms=(None if max_latency_ms is None else int(max_latency_ms)),
                    attempt_index=attempt_index,
                    failure_codes=(None if failure_codes is None else list(failure_codes)),
                )
            except Exception:
                decision = None
                effective_policy = None

        # Route 조회 (fallback)
        route = self.router.get_route(task_type)

        if not route:
            raise ValueError(f"No route for {task_type}")

        if decision is not None:
            route = TaskRoute(
                task_type=task_type,
                provider_id=str(decision.provider),
                model_name=str(decision.model_id),
                temperature=float(route.temperature),
                max_tokens=int(route.max_tokens),
                mode=str(route.mode),
                enable_cache=bool(route.enable_cache),
            )

        # Provider 조회
        provider = self.registry.get_provider(route.provider_id)

        if not provider:
            provider = self.registry.get_provider("__default__")

        if not provider:
            raise ProviderNotAvailableError("No provider available")

        # 비용 추정
        cost = float(decision.estimated_cost_usd) if (decision is not None and decision.estimated_cost_usd is not None) else provider.get_cost_estimate(prompt)

        # 구조화 호출
        prompt_to_send = self._apply_prompt_profile(prompt, prompt_profile=(decision.prompt_profile if decision is not None else "default"))
        response = provider.call_structured(prompt_to_send, schema, context, model=route.model_name, **kwargs)

        # 비용 기록
        self.daily_cost += cost
        self.total_cost += cost
        self.call_count += 1

        # Trace 기록 (실제 사용 provider 기준)
        provider_info = provider.get_info()
        used_provider_id = str(provider_info.get("provider_id") or route.provider_id)
        used_model_name = str(route.model_name or provider_info.get("model") or "unknown")
        if used_provider_id != str(route.provider_id):
            used_model_name = str(provider_info.get("model") or used_model_name)

        # (옵션) run_store selection decision 기록
        if decision is not None and run_id and (self.run_store is not None):
            try:
                self.run_store.append_llm_selection_decision(
                    str(run_id),
                    {
                        "task_type": str(task_type.value),
                        "policy_ref": str(policy_ref),
                        "effective_policy_digest": str(decision.effective_policy_digest),
                        "model_registry_digest": str(decision.registry_digest),
                        "task_spec_digest": str(decision.task_spec_digest),
                        "decision": decision.to_dict(),
                        "call_intent": str(call_intent),
                        "quality_target": str(quality_target),
                        "confidentiality": str(confidentiality),
                    },
                )
            except Exception:
                pass

        trace = LLMTrace(
            task_type=task_type.value,
            provider_id=used_provider_id,
            model_name=used_model_name,
            prompt_preview=prompt[:100],
            response_preview=str(response)[:100],
            cost_usd=cost,
            tokens_used=provider.estimate_token_count(prompt + str(response)),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self.traces.append(trace)

        return response

    def _build_cache_key(
        self,
        task_type: CMISTaskType,
        prompt: str,
        context: Optional[Dict],
        model_name: str = ""
    ) -> str:
        """Cache 키 생성"""
        context_str = json.dumps(context, sort_keys=True) if context else ""
        key_raw = f"{task_type.value}|{model_name}|{prompt}|{context_str}"

        return hashlib.sha256(key_raw.encode()).hexdigest()[:16]

    def _check_daily_cost_reset(self):
        """일일 비용 리셋"""
        today = date.today()

        if today != self.daily_reset_date:
            logger.info(f"Daily cost reset: {self.daily_cost:.2f} USD")
            self.daily_cost = 0.0
            self.daily_reset_date = today

    def _summarize_context(self, context: Optional[Dict]) -> Optional[Dict]:
        """Context 요약 (보안: 민감 정보 제거)"""
        if not context:
            return None

        # 핵심 정보만
        summary = {}
        safe_keys = ['domain', 'region', 'year', 'metric_id', 'company_name']

        for key in safe_keys:
            if key in context:
                summary[key] = context[key]

        return summary if summary else None

    def get_stats(self) -> Dict:
        """사용 통계"""
        return {
            "total_calls": self.call_count,
            "total_cost_usd": self.total_cost,
            "daily_cost_usd": self.daily_cost,
            "avg_cost_per_call": self.total_cost / self.call_count if self.call_count else 0,
            "cache_size": len(self.cache),
            "traces_count": len(self.traces),
        }

    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        logger.info("LLM cache cleared")

    def save_traces_to_memory_store(self, memory_store):
        """Trace를 memory_store에 저장

        Args:
            memory_store: EvidenceStore 또는 별도 store
        """
        for trace in self.traces:
            memory_id = f"MEM-llm-{uuid.uuid4().hex[:8]}"

            # memory_store 형식으로 변환
            memory_record = {
                "memory_id": memory_id,
                "memory_type": "llm_trace",
                "content_ref": json.dumps({
                    "task_type": trace.task_type,
                    "provider": trace.provider_id,
                    "model": trace.model_name,
                    "cost": trace.cost_usd,
                    "tokens": trace.tokens_used,
                }),
                "created_at": trace.timestamp,
            }

            # 저장 (memory_store API에 따라)
            if hasattr(memory_store, 'save'):
                memory_store.save(memory_record)

        # Trace 초기화
        logger.info(f"Saved {len(self.traces)} traces to memory_store")
        self.traces.clear()


# ========================================
# Factory
# ========================================

def create_llm_service(
    config: Optional[CMISConfig] = None,
    mode: str = "auto"  # auto | mock | openai
) -> LLMService:
    """LLMService 팩토리

    Args:
        config: CMISConfig (None이면 기본 로드)
        mode: LLM 모드
            - "auto": .env 기반 자동 선택 (OpenAI 우선)
            - "mock": MockLLM 사용 (테스트)
            - "openai": OpenAI 강제

    Returns:
        LLMService
    """
    if config is None:
        config = CMISConfig()

    service = LLMService(config)

    # Mode별 Provider 설정
    if mode == "mock":
        # Mock 모드
        from .providers import MockLLM

        mock_llm = MockLLM()
        service.registry.register_provider("mock", mock_llm)
        service.registry._providers["__default__"] = mock_llm
        # mock 모드에서는 외부 호출을 방지하기 위해 route를 강제로 mock으로 고정합니다.
        service.router.routes.clear()
        service.router.register_route(TaskRoute(task_type=None, provider_id="mock", model_name="mock"))

        logger.info("LLMService created (mock mode)")

    elif mode == "openai":
        # OpenAI 강제
        from .providers import OpenAILLM

        try:
            openai_llm = OpenAILLM(model="gpt-4o-mini")
            service.registry.register_provider("openai", openai_llm)
            service.registry._providers["__default__"] = openai_llm
            logger.info("LLMService created (OpenAI mode)")
        except ProviderNotAvailableError:
            logger.warning("OpenAI not available, falling back to mock")
            mode = "mock"

    elif mode == "auto":
        # 자동 선택: OpenAI 우선
        from .providers import OpenAILLM, MockLLM

        try:
            openai_llm = OpenAILLM(model="gpt-4o-mini")
            service.registry.register_provider("openai", openai_llm)
            service.registry._providers["__default__"] = openai_llm
            logger.info("LLMService created (auto → OpenAI)")
        except ProviderNotAvailableError:
            # Fallback: Mock
            mock_llm = MockLLM()
            service.registry.register_provider("mock", mock_llm)
            service.registry._providers["__default__"] = mock_llm
            logger.warning("OpenAI not available, using mock")

    # Default route는 항상 __default__ provider와 정렬합니다.
    default_provider = service.registry.get_provider("__default__")
    if default_provider is not None:
        info = default_provider.get_info()
        provider_id = str(info.get("provider_id") or "mock")
        model_name = str(info.get("model") or "mock")
    else:
        provider_id = "mock"
        model_name = "mock"

    service.router.register_route(TaskRoute(task_type=None, provider_id=provider_id, model_name=model_name))
    logger.info(f"Default route aligned: {provider_id}/{model_name}")

    return service
