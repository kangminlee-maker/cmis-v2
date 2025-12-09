"""EvidenceStore Unit Tests

Evidence 저장/조회/캐싱 기능 테스트
"""

import pytest
import time
from pathlib import Path

from cmis_core.evidence_store import (
    EvidenceStore,
    MemoryBackend,
    SQLiteBackend,
    create_evidence_store,
)
from cmis_core.types import (
    EvidenceRequest,
    EvidenceBundle,
    EvidenceRecord,
    EvidenceValueKind,
    MetricRequest,
)


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def sample_bundle():
    """샘플 EvidenceBundle"""
    request = EvidenceRequest(
        request_id="REQ-test-001",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "year": 2024}
    )
    
    bundle = EvidenceBundle(request=request)
    
    bundle.add_evidence(EvidenceRecord(
        evidence_id="EVD-001",
        source_tier="official",
        source_id="DART",
        value=1000000000,
        value_kind=EvidenceValueKind.NUMERIC,
        confidence=0.95
    ))
    
    bundle.calculate_quality_summary()
    
    return bundle


# ========================================
# MemoryBackend Tests
# ========================================

def test_memory_backend_save_get():
    """메모리 백엔드 저장/조회"""
    backend = MemoryBackend()
    
    backend.save("test-key", {"value": 123}, ttl=None)
    
    result = backend.get("test-key")
    assert result is not None
    assert result["value"] == 123


def test_memory_backend_ttl():
    """메모리 백엔드 TTL"""
    backend = MemoryBackend()
    
    # TTL 1초
    backend.save("test-key", {"value": 456}, ttl=1)
    
    # 즉시 조회 → 성공
    result1 = backend.get("test-key")
    assert result1 is not None
    
    # 2초 대기
    time.sleep(2)
    
    # 조회 → 만료됨
    result2 = backend.get("test-key")
    assert result2 is None


def test_memory_backend_clear():
    """메모리 백엔드 전체 삭제"""
    backend = MemoryBackend()
    
    backend.save("key1", {"value": 1})
    backend.save("key2", {"value": 2})
    
    backend.clear()
    
    assert backend.get("key1") is None
    assert backend.get("key2") is None


# ========================================
# SQLiteBackend Tests
# ========================================

def test_sqlite_backend_save_get(tmp_path):
    """SQLite 백엔드 저장/조회"""
    db_path = tmp_path / "test.db"
    backend = SQLiteBackend(str(db_path))
    
    backend.save("test-key", {"value": 789})
    
    result = backend.get("test-key")
    assert result is not None
    assert result["value"] == 789


def test_sqlite_backend_ttl(tmp_path):
    """SQLite 백엔드 TTL"""
    db_path = tmp_path / "test.db"
    backend = SQLiteBackend(str(db_path))
    
    # TTL 1초
    backend.save("test-key", {"value": 999}, ttl=1)
    
    # 즉시 조회 → 성공
    result1 = backend.get("test-key")
    assert result1 is not None
    
    # 2초 대기
    time.sleep(2)
    
    # 조회 → 만료됨
    result2 = backend.get("test-key")
    assert result2 is None


def test_sqlite_backend_cleanup_expired(tmp_path):
    """SQLite 만료 항목 정리"""
    db_path = tmp_path / "test.db"
    backend = SQLiteBackend(str(db_path))
    
    # TTL 1초
    backend.save("key1", {"value": 1}, ttl=1)
    backend.save("key2", {"value": 2}, ttl=None)  # 만료 없음
    
    # 2초 대기
    time.sleep(2)
    
    # 만료 항목 정리
    backend.cleanup_expired()
    
    # key1 삭제됨, key2 유지
    assert backend.get("key1") is None
    assert backend.get("key2") is not None


# ========================================
# EvidenceStore Tests
# ========================================

def test_evidence_store_save_get(sample_bundle):
    """EvidenceStore 저장/조회"""
    store = EvidenceStore(backend=MemoryBackend())
    
    # 저장
    store.save(sample_bundle)
    
    # 조회
    retrieved = store.get(sample_bundle.request)
    
    assert retrieved is not None
    assert retrieved.request.metric_id == "MET-Revenue"
    assert len(retrieved.records) == 1
    assert retrieved.records[0].value == 1000000000


