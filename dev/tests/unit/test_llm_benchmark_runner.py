"""LLM BenchmarkRunner unit tests (Phase 3)."""

from __future__ import annotations

from pathlib import Path

import yaml

from cmis_core.llm.benchmark import BenchmarkRunner, BenchmarkSuiteRegistry


def test_benchmark_suite_registry_digest_is_deterministic(tmp_path: Path) -> None:
    suites = tmp_path / "benchmark_suites.yaml"
    suites.write_text(
        """---
schema_version: 1
benchmark_suites:
  s1:
    tier: "unit"
    run_mode: "route"
    tasks:
      - task_type: "evidence_number_extraction"
        cases:
          - id: "c1"
            input: "x"
            expected_json: { value: 1 }
""",
        encoding="utf-8",
    )

    r1 = BenchmarkSuiteRegistry(suites)
    r1.compile()
    d1 = r1.get_ref().suites_digest

    r2 = BenchmarkSuiteRegistry(suites)
    r2.compile()
    d2 = r2.get_ref().suites_digest

    assert d1 == d2


def test_benchmark_runner_writes_run_artifacts(tmp_path: Path, monkeypatch) -> None:
    # isolate storage
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    project_root = tmp_path / "proj"
    (project_root / "config" / "llm").mkdir(parents=True, exist_ok=True)

    # minimal cmis.yaml for CMISConfig (LLM runtime only)
    (project_root / "cmis.yaml").write_text(
        """---
cmis:
  planes:
    cognition_plane:
      llm_runtime:
        providers:
          - id: "mock"
""",
        encoding="utf-8",
    )

    # minimal task specs (json)
    (project_root / "config" / "llm" / "task_specs_minimal.yaml").write_text(
        """---
schema_version: 1
registry_version: "t"
tasks:
  evidence_number_extraction:
    required_capabilities:
      supports_json_mode: true
    output_contract:
      format: "json"
    quality_gates:
      - gate_id: "json_parseable"
  _default:
    required_capabilities: {}
    output_contract:
      format: "text"
    quality_gates: []
""",
        encoding="utf-8",
    )

    # minimal benchmark suites
    suites = project_root / "config" / "llm" / "benchmark_suites.yaml"
    suites.write_text(
        """---
schema_version: 1
benchmark_suites:
  smoke:
    tier: "unit"
    run_mode: "route"
    tasks:
      - task_type: "evidence_number_extraction"
        cases:
          - id: "c1"
            input: "extract number"
            expected_json: { value: 1 }
""",
        encoding="utf-8",
    )

    runner = BenchmarkRunner(project_root=project_root)
    bench_id, run_dir, summary = runner.run_suite("smoke", llm_mode="mock")

    assert bench_id.startswith("BENCH-")
    assert run_dir.exists()
    assert (run_dir / "summary.json").exists()
    assert summary.status == "completed"
    assert float(summary.totals.get("pass_rate", 0.0)) == 1.0

    # validate summary.json is JSON
    data = yaml.safe_load((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)


