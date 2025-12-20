"""ContextViewStore (PRJ_VIEW) — derived view cache (BF-07).

ContextView(PRJ_VIEW-*)는 FocalActorContext(PRJ-...-vN)에서 파생된 "derived view"를 저장합니다.

원칙:
- PRJ_VIEW는 정본(SoT)이 아닙니다. 언제든 폐기/재생성 가능합니다.
- PRJ_VIEW는 PRJ의 입력(=CUB digest 등)에 대한 파생 결과이므로,
  `derived_from_*_digest`를 기록해 드리프트를 감지합니다.

검증 계약(최소):
- 단일 모드: view.derived_from_bundle_digest == PRJ.lineage.primary_source_bundle.bundle_digest
- 멀티 모드(선택): view.derived_from_sources_digest == sha256(canonical_json(source_bundles))

주의:
- view payload는 ArtifactStore(ART-*)로 externalize하고, DB에는 ref만 저장합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional, Tuple

from cmis_core.digest import canonical_digest
from cmis_core.stores.artifact_store import ArtifactStore
from cmis_core.types import FocalActorContext


@dataclass(frozen=True)
class ContextViewRecord:
    view_id: str
    focal_actor_context_id: str
    derived_from_bundle_digest: Optional[str]
    derived_from_sources_digest: Optional[str]
    view_payload_ref_artifact_id: Optional[str]
    created_at: str


def compute_sources_digest(source_bundles: Any) -> str:
    """source_bundles 기반 derived_from_sources_digest를 계산합니다.

    결정성(권장):
    - list[dict] 형태이면 bundle_digest/bundle_id 기준으로 정렬합니다.
    """

    sb = source_bundles

    if isinstance(sb, list):
        cleaned: List[Dict[str, Any]] = []
        for it in sb:
            if not isinstance(it, dict):
                continue
            cleaned.append(dict(it))

        def _sort_key(d: Dict[str, Any]) -> Tuple[str, str]:
            return (str(d.get("bundle_digest") or ""), str(d.get("bundle_id") or ""))

        cleaned.sort(key=_sort_key)
        sb = cleaned

    return canonical_digest({"source_bundles": sb})


def expected_view_digests_from_prj(prj: FocalActorContext) -> Tuple[Optional[str], Optional[str]]:
    """PRJ lineage에서 PRJ_VIEW가 따라야 하는 기대 digest들을 추출합니다."""

    lineage = prj.lineage or {}

    expected_bundle_digest: Optional[str] = None
    expected_sources_digest: Optional[str] = None

    primary = lineage.get("primary_source_bundle") if isinstance(lineage, dict) else None
    if isinstance(primary, dict):
        bd = primary.get("bundle_digest")
        if bd:
            expected_bundle_digest = str(bd)

    sources = lineage.get("source_bundles") if isinstance(lineage, dict) else None
    if sources is not None:
        try:
            expected_sources_digest = compute_sources_digest(sources)
        except Exception:
            expected_sources_digest = None

    return expected_bundle_digest, expected_sources_digest


def is_view_current(*, prj: FocalActorContext, view: ContextViewRecord) -> bool:
    """PRJ와 PRJ_VIEW 간 derived digest 일치 여부를 반환합니다."""

    expected_bundle_digest, expected_sources_digest = expected_view_digests_from_prj(prj)

    if view.derived_from_bundle_digest and expected_bundle_digest:
        return str(view.derived_from_bundle_digest) == str(expected_bundle_digest)

    if view.derived_from_sources_digest and expected_sources_digest:
        return str(view.derived_from_sources_digest) == str(expected_sources_digest)

    return False


class ContextViewStore:
    """brownfield.db의 context_views 테이블 스토어."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def put(
        self,
        *,
        focal_actor_context_id: str,
        view_payload: Optional[Dict[str, Any]] = None,
        view_payload_ref_artifact_id: Optional[str] = None,
        derived_from_bundle_digest: Optional[str] = None,
        derived_from_sources_digest: Optional[str] = None,
        artifact_store: Optional[ArtifactStore] = None,
        view_id: Optional[str] = None,
    ) -> str:
        """PRJ_VIEW를 저장합니다.

        payload는 ART로 저장한 뒤 view_payload_ref_artifact_id만 DB에 남깁니다.

        Returns:
            view_id
        """

        prj_id = str(focal_actor_context_id).strip()
        if not prj_id:
            raise ValueError("focal_actor_context_id is required")

        aid = str(view_payload_ref_artifact_id) if view_payload_ref_artifact_id is not None else None
        if aid is None and view_payload is not None:
            if artifact_store is None:
                raise ValueError("artifact_store is required when view_payload is provided")
            aid = artifact_store.put_json(
                view_payload,
                kind="brownfield_prj_view",
                meta={
                    "focal_actor_context_id": prj_id,
                    "derived_from_bundle_digest": str(derived_from_bundle_digest) if derived_from_bundle_digest else None,
                    "derived_from_sources_digest": str(derived_from_sources_digest) if derived_from_sources_digest else None,
                },
            )

        # best-effort dedupe: same prj + same derived digests -> reuse latest
        existing = self._find_existing(
            focal_actor_context_id=prj_id,
            derived_from_bundle_digest=str(derived_from_bundle_digest) if derived_from_bundle_digest is not None else None,
            derived_from_sources_digest=str(derived_from_sources_digest) if derived_from_sources_digest is not None else None,
        )
        if existing is not None:
            return existing

        vid = str(view_id) if view_id is not None else f"PRJ_VIEW-{uuid.uuid4().hex[:10]}"
        created_at = self._now()

        self.conn.execute(
            """
            INSERT INTO context_views(
                view_id, focal_actor_context_id,
                derived_from_bundle_digest, derived_from_sources_digest,
                view_payload_ref_artifact_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                vid,
                prj_id,
                str(derived_from_bundle_digest) if derived_from_bundle_digest is not None else None,
                str(derived_from_sources_digest) if derived_from_sources_digest is not None else None,
                aid,
                created_at,
            ),
        )
        return vid

    def get(self, view_id: str) -> Optional[ContextViewRecord]:
        cur = self.conn.execute(
            """
            SELECT focal_actor_context_id, derived_from_bundle_digest, derived_from_sources_digest,
                   view_payload_ref_artifact_id, created_at
            FROM context_views
            WHERE view_id = ?
            """,
            (str(view_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        (
            focal_actor_context_id,
            derived_from_bundle_digest,
            derived_from_sources_digest,
            view_payload_ref_artifact_id,
            created_at,
        ) = row

        return ContextViewRecord(
            view_id=str(view_id),
            focal_actor_context_id=str(focal_actor_context_id),
            derived_from_bundle_digest=str(derived_from_bundle_digest) if derived_from_bundle_digest is not None else None,
            derived_from_sources_digest=str(derived_from_sources_digest) if derived_from_sources_digest is not None else None,
            view_payload_ref_artifact_id=str(view_payload_ref_artifact_id) if view_payload_ref_artifact_id is not None else None,
            created_at=str(created_at),
        )

    def get_latest(self, focal_actor_context_id: str) -> Optional[ContextViewRecord]:
        cur = self.conn.execute(
            """
            SELECT view_id
            FROM context_views
            WHERE focal_actor_context_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (str(focal_actor_context_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self.get(str(row[0]))

    def get_current_or_none(self, *, prj: FocalActorContext) -> Optional[ContextViewRecord]:
        """PRJ 기준으로 최신 view를 조회하고, derived digest가 일치하면 반환합니다."""

        view = self.get_latest(prj.focal_actor_context_id)
        if view is None:
            return None
        return view if is_view_current(prj=prj, view=view) else None

    def load_payload(self, *, view: ContextViewRecord, artifact_store: ArtifactStore) -> Optional[Dict[str, Any]]:
        """PRJ_VIEW payload를 ART에서 로드합니다."""

        if not view.view_payload_ref_artifact_id:
            return None
        p = artifact_store.get_path(view.view_payload_ref_artifact_id)
        if p is None:
            return None
        try:
            obj = json.loads(p.read_text(encoding="utf-8") or "{}")
        except Exception:
            return None
        return obj if isinstance(obj, dict) else None

    def _find_existing(
        self,
        *,
        focal_actor_context_id: str,
        derived_from_bundle_digest: Optional[str],
        derived_from_sources_digest: Optional[str],
    ) -> Optional[str]:
        cur = self.conn.execute(
            """
            SELECT view_id
            FROM context_views
            WHERE focal_actor_context_id = ?
              AND COALESCE(derived_from_bundle_digest, '') = COALESCE(?, '')
              AND COALESCE(derived_from_sources_digest, '') = COALESCE(?, '')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (str(focal_actor_context_id), derived_from_bundle_digest, derived_from_sources_digest),
        )
        row = cur.fetchone()
        if not row:
            return None
        return str(row[0])
