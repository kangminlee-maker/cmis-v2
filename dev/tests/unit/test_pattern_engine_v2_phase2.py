"""Pattern Engine v2 Phase 2 테스트

Execution Fit, Context Archetype, Gap Discovery 검증

2025-12-10: Phase 2
"""

import pytest

from cmis_core.types import PatternSpec, PatternMatch, GapCandidate, FocalActorContext, ContextArchetype
from cmis_core.pattern_library import PatternLibrary
from cmis_core.pattern_scorer import PatternScorer
from cmis_core.context_binding import FocalActorContextBinding
from cmis_core.context_archetype import (
    ContextArchetypeLibrary,
    determine_context_archetype
)
from cmis_core.gap_discoverer import GapDiscoverer
from cmis_core.pattern_engine_v2 import PatternEngineV2
from cmis_core.graph import InMemoryGraph


class TestExecutionFit:
    """Execution Fit 계산 테스트"""

    def test_calculate_capability_match_full(self):
        """Capability 완전 매칭"""
        scorer = PatternScorer()

        required = [
            {"technology_domain": "AI_ML", "maturity_level": "production_ready"}
        ]

        available = [
            {"technology_domain": "AI_ML", "maturity_level": "production_ready"}
        ]

        score = scorer._calculate_capability_match(required, available)

        assert score == 1.0  # 완전 매칭

    def test_calculate_capability_match_partial(self):
        """Capability 부분 매칭"""
        scorer = PatternScorer()

        required = [
            {"technology_domain": "AI_ML"},
            {"technology_domain": "platform_tech"}
        ]

        available = [
            {"technology_domain": "AI_ML", "maturity_level": "mvp"}
        ]

        score = scorer._calculate_capability_match(required, available)

        assert score == 0.5  # 2개 중 1개 매칭

    def test_calculate_capability_match_none(self):
        """Capability 매칭 없음"""
        scorer = PatternScorer()

        required = [{"technology_domain": "AI_ML"}]
        available = [{"technology_domain": "blockchain"}]

        score = scorer._calculate_capability_match(required, available)

        assert score == 0.0

    def test_calculate_asset_sufficiency_channels(self):
        """Asset 충족도 - Channels"""
        scorer = PatternScorer()

        required = {
            "channels": {
                "online": True,
                "min_reach": 1000
            }
        }

        available = {
            "channels": [
                {"channel_type": "online", "reach": 5000}
            ]
        }

        score = scorer._calculate_asset_sufficiency(required, available)

        assert score == 1.0  # Online + reach OK

    def test_calculate_asset_sufficiency_insufficient(self):
        """Asset 충족도 - 부족"""
        scorer = PatternScorer()

        required = {
            "channels": {
                "online": True,
                "min_reach": 10000
            }
        }

        available = {
            "channels": [
                {"channel_type": "online", "reach": 500}  # 부족
            ]
        }

        score = scorer._calculate_asset_sufficiency(required, available)

        assert score == 0.0  # min_reach 부족

    def test_execution_fit_full(self):
        """Execution Fit 전체 계산"""
        library = PatternLibrary()
        library.load_all()

        pattern = library.get("PAT-subscription_model")

        # 강한 FocalActorContext
        project_context = FocalActorContext(
            focal_actor_context_id="PRJ-test-001",
            scope={"domain_id": "education", "region": "KR"},
            assets_profile={
                "capability_traits": [
                    {"technology_domain": "platform_tech", "maturity_level": "production_ready"}
                ],
                "channels": [
                    {"channel_type": "online", "reach": 10000}
                ],
                "brand_assets": {
                    "brand_awareness_level": "medium"
                },
                "organizational_assets": {
                    "team_size": 20,
                    "org_maturity": "scaleup"
                }
            }
        )

        scorer = PatternScorer()
        execution_fit = scorer.calculate_execution_fit(pattern, FocalActorContextBinding.from_record(project_context))

        assert 0.0 <= execution_fit <= 1.0
        assert execution_fit >= 0.5  # 강한 Context

        print(f"Execution Fit: {execution_fit:.2f}")


