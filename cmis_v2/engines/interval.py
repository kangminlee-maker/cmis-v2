"""CMIS v2 Interval — Estimation range arithmetic.

An Interval represents a P10/P90 range: the true value is expected to fall
within [lo, hi] with approximately 80% probability.  This is the primary
data type for the Estimation Engine.

Interval arithmetic follows standard rules for propagating uncertainty
through addition, subtraction, multiplication, and division.

Design decisions (8-Agent Panel Review, 2026-03-25, session 9780126d):
- lo = P10 (10th percentile), hi = P90 (90th percentile)
- NOT strict mathematical interval arithmetic (inputs are subjective)
- Supports Fermi decomposition: leaf intervals propagate to root
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Interval:
    """A P10/P90 estimation range.

    lo: lower bound (P10 — 10% chance the true value is below this)
    hi: upper bound (P90 — 10% chance the true value is above this)
    """

    lo: float
    hi: float

    def __post_init__(self) -> None:
        if self.lo > self.hi:
            object.__setattr__(self, "lo", min(self.lo, self.hi))
            object.__setattr__(self, "hi", max(self.lo, self.hi))

    # -- Derived properties --

    @property
    def midpoint(self) -> float:
        """Central estimate (arithmetic mean of lo and hi)."""
        return (self.lo + self.hi) / 2

    @property
    def width(self) -> float:
        """Absolute width of the interval."""
        return self.hi - self.lo

    @property
    def spread_ratio(self) -> float:
        """Relative uncertainty: width / |midpoint|.

        Lower is more precise. Returns float('inf') if midpoint is 0.
        """
        mid = self.midpoint
        if mid == 0:
            return float("inf")
        return self.width / abs(mid)

    # -- Arithmetic operators (interval arithmetic) --

    def __add__(self, other: Interval) -> Interval:
        return Interval(self.lo + other.lo, self.hi + other.hi)

    def __sub__(self, other: Interval) -> Interval:
        return Interval(self.lo - other.hi, self.hi - other.lo)

    def __mul__(self, other: Interval) -> Interval:
        products = [
            self.lo * other.lo,
            self.lo * other.hi,
            self.hi * other.lo,
            self.hi * other.hi,
        ]
        return Interval(min(products), max(products))

    def __truediv__(self, other: Interval) -> Interval:
        if other.lo <= 0 <= other.hi:
            raise ZeroDivisionError(
                f"Cannot divide by interval containing zero: {other}"
            )
        reciprocal = Interval(1 / other.hi, 1 / other.lo)
        return self * reciprocal

    # -- Scalar operations --

    def scale(self, factor: float) -> Interval:
        """Multiply both bounds by a scalar."""
        if factor >= 0:
            return Interval(self.lo * factor, self.hi * factor)
        return Interval(self.hi * factor, self.lo * factor)

    # -- Combination operations --

    def overlaps(self, other: Interval) -> bool:
        """Return True if the two intervals share any common range."""
        return self.lo <= other.hi and other.lo <= self.hi

    def intersect(self, other: Interval) -> Interval | None:
        """Return the overlapping region, or None if disjoint."""
        if not self.overlaps(other):
            return None
        return Interval(max(self.lo, other.lo), min(self.hi, other.hi))

    def convex_hull(self, other: Interval) -> Interval:
        """Return the smallest interval containing both.

        Called 'convex hull' rather than 'union' because when intervals
        are disjoint, the gap between them is included.
        """
        return Interval(min(self.lo, other.lo), max(self.hi, other.hi))

    def clamp(self, bound_lo: float, bound_hi: float) -> Interval:
        """Restrict interval to within [bound_lo, bound_hi]."""
        return Interval(
            max(self.lo, bound_lo),
            min(self.hi, bound_hi),
        )

    # -- Distribution conversion (Phase 4 bridge) --

    def to_uniform_samples(self, n: int = 1000) -> list[float]:
        """Generate uniform random samples from this interval.

        Entry point for Monte Carlo simulation. When richer distributions
        are needed (Phase 4), replace this with distribution-aware sampling.
        """
        import random
        return [random.uniform(self.lo, self.hi) for _ in range(n)]

    # -- Serialization --

    def to_dict(self) -> dict[str, float]:
        return {"lo": self.lo, "hi": self.hi, "midpoint": self.midpoint}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Interval:
        return cls(lo=float(d["lo"]), hi=float(d["hi"]))

    @classmethod
    def from_point(cls, value: float, spread: float = 0.2) -> Interval:
        """Create an interval from a point estimate with relative spread.

        spread=0.2 means +-20% around the value.
        """
        half = abs(value) * spread
        return cls(lo=value - half, hi=value + half)
