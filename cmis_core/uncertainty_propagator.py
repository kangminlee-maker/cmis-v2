"""Uncertainty Propagator

불확실성 전파 및 Monte Carlo 시뮬레이션.

공식 기반 Metric 계산 시 입력 분포의 불확실성을 출력 분포로 전파.

Phase 1: 기본 Monte Carlo (eval() 사용)
Phase 3: AST evaluator, Sobol Sequence, Samples 분리 저장
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import uuid
import json

try:
    import asteval
    HAS_ASTEVAL = True
except ImportError:
    HAS_ASTEVAL = False

try:
    from scipy.stats import qmc
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class UncertaintyPropagator:
    """불확실성 전파 및 시뮬레이션

    Monte Carlo 시뮬레이션을 통해 입력 변수의 분포를
    공식을 거쳐 출력 분포로 변환.

    Phase 3: AST evaluator, Samples 분리, Sobol Sequence

    Usage:
        propagator = UncertaintyPropagator(artifact_store_path=Path("data/artifacts"))

        result = propagator.monte_carlo(
            formula="Revenue = N_customers * ARPU",
            input_distributions={
                "N_customers": {"type": "normal", "params": {"mu": 100000, "sigma": 10000}},
                "ARPU": {"type": "lognormal", "params": {"mu": 3.5, "sigma": 0.3}}
            },
            n_samples=10000,
            use_sobol=True  # Phase 3
        )

        # → {"percentiles": {...}, "statistics": {...}, "samples_ref": "ART-..."}
    """

    def __init__(self, artifact_store_path: Optional[Path] = None):
        """Initialize Uncertainty Propagator

        Args:
            artifact_store_path: artifact_store 경로 (Phase 3)
        """
        # Phase 3: artifact_store
        if artifact_store_path:
            self.artifact_store_path = artifact_store_path
            self.artifact_store_path.mkdir(parents=True, exist_ok=True)
        else:
            self.artifact_store_path = Path(__file__).parent.parent / "data" / "artifacts"
            self.artifact_store_path.mkdir(parents=True, exist_ok=True)

        # Phase 3: AST evaluator
        if HAS_ASTEVAL:
            self.evaluator = asteval.Interpreter()
        else:
            self.evaluator = None

    def monte_carlo(
        self,
        formula: str,
        input_distributions: Dict[str, Dict],
        n_samples: int = 10000,
        use_sobol: bool = False
    ) -> Dict:
        """Monte Carlo 시뮬레이션

        Args:
            formula: "Revenue = N_customers * ARPU" 형식
            input_distributions: {
                "N_customers": {"type": "normal", "params": {...}},
                "ARPU": {"type": "lognormal", "params": {...}}
            }
            n_samples: 샘플 개수 (기본 10,000)

        Returns:
            {
                "samples": [...],  # Phase 3에서 제거 예정
                "percentiles": {"p10": ..., "p50": ..., "p90": ...},
                "statistics": {"mean": ..., "std": ..., "cv": ...}
            }
        """
        # 1. 각 입력 변수의 샘플 생성
        samples = {}

        if use_sobol and HAS_SCIPY:
            # Sobol Sequence (Quasi-random)
            samples = self._sample_sobol(input_distributions, n_samples)
        else:
            # Random sampling
            for var_name, dist in input_distributions.items():
                samples[var_name] = self._sample_distribution(dist, n_samples)

        # 2. 공식 평가 (각 샘플)
        output_samples = []
        for i in range(n_samples):
            var_values = {var: samples[var][i] for var in samples}
            try:
                output = self._evaluate_formula(formula, var_values)
                output_samples.append(output)
            except Exception:
                # 계산 실패 시 skip (예: 음수 log 등)
                continue

        if not output_samples:
            raise ValueError(f"Monte Carlo failed: all samples resulted in errors")

        output_samples = np.array(output_samples)

        # 3. 통계 계산
        result = {
            "percentiles": {
                "p10": float(np.percentile(output_samples, 10)),
                "p25": float(np.percentile(output_samples, 25)),
                "p50": float(np.percentile(output_samples, 50)),
                "p75": float(np.percentile(output_samples, 75)),
                "p90": float(np.percentile(output_samples, 90))
            },
            "statistics": {
                "mean": float(np.mean(output_samples)),
                "std": float(np.std(output_samples)),
                "cv": float(np.std(output_samples) / np.mean(output_samples)) if np.mean(output_samples) > 0 else 0.0,
                "min": float(np.min(output_samples)),
                "max": float(np.max(output_samples))
            },
            "n_samples": len(output_samples)
        }

        # Phase 3: samples는 artifact_store에 저장
        samples_ref = self._save_samples_to_store(
            output_samples,
            formula,
            input_distributions
        )
        result["samples_ref"] = samples_ref

        return result

    def sensitivity_analysis(
        self,
        formula: str,
        input_distributions: Dict[str, Dict],
        output_samples: List[float]
    ) -> Dict[str, float]:
        """민감도 분석 (분산 기여도)

        각 입력 변수가 출력 분산에 얼마나 기여하는지 계산.

        Args:
            formula: "Revenue = N_customers * ARPU"
            input_distributions: {...}
            output_samples: monte_carlo()의 결과 samples

        Returns:
            {
                "N_customers": 0.6,  # 출력 분산의 60% 기여
                "ARPU": 0.4
            }
        """
        # 간이 버전: 각 변수의 분산과 출력 분산의 상관관계
        # 실제론 Sobol Indices 사용 (Phase 3)

        output_var = np.var(output_samples)
        if output_var == 0:
            # 출력 분산 없음 → 모두 0
            return {var: 0.0 for var in input_distributions.keys()}

        sensitivity = {}

        for var_name in input_distributions.keys():
            # 해당 변수 기여도 추정 (간이)
            # Phase 3에서 Sobol Indices로 교체
            var_contribution = 1.0 / len(input_distributions)
            sensitivity[var_name] = var_contribution

        # 정규화 (합 = 1.0)
        total = sum(sensitivity.values())
        if total > 0:
            sensitivity = {k: v/total for k, v in sensitivity.items()}

        return sensitivity

    def _sample_distribution(self, dist: Dict, n: int) -> np.ndarray:
        """분포에서 샘플 생성

        Args:
            dist: {"type": "normal", "params": {...}}
            n: 샘플 개수

        Returns:
            numpy array (n개 샘플)
        """
        dist_type = dist.get("type", "normal")
        params = dist.get("params", {})

        if dist_type == "normal":
            mu = params.get("mu", 0)
            sigma = params.get("sigma", 1)
            return np.random.normal(mu, sigma, n)

        elif dist_type == "lognormal":
            mu = params.get("mu", 0)
            sigma = params.get("sigma", 1)
            return np.random.lognormal(mu, sigma, n)

        elif dist_type == "uniform":
            min_val = params.get("min", 0)
            max_val = params.get("max", 1)
            return np.random.uniform(min_val, max_val, n)

        elif dist_type == "beta":
            alpha = params.get("alpha", 1)
            beta = params.get("beta", 1)
            return np.random.beta(alpha, beta, n)

        else:
            raise ValueError(f"Unsupported distribution type: {dist_type}")

    def _evaluate_formula(self, formula: str, var_values: Dict) -> float:
        """공식 평가

        Phase 3: asteval 사용 (안전)
        Fallback: eval() (asteval 없을 때)

        Args:
            formula: "Revenue = N_customers * ARPU"
            var_values: {"N_customers": 100000, "ARPU": 50}

        Returns:
            계산 결과 (float)
        """
        # 공식에서 "=" 이후 수식만 추출
        if "=" in formula:
            expr = formula.split("=")[1].strip()
        else:
            expr = formula

        # Phase 3: AST evaluator (안전)
        if HAS_ASTEVAL and self.evaluator:
            # 변수 설정
            for var, val in var_values.items():
                self.evaluator.symtable[var] = val

            # 평가
            try:
                result = self.evaluator(expr)
                if self.evaluator.error:
                    raise ValueError(f"Expression error: {self.evaluator.error}")
                return float(result)
            except Exception as e:
                raise ValueError(f"Formula evaluation failed: {formula}, error: {e}")

        else:
            # Fallback: eval() (보안 주의!)
            for var, val in var_values.items():
                expr = expr.replace(var, str(val))

            try:
                result = eval(expr)
                return float(result)
            except Exception as e:
                raise ValueError(f"Formula evaluation failed: {formula}, error: {e}")

    def _sample_sobol(
        self,
        input_distributions: Dict[str, Dict],
        n_samples: int
    ) -> Dict[str, np.ndarray]:
        """Sobol Sequence 기반 샘플링 (Quasi-random)

        Phase 3: 수렴 빠른 샘플링

        Args:
            input_distributions: {...}
            n_samples: 샘플 개수

        Returns:
            {"var1": samples1, "var2": samples2, ...}
        """
        if not HAS_SCIPY:
            # Fallback: random sampling
            return {
                var: self._sample_distribution(dist, n_samples)
                for var, dist in input_distributions.items()
            }

        # Sobol Sampler
        d = len(input_distributions)
        sampler = qmc.Sobol(d=d, scramble=True)

        # [0,1] 균등 샘플
        sobol_samples = sampler.random(n_samples)

        # 각 분포에 맞게 변환
        samples = {}
        for idx, (var_name, dist) in enumerate(input_distributions.items()):
            uniform_samples = sobol_samples[:, idx]
            samples[var_name] = self._transform_uniform_to_distribution(
                uniform_samples,
                dist
            )

        return samples

    def _transform_uniform_to_distribution(
        self,
        uniform_samples: np.ndarray,
        dist: Dict
    ) -> np.ndarray:
        """[0,1] 균등 샘플을 특정 분포로 변환

        Args:
            uniform_samples: [0,1] 범위 샘플
            dist: {"type": "normal", "params": {...}}

        Returns:
            변환된 샘플
        """
        from scipy import stats

        dist_type = dist.get("type", "normal")
        params = dist.get("params", {})

        if dist_type == "normal":
            mu = params.get("mu", 0)
            sigma = params.get("sigma", 1)
            return stats.norm.ppf(uniform_samples, loc=mu, scale=sigma)

        elif dist_type == "lognormal":
            mu = params.get("mu", 0)
            sigma = params.get("sigma", 1)
            return stats.lognorm.ppf(uniform_samples, s=sigma, scale=np.exp(mu))

        elif dist_type == "uniform":
            min_val = params.get("min", 0)
            max_val = params.get("max", 1)
            return min_val + (max_val - min_val) * uniform_samples

        elif dist_type == "beta":
            alpha = params.get("alpha", 1)
            beta = params.get("beta", 1)
            return stats.beta.ppf(uniform_samples, a=alpha, b=beta)

        else:
            # Fallback
            return uniform_samples

    def _save_samples_to_store(
        self,
        samples: np.ndarray,
        formula: str,
        input_distributions: Dict
    ) -> str:
        """Samples를 artifact_store에 저장

        Phase 3: raw samples는 별도 저장, ref만 반환

        Args:
            samples: Output samples
            formula: 공식
            input_distributions: 입력 분포

        Returns:
            artifact_id ("ART-samples-xxxx")
        """
        artifact_id = f"ART-samples-{uuid.uuid4().hex[:8]}"

        artifact = {
            "artifact_id": artifact_id,
            "type": "monte_carlo_samples",
            "formula": formula,
            "input_distributions": input_distributions,
            "samples": samples.tolist(),
            "n_samples": len(samples),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # JSON 저장
        filepath = self.artifact_store_path / f"{artifact_id}.json"
        with open(filepath, "w") as f:
            json.dump(artifact, f, indent=2)

        return artifact_id
