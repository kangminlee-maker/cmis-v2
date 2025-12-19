"""Validation + commit gating (BF-10).

Validate는 "저장"이 아니라 "결정(pass/fail/warn_only)"과 "계약 강제"가 핵심입니다.

주의(누출 방지):
- ValidationReport는 ART로 저장하되, 원문/대량 수치를 포함하지 않습니다.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.import_run_store import ImportRunStore
from cmis_core.brownfield.uow import UnitOfWork
from cmis_core.stores.artifact_store import ArtifactStore


@dataclass(frozen=True)
class ValidationResult:
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    suggested_mapping_patches: List[Dict[str, Any]]
    suggested_data_override_patches: List[Dict[str, Any]]
    policy_decision: str  # pass|fail|warn_only

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "suggested_mapping_patches": list(self.suggested_mapping_patches),
            "suggested_data_override_patches": list(self.suggested_data_override_patches),
            "policy_decision": str(self.policy_decision),
        }


def validate_preview_summary(preview: Dict[str, Any]) -> ValidationResult:
    """Preview 요약(원문 없음)만으로 수행하는 최소 validate (MVP v1)."""

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    row_count = int(preview.get("row_count") or 0)
    columns = preview.get("columns") or []
    non_empty = preview.get("non_empty_counts") or {}

    if row_count <= 0:
        errors.append({"type": "empty_file", "message": "Input has no data rows"})

    if not columns:
        errors.append({"type": "missing_required_field", "message": "Columns are missing"})

    if isinstance(non_empty, dict):
        empty_cols = [c for c in columns if int(non_empty.get(c) or 0) == 0]
        if empty_cols:
            warnings.append({"type": "low_coverage", "message": "Some columns are entirely empty", "columns": empty_cols})

    fmt = str(preview.get("format") or "")
    if fmt == "xlsx":
        missing_cached = int(preview.get("formula_missing_cached_value_count") or 0)
        if missing_cached > 0:
            warnings.append(
                {
                    "type": "missing_cached_formula_values",
                    "message": "Some formula cells have no cached values (data_only=True yields None)",
                    "formula_cell_count": int(preview.get("formula_cell_count") or 0),
                    "missing_cached_value_count": int(missing_cached),
                }
            )

    decision = "fail" if errors else ("warn_only" if warnings else "pass")
    return ValidationResult(
        errors=errors,
        warnings=warnings,
        suggested_mapping_patches=[],
        suggested_data_override_patches=[],
        policy_decision=decision,
    )


def can_commit(*, policy_mode: str, validation_decision: str) -> bool:
    """policy_mode와 validation_decision으로 commit 가능 여부를 판정합니다."""

    mode = str(policy_mode)
    decision = str(validation_decision)
    if decision == "fail":
        return False
    if mode == "reporting_strict":
        return decision == "pass"
    if mode in {"decision_balanced", "exploration_friendly"}:
        return decision in {"pass", "warn_only"}
    # unknown mode: conservative
    return False


def validate_import_run(
    *,
    project_root: Path,
    import_run_id: str,
    policy_mode: str = "reporting_strict",
    brownfield_conn: Optional[sqlite3.Connection] = None,
    artifact_store: Optional[ArtifactStore] = None,
) -> ValidationResult:
    """ImportRun의 preview를 기반으로 validate하고 report(ART)를 attach합니다."""

    conn = brownfield_conn or open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    art_store = artifact_store or ArtifactStore(project_root=project_root)
    imp_store = ImportRunStore(conn)
    uow = UnitOfWork(conn)

    rec = imp_store.get(import_run_id)
    if rec is None:
        raise KeyError(f"Unknown import_run_id: {import_run_id}")
    if not rec.preview_report_artifact_id:
        raise ValueError("preview_report_artifact_id is missing; run preview first")

    preview_path = art_store.get_path(rec.preview_report_artifact_id)
    if preview_path is None:
        raise RuntimeError("Failed to resolve preview artifact path")
    preview = json.loads(preview_path.read_text(encoding="utf-8") or "{}")
    if not isinstance(preview, dict):
        preview = {}

    result = validate_preview_summary(preview)

    report_artifact_id = art_store.put_json(
        {
            "import_run_id": str(import_run_id),
            "policy_mode": str(policy_mode),
            "preview_ref": str(rec.preview_report_artifact_id),
            **result.to_summary_dict(),
        },
        kind="brownfield_validation",
        meta={"import_run_id": str(import_run_id), "policy_mode": str(policy_mode)},
    )

    with uow.transaction():
        imp_store.attach_validation(import_run_id, report_artifact_id, result.policy_decision)

    return result
