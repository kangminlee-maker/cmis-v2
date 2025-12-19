"""Cursor Agent Interface v2 - core unit tests.

범위:
- RunStore/LedgerStore(SQLite) 기본 동작
- OrchestrationKernel 실행 후 store 기록
- RunExporter export(view) 파일 생성
"""

from __future__ import annotations

from pathlib import Path
import yaml

from cmis_core.orchestration import OrchestrationKernel, RunRequest
from cmis_core.policy_engine import PolicyEngine
from cmis_core.run_exporter import RunExporter
from cmis_core.stores import LedgerStore, RunStore


def test_run_store_and_exporter_smoke(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    # isolate runtime artifacts
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    run_store = RunStore(project_root=project_root)
    ledger_store = LedgerStore(project_root=project_root)
    policy_engine = PolicyEngine(project_root=project_root)

    kernel = OrchestrationKernel(
        project_root=project_root,
        policy_engine=policy_engine,
        run_store=run_store,
        ledger_store=ledger_store,
        enable_stub_source=True,  # avoid external APIs
    )

    req = RunRequest(
        query="한국 어학 시장 분석",
        interface_id="cursor_agent",
        policy_id="exploration_friendly",
        budgets={"max_iterations": 5, "max_time_sec": 30},
        context={
            "domain_id": "Adult_Language_Education_KR",
            "region": "KR",
        },
    )

    result = kernel.execute(req)

    assert result.run_id.startswith("RUN-")
    assert result.interface_id == "cursor_agent"
    assert result.policy_id == "exploration_friendly"
    assert isinstance(result.events, list)
    assert isinstance(result.decision_log, list)

    # run store populated
    run = run_store.get_run(result.run_id)
    assert run is not None
    assert run["run_id"] == result.run_id
    assert run["policy_id"] == "exploration_friendly"
    assert any((e.get("type") == "tool_calls") for e in run_store.list_events(result.run_id))

    # ledger snapshot exists
    snapshot = ledger_store.get_latest_snapshot(result.run_id)
    assert snapshot is not None
    assert "project_ledger" in snapshot
    assert "progress_ledger" in snapshot
    project_ledger = snapshot["project_ledger"]
    progress_ledger = snapshot["progress_ledger"]

    # spec-aligned ledger fields (Phase 1)
    for key in [
        "goal_graph",
        "success_predicates",
        "scope",
        "constraints",
        "evidence_plan",
        "open_questions",
        "artifact_refs",
    ]:
        assert key in project_ledger

    for key in [
        "step_index",
        "step_status",
        "stall_count",
        "diff_reports",
        "next_step_suggestion",
        "last_engine_calls",
        "last_tool_calls",
    ]:
        assert key in progress_ledger

    # D-Graph view (Phase 1): goal_graph includes planned task nodes/edges
    goal_graph = project_ledger.get("goal_graph") or {}
    assert isinstance(goal_graph, dict)
    nodes = goal_graph.get("nodes") or []
    edges = goal_graph.get("edges") or []
    assert any(isinstance(n, dict) and n.get("type") == "task" for n in nodes)
    assert any(isinstance(e, dict) and e.get("type") == "plans" for e in edges)

    # export view created
    exporter = RunExporter(project_root=project_root)
    run_dir = exporter.export_run(
        run_id=result.run_id,
        run_store=run_store,
        ledger_store=ledger_store,
        policy_engine=policy_engine,
    )

    required = [
        "request.yaml",
        "policy.json",
        "project_ledger.yaml",
        "progress_ledger.yaml",
        "events.jsonl",
        "decision_log.jsonl",
        "results.md",
        "refs.json",
    ]
    for name in required:
        assert (run_dir / name).exists()

    # YAML parse sanity
    with open(run_dir / "request.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data["run_id"] == result.run_id

    run_store.close()
    ledger_store.close()


def test_kernel_run_mode_approval_required_plans_but_does_not_execute(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    run_store = RunStore(project_root=project_root)
    ledger_store = LedgerStore(project_root=project_root)
    policy_engine = PolicyEngine(project_root=project_root)

    kernel = OrchestrationKernel(
        project_root=project_root,
        policy_engine=policy_engine,
        run_store=run_store,
        ledger_store=ledger_store,
        enable_stub_source=True,
    )

    req = RunRequest(
        query="한국 어학 시장 분석",
        interface_id="cursor_agent",
        policy_id="exploration_friendly",
        run_mode="approval_required",
        budgets={"max_iterations": 5, "max_time_sec": 30},
        context={
            "domain_id": "Adult_Language_Education_KR",
            "region": "KR",
        },
    )

    result = kernel.execute(req)

    assert result.status == "incomplete"
    assert result.iterations == 0

    snapshot = ledger_store.get_latest_snapshot(result.run_id)
    assert snapshot is not None
    progress = snapshot["progress_ledger"]
    assert progress.get("overall_status") == "incomplete"
    assert (progress.get("loop_flags") or {}).get("waiting_approval") is True
    assert progress.get("steps") == []

    project_ledger = snapshot["project_ledger"]
    goal_graph = project_ledger.get("goal_graph") or {}
    assert isinstance(goal_graph, dict)
    nodes = goal_graph.get("nodes") or []
    assert any(isinstance(n, dict) and n.get("type") == "task" for n in nodes)

    run_store.close()
    ledger_store.close()


def test_kernel_run_mode_manual_executes_single_task_then_pauses(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    run_store = RunStore(project_root=project_root)
    ledger_store = LedgerStore(project_root=project_root)
    policy_engine = PolicyEngine(project_root=project_root)

    kernel = OrchestrationKernel(
        project_root=project_root,
        policy_engine=policy_engine,
        run_store=run_store,
        ledger_store=ledger_store,
        enable_stub_source=True,
    )

    req = RunRequest(
        query="한국 어학 시장 분석",
        interface_id="cursor_agent",
        policy_id="exploration_friendly",
        run_mode="manual",
        budgets={"max_iterations": 10, "max_time_sec": 30},
        context={
            "domain_id": "Adult_Language_Education_KR",
            "region": "KR",
        },
    )

    result = kernel.execute(req)

    assert result.status == "incomplete"
    assert result.iterations == 1

    snapshot = ledger_store.get_latest_snapshot(result.run_id)
    assert snapshot is not None
    progress = snapshot["progress_ledger"]
    assert progress.get("overall_status") == "incomplete"
    assert (progress.get("loop_flags") or {}).get("manual_pause") is True
    assert len(progress.get("steps") or []) >= 1

    project_ledger = snapshot["project_ledger"]
    goal_graph = project_ledger.get("goal_graph") or {}
    assert isinstance(goal_graph, dict)
    nodes = goal_graph.get("nodes") or []
    assert any(isinstance(n, dict) and n.get("type") == "task" for n in nodes)

    run_store.close()
    ledger_store.close()
