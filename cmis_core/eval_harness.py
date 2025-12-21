"""Eval Harness (Phase 1).

목표:
- `eval/regression_suite.yaml`, `eval/canary_domains.yaml`을 기반으로
  회귀/카나리 테스트를 실행합니다.
- 실행 결과를 `RunStore`에 기록하고, 임계치(thresholds) 위반 시 FAIL로 차단합니다.

주의:
- Phase 1은 규칙/지표를 최소 단위로만 제공하며, 스키마는 점진적으로 확장됩니다.
- 본 러너는 Cursor IDE 도구를 직접 호출하지 않습니다(엔진/워크플로우 실행만).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

import yaml

from cmis_core.orchestration import OrchestrationKernel, RunRequest, RunResult
from cmis_core.policy_engine import PolicyEngine
from cmis_core.stores import StoreFactory


@dataclass(frozen=True)
class EvalThresholds:
    """회귀 테스트 임계치(기본값은 fail-open)."""

    require_success: bool = True

    # 0..1
    max_avg_prior_ratio: float = 1.0
    max_policy_failure_rate: float = 1.0
    min_evidence_hit_rate: float = 0.0


@dataclass(frozen=True)
class EvalTestSpec:
    test_id: str
    query: str
    context: Dict[str, Any]
    policy_id: str
    budgets: Dict[str, Any]
    thresholds: EvalThresholds


@dataclass(frozen=True)
class EvalTestResult:
    test_id: str
    run_id: str
    status: str
    goal_satisfied: bool
    metrics: Dict[str, Any]
    thresholds: Dict[str, Any]
    passed: bool
    failures: List[str]


@dataclass(frozen=True)
class EvalSuiteResult:
    eval_run_id: str
    status: str
    started_at: str
    ended_at: str
    tests: List[EvalTestResult]


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return doc if isinstance(doc, dict) else {}


def _coerce_thresholds(d: Dict[str, Any], defaults: EvalThresholds) -> EvalThresholds:
    if not isinstance(d, dict):
        return defaults

    def _b(name: str, default: bool) -> bool:
        v = d.get(name)
        return default if v is None else bool(v)

    def _f(name: str, default: float) -> float:
        v = d.get(name)
        try:
            return default if v is None else float(v)
        except (TypeError, ValueError):
            return default

    return EvalThresholds(
        require_success=_b("require_success", defaults.require_success),
        max_avg_prior_ratio=_f("max_avg_prior_ratio", defaults.max_avg_prior_ratio),
        max_policy_failure_rate=_f("max_policy_failure_rate", defaults.max_policy_failure_rate),
        min_evidence_hit_rate=_f("min_evidence_hit_rate", defaults.min_evidence_hit_rate),
    )


def _parse_suite(doc: Dict[str, Any]) -> Tuple[EvalThresholds, Dict[str, Any], List[Dict[str, Any]]]:
    suite = doc.get("regression_suite", {}) if isinstance(doc, dict) else {}
    if not isinstance(suite, dict):
        suite = {}

    defaults_doc = suite.get("defaults", {})
    if not isinstance(defaults_doc, dict):
        defaults_doc = {}

    thresholds_default = _coerce_thresholds(defaults_doc.get("thresholds", {}) or {}, EvalThresholds())
    run_defaults = {
        "interface_id": str(defaults_doc.get("interface_id") or "eval_harness"),
        "policy_id": str(defaults_doc.get("policy_id") or "exploration_friendly"),
        "budgets": (defaults_doc.get("budgets") if isinstance(defaults_doc.get("budgets"), dict) else {}),
    }

    tests = suite.get("tests", [])
    if not isinstance(tests, list):
        tests = []

    return thresholds_default, run_defaults, [t for t in tests if isinstance(t, dict)]


def _extract_project_and_progress_ledgers(run_result: RunResult) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    ledgers = run_result.ledgers or {}
    if not isinstance(ledgers, dict):
        return {}, {}
    project_ledger = ledgers.get("project_ledger") or {}
    progress_ledger = ledgers.get("progress_ledger") or {}
    return (
        project_ledger if isinstance(project_ledger, dict) else {},
        progress_ledger if isinstance(progress_ledger, dict) else {},
    )


def _compute_eval_metrics(run_result: RunResult) -> Dict[str, Any]:
    project_ledger, progress_ledger = _extract_project_and_progress_ledgers(run_result)

    required_metrics = []
    evidence_plan = project_ledger.get("evidence_plan") or {}
    if isinstance(evidence_plan, dict) and isinstance(evidence_plan.get("required_metrics"), list):
        required_metrics = [str(x) for x in (evidence_plan.get("required_metrics") or [])]

    metrics = project_ledger.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}

    if not required_metrics:
        required_metrics = [str(k) for k in metrics.keys()]

    n = len(required_metrics)
    denom = float(n) if n else 1.0

    prior_ratios: List[float] = []
    evidence_hits = 0
    policy_failures = 0

    for mid in required_metrics:
        entry = metrics.get(mid, {}) or {}
        if not isinstance(entry, dict):
            continue

        metric_eval = entry.get("metric_eval") or {}
        if isinstance(metric_eval, dict):
            try:
                prior_ratios.append(float(metric_eval.get("prior_ratio", 0.0) or 0.0))
            except (TypeError, ValueError):
                prior_ratios.append(0.0)
        else:
            prior_ratios.append(0.0)

        evidence_summary = entry.get("evidence_summary") or {}
        if isinstance(evidence_summary, dict):
            try:
                if int(evidence_summary.get("num_sources", 0) or 0) >= 1:
                    evidence_hits += 1
            except (TypeError, ValueError):
                pass

        policy_check = entry.get("policy_check") or {}
        if isinstance(policy_check, dict):
            if not bool(policy_check.get("passed", False)):
                policy_failures += 1
        else:
            policy_failures += 1

    avg_prior = (sum(prior_ratios) / denom) if prior_ratios else 0.0
    evidence_hit_rate = float(evidence_hits) / denom
    policy_failure_rate = float(policy_failures) / denom

    return {
        "required_metrics": list(required_metrics),
        "num_required_metrics": n,
        "avg_prior_ratio": avg_prior,
        "evidence_hit_rate": evidence_hit_rate,
        "policy_failure_rate": policy_failure_rate,
        "diff_reports_count": len(progress_ledger.get("diff_reports") or []),
        "replanning_count": int(progress_ledger.get("replanning_count") or 0),
        "stall_count": int(progress_ledger.get("stall_count") or 0),
    }


def _evaluate_thresholds(run_result: RunResult, metrics: Dict[str, Any], thresholds: EvalThresholds) -> Tuple[bool, List[str]]:
    failures: List[str] = []

    if thresholds.require_success and (not bool(run_result.goal_satisfied)):
        failures.append("goal_satisfied == False")

    try:
        if float(metrics.get("avg_prior_ratio", 0.0)) > float(thresholds.max_avg_prior_ratio):
            failures.append(
                f"avg_prior_ratio {metrics.get('avg_prior_ratio'):.3f} > max_avg_prior_ratio {thresholds.max_avg_prior_ratio:.3f}"
            )
    except Exception:
        pass

    try:
        if float(metrics.get("policy_failure_rate", 0.0)) > float(thresholds.max_policy_failure_rate):
            failures.append(
                f"policy_failure_rate {metrics.get('policy_failure_rate'):.3f} > max_policy_failure_rate {thresholds.max_policy_failure_rate:.3f}"
            )
    except Exception:
        pass

    try:
        if float(metrics.get("evidence_hit_rate", 0.0)) < float(thresholds.min_evidence_hit_rate):
            failures.append(
                f"evidence_hit_rate {metrics.get('evidence_hit_rate'):.3f} < min_evidence_hit_rate {thresholds.min_evidence_hit_rate:.3f}"
            )
    except Exception:
        pass

    return (len(failures) == 0), failures


class EvalHarnessRunner:
    """회귀/카나리 테스트 러너."""

    def __init__(
        self,
        *,
        project_root: Path,
        suite_path: Path,
        canary_path: Optional[Path] = None,
        enable_stub_source: bool = False,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.suite_path = Path(suite_path).resolve()
        self.canary_path = (None if canary_path is None else Path(canary_path).resolve())
        self.enable_stub_source = bool(enable_stub_source)

    def run(self) -> EvalSuiteResult:
        started_at = datetime.now(timezone.utc).isoformat()
        eval_run_id = f"EVAL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        suite_doc = _read_yaml(self.suite_path)
        thresholds_default, run_defaults, tests_doc = _parse_suite(suite_doc)

        # Stores (authoritative)
        factory = StoreFactory(project_root=self.project_root)
        run_store = factory.run_store()
        ledger_store = factory.ledger_store()
        policy_engine = PolicyEngine(project_root=self.project_root)

        kernel = OrchestrationKernel(
            project_root=self.project_root,
            policy_engine=policy_engine,
            run_store=run_store,
            ledger_store=ledger_store,
            enable_stub_source=self.enable_stub_source,
        )

        run_store.create_run(
            {
                "run_id": eval_run_id,
                "started_at": started_at,
                "status": "running",
                "interface_id": "eval_harness",
                "query": f"regression_suite:{self.suite_path.name}",
                "role_id": "eval",
                "policy_id": str(run_defaults.get("policy_id") or ""),
                "run_mode": "manual",
                "context": {
                    "suite_path": str(self.suite_path),
                    "canary_path": (None if self.canary_path is None else str(self.canary_path)),
                    "enable_stub_source": self.enable_stub_source,
                },
            }
        )

        results: List[EvalTestResult] = []

        for t in tests_doc:
            test_id = str(t.get("id") or t.get("test_id") or f"test-{uuid.uuid4().hex[:6]}")
            query = str(t.get("query") or "")
            context = t.get("context") if isinstance(t.get("context"), dict) else {}
            policy_id = str(t.get("policy_id") or run_defaults.get("policy_id") or "exploration_friendly")
            budgets = run_defaults.get("budgets") if isinstance(run_defaults.get("budgets"), dict) else {}
            budgets = (t.get("budgets") if isinstance(t.get("budgets"), dict) else budgets)

            thresholds = _coerce_thresholds(t.get("thresholds") or {}, thresholds_default)

            req = RunRequest(
                query=query,
                interface_id="eval_harness",
                policy_id=policy_id,
                budgets=dict(budgets or {}),
                context=dict(context or {}),
            )

            rr = kernel.execute(req)
            metrics = _compute_eval_metrics(rr)
            passed, failures = _evaluate_thresholds(rr, metrics, thresholds)

            tr = EvalTestResult(
                test_id=test_id,
                run_id=rr.run_id,
                status=rr.status,
                goal_satisfied=bool(rr.goal_satisfied),
                metrics=metrics,
                thresholds={
                    "require_success": thresholds.require_success,
                    "max_avg_prior_ratio": thresholds.max_avg_prior_ratio,
                    "max_policy_failure_rate": thresholds.max_policy_failure_rate,
                    "min_evidence_hit_rate": thresholds.min_evidence_hit_rate,
                },
                passed=bool(passed),
                failures=list(failures),
            )
            results.append(tr)

            run_store.append_decision(
                eval_run_id,
                {
                    "type": "eval_test_result",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "test_id": test_id,
                        "run_id": rr.run_id,
                        "passed": bool(passed),
                        "failures": list(failures),
                        "metrics": metrics,
                        "policy_id": policy_id,
                    },
                },
            )

        all_passed = all(r.passed for r in results)
        status = "success" if all_passed else "failed"
        ended_at = datetime.now(timezone.utc).isoformat()

        run_store.finalize_run(
            eval_run_id,
            status,
            {
                "status": status,
                "total_tests": len(results),
                "passed_tests": sum(1 for r in results if r.passed),
                "failed_tests": sum(1 for r in results if not r.passed),
                "test_run_ids": [r.run_id for r in results],
            },
        )

        run_store.close()
        ledger_store.close()

        return EvalSuiteResult(
            eval_run_id=eval_run_id,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            tests=results,
        )
