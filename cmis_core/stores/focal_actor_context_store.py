"""FocalActorContextStore (SQLite).

cmis.yaml의 store key는 `focal_actor_context_store`이며,
`FocalActorContext`(PRJ-*)를 저장합니다.

Phase 1 목표:
- PRJ 컨텍스트를 sqlite에 저장/조회(최신/버전)
- context_binding/learning 경로에서 "store 우선, 없으면 fallback"을 가능하게 함

저장 규칙(Phase 1):
- `context_id`는 base PRJ id로 취급합니다.
  - 예: PRJ-abc-v2 → context_id=PRJ-abc, version=2
- `record_json`은 dataclass 전체를 저장합니다.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from cmis_core.stores.sqlite_base import StoragePaths, connect_sqlite
from cmis_core.types import FocalActorContext


def _split_context_id(focal_actor_context_id: str) -> Tuple[str, Optional[int]]:
    """focal_actor_context_id에서 base id와 버전을 추출합니다.

    예:
    - "PRJ-abc" → ("PRJ-abc", None)
    - "PRJ-abc-v2" → ("PRJ-abc", 2)
    """

    pid = str(focal_actor_context_id or "").strip()
    if not pid:
        return "", None

    if "-v" not in pid:
        return pid, None

    base, _, tail = pid.rpartition("-v")
    if not base:
        return pid, None

    try:
        ver = int(tail)
    except (TypeError, ValueError):
        return pid, None

    return base, ver


class FocalActorContextStore:
    """FocalActorContext(PRJ-*) 버전 관리 스토어."""

    def __init__(self, *, project_root: Optional[Path] = None, db_path: Optional[Path] = None) -> None:
        self.paths = StoragePaths.resolve(project_root)
        self.db_path = db_path or (self.paths.db_dir / "contexts.db")
        self.conn = connect_sqlite(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS focal_actor_contexts (
                context_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                versioned_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                previous_version_id TEXT,
                focal_actor_id TEXT,
                record_json TEXT NOT NULL,
                PRIMARY KEY (context_id, version)
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_focal_actor_contexts_context_id ON focal_actor_contexts(context_id)")
        self.conn.commit()

    def save(self, record: FocalActorContext) -> None:
        """컨텍스트 레코드를 저장(UPSERT)합니다."""

        base_id, parsed_version = _split_context_id(record.focal_actor_context_id)
        context_id = base_id or record.focal_actor_context_id
        version = int(getattr(record, "version", 1) or 1)
        if parsed_version is not None:
            version = int(parsed_version)

        created_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(asdict(record), ensure_ascii=False)

        self.conn.execute(
            """
            INSERT OR REPLACE INTO focal_actor_contexts (
                context_id, version, versioned_id, created_at, previous_version_id, focal_actor_id, record_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                context_id,
                version,
                            str(record.focal_actor_context_id),
                created_at,
                record.previous_version_id,
                record.focal_actor_id,
                payload,
            ),
        )
        self.conn.commit()

    def get_latest(self, focal_actor_context_id: str) -> Optional[FocalActorContext]:
        """base id 기준 최신 버전을 조회합니다."""

        base_id, _ = _split_context_id(focal_actor_context_id)
        context_id = base_id or str(focal_actor_context_id)

        cur = self.conn.execute(
            """
            SELECT record_json
            FROM focal_actor_contexts
            WHERE context_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (context_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        return self._parse_record_json(row[0])

    def get_by_version(self, focal_actor_context_id: str, version: int) -> Optional[FocalActorContext]:
        """base id + version으로 특정 버전을 조회합니다."""

        base_id, _ = _split_context_id(focal_actor_context_id)
        context_id = base_id or str(focal_actor_context_id)

        cur = self.conn.execute(
            """
            SELECT record_json
            FROM focal_actor_contexts
            WHERE context_id = ? AND version = ?
            """,
            (context_id, int(version)),
        )
        row = cur.fetchone()
        if not row:
            return None

        return self._parse_record_json(row[0])

    def list_versions(self, focal_actor_context_id: str) -> List[int]:
        """base id의 저장된 버전 목록을 반환합니다."""

        base_id, _ = _split_context_id(focal_actor_context_id)
        context_id = base_id or str(focal_actor_context_id)

        cur = self.conn.execute(
            """
            SELECT version
            FROM focal_actor_contexts
            WHERE context_id = ?
            ORDER BY version ASC
            """,
            (context_id,),
        )
        return [int(r[0]) for r in cur.fetchall()]

    @staticmethod
    def _parse_record_json(record_json: str) -> FocalActorContext:
        data: Dict[str, Any] = json.loads(record_json or "{}")
        if not isinstance(data, dict):
            data = {}
        # legacy key migration (best-effort): project_context_id -> focal_actor_context_id
        if "project_context_id" in data:
            if "focal_actor_context_id" not in data:
                data["focal_actor_context_id"] = data.get("project_context_id")
            data.pop("project_context_id", None)
        return FocalActorContext(**data)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
