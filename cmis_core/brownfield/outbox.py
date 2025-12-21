"""Brownfield outbox (local-first) — atomicity/idempotency bridge.

문제:
- Brownfield commit은 `brownfield.db`(SQLite) 트랜잭션으로 CUB/IMP 상태를 원자적으로 커밋할 수 있지만,
  PRJ publish는 `contexts.db`(별도 SQLite)로 기록해야 하므로 단일 트랜잭션으로 묶을 수 없습니다.

해결(Outbox pattern):
- `brownfield.db` 트랜잭션 안에서 "외부로 해야 하는 작업"을 outbox 테이블에 기록합니다.
- 트랜잭션이 커밋된 뒤, outbox를 처리(process)하여 `contexts.db` 등 외부 side-effect를 수행합니다.
- 처리 실패 시 outbox에 실패 원인/시도 횟수가 남고, 재시도(reconcile)가 가능합니다.

원칙:
- outbox는 at-least-once 실행을 전제로 하므로, 핸들러는 멱등(idempotent)해야 합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.import_run_store import ImportRunStore
from cmis_core.stores.focal_actor_context_store import FocalActorContextStore
from cmis_core.types import FocalActorContext


KIND_PUBLISH_FOCAL_ACTOR_CONTEXT_V1 = "publish_focal_actor_context_v1"


@dataclass(frozen=True)
class OutboxRecord:
    outbox_id: str
    kind: str
    idempotency_key: str
    status: str  # pending|processing|done|failed
    attempts: int
    last_error: Optional[str]
    payload: Dict[str, Any]
    created_at: str
    updated_at: str
    processed_at: Optional[str]


def enqueue_publish_focal_actor_context(
    conn: sqlite3.Connection,
    *,
    import_run_id: str,
    cub_id: str,
    cub_digest: str,
    focal_actor_context_base_id: str,
    focal_actor_context_version: int,
    focal_actor_context_id: str,
    context_builder_version: str,
) -> str:
    """PRJ publish 작업을 outbox에 enqueue합니다(트랜잭션 내부 호출을 권장)."""

    rid = str(import_run_id).strip()
    if not rid:
        raise ValueError("import_run_id is required")

    key = f"publish_prj:{rid}"
    payload = {
        "schema_version": 1,
        "import_run_id": rid,
        "cub_id": str(cub_id),
        "cub_digest": str(cub_digest),
        "focal_actor_context_base_id": str(focal_actor_context_base_id),
        "focal_actor_context_version": int(focal_actor_context_version),
        "focal_actor_context_id": str(focal_actor_context_id),
        "context_builder_version": str(context_builder_version),
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }
    return _enqueue(conn, kind=KIND_PUBLISH_FOCAL_ACTOR_CONTEXT_V1, idempotency_key=key, payload=payload)


def reconcile_brownfield_outbox(
    *,
    project_root: Path,
    import_run_id: Optional[str] = None,
    limit: int = 50,
    retry_failed: bool = False,
) -> Dict[str, Any]:
    """brownfield outbox를 처리합니다.

    Args:
        project_root: 프로젝트 루트
        import_run_id: 특정 IMP만 처리(선택)
        limit: 처리 개수 제한
        retry_failed: failed 상태도 재시도 대상에 포함할지 여부
    """

    conn = open_brownfield_db(project_root=project_root)
    try:
        migrate_brownfield_db(conn)
        return _process(conn, project_root=project_root, import_run_id=import_run_id, limit=limit, retry_failed=retry_failed)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _process(
    conn: sqlite3.Connection,
    *,
    project_root: Path,
    import_run_id: Optional[str],
    limit: int,
    retry_failed: bool,
) -> Dict[str, Any]:
    statuses = ["pending"]
    if retry_failed:
        statuses.append("failed")

    rows = _list_candidates(conn, statuses=statuses, import_run_id=import_run_id, limit=limit)
    processed: List[Dict[str, Any]] = []

    for rec in rows:
        try:
            claimed = _claim(conn, outbox_id=rec.outbox_id, allowed_statuses=statuses)
            if not claimed:
                continue
            # release write lock early (handler may touch other DBs)
            conn.commit()

            if rec.kind == KIND_PUBLISH_FOCAL_ACTOR_CONTEXT_V1:
                prj_id = _handle_publish_focal_actor_context(project_root=project_root, payload=rec.payload)
                # record result back to brownfield.db + mark outbox done (same tx)
                store = ImportRunStore(conn)
                conn.execute("BEGIN")
                store.set_published_focal_actor_context_id(
                    str(rec.payload.get("import_run_id") or ""),
                    focal_actor_context_id=str(prj_id),
                )
                _mark_done(conn, outbox_id=rec.outbox_id)
                conn.commit()
                processed.append({"outbox_id": rec.outbox_id, "kind": rec.kind, "status": "done", "result": {"prj_id": prj_id}})
            else:
                _mark_failed(conn, outbox_id=rec.outbox_id, error=f"unknown_kind:{rec.kind}")
                conn.commit()
                processed.append({"outbox_id": rec.outbox_id, "kind": rec.kind, "status": "failed", "error": f"unknown_kind:{rec.kind}"})
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            _mark_failed(conn, outbox_id=rec.outbox_id, error=str(e))
            try:
                conn.commit()
            except Exception:
                pass
            processed.append({"outbox_id": rec.outbox_id, "kind": rec.kind, "status": "failed", "error": str(e)})

    return {"ok": True, "processed": processed, "count": len(processed)}


def _handle_publish_focal_actor_context(*, project_root: Path, payload: Dict[str, Any]) -> str:
    """contexts.db에 PRJ를 publish합니다(멱등).

    NOTE:
    - import_runs 업데이트는 outbox processor가 담당합니다.
    """

    rid = str(payload.get("import_run_id") or "").strip()
    cub_id = str(payload.get("cub_id") or "").strip()
    cub_digest = str(payload.get("cub_digest") or "").strip()
    base_id = str(payload.get("focal_actor_context_base_id") or "").strip()
    version = int(payload.get("focal_actor_context_version") or 0)
    prj_id = str(payload.get("focal_actor_context_id") or "").strip()
    builder_version = str(payload.get("context_builder_version") or "").strip()

    if not rid or not cub_id or not cub_digest or not base_id or version <= 0 or not prj_id:
        raise ValueError("invalid_outbox_payload")

    # 1) Publish PRJ into contexts.db (idempotent)
    ctx_store = FocalActorContextStore(project_root=project_root)
    try:
        existing = ctx_store.get_by_version(base_id, version)
        if existing is not None:
            existing_digest = str((existing.lineage or {}).get("primary_source_bundle", {}).get("bundle_digest") or "")
            if existing_digest and existing_digest != cub_digest:
                raise ValueError(f"prj_version_conflict:{prj_id}:existing_bundle_digest={existing_digest} expected={cub_digest}")
        else:
            prev_id: Optional[str]
            if version <= 1:
                prev_id = None
            else:
                prev = ctx_store.get_by_version(base_id, version - 1)
                prev_id = (prev.focal_actor_context_id if prev is not None else None)
                if prev_id is None:
                    latest = ctx_store.get_latest(base_id)
                    prev_id = (latest.focal_actor_context_id if latest is not None else None)

            prj = FocalActorContext(
                focal_actor_context_id=prj_id,
                version=int(version),
                previous_version_id=prev_id,
                scope={},
                assets_profile={},
                baseline_state={},
                focal_actor_id=None,
                constraints_profile={},
                preference_profile={},
                lineage={
                    "primary_source_bundle": {"bundle_id": cub_id, "bundle_digest": cub_digest, "role": "baseline"},
                    "context_builder": {"version": builder_version or "unknown"},
                },
            )
            ctx_store.save(prj)
    finally:
        ctx_store.close()

    return prj_id


def _enqueue(conn: sqlite3.Connection, *, kind: str, idempotency_key: str, payload: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    oid = f"OBX-{uuid.uuid4().hex[:10]}"
    payload_text = json.dumps(payload or {}, ensure_ascii=False)

    conn.execute(
        """
        INSERT OR IGNORE INTO outbox (
            outbox_id, kind, idempotency_key, status, attempts, last_error, payload_json, created_at, updated_at, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (oid, str(kind), str(idempotency_key), "pending", 0, None, payload_text, now, now, None),
    )

    cur = conn.execute("SELECT outbox_id FROM outbox WHERE idempotency_key = ?", (str(idempotency_key),))
    row = cur.fetchone()
    if not row:
        raise RuntimeError("Failed to enqueue outbox record")
    return str(row[0])


