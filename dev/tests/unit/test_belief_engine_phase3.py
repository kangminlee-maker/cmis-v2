"""BeliefEngine Phase 3 Advanced Tests

고급 기능 테스트:
- Lognormal/Beta 업데이트 (4개)
- Sobol Monte Carlo (2개)
- Samples 저장 (4개)

총 10개 테스트
"""

import pytest
from pathlib import Path
import tempfile
import json
import math
import numpy as np

from cmis_core.belief_updater import BeliefUpdater
from cmis_core.uncertainty_propagator import UncertaintyPropagator


# ========================================
# Lognormal/Beta 업데이트 (4개)
# ========================================

def test_lognormal_update():
    """Lognormal Prior + Observations → Lognormal Posterior"""
    updater = BeliefUpdater()
    
    # Lognormal Prior
    prior = {
        "type": "lognormal",
        "params": {"mu": 10.8, "sigma": 0.5}  # median ≈ 50000
    }
    
    # Observations
    observations = [
        {"value": 48000, "weight": 1.0},
        {"value": 52000, "weight": 1.0}
    ]
    
    posterior = updater.bayesian_update(prior, observations)
    
    # 검증
    assert posterior["type"] == "lognormal"
    assert "mu" in posterior["params"]
    assert "sigma" in posterior["params"]
    
    # Posterior sigma가 Prior보다 작아야 함 (정보 증가)
    assert posterior["params"]["sigma"] < prior["params"]["sigma"]


def test_beta_binomial_update():
    """Beta Prior + Binary Observations → Beta Posterior"""
    updater = BeliefUpdater()
    
    # Beta Prior (uninformative)
    prior = {
        "type": "beta",
        "params": {"alpha": 1, "beta": 1}
    }
    
    # Binary observations (0~1)
    observations = [
        {"value": 0.8, "weight": 1.0},  # success
        {"value": 0.7, "weight": 1.0},  # success
        {"value": 0.3, "weight": 1.0}   # failure
    ]
    
    posterior = updater.bayesian_update(prior, observations)
    
    # 검증
    assert posterior["type"] == "beta"
    assert posterior["params"]["alpha"] > prior["params"]["alpha"]  # successes 추가
    # alpha = 1 + 2 = 3, beta = 1 + 1 = 2
    assert posterior["params"]["alpha"] == 3
    assert posterior["params"]["beta"] == 2


def test_empirical_update():
    """Empirical Update (비모수)"""
    updater = BeliefUpdater()
    
    # Prior는 무시됨
    prior = {"type": "unknown", "params": {}}
    
    observations = [
        {"value": 100, "weight": 1.0},
        {"value": 200, "weight": 1.0},
        {"value": 300, "weight": 1.0}
    ]
    
    posterior = updater.bayesian_update(prior, observations)
    
    # 검증
    assert posterior["type"] == "empirical"
    assert "samples" in posterior
    assert "params" in posterior
    assert posterior["params"]["mean"] == 200  # 평균
    assert len(posterior["samples"]) == 3


def test_mixed_distributions():
    """여러 분포 타입 테스트"""
    updater = BeliefUpdater()
    
    # Normal
    normal_post = updater.bayesian_update(
        {"type": "normal", "params": {"mu": 100, "sigma": 10}},
        [{"value": 105, "weight": 1.0}]
    )
    assert normal_post["type"] == "normal"
    
    # Lognormal
    lognormal_post = updater.bayesian_update(
        {"type": "lognormal", "params": {"mu": 4.6, "sigma": 0.2}},
        [{"value": 100, "weight": 1.0}]
    )
    assert lognormal_post["type"] == "lognormal"
    
    # Beta
    beta_post = updater.bayesian_update(
        {"type": "beta", "params": {"alpha": 2, "beta": 2}},
        [{"value": 0.6, "weight": 1.0}]
    )
    assert beta_post["type"] == "beta"


# ========================================
# Sobol Monte Carlo (2개)
# ========================================

def test_sobol_monte_carlo():
    """Sobol Sequence Monte Carlo"""
    propagator = UncertaintyPropagator()
    
    # Sobol vs Random 비교
    result_sobol = propagator.monte_carlo(
        formula="Z = X + Y",
        input_distributions={
            "X": {"type": "normal", "params": {"mu": 100, "sigma": 10}},
            "Y": {"type": "normal", "params": {"mu": 50, "sigma": 5}}
        },
        n_samples=1000,
        use_sobol=True
    )
    
    result_random = propagator.monte_carlo(
        formula="Z = X + Y",
        input_distributions={
            "X": {"type": "normal", "params": {"mu": 100, "sigma": 10}},
            "Y": {"type": "normal", "params": {"mu": 50, "sigma": 5}}
        },
        n_samples=1000,
        use_sobol=False
    )
    
    # 둘 다 평균 ≈ 150
    assert 140 < result_sobol["statistics"]["mean"] < 160
    assert 140 < result_random["statistics"]["mean"] < 160
    
    # samples_ref 존재
    assert "samples_ref" in result_sobol
    assert result_sobol["samples_ref"].startswith("ART-samples-")


