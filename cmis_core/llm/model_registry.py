"""LLM ModelRegistry (Phase 1).

목적(비개발자 설명):
- CMIS가 사용할 수 있는 "모델 목록"을 YAML로 선언하고, 코드에서는 이를 로드해 사용합니다.
- 모델의 능력(capabilities), 비용(cost), 사용 가능 환경(availability)을 명시적으로 관리해
  모델 선택이 하드코딩/주석이 아니라 "정책+레지스트리" 기반으로 이뤄지도록 합니다.
- 레지스트리는 digest로 고정(pin)할 수 있어, 동일 레지스트리 입력이면 동일 선택을 재현할 수 있습니다.

설계 문서:
- dev/docs/architecture/CMIS_LLM_Model_Management_Design_v1.1.0.md (Section 5.1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

from cmis_core.digest import canonical_digest


class ModelRegistryError(ValueError):
    """ModelRegistry YAML validation/compile 오류."""


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_dict(obj: Any, *, where: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise ModelRegistryError(f"{where} must be a dict")
    return obj


def _ensure_list(obj: Any, *, where: str) -> List[Any]:
    if not isinstance(obj, list):
        raise ModelRegistryError(f"{where} must be a list")
    return obj


def _ensure_str(obj: Any, *, where: str) -> str:
    if not isinstance(obj, str) or obj.strip() == "":
        raise ModelRegistryError(f"{where} must be a non-empty string")
    return obj


def _ensure_int(obj: Any, *, where: str) -> int:
    if not isinstance(obj, int):
        raise ModelRegistryError(f"{where} must be an int")
    return obj


def _ensure_bool(obj: Any, *, where: str) -> bool:
    if not isinstance(obj, bool):
        raise ModelRegistryError(f"{where} must be a bool")
    return obj


def _ensure_float(obj: Any, *, where: str) -> float:
    if not isinstance(obj, (int, float)):
        raise ModelRegistryError(f"{where} must be a number")
    return float(obj)


@dataclass(frozen=True)
class ModelCapabilities:
    """모델 능력(capabilities) 선언."""

    max_input_tokens: int
    max_output_tokens: int
    supports_json_mode: bool
    supports_tool_calling: bool
    multimodal: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_input_tokens": int(self.max_input_tokens),
            "max_output_tokens": int(self.max_output_tokens),
            "supports_json_mode": bool(self.supports_json_mode),
            "supports_tool_calling": bool(self.supports_tool_calling),
            "multimodal": bool(self.multimodal),
        }


@dataclass(frozen=True)
class CostModel:
    """모델 비용(cost model) 선언."""

    currency: str
    input_per_1m_tokens: float
    output_per_1m_tokens: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency": str(self.currency),
            "input_per_1m_tokens": float(self.input_per_1m_tokens),
            "output_per_1m_tokens": float(self.output_per_1m_tokens),
        }


@dataclass(frozen=True)
class Availability:
    """실행 프로파일(dev/test/prod) 기준 사용 가능 여부."""

    allowed_profiles: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        # allowed_profiles는 집합 성격이므로 정렬하여 결정성을 확보합니다.
        return {"allowed_profiles": sorted({str(x) for x in (self.allowed_profiles or []) if str(x).strip()})}


@dataclass(frozen=True)
class ModelSpec:
    """단일 모델 스펙."""

    model_id: str
    provider: str
    display_name: str
    version: str
    capabilities: ModelCapabilities
    cost_model: CostModel
    performance_tier: str  # fast|balanced|accurate|test
    availability: Availability

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": str(self.model_id),
            "provider": str(self.provider),
            "display_name": str(self.display_name),
            "version": str(self.version),
            "capabilities": self.capabilities.to_dict(),
            "cost_model": self.cost_model.to_dict(),
            "performance_tier": str(self.performance_tier),
            "availability": self.availability.to_dict(),
        }


@dataclass(frozen=True)
class ModelRegistryRef:
    """Digest로 pinning 가능한 레지스트리 참조."""

    schema_version: int
    registry_version: str
    registry_digest: str
    compiled_at: str


class ModelRegistry:
    """YAML 기반 ModelRegistry 로더/검증기."""

    def __init__(self, yaml_path: str | Path = "config/llm/model_registry.yaml") -> None:
        self.yaml_path = Path(yaml_path)
        self._compiled: Optional[Dict[str, Any]] = None
        self._models: Dict[str, ModelSpec] = {}
        self._ref: Optional[ModelRegistryRef] = None

    def compile(self) -> None:
        """YAML을 로드/검증 후, 결정적 digest를 계산합니다."""

        if not self.yaml_path.exists():
            raise ModelRegistryError(f"Model registry YAML not found: {self.yaml_path}")

        raw = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8")) or {}
        doc = _ensure_dict(raw, where="model_registry root")

        schema_version = _ensure_int(doc.get("schema_version"), where="schema_version")
        if int(schema_version) != 1:
            raise ModelRegistryError(f"Unsupported schema_version: {schema_version} (expected 1)")

        registry_version = _ensure_str(doc.get("registry_version"), where="registry_version")

        models_raw = _ensure_dict(doc.get("models"), where="models")
        models: Dict[str, ModelSpec] = {}

        for model_id, spec_raw in models_raw.items():
            model_id = _ensure_str(model_id, where="models key(model_id)")
            spec = _ensure_dict(spec_raw, where=f"models.{model_id}")

            provider = _ensure_str(spec.get("provider"), where=f"models.{model_id}.provider")
            display_name = _ensure_str(spec.get("display_name"), where=f"models.{model_id}.display_name")
            version = _ensure_str(spec.get("version"), where=f"models.{model_id}.version")
            performance_tier = _ensure_str(spec.get("performance_tier"), where=f"models.{model_id}.performance_tier")

            caps_raw = _ensure_dict(spec.get("capabilities"), where=f"models.{model_id}.capabilities")
            caps = ModelCapabilities(
                max_input_tokens=_ensure_int(caps_raw.get("max_input_tokens"), where=f"models.{model_id}.capabilities.max_input_tokens"),
                max_output_tokens=_ensure_int(
                    caps_raw.get("max_output_tokens"),
                    where=f"models.{model_id}.capabilities.max_output_tokens",
                ),
                supports_json_mode=_ensure_bool(
                    caps_raw.get("supports_json_mode"),
                    where=f"models.{model_id}.capabilities.supports_json_mode",
                ),
                supports_tool_calling=_ensure_bool(
                    caps_raw.get("supports_tool_calling"),
                    where=f"models.{model_id}.capabilities.supports_tool_calling",
                ),
                multimodal=_ensure_bool(
                    caps_raw.get("multimodal"),
                    where=f"models.{model_id}.capabilities.multimodal",
                ),
            )

            cost_raw = _ensure_dict(spec.get("cost_model"), where=f"models.{model_id}.cost_model")
            cost = CostModel(
                currency=_ensure_str(cost_raw.get("currency"), where=f"models.{model_id}.cost_model.currency"),
                input_per_1m_tokens=_ensure_float(
                    cost_raw.get("input_per_1m_tokens"),
                    where=f"models.{model_id}.cost_model.input_per_1m_tokens",
                ),
                output_per_1m_tokens=_ensure_float(
                    cost_raw.get("output_per_1m_tokens"),
                    where=f"models.{model_id}.cost_model.output_per_1m_tokens",
                ),
            )

            availability_raw = _ensure_dict(spec.get("availability") or {}, where=f"models.{model_id}.availability")
            allowed_profiles_raw = availability_raw.get("allowed_profiles") or []
            allowed_profiles = [str(x) for x in _ensure_list(allowed_profiles_raw, where=f"models.{model_id}.availability.allowed_profiles")]
            avail = Availability(allowed_profiles=allowed_profiles)

            models[model_id] = ModelSpec(
                model_id=model_id,
                provider=provider,
                display_name=display_name,
                version=version,
                capabilities=caps,
                cost_model=cost,
                performance_tier=performance_tier,
                availability=avail,
            )

        compiled: Dict[str, Any] = {
            "schema_version": int(schema_version),
            "registry_version": str(registry_version),
            # digest는 "정규화된 모델 스펙" 기준으로 계산합니다.
            "models": {mid: models[mid].to_dict() for mid in sorted(models.keys())},
        }
        reg_digest = canonical_digest(compiled)

        self._compiled = compiled
        self._models = models
        self._ref = ModelRegistryRef(
            schema_version=int(schema_version),
            registry_version=str(registry_version),
            registry_digest=str(reg_digest),
            compiled_at=_utc_now_iso_z(),
        )

    def get_ref(self) -> ModelRegistryRef:
        """현재 로드된 레지스트리 참조를 반환합니다."""

        if self._ref is None:
            raise ModelRegistryError("ModelRegistry is not compiled yet. Call compile() first.")
        return self._ref

    def get_model(self, model_id: str) -> Optional[ModelSpec]:
        """model_id로 ModelSpec을 조회합니다."""

        return self._models.get(str(model_id))

    def list_models(self) -> List[str]:
        """등록된 모델 ID 목록을 반환합니다."""

        return sorted(self._models.keys())


