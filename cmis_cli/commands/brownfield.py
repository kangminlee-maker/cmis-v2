"""brownfield 관련 명령어 (BF-13).

MVP:
- `cmis brownfield import <file>`
- `cmis brownfield preview IMP-...`
- `cmis brownfield validate IMP-... --policy-mode ...`
- `cmis brownfield commit IMP-... --policy-mode ... [--focal-actor-context-base-id PRJ-...]`

주의(누출 방지):
- preview/validation 출력은 원문 행/대량 수치를 포함하지 않는 요약(ART)만 다룹니다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from cmis_core.brownfield.commit import commit_import_run
from cmis_core.brownfield.csv_ingest import import_csv_file
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.import_run_store import ImportRunStore
from cmis_core.brownfield.validation import validate_import_run
from cmis_core.brownfield.xlsx_ingest import import_xlsx_file
from cmis_core.stores import StoreFactory


def _resolve_project_root(args: Any) -> Path:
    project_root = getattr(args, "project_root", None)
    if project_root:
        return Path(project_root).resolve()
    return Path.cwd().resolve()


def _resolve_cwd_relative_path(raw: str) -> Path:
    p = Path(str(raw)).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    return p


def _mapping_ref_from_args(args: Any) -> Optional[Dict[str, Any]]:
    mapping_id = getattr(args, "mapping_id", None)
    mapping_version = getattr(args, "mapping_version", None)

    if not mapping_id and mapping_version is None:
        return None

    ref: Dict[str, Any] = {}
    if mapping_id:
        ref["mapping_id"] = str(mapping_id)
    if mapping_version is not None:
        ref["mapping_version"] = int(mapping_version)
    return ref


def cmd_brownfield_import(args: Any) -> None:
    """`cmis brownfield import <file>`"""

    project_root = _resolve_project_root(args)
    file_path = _resolve_cwd_relative_path(getattr(args, "file", ""))

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise NotImplementedError(f"Only .csv/.xlsx are supported in MVP (got: {suffix})")

    mapping_ref = _mapping_ref_from_args(args)
    extractor_version = getattr(args, "extractor_version", None)
    if extractor_version is None:
        extractor_version = "csv_decoder@0.1.0" if suffix == ".csv" else "xlsx_decoder@0.1.0"

    conn = open_brownfield_db(project_root=project_root)
    factory = StoreFactory(project_root=project_root)
    art_store = factory.artifact_store()
    try:
        migrate_brownfield_db(conn)

        if suffix == ".csv":
            imp_id = import_csv_file(
                project_root=project_root,
                file_path=file_path,
                mapping_ref=mapping_ref,
                ingest_policy_digest=getattr(args, "ingest_policy_digest", None),
                normalization_defaults_digest=getattr(args, "normalization_defaults_digest", None),
                extractor_version=str(extractor_version),
                brownfield_conn=conn,
                artifact_store=art_store,
            )
        else:
            imp_id = import_xlsx_file(
                project_root=project_root,
                file_path=file_path,
                mapping_ref=mapping_ref,
                ingest_policy_digest=getattr(args, "ingest_policy_digest", None),
                normalization_defaults_digest=getattr(args, "normalization_defaults_digest", None),
                extractor_version=str(extractor_version),
                brownfield_conn=conn,
                artifact_store=art_store,
            )

        payload: Dict[str, Any] = {
            "ok": True,
            "import_run_id": str(imp_id),
            "file": str(file_path),
            "mapping_ref": mapping_ref,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            art_store.close()
        except Exception:
            pass


def cmd_brownfield_preview(args: Any) -> None:
    """`cmis brownfield preview IMP-...`"""

    project_root = _resolve_project_root(args)
    import_run_id = str(getattr(args, "import_run_id", "")).strip()

    conn = open_brownfield_db(project_root=project_root)
    factory = StoreFactory(project_root=project_root)
    art_store = factory.artifact_store()
    try:
        migrate_brownfield_db(conn)

        rec = ImportRunStore(conn).get(import_run_id)
        if rec is None:
            raise KeyError(f"Unknown import_run_id: {import_run_id}")
        if not rec.preview_report_artifact_id:
            raise ValueError("preview_report_artifact_id is missing; run import first")

        preview_path = art_store.get_path(rec.preview_report_artifact_id)
        if preview_path is None:
            raise RuntimeError("Failed to resolve preview artifact path")

        preview = json.loads(preview_path.read_text(encoding="utf-8") or "{}")
        if not isinstance(preview, dict):
            preview = {}

        payload: Dict[str, Any] = {
            "ok": True,
            "import_run_id": str(import_run_id),
            "status": str(rec.status),
            "preview_report_artifact_id": str(rec.preview_report_artifact_id),
            "preview": preview,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            art_store.close()
        except Exception:
            pass


def cmd_brownfield_validate(args: Any) -> None:
    """`cmis brownfield validate IMP-...`"""

    project_root = _resolve_project_root(args)
    import_run_id = str(getattr(args, "import_run_id", "")).strip()
    policy_mode = str(getattr(args, "policy_mode", "reporting_strict"))

    conn = open_brownfield_db(project_root=project_root)
    factory = StoreFactory(project_root=project_root)
    art_store = factory.artifact_store()
    try:
        migrate_brownfield_db(conn)

        result = validate_import_run(
            project_root=project_root,
            import_run_id=import_run_id,
            policy_mode=policy_mode,
            brownfield_conn=conn,
            artifact_store=art_store,
        )

        payload: Dict[str, Any] = {
            "ok": result.policy_decision != "fail",
            "import_run_id": str(import_run_id),
            "policy_mode": str(policy_mode),
            **result.to_summary_dict(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        if result.policy_decision == "fail":
            raise SystemExit(1)
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            art_store.close()
        except Exception:
            pass


def cmd_brownfield_commit(args: Any) -> None:
    """`cmis brownfield commit IMP-...`"""

    project_root = _resolve_project_root(args)
    import_run_id = str(getattr(args, "import_run_id", "")).strip()
    policy_mode = str(getattr(args, "policy_mode", "reporting_strict"))
    base_id = getattr(args, "focal_actor_context_base_id", None)

    conn = open_brownfield_db(project_root=project_root)
    factory = StoreFactory(project_root=project_root)
    art_store = factory.artifact_store()
    ctx_store = factory.focal_actor_context_store()
    try:
        migrate_brownfield_db(conn)

        cub_id, prj_id = commit_import_run(
            project_root=project_root,
            import_run_id=import_run_id,
            policy_mode=policy_mode,
            focal_actor_context_base_id=str(base_id) if base_id is not None else None,
            brownfield_conn=conn,
            artifact_store=art_store,
            focal_actor_context_store=ctx_store,
        )

        payload: Dict[str, Any] = {
            "ok": True,
            "import_run_id": str(import_run_id),
            "policy_mode": str(policy_mode),
            "bundle_id": str(cub_id),
            "focal_actor_context_id": str(prj_id),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            art_store.close()
        except Exception:
            pass
        try:
            ctx_store.close()
        except Exception:
            pass
