"""World Engine Phase A 테스트

RealityGraphStore, ProjectOverlay, 필터링, 서브그래프 추출 검증

2025-12-11: World Engine v2.0 Phase A
"""

import pytest
from datetime import datetime
from pathlib import Path

from cmis_core.types import FocalActorContext, RealityGraphSnapshot
from cmis_core.context_binding import FocalActorContextBinding
from cmis_core.graph import InMemoryGraph, Node
from cmis_core.reality_graph_store import (
    RealityGraphStore,
    apply_as_of_filter,
    apply_segment_filter
)
from cmis_core.project_overlay_store import (
    ProjectOverlayStore,
    ProjectOverlay,
    ingest_focal_actor_context,
    merge_graphs,
    extract_subgraph
)
from cmis_core.world_engine import WorldEngine


class TestRealityGraphStore:
    """RealityGraphStore 테스트"""

    def test_ingest_seed(self, project_root, seed_path):
        """seed YAML → RealityGraphStore"""
        store = RealityGraphStore()

        store.ingest_seed("Adult_Language_Education_KR", seed_path)

        assert store.has_domain("Adult_Language_Education_KR")

        graph = store.get_graph("Adult_Language_Education_KR")
        assert graph is not None
        assert len(list(graph.nodes_by_type("actor"))) > 0

        meta = store.get_meta("Adult_Language_Education_KR")
        assert meta["domain_id"] == "Adult_Language_Education_KR"
        assert "lineage" in meta

    def test_get_graph_not_found(self):
        """존재하지 않는 도메인"""
        store = RealityGraphStore()

        graph = store.get_graph("NonExistent")
        assert graph is None
        assert not store.has_domain("NonExistent")


class TestAsOfFilter:
    """as_of 필터링 테스트"""

    def test_as_of_filter_none(self):
        """as_of가 None이면 필터링 안 함"""
        graph = InMemoryGraph()

        graph.upsert_node("ACT-001", "actor", {"created_at": "2020-01-01"})
        graph.upsert_node("ACT-002", "actor", {"created_at": "2024-01-01"})

        filtered = apply_as_of_filter(graph, as_of=None)

        assert len(list(filtered.nodes_by_type("actor"))) == 2

    def test_as_of_filter_latest(self):
        """as_of='latest'는 현재 시점"""
        graph = InMemoryGraph()

        graph.upsert_node("ACT-001", "actor", {"created_at": "2020-01-01"})
        graph.upsert_node("ACT-002", "actor", {"created_at": "2030-01-01"})  # 미래

        filtered = apply_as_of_filter(graph, as_of="latest")

        actors = list(filtered.nodes_by_type("actor"))
        actor_ids = {a.id for a in actors}

        assert "ACT-001" in actor_ids
        # ACT-002는 미래라서 제외될 수 있음 (현재 날짜에 따라 다름)

    def test_as_of_filter_state(self):
        """State는 as_of 기준 최신만"""
        graph = InMemoryGraph()

        graph.upsert_node("ACT-001", "actor", {"created_at": "2020-01-01"})

        # 같은 Actor에 대한 여러 State
        graph.upsert_node(
            "STATE-001",
            "state",
            {"target_id": "ACT-001", "as_of": "2023-01-01", "properties": {"revenue": 100}}
        )
        graph.upsert_node(
            "STATE-002",
            "state",
            {"target_id": "ACT-001", "as_of": "2024-01-01", "properties": {"revenue": 200}}
        )
        graph.upsert_node(
            "STATE-003",
            "state",
            {"target_id": "ACT-001", "as_of": "2025-01-01", "properties": {"revenue": 300}}
        )

        # 2024-06-01 기준
        filtered = apply_as_of_filter(graph, as_of="2024-06-01")

        states = list(filtered.nodes_by_type("state"))

        # STATE-002만 포함 (2024-01-01이 2024-06-01 이전 중 최신)
        assert len(states) == 1
        assert states[0].id == "STATE-002"
        assert states[0].data["properties"]["revenue"] == 200

    def test_as_of_filter_money_flow(self):
        """MoneyFlow는 timestamp 기준"""
        graph = InMemoryGraph()

        graph.upsert_node("ACT-001", "actor", {})
        graph.upsert_node("ACT-002", "actor", {})

        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"payer_id": "ACT-001", "payee_id": "ACT-002", "timestamp": "2023-01-01"}
        )
        graph.upsert_node(
            "MFL-002",
            "money_flow",
            {"payer_id": "ACT-001", "payee_id": "ACT-002", "timestamp": "2025-01-01"}
        )

        # 2024-01-01 기준
        filtered = apply_as_of_filter(graph, as_of="2024-01-01")

        money_flows = list(filtered.nodes_by_type("money_flow"))
        mf_ids = {mf.id for mf in money_flows}

        assert "MFL-001" in mf_ids  # 2023 포함
        assert "MFL-002" not in mf_ids  # 2025 제외


