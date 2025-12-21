"""LLM Benchmark framework (Phase 3).

목적(비개발자 설명):
- LLM 모델/정책/프롬프트 변경을 "감"이 아니라 "숫자"로 승격하기 위한 벤치마크 러너입니다.
- 결과는 `.cmis/benchmarks/runs/<BENCH-...>/`에 저장되고,
  history는 `.cmis/benchmarks/history/`에 시계열로 누적됩니다.

설계 문서:
- dev/docs/architecture/CMIS_LLM_Model_Management_Design_v1.1.0.md (Section 9)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json
import uuid

import yaml

from cmis_core.digest import canonical_digest
from cmis_core.llm.quality_gate import QualityGateEngine
from cmis_core.llm.service import LLMService, create_llm_service
from cmis_core.llm.task_spec_registry import TaskSpecRegistry
from cmis_core.llm.types import CMISTaskType
from cmis_core.config import CMISConfig
from cmis_core.stores.factory import StoreFactory
from cmis_core.stores.sqlite_base import StoragePaths


class BenchmarkError(RuntimeError):
    """Benchmark 실행/검증 실패."""


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_dict(obj: Any, *, where: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise BenchmarkError(f"{where} must be a dict")
    return obj


def _ensure_list(obj: Any, *, where: str) -> List[Any]:
    if not isinstance(obj, list):
        raise BenchmarkError(f"{where} must be a list")
    return obj


def _ensure_str(obj: Any, *, where: str) -> str:
    if not isinstance(obj, str) or obj.strip() == "":
        raise BenchmarkError(f"{where} must be a non-empty string")
    return obj


@dataclass(frozen=True)
class BenchmarkJudgeSpec:
    judge_task_type: str
    judge_model_id: Optional[str] = None
    judge_policy_ref: Optional[str] = None
    judge_prompt_profile: str = "benchmark_judge_v1"
    judge_version_pin: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judge_task_type": str(self.judge_task_type),
            "judge_model_id": (None if self.judge_model_id is None else str(self.judge_model_id)),
            "judge_policy_ref": (None if self.judge_policy_ref is None else str(self.judge_policy_ref)),
            "judge_prompt_profile": str(self.judge_prompt_profile),
            "judge_version_pin": bool(self.judge_version_pin),
        }


@dataclass(frozen=True)
class BenchmarkCaseSpec:
    case_id: str
    input_text: str
    expected_json: Optional[Dict[str, Any]] = None
    expected_text_contains: List[str] = field(default_factory=list)
    judge_expected_json: Optional[Dict[str, Any]] = None  # deterministic smoke용

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.case_id),
            "input": str(self.input_text),
            "expected_json": (None if self.expected_json is None else dict(self.expected_json)),
            "expected_text_contains": list(self.expected_text_contains or []),
            "judge_expected_json": (None if self.judge_expected_json is None else dict(self.judge_expected_json)),
        }


@dataclass(frozen=True)
class BenchmarkTaskSpec:
    task_type: str
    cases: List[BenchmarkCaseSpec] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"task_type": str(self.task_type), "cases": [c.to_dict() for c in (self.cases or [])]}


@dataclass(frozen=True)
class BenchmarkSuite:
    suite_id: str
    tier: str  # unit|scenario|human
    run_mode: str = "managed"  # managed|route
    policy_ref: Optional[str] = None
    budget_remaining_usd: float = 1.0
    max_attempts: int = 1
    judge: Optional[BenchmarkJudgeSpec] = None
    tasks: List[BenchmarkTaskSpec] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "suite_id": str(self.suite_id),
            "tier": str(self.tier),
            "run_mode": str(self.run_mode),
            "policy_ref": (None if self.policy_ref is None else str(self.policy_ref)),
            "budget_remaining_usd": float(self.budget_remaining_usd),
            "max_attempts": int(self.max_attempts),
            "tasks": [t.to_dict() for t in (self.tasks or [])],
        }
        if self.judge is not None:
            out["judge"] = self.judge.to_dict()
        return out


@dataclass(frozen=True)
class BenchmarkSuiteRegistryRef:
    schema_version: int
    suites_digest: str
    compiled_at: str


class BenchmarkSuiteRegistry:
    """YAML 기반 BenchmarkSuiteRegistry."""

    def __init__(self, yaml_path: str | Path = "config/llm/benchmark_suites.yaml") -> None:
        self.yaml_path = Path(yaml_path)
        self._suites: Dict[str, BenchmarkSuite] = {}
        self._ref: Optional[BenchmarkSuiteRegistryRef] = None

    def compile(self) -> None:
        if not self.yaml_path.exists():
            raise BenchmarkError(f"Benchmark suites YAML not found: {self.yaml_path}")

        raw = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8")) or {}
        doc = _ensure_dict(raw, where="benchmark_suites root")
        schema_version = int(doc.get("schema_version", 0))
        if schema_version != 1:
            raise BenchmarkError(f"Unsupported schema_version: {schema_version} (expected 1)")

        suites_raw = _ensure_dict(doc.get("benchmark_suites"), where="benchmark_suites")
        suites: Dict[str, BenchmarkSuite] = {}

        for sid, s_raw in suites_raw.items():
            sid = _ensure_str(sid, where="benchmark_suites key(suite_id)")
            s = _ensure_dict(s_raw, where=f"benchmark_suites.{sid}")

            tier = _ensure_str(s.get("tier"), where=f"benchmark_suites.{sid}.tier")
            run_mode = str(s.get("run_mode", "managed") or "managed").strip()
            if run_mode not in {"managed", "route"}:
                raise BenchmarkError(f"benchmark_suites.{sid}.run_mode must be 'managed' or 'route'")

            policy_ref = s.get("policy_ref")
            if policy_ref is not None:
                policy_ref = _ensure_str(policy_ref, where=f"benchmark_suites.{sid}.policy_ref")

            try:
                budget_remaining_usd = float(s.get("budget_remaining_usd", 1.0) or 1.0)
            except Exception:
                budget_remaining_usd = 1.0
            try:
                max_attempts = int(s.get("max_attempts", 1) or 1)
            except Exception:
                max_attempts = 1

            judge: Optional[BenchmarkJudgeSpec] = None
            if "judge" in s and s.get("judge") is not None:
                j = _ensure_dict(s.get("judge"), where=f"benchmark_suites.{sid}.judge")
                judge = BenchmarkJudgeSpec(
                    judge_task_type=_ensure_str(j.get("judge_task_type"), where=f"benchmark_suites.{sid}.judge.judge_task_type"),
                    judge_model_id=(None if j.get("judge_model_id") is None else _ensure_str(j.get("judge_model_id"), where=f"benchmark_suites.{sid}.judge.judge_model_id")),
                    judge_policy_ref=(None if j.get("judge_policy_ref") is None else _ensure_str(j.get("judge_policy_ref"), where=f"benchmark_suites.{sid}.judge.judge_policy_ref")),
                    judge_prompt_profile=str(j.get("judge_prompt_profile", "benchmark_judge_v1") or "benchmark_judge_v1"),
                    judge_version_pin=bool(j.get("judge_version_pin", False)),
                )

            tasks_raw = _ensure_list(s.get("tasks") or [], where=f"benchmark_suites.{sid}.tasks")
            tasks: List[BenchmarkTaskSpec] = []
            for ti, t_raw in enumerate(tasks_raw):
                t = _ensure_dict(t_raw, where=f"benchmark_suites.{sid}.tasks[{ti}]")
                task_type = _ensure_str(t.get("task_type"), where=f"benchmark_suites.{sid}.tasks[{ti}].task_type")
                cases_raw = _ensure_list(t.get("cases") or [], where=f"benchmark_suites.{sid}.tasks[{ti}].cases")
                cases: List[BenchmarkCaseSpec] = []
                for ci, c_raw in enumerate(cases_raw):
                    c = _ensure_dict(c_raw, where=f"benchmark_suites.{sid}.tasks[{ti}].cases[{ci}]")
                    case_id = _ensure_str(c.get("id"), where=f"benchmark_suites.{sid}.tasks[{ti}].cases[{ci}].id")
                    inp = _ensure_str(c.get("input"), where=f"benchmark_suites.{sid}.tasks[{ti}].cases[{ci}].input")
                    expected_json = c.get("expected_json")
                    if expected_json is not None:
                        expected_json = _ensure_dict(expected_json, where=f"benchmark_suites.{sid}.tasks[{ti}].cases[{ci}].expected_json")
                    expected_text_contains_raw = c.get("expected_text_contains") or []
                    expected_text_contains: List[str] = []
                    if isinstance(expected_text_contains_raw, list):
                        expected_text_contains = [str(x) for x in expected_text_contains_raw if str(x).strip()]
                    judge_expected_json = c.get("judge_expected_json")
                    if judge_expected_json is not None:
                        judge_expected_json = _ensure_dict(judge_expected_json, where=f"benchmark_suites.{sid}.tasks[{ti}].cases[{ci}].judge_expected_json")

                    cases.append(
                        BenchmarkCaseSpec(
                            case_id=case_id,
                            input_text=inp,
                            expected_json=(None if expected_json is None else dict(expected_json)),
                            expected_text_contains=expected_text_contains,
                            judge_expected_json=(None if judge_expected_json is None else dict(judge_expected_json)),
                        )
                    )
                tasks.append(BenchmarkTaskSpec(task_type=task_type, cases=cases))

            suites[sid] = BenchmarkSuite(
                suite_id=sid,
                tier=tier,
                run_mode=run_mode,
                policy_ref=(None if policy_ref is None else str(policy_ref)),
                budget_remaining_usd=float(budget_remaining_usd),
                max_attempts=int(max_attempts),
                judge=judge,
                tasks=tasks,
            )

        compiled = {"schema_version": schema_version, "benchmark_suites": {sid: suites[sid].to_dict() for sid in sorted(suites.keys())}}
        digest = canonical_digest(compiled)
        self._suites = suites
        self._ref = BenchmarkSuiteRegistryRef(schema_version=schema_version, suites_digest=str(digest), compiled_at=_utc_now_iso_z())

    def get_ref(self) -> BenchmarkSuiteRegistryRef:
        if self._ref is None:
            raise BenchmarkError("BenchmarkSuiteRegistry is not compiled yet. Call compile() first.")
        return self._ref

    def get_suite(self, suite_id: str) -> BenchmarkSuite:
        sid = str(suite_id or "").strip()
        if not sid:
            raise BenchmarkError("suite_id is required")
        if sid not in self._suites:
            raise BenchmarkError(f"Unknown suite_id: {sid}")
        return self._suites[sid]

    def list_suites(self) -> List[str]:
        return sorted(self._suites.keys())


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case_id: str
    passed: bool
    latency_ms: int
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"case_id": str(self.case_id), "passed": bool(self.passed), "latency_ms": int(self.latency_ms), "metrics": dict(self.metrics or {})}


@dataclass(frozen=True)
class BenchmarkRunSummary:
    bench_run_id: str
    suite_id: str
    tier: str
    suite_digest: str
    started_at: str
    ended_at: str
    status: str
    totals: Dict[str, Any] = field(default_factory=dict)
    task_results: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bench_run_id": str(self.bench_run_id),
            "suite_id": str(self.suite_id),
            "tier": str(self.tier),
            "suite_digest": str(self.suite_digest),
            "started_at": str(self.started_at),
            "ended_at": str(self.ended_at),
            "status": str(self.status),
            "totals": dict(self.totals or {}),
            "task_results": dict(self.task_results or {}),
        }


class BenchmarkStore:
    """벤치마크 결과 저장소(.cmis/benchmarks/*)."""

    def __init__(self, *, project_root: Optional[Path] = None) -> None:
        self.paths = StoragePaths.resolve(project_root)
        self.root = self.paths.cmis_dir / "benchmarks"
        self.runs_dir = self.root / "runs"
        self.history_dir = self.root / "history"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def create_run_dir(self, bench_run_id: str) -> Path:
        d = self.runs_dir / str(bench_run_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_summary(self, run_dir: Path, summary: BenchmarkRunSummary) -> None:
        (run_dir / "summary.json").write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def append_history(self, summary: BenchmarkRunSummary) -> None:
        line = json.dumps(summary.to_dict(), ensure_ascii=False)
        p = self.history_dir / "runs.jsonl"
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def load_last_summary(self, *, suite_id: str) -> Optional[Dict[str, Any]]:
        p = self.history_dir / "runs.jsonl"
        if not p.exists():
            return None
        last: Optional[Dict[str, Any]] = None
        for ln in p.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(ln)
            except Exception:
                continue
            if str(d.get("suite_id")) == str(suite_id):
                last = d
        return last

    @staticmethod
    def detect_regression(current: BenchmarkRunSummary, baseline: Optional[Dict[str, Any]]) -> bool:
        """아주 단순한 회귀 감지(Phase 3 minimal): pass_rate 하락이면 regression."""

        if baseline is None:
            return False
        cur = float((current.totals or {}).get("pass_rate", 0.0))
        base = float((baseline.get("totals") or {}).get("pass_rate", 0.0))
        return cur < base


class BenchmarkRunner:
    """Benchmark suite 실행기."""

    def __init__(
        self,
        *,
        project_root: Optional[Path] = None,
        suites: Optional[BenchmarkSuiteRegistry] = None,
        task_specs: Optional[TaskSpecRegistry] = None,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()

        self.suites = suites or BenchmarkSuiteRegistry(self.project_root / "config" / "llm" / "benchmark_suites.yaml")
        self.suites.compile()

        full_task_specs = self.project_root / "config" / "llm" / "task_specs.yaml"
        minimal_task_specs = self.project_root / "config" / "llm" / "task_specs_minimal.yaml"
        self.task_specs = task_specs or TaskSpecRegistry(full_task_specs if full_task_specs.exists() else minimal_task_specs)
        self.task_specs.compile()

        # LLMService는 run_suite()에서 llm_mode에 따라 생성합니다.
        self.llm: Optional[LLMService] = llm_service

        self.store = BenchmarkStore(project_root=self.project_root)
        self.gates = QualityGateEngine()

    def run_suite(self, suite_id: str, *, llm_mode: str = "auto", dry_run: bool = False) -> Tuple[str, Path, BenchmarkRunSummary]:
        """벤치마크 suite를 실행하고 (bench_run_id, run_dir, summary)를 반환합니다."""

        suite = self.suites.get_suite(suite_id)
        ref = self.suites.get_ref()

        # LLMService 준비 (project_root의 cmis.yaml 기준)
        if self.llm is None:
            cmis_yaml = self.project_root / "cmis.yaml"
            if not cmis_yaml.exists():
                raise BenchmarkError(f"cmis.yaml not found under project_root: {self.project_root}")
            cfg = CMISConfig(cmis_yaml)
            self.llm = create_llm_service(config=cfg, mode=str(llm_mode))
        assert self.llm is not None

        started = _utc_now_iso_z()
        bench_run_id = f"BENCH-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        run_dir = self.store.create_run_dir(bench_run_id)
        (run_dir / "cases").mkdir(parents=True, exist_ok=True)

        # run_store에 bench run 메타를 기록(선택)
        factory = StoreFactory(project_root=self.project_root)
        run_store = factory.run_store()
        try:
            run_store.create_run(
                {
                    "run_id": bench_run_id,
                    "started_at": started,
                    "status": "running",
                    "interface_id": "llm_benchmark",
                    "query": f"suite:{suite_id}",
                    "role_id": "benchmark",
                    "policy_id": "benchmark",
                    "run_mode": str(suite.run_mode),
                    "context": {"suite_id": suite_id, "tier": suite.tier},
                    "summary": {},
                }
            )
        except Exception:
            pass

        # LLMService에 run_store 연결 (selection/quality logs)
        try:
            self.llm.run_store = run_store
        except Exception:
            pass

        # mock deterministic: expected output가 있는 케이스는 mock responses를 주입할 수 있게 case marker를 넣습니다.
        self._prime_mock_responses(suite)

        task_results: Dict[str, Any] = {}
        total_cases = 0
        passed_cases = 0

        try:
            for task in suite.tasks:
                task_type = str(task.task_type)
                t_spec = self.task_specs.get_task_spec(task_type)
                out_fmt = str(t_spec.output_contract.format or "text")

                case_results: List[BenchmarkCaseResult] = []
                for case in task.cases:
                    total_cases += 1
                    r = self._run_case(
                        suite,
                        task_type=task_type,
                        out_format=out_fmt,
                        case=case,
                        bench_run_id=bench_run_id,
                        run_dir=run_dir,
                        dry_run=dry_run,
                    )
                    case_results.append(r)
                    if r.passed:
                        passed_cases += 1

                task_results[task_type] = {"cases": [c.to_dict() for c in case_results]}

            ended = _utc_now_iso_z()
            pass_rate = (passed_cases / total_cases) if total_cases else 1.0
            summary = BenchmarkRunSummary(
                bench_run_id=bench_run_id,
                suite_id=suite_id,
                tier=suite.tier,
                suite_digest=ref.suites_digest,
                started_at=started,
                ended_at=ended,
                status="completed",
                totals={"total_cases": total_cases, "passed_cases": passed_cases, "pass_rate": pass_rate},
                task_results=task_results,
            )

            # regression detection (history baseline)
            baseline = self.store.load_last_summary(suite_id=suite_id)
            regression = self.store.detect_regression(summary, baseline)
            if regression:
                summary.task_results["regression"] = {"detected": True, "baseline": baseline.get("bench_run_id") if baseline else None}

            self.store.write_summary(run_dir, summary)
            self.store.append_history(summary)

            try:
                run_store.finalize_run(bench_run_id, "completed", {"summary_ref": str(run_dir / "summary.json")})
            except Exception:
                pass

            return bench_run_id, run_dir, summary

        finally:
            run_store.close()

    def _prime_mock_responses(self, suite: BenchmarkSuite) -> None:
        """MockLLM을 deterministic smoke 케이스에 맞게 준비합니다(best-effort)."""

        mock_provider = None
        try:
            mock_provider = self.llm.registry.get_provider("mock")
        except Exception:
            mock_provider = None
        if mock_provider is None:
            return

        responses = getattr(mock_provider, "responses", None)
        if not isinstance(responses, dict):
            return

        for task in suite.tasks:
            for case in task.cases:
                marker = self._case_marker(case.case_id)
                if case.expected_json is not None:
                    responses[marker] = json.dumps(case.expected_json, ensure_ascii=False)
                elif case.expected_text_contains:
                    # 최소: claim 형태 문자열 생성
                    responses[marker] = "\n".join([s if s.startswith("-") else f"- {s}" for s in case.expected_text_contains])

                if suite.judge is not None and case.judge_expected_json is not None:
                    j_marker = self._judge_marker(case.case_id)
                    responses[j_marker] = json.dumps(case.judge_expected_json, ensure_ascii=False)

    @staticmethod
    def _case_marker(case_id: str) -> str:
        return f"[BENCH_CASE:{case_id}]"

    @staticmethod
    def _judge_marker(case_id: str) -> str:
        return f"[BENCH_JUDGE:{case_id}]"

    def _run_case(
        self,
        suite: BenchmarkSuite,
        *,
        task_type: str,
        out_format: str,
        case: BenchmarkCaseSpec,
        bench_run_id: str,
        run_dir: Path,
        dry_run: bool,
    ) -> BenchmarkCaseResult:
        start = datetime.now(timezone.utc)

        prompt = f"{self._case_marker(case.case_id)} {case.input_text}"
        if dry_run:
            latency_ms = 0
            passed = True
            return BenchmarkCaseResult(case_id=case.case_id, passed=passed, latency_ms=latency_ms, metrics={"dry_run": True})

        # route/managed 분기 (Phase 3 minimal)
        if suite.run_mode == "route":
            output = self._call_by_route(task_type=task_type, out_format=out_format, prompt=prompt)
        else:
            output = self._call_managed(suite, task_type=task_type, out_format=out_format, prompt=prompt, bench_run_id=bench_run_id)

        latency_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        passed, metrics = self._evaluate_case(task_type=task_type, out_format=out_format, case=case, output=output, suite=suite, bench_run_id=bench_run_id)

        # case artifact (ref-only가 아니라 benchmark용 synthetic input을 가정)
        try:
            out_payload: Any
            if isinstance(output, dict):
                out_payload = output
            else:
                out_payload = str(output)
            case_artifact = {
                "bench_run_id": bench_run_id,
                "suite_id": str(suite.suite_id),
                "tier": str(suite.tier),
                "task_type": str(task_type),
                "case_id": str(case.case_id),
                "input": str(case.input_text),
                "output": out_payload,
                "passed": bool(passed),
                "latency_ms": int(latency_ms),
                "metrics": dict(metrics or {}),
            }
            out_path = run_dir / "cases" / f"case-{task_type}-{case.case_id}.json"
            out_path.write_text(json.dumps(case_artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        return BenchmarkCaseResult(case_id=case.case_id, passed=passed, latency_ms=latency_ms, metrics=metrics)

    def _call_by_route(self, *, task_type: str, out_format: str, prompt: str) -> Any:
        tt = CMISTaskType(task_type)
        if out_format == "json":
            return self.llm.call_structured(tt, prompt, enable_quality_gates=False, enable_escalation=False, max_attempts=1)
        return self.llm.call(tt, prompt)

    def _call_managed(self, suite: BenchmarkSuite, *, task_type: str, out_format: str, prompt: str, bench_run_id: str) -> Any:
        """policy_ref 기반 managed 실행."""

        policy_ref = str(suite.policy_ref or "").strip()
        if not policy_ref:
            raise BenchmarkError("managed run_mode requires suite.policy_ref")

        tt = CMISTaskType(task_type)
        if out_format == "json":
            return self.llm.call_structured(
                tt,
                prompt,
                policy_ref=policy_ref,
                run_id=bench_run_id,
                call_intent=("extract" if suite.tier == "unit" else "draft"),
                budget_remaining_usd=float(suite.budget_remaining_usd),
                max_attempts=int(max(1, suite.max_attempts)),
                enable_quality_gates=True,
                enable_escalation=True,
            )
        return self.llm.call(
            tt,
            prompt,
            policy_ref=policy_ref,
            run_id=bench_run_id,
            call_intent=("draft" if suite.tier != "scenario" else "draft"),
            budget_remaining_usd=float(suite.budget_remaining_usd),
        )
    def _evaluate_case(
        self,
        *,
        task_type: str,
        out_format: str,
        case: BenchmarkCaseSpec,
        output: Any,
        suite: BenchmarkSuite,
        bench_run_id: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        metrics: Dict[str, Any] = {}

        # 1) expected_json (unit deterministic)
        if case.expected_json is not None:
            ok_parse = isinstance(output, dict) and (output.get("error") is None)
            metrics["json_parseable"] = bool(ok_parse)
            ok_match = True
            if ok_parse:
                for k, v in case.expected_json.items():
                    if output.get(k) != v:
                        ok_match = False
                        break
            else:
                ok_match = False
            metrics["expected_match"] = bool(ok_match)
            return (bool(ok_parse and ok_match), metrics)

        # 2) expected_text_contains (unit)
        if case.expected_text_contains:
            s = str(output)
            ok = all(str(x) in s for x in case.expected_text_contains)
            metrics["text_contains"] = bool(ok)
            return (bool(ok), metrics)

        # 3) scenario judge
        if suite.judge is not None:
            judge_out = self._run_judge(suite, case=case, task_type=task_type, output=output, bench_run_id=bench_run_id)
            metrics["judge"] = judge_out
            score = float(judge_out.get("score", 0.0)) if isinstance(judge_out, dict) else 0.0
            return (score >= 0.5, metrics)

        # 4) fallback: quality gate (if any)
        try:
            spec = self.task_specs.get_task_spec(task_type)
            report = self.gates.evaluate(task_spec=spec, output=output)
            metrics["quality_gate_passed"] = bool(report.passed)
            metrics["failure_codes"] = list(report.failure_codes or [])
            return (bool(report.passed), metrics)
        except Exception:
            metrics["quality_gate_passed"] = True
            return (True, metrics)

    def _run_judge(self, suite: BenchmarkSuite, *, case: BenchmarkCaseSpec, task_type: str, output: Any, bench_run_id: str) -> Any:
        assert suite.judge is not None
        judge_task_type = CMISTaskType(str(suite.judge.judge_task_type))
        judge_prompt = (
            f"{self._judge_marker(case.case_id)}\n"
            f"BENCH_RUN_ID: {bench_run_id}\n"
            f"TASK: {task_type}\n"
            f"INPUT:\n{case.input_text}\n\n"
            f"OUTPUT:\n{str(output)}\n\n"
            f"채점 기준: 0~1 점수로 평가 (0=실패, 1=매우 우수)\n"
        )
        # managed + judge pinning(옵션)
        if suite.run_mode == "managed" and suite.judge.judge_version_pin and suite.judge.judge_model_id:
            judge_policy_ref = str(suite.judge.judge_policy_ref or suite.policy_ref or "").strip()
            if not judge_policy_ref:
                raise BenchmarkError("judge_version_pin requires judge_policy_ref or suite.policy_ref")
            try:
                decision, _ = self.llm._select_managed(  # type: ignore[attr-defined]
                    task_type=judge_task_type,
                    policy_ref=judge_policy_ref,
                    call_intent="judge",
                    quality_target="medium",
                    confidentiality="public",
                    budget_remaining_usd=float(suite.budget_remaining_usd),
                    max_latency_ms=None,
                    attempt_index=0,
                    failure_codes=[],
                )
                if str(decision.model_id) != str(suite.judge.judge_model_id):
                    raise BenchmarkError(f"judge pin mismatch: expected {suite.judge.judge_model_id} but selected {decision.model_id}")
            except Exception as e:
                raise BenchmarkError(str(e))

        return self.llm.call_structured(
            judge_task_type,
            judge_prompt,
            enable_quality_gates=False,
            enable_escalation=False,
            max_attempts=1,
            call_intent="judge",
        )


