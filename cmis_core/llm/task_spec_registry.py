"""LLM TaskSpecRegistry (Phase 1).

목적(비개발자 설명):
- LLM에게 시키는 작업(Task)마다 "필요한 능력"과 "기대 출력 형태"를 선언합니다.
- 예: 숫자 추출 작업은 JSON 출력이 가능해야 하고, 특정 최소 입력 토큰을 지원해야 합니다.
- Phase 1에서는 핵심 3개 Task만 명시하고, 나머지는 `_default`로 fallback합니다.

설계 문서:
- dev/docs/architecture/CMIS_LLM_Model_Management_Design_v1.1.0.md (Section 5.2)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from cmis_core.digest import canonical_digest


class TaskSpecRegistryError(ValueError):
    """TaskSpecRegistry YAML validation/compile 오류."""


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_dict(obj: Any, *, where: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise TaskSpecRegistryError(f"{where} must be a dict")
    return obj


def _ensure_list(obj: Any, *, where: str) -> List[Any]:
    if not isinstance(obj, list):
        raise TaskSpecRegistryError(f"{where} must be a list")
    return obj


def _ensure_str(obj: Any, *, where: str) -> str:
    if not isinstance(obj, str) or obj.strip() == "":
        raise TaskSpecRegistryError(f"{where} must be a non-empty string")
    return obj


def _ensure_int(obj: Any, *, where: str) -> int:
    if not isinstance(obj, int):
        raise TaskSpecRegistryError(f"{where} must be an int")
    return obj


def _ensure_bool(obj: Any, *, where: str) -> bool:
    if not isinstance(obj, bool):
        raise TaskSpecRegistryError(f"{where} must be a bool")
    return obj


@dataclass(frozen=True)
class RequiredCapabilities:
    """Task 수행에 필요한 최소 capability."""

    supports_json_mode: Optional[bool] = None
    min_max_input_tokens: Optional[int] = None
    supports_tool_calling: Optional[bool] = None
    multimodal: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if self.supports_json_mode is not None:
            out["supports_json_mode"] = bool(self.supports_json_mode)
        if self.min_max_input_tokens is not None:
            out["min_max_input_tokens"] = int(self.min_max_input_tokens)
        if self.supports_tool_calling is not None:
            out["supports_tool_calling"] = bool(self.supports_tool_calling)
        if self.multimodal is not None:
            out["multimodal"] = bool(self.multimodal)
        return out


@dataclass(frozen=True)
class OutputContract:
    """출력 형식 계약."""

    format: str  # text|structured_text|json
    json_schema_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"format": str(self.format)}
        if self.json_schema_ref:
            out["json_schema_ref"] = str(self.json_schema_ref)
        return out


@dataclass(frozen=True)
class QualityGateSpec:
    """품질 게이트(Phase 1에서는 gate_id만 관리)."""

    gate_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {"gate_id": str(self.gate_id)}


@dataclass(frozen=True)
class TaskSpec:
    """단일 Task 스펙."""

    task_type: str
    required_capabilities: RequiredCapabilities = field(default_factory=RequiredCapabilities)
    output_contract: OutputContract = field(default_factory=lambda: OutputContract(format="text"))
    quality_gates: List[QualityGateSpec] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": str(self.task_type),
            "required_capabilities": self.required_capabilities.to_dict(),
            "output_contract": self.output_contract.to_dict(),
            "quality_gates": [g.to_dict() for g in (self.quality_gates or [])],
        }


@dataclass(frozen=True)
class TaskSpecRegistryRef:
    """Digest로 pinning 가능한 TaskSpecRegistry 참조."""

    schema_version: int
    registry_version: str
    task_spec_digest: str
    compiled_at: str


class TaskSpecRegistry:
    """YAML 기반 TaskSpecRegistry 로더/검증기."""

    def __init__(self, yaml_path: str | Path = "config/llm/task_specs_minimal.yaml") -> None:
        self.yaml_path = Path(yaml_path)
        self._compiled: Optional[Dict[str, Any]] = None
        self._tasks: Dict[str, TaskSpec] = {}
        self._ref: Optional[TaskSpecRegistryRef] = None

    def compile(self) -> None:
        """YAML을 로드/검증 후, 결정적 digest를 계산합니다."""

        if not self.yaml_path.exists():
            raise TaskSpecRegistryError(f"Task specs YAML not found: {self.yaml_path}")

        raw = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8")) or {}
        doc = _ensure_dict(raw, where="task_specs root")

        schema_version = int(doc.get("schema_version", 0))
        if schema_version != 1:
            raise TaskSpecRegistryError(f"Unsupported schema_version: {schema_version} (expected 1)")

        registry_version = _ensure_str(doc.get("registry_version"), where="registry_version")

        tasks_raw = _ensure_dict(doc.get("tasks"), where="tasks")
        tasks: Dict[str, TaskSpec] = {}

        for task_type, spec_raw in tasks_raw.items():
            task_type = _ensure_str(task_type, where="tasks key(task_type)")
            spec = _ensure_dict(spec_raw, where=f"tasks.{task_type}")

            req_caps_raw = spec.get("required_capabilities", {}) or {}
            req_caps = _ensure_dict(req_caps_raw, where=f"tasks.{task_type}.required_capabilities")

            supports_json_mode: Optional[bool] = None
            if "supports_json_mode" in req_caps:
                supports_json_mode = _ensure_bool(req_caps.get("supports_json_mode"), where=f"tasks.{task_type}.required_capabilities.supports_json_mode")

            min_max_input_tokens: Optional[int] = None
            if "min_max_input_tokens" in req_caps:
                min_max_input_tokens = _ensure_int(req_caps.get("min_max_input_tokens"), where=f"tasks.{task_type}.required_capabilities.min_max_input_tokens")

            supports_tool_calling: Optional[bool] = None
            if "supports_tool_calling" in req_caps:
                supports_tool_calling = _ensure_bool(req_caps.get("supports_tool_calling"), where=f"tasks.{task_type}.required_capabilities.supports_tool_calling")

            multimodal: Optional[bool] = None
            if "multimodal" in req_caps:
                multimodal = _ensure_bool(req_caps.get("multimodal"), where=f"tasks.{task_type}.required_capabilities.multimodal")

            caps = RequiredCapabilities(
                supports_json_mode=supports_json_mode,
                min_max_input_tokens=min_max_input_tokens,
                supports_tool_calling=supports_tool_calling,
                multimodal=multimodal,
            )

            out_contract_raw = _ensure_dict(spec.get("output_contract") or {}, where=f"tasks.{task_type}.output_contract")
            fmt = _ensure_str(out_contract_raw.get("format"), where=f"tasks.{task_type}.output_contract.format")
            json_schema_ref = out_contract_raw.get("json_schema_ref")
            if json_schema_ref is not None:
                json_schema_ref = _ensure_str(json_schema_ref, where=f"tasks.{task_type}.output_contract.json_schema_ref")
            out_contract = OutputContract(format=fmt, json_schema_ref=json_schema_ref)

            qg_raw = spec.get("quality_gates", []) or []
            qg_list = _ensure_list(qg_raw, where=f"tasks.{task_type}.quality_gates")
            qg: List[QualityGateSpec] = []
            for i, g in enumerate(qg_list):
                g_d = _ensure_dict(g, where=f"tasks.{task_type}.quality_gates[{i}]")
                qg.append(QualityGateSpec(gate_id=_ensure_str(g_d.get("gate_id"), where=f"tasks.{task_type}.quality_gates[{i}].gate_id")))

            tasks[task_type] = TaskSpec(task_type=task_type, required_capabilities=caps, output_contract=out_contract, quality_gates=qg)

        if "_default" not in tasks:
            raise TaskSpecRegistryError("tasks must include a '_default' entry")

        compiled: Dict[str, Any] = {
            "schema_version": int(schema_version),
            "registry_version": str(registry_version),
            "tasks": {tid: tasks[tid].to_dict() for tid in sorted(tasks.keys())},
        }
        digest = canonical_digest(compiled)

        self._compiled = compiled
        self._tasks = tasks
        self._ref = TaskSpecRegistryRef(
            schema_version=int(schema_version),
            registry_version=str(registry_version),
            task_spec_digest=str(digest),
            compiled_at=_utc_now_iso_z(),
        )

    def get_ref(self) -> TaskSpecRegistryRef:
        """현재 로드된 레지스트리 참조를 반환합니다."""

        if self._ref is None:
            raise TaskSpecRegistryError("TaskSpecRegistry is not compiled yet. Call compile() first.")
        return self._ref

    def get_task_spec(self, task_type: str) -> TaskSpec:
        """task_type에 해당하는 TaskSpec을 반환합니다. 없으면 _default를 반환합니다."""

        tt = str(task_type or "").strip()
        if not tt:
            tt = "_default"
        return self._tasks.get(tt) or self._tasks["_default"]


