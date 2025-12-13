"""Evidence Engine Unit Tests

Evidence Engine 핵심 기능 테스트
"""

import pytest
from datetime import datetime

from cmis_core.config import CMISConfig
from cmis_core.types import (
    MetricRequest,
    EvidenceRequest,
    EvidenceRecord,
    EvidenceBundle,
    EvidenceMultiResult,
    EvidenceSufficiency,
    EvidencePolicy,
    SourceTier,
    EvidenceValueKind,
)
from cmis_core.evidence_engine import (
    EvidenceEngine,
    EvidencePlanner,
    EvidenceExecutor,
    SourceRegistry,
    BaseDataSource,
    EvidencePlan,
)
from cmis_core.evidence.sources import StubSource


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def config():
    """CMISConfig 로드"""
    return CMISConfig()


@pytest.fixture
def source_registry():
    """SourceRegistry 생성"""
    registry = SourceRegistry()

    # StubSource 등록
    stub1 = StubSource(
        source_id="StubOfficial",
        source_tier=SourceTier.OFFICIAL,
        stub_data={"value": 1000000, "source": "official"}
    )

    stub2 = StubSource(
        source_id="StubCommercial",
        source_tier=SourceTier.COMMERCIAL,
        stub_data={"value": 1200000, "source": "commercial"}
    )

    registry.register_source("StubOfficial", "official", stub1)
    registry.register_source("StubCommercial", "commercial", stub2)

    return registry


@pytest.fixture
def evidence_engine(config, source_registry):
    """EvidenceEngine 생성"""
    return EvidenceEngine(config, source_registry)


# ========================================
# EvidencePolicy Tests
# ========================================

def test_evidence_policy_from_config(config):
    """EvidencePolicy.from_config() 테스트"""
    policy = EvidencePolicy.from_config("reporting_strict", config)

    assert policy.policy_id == "reporting_strict"
    assert policy.min_literal_ratio == 0.7
    assert policy.max_spread_ratio == 0.3
    assert policy.allow_prior == False
    assert "official" in policy.allowed_tiers


def test_evidence_policy_decision_balanced(config):
    """decision_balanced policy 테스트"""
    policy = EvidencePolicy.from_config("decision_balanced", config)

    assert policy.min_literal_ratio == 0.5
    assert policy.max_spread_ratio == 0.5
    assert policy.allow_prior == True


# ========================================
# SourceRegistry Tests
# ========================================

def test_source_registry_register(source_registry):
    """Source 등록 테스트"""
    assert source_registry.get_source("StubOfficial") is not None
    assert source_registry.get_source("StubCommercial") is not None


def test_source_registry_get_by_tier(source_registry):
    """Tier별 source 조회 테스트"""
    official_sources = source_registry.get_sources_by_tier("official")
    assert len(official_sources) == 1
    assert official_sources[0].source_id == "StubOfficial"


def test_source_registry_find_capable(source_registry):
    """Capability 기반 source 찾기 테스트"""
    request = EvidenceRequest(
        request_id="test-req",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR"}
    )

    capable = source_registry.find_capable_sources(request)

    # Tier 순서로 정렬되어야 함 (official 먼저)
    assert len(capable) >= 1
    assert capable[0].source_tier == SourceTier.OFFICIAL


# ========================================
# EvidencePlanner Tests
# ========================================

def test_evidence_planner_build_plan(config, source_registry):
    """EvidencePlanner.build_plan() 테스트"""
    planner = EvidencePlanner(source_registry, config)
    policy = EvidencePolicy.from_config("reporting_strict", config)

    request = EvidenceRequest(
        request_id="test-req",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR"}
    )

    plan = planner.build_plan(request, policy)

    assert isinstance(plan, EvidencePlan)
    assert plan.request == request
    assert plan.policy == policy
    assert len(plan.tier_groups) >= 1


# ========================================
# EvidenceExecutor Tests
# ========================================

def test_evidence_executor_run(config, source_registry):
    """EvidenceExecutor.run() 테스트"""
    planner = EvidencePlanner(source_registry, config)
    executor = EvidenceExecutor(source_registry)
    policy = EvidencePolicy.from_config("reporting_strict", config)

    request = EvidenceRequest(
        request_id="test-req",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR"}
    )

    plan = planner.build_plan(request, policy)
    bundle = executor.run(plan, policy)

    assert isinstance(bundle, EvidenceBundle)
    assert len(bundle.records) >= 1
    assert bundle.execution_time_ms is not None