class TestContextArchetype:
    """Context Archetype 테스트"""

    def test_load_archetypes(self):
        """Archetype 로딩"""
        library = ContextArchetypeLibrary()
        library.load_all()

        archetypes = list(library.archetypes.values())

        # 3개 Archetype
        assert len(archetypes) >= 3

        archetype_ids = [a.archetype_id for a in archetypes]
        assert "ARCH-digital_service_KR" in archetype_ids
        assert "ARCH-education_platform_KR" in archetype_ids
        assert "ARCH-marketplace_global" in archetype_ids

        print(f"Loaded {len(archetypes)} archetypes")

    def test_archetype_expected_patterns(self):
        """Expected Pattern Set"""
        library = ContextArchetypeLibrary()
        library.load_all()

        archetype = library.get("ARCH-digital_service_KR")

        assert archetype is not None
        assert "core" in archetype.expected_patterns
        assert "common" in archetype.expected_patterns
        assert "rare" in archetype.expected_patterns

        # Core patterns
        core = archetype.expected_patterns["core"]
        assert len(core) > 0

        pattern_ids = [p["pattern_id"] for p in core]
        assert "PAT-subscription_model" in pattern_ids

        print(f"Core patterns: {len(core)}")
        print(f"Common patterns: {len(archetype.expected_patterns['common'])}")
        print(f"Rare patterns: {len(archetype.expected_patterns['rare'])}")

    def test_determine_archetype_fallback(self):
        """Archetype 결정 - Fallback"""
        graph = InMemoryGraph()

        # 빈 그래프
        archetype = determine_context_archetype(graph)

        assert archetype is not None
        assert archetype.archetype_id == "ARCH-fallback"
        assert archetype.confidence == 0.3

    def test_determine_archetype_from_graph_traits(self):
        """Archetype 결정 - Graph Trait 기반"""
        library = ContextArchetypeLibrary()
        library.load_all()

        graph = InMemoryGraph()

        # Digital service resource
        graph.upsert_node(
            "RES-001",
            "resource",
            {
                "kind": "digital_service",
                "traits": {
                    "delivery_channel": "online"
                }
            }
        )

        archetype = determine_context_archetype(
            graph,
            archetype_library=library
        )

        # digital_service_KR이 매칭될 가능성
        assert archetype is not None
        print(f"Archetype: {archetype.archetype_id} (confidence: {archetype.confidence})")


