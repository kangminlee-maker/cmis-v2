"""BeliefEngine Phase 2 Integration Tests

통합 및 연동 테스트:
- query_prior_api (4개)
- update_belief_api (4개)
- ValueEngine 연동 (2개)
- LearningEngine 연동 (2개)

총 12개 테스트
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import tempfile

from cmis_core.types import BeliefRecord, Outcome
from cmis_core.belief_engine import BeliefEngine
from cmis_core.prior_manager import PriorManager
from cmis_core.value_engine import ValueEngine
from cmis_core.learning_engine import LearningEngine


# ========================================
# query_prior_api Tests (4개)
# ========================================

def test_query_prior_api_uninformative():
    """query_prior_api - Uninformative Prior"""
    engine = BeliefEngine()
    
    # Prior 없을 때 → Uninformative (고유 context 사용)
    result = engine.query_prior_api(
        metric_id="MET-SAM-UNINFORMATIVE-TEST",
        context={"domain_id": "uninformative_test_domain", "region": "XX"},
        policy_ref="decision_balanced"
    )
    
    # 검증
    assert result["metric_id"] == "MET-SAM-UNINFORMATIVE-TEST"
    assert "distribution" in result
    assert result["confidence"] == 0.1  # Uninformative
    assert result["source"] == "uninformative"
    assert result["policy_mode"] == "decision_balanced"


def test_query_prior_api_cached():
    """query_prior_api - 캐싱된 Prior 조회"""
    engine = BeliefEngine()
    
    # 1. Belief 저장
    engine.prior_manager.save_belief(
        metric_id="MET-TAM",
        context={"domain_id": "test"},
        posterior={"type": "normal", "params": {"mu": 100000, "sigma": 20000}},
        observations=[{"value": 100000, "weight": 1.0}],
        prior=None
    )
    
    # 2. 조회 → 저장된 Belief 반환
    result = engine.query_prior_api(
        metric_id="MET-TAM",
        context={"domain_id": "test"}
    )
    
    assert result["source"] == "learned"  # 저장된 Belief
    assert result["confidence"] > 0.5
    assert result["distribution"]["params"]["mu"] == 100000


def test_query_prior_api_policy_strict():
    """query_prior_api - reporting_strict Policy"""
    engine = BeliefEngine()
    
    # Belief 저장
    engine.prior_manager.save_belief(
        metric_id="MET-Revenue",
        context={"domain_id": "test"},
        posterior={"type": "normal", "params": {"mu": 50000, "sigma": 5000}},
        observations=[{"value": 50000, "weight": 1.0}],
        prior=None
    )
    
    # reporting_strict → confidence 절반, spread 2배
    result = engine.query_prior_api(
        metric_id="MET-Revenue",
        context={"domain_id": "test"},
        policy_ref="reporting_strict"
    )
    
    # confidence 절반
    original_conf = 0.6  # 대략적인 값
    assert result["confidence"] < original_conf
    
    # spread 2배 (sigma 증가)
    assert result["distribution"]["params"]["sigma"] > 5000


def test_query_prior_api_policy_friendly():
    """query_prior_api - exploration_friendly Policy"""
    engine = BeliefEngine()
    
    # Belief 저장
    engine.prior_manager.save_belief(
        metric_id="MET-ARPU",
        context={"domain_id": "test"},
        posterior={"type": "normal", "params": {"mu": 5000, "sigma": 500}},
        observations=[{"value": 5000, "weight": 1.0}],
        prior=None
    )
    
    # exploration_friendly → spread 1.2배
    result = engine.query_prior_api(
        metric_id="MET-ARPU",
        context={"domain_id": "test"},
        policy_ref="exploration_friendly"
    )
    
    # spread 증가 (sigma × 1.2)
    expected_sigma = 500 * 1.2
    assert abs(result["distribution"]["params"]["sigma"] - expected_sigma) < 50


# ========================================
# update_belief_api Tests (4개)
# ========================================

def test_update_belief_api_bayesian():
    """update_belief_api - Bayesian 모드"""
    engine = BeliefEngine()
    
    # 1. 초기 Belief 없음 → Uninformative Prior 사용 (고유 context)
    observations = [
        {"value": 48000, "weight": 1.0, "source": "EVD-001"},
        {"value": 52000, "weight": 0.8, "source": "EVD-002"}
    ]
    
    result = engine.update_belief_api(
        metric_id="MET-SAM-BAYESIAN-TEST",
        context={"domain_id": "bayesian_test_unique"},
        observations=observations,
        update_mode="bayesian"
    )
    
    # 검증
    assert result["belief_id"].startswith("BELIEF-")
    assert "prior" in result
    assert "posterior" in result
    assert "delta" in result
    
    # Prior는 uninformative (0.1), Posterior는 observations 2개 (0.7)
    assert result["prior"]["confidence"] == 0.1
    assert result["posterior"]["confidence"] == 0.7  # n_observations=2


def test_update_belief_api_replace():
    """update_belief_api - Replace 모드"""
    engine = BeliefEngine()
    
    observations = [
        {"value": 45000, "weight": 1.0, "source": "OUT-001"},
        {"value": 50000, "weight": 1.0, "source": "OUT-002"},
        {"value": 55000, "weight": 1.0, "source": "OUT-003"}
    ]
    
    result = engine.update_belief_api(
        metric_id="MET-Revenue",
        context={"domain_id": "test"},
        observations=observations,
        update_mode="replace"
    )
    
    # Replace → Prior 무시하고 관측값만
    assert result["posterior"]["distribution"]["params"]["mu"] == 50000


def test_update_belief_api_delta():
    """update_belief_api - Delta 계산"""
    engine = BeliefEngine()
    
    # 1. 초기 Belief
    first_obs = [{"value": 50000, "weight": 1.0, "source": "EVD-001"}]
    first_result = engine.update_belief_api(
        metric_id="MET-TAM",
        context={"domain_id": "test"},
        observations=first_obs,
        update_mode="replace"
    )
    
    # 2. 두 번째 관측 (다른 값)
    second_obs = [{"value": 60000, "weight": 1.0, "source": "OUT-001"}]
    second_result = engine.update_belief_api(
        metric_id="MET-TAM",
        context={"domain_id": "test"},
        observations=second_obs,
        update_mode="bayesian"
    )
    
    # Delta 검증
    delta = second_result["delta"]
    assert "mean_shift" in delta
    assert delta["mean_shift"] > 0  # 50000 → 60000 방향
    assert "sigma_reduction" in delta


def test_update_belief_api_confidence_gain():
    """update_belief_api - 신뢰도 증가 확인"""
    engine = BeliefEngine()
    
    # 1개 관측
    obs1 = [{"value": 50000, "weight": 1.0, "source": "EVD-001"}]
    result1 = engine.update_belief_api(
        metric_id="MET-N_customers",
        context={"domain_id": "test"},
        observations=obs1,
        update_mode="replace"
    )
    
    conf1 = result1["posterior"]["confidence"]
    
    # 추가 관측
    obs2 = [{"value": 51000, "weight": 1.0, "source": "OUT-001"}]
    result2 = engine.update_belief_api(
        metric_id="MET-N_customers",
        context={"domain_id": "test"},
        observations=obs2,
        update_mode="bayesian"
    )
    
    conf2 = result2["posterior"]["confidence"]
    
    # 신뢰도 증가
    assert conf2 > conf1


# ========================================
# ValueEngine Integration Tests (2개)
# ========================================

def test_value_engine_prior_estimation():
    """ValueEngine에서 BeliefEngine 호출"""
    value_engine = ValueEngine()
    
    # Prior estimation (Evidence 없을 때)
    value_record = value_engine._resolve_metric_prior_estimation(
        metric_id="MET-SAM",
        context={"domain_id": "test", "region": "KR"},
        policy_ref="decision_balanced"
    )
    
    # 검증
    assert value_record is not None
    assert value_record.metric_id == "MET-SAM"
    assert value_record.point_estimate is None  # Prior는 분포만
    assert value_record.distribution is not None
    assert value_record.quality["literal_ratio"] == 0.0
    assert value_record.quality["method"] == "belief_engine"
    assert "from_prior_id" in value_record.lineage


def test_value_engine_policy_strict_skip():
    """ValueEngine - reporting_strict에서 Prior skip"""
    value_engine = ValueEngine()
    
    # reporting_strict → Prior 사용 안 함
    value_record = value_engine._resolve_metric_prior_estimation(
        metric_id="MET-SAM",
        context={"domain_id": "test"},
        policy_ref="reporting_strict"
    )
    
    # None 반환
    assert value_record is None


# ========================================
# LearningEngine Integration Tests (2개)
# ========================================

def test_learning_should_update_belief():
    """LearningEngine - metrics_spec 기반 판단"""
    learning_engine = LearningEngine()
    
    # 1. 작은 오차 → 업데이트 안 함
    delta_small = {"error_pct": 0.05}  # 5%
    should_update = learning_engine._should_update_belief("MET-SAM", delta_small)
    assert should_update is False  # target_convergence ±30% (기본 20%)
    
    # 2. 큰 오차 → 업데이트
    delta_large = {"error_pct": 0.35}  # 35%
    should_update = learning_engine._should_update_belief("MET-SAM", delta_large)
    assert should_update is True


def test_learning_drift_alert():
    """LearningEngine - drift_alert 생성"""
    learning_engine = LearningEngine()
    
    # 큰 Belief 변화
    belief_update_result = {
        "belief_id": "BELIEF-test123",
        "delta": {
            "mean_shift": 10000,
            "mean_shift_pct": 0.6  # 60%
        }
    }
    
    memory_id = learning_engine._create_drift_alert(
        "MET-Revenue",
        belief_update_result
    )
    
    # 검증
    assert memory_id.startswith("MEM-drift-")
    assert len(learning_engine.memory_store) == 1
    
    alert = learning_engine.memory_store[0]
    assert alert["memory_type"] == "drift_alert"
    assert alert["related_ids"]["metric_id"] == "MET-Revenue"
    # 포맷: "+60.0%" 또는 "+0.6"
    assert ("+60" in alert["content"] or "+0.6" in alert["content"])


# ========================================
# E2E Tests (통합 검증)
# ========================================

def test_e2e_value_to_belief_to_value():
    """E2E: ValueEngine → BeliefEngine → Prior → ValueRecord"""
    
    value_engine = ValueEngine()
    
    # 1. ValueEngine이 Prior 요청
    value_record = value_engine._resolve_metric_prior_estimation(
        metric_id="MET-SOM",
        context={"domain_id": "education", "region": "KR"},
        policy_ref="exploration_friendly"
    )
    
    assert value_record is not None
    assert value_record.quality["literal_ratio"] == 0.0
    assert value_record.quality["confidence"] > 0
    
    # 2. Prior ID 확인
    prior_id = value_record.lineage.get("from_prior_id")
    assert prior_id is not None
    assert prior_id.startswith("PRIOR-")


def test_e2e_learning_to_belief_update():
    """E2E: LearningEngine → BeliefEngine 업데이트"""
    
    learning_engine = LearningEngine()
    belief_engine = BeliefEngine()
    
    # 1. 초기 Belief 생성
    belief_engine.update_belief_api(
        metric_id="MET-ARPU",
        context={"domain_id": "test"},
        observations=[{"value": 5000, "weight": 1.0, "source": "EVD-001"}],
        update_mode="replace"
    )
    
    # 2. Outcome 생성
    outcome = Outcome(
        outcome_id="OUT-test001",
        as_of="2025-12-12",
        metrics={"MET-ARPU": 5500},  # 10% 증가
        context={"domain_id": "test"}
    )
    
    comparison = {
        "deltas": {
            "MET-ARPU": {"error_pct": 0.10}  # 10% 오차
        }
    }
    
    # 3. Belief 업데이트 (should_update=False, 기본 20%)
    should_update = learning_engine._should_update_belief("MET-ARPU", comparison["deltas"]["MET-ARPU"])
    assert should_update is False
    
    # 큰 오차로 변경
    comparison["deltas"]["MET-ARPU"]["error_pct"] = 0.25
    should_update = learning_engine._should_update_belief("MET-ARPU", comparison["deltas"]["MET-ARPU"])
    assert should_update is True


def test_policy_adjustment_flow():
    """Policy별 Prior 조정 플로우"""
    engine = BeliefEngine()
    
    # 동일 Belief 저장
    for policy in ["reporting_strict", "decision_balanced", "exploration_friendly"]:
        engine.prior_manager.save_belief(
            metric_id=f"MET-test-{policy}",
            context={"domain_id": "test"},
            posterior={"type": "normal", "params": {"mu": 10000, "sigma": 1000}},
            observations=[{"value": 10000, "weight": 1.0}],
            prior=None
        )
    
    # Policy별 조회
    strict_result = engine.query_prior_api(
        "MET-test-reporting_strict",
        {"domain_id": "test"},
        "reporting_strict"
    )
    
    balanced_result = engine.query_prior_api(
        "MET-test-decision_balanced",
        {"domain_id": "test"},
        "decision_balanced"
    )
    
    friendly_result = engine.query_prior_api(
        "MET-test-exploration_friendly",
        {"domain_id": "test"},
        "exploration_friendly"
    )
    
    # reporting_strict가 가장 보수적
    assert strict_result["confidence"] < balanced_result["confidence"]
    assert strict_result["distribution"]["params"]["sigma"] > balanced_result["distribution"]["params"]["sigma"]
    
    # exploration_friendly는 중간
    assert friendly_result["distribution"]["params"]["sigma"] > balanced_result["distribution"]["params"]["sigma"]


def test_beliefrecord_to_value_record():
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
    
    value_record = belief.to_value_record()
    
    # 검증
    assert value_record["value_id"] == "VAL-PRIOR-abc123"
    assert value_record["origin"] == "prior"
    assert value_record["quality"]["literal_ratio"] == 0.0
    assert value_record["quality"]["spread_ratio"] > 0


# ========================================
# 영속성 Tests (value_store)
# ========================================

def test_value_store_persistence():
    """value_store 영속성 테스트"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "value_store"
        
        # 1. PriorManager 생성 (value_store_path 지정)
        manager = PriorManager(value_store_path=store_path)
        
        # 2. Belief 저장
        belief = manager.save_belief(
            metric_id="MET-TAM",
            context={"domain_id": "test", "region": "KR"},
            posterior={"type": "normal", "params": {"mu": 100000, "sigma": 20000}},
            observations=[{"value": 100000, "weight": 1.0}],
            prior=None
        )
        
        # 3. 파일 존재 확인
        value_id = f"VAL-{belief.belief_id}"
        filepath = store_path / f"{value_id}.json"
        assert filepath.exists()
        
        # 4. 새 PriorManager 생성 (동일 경로)
        manager2 = PriorManager(value_store_path=store_path)
        
        # 5. 조회 → 파일에서 로드
        loaded = manager2.get_prior("MET-TAM", {"domain_id": "test", "region": "KR"})
        
        assert loaded is not None
        assert loaded.metric_id == "MET-TAM"
        assert loaded.distribution["params"]["mu"] == 100000


def test_cache_ttl():
    """캐시 TTL 테스트"""
    
    manager = PriorManager()
    
    # 1. Belief 저장
    manager.save_belief(
        metric_id="MET-test",
        context={"domain_id": "cache_test"},
        posterior={"type": "normal", "params": {"mu": 1000, "sigma": 100}},
        observations=[{"value": 1000, "weight": 1.0}],
        prior=None
    )
    
    # 2. 캐시 조회
    cache_key = manager._make_cache_key("MET-test", {"domain_id": "cache_test"})
    assert cache_key in manager._cache
    assert cache_key in manager._cache_timestamps
    
    # 3. TTL 만료 전 조회 → 캐시에서
    belief = manager.get_prior("MET-test", {"domain_id": "cache_test"})
    assert belief is not None
    assert belief.distribution["params"]["mu"] == 1000
