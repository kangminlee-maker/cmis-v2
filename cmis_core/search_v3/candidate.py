"""Search Strategy v3 candidate models (SSV3-06).

ref-only:
- CandidateValue는 원문/인용 텍스트를 직접 포함하지 않습니다.
- 인용은 ArtifactStore(ART)로 저장하고 span_quote_ref로만 참조합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urlsplit


@dataclass(frozen=True)
class SearchRequest:
    """v3 search request의 최소 단위(추출 단계에 필요한 필드만)."""

    metric_id: str
    expected_unit: Optional[str] = None
    as_of: Optional[str] = None
    min_high_quality_evidence: int = 2
    min_independent_sources: int = 2


@dataclass(frozen=True)
class CandidateValue:
    metric_id: str
    value: float
    unit: str
    as_of: Optional[str]
    independence_key: str
    span_quote_ref: Optional[Dict[str, str]]  # {"artifact_id":"ART-*","digest":"sha256:..."}
    provenance: Dict[str, Any]
    confidence: float
    notes: Dict[str, Any] = field(default_factory=dict)


def compute_independence_key(*, canonical_url: str, content_digest: str) -> str:
    """v1 independence_key = host + content_digest."""

    host = (urlsplit(str(canonical_url or "")).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    host = host or "unknown"
    return f"host:{host}|{str(content_digest)}"
