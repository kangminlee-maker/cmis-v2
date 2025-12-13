"""BeliefEngine Phase 1 Unit Tests

Core Components 테스트:
- PriorManager (3개)
- BeliefUpdater (4개)
- UncertaintyPropagator (3개)

총 10개 테스트
"""

import pytest
from datetime import datetime, timezone
import numpy as np

from cmis_core.types import BeliefRecord
from cmis_core.prior_manager import PriorManager
from cmis_core.belief_updater import BeliefUpdater
from cmis_core.uncertainty_propagator import UncertaintyPropagator


# ========================================
# PriorManager Tests (3개)
# ========================================

def test_prior_manager_get_set():
    """PriorManager 저장/조회 기본 동작"""
    manager = PriorManager()
    
    # 1. Prior 없을 때
    prior = manager.get_prior("MET-SAM", {"domain_id": "test", "region": "KR"})
    assert prior is None
    
    # 2. Belief 저장
    belief = manager.save_belief(
        metric_id="MET-SAM",
        context={"domain_id": "test", "region": "KR"},
        posterior={"type": "normal", "params": {"mu": 50000, "sigma": 10000}},
        observations=[{"value": 50000, "weight": 1.0, "source": "EVD-001"}],
        prior=None
    )
    
    assert belief.belief_id.startswith("BELIEF-")
    assert belief.metric_id == "MET-SAM"
    assert belief.confidence > 0
    assert belief.source == "learned"
    assert belief.n_observations == 1
    
    # 3. 저장된 Belief 조회
    retrieved = manager.get_prior("MET-SAM", {"domain_id": "test", "region": "KR"})
    assert retrieved is not None
    assert retrieved.belief_id == belief.belief_id
    assert retrieved.metric_id == "MET-SAM"
    assert retrieved.distribution["params"]["mu"] == 50000


def test_hash_context():
    """Context 해시 일관성"""
    manager = PriorManager()
    
    # 동일 Context → 동일 해시
    ctx1 = {"domain_id": "test", "region": "KR", "segment": "online"}
    ctx2 = {"region": "KR", "domain_id": "test", "segment": "online"}  # 순서 다름
    
    hash1 = manager._hash_context(ctx1)
    hash2 = manager._hash_context(ctx2)
    
    assert hash1 == hash2
    assert len(hash1) == 8  # MD5 8자
    
    # 다른 Context → 다른 해시
    ctx3 = {"domain_id": "test", "region": "US"}
    hash3 = manager._hash_context(ctx3)
    
    assert hash1 != hash3


def test_calculate_confidence():
    """신뢰도 계산 로직"""
    manager = PriorManager()
    
    # 1. 관측 없음 → 낮은 신뢰도
    conf0 = manager._calculate_confidence(
        {"type": "normal", "params": {"mu": 50000, "sigma": 10000}},
        []
    )
    assert conf0 == 0.1
    
    # 2. 관측 1개 → 중간 신뢰도
    conf1 = manager._calculate_confidence(
        {"type": "normal", "params": {"mu": 50000, "sigma": 10000}},
        [{"value": 50000, "weight": 1.0}]
    )
    assert 0.5 < conf1 < 0.7
    
    # 3. 관측 5개 → 높은 신뢰도
    conf5 = manager._calculate_confidence(
        {"type": "normal", "params": {"mu": 50000, "sigma": 5000}},
        [{"value": i*10000, "weight": 1.0} for i in range(5)]
    )
    assert conf5 > 0.8
    
    # 4. 좁은 분포 (CV 낮음) → 신뢰도 증가
    conf_narrow = manager._calculate_confidence(
        {"type": "normal", "params": {"mu": 50000, "sigma": 2000}},  # CV=0.04
        [{"value": 50000, "weight": 1.0}]
    )
    
    conf_wide = manager._calculate_confidence(
        {"type": "normal", "params": {"mu": 50000, "sigma": 20000}},  # CV=0.4
        [{"value": 50000, "weight": 1.0}]
    )
    
    assert conf_narrow > conf_wide


# ========================================
# BeliefUpdater Tests (4개)
# ========================================

