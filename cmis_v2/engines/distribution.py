"""CMIS v2 Distribution — Probability distribution fitting and sampling.

Fits P10/P90 intervals to parametric distributions (beta, lognormal, uniform)
for Monte Carlo simulation. Replaces naive uniform sampling with
distribution-aware sampling when shape information is available.

Design decisions:
- No scipy dependency: uses only Python stdlib (math, random, dataclasses)
- Beta fitting: nested search (alpha outer loop + beta bisection inner loop)
- Lognormal fitting: closed-form from z-score inversion
- Convergence failure or edge cases → automatic Uniform fallback
- sample() lives here (not interval.py) to prevent circular dependency
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from cmis_v2.engines.interval import Interval


# -- Constants --

_Z_090: float = 1.2816
"""Standard normal z-score for the 90th percentile."""

_BETA_MAX_ITER: int = 100
"""Maximum iterations for beta parameter search."""

_BETA_SAMPLE_SIZE: int = 5000
"""Sample size for beta CDF approximation."""

_NARROW_THRESHOLD: float = 1e-9
"""Intervals narrower than this skip fitting (early exit)."""


# -- Distribution dataclass --

@dataclass(frozen=True)
class Distribution:
    """A fitted probability distribution backed by an Interval.

    kind: distribution family — "beta", "lognormal", "uniform"
    params: distribution-specific parameters (JSON-serializable)
    interval: the original P10/P90 interval this was fitted from
    """

    kind: str
    params: dict[str, float]
    interval: Interval

    def samples(self, n: int = 1000) -> list[float]:
        """Draw n random samples from this distribution."""
        return _draw_samples(self, n)

    def percentile(self, p: float) -> float:
        """Estimate the p-th percentile (0.0–1.0) via sampling."""
        drawn = sorted(self.samples(n=_BETA_SAMPLE_SIZE))
        idx = int(p * len(drawn))
        idx = max(0, min(idx, len(drawn) - 1))
        return drawn[idx]

    def mode(self) -> float:
        """Return the distribution mode (most likely value)."""
        return _compute_mode(self)

    def mean(self) -> float:
        """Return the distribution mean."""
        return _compute_mean(self)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "kind": self.kind,
            "params": dict(self.params),
            "interval": self.interval.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Distribution:
        """Deserialize from a dict produced by to_dict()."""
        return cls(
            kind=str(d["kind"]),
            params={k: float(v) for k, v in d["params"].items()},
            interval=Interval.from_dict(d["interval"]),
        )


# -- Public API --

def sample(
    interval: Interval,
    n: int = 1000,
    distribution: Distribution | None = None,
) -> list[float]:
    """Sample from an interval, optionally using a fitted distribution.

    If distribution is provided, draws from that distribution.
    Otherwise, falls back to uniform sampling over [lo, hi].
    """
    if distribution is not None:
        return distribution.samples(n)
    return [random.uniform(interval.lo, interval.hi) for _ in range(n)]


def fit_distribution(
    interval: Interval,
    kind: str = "uniform",
    bounds: dict[str, float] | None = None,
) -> Distribution:
    """Fit a named distribution family to an interval."""
    if interval.width < _NARROW_THRESHOLD:
        return _make_uniform(interval)

    if kind == "beta":
        return _fit_beta(interval, bounds)
    if kind == "lognormal":
        return _fit_lognormal(interval)
    return _make_uniform(interval)


def infer_distribution(
    interval: Interval,
    unit: str = "",
    bounds: dict[str, float] | None = None,
) -> Distribution:
    """Auto-select and fit a distribution based on unit and bounds.

    Mapping rules:
    - ratio + bounds [0,1] → beta
    - currency, count (unbounded) → lognormal
    - percentage + bounds → beta (shifted)
    - index + bounds → beta (scaled)
    - default → uniform
    """
    kind = _infer_kind(unit, bounds)
    return fit_distribution(interval, kind=kind, bounds=bounds)


# -- Inference logic --

def _infer_kind(unit: str, bounds: dict[str, float] | None) -> str:
    """Determine the best distribution family from unit and bounds."""
    unit_lower = unit.lower().strip()
    is_bounded_01 = (
        bounds is not None
        and bounds.get("min", bounds.get("lo", -math.inf)) >= 0
        and bounds.get("max", bounds.get("hi", math.inf)) <= 1
    )

    if unit_lower == "ratio" and is_bounded_01:
        return "beta"
    if unit_lower == "percentage" and bounds is not None:
        return "beta"
    if unit_lower == "index" and bounds is not None:
        return "beta"
    if unit_lower in ("currency", "count"):
        return "lognormal"
    return "uniform"


# -- Uniform --

def _make_uniform(interval: Interval) -> Distribution:
    """Create a uniform distribution over the interval."""
    return Distribution(
        kind="uniform",
        params={"lo": interval.lo, "hi": interval.hi},
        interval=interval,
    )


# -- Beta fitting --

def _fit_beta(
    interval: Interval,
    bounds: dict[str, float] | None = None,
) -> Distribution:
    """Fit beta distribution to P10/P90 by nested search.

    Maps [lo, hi] into [0, 1] using bounds (default: interval edges).
    Searches alpha in outer loop, bisects beta in inner loop to match
    the P10/P90 targets.
    """
    bound_lo = bounds.get("min", bounds.get("lo", 0.0)) if bounds else 0.0
    bound_hi = bounds.get("max", bounds.get("hi", 1.0)) if bounds else 1.0
    span = bound_hi - bound_lo
    if span <= 0:
        return _make_uniform(interval)

    target_p10 = (interval.lo - bound_lo) / span
    target_p90 = (interval.hi - bound_lo) / span
    target_p10 = max(0.01, min(target_p10, 0.99))
    target_p90 = max(0.01, min(target_p90, 0.99))

    if target_p90 - target_p10 < 1e-6:
        return _make_uniform(interval)

    result = _search_beta_params(target_p10, target_p90)
    if result is None:
        return _make_uniform(interval)

    alpha, beta_param = result
    return Distribution(
        kind="beta",
        params={
            "alpha": alpha,
            "beta": beta_param,
            "bound_lo": bound_lo,
            "bound_hi": bound_hi,
        },
        interval=interval,
    )


def _search_beta_params(
    target_p10: float,
    target_p90: float,
) -> tuple[float, float] | None:
    """Find (alpha, beta) such that sample P10 ~ target_p10, P90 ~ target_p90.

    Outer loop: sweep alpha from 0.5 to 20.
    Inner loop: bisect beta to minimize P10/P90 error.
    Returns None if no acceptable fit is found.
    """
    best_error = float("inf")
    best_pair: tuple[float, float] | None = None
    tolerance = 0.02

    for i in range(40):
        alpha = 0.5 + i * 0.5
        found = _bisect_beta_for_alpha(alpha, target_p10, target_p90)
        if found is None:
            continue
        beta_val, error = found
        if error < best_error:
            best_error = error
            best_pair = (alpha, beta_val)
        if best_error < tolerance:
            break

    if best_pair is None or best_error > 0.1:
        return None
    return best_pair


def _bisect_beta_for_alpha(
    alpha: float,
    target_p10: float,
    target_p90: float,
) -> tuple[float, float] | None:
    """Bisect beta parameter for a fixed alpha to match P10/P90 targets."""
    lo_b, hi_b = 0.3, 50.0
    best_beta = lo_b
    best_err = float("inf")

    for _ in range(_BETA_MAX_ITER):
        mid_b = (lo_b + hi_b) / 2
        p10_hat, p90_hat = _beta_percentiles(alpha, mid_b)
        err = abs(p10_hat - target_p10) + abs(p90_hat - target_p90)

        if err < best_err:
            best_err = err
            best_beta = mid_b

        if hi_b - lo_b < 0.001:
            break

        # Steer bisection: if spread is too wide, increase beta
        spread_hat = p90_hat - p10_hat
        spread_target = target_p90 - target_p10
        if spread_hat > spread_target:
            lo_b = mid_b
        else:
            hi_b = mid_b

    return (best_beta, best_err)


def _beta_percentiles(alpha: float, beta: float) -> tuple[float, float]:
    """Estimate P10 and P90 of Beta(alpha, beta) via sorted samples."""
    drawn = sorted(
        random.betavariate(alpha, beta) for _ in range(_BETA_SAMPLE_SIZE)
    )
    idx_10 = int(0.10 * len(drawn))
    idx_90 = int(0.90 * len(drawn))
    return drawn[idx_10], drawn[idx_90]


# -- Lognormal fitting --

def _fit_lognormal(interval: Interval) -> Distribution:
    """Fit lognormal distribution from P10/P90 (closed-form).

    Falls back to uniform if lo <= 0 (shifted lognormal is complex).
    """
    if interval.lo <= 0:
        return _make_uniform(interval)

    log_lo = math.log(interval.lo)
    log_hi = math.log(interval.hi)
    mu = (log_lo + log_hi) / 2
    sigma = (log_hi - log_lo) / (2 * _Z_090)

    if sigma <= 0:
        return _make_uniform(interval)

    return Distribution(
        kind="lognormal",
        params={"mu": mu, "sigma": sigma},
        interval=interval,
    )


# -- Sampling dispatch --

def _draw_samples(dist: Distribution, n: int) -> list[float]:
    """Draw n samples from a Distribution."""
    if dist.kind == "uniform":
        lo = dist.params["lo"]
        hi = dist.params["hi"]
        return [random.uniform(lo, hi) for _ in range(n)]

    if dist.kind == "beta":
        return _draw_beta_samples(dist, n)

    if dist.kind == "lognormal":
        mu = dist.params["mu"]
        sigma = dist.params["sigma"]
        return [random.lognormvariate(mu, sigma) for _ in range(n)]

    # Unknown kind — fall back to uniform over interval
    return [
        random.uniform(dist.interval.lo, dist.interval.hi)
        for _ in range(n)
    ]


def _draw_beta_samples(dist: Distribution, n: int) -> list[float]:
    """Draw beta samples and rescale to [bound_lo, bound_hi]."""
    alpha = dist.params["alpha"]
    beta_param = dist.params["beta"]
    bound_lo = dist.params.get("bound_lo", 0.0)
    bound_hi = dist.params.get("bound_hi", 1.0)
    span = bound_hi - bound_lo
    return [
        bound_lo + random.betavariate(alpha, beta_param) * span
        for _ in range(n)
    ]


# -- Mode and mean --

def _compute_mode(dist: Distribution) -> float:
    """Compute the mode of a distribution."""
    if dist.kind == "uniform":
        return (dist.params["lo"] + dist.params["hi"]) / 2

    if dist.kind == "beta":
        alpha = dist.params["alpha"]
        beta_param = dist.params["beta"]
        bound_lo = dist.params.get("bound_lo", 0.0)
        bound_hi = dist.params.get("bound_hi", 1.0)
        if alpha > 1 and beta_param > 1:
            raw_mode = (alpha - 1) / (alpha + beta_param - 2)
        else:
            raw_mode = 0.5
        return bound_lo + raw_mode * (bound_hi - bound_lo)

    if dist.kind == "lognormal":
        mu = dist.params["mu"]
        sigma = dist.params["sigma"]
        return math.exp(mu - sigma ** 2)

    return dist.interval.midpoint


def _compute_mean(dist: Distribution) -> float:
    """Compute the mean of a distribution."""
    if dist.kind == "uniform":
        return (dist.params["lo"] + dist.params["hi"]) / 2

    if dist.kind == "beta":
        alpha = dist.params["alpha"]
        beta_param = dist.params["beta"]
        bound_lo = dist.params.get("bound_lo", 0.0)
        bound_hi = dist.params.get("bound_hi", 1.0)
        raw_mean = alpha / (alpha + beta_param)
        return bound_lo + raw_mean * (bound_hi - bound_lo)

    if dist.kind == "lognormal":
        mu = dist.params["mu"]
        sigma = dist.params["sigma"]
        return math.exp(mu + sigma ** 2 / 2)

    return dist.interval.midpoint
