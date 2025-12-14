"""Context binding layer.

의도:
- `FocalActorContext`(PRJ-*)는 SoT/버전/권한/lineage를 포함하는 '컨텍스트 레코드(모델)'입니다.
- 엔진(World/Pattern/Value/Strategy)에 주입되는 형태는 동일하지 않으며,
  실행 단위 task/workflow step과도 명확히 분리되어야 합니다.

이 모듈은 '레코드(model) ↔ 주입(view/binding)' 경계를 명시합니다.

Phase 1:
- Store 미구현 상태에서도 테스트/런타임을 위해 최소 binding 생성(스텁) 지원
Phase 2+:
- project_context_store(또는 focal_actor_context_store)에서 로딩
- 권한/버전/lineage 정책 강화
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from cmis_core.stores.project_context_store import ProjectContextStore
from cmis_core.types import FocalActorContext


@dataclass(frozen=True)
class FocalActorContextBinding:
    """엔진 주입용 Focal Actor Context binding.

    - 레코드 전체를 그대로 노출하기보다, 엔진들이 공통으로 쓰는 최소 표면만 제공합니다.
    - 내부 구조(assets_profile/constraints_profile 등)는 스키마 발전에 따라 확장될 수 있습니다.
    """

    context_id: str
    focal_actor_id: Optional[str]
    version: int

    scope: Dict[str, Any]
    baseline_state: Dict[str, Any]
    assets_profile: Dict[str, Any]
    constraints_profile: Dict[str, Any]
    preference_profile: Dict[str, Any]
    lineage: Dict[str, Any]

    @classmethod
    def from_record(cls, record: FocalActorContext) -> "FocalActorContextBinding":
        raw_version = getattr(record, "version", None)
        if raw_version is None:
            version = 1
        else:
            try:
                version = int(raw_version)
            except (TypeError, ValueError):
                version = 1

        return cls(
            context_id=record.project_context_id,
            focal_actor_id=record.focal_actor_id,
            version=version,
            scope=dict(record.scope or {}),
            baseline_state=dict(record.baseline_state or {}),
            assets_profile=dict(record.assets_profile or {}),
            constraints_profile=dict(record.constraints_profile or {}),
            preference_profile=dict(record.preference_profile or {}),
            lineage=dict(record.lineage or {}),
        )

    @property
    def capability_traits(self) -> List[Dict[str, Any]]:
        traits = self.assets_profile.get("capability_traits")
        return list(traits) if isinstance(traits, list) else []

    @property
    def hard_constraints(self) -> List[Dict[str, Any]]:
        cs = self.constraints_profile.get("hard_constraints")
        return list(cs) if isinstance(cs, list) else []

    @property
    def soft_preferences(self) -> List[Dict[str, Any]]:
        prefs = self.preference_profile.get("soft_preferences")
        return list(prefs) if isinstance(prefs, list) else []


def resolve_focal_actor_context_binding(
    project_context_id: str,
    *,
    project_root: Optional[Path] = None,
) -> FocalActorContextBinding:
    """FocalActorContextBinding 로딩.

    Phase 1:
    - store가 있으면 우선 로딩 (ProjectContextStore)
    - 없으면 최소 레코드 생성(스텁)으로 fallback

    Args:
        project_context_id: PRJ-* (또는 PRJ-*-vN)
        project_root: 프로젝트 루트(선택). 미지정 시 CWD를 기준으로 `.cmis`를 사용합니다.

    Returns:
        FocalActorContextBinding
    """

    record: Optional[FocalActorContext] = None
    store: Optional[ProjectContextStore] = None
    try:
        store = ProjectContextStore(project_root=project_root)
        record = store.get_latest(project_context_id)
    except Exception:
        record = None
    finally:
        if store is not None:
            store.close()

    if record is None:
        record = FocalActorContext(
            project_context_id=project_context_id,
            scope={},
            assets_profile={
                "capability_traits": [],
                "channels": [],
                "brand_assets": {},
                "organizational_assets": {},
            },
            baseline_state={},
            constraints_profile={},
            preference_profile={},
            focal_actor_id=None,
            lineage={},
        )

    return FocalActorContextBinding.from_record(record)