def test_bayesian_update_normal_normal():
    """Normal-Normal Bayesian Update"""
    updater = BeliefUpdater()
    
    # Prior: μ=50000, σ=10000
    prior = {
        "type": "normal",
        "params": {"mu": 50000, "sigma": 10000}
    }
    
    # Observations: 48000, 52000
    observations = [
        {"value": 48000, "weight": 1.0},
        {"value": 52000, "weight": 1.0}
    ]
    
    posterior = updater.bayesian_update(prior, observations)
    
    # Posterior 검증
    assert posterior["type"] == "normal"
    assert "mu" in posterior["params"]
    assert "sigma" in posterior["params"]
    
    # μ_post는 Prior와 Observation 사이
    mu_post = posterior["params"]["mu"]
    assert 48000 <= mu_post <= 52000
    
    # σ_post는 Prior보다 작아야 함 (정보 증가)
    sigma_post = posterior["params"]["sigma"]
    assert sigma_post < prior["params"]["sigma"]


def test_direct_replace():
    """직접 대체 (numpy 사용)"""
    updater = BeliefUpdater()
    
    observations = [
        {"value": 45000, "weight": 1.0},
        {"value": 50000, "weight": 1.0},
        {"value": 55000, "weight": 1.0}
    ]
    
    posterior = updater.direct_replace(observations)
    
    assert posterior["type"] == "normal"
    assert posterior["params"]["mu"] == 50000  # 평균
    assert posterior["params"]["sigma"] > 0  # 표준편차
    
    # 가중치 다를 때
    weighted_obs = [
        {"value": 40000, "weight": 0.5},
        {"value": 60000, "weight": 1.0}
    ]
    
    weighted_posterior = updater.direct_replace(weighted_obs)
    
    # 가중 평균 = (40000*0.5 + 60000*1.0) / 1.5 ≈ 53333
    assert 52000 < weighted_posterior["params"]["mu"] < 54000


def test_lineage_separation():
    """EVD-*/OUT-* 분리 테스트 (PriorManager에서 수행)"""
    manager = PriorManager()
    
    observations = [
        {"value": 48000, "weight": 1.0, "source": "EVD-001"},
        {"value": 50000, "weight": 0.9, "source": "OUT-002"},
        {"value": 52000, "weight": 0.8, "source": "EVD-003"}
    ]
    
    belief = manager.save_belief(
        metric_id="MET-SAM",
        context={"domain_id": "test"},
        posterior={"type": "normal", "params": {"mu": 50000, "sigma": 5000}},
        observations=observations,
        prior=None
    )
    
    # Lineage 분리 확인
    assert "from_evidence_ids" in belief.lineage
    assert "from_outcome_ids" in belief.lineage
    
    assert "EVD-001" in belief.lineage["from_evidence_ids"]
    assert "EVD-003" in belief.lineage["from_evidence_ids"]
    assert "OUT-002" in belief.lineage["from_outcome_ids"]
    
    assert len(belief.lineage["from_evidence_ids"]) == 2
    assert len(belief.lineage["from_outcome_ids"]) == 1


def test_observation_weighting():
    """관측 가중치 반영"""
    updater = BeliefUpdater()
    
    # Prior: μ=50000
    prior = {"type": "normal", "params": {"mu": 50000, "sigma": 10000}}
    
    # Observation: 40000 (weight=1.0) → Prior보다 낮음
    observations = [{"value": 40000, "weight": 1.0}]
    
    posterior = updater.bayesian_update(prior, observations)
    mu_post = posterior["params"]["mu"]
    
    # Posterior는 Prior와 Observation 사이
    assert 40000 < mu_post < 50000
    
    # weight 높이면 observation 쪽으로 더 이동
    heavy_obs = [{"value": 40000, "weight": 10.0}]
    heavy_posterior = updater.bayesian_update(prior, heavy_obs)
    heavy_mu = heavy_posterior["params"]["mu"]
    
    # heavy_mu가 mu_post보다 40000에 가까워야 함
    assert abs(heavy_mu - 40000) < abs(mu_post - 40000)


# ========================================
# UncertaintyPropagator Tests (3개)
# ========================================

def test_monte_carlo_basic():
    """Monte Carlo 기본 동작"""
    propagator = UncertaintyPropagator()
    
    # 간단한 공식: Y = X * 2
    result = propagator.monte_carlo(
        formula="Y = X * 2",
        input_distributions={
            "X": {"type": "normal", "params": {"mu": 100, "sigma": 10}}
        },
        n_samples=1000
    )
    
    # 결과 검증
    assert "samples" in result
    assert "percentiles" in result
    assert "statistics" in result
    
    # Y의 평균 ≈ 200 (X의 평균 100 × 2)
    assert 190 < result["statistics"]["mean"] < 210
    
    # Y의 표준편차 ≈ 20 (X의 표준편차 10 × 2)
    assert 15 < result["statistics"]["std"] < 25


