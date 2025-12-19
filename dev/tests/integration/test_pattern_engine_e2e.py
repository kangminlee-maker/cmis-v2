"""Pattern Engine E2E 테스트

전체 워크플로우 통합 테스트

2025-12-10: Phase 3
"""

import pytest

from cmis_core.pattern_engine_v2 import PatternEngineV2
from cmis_core.pattern_library import PatternLibrary
from cmis_core.pattern_benchmark import PatternBenchmarkProvider, estimate_metric_from_pattern
from cmis_core.context_archetype import ContextArchetypeLibrary
from cmis_core.graph import InMemoryGraph


class TestPhase3Complete:
    """Phase 3 완성도 테스트"""

    def test_23_patterns_loaded(self):
        """23개 Pattern 로딩 검증"""
        library = PatternLibrary()
        library.load_all()

        patterns = library.get_all()

        assert len(patterns) == 23

        # Family별 개수
        from collections import Counter
        families = Counter(p.family for p in patterns)

        assert families["business_model_patterns"] == 6
        assert families["value_chain_patterns"] == 5
        assert families["growth_mechanism_patterns"] == 5
        assert families["competitive_structure_patterns"] == 4
        assert families["revenue_architecture_patterns"] == 3

        print(f"23 patterns loaded successfully")

    def test_all_patterns_valid(self):
        """모든 Pattern 검증 통과"""
        library = PatternLibrary()
        library.load_all()

        for pattern in library.get_all():
            errors = library._validate_pattern_spec(pattern)
            assert len(errors) == 0, f"{pattern.pattern_id} validation failed: {errors}"

        print(f"All 23 patterns validated")

    def test_p_graph_compilation(self):
        """P-Graph 컴파일"""
        library = PatternLibrary()
        library.load_all()

        p_graph = library.compile_to_p_graph()

        # 23 pattern nodes + 5 family nodes
        assert len(p_graph.nodes) >= 28

        # Pattern 관계 edges
        assert len(p_graph.edges) > 0

        # Family 노드 확인
        families = p_graph.nodes_by_type("pattern_family")
        assert len(families) == 5

        # Pattern 노드 확인
        patterns = p_graph.nodes_by_type("pattern")
        assert len(patterns) == 23

        print(f"P-Graph: {len(p_graph.nodes)} nodes, {len(p_graph.edges)} edges")


class TestPatternBenchmark:
    """Pattern Benchmark 연동 테스트"""

    def test_get_prior_from_pattern(self):
        """Pattern에서 Prior 추출"""
        library = PatternLibrary()
        library.load_all()

        from cmis_core.types import PatternMatch

        # Subscription 패턴 매칭
        match = PatternMatch(
            pattern_id="PAT-subscription_model",
            description="Test",
            structure_fit_score=0.95,
            combined_score=0.95
        )

        provider = PatternBenchmarkProvider(library)

        # Churn rate prior
        prior = provider.get_prior_from_patterns("MET-Churn_rate", [match])

        assert prior is not None
        assert "min" in prior
        assert "max" in prior
        assert "typical" in prior
        assert prior["source"] == "pattern:PAT-subscription_model"
        assert prior["confidence"] == 0.95

        print(f"Churn rate prior: {prior}")

    def test_get_all_priors(self):
        """모든 Prior 추출"""
        library = PatternLibrary()
        library.load_all()

        from cmis_core.types import PatternMatch

        matches = [
            PatternMatch(
                pattern_id="PAT-subscription_model",
                description="Subscription",
                structure_fit_score=0.95,
                combined_score=0.95
            ),
            PatternMatch(
                pattern_id="PAT-platform_business_model",
                description="Platform",
                structure_fit_score=0.90,
                combined_score=0.90
            )
        ]

        provider = PatternBenchmarkProvider(library)
        priors = provider.get_all_priors_from_patterns(matches)

        # 여러 Metric에 대한 Prior가 있어야 함
        assert len(priors) > 0

        print(f"Total priors: {len(priors)}")
        for metric_id, prior in list(priors.items())[:3]:
            print(f"  {metric_id}: {prior.get('typical')}")