class TestSegmentFilter:
    """segment 필터링 테스트"""

    def test_segment_filter_none(self):
        """segment가 None이면 필터링 안 함"""
        graph = InMemoryGraph()

        graph.upsert_node("ACT-001", "actor", {"kind": "customer_segment"})
        graph.upsert_node("ACT-002", "actor", {"kind": "company"})

        filtered = apply_segment_filter(graph, segment=None)

        assert len(list(filtered.nodes_by_type("actor"))) == 2

    def test_segment_filter_customer_segment(self):
        """customer_segment kind + segment trait"""
        graph = InMemoryGraph()

        graph.upsert_node(
            "ACT-CS-01",
            "actor",
            {"kind": "customer_segment", "traits": {"segment": "office_worker"}}
        )
        graph.upsert_node(
            "ACT-CS-02",
            "actor",
            {"kind": "customer_segment", "traits": {"segment": "student"}}
        )
        graph.upsert_node(
            "ACT-COMPANY",
            "actor",
            {"kind": "company", "name": "교육 회사"}
        )

        # MoneyFlow: office_worker → 교육 회사
        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"payer_id": "ACT-CS-01", "payee_id": "ACT-COMPANY", "timestamp": "2024-01-01"}
        )

        # office_worker segment 필터
        filtered = apply_segment_filter(graph, segment="office_worker")

        actors = list(filtered.nodes_by_type("actor"))
        actor_ids = {a.id for a in actors}

        assert "ACT-CS-01" in actor_ids  # office_worker 세그먼트
        assert "ACT-COMPANY" in actor_ids  # 거래 상대방
        assert "ACT-CS-02" not in actor_ids  # student 세그먼트 (제외)

        # MoneyFlow도 포함
        money_flows = list(filtered.nodes_by_type("money_flow"))
        assert len(money_flows) == 1


class TestProjectOverlay:
    """ProjectOverlay 테스트"""

    def test_create_overlay(self):
        """Overlay 생성"""
        store = ProjectOverlayStore()

        overlay = store.create_overlay("PRJ-001", "ACT-my-company")

        assert overlay.focal_actor_context_id == "PRJ-001"
        assert overlay.focal_actor_id == "ACT-my-company"
        assert len(overlay.nodes) == 0

    def test_overlay_add_nodes(self):
        """Overlay에 노드 추가"""
        overlay = ProjectOverlay("PRJ-001", "ACT-my-company")

        node = Node(
            id="ACT-my-company",
            type="actor",
            data={"name": "My Company"}
        )

        overlay.add_node(node)

        assert len(overlay.nodes) == 1

        graph = overlay.to_graph()
        assert len(list(graph.nodes_by_type("actor"))) == 1


class TestIngestFocalActorContext:
    """ingest_focal_actor_context 테스트"""

    def test_ingest_basic(self):
        """기본 FocalActorContext → Overlay"""
        project_context = FocalActorContext(
            focal_actor_context_id="PRJ-test",
            scope={"domain_id": "test", "region": "KR"},
            assets_profile={
                "capability_traits": [
                    {"technology_domain": "AI_ML", "maturity_level": "mvp"}
                ],
                "channels": [
                    {"channel_type": "online", "reach": 5000}
                ]
            }
        )

        store = ProjectOverlayStore()
        focal_actor_id, updated_ids = ingest_focal_actor_context(FocalActorContextBinding.from_record(project_context), store)

        assert focal_actor_id == "ACT-PRJ-test"
        assert len(updated_ids) > 0

        overlay = store.get_overlay("PRJ-test")
        assert overlay is not None
        assert overlay.focal_actor_id == focal_actor_id

    def test_ingest_with_baseline_state(self):
        """baseline_state 포함"""
        project_context = FocalActorContext(
            focal_actor_context_id="PRJ-test",
            scope={},
            assets_profile={},
            baseline_state={
                "current_revenue": 1000000000,
                "current_customers": 10000,
                "margin_structure": {"gross_margin": 0.7},
                "as_of": "2025-12-01"
            }
        )

        store = ProjectOverlayStore()
        focal_actor_id, updated_ids = ingest_focal_actor_context(FocalActorContextBinding.from_record(project_context), store)

        overlay = store.get_overlay("PRJ-test")

        # baseline_state → State 노드 확인
        state_nodes = [n for n in overlay.nodes if n.type == "state" and "baseline" in n.id]
        assert len(state_nodes) == 1

        state = state_nodes[0]
        assert state.data["properties"]["revenue"] == 1000000000
        assert state.data["properties"]["n_customers"] == 10000
        assert state.data["properties"]["gross_margin"] == 0.7


