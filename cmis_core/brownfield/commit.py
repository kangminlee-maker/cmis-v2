"""Commit orchestrator (BF-11).

MVP 범위:
- validated ImportRun(IMP)에서 CUR/CUB를 생성하고, PRJ vN을 발행합니다.
- CUR/CUB/IMP 업데이트는 brownfield.db 단일 트랜잭션으로 처리합니다.

주의:
- PRJ는 현재 FocalActorContextStore(=contexts.db)에 저장합니다.
  (시스템 전반에서 PRJ를 조회할 수 있도록 하기 위함)
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import uuid
from typing import Any, Dict, Optional, Tuple

from cmis_core.brownfield.curated_store import CuratedBundleStore, CuratedDatumStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.import_run_store import ImportRunStore
from cmis_core.brownfield.semantic_key import make as make_semantic_key
from cmis_core.brownfield.uow import UnitOfWork
from cmis_core.brownfield.validation import can_commit
from cmis_core.stores.artifact_store import ArtifactStore
from cmis_core.stores.focal_actor_context_store import FocalActorContextStore
from cmis_core.types import FocalActorContext


CONTEXT_BUILDER_VERSION = "brownfield_context_builder@0.1.0"


def commit_import_run(
    *,
    project_root: Path,
    import_run_id: str,
    policy_mode: str = "reporting_strict",
    focal_actor_context_base_id: Optional[str] = None,
    brownfield_conn: Optional[sqlite3.Connection] = None,
    artifact_store: Optional[ArtifactStore] = None,
    focal_actor_context_store: Optional[FocalActorContextStore] = None,
) -> Tuple[str, str]:
    """validated IMP를 commit하여 (CUB-*, PRJ-...-vN)를 반환합니다."""

    conn = brownfield_conn or open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    art_store = artifact_store or ArtifactStore(project_root=project_root)
    imp_store = ImportRunStore(conn)
    datum_store = CuratedDatumStore(conn)
    bundle_store = CuratedBundleStore(conn)
    uow = UnitOfWork(conn)

    rec = imp_store.get(import_run_id)
    if rec is None:
        raise KeyError(f"Unknown import_run_id: {import_run_id}")
    if rec.status != "validated":
        raise ValueError(f"ImportRun is not validated (status={rec.status})")
    if not rec.validation_decision:
        raise ValueError("validation_decision is missing")
    if not can_commit(policy_mode=policy_mode, validation_decision=rec.validation_decision):
        raise ValueError(f"Commit denied by gate: mode={policy_mode}, decision={rec.validation_decision}")

    if not rec.artifact_ids:
        raise ValueError("artifact_ids is empty")
    upload_artifact_id = rec.artifact_ids[0]

    meta = art_store.get_meta(upload_artifact_id) or {}
    sha256_hex = str(meta.get("sha256") or "")
    size_bytes = int(meta.get("size_bytes") or 0)

    if not rec.preview_report_artifact_id:
        raise ValueError("preview_report_artifact_id is missing")
    preview_path = art_store.get_path(rec.preview_report_artifact_id)
    if preview_path is None:
        raise RuntimeError("Failed to resolve preview artifact path")
    preview = json.loads(preview_path.read_text(encoding="utf-8") or "{}")
    if not isinstance(preview, dict):
        preview = {}

    # --- atomic commit (brownfield.db) ---
    with uow.transaction():
        # CUR: raw upload as externalized payload(ART ref) + stable payload digest based on sha/size/shape
        fmt = str(preview.get("format") or "")
        if not fmt:
            mime = str(meta.get("mime_type") or "")
            if mime == "text/csv":
                fmt = "csv"
            elif mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                fmt = "xlsx"
            else:
                fmt = "unknown"

        entity = "csv_upload" if fmt == "csv" else ("xlsx_upload" if fmt == "xlsx" else "file_upload")
        semantic_key = make_semantic_key(
            datum_type="table",
            entity=entity,
            name="raw",
            extra={"sha256": sha256_hex},
        )
        cur_payload = {
            "format": fmt,
            "source_sha256": sha256_hex,
            "source_size_bytes": size_bytes,
            "columns": preview.get("columns") or [],
            "row_count": int(preview.get("row_count") or 0),
        }
        if fmt == "xlsx":
            cur_payload["sheets"] = preview.get("sheets") or []
            cur_payload["formula_cell_count"] = int(preview.get("formula_cell_count") or 0)
            cur_payload["formula_missing_cached_value_count"] = int(preview.get("formula_missing_cached_value_count") or 0)
        cur_id, cur_digest = datum_store.put(
            datum_type="table",
            semantic_key=semantic_key,
            payload=cur_payload,
            payload_ref_artifact_id=upload_artifact_id,
            lineage={
                "from_artifact_ids": [upload_artifact_id],
                "mapping_ref": rec.mapping_ref,
                "extractor_version": rec.extractor_version,
                "ingest_policy_digest": rec.ingest_policy_digest,
                "normalization_defaults_digest": rec.normalization_defaults_digest,
                "patches_digest": rec.patches_digest,
            },
        )

        cub_digest_input: Dict[str, Any] = {
            "schema_version": 1,
            "normalization_defaults_digest": rec.normalization_defaults_digest,
            "ingest_policy_digest": rec.ingest_policy_digest,
            "mapping_ref": rec.mapping_ref,
            "extractor_version": rec.extractor_version,
            "patch_chain_digests": [],
            "curated_items": [
                {"semantic_key": semantic_key, "cur_payload_digest": cur_digest, "cur_schema_version": 1}
            ],
        }
        cub_id, cub_digest = bundle_store.put(
            cub_digest_input=cub_digest_input,
            import_run_id=import_run_id,
            normalization_defaults_digest=rec.normalization_defaults_digest,
            ingest_policy_digest=rec.ingest_policy_digest,
            mapping_ref=rec.mapping_ref,
            extractor_version=rec.extractor_version,
            patch_chain_digests=[],
            curated_items=cub_digest_input["curated_items"],
            quality_summary={"validated": True, "validation_report_ref": rec.validation_report_artifact_id},
            schema_version=1,
        )

        imp_store.mark_committed(import_run_id, cub_id)

    # --- PRJ publish (contexts.db) ---
    ctx_store = focal_actor_context_store or FocalActorContextStore(project_root=project_root)
    base = str(focal_actor_context_base_id).strip() if focal_actor_context_base_id else f"PRJ-{uuid.uuid4().hex[:8]}"

    latest = ctx_store.get_latest(base)
    if latest is None:
        next_version = 1
        prev_id = None
    else:
        next_version = int(latest.version) + 1
        prev_id = latest.focal_actor_context_id

    prj_id = f"{base}-v{next_version}"
    prj = FocalActorContext(
        focal_actor_context_id=prj_id,
        version=next_version,
        previous_version_id=prev_id,
        scope={},
        assets_profile={},
        baseline_state={},
        focal_actor_id=None,
        constraints_profile={},
        preference_profile={},
        lineage={
            "primary_source_bundle": {"bundle_id": cub_id, "bundle_digest": cub_digest, "role": "baseline"},
            "context_builder": {"version": CONTEXT_BUILDER_VERSION},
        },
    )
    ctx_store.save(prj)

    return cub_id, prj_id
