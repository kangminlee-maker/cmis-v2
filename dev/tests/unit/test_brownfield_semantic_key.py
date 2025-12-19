"""BF-05a: semantic_key tests."""

from __future__ import annotations

import pytest

from cmis_core.brownfield.semantic_key import make


def test_semantic_key_basic() -> None:
    assert (
        make(datum_type="statement", entity="financial_statement", name="income_statement", period="2024FY")
        == "statement:financial_statement:income_statement:2024FY"
    )


def test_semantic_key_extra_is_sorted() -> None:
    assert (
        make(datum_type="table", entity="crm", name="customers", as_of="2025-12-13", extra={"b": "2", "a": "1"})
        == "table:crm:customers:as_of=2025-12-13:a=1:b=2"
    )


def test_semantic_key_rejects_period_and_as_of_together() -> None:
    with pytest.raises(ValueError):
        make(datum_type="kv", entity="baseline", period="2024FY", as_of="2025-12-13")
