"""Pattern Engine v2 Phase 1 테스트

v1.1 설계 반영:
- PatternSpec 13개 필드
- PatternMatch 8개 필드
- Trait 2단계 계산
- 5개 Pattern YAML

2025-12-10: Phase 1 Core Infrastructure
"""

import pytest
from pathlib import Path

from cmis_core.types import PatternSpec, PatternMatch
from cmis_core.pattern_library import PatternLibrary, PatternValidationError
from cmis_core.pattern_matcher import (
    PatternMatcher,
    check_trait_constraints,
    check_graph_structure,
    calculate_trait_score
)
from cmis_core.pattern_scorer import PatternScorer, calculate_combined_score
from cmis_core.pattern_engine_v2 import PatternEngineV2
from cmis_core.graph import InMemoryGraph


class TestPatternLibrary:
    """PatternLibrary 테스트"""

    def test_load_all_patterns(self):
        """5개 Pattern YAML 로딩"""
        library = PatternLibrary()
        library.load_all()

        patterns = library.get_all()

        # 5개 Pattern이 로딩되어야 함
        assert len(patterns) >= 5

        # Pattern ID 확인
        pattern_ids = {p.pattern_id for p in patterns}
        assert "PAT-subscription_model" in pattern_ids
        assert "PAT-asset_light_model" in pattern_ids
        assert "PAT-network_effects" in pattern_ids
        assert "PAT-market_concentration" in pattern_ids
        assert "PAT-recurring_revenue" in pattern_ids

        print(f"Loaded {len(patterns)} patterns")

    def test_pattern_spec_fields(self):
        """PatternSpec 13개 필드 검증"""
        library = PatternLibrary()
        library.load_all()

        pattern = library.get("PAT-subscription_model")

        assert pattern is not None

        # 기존 10개 필드
        assert pattern.pattern_id == "PAT-subscription_model"
        assert pattern.name
        assert pattern.family == "business_model_patterns"
        assert pattern.description
        assert pattern.trait_constraints
        assert pattern.graph_structure
        assert isinstance(pattern.composes_with, list)
        assert isinstance(pattern.benchmark_metrics, list)

        # v1.1 추가 3개 필드
        assert isinstance(pattern.required_capabilities, list)
        assert isinstance(pattern.required_assets, dict)
        assert isinstance(pattern.constraint_checks, list)

        print(f"Pattern: {pattern.name}")
        print(f"  Required capabilities: {len(pattern.required_capabilities)}")
        print(f"  Required assets: {list(pattern.required_assets.keys())}")

    def test_pattern_validation(self):
        """Pattern 검증"""
        library = PatternLibrary()

        # 유효한 Pattern
        valid_pattern = PatternSpec(
            pattern_id="PAT-test-valid",
            name="Test Pattern",
            family="test_family",
            description="Test",
            trait_constraints={"actor": {"required_traits": {"kind": "company"}}},
            graph_structure={}
        )

        errors = library._validate_pattern_spec(valid_pattern)
        assert len(errors) == 0

        # 유효하지 않은 Pattern (pattern_id 형식 오류)
        invalid_pattern = PatternSpec(
            pattern_id="invalid-id",  # PAT-로 시작하지 않음
            name="Test",
            family="test",
            description="Test",
            trait_constraints={"actor": {"required_traits": {}}},
            graph_structure={}
        )

        errors = library._validate_pattern_spec(invalid_pattern)
        assert len(errors) > 0
        assert any("pattern_id" in err for err in errors)

    def test_get_by_family(self):
        """Family별 Pattern 조회"""
        library = PatternLibrary()
        library.load_all()

        bm_patterns = library.get_by_family("business_model_patterns")

        assert len(bm_patterns) >= 2  # subscription, platform

        pattern_ids = [p.pattern_id for p in bm_patterns]
        assert "PAT-subscription_model" in pattern_ids


class TestTraitConstraints:
    """Trait 제약 체크 테스트"""

    def test_check_trait_constraints_match(self):
        """Trait 매칭 성공"""
        graph = InMemoryGraph()

        # Money flow with subscription
        graph.upsert_node(
            node_id="MFL-001",
            node_type="money_flow",
            data={
                "traits": {
                    "revenue_model": "subscription",
                    "payment_recurs": True
                }
            }
        )

        trait_constraints = {
            "money_flow": {
                "required_traits": {
                    "revenue_model": "subscription",
                    "payment_recurs": True
                }
            }
        }

        result = check_trait_constraints(graph, trait_constraints)

        assert result["is_match"] is True
        assert len(result["matched_node_ids"]) == 1
        assert "MFL-001" in result["matched_node_ids"]

    def test_check_trait_constraints_no_match(self):
        """Trait 매칭 실패"""
        graph = InMemoryGraph()

        # Money flow without subscription
        graph.upsert_node(
            node_id="MFL-002",
            node_type="money_flow",
            data={
                "traits": {
                    "revenue_model": "one_off"
                }
            }
        )

        trait_constraints = {
            "money_flow": {
                "required_traits": {
                    "revenue_model": "subscription"
                }
            }
        }

        result = check_trait_constraints(graph, trait_constraints)

        assert result["is_match"] is False

    def test_trait_score_calculation(self):
        """Trait Score 계산 (2단계)"""
        trait_match = {
            "money_flow": {
                "required": {"matched": 2, "total": 2},
                "optional": {"matched": 1, "total": 3}
            }
        }

        score = calculate_trait_score(trait_match)

        # required 100% + optional 33% × 0.1 = 1.0 + 0.033 → 1.0 (clamp)
        assert 1.0 <= score <= 1.0
        assert score == 1.0


