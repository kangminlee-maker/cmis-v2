"""Search Strategy v3 query request + query artifact (SSV3-03).

핵심 규칙(Production-minimal v1):
- 실행된 모든 query는 항상 query_artifact_id(ART-*)로 저장합니다. (LLM/비LLM 분기 없음)
- request_digest는 query 내용/파라미터에 대해 결정적으로 계산합니다.
- digest 계산에는 query_artifact_id 같은 런타임 생성 ID를 포함하지 않습니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from cmis_core.digest import canonical_digest
from cmis_core.stores.artifact_store import ArtifactStore


@dataclass(frozen=True)
class SearchQueryRequest:
    """Provider에 전달되는 검색 요청.

    NOTE:
    - 런타임에서는 query 문자열이 필요하지만,
      ledger/event에는 query_text를 직접 저장하지 않고 artifact/ref로만 저장합니다.
    """

    provider_id: str
    query: str
    language: str
    region: str
    top_k: int
    timeout_sec: int
    filters: Dict[str, Any] = field(default_factory=dict)  # recency_days, allow/deny domains, safe_search...
    query_artifact_id: Optional[str] = None  # ART-* (query text + generator meta)
    request_digest: str = ""  # sha256:... (canonicalized request, without artifact id)


def compute_query_request_digest(req: SearchQueryRequest) -> str:
    """query request digest를 결정적으로 계산합니다.

    주의:
    - query_artifact_id / request_digest 같은 런타임 생성 필드는 digest에 포함하지 않습니다.
    """

    payload = {
        "provider_id": req.provider_id,
        "query": req.query,
        "language": req.language,
        "region": req.region,
        "top_k": int(req.top_k),
        "timeout_sec": int(req.timeout_sec),
        "filters": dict(req.filters or {}),
    }
    return canonical_digest(payload)


def persist_query_artifact(
    store: ArtifactStore,
    *,
    provider_id: str,
    query: str,
    language: str,
    region: str,
    generator_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """query 텍스트를 ART로 저장하고 artifact_id를 반환합니다."""

    payload = {
        "provider_id": str(provider_id),
        "query": str(query),
        "language": str(language),
        "region": str(region),
        "generator": dict(generator_meta or {}),
    }
    return store.put_json(payload, kind="search_v3_query")


def finalize_query_request(
    store: ArtifactStore,
    req: SearchQueryRequest,
    *,
    generator_meta: Optional[Dict[str, Any]] = None,
) -> SearchQueryRequest:
    """SearchQueryRequest를 '실행 직전' 형태로 확정합니다.

    - query_artifact_id: 항상 생성
    - request_digest: 결정적으로 계산
    """

    query_artifact_id = persist_query_artifact(
        store,
        provider_id=req.provider_id,
        query=req.query,
        language=req.language,
        region=req.region,
        generator_meta=generator_meta,
    )
    digest = compute_query_request_digest(req)

    return SearchQueryRequest(
        provider_id=req.provider_id,
        query=req.query,
        language=req.language,
        region=req.region,
        top_k=req.top_k,
        timeout_sec=req.timeout_sec,
        filters=dict(req.filters or {}),
        query_artifact_id=query_artifact_id,
        request_digest=digest,
    )
