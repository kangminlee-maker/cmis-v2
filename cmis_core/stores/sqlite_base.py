"""SQLite store base utilities.

저장 경로 규칙:
- 기본: <project_root>/.cmis/
- 테스트/격리: 환경변수 `CMIS_STORAGE_ROOT`가 있으면 그 경로를 root로 사용
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
import sqlite3


@dataclass(frozen=True)
class StoragePaths:
    """스토리지 경로 집합.

    기본 규칙:
    - storage_root 아래에 `.cmis/`를 생성하고, 그 하위에 DB/아티팩트/캐시/런 뷰를 저장합니다.
    - 테스트/격리: 환경변수 `CMIS_STORAGE_ROOT`가 있으면 이를 storage_root로 사용합니다.
    """

    storage_root: Path
    cmis_dir: Path
    db_dir: Path
    runs_dir: Path
    artifacts_dir: Path
    cache_dir: Path
    results_dir: Path
    reality_graphs_dir: Path
    value_store_dir: Path

    @property
    def evidence_cache_db_path(self) -> Path:
        """legacy evidence_cache.db 위치."""

        return self.cmis_dir / "evidence_cache.db"

    @staticmethod
    def resolve(project_root: Optional[Path] = None) -> "StoragePaths":
        env_root = os.getenv("CMIS_STORAGE_ROOT")
        root = Path(env_root) if env_root else (Path(project_root) if project_root else Path.cwd())
        cmis_dir = root / ".cmis"
        db_dir = cmis_dir / "db"
        runs_dir = cmis_dir / "runs"
        artifacts_dir = cmis_dir / "artifacts"
        cache_dir = cmis_dir / "cache"
        results_dir = cache_dir / "results"
        reality_graphs_dir = cmis_dir / "reality_graphs"
        value_store_dir = cmis_dir / "value_store"

        # NOTE: StoragePaths.resolve()는 런타임 경로를 보장합니다.
        # (단일 노드/테스트 모두 동일 규칙)
        for p in [
            db_dir,
            runs_dir,
            artifacts_dir,
            cache_dir,
            results_dir,
            reality_graphs_dir,
            value_store_dir,
        ]:
            p.mkdir(parents=True, exist_ok=True)

        return StoragePaths(
            storage_root=root,
            cmis_dir=cmis_dir,
            db_dir=db_dir,
            runs_dir=runs_dir,
            artifacts_dir=artifacts_dir,
            cache_dir=cache_dir,
            results_dir=results_dir,
            reality_graphs_dir=reality_graphs_dir,
            value_store_dir=value_store_dir,
        )


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    """SQLite 연결 (non-thread-safe 사용은 호출자가 책임)"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