class TestGraphStructure:
    """Graph 구조 체크 테스트"""

    def test_check_graph_structure_match(self):
        """Graph 구조 매칭 성공"""
        graph = InMemoryGraph()

        # 3개 money_flow 노드
        for i in range(3):
            graph.upsert_node(
                node_id=f"MFL-{i:03d}",
                node_type="money_flow",
                data={}
            )

        graph_structure = {
            "requires": [
                {"node_type": "money_flow", "min_count": 1}
            ]
        }

        result = check_graph_structure(graph, graph_structure)

        assert result["is_match"] is True
        assert len(result["satisfied"]) == 1

    def test_check_graph_structure_no_match(self):
        """Graph 구조 매칭 실패 (min_count 부족)"""
        graph = InMemoryGraph()

        # 노드 없음

        graph_structure = {
            "requires": [
                {"node_type": "money_flow", "min_count": 1}
            ]
        }

        result = check_graph_structure(graph, graph_structure)

        assert result["is_match"] is False
        assert len(result["unsatisfied"]) == 1


class TestPatternScorer:
    """PatternScorer 테스트"""

    def test_combined_score_no_execution(self):
        """combined_score (Project Context 없음)"""
        structure_fit = 0.85
        execution_fit = None

        combined = calculate_combined_score(structure_fit, execution_fit)

        assert combined == structure_fit

    def test_combined_score_with_execution(self):
        """combined_score (Project Context 있음)"""
        structure_fit = 0.90
        execution_fit = 0.80

        combined = calculate_combined_score(structure_fit, execution_fit)

        assert abs(combined - 0.72) < 0.001  # 0.90 × 0.80 (floating point)

    def test_calculate_structure_fit(self):
        """Structure Fit 계산"""
        library = PatternLibrary()
        library.load_all()

        pattern = library.get("PAT-subscription_model")

        trait_result = {
            "trait_match": {
                "money_flow": {
                    "required": {"matched": 2, "total": 2},
                    "optional": {"matched": 0, "total": 1}
                }
            }
        }

        structure_result = {
            "satisfied": [{"node_type": "money_flow"}],
            "unsatisfied": []
        }

        scorer = PatternScorer()
        score = scorer.calculate_structure_fit(pattern, trait_result, structure_result)

        # Trait: 1.0, Structure: 1.0 → 1.0
        assert score == 1.0


class TestPatternEngineV2:
    """PatternEngine v2 통합 테스트"""

    def test_engine_initialization(self):
        """엔진 초기화"""
        engine = PatternEngineV2()

        patterns = engine.get_all_patterns()

        assert len(patterns) >= 5
        print(f"Loaded {len(patterns)} patterns")

    def test_match_patterns_subscription_model(self):
        """구독 모델 매칭"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # Subscription money flow
        graph.upsert_node(
            node_id="MFL-sub-001",
            node_type="money_flow",
            data={
                "traits": {
                    "revenue_model": "subscription",
                    "payment_recurs": True
                }
            }
        )

        matches = engine.match_patterns(graph)

        # PAT-subscription_model이 매칭되어야 함
        subscription_matches = [
            m for m in matches
            if m.pattern_id == "PAT-subscription_model"
        ]

        assert len(subscription_matches) > 0

        match = subscription_matches[0]
        assert match.structure_fit_score > 0.0
        assert match.combined_score > 0.0
        # matched_node_ids는 trait_result 안에 있음
        trait_result = match.evidence.get("trait_result", {})
        assert "MFL-sub-001" in trait_result.get("matched_node_ids", [])

        print(f"Subscription model matched: {match.structure_fit_score:.2f}")

    def test_match_patterns_platform_model(self):
        """플랫폼 모델 매칭"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # Platform actor
        graph.upsert_node(
            node_id="ACT-platform-001",
            node_type="actor",
            data={
                "traits": {
                    "institution_type": "online_platform"
                }
            }
        )

        matches = engine.match_patterns(graph)

        # PAT-platform_business_model이 매칭되어야 함
        platform_matches = [
            m for m in matches
            if m.pattern_id == "PAT-platform_business_model"
        ]

        assert len(platform_matches) > 0

        match = platform_matches[0]
        assert match.structure_fit_score > 0.0
        # matched_node_ids는 trait_result 안에 있음
        trait_result = match.evidence.get("trait_result", {})
        assert "ACT-platform-001" in trait_result.get("matched_node_ids", [])

    def test_match_patterns_empty_graph(self):
        """빈 그래프 (매칭 없음)"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        matches = engine.match_patterns(graph)

        # 매칭 없음
        assert len(matches) == 0

    def test_match_patterns_sorting(self):
        """매칭 결과 정렬 (combined_score 기준)"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # Subscription + Platform
        graph.upsert_node(
            node_id="MFL-001",
            node_type="money_flow",
            data={
                "traits": {
                    "revenue_model": "subscription",
                    "payment_recurs": True
                }
            }
        )

        graph.upsert_node(
            node_id="ACT-001",
            node_type="actor",
            data={
                "traits": {
                    "institution_type": "online_platform"
                }
            }
        )

        matches = engine.match_patterns(graph)

        if len(matches) > 1:
            # combined_score 기준 내림차순 정렬 확인
            for i in range(len(matches) - 1):
                assert matches[i].combined_score >= matches[i+1].combined_score

            print(f"Matched {len(matches)} patterns (sorted by combined_score)")