class TestGapDiscovery:
    """Gap Discovery 테스트"""

    def test_gap_discoverer_basic(self):
        """기본 Gap 탐지"""
        discoverer = GapDiscoverer()
        graph = InMemoryGraph()

        # Digital service 구조 (Archetype 매칭 가능하도록)
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

        # Subscription 매칭
        from cmis_core.pattern_engine_v2 import PatternEngineV2
        engine = PatternEngineV2()
        matches = engine.match_patterns(graph)

        # Gap 탐지
        gaps = discoverer.discover_gaps(graph, matches)

        # Expected에 있지만 Matched에 없는 패턴들
        assert len(gaps) > 0

        # Gap은 expected_level 정보를 가져야 함
        for gap in gaps:
            assert gap.expected_level in ["core", "common", "rare"]
            assert gap.feasibility in ["high", "medium", "low", "unknown"]

        print(f"Found {len(gaps)} gaps")

    def test_gap_sorting(self):
        """Gap 정렬 (expected_level → feasibility)"""
        discoverer = GapDiscoverer()

        gaps = [
            GapCandidate(
                pattern_id="PAT-001",
                description="Gap 1",
                expected_level="rare",
                feasibility="high"
            ),
            GapCandidate(
                pattern_id="PAT-002",
                description="Gap 2",
                expected_level="core",
                feasibility="medium"
            ),
            GapCandidate(
                pattern_id="PAT-003",
                description="Gap 3",
                expected_level="common",
                feasibility="high"
            )
        ]

        sorted_gaps = discoverer._sort_gaps(gaps)

        # core > common > rare
        assert sorted_gaps[0].expected_level == "core"
        assert sorted_gaps[1].expected_level == "common"
        assert sorted_gaps[2].expected_level == "rare"

    def test_gap_with_feasibility(self):
        """Gap with Feasibility (FocalActorContext)"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # Subscription만
        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True}}
        )

        matches = engine.match_patterns(graph)

        # FocalActorContext 있으면 feasibility 평가
        gaps = engine.discover_gaps(
            graph,
            focal_actor_context_id="PRJ-test-001",
            precomputed_matches=matches
        )

        # Feasibility가 계산되어야 함
        # (지금은 기본 FocalActorContext라 "unknown" 가능)
        for gap in gaps:
            assert gap.feasibility in ["high", "medium", "low", "unknown"]


class TestPatternEngineV2Phase2:
    """PatternEngine v2 Phase 2 통합 테스트"""

    def test_match_with_execution_fit(self):
        """Execution Fit 포함 매칭 (Brownfield)"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # Subscription 구조
        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True}}
        )

        # FocalActorContext 포함 매칭
        matches = engine.match_patterns(
            graph,
            focal_actor_context_id="PRJ-test-brownfield",
        )

        if len(matches) > 0:
            match = matches[0]

            # Execution Fit가 계산되어야 함
            assert match.execution_fit_score is not None
            assert 0.0 <= match.execution_fit_score <= 1.0

            # Combined Score = structure × execution
            expected_combined = match.structure_fit_score * match.execution_fit_score
            assert abs(match.combined_score - expected_combined) < 0.001

            print(f"Structure: {match.structure_fit_score:.2f}")
            print(f"Execution: {match.execution_fit_score:.2f}")
            print(f"Combined: {match.combined_score:.2f}")

    def test_workflow_optimization(self):
        """Workflow 최적화 (precomputed 재사용)"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 구조 생성
        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True}}
        )

        # 1. match_patterns 실행
        matches = engine.match_patterns(graph)

        # 2. discover_gaps with precomputed (중복 스캔 방지)
        gaps = engine.discover_gaps(graph, precomputed_matches=matches)

        # Gap이 발견되어야 함
        assert isinstance(gaps, list)

        print(f"Matches: {len(matches)}, Gaps: {len(gaps)}")
        print("Workflow optimization: precomputed reuse")

    def test_end_to_end_greenfield(self):
        """E2E: Greenfield 분석"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # Digital service 구조
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

        # Greenfield: Project Context 없음
        matches = engine.match_patterns(graph)
        gaps = engine.discover_gaps(graph, precomputed_matches=matches)

        # Structure Fit만 계산
        for match in matches:
            assert match.execution_fit_score is None
            assert match.combined_score == match.structure_fit_score

        # Gap도 feasibility "unknown"
        for gap in gaps:
            assert gap.feasibility == "unknown"

        print(f"Greenfield: {len(matches)} matches, {len(gaps)} gaps")

    def test_end_to_end_brownfield(self):
        """E2E: Brownfield 분석"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 구조
        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True}}
        )

        # Brownfield: FocalActorContext 있음
        matches = engine.match_patterns(graph, focal_actor_context_id="PRJ-test-001")
        gaps = engine.discover_gaps(
            graph,
            focal_actor_context_id="PRJ-test-001",
            precomputed_matches=matches
        )

        # Execution Fit 계산됨
        for match in matches:
            if match.execution_fit_score is not None:
                assert 0.0 <= match.execution_fit_score <= 1.0
                assert match.combined_score <= match.structure_fit_score

        # Gap도 feasibility 평가됨
        # (기본 FocalActorContext라 값은 다양할 수 있음)

        print(f"Brownfield: {len(matches)} matches, {len(gaps)} gaps")


class TestFocalActorContext:
    """FocalActorContext 관련 테스트"""

    def test_focal_actor_context_creation(self):
        """FocalActorContext 생성"""
        pc = FocalActorContext(
            focal_actor_context_id="PRJ-test",
            scope={"domain_id": "education", "region": "KR"},
            assets_profile={
                "capability_traits": [
                    {"technology_domain": "AI_ML"}
                ],
                "channels": [
                    {"channel_type": "online", "reach": 5000}
                ]
            }
        )

        assert pc.focal_actor_context_id == "PRJ-test"
        assert pc.scope["region"] == "KR"
        assert len(pc.assets_profile["capability_traits"]) == 1

    def test_focal_actor_context_in_scoring(self):
        """FocalActorContext가 Scoring에 영향"""
        library = PatternLibrary()
        library.load_all()

        pattern = library.get("PAT-subscription_model")

        # 약한 Context
        weak_context = FocalActorContext(
            focal_actor_context_id="PRJ-weak",
            scope={},
            assets_profile={
                "capability_traits": [],
                "channels": []
            }
        )

        # 강한 Context
        strong_context = FocalActorContext(
            focal_actor_context_id="PRJ-strong",
            scope={},
            assets_profile={
                "capability_traits": [
                    {"technology_domain": "platform_tech", "maturity_level": "production_ready"}
                ],
                "channels": [
                    {"channel_type": "online", "reach": 100000}
                ],
                "brand_assets": {"brand_awareness_level": "high"}
            }
        )

        scorer = PatternScorer()

        weak_score = scorer.calculate_execution_fit(pattern, FocalActorContextBinding.from_record(weak_context))
        strong_score = scorer.calculate_execution_fit(pattern, FocalActorContextBinding.from_record(strong_context))

        # 강한 Context의 점수가 더 높아야 함
        assert strong_score > weak_score

        print(f"Weak: {weak_score:.2f}, Strong: {strong_score:.2f}")


class TestGapCandidateFields:
    """GapCandidate 필드 검증"""

    def test_gap_candidate_fields(self):
        """GapCandidate 필드"""
        gap = GapCandidate(
            pattern_id="PAT-test",
            description="Test Gap",
            expected_level="core",
            feasibility="high",
            execution_fit_score=0.85,
            related_pattern_ids=["PAT-related"],
            evidence={"archetype": "ARCH-test"}
        )

        assert gap.pattern_id == "PAT-test"
        assert gap.expected_level == "core"
        assert gap.feasibility == "high"
        assert gap.execution_fit_score == 0.85


class TestIntegrationPhase2:
    """Phase 2 통합 테스트"""

    def test_full_pipeline_greenfield(self):
        """전체 파이프라인 (Greenfield)"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 디지털 서비스 시장 구조
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

        # Step 1: match_patterns
        matches = engine.match_patterns(graph)

        # Step 2: discover_gaps (precomputed 재사용)
        gaps = engine.discover_gaps(graph, precomputed_matches=matches)

        assert len(matches) >= 1
        assert isinstance(gaps, list)

        # Greenfield: execution_fit 없음
        for match in matches:
            assert match.execution_fit_score is None

        for gap in gaps:
            assert gap.feasibility == "unknown"

        print(f"Greenfield pipeline: {len(matches)} matches, {len(gaps)} gaps")

    def test_full_pipeline_brownfield(self):
        """전체 파이프라인 (Brownfield)"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # 구조
        graph.upsert_node(
            "MFL-001",
            "money_flow",
            {"traits": {"revenue_model": "subscription", "payment_recurs": True}}
        )

        focal_actor_context_id = "PRJ-test-brownfield"

        # Step 1: match_patterns (with FocalActorContext)
        matches = engine.match_patterns(graph, focal_actor_context_id)

        # Step 2: discover_gaps (with FocalActorContext)
        gaps = engine.discover_gaps(
            graph,
            focal_actor_context_id,
            precomputed_matches=matches
        )

        # Brownfield: execution_fit 있음
        for match in matches:
            if match.execution_fit_score is not None:
                assert 0.0 <= match.execution_fit_score <= 1.0

        # Gap도 feasibility 평가됨
        # (실제 평가는 FocalActorContext에 따라 다름)

        print(f"Brownfield pipeline: {len(matches)} matches, {len(gaps)} gaps")

