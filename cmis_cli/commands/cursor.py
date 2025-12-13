"""Cursor Agent Interface commands (cmis cursor ...).

Cursor IDE 안에서 Agent가 호출하기 좋은 '프로토콜(커맨드)'을 제공합니다.
정본은 CMIS stores(SQLite)에 저장되고, Cursor UX는 `.cmis/runs/<run_id>/` export(view)를 열람합니다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmis_core.orchestration import OrchestrationKernel, RunRequest
from cmis_core.policy_engine import PolicyEngine
from cmis_core.run_exporter import RunExporter
from cmis_core.stores import LedgerStore, RunStore
from cmis_core.stores.sqlite_base import StoragePaths


def cmd_cursor_init(args) -> None:
    """cmis cursor init"""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()
    # StoragePaths.resolve()가 디렉토리 생성까지 수행하므로 store 초기화로 충분
    run_store = RunStore(project_root=project_root)
    ledger_store = LedgerStore(project_root=project_root)
    run_store.close()
    ledger_store.close()

    print("CMIS Cursor init: OK")
    print(f"- project_root: {project_root}")
    print("- created: .cmis/db, .cmis/runs")


def _collect_doctor_issues(project_root: Path) -> list[str]:
    issues: list[str] = []

    # 1) YAML syntax checks
    for rel in ["cmis.yaml", "config/policies.yaml", "config/workflows.yaml"]:
        p = project_root / rel
        if not p.exists():
            issues.append(f"missing_file:{rel}")
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except Exception as e:
            issues.append(f"yaml_parse_error:{rel}:{e}")

    # 2) Store write checks
    try:
        run_store = RunStore(project_root=project_root)
        ledger_store = LedgerStore(project_root=project_root)
        run_store.close()
        ledger_store.close()
    except Exception as e:
        issues.append(f"store_init_failed:{e}")

    return issues


def _build_manifest(project_root: Path) -> Dict[str, Any]:
    # roles: from cmis.yaml
    roles = []
    cmis_yaml_path = project_root / "cmis.yaml"
    if cmis_yaml_path.exists():
        with open(cmis_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        roles = (data.get("cmis", {}).get("planes", {}).get("role_plane", {}).get("roles", [])) or []

    # workflows: from config/workflows.yaml
    workflows = {}
    workflows_path = project_root / "config" / "workflows.yaml"
    if workflows_path.exists():
        with open(workflows_path, "r", encoding="utf-8") as f:
            wf_data = yaml.safe_load(f) or {}
        workflows = wf_data.get("canonical_workflows", {}) or {}

    # policies: via PolicyEngine
    policy_engine = PolicyEngine(project_root=project_root)
    policies = policy_engine.list_policies()

    return {
        "schema_version": 1,
        "roles": roles,
        "workflows": list(workflows.keys()),
        "policy_modes": policies,
    }


def cmd_cursor_doctor(args) -> None:
    """cmis cursor doctor"""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()

    issues = _collect_doctor_issues(project_root)

    if issues:
        print("CMIS Doctor: FAIL")
        for it in issues:
            print(f"- {it}")
        return

    print("CMIS Doctor: OK")
    print(f"- project_root: {project_root}")


def cmd_cursor_manifest(args) -> None:
    """cmis cursor manifest"""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()
    manifest = _build_manifest(project_root)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def cmd_cursor_bootstrap(args) -> None:
    """cmis cursor bootstrap

    온보딩(초기화+환경점검+manifest 저장)을 단일 커맨드로 수행합니다.
    """
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()
    paths = StoragePaths.resolve(project_root)

    print("=" * 60)
    print("CMIS Cursor Bootstrap")
    print("=" * 60)
    print(f"- project_root: {project_root}")
    print(f"- storage_root: {paths.storage_root}")

    # 0) .env 생성 (옵션)
    env_path = project_root / ".env"
    env_example = project_root / "env.example"

    if not args.no_env:
        if env_path.exists() and args.force_env:
            if env_example.exists():
                env_path.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
                print("- .env: overwritten from env.example")
            else:
                print("- .env: exists, env.example missing (skip overwrite)")
        elif not env_path.exists():
            if env_example.exists():
                env_path.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
                print("- .env: created from env.example")
            else:
                print("- .env: env.example not found (skip)")
        else:
            print("- .env: exists (skip)")
    else:
        print("- .env: skipped by --no-env")

    # 1) init
    run_store = RunStore(project_root=project_root)
    ledger_store = LedgerStore(project_root=project_root)
    run_store.close()
    ledger_store.close()
    print(f"- stores: initialized at {paths.cmis_dir}")

    # 2) doctor
    issues = _collect_doctor_issues(project_root)
    if issues:
        print("- doctor: FAIL")
        for it in issues:
            print(f"  - {it}")
        # non-zero exit for automation
        raise SystemExit(1)

    print("- doctor: OK")

    # 3) manifest (save + optional print)
    manifest = _build_manifest(project_root)
    manifest_path = paths.cmis_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"- manifest: saved to {manifest_path}")

    if args.print_manifest:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))

    # 4) optional smoke run
    if args.smoke_run:
        policy_engine = PolicyEngine(project_root=project_root)
        run_store = RunStore(project_root=project_root)
        ledger_store = LedgerStore(project_root=project_root)

        kernel = OrchestrationKernel(
            project_root=project_root,
            policy_engine=policy_engine,
            run_store=run_store,
            ledger_store=ledger_store,
        )

        context: Dict[str, Any] = {
            "domain_id": args.domain,
            "region": args.region,
        }
        if args.segment:
            context["segment"] = args.segment

        req = RunRequest(
            query=args.smoke_query,
            interface_id="cursor_agent",
            policy_id=args.policy,
            budgets={"max_iterations": args.max_iterations, "max_time_sec": args.max_time_sec},
            context=context,
        )
        result = kernel.execute(req)

        exporter = RunExporter(project_root=project_root)
        run_dir = exporter.export_run(
            run_id=result.run_id,
            run_store=run_store,
            ledger_store=ledger_store,
            policy_engine=policy_engine,
        )

        print(f"- smoke_run: run_id={result.run_id} status={result.status} run_dir={run_dir}")

        run_store.close()
        ledger_store.close()

    print("Bootstrap: OK")


def cmd_cursor_ask(args) -> None:
    """cmis cursor ask"""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()

    query = args.query
    context: Dict[str, Any] = {
        "domain_id": args.domain,
        "region": args.region,
        "segment": args.segment,
        "as_of": args.as_of,
        "project_context_id": args.project_context,
        "role_id": args.role,
    }
    # remove None
    context = {k: v for k, v in context.items() if v is not None}

    budgets = {
        "max_iterations": args.max_iterations,
        "max_time_sec": args.max_time_sec,
    }

    # stores + engines
    run_store = RunStore(project_root=project_root)
    ledger_store = LedgerStore(project_root=project_root)
    policy_engine = PolicyEngine(project_root=project_root)

    kernel = OrchestrationKernel(
        project_root=project_root,
        policy_engine=policy_engine,
        run_store=run_store,
        ledger_store=ledger_store,
    )

    req = RunRequest(
        query=query,
        interface_id="cursor_agent",
        role_id=args.role,
        policy_id=args.policy,
        run_mode=args.mode,
        budgets=budgets,
        context=context,
    )

    result = kernel.execute(req)

    # export view
    exporter = RunExporter(project_root=project_root)
    run_dir = exporter.export_run(run_id=result.run_id, run_store=run_store, ledger_store=ledger_store, policy_engine=policy_engine)

    # stdout summary (Cursor Agent가 읽기 쉬운 형태)
    print("=" * 60)
    print("CMIS Cursor Ask Result")
    print("=" * 60)
    print(f"run_id: {result.run_id}")
    print(f"status: {result.status}")
    print(f"goal_satisfied: {result.goal_satisfied}")
    print(f"role_id: {result.role_id}")
    print(f"policy_id: {result.policy_id}")
    print(f"run_dir: {run_dir}")
    print(f"iterations: {result.iterations}")

    # Guardian scoreboard (minimal)
    progress = (result.ledgers.get("progress_ledger") or {})
    budgets_used = (progress.get("budgets") or {})
    stall = (progress.get("stall_counters") or {})
    replans = progress.get("replanning_count")

    print("-" * 60)
    print("Guardian scoreboard")
    print("- budget.time_spent_sec:", budgets_used.get("time_spent_sec"))
    print("- budget.max_time_sec:", args.max_time_sec)
    print("- budget.max_iterations:", args.max_iterations)
    print("- replanning_count:", replans)
    print("- stall_counters:", stall)

    run_store.close()
    ledger_store.close()

