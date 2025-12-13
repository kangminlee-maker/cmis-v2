"""World Engine Phase B 테스트

ingest_evidence, ActorResolver, EvidenceMapper 검증

2025-12-11: World Engine v2.0 Phase B
"""

import pytest
from datetime import datetime

from cmis_core.types import EvidenceRecord, FocalActorContext
from cmis_core.graph import InMemoryGraph, Node
from cmis_core.actor_resolver import ActorResolver
from cmis_core.evidence_mapper import EvidenceMapper
from cmis_core.reality_graph_store import RealityGraphStore
from cmis_core.world_engine import WorldEngine


class TestActorResolver:
    """ActorResolver 테스트"""

    def test_resolve_by_crn(self):
        """사업자등록번호로 식별"""
        graph = InMemoryGraph()
        graph.upsert_node(
            "ACT-001",
            "actor",
            {"name": "회사A", "traits": {"company_registration_number": "123-45-67890"}}
        )

        resolver = ActorResolver(graph)

        actor_id, is_new = resolver.resolve_actor_id({
            "company_registration_number": "123-45-67890"
        })

        assert actor_id == "ACT-001"
        assert is_new is False

    def test_resolve_by_stock_code(self):
        """증권코드로 식별"""
        graph = InMemoryGraph()
        graph.upsert_node(
            "ACT-002",
            "actor",
            {"name": "회사B", "traits": {"stock_code": "005930"}}
        )

        resolver = ActorResolver(graph)

        actor_id, is_new = resolver.resolve_actor_id({
            "stock_code": "005930"
        })

        assert actor_id == "ACT-002"
        assert is_new is False

    def test_resolve_by_fuzzy_matching(self):
        """Fuzzy matching으로 식별"""
        graph = InMemoryGraph()
        graph.upsert_node(
            "ACT-003",
            "actor",
            {"name": "삼성전자(주)"}
        )

        resolver = ActorResolver(graph)

        # 유사한 이름
        actor_id, is_new = resolver.resolve_actor_id({
            "company_name": "삼성전자 주식회사"
        })

        assert actor_id == "ACT-003"
        assert is_new is False

    def test_resolve_new_actor(self):
        """신규 Actor 생성 필요"""
        graph = InMemoryGraph()

        resolver = ActorResolver(graph)

        actor_id, is_new = resolver.resolve_actor_id({
            "company_name": "완전히 새로운 회사"
        })

        assert actor_id is None
        assert is_new is True

    def test_generate_new_actor_id(self):
        """신규 Actor ID 생성"""
        graph = InMemoryGraph()
        resolver = ActorResolver(graph)

        actor_id = resolver.generate_new_actor_id({
            "company_name": "테스트 회사"
        })

        assert actor_id.startswith("ACT-")
        assert "테스트회사" in actor_id or "test" in actor_id.lower()

    def test_merge_actor_data(self):
        """기존 Actor + 새 Evidence 병합"""
        graph = InMemoryGraph()
        existing = graph.upsert_node(
            "ACT-001",
            "actor",
            {
                "name": "회사A",
                "traits": {"industry": "education"},
                "lineage": {"from_evidence_ids": ["EVD-001"]}
            }
        )

        resolver = ActorResolver(graph)

        evidence = EvidenceRecord(
            evidence_id="EVD-002",
            source_tier="official",
            source_id="DART",
            value=1000000000,
            context={"domain_expertise": "edtech"},
            as_of="2025-12-01",
            timestamp="2025-12-01T10:00:00Z"
        )

        updated = resolver.merge_actor_data(existing, evidence)

        # traits 병합 확인
        assert updated.data["traits"]["industry"] == "education"  # 기존 유지
        assert updated.data["traits"]["domain_expertise"] == "edtech"  # 새로 추가

        # lineage 업데이트
        assert "EVD-002" in updated.data["lineage"]["from_evidence_ids"]


