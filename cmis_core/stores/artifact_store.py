"""ArtifactStore (local object_store + SQLite meta).

Artifact(ART-*)는 리포트/차트/샘플/중간 산출물 등 "대용량/파일 기반" 결과를 저장합니다.

Phase 1 목표:
- 파일은 `.cmis/artifacts/`에 저장
- 메타데이터는 `.cmis/db/artifacts.db`에 저장

주의:
- Phase 1에서는 로컬 파일 백엔드를 object_store로 취급합니다.

BF-00 목표(확장):
- 업로드 파일 및 대용량 산출물(ValidationReport/PreviewReport)을 ART로 저장
- sha256/size/mime/original_filename 메타를 저장하여 결정성/감사를 지원
- CLI/log에는 원문/대량 데이터가 아니라 ART ref만 남기도록 설계(누출 방지)
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import uuid
from typing import Any, Dict, Optional, Tuple

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
                sha256 TEXT,
                size_bytes INTEGER,
                original_filename TEXT,
                meta_json TEXT NOT NULL
            )
            """
        )
        self._ensure_columns()
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_sha256 ON artifacts(sha256)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_sha256_size ON artifacts(sha256, size_bytes)")
        self.conn.commit()

    def _ensure_columns(self) -> None:
        """구버전 artifacts 테이블에 누락된 컬럼을 best-effort로 추가합니다."""

        cols = self._column_names("artifacts")
        to_add: list[Tuple[str, str]] = []
        if "sha256" not in cols:
            to_add.append(("sha256", "TEXT"))
        if "size_bytes" not in cols:
            to_add.append(("size_bytes", "INTEGER"))
        if "original_filename" not in cols:
            to_add.append(("original_filename", "TEXT"))

        for name, typ in to_add:
            self.conn.execute(f"ALTER TABLE artifacts ADD COLUMN {name} {typ}")

    def _column_names(self, table: str) -> set[str]:
        cur = self.conn.execute(f"PRAGMA table_info({table})")
        return {str(r[1]) for r in cur.fetchall()}

    @staticmethod
    def _sha256_hex(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _guess_mime_type(*, filename: Optional[str]) -> str:
        if filename:
            guessed, _ = mimetypes.guess_type(filename)
            if guessed:
                return str(guessed)
        return "application/octet-stream"

    @staticmethod
    def _safe_suffix(*, filename: Optional[str], fallback: str = ".bin") -> str:
        if not filename:
            return fallback
        suffix = Path(filename).suffix
        if not suffix:
            return fallback
        # Path.suffix includes leading dot. Keep only safe characters.
        safe = "".join([c for c in suffix if c.isalnum() or c in "._-"])
        if not safe.startswith("."):
            safe = f".{safe}"
        if safe in {".", ".."}:
            return fallback
        if len(safe) > 16:
            return fallback
        return safe

    def _find_existing_by_sha256(self, *, sha256_hex: str, size_bytes: int) -> Optional[str]:
        """sha256/size 기반 best-effort dedupe 조회."""

        cur = self.conn.execute(
            """
            SELECT artifact_id, file_path
            FROM artifacts
            WHERE sha256 = ? AND size_bytes = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (str(sha256_hex), int(size_bytes)),
        )
        row = cur.fetchone()
        if not row:
            return None

        aid, file_path = row
        try:
            if file_path and Path(file_path).exists():
                return str(aid)
        except Exception:
            return None
        return None

    def put_file(
        self,
        file_path: Path,
        *,
        artifact_id: Optional[str] = None,
        kind: str = "file",
        mime_type: Optional[str] = None,
        original_filename: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        dedupe: bool = False,
    ) -> str:
        """파일을 Artifact로 저장합니다(원문/대용량 산출물용).

        주의: dedupe는 best-effort이며, 동일 sha256/size가 이미 존재하면 기존 artifact_id를 반환할 수 있습니다.
        """

        path = Path(file_path)
        data = path.read_bytes()
        filename = str(original_filename) if original_filename is not None else path.name
        return self.put_bytes(
            data,
            artifact_id=artifact_id,
            kind=kind,
            mime_type=mime_type,
            original_filename=filename,
            meta=meta,
            dedupe=dedupe,
        )

    def put_bytes(
        self,
        data: bytes,
        *,
        artifact_id: Optional[str] = None,
        kind: str = "file",
        mime_type: Optional[str] = None,
        original_filename: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        dedupe: bool = False,
    ) -> str:
        """bytes를 Artifact로 저장합니다."""

        b = bytes(data or b"")
        size_bytes = len(b)
        sha = self._sha256_hex(b)

        if dedupe:
            existing = self._find_existing_by_sha256(sha256_hex=sha, size_bytes=size_bytes)
            if existing:
                return existing

        aid = str(artifact_id) if artifact_id else f"ART-{kind}-{uuid.uuid4().hex[:8]}"
        suffix = self._safe_suffix(filename=original_filename, fallback=".bin")
        path = self.artifacts_dir / f"{aid}{suffix}"

        path.write_bytes(b)

        mt = str(mime_type) if mime_type else self._guess_mime_type(filename=original_filename)
        self._upsert_meta(
            artifact_id=aid,
            kind=kind,
            mime_type=mt,
            file_path=path,
            sha256=sha,
            size_bytes=size_bytes,
            original_filename=original_filename,
            meta=(meta or {}),
        )
        return aid

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

        payload_text = json.dumps(data, ensure_ascii=False, indent=2)
        if not payload_text.endswith("\n"):
            payload_text = payload_text + "\n"
        payload_bytes = payload_text.encode("utf-8")
        path.write_text(payload_text, encoding="utf-8")

        self._upsert_meta(
            artifact_id=aid,
            kind=kind,
            mime_type="application/json",
            file_path=path,
            sha256=self._sha256_hex(payload_bytes),
            size_bytes=len(payload_bytes),
            original_filename=f"{aid}.json",
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

        content = str(text)
        if not content.endswith("\n"):
            content = content + "\n"
        path.write_text(content, encoding="utf-8")
        payload_bytes = content.encode("utf-8")

        self._upsert_meta(
            artifact_id=aid,
            kind=kind,
            mime_type="text/plain",
            file_path=path,
            sha256=self._sha256_hex(payload_bytes),
            size_bytes=len(payload_bytes),
            original_filename=f"{aid}.txt",
            meta=(meta or {}),
        )
        return aid

    def get_meta(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """artifact 메타데이터 조회."""

        cur = self.conn.execute(
            """
            SELECT created_at, kind, mime_type, file_path, sha256, size_bytes, original_filename, meta_json
            FROM artifacts
            WHERE artifact_id = ?
            """,
            (str(artifact_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        created_at, kind, mime_type, file_path, sha256, size_bytes, original_filename, meta_json = row
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
            "sha256": sha256,
            "size_bytes": size_bytes,
            "original_filename": original_filename,
            "meta": meta,
        }

    def get_path(self, artifact_id: str) -> Optional[Path]:
        """artifact의 실제 파일 경로를 반환합니다."""

        meta = self.get_meta(artifact_id)
        if not meta:
            return None
        try:
            return Path(str(meta["file_path"]))
        except Exception:
            return None

    def _upsert_meta(
        self,
        *,
        artifact_id: str,
        kind: str,
        mime_type: str,
        file_path: Path,
        sha256: Optional[str] = None,
        size_bytes: Optional[int] = None,
        original_filename: Optional[str] = None,
        meta: Dict[str, Any],
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(meta or {}, ensure_ascii=False)

        self.conn.execute(
            """
            INSERT OR REPLACE INTO artifacts (
                artifact_id, created_at, kind, mime_type, file_path, sha256, size_bytes, original_filename, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(artifact_id),
                created_at,
                str(kind),
                str(mime_type),
                str(file_path),
                str(sha256) if sha256 is not None else None,
                int(size_bytes) if size_bytes is not None else None,
                str(original_filename) if original_filename is not None else None,
                payload,
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