class TestPatternMatchFields:
    """PatternMatch 8개 필드 검증"""

    def test_pattern_match_v11_fields(self):
        """PatternMatch v1.1 필드 검증"""
        match = PatternMatch(
            pattern_id="PAT-test",
            description="Test",
            structure_fit_score=0.95,
            execution_fit_score=0.80,
            combined_score=0.76,  # 0.95 × 0.80
            evidence={},
            anchor_nodes={"actor": ["ACT-001"]},
            instance_scope={"domain": "test"}
        )

        # 8개 필드 존재 확인
        assert match.pattern_id == "PAT-test"
        assert match.description == "Test"
        assert match.structure_fit_score == 0.95
        assert match.execution_fit_score == 0.80
        assert match.combined_score == 0.76
        assert isinstance(match.evidence, dict)
        assert isinstance(match.anchor_nodes, dict)
        assert match.instance_scope is not None


class TestPatternYAML:
    """Pattern YAML 형식 검증"""

    def test_subscription_model_yaml(self):
        """PAT-subscription_model YAML 검증"""
        library = PatternLibrary()
        library.load_all()

        pattern = library.get("PAT-subscription_model")

        assert pattern.pattern_id == "PAT-subscription_model"
        assert pattern.family == "business_model_patterns"

        # Trait constraints
        assert "money_flow" in pattern.trait_constraints
        mf_traits = pattern.trait_constraints["money_flow"]
        assert "required_traits" in mf_traits
        assert mf_traits["required_traits"]["revenue_model"] == "subscription"

        # Benchmark metrics
        assert "MET-Churn_rate" in pattern.benchmark_metrics
        assert "MET-LTV" in pattern.benchmark_metrics

        # v1.1 fields
        assert len(pattern.required_capabilities) > 0
        assert "channels" in pattern.required_assets

    def test_all_5_patterns_valid(self):
        """5개 Pattern 모두 유효성 검증"""
        library = PatternLibrary()
        library.load_all()

        pattern_ids = [
            "PAT-subscription_model",
            "PAT-asset_light_model",
            "PAT-network_effects",
            "PAT-market_concentration",
            "PAT-recurring_revenue"
        ]

        for pattern_id in pattern_ids:
            pattern = library.get(pattern_id)

            assert pattern is not None, f"{pattern_id} not found"

            # 기본 검증
            errors = library._validate_pattern_spec(pattern)
            assert len(errors) == 0, f"{pattern_id} validation failed: {errors}"

            print(f"  {pattern_id}: {pattern.name} ({pattern.family})")


class TestIntegration:
    """통합 테스트"""

    def test_full_matching_pipeline(self):
        """전체 매칭 파이프라인"""
        engine = PatternEngineV2()
        graph = InMemoryGraph()

        # Subscription 구조
        graph.upsert_node(
            node_id="MFL-001",
            node_type="money_flow",
            data={
                "traits": {
                    "revenue_model": "subscription",
                    "payment_recurs": True,
                    "recurrence": "monthly"
                }
            }
        )

        graph.upsert_node(
            node_id="ACT-001",
            node_type="actor",
            data={
                "kind": "company",
                "traits": {}
            }
        )

        # 매칭 실행
        matches = engine.match_patterns(graph)

        # 결과 검증
        assert len(matches) >= 1

        # 최소 PAT-subscription_model 또는 PAT-recurring_revenue 매칭
        matched_ids = [m.pattern_id for m in matches]
        assert any("subscription" in pid or "recurring" in pid for pid in matched_ids)

        # 모든 match가 8개 필드를 가져야 함
        for match in matches:
            assert hasattr(match, 'pattern_id')
            assert hasattr(match, 'structure_fit_score')
            assert hasattr(match, 'combined_score')
            assert hasattr(match, 'anchor_nodes')

            # combined_score = structure_fit (execution_fit 없음)
            if match.execution_fit_score is None:
                assert match.combined_score == match.structure_fit_score

        print(f"Matched {len(matches)} patterns")
        for match in matches:
            print(f"  {match.pattern_id}: {match.combined_score:.2f}")
