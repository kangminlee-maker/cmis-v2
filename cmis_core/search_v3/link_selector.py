"""Search Strategy v3 LinkSelectionPolicy v1 (SSV3-15).

목표:
- LinkExtractor가 산출한 후보(LinkCandidate)에 대해, 정책/예산/visited 제약 내에서
  "실제로 따라갈 링크"를 선택합니다.

핵심 원칙:
- budget 내에서만 선택 (문서당 max_links_per_doc, 전체 budget은 상위 호출자에서 제한)
- visited(중복) 제거
- (옵션) same_domain_only 강제
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, Set
from urllib.parse import urlsplit

from cmis_core.search_v3.url_utils import canonicalize_url


class LinkCandidateLike(Protocol):
    """LinkCandidate에 대한 구조적 타입(순환 import 회피)."""

    url: str
    canonical_url: str
    relevance_score: float
    link_type: str


@dataclass(frozen=True)
class LinkSelectionConfig:
    """링크 선택 정책 파라미터."""

    max_links_per_doc: int = 3
    min_relevance_score: float = 0.6
    same_domain_only: bool = False


class LinkSelectionPolicyV1:
    """규칙 기반 LinkSelectionPolicy v1."""

    def select_links(
        self,
        candidates: List[LinkCandidateLike],
        *,
        visited: Set[str],
        parent_url: str,
        config: Optional[LinkSelectionConfig] = None,
    ) -> List[LinkCandidateLike]:
        """후보 링크를 정책에 따라 선택해 반환합니다."""

        cfg = config or LinkSelectionConfig()
        max_links = max(0, int(cfg.max_links_per_doc))
        min_score = float(cfg.min_relevance_score)
        same_domain_only = bool(cfg.same_domain_only)

        if not isinstance(candidates, list) or not candidates or max_links <= 0:
            return []

        parent_host = _host_for_url(parent_url)

        filtered: List[LinkCandidateLike] = []
        for c in candidates:
            try:
                score = float(getattr(c, "relevance_score", 0.0) or 0.0)
            except Exception:
                score = 0.0
            if score < min_score:
                continue

            canon = str(getattr(c, "canonical_url", "") or "").strip()
            if not canon:
                url = str(getattr(c, "url", "") or "").strip()
                canon = canonicalize_url(url)

            if not canon or canon in visited:
                continue

            if same_domain_only:
                host = _host_for_url(canon)
                if not _is_same_or_subdomain(host, parent_host):
                    continue

            filtered.append(c)

        filtered.sort(key=lambda x: (-float(getattr(x, "relevance_score", 0.0) or 0.0), str(getattr(x, "canonical_url", "") or getattr(x, "url", ""))))
        return filtered[:max_links]


def _host_for_url(url: str) -> str:
    host = (urlsplit(str(url or "")).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_same_or_subdomain(a: str, b: str) -> bool:
    """a가 b와 같거나 하위 도메인인지, 또는 그 반대인지(완화) 판단합니다."""

    a_s = str(a or "").strip().lower()
    b_s = str(b or "").strip().lower()
    if not a_s or not b_s:
        return False
    if a_s == b_s:
        return True
    if a_s.endswith(f".{b_s}"):
        return True
    if b_s.endswith(f".{a_s}"):
        return True
    return False