class TestMergeGraphs:
    """그래프 병합 테스트"""

    def test_merge_basic(self):
        """기본 그래프 병합"""
        base_graph = InMemoryGraph()
        base_graph.upsert_node("ACT-001", "actor", {"name": "Company A"})

        overlay = ProjectOverlay("PRJ-001", "ACT-my-company")
        overlay.add_node(Node(
            id="ACT-my-company",
            type="actor",
            data={"name": "My Company"}
        ))

        merged = merge_graphs(base_graph, overlay)

        actors = list(merged.nodes_by_type("actor"))
        assert len(actors) == 2

        actor_ids = {a.id for a in actors}
        assert "ACT-001" in actor_ids
        assert "ACT-my-company" in actor_ids


class TestExtractSubgraph:
    """서브그래프 추출 테스트"""

    def test_extract_1hop(self):
        """1-hop 서브그래프"""
        graph = InMemoryGraph()

        # focal_actor
        graph.upsert_node("ACT-focal", "actor", {})

        # 1-hop 이웃
        graph.upsert_node("ACT-001", "actor", {})
        graph.upsert_node("ACT-002", "actor", {})

        # 2-hop 이웃
        graph.upsert_node("ACT-003", "actor", {})

        # Edges
        graph.add_edge("actor_pays_actor", "ACT-focal", "ACT-001")
        graph.add_edge("actor_competes_with_actor", "ACT-focal", "ACT-002")
        graph.add_edge("actor_pays_actor", "ACT-001", "ACT-003")  # 2-hop

        # 1-hop 추출
        subgraph = extract_subgraph(graph, "ACT-focal", n_hops=1)

        actors = list(subgraph.nodes_by_type("actor"))
        actor_ids = {a.id for a in actors}

        assert "ACT-focal" in actor_ids
        assert "ACT-001" in actor_ids
        assert "ACT-002" in actor_ids
        assert "ACT-003" not in actor_ids  # 2-hop이라서 제외

    def test_extract_2hop(self):
        """2-hop 서브그래프"""
        graph = InMemoryGraph()

        # focal_actor
        graph.upsert_node("ACT-focal", "actor", {})

        # 1-hop
        graph.upsert_node("ACT-001", "actor", {})

        # 2-hop
        graph.upsert_node("ACT-002", "actor", {})

        # 3-hop
        graph.upsert_node("ACT-003", "actor", {})

        # Edges
        graph.add_edge("actor_pays_actor", "ACT-focal", "ACT-001")
        graph.add_edge("actor_pays_actor", "ACT-001", "ACT-002")
        graph.add_edge("actor_pays_actor", "ACT-002", "ACT-003")

        # 2-hop 추출
        subgraph = extract_subgraph(graph, "ACT-focal", n_hops=2)

        actors = list(subgraph.nodes_by_type("actor"))
        actor_ids = {a.id for a in actors}

        assert "ACT-focal" in actor_ids
        assert "ACT-001" in actor_ids
        assert "ACT-002" in actor_ids
        assert "ACT-003" not in actor_ids  # 3-hop

    def test_extract_with_money_flow(self):
        """focal_actor의 MoneyFlow 포함"""
        graph = InMemoryGraph()

        graph.upsert_node("ACT-focal", "actor", {})
        graph.upsert_node("ACT-001", "actor", {})

        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"payer_id": "ACT-focal", "payee_id": "ACT-001", "timestamp": "2024-01-01"}
        )

        graph.add_edge("actor_pays_actor", "ACT-focal", "ACT-001")

        subgraph = extract_subgraph(graph, "ACT-focal", n_hops=1)

        # MoneyFlow 포함 확인
        money_flows = list(subgraph.nodes_by_type("money_flow"))
        assert len(money_flows) == 1
        assert money_flows[0].id == "MFL-001"

    def test_extract_with_state(self):
        """focal_actor의 State 포함"""
        graph = InMemoryGraph()

        graph.upsert_node("ACT-focal", "actor", {})

        graph.upsert_node(
            "STATE-001",
            "state",
            {"target_id": "ACT-focal", "as_of": "2024-01-01", "properties": {"revenue": 100}}
        )

        subgraph = extract_subgraph(graph, "ACT-focal", n_hops=1)

        # State 포함 확인
        states = list(subgraph.nodes_by_type("state"))
        assert len(states) == 1
        assert states[0].id == "STATE-001"