def test_evidence_executor_early_return(config, source_registry):
    """Early Return 로직 테스트"""
    executor = EvidenceExecutor(source_registry)
    policy = EvidencePolicy.from_config("exploration_friendly", config)
    # exploration_friendly는 best_effort_mode=True

    request = EvidenceRequest(
        request_id="test-req",
        request_type="metric",
        context={}
    )

    # Plan with multiple tiers
    plan = EvidencePlan(
        request=request,
        tier_groups={
            1: [source_registry.get_source("StubOfficial")],
            3: [source_registry.get_source("StubCommercial")]
        },
        policy=policy
    )

    bundle = executor.run(plan, policy)

    # Tier 1에서 성공했으면 Tier 3는 호출 안 됨
    assert len(bundle.debug_trace) >= 1


# ========================================
# EvidenceEngine Integration Tests
# ========================================

def test_evidence_engine_fetch_for_metrics(evidence_engine):
    """EvidenceEngine.fetch_for_metrics() 통합 테스트"""
    requests = [
        MetricRequest(
            metric_id="MET-Revenue",
            context={"region": "KR", "year": 2024}
        ),
        MetricRequest(
            metric_id="MET-N_customers",
            context={"region": "KR", "year": 2024}
        )
    ]

    result = evidence_engine.fetch_for_metrics(
        requests,
        policy_ref="decision_balanced"
    )

    assert isinstance(result, EvidenceMultiResult)
    assert len(result.bundles) == 2
    assert "MET-Revenue" in result.bundles
    assert "MET-N_customers" in result.bundles


def test_evidence_engine_bundle_quality(evidence_engine):
    """EvidenceBundle quality_summary 테스트"""
    requests = [
        MetricRequest(
            metric_id="MET-Revenue",
            context={"region": "KR"}
        )
    ]

    result = evidence_engine.fetch_for_metrics(requests)
    bundle = result.get_bundle("MET-Revenue")

    assert bundle is not None
    bundle.calculate_quality_summary()

    summary = bundle.quality_summary
    assert "literal_ratio" in summary
    assert "spread_ratio" in summary
    assert "num_sources" in summary


# ========================================
# EvidenceBundle Tests
# ========================================

def test_evidence_bundle_add_evidence():
    """EvidenceBundle.add_evidence() 테스트"""
    request = EvidenceRequest(
        request_id="test",
        request_type="metric"
    )

    bundle = EvidenceBundle(request=request)

    record = EvidenceRecord(
        evidence_id="EVD-1",
        source_tier="official",
        source_id="Test",
        value=1000,
        confidence=0.9
    )

    bundle.add_evidence(record)

    assert len(bundle.records) == 1
    assert bundle.get_best_record() == record


def test_evidence_bundle_calculate_quality():
    """EvidenceBundle.calculate_quality_summary() 테스트"""
    request = EvidenceRequest(
        request_id="test",
        request_type="metric"
    )

    bundle = EvidenceBundle(request=request)

    # Official tier record
    bundle.add_evidence(EvidenceRecord(
        evidence_id="EVD-1",
        source_tier="official",
        source_id="Source1",
        value=1000,
        confidence=0.9
    ))

    # Commercial tier record
    bundle.add_evidence(EvidenceRecord(
        evidence_id="EVD-2",
        source_tier="commercial",
        source_id="Source2",
        value=1200,
        confidence=0.8
    ))

    bundle.calculate_quality_summary()

    summary = bundle.quality_summary
    assert summary["literal_ratio"] == 0.5  # 1 official / 2 total
    assert summary["num_sources"] == 2


# ========================================
# StubSource Tests
# ========================================

def test_stub_source_fetch():
    """StubSource.fetch() 테스트"""
    stub = StubSource(
        source_id="TestStub",
        source_tier=SourceTier.OFFICIAL,
        stub_data={"value": 12345}
    )

    request = EvidenceRequest(
        request_id="test",
        request_type="metric"
    )

    record = stub.fetch(request)

    assert record.value == 12345
    assert record.source_id == "TestStub"
    assert record.source_tier == "official"


def test_stub_source_can_handle():
    """StubSource.can_handle() 테스트"""
    stub = StubSource(
        source_id="TestStub",
        source_tier=SourceTier.OFFICIAL,
        stub_data={}
    )

    request = EvidenceRequest(
        request_id="test",
        request_type="metric"
    )

    assert stub.can_handle(request) == True



