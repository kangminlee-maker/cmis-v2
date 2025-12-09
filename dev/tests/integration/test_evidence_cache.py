"""Evidence Cache 통합 테스트

EvidenceEngine + EvidenceStore 캐시 동작 검증
"""

import pytest
import time

from cmis_core.config import CMISConfig
from cmis_core.types import MetricRequest
from cmis_core.evidence_engine import EvidenceEngine, SourceRegistry
from cmis_core.evidence_store import create_evidence_store
from cmis_core.evidence.sources import StubSource, SourceTier


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def config():
    """CMISConfig"""
    return CMISConfig()


class CallCounter:
    """호출 횟수 추적 클래스"""
    def __init__(self):
        self.count = 0
    
    def increment(self):
        self.count += 1
    
    def reset(self):
        self.count = 0


@pytest.fixture
def evidence_engine_with_cache(config):
    """캐시가 활성화된 EvidenceEngine"""
    # SourceRegistry
    registry = SourceRegistry()
    counter = CallCounter()
    
    # TrackedSource (호출 추적용)
    class TrackedSource(StubSource):
        def __init__(self, counter, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.counter = counter
        
        def fetch(self, request):
            self.counter.increment()
            time.sleep(0.01)  # 약간 지연
            return super().fetch(request)
    
    tracked_source = TrackedSource(
        counter,
        source_id="TrackedSource",
        source_tier=SourceTier.OFFICIAL,
        stub_data={"value": 1234567890}
    )
    
    registry.register_source("TrackedSource", "official", tracked_source)
    
    # EvidenceStore (메모리)
    store = create_evidence_store(backend_type="memory", default_ttl=3600)
    
    # EvidenceEngine
    engine = EvidenceEngine(config, registry, store)
    engine._counter = counter  # 추적용
    
    return engine


# ========================================
# Cache Tests
# ========================================

def test_cache_hit(evidence_engine_with_cache):
    """캐시 hit 테스트"""
    engine = evidence_engine_with_cache
    counter = engine._counter
    
    requests = [
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR"})
    ]
    
    # 첫 번째 호출 (캐시 miss)
    counter.reset()
    result1 = engine.fetch_for_metrics(requests)
    
    assert counter.count == 1  # Source 호출됨
    assert result1.execution_summary["cache_hits"] == 0
    assert result1.execution_summary["cache_misses"] == 1
    
    # 두 번째 호출 (캐시 hit)
    counter.reset()
    result2 = engine.fetch_for_metrics(requests)
    
    assert counter.count == 0  # Source 호출 안 됨
    assert result2.execution_summary["cache_hits"] == 1
    assert result2.execution_summary["cache_misses"] == 0
    
    # 값 동일
    bundle1 = result1.get_bundle("MET-Revenue")
    bundle2 = result2.get_bundle("MET-Revenue")
    
    assert bundle1.records[0].value == bundle2.records[0].value


def test_cache_different_context(evidence_engine_with_cache):
    """다른 context → 다른 캐시 키"""
    engine = evidence_engine_with_cache
    counter = engine._counter
    
    # Context 1: 2024년
    requests1 = [
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR", "year": 2024})
    ]
    
    # Context 2: 2023년
    requests2 = [
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR", "year": 2023})
    ]
    
    # 첫 번째 호출
    counter.reset()
    result1 = engine.fetch_for_metrics(requests1)
    assert counter.count == 1
    
    # 두 번째 호출 (다른 context) → 캐시 miss
    counter.reset()
    result2 = engine.fetch_for_metrics(requests2)
    assert counter.count == 1  # 다시 호출됨


def test_cache_multiple_metrics(evidence_engine_with_cache):
    """여러 Metric 캐싱"""
    engine = evidence_engine_with_cache
    counter = engine._counter
    
    requests = [
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR"}),
        MetricRequest(metric_id="MET-N_customers", context={"region": "KR"}),
    ]
    
    # 첫 번째 호출
    counter.reset()
    result1 = engine.fetch_for_metrics(requests)
    assert counter.count == 2  # 2개 metric
    assert result1.execution_summary["cache_misses"] == 2
    
    # 두 번째 호출 (전체 캐시 hit)
    counter.reset()
    result2 = engine.fetch_for_metrics(requests)
    assert counter.count == 0
    assert result2.execution_summary["cache_hits"] == 2


def test_cache_disable(evidence_engine_with_cache):
    """캐시 비활성화"""
    engine = evidence_engine_with_cache
    counter = engine._counter
    
    requests = [
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR"})
    ]
    
    # 첫 번째 호출 (캐시 사용)
    counter.reset()
    result1 = engine.fetch_for_metrics(requests, use_cache=True)
    assert counter.count == 1
    
    # 두 번째 호출 (캐시 비활성화)
    counter.reset()
    result2 = engine.fetch_for_metrics(requests, use_cache=False)
    assert counter.count == 1  # 다시 호출됨


def test_cache_partial_hit(evidence_engine_with_cache):
    """부분 캐시 hit (일부만 캐시)"""
    engine = evidence_engine_with_cache
    counter = engine._counter
    
    # 첫 번째 호출: MET-Revenue만
    counter.reset()
    result1 = engine.fetch_for_metrics([
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR"})
    ])
    assert counter.count == 1
    
    # 두 번째 호출: MET-Revenue + MET-N_customers
    counter.reset()
    result2 = engine.fetch_for_metrics([
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR"}),
        MetricRequest(metric_id="MET-N_customers", context={"region": "KR"}),
    ])
    
    # MET-Revenue는 캐시 hit, MET-N_customers만 호출
    assert counter.count == 1
    assert result2.execution_summary["cache_hits"] == 1
    assert result2.execution_summary["cache_misses"] == 1


def test_sqlite_backend_persistence(config, tmp_path):
    """SQLite 백엔드 영구 저장"""
    db_path = tmp_path / "cache.db"
    
    # EvidenceEngine 1 (저장)
    registry1 = SourceRegistry()
    stub1 = StubSource("Stub1", SourceTier.OFFICIAL, {"value": 11111})
    registry1.register_source("Stub1", "official", stub1)
    
    store1 = create_evidence_store(backend_type="sqlite", db_path=str(db_path))
    engine1 = EvidenceEngine(config, registry1, store1)
    
    requests = [MetricRequest(metric_id="MET-Revenue", context={"region": "KR"})]
    result1 = engine1.fetch_for_metrics(requests)
    
    assert result1.execution_summary["cache_misses"] == 1
    
    # EvidenceEngine 2 (새 인스턴스, 같은 DB)
    registry2 = SourceRegistry()
    stub2 = StubSource("Stub2", SourceTier.OFFICIAL, {"value": 22222})
    registry2.register_source("Stub2", "official", stub2)
    
    store2 = create_evidence_store(backend_type="sqlite", db_path=str(db_path))
    engine2 = EvidenceEngine(config, registry2, store2)
    
    # 같은 요청 → 캐시 hit (DB에서 로드)
    result2 = engine2.fetch_for_metrics(requests)
    
    assert result2.execution_summary["cache_hits"] == 1
    
    # 값 동일 (첫 번째 engine의 값)
    bundle = result2.get_bundle("MET-Revenue")
    assert bundle.records[0].source_id == "Stub1"  # 첫 번째 source

