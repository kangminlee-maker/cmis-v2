"""Run export (Cursor-friendly view).

정본은 stores(SQLite)에 있고, Cursor UX를 위해 파일 기반 view를 생성합니다.

폴더 규약:
  <storage_root>/.cmis/runs/<run_id>/
    - request.yaml
    - policy.json
    - project_ledger.yaml
    - progress_ledger.yaml
    - events.jsonl
    - decision_log.jsonl
    - results.md
    - refs.json
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional
import json

import yaml

from cmis_core.policy_engine import PolicyEngine
from cmis_core.stores import LedgerStore, RunStore
from cmis_core.stores.sqlite_base import StoragePaths


class RunExporter:
    """Run export(view) 생성기"""

    def __init__(self, *, project_root: Optional[Path] = None) -> None:
        self.paths = StoragePaths.resolve(project_root)

    def export_run(
        self,
        *,
        run_id: str,
        run_store: RunStore,
        ledger_store: LedgerStore,
        policy_engine: PolicyEngine,
    ) -> Path:
        run_dir = self.paths.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        run = run_store.get_run(run_id) or {}
        snapshot = ledger_store.get_latest_snapshot(run_id) or {}

        project_ledger = snapshot.get("project_ledger") or {}
        progress_ledger = snapshot.get("progress_ledger") or {}

        # 1) request.yaml
        request_yaml = {
            "schema_version": 1,
            "run_id": run_id,
            "interface_id": run.get("interface_id"),
            "query": run.get("query"),
            "role_id": run.get("role_id"),
            "policy_id": run.get("policy_id"),
            "run_mode": run.get("run_mode"),
            "context": run.get("context") or {},
            "started_at": run.get("started_at"),
        }
        self._write_yaml(run_dir / "request.yaml", request_yaml)

        # 2) policy.json (compiled)
        policy_id = str(run.get("policy_id") or progress_ledger.get("policy_id") or "decision_balanced")
        policy_obj = policy_engine.get_policy(policy_id)
        self._write_json(run_dir / "policy.json", policy_obj.to_dict())

        # 3) ledgers
        self._write_yaml(run_dir / "project_ledger.yaml", project_ledger)
        self._write_yaml(run_dir / "progress_ledger.yaml", progress_ledger)

        # 4) streams
        events = run_store.list_events(run_id)
        decisions = run_store.list_decisions(run_id)
        self._write_jsonl(run_dir / "events.jsonl", events)
        self._write_jsonl(run_dir / "decision_log.jsonl", decisions)

        # 5) refs.json
        refs = self._build_refs(project_ledger)
        self._write_json(run_dir / "refs.json", refs)

        # 6) results.md
        results_md = self._render_results_md(run, project_ledger, progress_ledger, refs)
        (run_dir / "results.md").write_text(results_md, encoding="utf-8")

        return run_dir

    @staticmethod
    def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_jsonl(path: Path, items: list[Dict[str, Any]]) -> None:
        lines = [json.dumps(it, ensure_ascii=False) for it in items]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    @staticmethod
    def _build_refs(project_ledger: Dict[str, Any]) -> Dict[str, Any]:
        evidence_refs = list(project_ledger.get("evidence_refs", []))
        value_refs = list(project_ledger.get("value_refs", []))

        metrics = project_ledger.get("metrics") or {}
        metric_ids = sorted(list(metrics.keys()))

        evidence_ids_from_values = []
        for m in metrics.values():
            vr = (m.get("value_record") or {})
            lineage = (vr.get("lineage") or {})
            for eid in lineage.get("from_evidence_ids", []) or []:
                evidence_ids_from_values.append(eid)

        all_evidence_ids = sorted(list({*evidence_refs, *evidence_ids_from_values}))

        return {
            "metric_ids": metric_ids,
            "evidence_ids": all_evidence_ids,
            "value_refs": value_refs,
        }

    @staticmethod
    def _render_results_md(
        run: Dict[str, Any],
        project_ledger: Dict[str, Any],
        progress_ledger: Dict[str, Any],
        refs: Dict[str, Any],
    ) -> str:
        status = run.get("status") or progress_ledger.get("overall_status") or "unknown"
        query = run.get("query") or ""
        role_id = run.get("role_id") or progress_ledger.get("role_id") or ""
        policy_id = run.get("policy_id") or progress_ledger.get("policy_id") or ""

        lines: list[str] = []
        lines.append("# CMIS Run Results")
        lines.append("")
        lines.append(f"- status: {status}")
        lines.append(f"- query: {query}")
        lines.append(f"- role_id: {role_id}")
        lines.append(f"- policy_id: {policy_id}")
        lines.append("")

        lines.append("## Metrics")
        lines.append("")
        metrics = project_ledger.get("metrics") or {}
        if not metrics:
            lines.append("- (none)")
        else:
            for metric_id in sorted(metrics.keys()):
                entry = metrics[metric_id] or {}
                vr = entry.get("value_record") or {}
                pe = vr.get("point_estimate")
                dist = vr.get("distribution")
                pc = entry.get("policy_check") or {}
                passed = pc.get("passed")
                lines.append(f"- {metric_id}: point={pe} dist={dist} policy_passed={passed}")

        lines.append("")
        lines.append("## Refs")
        lines.append("")
        lines.append(f"- metric_ids: {refs.get('metric_ids', [])}")
        lines.append(f"- evidence_ids: {refs.get('evidence_ids', [])}")
        lines.append("")

        lines.append("## Next")
        lines.append("")
        lines.append("- 상세 이벤트: events.jsonl")
        lines.append("- 결정 로그: decision_log.jsonl")
        lines.append("- Ledger: project_ledger.yaml / progress_ledger.yaml")

        return "\n".join(lines) + "\n"

