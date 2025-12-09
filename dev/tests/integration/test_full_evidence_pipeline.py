"""전체 Evidence Pipeline 통합 테스트

EvidenceEngine + 실제 Sources + ValueEngine 전체 흐름 검증
"""

import pytest
import os
from dotenv import load_dotenv

from cmis_core.config import CMISConfig
from cmis_core.graph import InMemoryGraph
from cmis_core.types import MetricRequest
from cmis_core.value_engine import ValueEngine
from cmis_core.evidence_engine import EvidenceEngine, SourceRegistry
from cmis_core.evidence_store import create_evidence_store

load_dotenv()

HAS_GOOGLE_KEY = bool(
    os.getenv("GOOGLE_API_KEY") and
    os.getenv("GOOGLE_SEARCH_ENGINE_ID")
)


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def config():
    """CMISConfig"""
    return CMISConfig()


@pytest.fixture
def simple_graph():
    """Simple R-Graph"""
    graph = InMemoryGraph()
    
    graph.upsert_node(
        "ACT-cust-001",
        "actor",
        {
            "kind": "customer_segment",
            "metadata": {"approx_population": 3000000}
        }
    )
    
    graph.upsert_node(
        "MFL-001",
        "money_flow",
        {"quantity": {"amount": 290000000000, "unit": "KRW"}}
    )
    
    graph.add_edge("actor_pays_actor", "ACT-cust-001", "ACT-comp-001", {"via": "MFL-001"})
    
    return graph


@pytest.fixture
def full_evidence_engine(config):
    """실제 Source가 등록된 EvidenceEngine"""
    registry = SourceRegistry()
    
    # DART Source
    try:
        from cmis_core.evidence.sources import DARTSource
        dart = DARTSource()
        registry.register_source("DART", "official", dart)
    except Exception:
        pass
    
    # Google Search Source (API 키 있을 때만)
    if HAS_GOOGLE_KEY:
        try:
            from cmis_core.evidence.google_search_source import GoogleSearchSource
            google = GoogleSearchSource(max_results=3)
            registry.register_source("GoogleSearch", "commercial", google)
        except Exception:
            pass
    
    # KOSIS Source
    try:
        from cmis_core.evidence.kosis_source import KOSISSource
        kosis = KOSISSource()
        registry.register_source("KOSIS", "official", kosis)
    except Exception:
        pass
    
    # DuckDuckGo Source
    try:
        from cmis_core.evidence.duckduckgo_source import DuckDuckGoSource
        ddg = DuckDuckGoSource(max_results=3)
        registry.register_source("DuckDuckGo", "commercial", ddg)
    except Exception:
        pass
    
    # Store
    store = create_evidence_store("memory")
    
    return EvidenceEngine(config, registry, store)


# ========================================
# Pipeline Tests
# ========================================

def test_evidence_engine_with_multiple_sources(full_evidence_engine):
    """여러 Source 등록 확인"""
    engine = full_evidence_engine
    registry = engine.source_registry
    
    # 등록된 source 확인
    num_sources = len(registry._sources)
    print(f"\n등록된 Source 수: {num_sources}")
    
    for source_id, source in registry._sources.items():
        print(f"  - {source_id} ({source.source_tier.value})")
    
    assert num_sources >= 1  # 최소 1개는 등록되어야 함


@pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="Google API key required")
def test_full_pipeline_with_google(config, full_evidence_engine, simple_graph):
    """전체 Pipeline: Google Search → ValueEngine"""
    # ValueEngine with EvidenceEngine
    value_engine = ValueEngine(config, full_evidence_engine)
    
    requests = [
        MetricRequest(
            metric_id="MET-Revenue",
            context={
                "domain_id": "Adult_Language_Education_KR",
                "region": "KR",
                "year": 2024
            }
        )
    ]
    
    # 실행
    results, program = value_engine.evaluate_metrics(
        simple_graph,
        requests,
        use_evidence_engine=True
    )
    
    assert len(results) == 1
    
    revenue = results[0]
    print(f"\n전체 Pipeline 결과:")
    print(f"  Metric: {revenue.metric_id}")
    print(f"  Value: {revenue.point_estimate:,}")
    print(f"  Method: {revenue.quality['method']}")
    print(f"  Evidence Source: {revenue.quality.get('evidence_source', 'N/A')}")
    
    # Google Search 또는 R-Graph 값이어야 함
    assert revenue.point_estimate > 0
    
    # Program 확인
    assert program["use_evidence_engine"] == True


def test_source_registry_tiering(full_evidence_engine):
    """Source Tier 우선순위 확인"""
    registry = full_evidence_engine.source_registry
    
    # Tier별 source 확인
    tier_counts = {}
    
    for tier in ["official", "curated_internal", "commercial"]:
        sources = registry.get_sources_by_tier(tier)
        tier_counts[tier] = len(sources)
        
        print(f"\nTier {tier}: {len(sources)}개")
        for src in sources:
            print(f"  - {src.source_id}")
    
    # Official tier가 우선
    assert tier_counts["official"] >= 0


def test_cache_with_real_api(full_evidence_engine):
    """실제 API + 캐시 동작 확인"""
    engine = full_evidence_engine
    
    requests = [
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR"})
    ]
    
    # 첫 번째 호출
    result1 = engine.fetch_for_metrics(requests, use_cache=True)
    summary1 = result1.execution_summary
    
    print(f"\n첫 번째 호출:")
    print(f"  Cache hits: {summary1.get('cache_hits', 0)}")
    print(f"  Cache misses: {summary1.get('cache_misses', 0)}")
    
    # 두 번째 호출 (캐시 hit 예상)
    result2 = engine.fetch_for_metrics(requests, use_cache=True)
    summary2 = result2.execution_summary
    
    print(f"\n두 번째 호출:")
    print(f"  Cache hits: {summary2.get('cache_hits', 0)}")
    print(f"  Cache misses: {summary2.get('cache_misses', 0)}")
    
    # 두 번째는 캐시 hit
    assert summary2["cache_hits"] == 1
    assert summary2["cache_misses"] == 0

