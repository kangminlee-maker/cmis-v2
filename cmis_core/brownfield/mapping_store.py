"""MappingStore (BF-03).

Mapping(MAP)은 "업로드 파일(ART) → 정규화 스키마"로의 변환 규칙을 정의합니다.

원칙:
- MappingPatch는 새로운 mapping_version을 생성하는 것으로만 표현합니다.
- mapping_digest는 spec payload(=id/version 제외) 기반 결정적 digest입니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
import uuid
from typing import Any, Dict, Optional, Tuple

from cmis_core.digest import canonical_digest, canonical_json


@dataclass(frozen=True)
class MappingRecord:
    mapping_id: str
    mapping_version: int
    mapping_digest: str
    artifact_id: Optional[str]
    extractor_version: Optional[str]
    schema_version: Optional[int]
    spec: Dict[str, Any]
    created_at: str


class MappingStore:
    """brownfield.db의 mappings 테이블을 다루는 스토어."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _sanitize_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
        # digest 안정성을 위해 id/version 같은 식별자는 spec에서 제외
        cleaned = dict(spec or {})
        cleaned.pop("mapping_id", None)
        cleaned.pop("mapping_version", None)
        cleaned.pop("mapping_digest", None)
        cleaned.pop("created_at", None)
        return cleaned

    def create(
        self,
        spec: Dict[str, Any],
        *,
        mapping_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        extractor_version: Optional[str] = None,
        schema_version: Optional[int] = 1,
    ) -> Tuple[str, int, str]:
        """Mapping을 생성합니다.

        동일 spec payload(=digest)가 이미 존재하면 기존 mapping_id/version을 재사용합니다.
        """

        spec_payload = self._sanitize_spec(spec)
        digest = canonical_digest(spec_payload)

        existing = self._get_by_digest(digest)
        if existing is not None:
            return existing.mapping_id, existing.mapping_version, existing.mapping_digest

        mid = str(mapping_id) if mapping_id else f"MAP-{uuid.uuid4().hex[:10]}"
        version = 1
        created_at = self._now()
        spec_json = canonical_json(spec_payload)

        self.conn.execute(
            """
            INSERT INTO mappings(
                mapping_id, mapping_version, mapping_digest, artifact_id, extractor_version, schema_version, spec_json, spec_ref_artifact_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mid,
                int(version),
                str(digest),
                str(artifact_id) if artifact_id is not None else None,
                str(extractor_version) if extractor_version is not None else None,
                int(schema_version) if schema_version is not None else None,
                spec_json,
                None,
                created_at,
            ),
        )
        return mid, version, digest

    def bump_version(self, mapping_id: str, new_spec: Dict[str, Any]) -> Tuple[str, int, str]:
        """MappingPatch를 반영해 새 버전을 생성합니다."""

        latest = self.get_latest(mapping_id)
        if latest is None:
            raise KeyError(f"Unknown mapping_id: {mapping_id}")

        spec_payload = self._sanitize_spec(new_spec)
        digest = canonical_digest(spec_payload)

        # no-op: same digest -> return latest
        if digest == latest.mapping_digest:
            return latest.mapping_id, latest.mapping_version, latest.mapping_digest

        existing = self._get_by_digest(digest)
        if existing is not None:
            return existing.mapping_id, existing.mapping_version, existing.mapping_digest

        new_version = int(latest.mapping_version) + 1
        created_at = self._now()
        spec_json = canonical_json(spec_payload)

        self.conn.execute(
            """
            INSERT INTO mappings(
                mapping_id, mapping_version, mapping_digest, artifact_id, extractor_version, schema_version, spec_json, spec_ref_artifact_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(mapping_id),
                int(new_version),
                str(digest),
                latest.artifact_id,
                latest.extractor_version,
                int(latest.schema_version) if latest.schema_version is not None else None,
                spec_json,
                None,
                created_at,
            ),
        )
        return str(mapping_id), new_version, digest

    def get(self, mapping_id: str, mapping_version: int) -> Optional[MappingRecord]:
        cur = self.conn.execute(
            """
            SELECT mapping_digest, artifact_id, extractor_version, schema_version, spec_json, created_at
            FROM mappings
            WHERE mapping_id = ? AND mapping_version = ?
            """,
            (str(mapping_id), int(mapping_version)),
        )
        row = cur.fetchone()
        if not row:
            return None

        mapping_digest, artifact_id, extractor_version, schema_version, spec_json, created_at = row
        spec = json.loads(spec_json or "{}")
        if not isinstance(spec, dict):
            spec = {}
        return MappingRecord(
            mapping_id=str(mapping_id),
            mapping_version=int(mapping_version),
            mapping_digest=str(mapping_digest),
            artifact_id=str(artifact_id) if artifact_id is not None else None,
            extractor_version=str(extractor_version) if extractor_version is not None else None,
            schema_version=int(schema_version) if schema_version is not None else None,
            spec=spec,
            created_at=str(created_at),
        )

    def get_latest(self, mapping_id: str) -> Optional[MappingRecord]:
        cur = self.conn.execute(
            """
            SELECT mapping_version
            FROM mappings
            WHERE mapping_id = ?
            ORDER BY mapping_version DESC
            LIMIT 1
            """,
            (str(mapping_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self.get(mapping_id, int(row[0]))

    def _get_by_digest(self, mapping_digest: str) -> Optional[MappingRecord]:
        cur = self.conn.execute(
            """
            SELECT mapping_id, mapping_version
            FROM mappings
            WHERE mapping_digest = ?
            LIMIT 1
            """,
            (str(mapping_digest),),
        )
        row = cur.fetchone()
        if not row:
            return None
        mid, ver = row
        return self.get(str(mid), int(ver))
