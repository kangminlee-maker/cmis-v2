"""ValueEngine + EvidenceEngine 통합 테스트

ValueEngine이 EvidenceEngine을 통해 Evidence를 수집하고
ValueRecord로 변환하는 과정을 테스트
"""

import pytest

from cmis_core.config import CMISConfig
from cmis_core.graph import InMemoryGraph
from cmis_core.types import MetricRequest, Node, Edge
from cmis_core.value_engine import ValueEngine
from cmis_core.evidence_engine import SourceRegistry
from cmis_core.evidence.sources import StubSource, SourceTier


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def config():
    """CMISConfig"""
    return CMISConfig()


@pytest.fixture
def simple_graph():
    """간단한 R-Graph (테스트용)"""
    graph = InMemoryGraph()

    # Actor: customer_segment
    graph.upsert_node(
        "ACT-cust-001",
        "actor",
        {
            "kind": "customer_segment",
            "name": "성인 학습자",
            "metadata": {"approx_population": 3000000}
        }
    )

    # Actor: company (provider)
    graph.upsert_node(
        "ACT-comp-001",
        "actor",
        {
            "kind": "company",
            "name": "Provider A"
        }
    )

    # MoneyFlow
    graph.upsert_node(
        "MFL-001",
        "money_flow",
        {
            "quantity": {
                "amount": 290000000000,  # 2900억원
                "unit": "KRW",
                "per": "year"
            }
        }
    )

    # Edge: actor_pays_actor
    graph.add_edge(
        "actor_pays_actor",
        "ACT-cust-001",
        "ACT-comp-001",
        {"via": "MFL-001"}
    )

    return graph


@pytest.fixture
def value_engine_with_evidence(config):
    """EvidenceEngine이 통합된 ValueEngine"""
    from cmis_core.evidence_engine import (
        EvidenceEngine,
        BaseDataSource,
        SourceRegistry
    )
    from cmis_core.types import EvidenceRequest, EvidenceRecord, EvidenceValueKind

    # Custom Source (MET-Revenue만 처리)
    class RevenueOnlySource(BaseDataSource):
        def __init__(self):
            super().__init__(
                source_id="StubRevenue",
                source_tier=SourceTier.OFFICIAL,
                capabilities={
                    "provides": ["*"],
                    "regions": ["*"],
                    "data_types": ["numeric"]
                }
            )

        def fetch(self, request):
            return EvidenceRecord(
                evidence_id=f"EVD-{self.source_id}-{request.request_id[:8]}",
                source_tier=self.source_tier.value,
                source_id=self.source_id,
                value=300000000000,
                value_kind=EvidenceValueKind.NUMERIC,
                confidence=0.8
            )

        def can_handle(self, request):
            # MET-Revenue만 처리
            return request.metric_id == "MET-Revenue"

    # SourceRegistry에 등록
    registry = SourceRegistry()
    revenue_source = RevenueOnlySource()
    registry.register_source("StubRevenue", "official", revenue_source)

    # EvidenceEngine 생성
    evidence_engine = EvidenceEngine(config, registry)

    # ValueEngine 생성 (EvidenceEngine 주입)
    return ValueEngine(config, evidence_engine)


# ========================================
# Integration Tests
# ========================================

def test_value_engine_without_evidence(config, simple_graph):
    """EvidenceEngine 없이 R-Graph 기반 계산 (기존 방식)"""
    # EvidenceEngine 없는 ValueEngine
    value_engine = ValueEngine(config)

    requests = [
        MetricRequest(
            metric_id="MET-Revenue",
            context={"region": "KR"}
        )
    ]

    # use_evidence_engine=False로 R-Graph만 사용
    results, program, _metric_evals = value_engine.evaluate_metrics(
        simple_graph,
        requests,
        use_evidence_engine=False
    )

    assert len(results) == 1

    revenue_record = results[0]
    assert revenue_record.metric_id == "MET-Revenue"
    assert revenue_record.point_estimate == 290000000000  # R-Graph 값
    assert revenue_record.quality["method"] == "r_graph_aggregation"

    # Program 확인
    assert program["use_evidence_engine"] == False
    assert len(program["evidence_metrics"]) == 0


def test_value_engine_with_evidence(value_engine_with_evidence, simple_graph):
    """EvidenceEngine 통합: Evidence 우선 사용"""
    requests = [
        MetricRequest(
            metric_id="MET-Revenue",
            context={"region": "KR"}
        )
    ]

    # use_evidence_engine=True (기본값)
    results, program, _metric_evals = value_engine_with_evidence.evaluate_metrics(
        simple_graph,
        requests,
        use_evidence_engine=True
    )

    assert len(results) == 1

    revenue_record = results[0]
    assert revenue_record.metric_id == "MET-Revenue"

    # Evidence 값 사용 (StubSource의 3000억)
    assert revenue_record.point_estimate == 300000000000

    # Quality 확인
    assert revenue_record.quality["method"] == "evidence_direct"
    assert revenue_record.quality["evidence_source"] == "StubRevenue"
    assert revenue_record.quality["evidence_tier"] == "official"

    # Lineage 확인
    assert "evidence_engine" in revenue_record.lineage["engine_ids"]
    assert "value_engine" in revenue_record.lineage["engine_ids"]
    assert len(revenue_record.lineage["from_evidence_ids"]) >= 1

    # Program 확인
    assert program["use_evidence_engine"] == True
    assert "MET-Revenue" in program["evidence_metrics"]


