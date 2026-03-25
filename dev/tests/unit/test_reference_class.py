"""Tests for reference_class module — Reference Class Forecasting."""

from __future__ import annotations

from cmis_v2.engines.reference_class import build_reference_class, suggest_estimate


def test_build_reference_class_empty() -> None:
    """No outcomes should return insufficient."""
    rc = build_reference_class("MET-TAM")
    assert rc["outcome_count"] == 0
    assert rc["sufficient"] is False
    assert rc["statistics"] is None


def test_suggest_estimate_insufficient() -> None:
    """Fewer than 3 outcomes should return insufficient."""
    s = suggest_estimate("MET-TAM")
    assert s["sufficient"] is False
    assert "reason" in s
