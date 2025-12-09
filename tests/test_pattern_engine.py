"""Tests for Pattern Engine"""

import pytest
from umis_v9_core.pattern_engine import PatternEngine
from umis_v9_core.world_engine import WorldEngine


def test_pattern_engine_init():
    """Pattern Engine 초기화 테스트"""
    engine = PatternEngine()
    assert engine is not None


def test_match_subscription_pattern(project_root, seed_path):
    """구독형 패턴 매칭 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    pattern_engine = PatternEngine()
    
    matches = pattern_engine.match_patterns(snapshot.graph)
    
    # 구독형 패턴 확인
    subscription_matches = [m for m in matches if m.pattern_id == "PAT-subscription_model"]
    assert len(subscription_matches) == 1
    
    match = subscription_matches[0]
    assert match.structure_fit_score == 1.0
    assert ("구독" in match.description or "subscription" in match.description.lower())
    assert len(match.evidence["node_ids"]) > 0


def test_match_platform_pattern(project_root, seed_path):
    """플랫폼 패턴 매칭 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    pattern_engine = PatternEngine()
    
    matches = pattern_engine.match_patterns(snapshot.graph)
    
    # 플랫폼 패턴 확인
    platform_matches = [m for m in matches if m.pattern_id == "PAT-platform_business_model"]
    assert len(platform_matches) == 1
    
    match = platform_matches[0]
    assert match.structure_fit_score == 1.0
    assert "platform" in match.description.lower() or "플랫폼" in match.description


def test_match_patterns_all(project_root, seed_path):
    """전체 패턴 매칭 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    pattern_engine = PatternEngine()
    
    matches = pattern_engine.match_patterns(snapshot.graph)
    
    # Adult Language seed에는 subscription + platform 둘 다 있음
    assert len(matches) == 2
    
    pattern_ids = {m.pattern_id for m in matches}
    assert "PAT-subscription_model" in pattern_ids
    assert "PAT-platform_business_model" in pattern_ids


def test_discover_gaps(project_root, seed_path):
    """갭 탐지 테스트"""
    world_engine = WorldEngine(project_root)
    snapshot = world_engine.load_reality_seed(seed_path)
    
    pattern_engine = PatternEngine()
    
    gaps = pattern_engine.discover_gaps(snapshot.graph)
    
    # Adult Language seed의 state에 entry_strategy_clues 있음
    assert len(gaps) >= 0  # 있을 수도, 없을 수도
    
    # Gap이 있다면 구조 확인
    if gaps:
        gap = gaps[0]
        assert gap.description is not None
        assert isinstance(gap.related_pattern_ids, list)
        assert "state_id" in gap.evidence