def test_sample_distribution():
    """분포별 샘플링"""
    propagator = UncertaintyPropagator()
    
    # Normal
    normal_samples = propagator._sample_distribution(
        {"type": "normal", "params": {"mu": 100, "sigma": 10}},
        n=1000
    )
    assert len(normal_samples) == 1000
    assert 80 < np.mean(normal_samples) < 120
    
    # Lognormal
    lognormal_samples = propagator._sample_distribution(
        {"type": "lognormal", "params": {"mu": 4.6, "sigma": 0.2}},
        n=1000
    )
    assert len(lognormal_samples) == 1000
    assert all(s > 0 for s in lognormal_samples)  # Lognormal은 양수
    
    # Uniform
    uniform_samples = propagator._sample_distribution(
        {"type": "uniform", "params": {"min": 0, "max": 100}},
        n=1000
    )
    assert len(uniform_samples) == 1000
    assert all(0 <= s <= 100 for s in uniform_samples)


def test_sensitivity_analysis():
    """민감도 분석 (간단 버전)"""
    propagator = UncertaintyPropagator()
    
    # 2개 입력 변수
    input_dists = {
        "X": {"type": "normal", "params": {"mu": 100, "sigma": 10}},
        "Y": {"type": "normal", "params": {"mu": 50, "sigma": 5}}
    }
    
    # Monte Carlo 실행
    result = propagator.monte_carlo(
        formula="Z = X + Y",
        input_distributions=input_dists,
        n_samples=1000
    )
    
    # 민감도 분석
    sensitivity = propagator.sensitivity_analysis(
        formula="Z = X + Y",
        input_distributions=input_dists,
        output_samples=result["samples"]
    )
    
    # 결과 검증
    assert "X" in sensitivity
    assert "Y" in sensitivity
    
    # 합이 1.0이어야 함
    total = sum(sensitivity.values())
    assert 0.99 < total < 1.01
    
    # Phase 1은 균등 분포 (Phase 3에서 Sobol로 개선)
    # 각 변수 ≈ 0.5
    assert 0.4 < sensitivity["X"] < 0.6
    assert 0.4 < sensitivity["Y"] < 0.6


# ========================================
# Integration Tests (통합 검증)
# ========================================

def test_prior_to_belief_workflow():
    """Prior → Observation → Belief 워크플로우"""
    manager = PriorManager()
    updater = BeliefUpdater()
    
    # 1. 초기 Prior 없음
    prior = manager.get_prior("MET-TAM", {"domain_id": "test"})
    assert prior is None
    
    # 2. 첫 관측으로 Belief 생성
    obs1 = [{"value": 100000, "weight": 1.0, "source": "EVD-001"}]
    belief1 = manager.save_belief(
        metric_id="MET-TAM",
        context={"domain_id": "test"},
        posterior={"type": "normal", "params": {"mu": 100000, "sigma": 20000}},
        observations=obs1,
        prior=None
    )
    
    assert belief1.n_observations == 1
    assert belief1.confidence > 0.5
    
    # 3. 두 번째 관측으로 업데이트
    prior_for_update = manager.get_prior("MET-TAM", {"domain_id": "test"})
    assert prior_for_update is not None
    
    obs2 = [{"value": 120000, "weight": 1.0, "source": "OUT-002"}]
    posterior2 = updater.bayesian_update(
        prior_for_update.distribution,
        obs2
    )
    
    belief2 = manager.save_belief(
        metric_id="MET-TAM",
        context={"domain_id": "test"},
        posterior=posterior2,
        observations=obs2,
        prior=prior_for_update
    )
    
    # 검증
    assert belief2.n_observations == 2  # 누적
    assert belief2.confidence > belief1.confidence  # 신뢰도 증가
    assert belief2.lineage["from_prior_id"] == belief1.belief_id
    
    # μ는 100000과 120000 사이
    mu2 = belief2.distribution["params"]["mu"]
    assert 100000 < mu2 < 120000


def test_belief_record_serialization():
    """BeliefRecord 직렬화/역직렬화"""
    original = BeliefRecord(
        belief_id="BELIEF-test123",
        metric_id="MET-SAM",
        context={"domain_id": "test", "region": "KR"},
        distribution={"type": "normal", "params": {"mu": 50000, "sigma": 10000}},
        confidence=0.75,
        source="pattern_benchmark",
        observations=[{"value": 50000, "weight": 1.0}],
        n_observations=1,
        created_at="2025-12-12T10:00:00Z",
        updated_at="2025-12-12T10:00:00Z",
        lineage={"from_pattern_ids": ["PAT-001"]}
    )
    
    # to_dict
    data = original.to_dict()
    assert data["belief_id"] == "BELIEF-test123"
    assert data["metric_id"] == "MET-SAM"
    assert data["confidence"] == 0.75
    
    # from_dict
    restored = BeliefRecord.from_dict(data)
    assert restored.belief_id == original.belief_id
    assert restored.metric_id == original.metric_id
    assert restored.confidence == original.confidence
    assert restored.distribution == original.distribution


