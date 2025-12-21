"""db-manage 명령어

런타임 스토리지(`.cmis/`)의 마이그레이션/리셋을 수행합니다.

- migrate: legacy key(project_context_id 등) -> focal_actor_context_id 계열로 변환
  - 대상(존재하는 경우):
    - `.cmis/db/*.db` (runs/ledgers/contexts/outcomes/artifacts 등)
    - `.cmis/evidence_cache.db` (legacy EvidenceStore sqlite backend)
    - `.cmis/value_store/*.json` (PriorManager)
- reset: `.cmis` 런타임 스토어를 백업 후 초기화
  - 기본 포함: `.cmis/db`, `.cmis/runs`, `.cmis/artifacts`, `.cmis/value_store`, `.cmis/cache`, `.cmis/evidence_cache.db`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from cmis_core.brownfield.outbox import reconcile_brownfield_outbox
from cmis_core.storage_migration import migrate_runtime_storage, reset_runtime_storage


def _as_path(p: Optional[str]) -> Optional[Path]:
    if not p:
        return None
    return Path(p)


def cmd_db_manage(args) -> None:
    """db-manage 명령 실행"""

    print("=" * 60)
    print("CMIS - DB Management (.cmis)")
    print("=" * 60)
    print()

    project_root = _as_path(getattr(args, "project_root", None))

    do_migrate = bool(getattr(args, "migrate", False))
    do_reset = bool(getattr(args, "reset", False))
    do_reconcile = bool(getattr(args, "reconcile", False))

    if do_reset and (do_migrate or do_reconcile):
        raise ValueError("--reset cannot be combined with --migrate/--reconcile")

    if not do_migrate and not do_reset and not do_reconcile:
        print("사용법:")
        print("  cmis db-manage --migrate [--project-root <path>] [--skip-reexport]")
        print("  cmis db-manage --reset [--project-root <path>] [--no-backup] [--keep-runs]")
        print("  cmis db-manage --reconcile [--project-root <path>] [--import-run-id IMP-...] [--retry-failed] [--limit N]")
        return

    if do_reset:
        backup = not bool(getattr(args, "no_backup", False))
        reset_runs_dir = not bool(getattr(args, "keep_runs", False))

        report = reset_runtime_storage(
            project_root=project_root,
            backup=backup,
            reset_runs_dir=reset_runs_dir,
        )

        print("[OK] reset completed")
        print(f"- storage_root: {report.get('storage_root')}")
        print(f"- backup: {report.get('backup')}")
        if report.get("backup_root"):
            print(f"- backup_root: {report.get('backup_root')}")
        moved = report.get("moved") or {}
        if moved:
            print("- moved:")
            for k, v in moved.items():
                print(f"  - {k}: {v}")
        print()
        return

    # migrate
    if do_migrate:
        skip_reexport = bool(getattr(args, "skip_reexport", False))

        report = migrate_runtime_storage(
            project_root=project_root,
            reexport_runs=(not skip_reexport),
        )

        print("[OK] migration completed")
        print(f"- storage_root: {report.get('storage_root')}")
        print(f"- db_dir: {report.get('db_dir')}")

        updated = report.get("updated") or {}
        if updated:
            print("- updated:")
            for db_name, info in updated.items():
                rows = info.get("updated_rows")
                touched = info.get("touched_tables")
                print(f"  - {db_name}: updated_rows={rows} touched={touched}")

        rexport = report.get("run_export")
        if rexport:
            print(f"- run_export: count={rexport.get('count')}")
        print()

    if do_reconcile:
        import_run_id = getattr(args, "import_run_id", None)
        retry_failed = bool(getattr(args, "retry_failed", False))
        limit = int(getattr(args, "limit", 50) or 50)

        rep = reconcile_brownfield_outbox(
            project_root=(project_root or Path.cwd()),
            import_run_id=(str(import_run_id).strip() if import_run_id else None),
            retry_failed=retry_failed,
            limit=limit,
        )

        print("[OK] reconcile completed")
        print(f"- processed: {rep.get('count')}")
        processed = rep.get("processed") or []
        if isinstance(processed, list) and processed:
            failed = [it for it in processed if isinstance(it, dict) and it.get("status") == "failed"]
            if failed:
                print(f"- failed: {len(failed)}")
                # non-zero exit for automation
                raise SystemExit(1)
        print()