def test_sobol_convergence():
    """Sobol Sequence 수렴 속도 (간접 확인)"""
    propagator = UncertaintyPropagator()
    
    # 적은 샘플로도 안정적인 결과
    result = propagator.monte_carlo(
        formula="Y = X * 2",
        input_distributions={
            "X": {"type": "normal", "params": {"mu": 100, "sigma": 10}}
        },
        n_samples=500,  # 적은 샘플
        use_sobol=True
    )
    
    # 평균 ≈ 200 (정확도 확인)
    assert 190 < result["statistics"]["mean"] < 210


# ========================================
# Samples 저장 (4개)
# ========================================

def test_save_samples_to_store():
    """Samples artifact_store 저장"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = Path(tmpdir) / "artifacts"
        propagator = UncertaintyPropagator(artifact_store_path=artifact_path)
        
        samples = np.array([100, 200, 300, 400, 500])
        
        artifact_id = propagator._save_samples_to_store(
            samples,
            "Y = X * 2",
            {"X": {"type": "normal", "params": {"mu": 100, "sigma": 10}}}
        )
        
        # 검증
        assert artifact_id.startswith("ART-samples-")
        
        # 파일 존재
        filepath = artifact_path / f"{artifact_id}.json"
        assert filepath.exists()
        
        # 내용 확인
        with open(filepath, "r") as f:
            artifact = json.load(f)
        
        assert artifact["artifact_id"] == artifact_id
        assert artifact["type"] == "monte_carlo_samples"
        assert artifact["formula"] == "Y = X * 2"
        assert len(artifact["samples"]) == 5


def test_load_samples_from_store():
    """저장된 Samples 로딩"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = Path(tmpdir) / "artifacts"
        propagator = UncertaintyPropagator(artifact_store_path=artifact_path)
        
        # 1. Monte Carlo 실행 (samples 저장됨)
        result = propagator.monte_carlo(
            formula="Z = X + Y",
            input_distributions={
                "X": {"type": "normal", "params": {"mu": 100, "sigma": 10}},
                "Y": {"type": "normal", "params": {"mu": 50, "sigma": 5}}
            },
            n_samples=100
        )
        
        samples_ref = result["samples_ref"]
        
        # 2. 파일에서 로딩
        filepath = artifact_path / f"{samples_ref}.json"
        assert filepath.exists()
        
        with open(filepath, "r") as f:
            artifact = json.load(f)
        
        # 3. 검증
        assert len(artifact["samples"]) == result["n_samples"]
        assert artifact["formula"] == "Z = X + Y"


def test_monte_carlo_without_samples_in_response():
    """Monte Carlo 응답에 samples 없음 (samples_ref만)"""
    propagator = UncertaintyPropagator()
    
    result = propagator.monte_carlo(
        formula="Y = X * 2",
        input_distributions={
            "X": {"type": "normal", "params": {"mu": 100, "sigma": 10}}
        },
        n_samples=1000
    )
    
    # samples는 응답에 없음 (artifact_store에만)
    assert "samples" not in result
    assert "samples_ref" in result
    assert "percentiles" in result
    assert "statistics" in result


def test_artifact_cleanup():
    """Artifact 정리 테스트"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = Path(tmpdir) / "artifacts"
        propagator = UncertaintyPropagator(artifact_store_path=artifact_path)
        
        # 여러 Monte Carlo 실행
        refs = []
        for i in range(3):
            result = propagator.monte_carlo(
                formula=f"Y = X * {i+1}",
                input_distributions={
                    "X": {"type": "normal", "params": {"mu": 100, "sigma": 10}}
                },
                n_samples=100
            )
            refs.append(result["samples_ref"])
        
        # 3개 파일 존재
        assert len(list(artifact_path.glob("*.json"))) == 3
        
        # 각 ref 확인
        for ref in refs:
            filepath = artifact_path / f"{ref}.json"
            assert filepath.exists()


# ========================================
# AST Evaluator (안전성)
# ========================================

def test_ast_evaluator_safety():
    """AST evaluator 안전성 테스트"""
    propagator = UncertaintyPropagator()
    
    # 안전한 표현식
    safe_result = propagator._evaluate_formula(
        "Z = X * Y + 100",
        {"X": 10, "Y": 5}
    )
    assert safe_result == 150
    
    # 복잡한 표현식
    complex_result = propagator._evaluate_formula(
        "R = (A + B) / (C + 1)",
        {"A": 100, "B": 50, "C": 49}
    )
    assert complex_result == 3.0


def test_ast_evaluator_error_handling():
    """AST evaluator 에러 처리"""
    propagator = UncertaintyPropagator()
    
    # 0으로 나누기
    with pytest.raises(ValueError):
        propagator._evaluate_formula(
            "Y = X / 0",
            {"X": 100}
        )
    
    # 정의되지 않은 변수
    with pytest.raises(ValueError):
        propagator._evaluate_formula(
            "Y = X + Z",
            {"X": 100}  # Z 없음
        )