def test_belief_to_value_record():
    """BeliefRecord → ValueRecord 변환"""
    belief = BeliefRecord(
        belief_id="PRIOR-abc123",
        metric_id="MET-SAM",
        context={"domain_id": "test"},
        distribution={"type": "normal", "params": {"mu": 50000, "sigma": 10000}},
        confidence=0.5,
        source="pattern_benchmark",
        observations=[],
        n_observations=0,
        created_at="2025-12-12T10:00:00Z",
        updated_at="2025-12-12T10:00:00Z",
        lineage={"from_pattern_ids": ["PAT-001"]}
    )
    
    # ValueRecord 변환
    value_record = belief.to_value_record()
    
    # 검증
    assert value_record["value_id"] == "VAL-PRIOR-abc123"
    assert value_record["metric_id"] == "MET-SAM"
    assert value_record["point_estimate"] is None  # Prior는 분포만
    assert value_record["distribution"] == belief.distribution
    assert value_record["quality"]["literal_ratio"] == 0.0  # Prior는 literal 없음
    assert value_record["quality"]["confidence"] == 0.5
    assert value_record["origin"] == "prior"  # source가 pattern_benchmark


def test_monte_carlo_two_variables():
    """2개 변수 Monte Carlo"""
    propagator = UncertaintyPropagator()
    
    # Revenue = N_customers * ARPU
    result = propagator.monte_carlo(
        formula="Revenue = N_customers * ARPU",
        input_distributions={
            "N_customers": {"type": "normal", "params": {"mu": 100000, "sigma": 10000}},
            "ARPU": {"type": "normal", "params": {"mu": 50, "sigma": 5}}
        },
        n_samples=5000
    )
    
    # 평균 Revenue ≈ 100000 * 50 = 5,000,000
    assert 4500000 < result["statistics"]["mean"] < 5500000
    
    # Percentiles 존재
    assert result["percentiles"]["p10"] < result["percentiles"]["p50"]
    assert result["percentiles"]["p50"] < result["percentiles"]["p90"]
    
    # CV (Coefficient of Variation) 존재
    assert result["statistics"]["cv"] > 0


# ========================================
# 추가 검증
# ========================================

def test_beliefrecord_spread_calculation():
    """BeliefRecord의 _calculate_spread() 메서드"""
    
    # Normal 분포
    belief_normal = BeliefRecord(
        belief_id="TEST-001",
        metric_id="MET-TEST",
        context={},
        distribution={"type": "normal", "params": {"mu": 100, "sigma": 20}},
        confidence=0.5,
        source="test",
        observations=[],
        n_observations=0,
        created_at="2025-12-12T10:00:00Z",
        updated_at="2025-12-12T10:00:00Z",
        lineage={}
    )
    
    spread_normal = belief_normal._calculate_spread()
    assert spread_normal == 0.2  # sigma/mu = 20/100
    
    # Lognormal 분포
    belief_lognormal = BeliefRecord(
        belief_id="TEST-002",
        metric_id="MET-TEST",
        context={},
        distribution={"type": "lognormal", "params": {"mu": 4.6, "sigma": 0.3}},
        confidence=0.5,
        source="test",
        observations=[],
        n_observations=0,
        created_at="2025-12-12T10:00:00Z",
        updated_at="2025-12-12T10:00:00Z",
        lineage={}
    )
    
    spread_lognormal = belief_lognormal._calculate_spread()
    assert spread_lognormal == 0.3  # sigma 파라미터
    
    # Uniform 분포
    belief_uniform = BeliefRecord(
        belief_id="TEST-003",
        metric_id="MET-TEST",
        context={},
        distribution={"type": "uniform", "params": {"min": 0, "max": 100}},
        confidence=0.1,
        source="uninformative",
        observations=[],
        n_observations=0,
        created_at="2025-12-12T10:00:00Z",
        updated_at="2025-12-12T10:00:00Z",
        lineage={}
    )
    
    spread_uniform = belief_uniform._calculate_spread()
    assert spread_uniform == 1.0  # (max-min)/(2*mean) = 100/(2*50)

