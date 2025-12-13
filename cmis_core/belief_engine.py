"""Belief Engine

Prior/Belief 관리 및 불확실성 정량화 엔진.

CMIS의 9번째이자 마지막 엔진으로,
Evidence가 부족할 때 Prior Distribution을 제공하고,
Outcome 기반으로 Belief를 업데이트하는 역할.

핵심 원칙:
- Evidence-first, Prior-last
- Conservative by Default
- Context-aware
- Monotonic Improvability
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import uuid
import math

from cmis_core.types import BeliefRecord
from cmis_core.prior_manager import PriorManager
from cmis_core.belief_updater import BeliefUpdater
from cmis_core.uncertainty_propagator import UncertaintyPropagator


class BeliefEngine:
    """Belief Engine - Prior/Belief 관리 엔진

    Usage:
        engine = BeliefEngine()

        # Prior 조회
        prior = engine.query_prior_api(
            metric_id="MET-SAM",
            context={"domain_id": "...", "region": "KR"},
            policy_ref="decision_balanced"
        )

        # Belief 업데이트
        result = engine.update_belief_api(
            metric_id="MET-SAM",
            context={"domain_id": "...", "region": "KR"},
            observations=[{"value": 50000, "weight": 1.0}],
            update_mode="bayesian"
        )

        # 불확실성 전파
        mc_result = engine.propagate_uncertainty_api(
            formula="Revenue = N_customers * ARPU",
            input_distributions={...},
            n_samples=10000
        )
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize Belief Engine

        Args:
            project_root: 프로젝트 루트 경로 (Phase 2: value_store 경로)
        """
        self.project_root = project_root or Path(__file__).parent.parent

        # Core Components
        self.prior_manager = PriorManager(project_root=self.project_root)
        self.belief_updater = BeliefUpdater()
        self.uncertainty_propagator = UncertaintyPropagator()

        # Phase 2: PatternEngine 연동 (지금은 None)
        self.pattern_engine = None

    # ========================================
    # Public API (cmis.yaml 대응)
    # ========================================

    def query_prior_api(
        self,
        metric_id: str,
        context: Dict[str, Any],
        policy_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """Public API - Prior Distribution 조회

        ValueEngine의 prior_estimation 단계에서 호출.

        Args:
            metric_id: "MET-SAM", "MET-TAM", etc.
            context: {"domain_id": "...", "region": "...", "segment": "..."}
            policy_ref: "reporting_strict" | "decision_balanced" | "exploration_friendly"

        Returns:
            {
                "prior_id": "PRIOR-xxxx",
                "metric_id": "MET-SAM",
                "context": {...},
                "distribution": {...},
                "confidence": 0.5,
                "source": "pattern_benchmark",
                "policy_mode": "decision_balanced",
                "lineage": {...}
            }
        """
        # 1. 기존 Prior/Belief 조회
        prior = self.prior_manager.get_prior(metric_id, context)

        if prior is None:
            # 2. Prior 없으면 생성
            # Phase 2: Pattern 기반
            # Phase 1: Uninformative만
            prior = self._generate_uninformative_prior(metric_id, context)
            # 생성된 prior는 distribution_ref로 참조 가능해야 하므로 저장(Phase 2+)
            prior = self.prior_manager.save_prior(prior)

        # 3. Policy별 조정
        policy_mode = policy_ref or "decision_balanced"
        prior = self._apply_policy_adjustment(prior, policy_mode)

        return {
            "prior_id": prior.belief_id,
            "distribution_ref": f"VAL-{prior.belief_id}",
            "metric_id": prior.metric_id,
            "context": prior.context,
            "distribution": prior.distribution,
            "confidence": prior.confidence,
            "source": prior.source,
            "policy_mode": policy_mode,
            "lineage": prior.lineage
        }

    def update_belief_api(
        self,
        metric_id: str,
        context: Dict[str, Any],
        observations: List[Dict],
        update_mode: str = "bayesian"
    ) -> Dict[str, Any]:
        """Public API - Belief 업데이트

        LearningEngine이 Outcome 기반으로 호출.

        Args:
            metric_id: "MET-SAM", etc.
            context: {...}
            observations: [
                {"value": 50000, "weight": 1.0, "source": "EVD-001"},
                {"value": 48000, "weight": 0.8, "source": "OUT-002"},
                ...
            ]
            update_mode: "bayesian" | "replace"

        Returns:
            {
                "belief_id": "BELIEF-xxxx",
                "metric_id": "MET-SAM",
                "context": {...},
                "prior": {...},
                "posterior": {...},
                "delta": {
                    "mean_shift": +5000,
                    "sigma_reduction": -0.2,
                    "confidence_gain": +0.25
                },
                "lineage": {...}
            }
        """
        # 1. 기존 Prior/Belief 조회
        prior = self.prior_manager.get_prior(metric_id, context)
        if prior is None:
            prior = self._generate_uninformative_prior(metric_id, context)

        # 2. Update
        if update_mode == "bayesian":
            posterior = self.belief_updater.bayesian_update(
                prior.distribution,
                observations
            )
        else:  # replace
            posterior = self.belief_updater.direct_replace(observations)

        # 3. Delta 계산
        delta = self._calculate_delta(prior.distribution, posterior)

        # 4. 업데이트된 Belief 저장
        belief = self.prior_manager.save_belief(
            metric_id=metric_id,
            context=context,
            posterior=posterior,
            observations=observations,
            prior=prior
        )

        return {
            "belief_id": belief.belief_id,
            "metric_id": belief.metric_id,
            "context": belief.context,
            "prior": {
                "distribution": prior.distribution,
                "confidence": prior.confidence
            },
            "posterior": {
                "distribution": posterior,
                "confidence": belief.confidence
            },
            "delta": delta,
            "lineage": belief.lineage
        }

    def propagate_uncertainty_api(
        self,
        formula: str,
        input_distributions: Dict[str, Dict],
        n_samples: int = 10000
    ) -> Dict[str, Any]:
        """Public API - 불확실성 전파 (Monte Carlo)

        Args:
            formula: "Revenue = N_customers * ARPU"
            input_distributions: {
                "N_customers": {"type": "normal", "params": {...}},
                "ARPU": {"type": "lognormal", "params": {...}}
            }
            n_samples: 샘플 개수

        Returns:
            {
                "output_distribution": {
                    "type": "empirical",
                    "percentiles": {...},
                    "statistics": {...}
                },
                "sensitivity": {
                    "N_customers": 0.6,
                    "ARPU": 0.4
                }
            }
        """
        # Monte Carlo 시뮬레이션
        mc_result = self.uncertainty_propagator.monte_carlo(
            formula=formula,
            input_distributions=input_distributions,
            n_samples=n_samples
        )

        # 민감도 분석
        sensitivity = self.uncertainty_propagator.sensitivity_analysis(
            formula=formula,
            input_distributions=input_distributions,
            output_samples=mc_result["samples"]
        )

        return {
            "output_distribution": {
                "type": "empirical",
                "percentiles": mc_result["percentiles"],
                "statistics": mc_result["statistics"]
            },
            "sensitivity": sensitivity
        }

    # ========================================
    # Internal Methods
    # ========================================

    def _generate_prior_from_pattern(
        self,
        metric_id: str,
        context: Dict[str, Any]
    ) -> Optional[BeliefRecord]:
        """Pattern Benchmark 기반 Prior 생성

        Context 유사도 기반 Pattern Benchmark 필터링.

        Args:
            metric_id: "MET-SAM", etc.
            context: {"domain_id": "...", "region": "...", "segment": "..."}

        Returns:
            BeliefRecord 또는 None
        """
        # Phase 2: PatternEngine 없으면 None
        if self.pattern_engine is None:
            return None

        # 1. 유사 Pattern 찾기
        # Phase 2: 실제 구현 시 pattern_engine.match_patterns() 호출
        similar_patterns = []  # 스텁

        if not similar_patterns:
            return None

        # 2. Context 유사도 기반 가중치 조정
        benchmark_values = []

        for pattern_match in similar_patterns:
            pattern_id = pattern_match["pattern_id"]
            benchmark = self.prior_manager.load_pattern_benchmark(pattern_id)

            if benchmark and metric_id in benchmark.get("metrics", {}):
                # Context 유사도 계산
                context_similarity = self._calculate_context_similarity(
                    context,
                    benchmark.get("context", {})
                )

                # 구조 적합도 × Context 유사도
                pattern_score = pattern_match.get("score", 1.0)
                combined_weight = pattern_score * context_similarity

                benchmark_values.append({
                    "value": benchmark["metrics"][metric_id]["median"],
                    "weight": combined_weight,
                    "pattern_id": pattern_id,
                    "context_similarity": context_similarity
                })

        if not benchmark_values:
            return None

        # 3. 가중 평균
        total_weight = sum(b["weight"] for b in benchmark_values)
        if total_weight == 0:
            return None

        import numpy as np
        values = [b["value"] for b in benchmark_values]
        weights = [b["weight"] for b in benchmark_values]

        weighted_mean = np.average(values, weights=weights)
        weighted_std = np.std(values) * 1.5  # 보수적 확대

        # 4. BeliefRecord 생성
        belief = BeliefRecord(
            belief_id=f"PRIOR-{uuid.uuid4().hex[:8]}",
            metric_id=metric_id,
            context=context,
            distribution={
                "type": "lognormal",
                "params": {
                    "mu": math.log(weighted_mean) if weighted_mean > 0 else 0,
                    "sigma": math.log(1 + weighted_std / weighted_mean) if weighted_mean > 0 else 0.5
                }
            },
            confidence=min(total_weight / len(benchmark_values), 0.8),  # 최대 0.8
            source="pattern_benchmark",
            observations=[],
            n_observations=0,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            lineage={
                "from_pattern_ids": [b["pattern_id"] for b in benchmark_values],
                "context_similarities": [b["context_similarity"] for b in benchmark_values],
                "engine_ids": ["belief_engine"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )

        return belief

    def _calculate_context_similarity(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> float:
        """Context 유사도 계산

        주요 키별 가중치:
        - domain_id: 40%
        - region: 30%
        - segment: 20%
        - scale_tier: 10%

        Args:
            context1: {"domain_id": "...", "region": "KR", ...}
            context2: {"domain_id": "...", "region": "US", ...}

        Returns:
            similarity (0~1)
        """
        key_weights = {
            "domain_id": 0.4,
            "region": 0.3,
            "segment": 0.2,
            "scale_tier": 0.1
        }

        similarity = 0.0

        for key, weight in key_weights.items():
            if key in context1 and key in context2:
                if context1[key] == context2[key]:
                    # 완전 일치
                    similarity += weight
                elif key == "region" and self._is_similar_region(context1[key], context2[key]):
                    # 유사 지역 (절반 점수)
                    similarity += weight * 0.5
                # 불일치 시 0점
            # 키 없으면 0점

        return similarity

    def _is_similar_region(self, region1: str, region2: str) -> bool:
        """지역 유사도 판단

        같은 지역 그룹이면 True.

        Args:
            region1: "KR", "US", etc.
            region2: "KR", "JP", etc.

        Returns:
            bool
        """
        # 지역 그룹 정의
        region_groups = {
            "east_asia": ["KR", "JP", "CN", "TW"],
            "north_america": ["US", "CA"],
            "europe": ["UK", "DE", "FR", "IT", "ES"],
            "southeast_asia": ["SG", "TH", "VN", "ID", "MY"]
        }

        # 같은 그룹에 속하는지 확인
        for group_regions in region_groups.values():
            if region1 in group_regions and region2 in group_regions:
                return True

        return False

    def _generate_uninformative_prior(
        self,
        metric_id: str,
        context: Dict[str, Any]
    ) -> BeliefRecord:
        """Uninformative Prior 생성

        Evidence 전혀 없을 때 매우 넓은 분포.

        Args:
            metric_id: "MET-SAM", etc.
            context: {...}

        Returns:
            BeliefRecord (confidence=0.1)
        """
        # Metric category 추론 (간단 버전)
        # Phase 2: metrics_spec에서 로드
        if "TAM" in metric_id or "SAM" in metric_id or "SOM" in metric_id or "Revenue" in metric_id:
            category = "market_size"
        elif "ARPU" in metric_id or "price" in metric_id or "CAC" in metric_id:
            category = "unit_economics"
        elif "margin" in metric_id or "rate" in metric_id or "ratio" in metric_id:
            category = "ratio"
        else:
            category = "custom"

        # Category별 Uninformative Prior
        if category == "market_size":
            # 시장 규모: 1M ~ 1T (loguniform)
            distribution = {
                "type": "loguniform",
                "params": {
                    "min": 1e6,
                    "max": 1e12
                }
            }
        elif category == "unit_economics":
            # 단가: 100 ~ 1M (loguniform)
            distribution = {
                "type": "loguniform",
                "params": {
                    "min": 100,
                    "max": 1e6
                }
            }
        elif category == "ratio":
            # 비율: 0 ~ 1 (uniform)
            distribution = {
                "type": "uniform",
                "params": {
                    "min": 0.0,
                    "max": 1.0
                }
            }
        else:
            # 기타: 0 ~ 1B (loguniform)
            distribution = {
                "type": "loguniform",
                "params": {
                    "min": 1,
                    "max": 1e9
                }
            }

        return BeliefRecord(
            belief_id=f"PRIOR-{uuid.uuid4().hex[:8]}",
            metric_id=metric_id,
            context=context,
            distribution=distribution,
            confidence=0.1,  # 매우 낮은 신뢰도
            source="uninformative",
            observations=[],
            n_observations=0,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            lineage={
                "engine_ids": ["belief_engine"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )

    def _calculate_delta(
        self,
        prior_dist: Dict,
        posterior_dist: Dict
    ) -> Dict[str, Any]:
        """Prior vs Posterior Delta 계산

        Args:
            prior_dist: {"type": "normal", "params": {...}}
            posterior_dist: {"type": "normal", "params": {...}}

        Returns:
            {
                "mean_shift": +5000 | -2000,
                "sigma_reduction": -0.2 | +0.1,
                "confidence_gain": +0.25
            }
        """
        delta = {}

        # Normal 분포 가정 (Phase 3: 다른 분포 지원)
        if prior_dist.get("type") == "normal" and posterior_dist.get("type") == "normal":
            mu_prior = prior_dist["params"]["mu"]
            sigma_prior = prior_dist["params"]["sigma"]

            mu_post = posterior_dist["params"]["mu"]
            sigma_post = posterior_dist["params"]["sigma"]

            delta["mean_shift"] = mu_post - mu_prior
            delta["sigma_reduction"] = sigma_post - sigma_prior

            # 상대 변화
            if mu_prior > 0:
                delta["mean_shift_pct"] = (mu_post - mu_prior) / mu_prior
            if sigma_prior > 0:
                delta["sigma_reduction_pct"] = (sigma_post - sigma_prior) / sigma_prior

        return delta

    # ========================================
    # Policy/Quality Integration (Phase 2)
    # ========================================

    def _apply_policy_adjustment(
        self,
        prior: BeliefRecord,
        policy_mode: str
    ) -> BeliefRecord:
        """Policy에 따라 Prior 조정

        Args:
            prior: 원본 Prior
            policy_mode: "reporting_strict" | "decision_balanced" | "exploration_friendly"

        Returns:
            조정된 Prior (복사본)
        """
        # Prior 복사 (원본 보존)
        adjusted_prior = BeliefRecord(
            belief_id=prior.belief_id,
            metric_id=prior.metric_id,
            context=prior.context,
            distribution=prior.distribution.copy(),
            confidence=prior.confidence,
            source=prior.source,
            observations=prior.observations,
            n_observations=prior.n_observations,
            created_at=prior.created_at,
            updated_at=prior.updated_at,
            lineage=prior.lineage.copy()
        )

        if policy_mode == "reporting_strict":
            # reporting_strict: Prior 사용 최소화
            # - 신뢰도 절반
            # - 분포 2배 확대 (보수적)
            adjusted_prior.confidence *= 0.5
            adjusted_prior.distribution = self._widen_distribution(
                adjusted_prior.distribution,
                factor=2.0
            )
            adjusted_prior.lineage["policy_adjustment"] = "reporting_strict_conservative"

        elif policy_mode == "exploration_friendly":
            # exploration_friendly: Prior 적극 활용
            # - 신뢰도 유지
            # - 분포 20% 확대 (약간 보수적)
            adjusted_prior.distribution = self._widen_distribution(
                adjusted_prior.distribution,
                factor=1.2
            )
            adjusted_prior.lineage["policy_adjustment"] = "exploration_friendly_permissive"

        else:  # decision_balanced
            # 기본값 유지
            adjusted_prior.lineage["policy_adjustment"] = "decision_balanced_default"

        return adjusted_prior

    def _widen_distribution(
        self,
        dist: Dict,
        factor: float
    ) -> Dict:
        """분포 확대 (보수적으로)

        Args:
            dist: {"type": "normal", "params": {...}}
            factor: 확대 비율 (1.2 = 20% 확대)

        Returns:
            확대된 분포
        """
        dist_copy = dist.copy()
        params = dist_copy.get("params", {}).copy()

        if dist_copy.get("type") == "normal":
            # sigma 확대
            params["sigma"] = params.get("sigma", 0) * factor

        elif dist_copy.get("type") == "lognormal":
            # sigma 확대
            params["sigma"] = params.get("sigma", 0) * factor

        elif dist_copy.get("type") == "uniform":
            # 범위 확대
            min_val = params.get("min", 0)
            max_val = params.get("max", 0)
            center = (min_val + max_val) / 2
            half_range = (max_val - min_val) / 2

            params["min"] = center - half_range * factor
            params["max"] = center + half_range * factor

        dist_copy["params"] = params
        return dist_copy

    def _narrow_distribution(
        self,
        dist: Dict,
        target_spread: float
    ) -> Dict:
        """분포 좁히기 (Quality 제약 적용)

        Args:
            dist: {"type": "normal", "params": {...}}
            target_spread: 목표 spread_ratio

        Returns:
            좁아진 분포
        """
        dist_copy = dist.copy()
        params = dist_copy.get("params", {}).copy()

        if dist_copy.get("type") == "normal":
            mu = params.get("mu", 0)
            if mu > 0:
                # target_spread = sigma / mu
                params["sigma"] = mu * target_spread

        elif dist_copy.get("type") == "lognormal":
            # sigma를 target_spread로 설정
            params["sigma"] = target_spread

        dist_copy["params"] = params
        return dist_copy