def test_value_engine_evidence_fallback(value_engine_with_evidence, simple_graph):
    """Evidence record 없을 때 R-Graph로 fallback"""
    requests = [
        MetricRequest(
            metric_id="MET-N_customers",  # RevenueOnlySource가 처리 안 함
            context={"region": "KR"}
        )
    ]

    results, program, _metric_evals = value_engine_with_evidence.evaluate_metrics(
        simple_graph,
        requests,
        use_evidence_engine=True
    )

    assert len(results) == 1

    customer_record = results[0]
    assert customer_record.metric_id == "MET-N_customers"

    # Evidence record 없음 (bundle은 있지만 records=[]) → R-Graph fallback
    assert customer_record.point_estimate == 3000000  # R-Graph 값
    assert customer_record.quality["method"] == "r_graph_aggregation"

    # Program 확인
    assert program["use_evidence_engine"] == True
    # EvidenceEngine은 호출되었으므로 evidence_metrics에 포함됨
    assert "MET-N_customers" in program["evidence_metrics"]


def test_value_engine_multiple_metrics_mixed(value_engine_with_evidence, simple_graph):
    """여러 Metric: Evidence + R-Graph 혼합"""
    requests = [
        MetricRequest(
            metric_id="MET-Revenue",  # Evidence 있음
            context={"region": "KR"}
        ),
        MetricRequest(
            metric_id="MET-N_customers",  # Evidence 없음
            context={"region": "KR"}
        ),
        MetricRequest(
            metric_id="MET-Avg_price_per_unit",  # Derived
            context={"region": "KR"}
        )
    ]

    results, program, _metric_evals = value_engine_with_evidence.evaluate_metrics(
        simple_graph,
        requests,
        use_evidence_engine=True
    )

    assert len(results) == 3

    # MET-Revenue: Evidence
    revenue = next(r for r in results if r.metric_id == "MET-Revenue")
    assert revenue.quality["method"] == "evidence_direct"
    assert revenue.point_estimate == 300000000000

    # MET-N_customers: R-Graph fallback (RevenueOnlySource가 처리 안 함)
    customers = next(r for r in results if r.metric_id == "MET-N_customers")
    assert customers.quality["method"] == "r_graph_aggregation"
    assert customers.point_estimate == 3000000

    # MET-Avg_price_per_unit: Derived
    avg_price = next(r for r in results if r.metric_id == "MET-Avg_price_per_unit")
    assert avg_price.quality["method"] == "derived_calculation"
    assert avg_price.point_estimate == pytest.approx(96666.67, rel=1e-2)


def test_evidence_to_value_record_conversion(value_engine_with_evidence):
    """EvidenceBundle → ValueRecord 변환 테스트"""
    from cmis_core.types import EvidenceRequest, EvidenceBundle, EvidenceRecord, EvidenceValueKind

    # EvidenceBundle 생성
    request = EvidenceRequest(
        request_id="test-req",
        request_type="metric",
        metric_id="MET-Revenue"
    )

    bundle = EvidenceBundle(request=request)

    # EvidenceRecord 추가
    bundle.add_evidence(EvidenceRecord(
        evidence_id="EVD-001",
        source_tier="official",
        source_id="DART",
        value=250000000000,
        value_kind=EvidenceValueKind.NUMERIC,
        confidence=0.95
    ))

    bundle.calculate_quality_summary()

    # 변환
    value_record = value_engine_with_evidence._evidence_to_value_record(
        "MET-Revenue",
        {"region": "KR"},
        bundle
    )

    assert value_record.metric_id == "MET-Revenue"
    assert value_record.point_estimate == 250000000000
    assert value_record.quality["method"] == "evidence_direct"
    assert value_record.quality["evidence_source"] == "DART"
    assert value_record.quality["confidence"] == 0.95
    assert "evidence_engine" in value_record.lineage["engine_ids"]


def test_value_program_tracking(value_engine_with_evidence, simple_graph):
    """Value Program에 Evidence 사용 여부 추적"""
    requests = [
        MetricRequest(metric_id="MET-Revenue", context={"region": "KR"})
    ]

    # EvidenceEngine 사용
    results1, program1, _metric_evals1 = value_engine_with_evidence.evaluate_metrics(
        simple_graph,
        requests,
        use_evidence_engine=True
    )

    assert program1["engine"] == "ValueEngine_v3"
    assert program1["use_evidence_engine"] == True
    assert len(program1["evidence_metrics"]) >= 1

    # EvidenceEngine 미사용
    results2, program2, _metric_evals2 = value_engine_with_evidence.evaluate_metrics(
        simple_graph,
        requests,
        use_evidence_engine=False
    )

    assert program2["use_evidence_engine"] == False
    assert len(program2["evidence_metrics"]) == 0



