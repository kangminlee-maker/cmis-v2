"""Context verify contract enforcement (BF-12).

MVP:
- `cmis context verify PRJ-...-vN`에서 사용할 핵심 검증 로직 제공

검증 항목(최소):
- PRJ id는 version pin(PRJ-...-vN)이어야 함
- PRJ lineage에 primary_source_bundle(bundle_id/bundle_digest) + context_builder.version 존재
- PRJ가 참조하는 CUB(bundle_id)의 실제 bundle_digest와 PRJ에 기록된 digest가 일치
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import List, Optional, Tuple

from cmis_core.brownfield.curated_store import CuratedBundleStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.stores.focal_actor_context_store import FocalActorContextStore


_PRJ_VERSIONED_RE = re.compile(r"^(PRJ-[A-Za-z0-9_-]+)-v([0-9]+)$")


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def _split_prj_versioned_id(prj_id: str) -> Tuple[str, int]:
    m = _PRJ_VERSIONED_RE.match(str(prj_id).strip())
    if not m:
        raise ValueError("PRJ id must be version-pinned: PRJ-...-vN")
    base = str(m.group(1))
    ver = int(m.group(2))
    if ver < 1:
        raise ValueError("PRJ version must be >= 1")
    return base, ver


def verify_prj(
    *,
    project_root: Path,
    focal_actor_context_id: str,
    brownfield_conn: Optional[sqlite3.Connection] = None,
    focal_actor_context_store: Optional[FocalActorContextStore] = None,
) -> VerifyResult:
    """PRJ-...-vN의 계약을 검증합니다."""

    errors: List[str] = []
    warnings: List[str] = []

    try:
        base, ver = _split_prj_versioned_id(focal_actor_context_id)
    except Exception as e:
        return VerifyResult(ok=False, errors=[str(e)], warnings=[])

    ctx_store = focal_actor_context_store or FocalActorContextStore(project_root=project_root)
    prj = ctx_store.get_by_version(base, ver)
    if prj is None:
        return VerifyResult(ok=False, errors=[f"PRJ not found: {focal_actor_context_id}"], warnings=[])

    lineage = prj.lineage or {}
    builder = lineage.get("context_builder") or {}
    builder_version = builder.get("version") if isinstance(builder, dict) else None
    if not builder_version:
        errors.append("PRJ missing context_builder.version")

    primary = lineage.get("primary_source_bundle") if isinstance(lineage, dict) else None
    if not isinstance(primary, dict):
        errors.append("PRJ missing primary_source_bundle")
        return VerifyResult(ok=False, errors=errors, warnings=warnings)

    bundle_id = primary.get("bundle_id")
    bundle_digest_expected = primary.get("bundle_digest")
    if not bundle_id or not bundle_digest_expected:
        errors.append("PRJ primary_source_bundle must include bundle_id and bundle_digest")
        return VerifyResult(ok=False, errors=errors, warnings=warnings)

    conn = brownfield_conn or open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)
    bundle_store = CuratedBundleStore(conn)
    bundle = bundle_store.get(str(bundle_id))
    if bundle is None:
        errors.append(f"CUB not found: {bundle_id}")
        return VerifyResult(ok=False, errors=errors, warnings=warnings)

    if str(bundle.bundle_digest) != str(bundle_digest_expected):
        errors.append(
            f"CUB digest mismatch: expected={bundle_digest_expected}, actual={bundle.bundle_digest} (bundle_id={bundle_id})"
        )

    # optional checks (warnings)
    if bundle.ingest_policy_digest is None:
        warnings.append("CUB ingest_policy_digest is missing")
    if bundle.extractor_version is None:
        warnings.append("CUB extractor_version is missing")

    return VerifyResult(ok=(len(errors) == 0), errors=errors, warnings=warnings)
