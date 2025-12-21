"""LLM model management commands (cmis llm ...).

Phase 3 목표:
- `cmis llm benchmark run --suite <suite_id>`
- `cmis llm benchmark report --run <BENCH-...>`
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from cmis_core.llm.benchmark import BenchmarkRunner, BenchmarkStore, BenchmarkSuiteRegistry


def cmd_llm_benchmark_run(args) -> None:
    """cmis llm benchmark run --suite <suite_id>"""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()
    suite_id = str(args.suite)
    llm_mode = str(getattr(args, "llm_mode", "auto") or "auto")
    dry_run = bool(getattr(args, "dry_run", False))

    runner = BenchmarkRunner(project_root=project_root)
    bench_id, run_dir, summary = runner.run_suite(suite_id, llm_mode=llm_mode, dry_run=dry_run)

    print(json.dumps({"bench_run_id": bench_id, "run_dir": str(run_dir), "summary": summary.to_dict()}, ensure_ascii=False, indent=2))


def cmd_llm_benchmark_report(args) -> None:
    """cmis llm benchmark report --run <BENCH-...>"""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()
    run_id = str(args.run_id)

    store = BenchmarkStore(project_root=project_root)
    run_dir = store.runs_dir / run_id
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        raise SystemExit(f"Benchmark run not found: {run_id} (expected {summary_path})")

    data: Dict[str, Any] = json.loads(summary_path.read_text(encoding="utf-8"))
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_llm_benchmark_list_suites(args) -> None:
    """cmis llm benchmark list-suites"""
    project_root = Path(args.project_root) if getattr(args, "project_root", None) else Path.cwd()
    reg = BenchmarkSuiteRegistry(project_root / "config" / "llm" / "benchmark_suites.yaml")
    reg.compile()
    print(json.dumps({"suites": reg.list_suites(), "registry_digest": reg.get_ref().suites_digest}, ensure_ascii=False, indent=2))


