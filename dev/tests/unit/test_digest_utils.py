"""BF-01 deterministic digest utilities unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from cmis_core.digest import canonical_digest, canonical_json


def test_canonical_json_sorts_keys_and_is_compact() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonical_digest_stable_for_key_order() -> None:
    assert canonical_digest({"b": 1, "a": 2}) == canonical_digest({"a": 2, "b": 1})


def test_canonical_json_integer_float_normalized_to_int() -> None:
    assert canonical_json({"a": 1.0}) == canonical_json({"a": 1})


def test_canonical_json_preserves_list_order() -> None:
    assert canonical_json([1, 2]) != canonical_json([2, 1])


def test_canonical_json_rejects_non_finite_floats() -> None:
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})
    with pytest.raises(ValueError):
        canonical_json({"x": float("inf")})


def test_canonical_json_datetime_utc_uses_z_notation() -> None:
    dt = datetime(2025, 12, 13, 0, 0, 0, tzinfo=timezone.utc)
    assert canonical_json({"t": dt}) == '{"t":"2025-12-13T00:00:00Z"}'


def test_canonical_json_decimal_is_string() -> None:
    assert canonical_json({"d": Decimal("1.0")}) == '{"d":"1.0"}'


def test_canonical_json_rejects_non_string_dict_keys() -> None:
    with pytest.raises(TypeError):
        canonical_json({1: "x"})  # type: ignore[arg-type]
