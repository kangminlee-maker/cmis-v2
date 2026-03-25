"""Tests for calibration module — source_reliability correction."""

from __future__ import annotations

from cmis_v2.engines.calibration import compute_calibration, calibrated_reliability


def test_compute_calibration_empty() -> None:
    """No outcomes should return zero totals."""
    cal = compute_calibration()
    assert cal["total_outcomes"] == 0


def test_calibrated_reliability_defaults() -> None:
    """Without calibration data, should return default values."""
    assert calibrated_reliability("official") == 0.8
    assert calibrated_reliability("curated") == 0.7
    assert calibrated_reliability("web") == 0.5


def test_calibrated_reliability_unknown_tier() -> None:
    """Unknown source tier should return 0.5 default."""
    r = calibrated_reliability("unknown_tier")
    assert r == 0.5
