"""World Engine Phase C 테스트

성능 최적화, 백엔드, 캐싱, 시계열 비교 검증

2025-12-11: World Engine v2.0 Phase C
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from cmis_core.types import RealityGraphSnapshot, FocalActorContext
from cmis_core.graph import InMemoryGraph
from cmis_core.reality_graph_backend import RealityGraphBackend, GraphCache
from cmis_core.timeseries_comparator import TimeseriesComparator, compare_timeseries
from cmis_core.world_engine import WorldEngine


class TestRealityGraphBackend:
    """파일 시스템 백엔드 테스트"""

    def test_save_and_load_graph(self):
        """그래프 저장 및 로딩"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = RealityGraphBackend(Path(tmpdir))

            # 그래프 생성
            graph = InMemoryGraph()
            graph.upsert_node("ACT-001", "actor", {"name": "Test Actor"})

            meta = {
                "domain_id": "Test_Domain",
                "region": "KR"
            }

            # 저장
            backend.save_graph("Test_Domain", graph, meta)

            # 로딩
            result = backend.load_graph("Test_Domain")

            assert result is not None
            loaded_graph, loaded_meta = result

            assert len(list(loaded_graph.nodes_by_type("actor"))) == 1
            assert loaded_meta["domain_id"] == "Test_Domain"

    def test_has_domain(self):
        """도메인 존재 여부"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = RealityGraphBackend(Path(tmpdir))

            graph = InMemoryGraph()
            meta = {"domain_id": "Test"}

            backend.save_graph("Test", graph, meta)

            assert backend.has_domain("Test")
            assert not backend.has_domain("NonExistent")

    def test_query_by_region(self):
        """지역별 쿼리"""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = RealityGraphBackend(Path(tmpdir))

            # KR 도메인 2개
            for i in range(1, 3):
                graph = InMemoryGraph()
                meta = {"domain_id": f"KR_Domain_{i}", "region": "KR"}
                backend.save_graph(f"KR_Domain_{i}", graph, meta)

            # US 도메인 1개
            graph = InMemoryGraph()
            meta = {"domain_id": "US_Domain_1", "region": "US"}
            backend.save_graph("US_Domain_1", graph, meta)

            # 쿼리
            kr_domains = backend.query_by_region("KR")

            assert len(kr_domains) == 2
            assert "KR_Domain_1" in kr_domains
            assert "KR_Domain_2" in kr_domains


class TestGraphCache:
    """캐시 테스트"""

    def test_cache_put_get(self):
        """캐시 저장 및 조회"""
        cache = GraphCache(ttl_seconds=60)

        snapshot = RealityGraphSnapshot(
            graph=InMemoryGraph(),
            meta={"domain_id": "Test"}
        )

        cache_key = cache.get_cache_key("Test", "KR", None, None, None)

        # 저장
        cache.put(cache_key, snapshot)

        # 조회
        cached = cache.get(cache_key)

        assert cached is not None
        assert cached.meta["domain_id"] == "Test"

    def test_cache_ttl_expiration(self):
        """TTL 만료"""
        cache = GraphCache(ttl_seconds=0)  # 즉시 만료

        snapshot = RealityGraphSnapshot(
            graph=InMemoryGraph(),
            meta={"domain_id": "Test"}
        )

        cache_key = "test_key"
        cache.put(cache_key, snapshot)

        # 즉시 만료되어야 함
        import time
        time.sleep(0.1)

        cached = cache.get(cache_key)
        assert cached is None

    def test_cache_invalidate(self):
        """캐시 무효화"""
        cache = GraphCache()

        snapshot = RealityGraphSnapshot(
            graph=InMemoryGraph(),
            meta={"domain_id": "Test"}
        )

        cache_key = cache.get_cache_key("Test", "KR", None, None, None)
        cache.put(cache_key, snapshot)

        # 무효화
        cache.invalidate("Test")

        # 조회 실패
        cached = cache.get(cache_key)
        assert cached is None


class TestSliceSpec:
    """slice_spec 커스터마이즈 테스트"""

    def test_slice_spec_n_hops(self, project_root):
        """n_hops 커스터마이즈"""
        engine = WorldEngine(project_root)

        # FocalActorContext 설정
        project_context = FocalActorContext(
            project_context_id="PRJ-hops",
            scope={},
            assets_profile={}
        )

        engine.ingest_focal_actor_context(project_context)

        # 3-hop snapshot
        snapshot = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            project_context_id="PRJ-hops",
            slice_spec={"n_hops": 3}
        )

        assert snapshot.graph is not None
        # 3-hop이므로 더 많은 노드 포함 가능

    def test_slice_spec_exclude_competitors(self, project_root):
        """경쟁사 제외 옵션"""
        engine = WorldEngine(project_root)

        project_context = FocalActorContext(
            project_context_id="PRJ-no-comp",
            scope={},
            assets_profile={}
        )

        engine.ingest_focal_actor_context(project_context)

        # 경쟁사 제외
        snapshot = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR",
            project_context_id="PRJ-no-comp",
            slice_spec={"include_competitors": False}
        )

        assert snapshot.graph is not None


class TestTimeseriesComparator:
    """시계열 비교 테스트"""

    def test_compare_snapshots_basic(self):
        """기본 시계열 비교"""
        comparator = TimeseriesComparator()

        # 2개 시점 snapshot
        snap1 = RealityGraphSnapshot(
            graph=InMemoryGraph(),
            meta={"as_of": "2023"}
        )

        snap2 = RealityGraphSnapshot(
            graph=InMemoryGraph(),
            meta={"as_of": "2024"}
        )

        # State 추가
        snap1.graph.upsert_node(
            "STATE-001",
            "state",
            {"properties": {"revenue": 100}}
        )

        snap2.graph.upsert_node(
            "STATE-002",
            "state",
            {"properties": {"revenue": 150}}
        )

        # 비교
        result = comparator.compare_snapshots([snap1, snap2], metric_key="revenue")

        assert len(result["snapshots"]) == 2
        assert result["snapshots"][0]["total"] == 100
        assert result["snapshots"][1]["total"] == 150
        assert result["snapshots"][1]["growth_rate"] == 0.5  # 50% 성장

    def test_detect_structural_changes(self):
        """구조적 변화 탐지"""
        comparator = TimeseriesComparator()

        # 2023 snapshot
        graph1 = InMemoryGraph()
        graph1.upsert_node("ACT-001", "actor", {})
        graph1.upsert_node("ACT-002", "actor", {})

        snap1 = RealityGraphSnapshot(
            graph=graph1,
            meta={"as_of": "2023"}
        )

        # 2024 snapshot (ACT-003 추가, ACT-001 제거)
        graph2 = InMemoryGraph()
        graph2.upsert_node("ACT-002", "actor", {})
        graph2.upsert_node("ACT-003", "actor", {})

        snap2 = RealityGraphSnapshot(
            graph=graph2,
            meta={"as_of": "2024"}
        )

        # 변화 탐지
        changes = comparator.detect_structural_changes(snap1, snap2)

        assert changes["actors"]["new"] == 1
        assert changes["actors"]["removed"] == 1
        assert "ACT-003" in changes["actors"]["new_ids"]


class TestWorldEnginePhaseC:
    """World Engine Phase C 통합 테스트"""

    def test_world_engine_with_backend(self, project_root):
        """백엔드 사용 WorldEngine"""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = WorldEngine(
                project_root,
                use_backend=True,
                use_cache=False  # 테스트에서 캐시 비활성화
            )

            # Backend 설정 (임시 디렉토리)
            from cmis_core.reality_graph_backend import RealityGraphBackend
            engine.reality_store.backend = RealityGraphBackend(Path(tmpdir))
            engine.reality_store.use_backend = True

            # snapshot (seed ingestion)
            snapshot = engine.snapshot(
                domain_id="Adult_Language_Education_KR",
                region="KR"
            )

            assert snapshot.graph is not None

            # 백엔드에 저장되었는지 확인
            backend_check = engine.reality_store.backend.has_domain("Adult_Language_Education_KR")
            assert backend_check

    def test_world_engine_with_cache(self, project_root):
        """캐시 사용 WorldEngine"""
        engine = WorldEngine(
            project_root,
            use_backend=False,
            use_cache=True,
            cache_ttl=60
        )

        # 첫 번째 snapshot (캐시 miss)
        snapshot1 = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR"
        )

        # 두 번째 snapshot (캐시 hit)
        snapshot2 = engine.snapshot(
            domain_id="Adult_Language_Education_KR",
            region="KR"
        )

        # 같은 결과 (캐시에서)
        assert snapshot1.meta["domain_id"] == snapshot2.meta["domain_id"]


class TestIntegrationPhaseC:
    """Phase C 통합 테스트"""

    def test_full_workflow_with_cache_and_backend(self, project_root):
        """백엔드 + 캐시 전체 워크플로우"""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = WorldEngine(
                project_root,
                use_backend=True,
                use_cache=True
            )

            # Backend 임시 설정
            from cmis_core.reality_graph_backend import RealityGraphBackend
            engine.reality_store.backend = RealityGraphBackend(Path(tmpdir))

            # snapshot
            snapshot = engine.snapshot(
                domain_id="Adult_Language_Education_KR",
                region="KR",
                as_of="latest"
            )

            assert snapshot.graph is not None