def test_evidence_store_cache_key(sample_bundle):
    """캐시 키 생성 테스트"""
    store = EvidenceStore(backend=MemoryBackend())
    
    key1 = store._build_cache_key(sample_bundle.request)
    
    # 동일한 request → 동일한 키
    request2 = EvidenceRequest(
        request_id="REQ-test-002",  # 다른 ID
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "year": 2024}
    )
    
    key2 = store._build_cache_key(request2)
    
    assert key1 == key2  # metric_id, context가 같으면 동일 키


def test_evidence_store_cache_key_different_context():
    """다른 context → 다른 캐시 키"""
    store = EvidenceStore(backend=MemoryBackend())
    
    req1 = EvidenceRequest(
        request_id="REQ-1",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "year": 2024}
    )
    
    req2 = EvidenceRequest(
        request_id="REQ-2",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "year": 2023}  # 다른 year
    )
    
    key1 = store._build_cache_key(req1)
    key2 = store._build_cache_key(req2)
    
    assert key1 != key2


def test_evidence_store_max_age(sample_bundle):
    """max_age_seconds 체크"""
    store = EvidenceStore(backend=MemoryBackend())
    
    # 저장
    store.save(sample_bundle)
    
    # 즉시 조회 (max_age=10초) → 성공
    retrieved1 = store.get(sample_bundle.request, max_age_seconds=10)
    assert retrieved1 is not None
    
    # 1초 대기
    time.sleep(1)
    
    # max_age=0.5초 → 만료된 것으로 간주
    retrieved2 = store.get(sample_bundle.request, max_age_seconds=0.5)
    assert retrieved2 is None


def test_evidence_store_metric_request():
    """MetricRequest로 조회 (자동 변환)"""
    store = EvidenceStore(backend=MemoryBackend())
    
    # MetricRequest
    metric_req = MetricRequest(
        metric_id="MET-Revenue",
        context={"region": "KR"}
    )
    
    # EvidenceRequest로 변환
    evidence_req = store._metric_to_evidence_request(metric_req)
    
    assert evidence_req.metric_id == "MET-Revenue"
    assert evidence_req.context == {"region": "KR"}


def test_evidence_store_invalidate():
    """캐시 무효화"""
    store = EvidenceStore(backend=MemoryBackend())
    
    # 저장
    req = EvidenceRequest(
        request_id="REQ-test",
        request_type="metric",
        metric_id="MET-Revenue",
        context={}
    )
    
    bundle = EvidenceBundle(request=req)
    store.save(bundle)
    
    # 전체 무효화
    store.invalidate("*")
    
    # 조회 → 없음
    assert store.get(req) is None


# ========================================
# Factory Tests
# ========================================

def test_create_evidence_store_memory():
    """메모리 백엔드 팩토리"""
    store = create_evidence_store(backend_type="memory")
    
    assert isinstance(store.backend, MemoryBackend)
    assert store.default_ttl == 86400


def test_create_evidence_store_sqlite(tmp_path):
    """SQLite 백엔드 팩토리"""
    db_path = tmp_path / "test.db"
    
    store = create_evidence_store(
        backend_type="sqlite",
        db_path=str(db_path)
    )
    
    assert isinstance(store.backend, SQLiteBackend)
    assert store.default_ttl == 86400


# ========================================
# Serialization Tests
# ========================================

def test_evidence_store_serialization(sample_bundle):
    """EvidenceBundle 직렬화/역직렬화"""
    store = EvidenceStore(backend=MemoryBackend())
    
    # 직렬화
    serialized = store._serialize_bundle(sample_bundle)
    
    assert "request" in serialized
    assert "records" in serialized
    assert len(serialized["records"]) == 1
    
    # 역직렬화
    deserialized = store._deserialize_bundle(serialized)
    
    assert deserialized.request.metric_id == "MET-Revenue"
    assert len(deserialized.records) == 1
    assert deserialized.records[0].value == 1000000000

