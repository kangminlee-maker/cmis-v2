"""Run inspection commands (cmis run ...).

Phase 1에서는 Cursor UX를 위해 '열람/설명' 위주로 제공하고,
streaming/follow/replay/approve는 Phase 2+에서 확장합니다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmis_core.run_exporter import RunExporter
from cmis_core.stores import LedgerStore, RunStore
from cmis_core.policy_engine import PolicyEngine


def cmd_run_explain(args) -> None:
    """cmis run explain RUN-..."""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()
    run_id = args.run_id

    run_store = RunStore(project_root=project_root)
    decisions = run_store.list_decisions(run_id)
    run = run_store.get_run(run_id) or {}

    print("=" * 60)
    print("CMIS Run Explain")
    print("=" * 60)
    print(f"run_id: {run_id}")
    print(f"status: {run.get('status')}")
    print(f"query: {run.get('query')}")
    print()

    if not decisions:
        print("(no decisions)")
        run_store.close()
        return

    # 요약: decision type 빈도 + 최근 10개
    counts: Dict[str, int] = {}
    for d in decisions:
        t = d.get("type", "unknown")
        counts[t] = counts.get(t, 0) + 1

    print("Decision types:")
    for k in sorted(counts.keys()):
        print(f"- {k}: {counts[k]}")

    print()
    print("Last decisions:")
    for d in decisions[-10:]:
        print(json.dumps(d, ensure_ascii=False))

    run_store.close()


def cmd_run_open(args) -> None:
    """cmis run open RUN-... (export view path 출력)"""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()
    run_id = args.run_id

    run_store = RunStore(project_root=project_root)
    ledger_store = LedgerStore(project_root=project_root)
    policy_engine = PolicyEngine(project_root=project_root)

    exporter = RunExporter(project_root=project_root)
    run_dir = exporter.export_run(run_id=run_id, run_store=run_store, ledger_store=ledger_store, policy_engine=policy_engine)

    print(str(run_dir))

    run_store.close()
    ledger_store.close()