class TestEvidenceMapper:
    """EvidenceMapper 테스트"""

    def test_map_financial_statement(self):
        """재무제표 → State"""
        graph = InMemoryGraph()

        # 기존 Actor
        graph.upsert_node(
            "ACT-samsung",
            "actor",
            {"name": "삼성전자", "traits": {"stock_code": "005930"}}
        )

        resolver = ActorResolver(graph)
        mapper = EvidenceMapper(resolver)

        evidence = EvidenceRecord(
            evidence_id="EVD-financial-001",
            source_tier="official",
            source_id="KR_DART_filings",
            value=300000000000000,  # 300조
            context={
                "stock_code": "005930",
                "fiscal_year": "2024"
            },
            as_of="2024-12-31"
        )

        result = mapper.map_evidence(evidence)

        assert result is not None
        assert isinstance(result, Node)
        assert result.type == "state"
        assert result.data["target_id"] == "ACT-samsung"
        assert result.data["properties"]["revenue"] == 300000000000000

    def test_map_market_size(self):
        """시장규모 → State (market)"""
        graph = InMemoryGraph()
        resolver = ActorResolver(graph)
        mapper = EvidenceMapper(resolver)

        evidence = EvidenceRecord(
            evidence_id="EVD-market-001",
            source_tier="official",
            source_id="KOSIS",
            value=5000000000000,  # 5조
            metadata={"metric_id": "MET-Market_size"},
            context={
                "domain_id": "Adult_Language_Education",
                "region": "KR",
                "year": 2024
            },
            as_of="2024"
        )

        result = mapper.map_evidence(evidence)

        assert result is not None
        assert isinstance(result, Node)
        assert result.type == "state"
        assert "MARKET-" in result.id
        assert result.data["properties"]["market_size"] == 5000000000000

    def test_map_customer_count(self):
        """고객수 → State"""
        graph = InMemoryGraph()
        graph.upsert_node("ACT-001", "actor", {"name": "회사A"})

        resolver = ActorResolver(graph)
        mapper = EvidenceMapper(resolver)

        evidence = EvidenceRecord(
            evidence_id="EVD-customers-001",
            source_tier="search",
            source_id="google_search",
            value=150000,
            metadata={"metric_id": "MET-N_customers"},
            context={"company_name": "회사A"},
            as_of="2025-12-01"
        )

        result = mapper.map_evidence(evidence)

        assert result is not None
        assert result.type == "state"
        assert result.data["properties"]["n_customers"] == 150000


class TestIngestEvidence:
    """ingest_evidence 통합 테스트"""

    def test_ingest_single_evidence(self):
        """단일 Evidence 수집"""
        store = RealityGraphStore()

        evidence = EvidenceRecord(
            evidence_id="EVD-test-001",
            source_tier="official",
            source_id="KOSIS",
            value=5000000000000,
            metadata={"metric_id": "MET-Market_size"},
            context={
                "domain_id": "Test_Market",
                "region": "KR",
                "year": 2024
            },
            as_of="2024"
        )

        updated_ids = store.ingest_evidence("Test_Domain", [evidence])

        assert len(updated_ids) >= 1

        graph = store.get_graph("Test_Domain")
        assert graph is not None

        states = list(graph.nodes_by_type("state"))
        assert len(states) >= 1

    def test_ingest_multiple_evidence(self):
        """여러 Evidence 동시 수집"""
        store = RealityGraphStore()

        evidence_list = [
            EvidenceRecord(
                evidence_id=f"EVD-{i}",
                source_tier="official",
                source_id="KOSIS",
                value=1000000000 * i,
                metadata={"metric_id": "MET-Market_size"},
                context={"domain_id": f"Market_{i}", "region": "KR"},
                as_of="2024"
            )
            for i in range(1, 4)
        ]

        updated_ids = store.ingest_evidence("Multi_Domain", evidence_list)

        assert len(updated_ids) >= 3

    def test_ingest_evidence_actor_creation(self):
        """Evidence로 Actor 신규 생성"""
        store = RealityGraphStore()

        # 회사 정보 Evidence
        evidence = EvidenceRecord(
            evidence_id="EVD-company-001",
            source_tier="search",
            source_id="google_search",
            value=100,  # 더미 값
            metadata={"metric_id": "MET-Revenue"},
            context={
                "company_name": "신규 스타트업",
                "industry": "edtech"
            },
            as_of="2025-12-01"
        )

        updated_ids = store.ingest_evidence("Test_Domain", [evidence])

        graph = store.get_graph("Test_Domain")

        # Actor 또는 State 생성 확인
        assert len(updated_ids) >= 1