class TestWorkflowStructureAnalysis:
    """structure_analysis Workflow E2E"""

    def test_structure_analysis_workflow(self):
        """구조 분석 워크플로우"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 디지털 서비스 시장 구조
        graph.upsert_node(
            "RES-001",
            "resource",
            {"kind": "digital_service", "traits": {"delivery_channel": "online"}}
        )

        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True}}
        )

        graph.upsert_node(
            "ACT-001",
            "actor",
            {"kind": "company", "traits": {"institution_type": "online_platform"}}
        )

        # Step 1: Pattern Matching
        matches = engine.match_patterns(graph)

        assert len(matches) > 0

        # 예상 매칭: subscription, platform, asset_light, recurring 등
        matched_ids = [m.pattern_id for m in matches]

        print(f"Structure Analysis:")
        print(f"  Matched patterns: {len(matches)}")
        for match in matches[:5]:
            print(f"    {match.pattern_id}: {match.combined_score:.2f}")


class TestWorkflowOpportunityDiscovery:
    """opportunity_discovery Workflow E2E"""

    def test_opportunity_discovery_workflow(self):
        """기회 발굴 워크플로우"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 구조
        graph.upsert_node(
            "RES-001",
            "resource",
            {"kind": "digital_service", "traits": {"delivery_channel": "online"}}
        )

        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True}}
        )

        # Step 1: Pattern Matching
        matches = engine.match_patterns(graph)

        # Step 2: Gap Discovery (precomputed 재사용)
        gaps = engine.discover_gaps(graph, precomputed_matches=matches)

        assert len(gaps) > 0

        # Gap은 expected_level 정보를 가져야 함
        for gap in gaps[:5]:
            assert gap.expected_level in ["core", "common", "rare"]

        print(f"Opportunity Discovery:")
        print(f"  Matched: {len(matches)} patterns")
        print(f"  Gaps: {len(gaps)} opportunities")
        for gap in gaps[:5]:
            print(f"    {gap.pattern_id} ({gap.expected_level}, {gap.feasibility})")

    def test_gap_to_benchmark(self):
        """Gap Pattern의 Benchmark 조회"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 간단한 구조
        graph.upsert_node(
            "RES-001",
            "resource",
            {"kind": "digital_service"}
        )

        # Gap 발견
        matches = engine.match_patterns(graph)
        gaps = engine.discover_gaps(graph, precomputed_matches=matches)

        if len(gaps) > 0:
            gap = gaps[0]

            # Gap Pattern의 Benchmark 조회
            pattern = engine.get_pattern(gap.pattern_id)

            assert pattern is not None

            if pattern.benchmark_metrics:
                print(f"Gap pattern: {gap.pattern_id}")
                print(f"  Benchmark metrics: {pattern.benchmark_metrics}")


class TestE2EGreenfield:
    """Greenfield 전체 플로우"""

    def test_greenfield_analysis(self):
        """Greenfield 시장 분석"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 시장 구조 (여러 Pattern 매칭되도록)
        graph.upsert_node(
            "RES-digital",
            "resource",
            {"kind": "digital_service", "traits": {"delivery_channel": "online"}}
        )

        graph.upsert_node(
            "MFL-sub",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True, "recurrence": "monthly"}}
        )

        graph.upsert_node(
            "ACT-platform",
            "actor",
            {"kind": "company", "traits": {"institution_type": "online_platform"}}
        )

        # Pattern Matching (Greenfield: no Project Context)
        matches = engine.match_patterns(graph)

        # Gap Discovery
        gaps = engine.discover_gaps(graph, precomputed_matches=matches)

        # Greenfield 특성
        for match in matches:
            assert match.execution_fit_score is None
            assert match.combined_score == match.structure_fit_score

        for gap in gaps:
            assert gap.feasibility == "unknown"

        # Pattern Benchmark 조회
        provider = PatternBenchmarkProvider()
        priors = provider.get_all_priors_from_patterns(matches)

        print(f"Greenfield Analysis:")
        print(f"  Patterns: {len(matches)}")
        print(f"  Gaps: {len(gaps)}")
        print(f"  Benchmark Priors: {len(priors)}")


class TestE2EBrownfield:
    """Brownfield 전체 플로우"""

    def test_brownfield_analysis(self):
        """Brownfield 분석 (Project Context)"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 구조
        graph.upsert_node(
            "RES-001",
            "resource",
            {"kind": "digital_service"}
        )

        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True}}
        )

        focal_actor_context_id = "PRJ-brownfield-test"

        # Pattern Matching (Brownfield: with Project Context)
        matches = engine.match_patterns(graph, focal_actor_context_id)

        # Gap Discovery
        gaps = engine.discover_gaps(
            graph,
            focal_actor_context_id,
            precomputed_matches=matches
        )

        # Brownfield 특성
        for match in matches:
            # Execution Fit가 계산될 수 있음
            if match.execution_fit_score is not None:
                assert 0.0 <= match.execution_fit_score <= 1.0

        # Gap Feasibility 평가됨 (unknown 아닐 수 있음)

        print(f"Brownfield Analysis:")
        print(f"  Patterns: {len(matches)}")
        print(f"  Gaps: {len(gaps)}")
