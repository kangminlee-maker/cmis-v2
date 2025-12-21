"""Search Strategy v3 LinkSelectionPolicy unit tests (SSV3-15)."""

from __future__ import annotations

from dataclasses import dataclass

from cmis_core.search_v3.link_selector import LinkSelectionConfig, LinkSelectionPolicyV1


@dataclass(frozen=True)
class _C:
    url: str
    canonical_url: str
    relevance_score: float
    link_type: str = "general"


def test_link_selector_applies_threshold_and_visited_and_domain() -> None:
    policy = LinkSelectionPolicyV1()
    visited = {"https://example.com/already"}

    cands = [
        _C(url="https://example.com/already", canonical_url="https://example.com/already", relevance_score=0.9),
        _C(url="https://evil.com/x", canonical_url="https://evil.com/x", relevance_score=0.9),
        _C(url="https://example.com/good", canonical_url="https://example.com/good", relevance_score=0.7),
        _C(url="https://example.com/low", canonical_url="https://example.com/low", relevance_score=0.1),
    ]

    selected = policy.select_links(
        cands,
        visited=visited,
        parent_url="https://example.com/root",
        config=LinkSelectionConfig(max_links_per_doc=10, min_relevance_score=0.6, same_domain_only=True),
    )

    assert [c.canonical_url for c in selected] == ["https://example.com/good"]


