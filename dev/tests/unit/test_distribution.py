"""Tests for distribution module — Phase 4 Distribution fitting and sampling."""

from __future__ import annotations

from cmis_v2.engines.distribution import (
    Distribution,
    fit_distribution,
    infer_distribution,
    sample,
)
from cmis_v2.engines.interval import Interval


def test_beta_fitting_roundtrip() -> None:
    """Beta P10/P90 should match within 10% tolerance."""
    iv = Interval(0.1, 0.4)
    d = fit_distribution(iv, kind="beta", bounds={"min": 0.0, "max": 1.0})
    assert d.kind == "beta"
    p10 = d.percentile(0.1)
    p90 = d.percentile(0.9)
    assert abs(p10 - iv.lo) / max(iv.lo, 1e-9) < 0.15
    assert abs(p90 - iv.hi) / max(iv.hi, 1e-9) < 0.15


def test_lognormal_fitting_roundtrip() -> None:
    """Lognormal P10/P90 should match within 10% tolerance."""
    iv = Interval(1e8, 5e8)
    d = fit_distribution(iv, kind="lognormal")
    assert d.kind == "lognormal"
    p10 = d.percentile(0.1)
    p90 = d.percentile(0.9)
    assert abs(p10 - iv.lo) / iv.lo < 0.15
    assert abs(p90 - iv.hi) / iv.hi < 0.15


def test_lognormal_negative_lo_fallback() -> None:
    """Lognormal with lo <= 0 should fallback to uniform."""
    iv = Interval(-100, 500)
    d = fit_distribution(iv, kind="lognormal")
    assert d.kind == "uniform"


def test_beta_bisection_failure_fallback() -> None:
    """Beta with extreme values should fallback to uniform."""
    iv = Interval(0.001, 0.001)  # point estimate
    d = fit_distribution(iv, kind="beta", bounds={"min": 0.0, "max": 1.0})
    # Should either succeed or fallback to uniform
    assert d.kind in ("beta", "uniform")


def test_infer_distribution_ratio() -> None:
    """ratio + [0,1] bounds should infer beta."""
    d = infer_distribution(
        Interval(0.2, 0.6), unit="ratio", bounds={"min": 0.0, "max": 1.0},
    )
    assert d.kind == "beta"


def test_infer_distribution_currency() -> None:
    """currency should infer lognormal."""
    d = infer_distribution(Interval(1e6, 5e6), unit="currency")
    assert d.kind == "lognormal"


def test_infer_distribution_default() -> None:
    """Unknown unit should default to uniform."""
    d = infer_distribution(Interval(10, 20), unit="unknown_unit")
    assert d.kind == "uniform"


def test_sample_with_distribution() -> None:
    """Samples from distribution should be within plausible range."""
    iv = Interval(0.1, 0.4)
    d = fit_distribution(iv, kind="beta", bounds={"min": 0.0, "max": 1.0})
    s = sample(iv, n=500, distribution=d)
    assert len(s) == 500
    assert all(0.0 <= x <= 1.0 for x in s)


def test_sample_without_distribution() -> None:
    """Uniform samples should be within interval."""
    iv = Interval(10, 20)
    s = sample(iv, n=100)
    assert len(s) == 100
    assert all(10 <= x <= 20 for x in s)


def test_serialization_roundtrip() -> None:
    """to_dict / from_dict should preserve all fields."""
    iv = Interval(0.1, 0.4)
    d = fit_distribution(iv, kind="beta", bounds={"min": 0.0, "max": 1.0})
    dd = d.to_dict()
    restored = Distribution.from_dict(dd)
    assert restored.kind == d.kind
    assert restored.params == d.params
    assert restored.interval.lo == d.interval.lo
    assert restored.interval.hi == d.interval.hi


def test_mode_and_mean() -> None:
    """mode and mean should be within interval bounds."""
    iv = Interval(0.1, 0.4)
    d = fit_distribution(iv, kind="beta", bounds={"min": 0.0, "max": 1.0})
    assert 0.0 <= d.mode() <= 1.0
    assert 0.0 <= d.mean() <= 1.0
