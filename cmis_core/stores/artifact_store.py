"""ArtifactStore (local object_store + SQLite meta).

Artifact(ART-*)는 리포트/차트/샘플/중간 산출물 등 "대용량/파일 기반" 결과를 저장합니다.

Phase 1 목표:
- 파일은 `.cmis/artifacts/`에 저장
- 메타데이터는 `.cmis/db/artifacts.db`에 저장

주의:
- Phase 1에서는 로컬 파일 백엔드를 object_store로 취급합니다.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from typing import Any, Dict, Optional

from cmis_core.stores.sqlite_base import StoragePaths, connect_sqlite


class ArtifactStore:
    """Artifact 저장소."""

    def __init__(self, *, project_root: Optional[Path] = None, artifacts_dir: Optional[Path] = None, db_path: Optional[Path] = None) -> None:
        self.paths = StoragePaths.resolve(project_root)
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir is not None else (self.paths.cmis_dir / "artifacts")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path or (self.paths.db_dir / "artifacts.db")
        self.conn = connect_sqlite(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                kind TEXT,
                mime_type TEXT,
                file_path TEXT NOT NULL,
                meta_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind)")
        self.conn.commit()

    def put_json(
        self,
        data: Any,
        *,
        artifact_id: Optional[str] = None,
        kind: str = "json",
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """JSON artifact 저장."""

        aid = str(artifact_id) if artifact_id else f"ART-{kind}-{uuid.uuid4().hex[:8]}"
        path = self.artifacts_dir / f"{aid}.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._upsert_meta(
            artifact_id=aid,
            kind=kind,
            mime_type="application/json",
            file_path=path,
            meta=(meta or {}),
        )
        return aid

    def put_text(
        self,
        text: str,
        *,
        artifact_id: Optional[str] = None,
        kind: str = "text",
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """텍스트 artifact 저장."""

        aid = str(artifact_id) if artifact_id else f"ART-{kind}-{uuid.uuid4().hex[:8]}"
        path = self.artifacts_dir / f"{aid}.txt"

        with open(path, "w", encoding="utf-8") as f:
            f.write(str(text))
            if not str(text).endswith("\n"):
                f.write("\n")

        self._upsert_meta(
            artifact_id=aid,
            kind=kind,
            mime_type="text/plain",
            file_path=path,
            meta=(meta or {}),
        )
        return aid

    def get_meta(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """artifact 메타데이터 조회."""

        cur = self.conn.execute(
            """
            SELECT created_at, kind, mime_type, file_path, meta_json
            FROM artifacts
            WHERE artifact_id = ?
            """,
            (str(artifact_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        created_at, kind, mime_type, file_path, meta_json = row
        try:
            meta = json.loads(meta_json or "{}")
        except Exception:
            meta = {}

        return {
            "artifact_id": str(artifact_id),
            "created_at": created_at,
            "kind": kind,
            "mime_type": mime_type,
            "file_path": file_path,
            "meta": meta,
        }

    def _upsert_meta(self, *, artifact_id: str, kind: str, mime_type: str, file_path: Path, meta: Dict[str, Any]) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(meta or {}, ensure_ascii=False)

        self.conn.execute(
            """
            INSERT OR REPLACE INTO artifacts (
                artifact_id, created_at, kind, mime_type, file_path, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(artifact_id), created_at, str(kind), str(mime_type), str(file_path), payload),
        )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
