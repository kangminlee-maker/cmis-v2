"""LLM PromptProfileRegistry (Phase 2).

목적(비개발자 설명):
- 프롬프트 프로파일(예: strict_json)을 YAML로 버전 관리하고, digest로 pinning 할 수 있게 합니다.
- ModelSelector/LLMService는 "프로파일 ID"만 다루고, 실제 텍스트는 이 레지스트리에서 로드합니다.

설계 문서:
- dev/docs/architecture/CMIS_LLM_Model_Management_Design_v1.1.0.md (Section 6, 8)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from cmis_core.digest import canonical_digest


class PromptProfileRegistryError(ValueError):
    """PromptProfileRegistry YAML validation/compile 오류."""


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_dict(obj: Any, *, where: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise PromptProfileRegistryError(f"{where} must be a dict")
    return obj


def _ensure_str(obj: Any, *, where: str) -> str:
    if not isinstance(obj, str) or obj.strip() == "":
        raise PromptProfileRegistryError(f"{where} must be a non-empty string")
    return obj


def _ensure_int(obj: Any, *, where: str) -> int:
    if not isinstance(obj, int):
        raise PromptProfileRegistryError(f"{where} must be an int")
    return obj


@dataclass(frozen=True)
class PromptProfile:
    """단일 프롬프트 프로파일."""

    profile_id: str
    description: str
    prefix: str

    def to_dict(self) -> Dict[str, Any]:
        return {"profile_id": str(self.profile_id), "description": str(self.description), "prefix": str(self.prefix)}


@dataclass(frozen=True)
class PromptProfileRegistryRef:
    """Digest로 pinning 가능한 PromptProfileRegistry 참조."""

    schema_version: int
    registry_version: str
    prompt_profile_digest: str
    compiled_at: str


class PromptProfileRegistry:
    """YAML 기반 PromptProfileRegistry 로더/검증기."""

    def __init__(self, yaml_path: str | Path = "config/llm/prompt_profiles.yaml") -> None:
        self.yaml_path = Path(yaml_path)
        self._profiles: Dict[str, PromptProfile] = {}
        self._ref: Optional[PromptProfileRegistryRef] = None

    def compile(self) -> None:
        """YAML을 로드/검증 후 결정적 digest를 계산합니다."""

        if not self.yaml_path.exists():
            raise PromptProfileRegistryError(f"Prompt profiles YAML not found: {self.yaml_path}")

        raw = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8")) or {}
        doc = _ensure_dict(raw, where="prompt_profiles root")

        schema_version = _ensure_int(doc.get("schema_version"), where="schema_version")
        if schema_version != 1:
            raise PromptProfileRegistryError(f"Unsupported schema_version: {schema_version} (expected 1)")

        registry_version = _ensure_str(doc.get("registry_version"), where="registry_version")

        profiles_raw = _ensure_dict(doc.get("profiles"), where="profiles")
        profiles: Dict[str, PromptProfile] = {}
        for pid, p_raw in profiles_raw.items():
            pid = _ensure_str(pid, where="profiles key(profile_id)")
            p = _ensure_dict(p_raw, where=f"profiles.{pid}")
            desc = str(p.get("description", "") or "")
            prefix = str(p.get("prefix", "") or "")
            profiles[pid] = PromptProfile(profile_id=pid, description=desc, prefix=prefix)

        if "default" not in profiles:
            raise PromptProfileRegistryError("profiles must include 'default'")

        compiled: Dict[str, Any] = {
            "schema_version": int(schema_version),
            "registry_version": str(registry_version),
            "profiles": {pid: profiles[pid].to_dict() for pid in sorted(profiles.keys())},
        }
        digest = canonical_digest(compiled)

        self._profiles = profiles
        self._ref = PromptProfileRegistryRef(
            schema_version=int(schema_version),
            registry_version=str(registry_version),
            prompt_profile_digest=str(digest),
            compiled_at=_utc_now_iso_z(),
        )

    def get_ref(self) -> PromptProfileRegistryRef:
        if self._ref is None:
            raise PromptProfileRegistryError("PromptProfileRegistry is not compiled yet. Call compile() first.")
        return self._ref

    def get_profile(self, profile_id: str) -> PromptProfile:
        """profile_id에 해당하는 PromptProfile을 반환합니다. 없으면 default를 반환합니다."""

        pid = str(profile_id or "").strip() or "default"
        return self._profiles.get(pid) or self._profiles["default"]

    def list_profiles(self) -> List[str]:
        return sorted(self._profiles.keys())