def _list_candidates(
    conn: sqlite3.Connection,
    *,
    statuses: List[str],
    import_run_id: Optional[str],
    limit: int,
) -> List[OutboxRecord]:
    sts = [str(s) for s in (statuses or [])]
    if not sts:
        return []

    where = "status IN ({})".format(",".join(["?"] * len(sts)))
    params: List[Any] = list(sts)

    # optional filter by import_run_id (payload_json LIKE is a best-effort local filter)
    if import_run_id:
        where = where + " AND payload_json LIKE ?"
        params.append(f"%{str(import_run_id).strip()}%")

    q = f"""
        SELECT outbox_id, kind, idempotency_key, status, attempts, last_error, payload_json, created_at, updated_at, processed_at
        FROM outbox
        WHERE {where}
        ORDER BY created_at ASC
        LIMIT ?
    """
    params.append(int(limit))

    cur = conn.execute(q, tuple(params))
    rows = cur.fetchall() or []

    out: List[OutboxRecord] = []
    for (
        outbox_id,
        kind,
        idempotency_key,
        status,
        attempts,
        last_error,
        payload_json,
        created_at,
        updated_at,
        processed_at,
    ) in rows:
        try:
            payload = json.loads(payload_json or "{}")
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        out.append(
            OutboxRecord(
                outbox_id=str(outbox_id),
                kind=str(kind),
                idempotency_key=str(idempotency_key),
                status=str(status),
                attempts=int(attempts or 0),
                last_error=str(last_error) if last_error is not None else None,
                payload=payload,
                created_at=str(created_at),
                updated_at=str(updated_at),
                processed_at=str(processed_at) if processed_at is not None else None,
            )
        )
    return out


def _claim(conn: sqlite3.Connection, *, outbox_id: str, allowed_statuses: List[str]) -> bool:
    oid = str(outbox_id)
    now = datetime.now(timezone.utc).isoformat()

    allowed = [str(s) for s in (allowed_statuses or ["pending"])]
    if not allowed:
        allowed = ["pending"]

    where = "outbox_id = ? AND status IN ({})".format(",".join(["?"] * len(allowed)))
    params: List[Any] = [oid, *allowed]

    cur = conn.execute(
        f"""
        UPDATE outbox
        SET status = ?, attempts = attempts + 1, updated_at = ?
        WHERE {where}
        """,
        ("processing", now, *params),
    )
    return int(cur.rowcount or 0) == 1


def _mark_done(conn: sqlite3.Connection, *, outbox_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE outbox
        SET status = ?, last_error = NULL, processed_at = ?, updated_at = ?
        WHERE outbox_id = ?
        """,
        ("done", now, now, str(outbox_id)),
    )


def _mark_failed(conn: sqlite3.Connection, *, outbox_id: str, error: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE outbox
        SET status = ?, last_error = ?, updated_at = ?
        WHERE outbox_id = ?
        """,
        ("failed", str(error), now, str(outbox_id)),
    )

