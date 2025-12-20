"""Search Strategy v3 registry (SSV3-01).

목표:
- YAML 기반 전략 레지스트리를 로드/검증하고, 결정적(deterministic) digest를 pinning 합니다.
- 런타임은 registry_digest를 pin하여 재현성을 확보합니다.

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 1.3 StrategyRegistry, 5.6 확정 결정)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

from cmis_core.digest import canonical_digest


class StrategyRegistryError(ValueError):
    """Search Strategy v3 registry validation/compile 오류."""


@dataclass(frozen=True)
class StrategyRef:
    """Versioned registry reference pinned to a digest."""

    registry_version: int
    registry_digest: str  # sha256:...
    compiled_at: str  # ISO8601
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderConfig:
    """SERP provider configuration (v3)."""

    provider_id: str
    adapter: str  # "serpapi" | "tavily" | "google_cse" | ...
    api_key_ref: Optional[str]
    default_timeout_sec: int = 10
    rate_limit_qps: float = 1.0
    burst: int = 2
    cache_ttl_sec: int = 86400
    cost_model: Optional[Dict[str, Any]] = None
    locale_mapping: Dict[str, str] = field(default_factory=dict)
    provider_config_digest: str = ""  # sha256:... (canonicalized ProviderConfig without this field)
    notes: Dict[str, Any] = field(default_factory=dict)

    def compute_digest(self) -> str:
        """provider_config_digest를 결정적으로 계산합니다."""

        # digest에 자기 자신(provider_config_digest)을 포함하면 순환 참조가 되므로 제외합니다.
        payload = {
            "provider_id": self.provider_id,
            "adapter": self.adapter,
            "api_key_ref": self.api_key_ref,
            "default_timeout_sec": self.default_timeout_sec,
            "rate_limit_qps": self.rate_limit_qps,
            "burst": self.burst,
            "cache_ttl_sec": self.cache_ttl_sec,
            "cost_model": self.cost_model,
            "locale_mapping": self.locale_mapping,
            "notes": self.notes,
        }
        return canonical_digest(payload)


def _utc_now_iso_z() -> str:
    """UTC ISO8601 (Z-notation) timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_dict(obj: Any, *, where: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise StrategyRegistryError(f"{where} must be a dict")
    return obj


def _ensure_list(obj: Any, *, where: str) -> List[Any]:
    if not isinstance(obj, list):
        raise StrategyRegistryError(f"{where} must be a list")
    return obj


def _ensure_str(obj: Any, *, where: str) -> str:
    if not isinstance(obj, str) or obj.strip() == "":
        raise StrategyRegistryError(f"{where} must be a non-empty string")
    return obj


def _ensure_int(obj: Any, *, where: str) -> int:
    if not isinstance(obj, int):
        raise StrategyRegistryError(f"{where} must be an int")
    return obj


def _ensure_float(obj: Any, *, where: str) -> float:
    if not isinstance(obj, (int, float)):
        raise StrategyRegistryError(f"{where} must be a number")
    return float(obj)


class StrategyRegistryV3:
    """Search Strategy v3 registry (YAML -> compiled)."""

    def __init__(self, yaml_path: str | Path = "config/search_strategy_registry_v3.yaml"):
        self.yaml_path = Path(yaml_path)

        self._compiled: Optional[Dict[str, Any]] = None
        self._providers: Dict[str, ProviderConfig] = {}
        self._metrics: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._phases_allowed: Optional[List[str]] = None
        self._strategy_ref: Optional[StrategyRef] = None

    def compile(self) -> None:
        """YAML을 로드/검증 후 compiled registry를 생성합니다."""

        if not self.yaml_path.exists():
            raise StrategyRegistryError(f"Registry YAML not found: {self.yaml_path}")

        raw = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8")) or {}
        doc = _ensure_dict(raw, where="registry root")

        registry_version = _ensure_int(doc.get("registry_version"), where="registry_version")

        phases_allowed_raw = doc.get("phases_allowed")
        phases_allowed: Optional[List[str]] = None
        if phases_allowed_raw is not None:
            phases_allowed = []
            for i, p in enumerate(_ensure_list(phases_allowed_raw, where="phases_allowed")):
                phases_allowed.append(_ensure_str(p, where=f"phases_allowed[{i}]"))
        self._phases_allowed = phases_allowed

        providers_raw = _ensure_dict(doc.get("providers"), where="providers")
        providers: Dict[str, ProviderConfig] = {}
        for provider_id, cfg_raw in providers_raw.items():
            if not isinstance(provider_id, str) or provider_id.strip() == "":
                raise StrategyRegistryError("providers keys must be non-empty strings")
            cfg = _ensure_dict(cfg_raw, where=f"providers.{provider_id}")

            adapter = _ensure_str(cfg.get("adapter"), where=f"providers.{provider_id}.adapter")
            api_key_ref = cfg.get("api_key_ref")
            if api_key_ref is not None:
                api_key_ref = _ensure_str(api_key_ref, where=f"providers.{provider_id}.api_key_ref")

            default_timeout_sec = int(cfg.get("default_timeout_sec", 10))
            rate_limit_qps = _ensure_float(cfg.get("rate_limit_qps", 1.0), where=f"providers.{provider_id}.rate_limit_qps")
            burst = int(cfg.get("burst", 2))
            cache_ttl_sec = int(cfg.get("cache_ttl_sec", 86400))

            locale_mapping_raw = cfg.get("locale_mapping", {}) or {}
            locale_mapping = _ensure_dict(locale_mapping_raw, where=f"providers.{provider_id}.locale_mapping")
            locale_mapping_out: Dict[str, str] = {}
            for k, v in locale_mapping.items():
                locale_mapping_out[_ensure_str(k, where=f"providers.{provider_id}.locale_mapping key")] = _ensure_str(
                    v,
                    where=f"providers.{provider_id}.locale_mapping[{k}]",
                )

            cost_model_raw = cfg.get("cost_model")
            if cost_model_raw is not None:
                cost_model = _ensure_dict(cost_model_raw, where=f"providers.{provider_id}.cost_model")
            else:
                cost_model = None

            notes_raw = cfg.get("notes", {}) or {}
            notes = _ensure_dict(notes_raw, where=f"providers.{provider_id}.notes")

            pc = ProviderConfig(
                provider_id=provider_id,
                adapter=adapter,
                api_key_ref=api_key_ref,
                default_timeout_sec=default_timeout_sec,
                rate_limit_qps=rate_limit_qps,
                burst=burst,
                cache_ttl_sec=cache_ttl_sec,
                cost_model=cost_model,
                locale_mapping=locale_mapping_out,
                provider_config_digest="",
                notes=notes,
            )
            pc_digest = pc.compute_digest()
            providers[provider_id] = ProviderConfig(
                provider_id=pc.provider_id,
                adapter=pc.adapter,
                api_key_ref=pc.api_key_ref,
                default_timeout_sec=pc.default_timeout_sec,
                rate_limit_qps=pc.rate_limit_qps,
                burst=pc.burst,
                cache_ttl_sec=pc.cache_ttl_sec,
                cost_model=pc.cost_model,
                locale_mapping=pc.locale_mapping,
                provider_config_digest=pc_digest,
                notes=pc.notes,
            )

        metrics_raw = _ensure_dict(doc.get("metrics"), where="metrics")
        metrics: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for metric_id, per_policy in metrics_raw.items():
            metric_id = _ensure_str(metric_id, where="metrics key(metric_id)")
            per_policy_dict = _ensure_dict(per_policy, where=f"metrics.{metric_id}")

            out_per_policy: Dict[str, Dict[str, Any]] = {}
            for policy_ref, plan in per_policy_dict.items():
                policy_ref = _ensure_str(policy_ref, where=f"metrics.{metric_id} policy_ref key")
                plan_dict = _ensure_dict(plan, where=f"metrics.{metric_id}.{policy_ref}")

                phases = _ensure_list(plan_dict.get("phases"), where=f"metrics.{metric_id}.{policy_ref}.phases")
                for idx, phase in enumerate(phases):
                    phase_dict = _ensure_dict(phase, where=f"metrics.{metric_id}.{policy_ref}.phases[{idx}]")

                    phase_id = _ensure_str(phase_dict.get("phase_id"), where=f"metrics.{metric_id}.{policy_ref}.phases[{idx}].phase_id")
                    if phases_allowed is not None and phase_id not in phases_allowed:
                        raise StrategyRegistryError(
                            f"Unknown phase_id '{phase_id}' (allowed={phases_allowed}) in metrics.{metric_id}.{policy_ref}.phases[{idx}]"
                        )

                    provider_ids = _ensure_list(
                        phase_dict.get("providers"),
                        where=f"metrics.{metric_id}.{policy_ref}.phases[{idx}].providers",
                    )
                    for p_i, p in enumerate(provider_ids):
                        p = _ensure_str(p, where=f"metrics.{metric_id}.{policy_ref}.phases[{idx}].providers[{p_i}]")
                        if p not in providers:
                            raise StrategyRegistryError(
                                f"Unknown provider '{p}' referenced in metrics.{metric_id}.{policy_ref}.phases[{idx}].providers[{p_i}]"
                            )

                    query_templates = _ensure_list(
                        phase_dict.get("query_templates"),
                        where=f"metrics.{metric_id}.{policy_ref}.phases[{idx}].query_templates",
                    )
                    for q_i, q in enumerate(query_templates):
                        _ensure_str(q, where=f"metrics.{metric_id}.{policy_ref}.phases[{idx}].query_templates[{q_i}]")

                out_per_policy[policy_ref] = plan_dict

            metrics[metric_id] = out_per_policy

        compiled: Dict[str, Any] = {
            "registry_version": registry_version,
            "phases_allowed": phases_allowed,
            "providers": {pid: providers[pid] for pid in providers.keys()},
            "metrics": metrics,
        }
        registry_digest = canonical_digest(compiled)

        self._compiled = compiled
        self._providers = providers
        self._metrics = metrics
        self._strategy_ref = StrategyRef(
            registry_version=registry_version,
            registry_digest=registry_digest,
            compiled_at=_utc_now_iso_z(),
        )

    def get_strategy_ref(self) -> StrategyRef:
        """현재 registry의 pinned StrategyRef를 반환합니다."""

        if self._strategy_ref is None:
            self.compile()
        assert self._strategy_ref is not None
        return self._strategy_ref

    def get_provider_config(self, provider_id: str) -> ProviderConfig:
        """provider_id에 해당하는 ProviderConfig를 반환합니다."""

        if not self._providers:
            self.compile()
        provider_id = _ensure_str(provider_id, where="provider_id")
        if provider_id not in self._providers:
            raise StrategyRegistryError(f"Unknown provider_id: {provider_id}")
        return self._providers[provider_id]

    def resolve_metric_plan_template(self, metric_id: str, policy_ref: str) -> Dict[str, Any]:
        """metric_id + policy_ref에 대한 plan template(dict)를 반환합니다."""

        if not self._metrics:
            self.compile()

        metric_id = _ensure_str(metric_id, where="metric_id")
        policy_ref = _ensure_str(policy_ref, where="policy_ref")

        if metric_id not in self._metrics:
            raise StrategyRegistryError(f"Unknown metric_id: {metric_id}")
        per_policy = self._metrics[metric_id]
        if policy_ref not in per_policy:
            raise StrategyRegistryError(f"Unknown policy_ref for metric '{metric_id}': {policy_ref}")
        # 반환값이 호출자에 의해 mutate될 수 있으므로 copy를 제공합니다.
        # (deep copy는 필요 시 상위 레이어에서 수행)
        return dict(per_policy[policy_ref])

    def as_compiled(self) -> Mapping[str, Any]:
        """테스트/디버깅용 compiled registry view."""

        if self._compiled is None:
            self.compile()
        assert self._compiled is not None
        return self._compiled
