"""semantic_key generator (BF-05a).

semantic_key는 CUB digest의 결정성 축입니다.

원칙:
- 사람이 읽을 수 있고, 충돌 가능성이 낮아야 함
- 안정 키(datum_type/entity/time)를 우선으로 구성
- 추가 요소(extra)는 key 정렬로 결정성을 확보
"""

from __future__ import annotations

from typing import Dict, Optional


def make(
    *,
    datum_type: str,
    entity: str,
    name: Optional[str] = None,
    period: Optional[str] = None,
    as_of: Optional[str] = None,
    extra: Optional[Dict[str, str]] = None,
) -> str:
    """semantic_key를 생성합니다.

    Args:
        datum_type: table|timeseries|statement|kv|model 등
        entity: 대상 엔티티(예: financial_statement, crm_metrics, baseline_state 등)
        name: statement_type/table_name 등 추가 구분자
        period: 기간(예: 2024FY, 2025Q3)
        as_of: 기준 시점(예: 2025-12-13)
        extra: 추가 key-value(정렬되어 반영됨)

    Notes:
        - period와 as_of는 동시에 주지 않는 것을 권장합니다.
    """

    dt = str(datum_type).strip()
    ent = str(entity).strip()
    if not dt:
        raise ValueError("datum_type is required")
    if not ent:
        raise ValueError("entity is required")
    if period and as_of:
        raise ValueError("period and as_of cannot be set together")

    parts = [dt, ent]
    if name:
        parts.append(str(name).strip())
    if period:
        parts.append(str(period).strip())
    if as_of:
        parts.append(f"as_of={str(as_of).strip()}")

    if extra:
        for k in sorted(extra.keys()):
            parts.append(f"{k}={extra[k]}")

    return ":".join([p for p in parts if p])