class TestWorldEnginePhaseA:
    """World Engine Phase A 통합 테스트"""

    def test_snapshot_with_as_of_filter(self, project_root):
        """as_of 필터링 snapshot"""
        engine = WorldEngine(project_root)

        snapshot = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            as_of="2024-12-31"
        )

        assert snapshot.meta["as_of"] == "2024-12-31"
        assert snapshot.graph is not None

    def test_snapshot_greenfield(self, project_root):
        """Greenfield snapshot (project_context 없음)"""
        engine = WorldEngine(project_root)

        snapshot = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR"
        )

        assert snapshot.meta["focal_actor_context_id"] is None
        assert len(snapshot.graph.nodes) > 0

    def test_snapshot_brownfield(self, project_root):
        """Brownfield snapshot (project_context 있음)"""
        engine = WorldEngine(project_root)

        # 1. ingest_focal_actor_context
        project_context = FocalActorContext(
            focal_actor_context_id="PRJ-test",
            scope={"domain_id": "Adult_Language_Education_KR", "region": "KR"},
            assets_profile={
                "capability_traits": [
                    {"technology_domain": "platform_tech"}
                ]
            },
            baseline_state={
                "current_revenue": 1000000000,
                "current_customers": 10000,
                "as_of": "2025-12-01"
            }
        )

        focal_actor_id, updated_ids = engine.ingest_focal_actor_context(project_context)

        assert focal_actor_id == "ACT-PRJ-test"
        assert len(updated_ids) > 0

        # 2. snapshot (Brownfield)
        snapshot = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            focal_actor_context_id="PRJ-test",
        )

        assert snapshot.meta["focal_actor_context_id"] == "PRJ-test"

        # focal_actor 포함 확인
        actors = list(snapshot.graph.nodes_by_type("actor"))
        actor_ids = {a.id for a in actors}
        assert "ACT-PRJ-test" in actor_ids

        # baseline_state State 포함 확인
        states = list(snapshot.graph.nodes_by_type("state"))
        baseline_states = [s for s in states if "baseline" in s.id]
        assert len(baseline_states) >= 1

    def test_snapshot_with_all_filters(self, project_root):
        """모든 필터 동시 적용"""
        engine = WorldEngine(project_root)

        snapshot = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            segment="office_worker",
            as_of="2024-12-31"
        )

        assert snapshot.meta["segment"] == "office_worker"
        assert snapshot.meta["as_of"] == "2024-12-31"


class TestIntegrationPhaseA:
    """Phase A 통합 테스트"""

    def test_greenfield_to_brownfield(self, project_root):
        """Greenfield → Brownfield 전환"""
        engine = WorldEngine(project_root)

        # 1. Greenfield 분석
        greenfield_snapshot = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR"
        )

        greenfield_actor_count = len(list(greenfield_snapshot.graph.nodes_by_type("actor")))

        # 2. FocalActorContext 추가
        project_context = FocalActorContext(
            focal_actor_context_id="PRJ-transition",
            scope={},
            assets_profile={},
            baseline_state={
                "current_revenue": 500000000
            }
        )

        engine.ingest_focal_actor_context(project_context)

        # 3. Brownfield 분석
        brownfield_snapshot = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            focal_actor_context_id="PRJ-transition",
        )

        brownfield_actor_count = len(list(brownfield_snapshot.graph.nodes_by_type("actor")))

        # Brownfield는 focal_actor 추가 + 서브그래프 추출로 개수 변화
        # (작거나 같을 수 있음 - 서브그래프 추출 때문)
        assert brownfield_actor_count >= 1  # 최소 focal_actor

    def test_reality_store_reuse(self, project_root):
        """RealityGraphStore 재사용"""
        engine = WorldEngine(project_root)

        # 첫 번째 snapshot (seed 로딩)
        snapshot1 = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR"
        )

        # 두 번째 snapshot (재사용)
        snapshot2 = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            as_of="2024-01-01"
        )

        # 동일한 RealityGraphStore 사용 (재로딩 안 함)
        assert engine.reality_store.has_domain("Adult_Language_Education_KR")
