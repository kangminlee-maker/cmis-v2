"""Stores factory (local backend).

목표:
- Store 생성/경로 결정을 한 곳으로 모아, 이후 인프라(Postgres/S3 등) 전환 시 변경 지점을 최소화합니다.
- 현재는 local-first( SQLite + 파일 ) 구현만 제공합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cmis_core.evidence_store import EvidenceStore, create_evidence_store

from .artifact_store import ArtifactStore
from .focal_actor_context_store import FocalActorContextStore
from .ledger_store import LedgerStore
from .run_store import RunStore
from .sqlite_base import StoragePaths
from .outcome_store import OutcomeStore


@dataclass(frozen=True)
class StoreFactory:
    """스토어 생성 팩토리.

    설계 의도:
    - project_root를 중심으로 StoragePaths를 고정하고,
      그 경로 규칙 하에서 각 store 인스턴스를 생성합니다.

    NOTE:
    - 반환되는 store 인스턴스는 각각 SQLite 연결을 생성합니다.
    - 호출자가 close() 책임을 갖습니다.
    """

    project_root: Optional[Path] = None

    @property
    def paths(self) -> StoragePaths:
        return StoragePaths.resolve(self.project_root)

    # ---- core stores ----

    def run_store(self) -> RunStore:
        return RunStore(project_root=self.project_root)

    def ledger_store(self) -> LedgerStore:
        return LedgerStore(project_root=self.project_root)

    def artifact_store(self) -> ArtifactStore:
        return ArtifactStore(project_root=self.project_root)

    def focal_actor_context_store(self) -> FocalActorContextStore:
        return FocalActorContextStore(project_root=self.project_root)

    def outcome_store(self) -> OutcomeStore:
        return OutcomeStore(project_root=self.project_root)

    # ---- caches (derived) ----

    def evidence_cache_store(self, *, backend_type: str = "memory") -> EvidenceStore:
        """EvidenceStore 생성.

        backend_type:
        - "memory" (기본): 프로세스 내 캐시
        - "sqlite": `.cmis/evidence_cache.db` 기반 캐시 (legacy)
        """

        return create_evidence_store(backend_type=str(backend_type), project_root=self.project_root)

