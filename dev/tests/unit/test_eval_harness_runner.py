"""Eval harness runner unit tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from cmis_core.eval_harness import EvalHarnessRunner


def test_eval_harness_runner_smoke(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    suite_path = tmp_path / "regression_suite.yaml"
    suite_doc = {
        "schema_version": 1,
        "description": "test suite",
        "regression_suite": {
            "defaults": {
                "interface_id": "eval_harness",
                "policy_id": "exploration_friendly",
                "budgets": {"max_iterations": 5, "max_time_sec": 30},
                "thresholds": {
                    "require_success": True,
                    "max_avg_prior_ratio": 1.0,
                    "max_policy_failure_rate": 1.0,
                    "min_evidence_hit_rate": 0.0,
                },
            },
            "tests": [
                {
                    "id": "smoke",
                    "query": "한국 어학 시장 분석",
                    "context": {"domain_id": "Adult_Language_Education_KR", "region": "KR"},
                }
            ],
        },
    }

    suite_path.write_text(yaml.safe_dump(suite_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    runner = EvalHarnessRunner(
        project_root=project_root,
        suite_path=suite_path,
        enable_stub_source=True,
    )

    result = runner.run()

    assert result.status == "success"
    assert len(result.tests) == 1
    assert result.tests[0].passed is True
