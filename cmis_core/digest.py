"""Deterministic hashing utilities (BF-01).

Brownfield MVP에서 digest는 "재현성/중복 제거(idempotent)/검증(verify)"의 핵심입니다.

이 모듈은 다음 계약을 지원합니다.
- canonical_json: 객체를 결정적으로 직렬화(JSON)
- canonical_digest: canonical_json의 sha256 digest

주의:
- list의 정렬은 자동으로 하지 않습니다. (순서 의미 유무는 caller가 책임)
- NaN/Infinity float은 허용하지 않습니다(결정성/이식성 문제).
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import json
import math
import hashlib
from pathlib import Path
from typing import Any, Dict, List


def sha256_hexdigest(data: bytes) -> str:
    """sha256 hex digest를 반환합니다(접두사 없음)."""

    return hashlib.sha256(bytes(data)).hexdigest()


def sha256_digest(data: bytes) -> str:
    """sha256 digest를 반환합니다(접두사 포함)."""

    return f"sha256:{sha256_hexdigest(data)}"


def canonical_json(obj: Any) -> str:
    """결정적(canonical) JSON 문자열을 반환합니다.

    Rules:
    - dict key: str만 허용하며, sort_keys=True로 정렬
    - list/tuple: 순서 유지(정렬하지 않음)
    - float: finite만 허용, 정수형 float(예: 1.0)은 int로 정규화
    - datetime: timezone-aware이면 UTC ISO8601(Z)로 정규화, naive면 isoformat 그대로 사용
    - Decimal: 고정 소수점 문자열로 변환
    """

    canonical_obj = _to_canonical_obj(obj)
    return json.dumps(
        canonical_obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_digest(obj: Any) -> str:
    """canonical_json(obj)의 sha256 digest를 반환합니다."""

    return sha256_digest(canonical_json(obj).encode("utf-8"))


def _to_canonical_obj(obj: Any) -> Any:
    # None/bool/int/str
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj

    # float: finite only + integer-float normalization
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("Non-finite float (NaN/Infinity) is not allowed in canonical_json()")
        if obj.is_integer():
            return int(obj)
        return obj

    # Decimal: preserve numeric meaning without float conversion
    if isinstance(obj, Decimal):
        # format(d, "f") is deterministic for Decimal
        return format(obj, "f")

    # datetime/date
    if isinstance(obj, datetime):
        if obj.tzinfo is not None:
            dt = obj.astimezone(timezone.utc)
            # Z-notation for UTC
            return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()

    # Path
    if isinstance(obj, Path):
        return str(obj)

    # Enum
    if isinstance(obj, Enum):
        return _to_canonical_obj(obj.value)

    # dataclass
    if is_dataclass(obj):
        return _to_canonical_obj(asdict(obj))

    # dict
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"Non-string dict key is not allowed in canonical_json(): {type(k).__name__}")
            out[k] = _to_canonical_obj(v)
        return out

    # list/tuple
    if isinstance(obj, (list, tuple)):
        return [_to_canonical_obj(v) for v in obj]

    # bytes: reject by default to avoid accidental raw leakage into digest inputs
    if isinstance(obj, (bytes, bytearray, memoryview)):
        raise TypeError("bytes-like object is not allowed in canonical_json(); store it as ART-* and reference it")

    raise TypeError(f"Unsupported type for canonical_json(): {type(obj).__name__}")
