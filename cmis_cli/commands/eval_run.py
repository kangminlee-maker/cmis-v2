"""Eval Harness CLI command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cmis_core.eval_harness import EvalHarnessRunner


def cmd_eval_run(args: Any) -> None:
    """Run eval harness.

    Args:
        args: argparse args
    """
    project_root = Path(args.project_root).resolve() if getattr(args, "project_root", None) else Path.cwd().resolve()

    suite_path = Path(getattr(args, "suite", "eval/regression_suite.yaml"))
    if not suite_path.is_absolute():
        suite_path = project_root / suite_path

    canary_path = getattr(args, "canary", None)
    canary_file = None
    if canary_path:
        p = Path(canary_path)
        canary_file = (p if p.is_absolute() else (project_root / p)).resolve()

    runner = EvalHarnessRunner(
        project_root=project_root,
        suite_path=suite_path,
        canary_path=canary_file,
        enable_stub_source=bool(getattr(args, "enable_stub_source", False)),
    )

    result = runner.run()

    print("=" * 60)
    print("CMIS - Eval Harness")
    print("=" * 60)
    print(f"eval_run_id: {result.eval_run_id}")
    print(f"status: {result.status}")
    print(f"tests: {len(result.tests)}")

    for t in result.tests:
        status = "PASS" if t.passed else "FAIL"
        print("-" * 60)
        print(f"[{status}] {t.test_id} -> {t.run_id}")
        print(f"  goal_satisfied: {t.goal_satisfied} (status: {t.status})")
        print(f"  metrics: {t.metrics}")
        if t.failures:
            print("  failures:")
            for f in t.failures:
                print(f"    - {f}")

    if result.status != "success":
        raise SystemExit(1)
