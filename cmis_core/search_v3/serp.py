"""Search Strategy v3 SERP models (SSV3-04 base types).

ref-only 원칙:
- SearchHitRef에는 title/snippet 같은 원문을 포함하지 않습니다.
- SERP 원본(title/snippet 포함)은 ArtifactStore(ART-*)에 저장하고,
  ledger/event에는 serp_artifact_id + serp_digest + SearchHitRef만 남깁니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SearchHitRef:
    url: str
    canonical_url: str
    rank: int
    provider_id: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SerpSnapshotRef:
    provider_id: str
    serp_artifact_id: str  # ART-* (provider raw response + normalized hits)
    serp_digest: str  # sha256:... (canonicalized snapshot)
    query_request_digest: str  # sha256:... (SearchQueryRequest digest)
    retrieved_at: str  # ISO8601
    hits: List[SearchHitRef] = field(default_factory=list)
    provider_config_digest: Optional[str] = None
