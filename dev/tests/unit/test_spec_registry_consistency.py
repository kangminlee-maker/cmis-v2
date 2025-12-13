"""Spec/Registry Consistency Unit Tests

스펙(cmis.yaml/modules/registries)과 구현(코드/파일 경로)의 정합성을 최소 단위로 검증합니다.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

from cmis_core.config import CMISConfig
from cmis_core.pattern_library import PatternLibrary


def test_metrics_spec_loaded_from_external_file():
    """CMISConfig가 외부 metrics_spec.yaml에서 metric/metric_sets를 로드한다."""
    config = CMISConfig()

    metric = config.get_metric_spec("MET-Revenue")
    assert metric is not None
    assert metric.metric_id == "MET-Revenue"

    metric_set = config.get_metric_set("structure_core_economics")
    assert "MET-Revenue" in metric_set


def test_pattern_library_default_dir_loads_patterns():
    """PatternLibrary 기본 경로가 libraries/patterns/로 설정되어 로딩 가능해야 한다."""
    lib = PatternLibrary()
    lib.load_all()

    patterns = lib.get_all()
    assert len(patterns) > 0


def test_config_validate_registry_passes():
    """config-validate --check-registry가 PASS를 출력해야 한다."""
    repo_root = Path(__file__).resolve().parents[3]

    proc = subprocess.run(
        [
            "python3",
            "-m",
            "cmis_cli",
            "config-validate",
            "--check-registry",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    assert proc.returncode == 0, stderr
    assert "Overall: PASS" in stdout

