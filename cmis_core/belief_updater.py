"""Belief Updater

Bayesian Update 로직을 담당하는 모듈.

Prior Distribution + Observations → Posterior Distribution

Phase 1: Normal-Normal Bayesian Update
Phase 3: Lognormal, Beta 등 추가 분포 지원
"""

from typing import Dict, List, Any
import math
import numpy as np


class BeliefUpdater:
    """Bayesian Belief Update
    
    Prior와 Observations를 받아 Posterior 계산.
    
    Usage:
        updater = BeliefUpdater()
        
        prior = {"type": "normal", "params": {"mu": 50000, "sigma": 10000}}
        observations = [
            {"value": 48000, "weight": 1.0},
            {"value": 52000, "weight": 0.8}
        ]
        
        posterior = updater.bayesian_update(prior, observations)
        # → {"type": "normal", "params": {"mu": 49500, "sigma": 6000}}
    """
    
    def bayesian_update(
        self,
        prior: Dict,
        observations: List[Dict]
    ) -> Dict:
        """베이지안 업데이트
        
        분포 타입에 따라 적절한 업데이트 메서드 호출.
        
        Args:
            prior: {
                "type": "normal" | "lognormal" | "beta" | ...,
                "params": {...}
            }
            observations: [
                {"value": 48000, "weight": 1.0, "source": "EVD-001"},
                ...
            ]
        
        Returns:
            posterior: {"type": "...", "params": {...}}
        """
        prior_type = prior.get("type", "normal")
        
        if prior_type == "normal":
            return self._normal_normal_update(prior, observations)
        
        elif prior_type == "lognormal":
            # Phase 3에서 구현
            return self._lognormal_update(prior, observations)
        
        elif prior_type == "beta":
            # Phase 3에서 구현
            return self._beta_binomial_update(prior, observations)
        
        else:
            # Fallback: Empirical update
            return self._empirical_update(prior, observations)
    
    def _normal_normal_update(
        self,
        prior: Dict,
        observations: List[Dict]
    ) -> Dict:
        """Normal Prior + Normal Likelihood → Normal Posterior
        
        Conjugate Prior 이용한 해석적 업데이트.
        
        공식:
        σ²_post = 1 / (1/σ²_prior + Σ(w_i/σ²_obs))
        μ_post = σ²_post * (μ_prior/σ²_prior + Σ(w_i*x_i/σ²_obs))
        
        Args:
            prior: {"type": "normal", "params": {"mu": 50000, "sigma": 10000}}
            observations: [{"value": 48000, "weight": 1.0}, ...]
        
        Returns:
            posterior: {"type": "normal", "params": {"mu": ..., "sigma": ...}}
        """
        # Prior 파라미터
        mu_prior = prior["params"]["mu"]
        sigma_prior = prior["params"]["sigma"]
        
        # sigma_prior=0 방어
        if sigma_prior <= 0:
            sigma_prior = mu_prior * 0.1 if mu_prior > 0 else 1.0
        
        # Observation variance (가정: 관측 오차 10%)
        # 실제론 관측마다 다를 수 있음
        sigma_obs = sigma_prior * 0.1
        if sigma_obs <= 0:
            sigma_obs = 1.0
        
        # Weighted observations
        total_weight = sum(obs["weight"] for obs in observations)
        weighted_sum = sum(obs["value"] * obs["weight"] for obs in observations)
        
        # Precision (정밀도 = 1/σ²)
        precision_prior = 1 / (sigma_prior ** 2)
        precision_obs = total_weight / (sigma_obs ** 2)
        precision_post = precision_prior + precision_obs
        
        # Posterior 파라미터
        sigma_post = math.sqrt(1 / precision_post)
        mu_post = (mu_prior * precision_prior + weighted_sum / (sigma_obs ** 2)) / precision_post
        
        return {
            "type": "normal",
            "params": {
                "mu": mu_post,
                "sigma": sigma_post
            }
        }
    
    def _lognormal_update(
        self,
        prior: Dict,
        observations: List[Dict]
    ) -> Dict:
        """Lognormal Prior + Lognormal Likelihood → Lognormal Posterior
        
        Phase 3: 수치적 근사 (log 공간에서 Normal-Normal)
        
        Args:
            prior: {"type": "lognormal", "params": {"mu": ..., "sigma": ...}}
            observations: [...]
        
        Returns:
            posterior: {"type": "lognormal", "params": {...}}
        """
        # Log 공간으로 변환
        log_observations = [
            {"value": math.log(obs["value"]) if obs["value"] > 0 else 0, "weight": obs["weight"]}
            for obs in observations
            if obs["value"] > 0
        ]
        
        if not log_observations:
            return prior
        
        # Log 공간에서 Normal-Normal 업데이트
        log_prior = {
            "type": "normal",
            "params": {
                "mu": prior["params"]["mu"],
                "sigma": prior["params"]["sigma"]
            }
        }
        
        log_posterior = self._normal_normal_update(log_prior, log_observations)
        
        # Lognormal로 복원
        return {
            "type": "lognormal",
            "params": {
                "mu": log_posterior["params"]["mu"],
                "sigma": log_posterior["params"]["sigma"]
            }
        }
    
    def _beta_binomial_update(
        self,
        prior: Dict,
        observations: List[Dict]
    ) -> Dict:
        """Beta Prior + Binomial Likelihood → Beta Posterior
        
        Phase 3: Conjugate Prior 업데이트
        
        Args:
            prior: {"type": "beta", "params": {"alpha": ..., "beta": ...}}
            observations: [0~1 값들]
        
        Returns:
            posterior: {"type": "beta", "params": {...}}
        """
        alpha_prior = prior["params"]["alpha"]
        beta_prior = prior["params"]["beta"]
        
        # Observations (0~1 범위 가정)
        successes = 0
        failures = 0
        
        for obs in observations:
            weight = obs["weight"]
            value = obs["value"]
            
            # Binary로 변환 (0.5 기준)
            if value > 0.5:
                successes += weight
            else:
                failures += weight
        
        # Beta 업데이트: α_post = α_prior + successes, β_post = β_prior + failures
        alpha_post = alpha_prior + successes
        beta_post = beta_prior + failures
        
        return {
            "type": "beta",
            "params": {
                "alpha": alpha_post,
                "beta": beta_post
            }
        }
    
    def _empirical_update(
        self,
        prior: Dict,
        observations: List[Dict]
    ) -> Dict:
        """Empirical Update (비모수)
        
        분포 타입이 불확실하거나 복잡할 때 사용.
        관측값들의 경험적 분포로 근사.
        
        Phase 3: 구현
        
        Args:
            prior: {...}
            observations: [...]
        
        Returns:
            posterior: {"type": "empirical", "samples": [...], "params": {...}}
        """
        # 관측값만 사용 (Prior 무시)
        values = np.array([obs["value"] for obs in observations])
        weights = np.array([obs["weight"] for obs in observations])
        
        # 가중 통계
        mean = np.average(values, weights=weights)
        std = np.sqrt(np.average((values - mean)**2, weights=weights))
        
        # Empirical 분포 (통계로 근사)
        return {
            "type": "empirical",
            "samples": values.tolist(),
            "params": {
                "mean": float(mean),
                "std": float(std),
                "n": len(values)
            }
        }
    
    def direct_replace(
        self,
        observations: List[Dict]
    ) -> Dict:
        """직접 대체 (Bayesian 아님)
        
        Prior 무시하고 관측값만으로 새 분포 생성.
        강한 Evidence가 있을 때 사용.
        
        Args:
            observations: [{"value": 50000, "weight": 1.0}, ...]
        
        Returns:
            distribution: {"type": "normal", "params": {...}}
        """
        # numpy array로 변환 (안전)
        values = np.array([obs["value"] for obs in observations])
        weights = np.array([obs["weight"] for obs in observations])
        
        # 가중 평균 및 표준편차
        mean = np.average(values, weights=weights)
        std = np.sqrt(np.average((values - mean)**2, weights=weights))
        
        return {
            "type": "normal",
            "params": {
                "mu": float(mean),
                "sigma": float(std)
            }
        }