class TestWorldEnginePhaseB:
    """World Engine Phase B 통합 테스트"""

    def test_ingest_evidence_api(self, project_root):
        """WorldEngine.ingest_evidence API"""
        engine = WorldEngine(project_root)

        evidence = EvidenceRecord(
            evidence_id="EVD-test",
            source_tier="official",
            source_id="KOSIS",
            value=3000000000000,
            metadata={"metric_id": "MET-Market_size"},
            context={"domain_id": "Test", "region": "KR"},
            as_of="2024"
        )

        updated_ids = engine.ingest_evidence(
            "Test_Domain",
            [evidence]
        )

        assert len(updated_ids) >= 1

    def test_snapshot_after_ingest_evidence(self, project_root):
        """ingest_evidence 후 snapshot"""
        engine = WorldEngine(project_root)

        # Evidence 수집
        evidence = EvidenceRecord(
            evidence_id="EVD-market",
            source_tier="official",
            source_id="KOSIS",
            value=5000000000000,
            metadata={"metric_id": "MET-Market_size"},
            context={"domain_id": "Dynamic_Market", "region": "KR", "year": 2024},
            as_of="2024"
        )

        engine.ingest_evidence("Dynamic_Market", [evidence])

        # snapshot 생성
        snapshot = engine.snapshot("Dynamic_Market", "KR")

        assert snapshot.graph is not None

        states = list(snapshot.graph.nodes_by_type("state"))
        assert len(states) >= 1

    def test_evidence_to_r_graph_to_pattern(self, project_root):
        """Evidence → R-Graph → Pattern 전체 파이프라인"""
        from cmis_core.pattern_engine_v2 import PatternEngineV2

        engine = WorldEngine(project_root)
        pattern_engine = PatternEngineV2()

        # 1. Evidence 수집 (구독 모델 시사)
        evidence_list = [
            EvidenceRecord(
                evidence_id="EVD-revenue",
                source_tier="official",
                source_id="internal_db",
                value=1000000000,
                metadata={"metric_id": "MET-Revenue"},
                context={"company_name": "구독 서비스 회사", "year": 2024},
                as_of="2024-12-31"
            )
        ]

        # 추가: MoneyFlow 생성을 위한 더미 데이터
        # (Phase B에서는 간단한 State만 생성하므로 패턴 매칭은 제한적)

        engine.ingest_evidence("Subscription_Market", evidence_list)

        # 2. snapshot
        snapshot = engine.snapshot("Subscription_Market", "KR")

        # 3. Pattern 매칭 (제한적)
        # State만 있으므로 대부분 패턴은 매칭 안 됨
        matches = pattern_engine.match_patterns(snapshot.graph)

        # 검증: 파이프라인 작동 확인
        assert snapshot.graph is not None


class TestLineageTracking:
    """Lineage 추적 테스트"""

    def test_evidence_lineage_in_state(self):
        """State 노드의 lineage"""
        store = RealityGraphStore()

        evidence = EvidenceRecord(
            evidence_id="EVD-lineage-001",
            source_tier="official",
            source_id="KOSIS",
            value=1000000000,
            metadata={"metric_id": "MET-Market_size"},
            context={"domain_id": "Test", "region": "KR"},
            as_of="2024"
        )

        store.ingest_evidence("Test_Domain", [evidence])

        graph = store.get_graph("Test_Domain")
        states = list(graph.nodes_by_type("state"))

        assert len(states) >= 1

        state = states[0]
        assert "lineage" in state.data
        assert "from_evidence_ids" in state.data["lineage"]
        assert "EVD-lineage-001" in state.data["lineage"]["from_evidence_ids"]

    def test_multiple_evidence_lineage(self):
        """여러 Evidence로 업데이트 시 lineage 누적"""
        graph = InMemoryGraph()
        graph.upsert_node(
            "ACT-multi",
            "actor",
            {
                "name": "회사",
                "traits": {},
                "lineage": {"from_evidence_ids": ["EVD-001"]}
            }
        )

        resolver = ActorResolver(graph)

        evidence1 = EvidenceRecord(
            evidence_id="EVD-002",
            source_tier="official",
            source_id="DART",
            value=100,
            context={"company_name": "회사"},
            timestamp="2025-12-01T10:00:00Z"
        )

        evidence2 = EvidenceRecord(
            evidence_id="EVD-003",
            source_tier="search",
            source_id="google",
            value=200,
            context={"company_name": "회사"},
            timestamp="2025-12-01T11:00:00Z"
        )

        existing = graph.get_node("ACT-multi")

        updated1 = resolver.merge_actor_data(existing, evidence1)
        updated2 = resolver.merge_actor_data(updated1, evidence2)

        # 3개 Evidence 모두 lineage에 있어야 함
        evidence_ids = updated2.data["lineage"]["from_evidence_ids"]
        assert "EVD-001" in evidence_ids
        assert "EVD-002" in evidence_ids
        assert "EVD-003" in evidence_ids


