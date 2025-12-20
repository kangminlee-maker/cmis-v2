"""GenericWebSearch provider abstraction (SSV3-04).

Production-minimal v1:
- adapter: google_cse (Google Custom Search)
- caching: in-memory TTL cache (provider instance scope)
- rate limiting: token bucket (qps/burst)
- error taxonomy: ProviderError(type/retryable/http_status)

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 3, 3.6)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, Optional

from cmis_core.digest import canonical_digest
from cmis_core.search_v3.query import SearchQueryRequest, compute_query_request_digest
from cmis_core.search_v3.registry import ProviderConfig
from cmis_core.search_v3.serp import SearchHitRef, SerpSnapshotRef
from cmis_core.search_v3.url_utils import canonicalize_url
from cmis_core.stores.artifact_store import ArtifactStore


@dataclass(frozen=True)
class ProviderError(Exception):
    """Provider 표준 오류.

    type:
      - RateLimited | Timeout | AuthFailed | BadRequest | UpstreamError | Unknown
    """

    type: str
    retryable: bool
    message: str
    http_status: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover
        status = f" http_status={self.http_status}" if self.http_status is not None else ""
        return f"ProviderError(type={self.type}{status}, retryable={self.retryable}): {self.message}"


class _TTLCache:
    """간단한 in-memory TTL cache."""

    def __init__(self) -> None:
        self._data: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < now:
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, *, ttl_sec: int) -> None:
        expires_at = time.time() + max(0, int(ttl_sec))
        self._data[key] = (expires_at, value)


class _TokenBucket:
    """Token bucket rate limiter (qps/burst)."""

    def __init__(self, *, rate_qps: float, burst: int) -> None:
        self.rate_qps = float(rate_qps)
        self.capacity = float(max(1, int(burst)))
        self.tokens = self.capacity
        self.updated_at = time.monotonic()

    def try_acquire(self) -> tuple[bool, float]:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.updated_at = now

        if self.rate_qps > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_qps)

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0.0

        if self.rate_qps <= 0:
            return False, float("inf")

        wait = (1.0 - self.tokens) / self.rate_qps
        return False, max(0.0, float(wait))


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _dedupe_hits(hits: list[SearchHitRef]) -> list[SearchHitRef]:
    """canonical_url 기준 중복 제거 (rank는 최소 유지)."""

    best: Dict[str, SearchHitRef] = {}
    for h in hits:
        key = h.canonical_url or h.url
        prev = best.get(key)
        if prev is None or h.rank < prev.rank:
            best[key] = h
    return sorted(best.values(), key=lambda x: x.rank)


class GoogleCseProvider:
    """Google Custom Search adapter (GenericWebSearch)."""

    def __init__(
        self,
        cfg: ProviderConfig,
        *,
        api_key: str,
        search_engine_id: str,
        artifact_store: ArtifactStore,
        http_get: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.cfg = cfg
        self.api_key = str(api_key)
        self.search_engine_id = str(search_engine_id)
        self.artifacts = artifact_store

        # http_get(url, params=params, timeout=timeout) -> response-like
        self.http_get = http_get

        self.cache = _TTLCache()
        self.rate = _TokenBucket(rate_qps=cfg.rate_limit_qps, burst=cfg.burst)

    @property
    def provider_id(self) -> str:
        return self.cfg.provider_id

    def supports(self, capability: str) -> bool:
        return str(capability) in {"web_search", "site_filter", "time_filter", "safe_search"}

    def search(self, req: SearchQueryRequest) -> SerpSnapshotRef:
        """SERP를 조회하고 SerpSnapshotRef를 반환합니다."""

        req_digest = req.request_digest or compute_query_request_digest(req)
        cache_key = f"{self.cfg.provider_config_digest}|{req_digest}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        ok, wait_sec = self.rate.try_acquire()
        if not ok:
            raise ProviderError(
                type="RateLimited",
                retryable=True,
                message="rate limit exceeded",
                http_status=429,
                meta={"wait_sec": wait_sec},
            )

        url = "https://www.googleapis.com/customsearch/v1"
        params: Dict[str, Any] = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": req.query,
            "num": int(req.top_k),
            "hl": req.language,
            "gl": req.region.lower(),
        }

        # Optional filters
        recency_days = (req.filters or {}).get("recency_days")
        if isinstance(recency_days, int) and recency_days > 0:
            params["dateRestrict"] = f"d{recency_days}"

        try:
            resp = self._http_get(url, params=params, timeout=int(req.timeout_sec))
        except ProviderError:
            raise
        except Exception as e:  # pragma: no cover (defensive)
            raise ProviderError(type="Unknown", retryable=True, message=str(e))

        status = int(getattr(resp, "status_code", 0) or 0)
        if status != 200:
            raise self._classify_http_error(status, resp)

        data = resp.json() if hasattr(resp, "json") else {}
        if not isinstance(data, dict):
            raise ProviderError(type="UpstreamError", retryable=True, message="invalid JSON response", http_status=200)

        raw_items = data.get("items", []) or []
        if not isinstance(raw_items, list):
            raw_items = []

        hits: list[SearchHitRef] = []
        normalized_hits: list[Dict[str, Any]] = []
        for i, item in enumerate(raw_items):
            if not isinstance(item, dict):
                continue
            link = str(item.get("link") or "").strip()
            if link == "":
                continue

            canonical = canonicalize_url(link)
            rank = i + 1

            hits.append(
                SearchHitRef(
                    url=link,
                    canonical_url=canonical,
                    rank=rank,
                    provider_id=self.provider_id,
                )
            )
            normalized_hits.append(
                {
                    "rank": rank,
                    "url": link,
                    "canonical_url": canonical,
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                }
            )

        hits = _dedupe_hits(hits)

        serp_payload = {
            "provider_id": self.provider_id,
            "provider_config_digest": self.cfg.provider_config_digest,
            "query_request_digest": req_digest,
            "query_artifact_id": req.query_artifact_id,
            "request": {
                "language": req.language,
                "region": req.region,
                "top_k": int(req.top_k),
                "timeout_sec": int(req.timeout_sec),
                "filters": dict(req.filters or {}),
            },
            "raw_response": data,
            "normalized_hits": normalized_hits,
        }
        serp_digest = canonical_digest(
            {
                "provider_id": self.provider_id,
                "provider_config_digest": self.cfg.provider_config_digest,
                "query_request_digest": req_digest,
                "raw_response": data,
                "normalized_hits": normalized_hits,
            }
        )
        serp_artifact_id = self.artifacts.put_json(serp_payload, kind="search_v3_serp")

        snapshot = SerpSnapshotRef(
            provider_id=self.provider_id,
            serp_artifact_id=serp_artifact_id,
            serp_digest=serp_digest,
            query_request_digest=req_digest,
            retrieved_at=_utc_now_iso_z(),
            hits=hits,
            provider_config_digest=self.cfg.provider_config_digest,
        )

        ttl = int(self.cfg.cache_ttl_sec)
        if ttl > 0:
            self.cache.set(cache_key, snapshot, ttl_sec=ttl)
        return snapshot

    def _http_get(self, url: str, *, params: Dict[str, Any], timeout: int) -> Any:
        if self.http_get is not None:
            return self.http_get(url, params=params, timeout=timeout)

        # Lazy import: requests는 기존 codebase에서도 사용 중이지만, import 비용/환경을 최소화합니다.
        try:
            import requests  # type: ignore
        except Exception as e:  # pragma: no cover
            raise ProviderError(type="UpstreamError", retryable=True, message=f"requests import failed: {e}")

        try:
            return requests.get(url, params=params, timeout=timeout)
        except requests.Timeout as e:
            raise ProviderError(type="Timeout", retryable=True, message=str(e))
        except requests.RequestException as e:
            raise ProviderError(type="UpstreamError", retryable=True, message=str(e))

    @staticmethod
    def _classify_http_error(status_code: int, resp: Any) -> ProviderError:
        text = ""
        try:
            text = str(getattr(resp, "text", "") or "")
        except Exception:
            text = ""

        if status_code == 429:
            return ProviderError(type="RateLimited", retryable=True, message="upstream rate limited", http_status=429)
        if status_code in {401, 403}:
            return ProviderError(type="AuthFailed", retryable=False, message="auth failed", http_status=status_code)
        if 400 <= status_code < 500:
            return ProviderError(type="BadRequest", retryable=False, message=(text or "bad request"), http_status=status_code)
        if 500 <= status_code < 600:
            return ProviderError(type="UpstreamError", retryable=True, message=(text or "upstream error"), http_status=status_code)
        return ProviderError(type="Unknown", retryable=True, message=(text or "unknown error"), http_status=status_code)
