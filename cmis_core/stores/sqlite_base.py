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
    """스토리지 경로 집합"""

    storage_root: Path
    cmis_dir: Path
    db_dir: Path
    runs_dir: Path

    @staticmethod
    def resolve(project_root: Optional[Path] = None) -> "StoragePaths":
        env_root = os.getenv("CMIS_STORAGE_ROOT")
        root = Path(env_root) if env_root else (Path(project_root) if project_root else Path.cwd())
        cmis_dir = root / ".cmis"
        db_dir = cmis_dir / "db"
        runs_dir = cmis_dir / "runs"

        db_dir.mkdir(parents=True, exist_ok=True)
        runs_dir.mkdir(parents=True, exist_ok=True)

        return StoragePaths(storage_root=root, cmis_dir=cmis_dir, db_dir=db_dir, runs_dir=runs_dir)


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    """SQLite 연결 (non-thread-safe 사용은 호출자가 책임)"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