class TestConflictResolution:
    """Conflict 해결 테스트"""

    def test_trait_conflict_latest_wins(self):
        """Trait conflict: 최신 Evidence 우선"""
        graph = InMemoryGraph()
        existing = graph.upsert_node(
            "ACT-conflict",
            "actor",
            {
                "traits": {"industry": "old_value"},
                "last_updated": "2024-01-01"
            }
        )

        resolver = ActorResolver(graph)

        # 더 최신 Evidence
        new_evidence = EvidenceRecord(
            evidence_id="EVD-new",
            source_tier="official",
            source_id="DART",
            value=100,
            context={"industry": "new_value"},
            as_of="2025-01-01",
            timestamp="2025-01-01T10:00:00Z"
        )

        updated = resolver.merge_actor_data(existing, new_evidence)

        # 최신 값으로 업데이트
        assert updated.data["traits"]["industry"] == "new_value"

    def test_trait_no_conflict_merge(self):
        """Trait 충돌 없음: 합집합"""
        graph = InMemoryGraph()
        existing = graph.upsert_node(
            "ACT-merge",
            "actor",
            {"traits": {"industry": "education"}}
        )

        resolver = ActorResolver(graph)

        evidence = EvidenceRecord(
            evidence_id="EVD-merge",
            source_tier="search",
            source_id="google",
            value=100,
            context={"domain_expertise": "edtech"},  # 다른 key
            timestamp="2025-12-01T10:00:00Z"
        )

        updated = resolver.merge_actor_data(existing, evidence)

        # 두 trait 모두 있어야 함
        assert updated.data["traits"]["industry"] == "education"
        assert updated.data["traits"]["domain_expertise"] == "edtech"


class TestIntegrationPhaseB:
    """Phase B 통합 테스트"""

    def test_evidence_to_snapshot_workflow(self, project_root):
        """Evidence → ingest_evidence → snapshot 전체 워크플로우"""
        engine = WorldEngine(project_root)

        # 1. Evidence 수집 (서로 다른 도메인/연도)
        evidence_list = [
            EvidenceRecord(
                evidence_id="EVD-1",
                source_tier="official",
                source_id="KOSIS",
                value=1000000000,
                metadata={"metric_id": "MET-Market_size"},
                context={
                    "domain_id": "Market_A",
                    "region": "KR",
                    "year": 2022
                },
                as_of="2022"
            ),
            EvidenceRecord(
                evidence_id="EVD-2",
                source_tier="official",
                source_id="KOSIS",
                value=2000000000,
                metadata={"metric_id": "MET-Market_size"},
                context={
                    "domain_id": "Market_A",
                    "region": "KR",
                    "year": 2023
                },
                as_of="2023"
            ),
            EvidenceRecord(
                evidence_id="EVD-3",
                source_tier="official",
                source_id="KOSIS",
                value=3000000000,
                metadata={"metric_id": "MET-Market_size"},
                context={
                    "domain_id": "Market_A",
                    "region": "KR",
                    "year": 2024
                },
                as_of="2024"
            )
        ]

        # 2. ingest_evidence
        updated_ids = engine.ingest_evidence("Workflow_Test", evidence_list)

        assert len(updated_ids) >= 3

        # 3. snapshot
        snapshot = engine.snapshot("Workflow_Test", "KR")

        assert snapshot.graph is not None
        assert len(list(snapshot.graph.nodes_by_type("state"))) >= 3



