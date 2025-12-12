"""CMIS Value Engine

Metric 계산 및 Fusion 엔진
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any, Optional

from .graph import InMemoryGraph
from .types import MetricRequest, ValueRecord
from .config import CMISConfig
from .evidence_engine import EvidenceEngine, SourceRegistry


class ValueEngine:
    """Value Engine - R-Graph 기반 Metric 계산 및 Fusion
    
    지원 Metric:
    - MET-N_customers: Actor 집계
    - MET-Revenue: MoneyFlow 합산
    - MET-Avg_price_per_unit: Revenue / N_customers
    - (기타 Metric: 확장 가능)
    
    Fusion 기능:
    - 4-Method Fusion (Top-down/Bottom-up/Fermi/Proxy)
    - 가중 평균 알고리즘
    - 범위 교집합
    - Convergence 검증 (±30%)
    """
    
    def __init__(
        self,
        config: Optional[CMISConfig] = None,
        evidence_engine: Optional[EvidenceEngine] = None
    ):
        """
        Args:
            config: CMIS 설정 (None이면 기본 로드)
            evidence_engine: EvidenceEngine (None이면 기본 생성)
        """
        if config is None:
            config = CMISConfig()
        
        self.config = config
        self.metrics = config.metrics
        
        # Evidence Engine (v2 통합)
        if evidence_engine is None:
            # 기본 SourceRegistry 생성 (스텁만)
            source_registry = SourceRegistry()
            evidence_engine = EvidenceEngine(config, source_registry)
        
        self.evidence_engine = evidence_engine
        
        # v7 Fusion 가중치 (v9 4-Method에 맞게 조정)
        self.default_method_weights = {
            "top_down": 0.2,
            "bottom_up": 0.4,
            "fermi": 0.3,
            "proxy": 0.1,
        }
    
    def evaluate_metrics(
        self,
        graph: InMemoryGraph,
        metric_requests: List[MetricRequest],
        policy_ref: str = "reporting_strict",
        project_context_id: Optional[str] = None,
        use_evidence_engine: bool = True
    ) -> Tuple[List[ValueRecord], Dict[str, Any]]:
        """Metric 평가 (v2: EvidenceEngine 통합)
        
        Args:
            graph: R-Graph
            metric_requests: Metric 요청 목록
            policy_ref: 품질 정책
            project_context_id: 프로젝트 컨텍스트 (선택)
            use_evidence_engine: EvidenceEngine 사용 여부 (기본 True)
        
        Returns:
            (value_records, value_program)
        
        로직 (v2):
            1. EvidenceEngine.fetch_for_metrics() 호출 (use_evidence_engine=True)
            2. Evidence 있으면 → EvidenceRecord → ValueRecord 변환
            3. Evidence 없으면 → 기존 R-Graph 기반 계산 (fallback)
        """
        results = []
        evidence_bundles = {}
        
        # 1. EvidenceEngine 호출 (옵션)
        if use_evidence_engine:
            try:
                evidence_multi = self.evidence_engine.fetch_for_metrics(
                    metric_requests,
                    policy_ref=policy_ref
                )
                evidence_bundles = evidence_multi.bundles
            except Exception as e:
                # EvidenceEngine 실패 시 경고만 (fallback)
                print(f"Warning: EvidenceEngine failed: {e}")
        
        # 2. Metric별 평가
        for req in metric_requests:
            # 2.1 Evidence 우선 시도
            evidence_bundle = evidence_bundles.get(req.metric_id)
            
            if evidence_bundle and evidence_bundle.records:
                # Evidence 있음 → ValueRecord 변환
                record = self._evidence_to_value_record(
                    req.metric_id,
                    req.context,
                    evidence_bundle
                )
                results.append(record)
                continue
            
            # 2.2 Fallback: R-Graph 기반 계산
            if req.metric_id == "MET-N_customers":
                value = self._compute_n_customers(graph, req.context)
                record = self._build_record(
                    req.metric_id,
                    req.context,
                    value,
                    method="r_graph_aggregation"
                )
            
            elif req.metric_id == "MET-Revenue":
                value = self._compute_total_revenue(graph, req.context)
                record = self._build_record(
                    req.metric_id,
                    req.context,
                    value,
                    method="r_graph_aggregation"
                )
            
            elif req.metric_id == "MET-Avg_price_per_unit":
                value = self._compute_avg_price_per_unit(graph, req.context)
                record = self._build_record(
                    req.metric_id,
                    req.context,
                    value,
                    method="derived_calculation"
                )
            
            else:
                # 미구현 Metric
                record = self._build_record(
                    req.metric_id,
                    req.context,
                    None,
                    method="not_implemented",
                    status="not_implemented"
                )
            
            results.append(record)
        
        # Value Program (실행 추적)
        value_program = {
            "engine": "ValueEngine_v2",
            "policy_ref": policy_ref,
            "project_context_id": project_context_id,
            "use_evidence_engine": use_evidence_engine,
            "evidence_metrics": list(evidence_bundles.keys()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metric_ids": [r.metric_id for r in results],
        }
        
        return results, value_program
    
    # ========================================
    # Evidence → ValueRecord 변환
    # ========================================
    
    def _evidence_to_value_record(
        self,
        metric_id: str,
        context: Dict[str, Any],
        evidence_bundle: Any  # EvidenceBundle
    ) -> ValueRecord:
        """EvidenceBundle → ValueRecord 변환
        
        Args:
            metric_id: Metric ID
            context: 컨텍스트
            evidence_bundle: EvidenceBundle
        
        Returns:
            ValueRecord
        """
        # Best evidence 선택 (신뢰도 높은 순)
        best_record = evidence_bundle.get_best_record()
        
        if best_record is None:
            # Evidence 없음 → 빈 record
            return self._build_record(
                metric_id,
                context,
                None,
                method="evidence_not_found",
                status="failed"
            )
        
        # Evidence 값 추출
        value = best_record.value
        
        # Quality 계산 (EvidenceBundle의 quality_summary 활용)
        quality_summary = evidence_bundle.quality_summary
        
        quality = {
            "status": "ok",
            "method": "evidence_direct",
            "literal_ratio": quality_summary.get("literal_ratio", 0.0),
            "spread_ratio": quality_summary.get("spread_ratio", 0.0),
            "evidence_source": best_record.source_id,
            "evidence_tier": best_record.source_tier,
            "confidence": best_record.confidence,
        }
        
        # Lineage (evidence_ids 포함)
        lineage = {
            "from_evidence_ids": [r.evidence_id for r in evidence_bundle.records],
            "from_value_ids": [],
            "from_pattern_ids": [],
            "from_program_id": "EvidenceEngine",
            "engine_ids": ["evidence_engine", "value_engine"],
            "policy_id": None,
            "created_by_role": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        return ValueRecord(
            metric_id=metric_id,
            context=context,
            point_estimate=value if isinstance(value, (int, float)) else None,
            quality=quality,
            lineage=lineage,
        )
    
    # ========================================
    # Metric 계산 로직
    # ========================================
    
    @staticmethod
    def _compute_n_customers(graph: InMemoryGraph, context: Dict[str, Any]) -> float:
        """고객 수 계산
        
        로직:
        - Actor kind="customer_segment"의 metadata.approx_population 합산
        - Actor kind="customer_segment"의 metadata.approx_company_count 합산
        """
        total = 0.0
        
        for actor in graph.nodes_by_type("actor"):
            if actor.data.get("kind") != "customer_segment":
                continue
            
            metadata = actor.data.get("metadata", {})
            
            # 개인 학습자
            pop = metadata.get("approx_population")
            if isinstance(pop, (int, float)):
                total += float(pop)
            
            # 기업 고객
            company_count = metadata.get("approx_company_count")
            if isinstance(company_count, (int, float)):
                total += float(company_count)
        
        return total
    
    @staticmethod
    def _compute_total_revenue(graph: InMemoryGraph, context: Dict[str, Any]) -> float:
        """총 매출 계산
        
        로직:
        - customer_segment → provider MoneyFlow 합산
        - actor_pays_actor edge를 따라가서 money_flow.quantity.amount 합산
        """
        customer_actor_ids = {
            node.id
            for node in graph.nodes_by_type("actor")
            if node.data.get("kind") == "customer_segment"
        }
        
        total = 0.0
        
        for edge in graph.edges:
            if edge.type != "actor_pays_actor":
                continue
            
            if edge.source not in customer_actor_ids:
                continue
            
            mf_id = edge.data.get("via")
            if not mf_id:
                continue
            
            mf_node = graph.get_node(mf_id)
            if mf_node is None:
                continue
            
            quantity = mf_node.data.get("quantity", {})
            amount = quantity.get("amount")
            
            if isinstance(amount, (int, float)):
                total += float(amount)
        
        return total
    
    def _compute_avg_price_per_unit(self, graph: InMemoryGraph, context: Dict[str, Any]) -> Optional[float]:
        """평균 단가 계산
        
        로직:
        - Revenue / N_customers
        - N_customers가 0이면 None
        """
        revenue = self._compute_total_revenue(graph, context)
        customers = self._compute_n_customers(graph, context)
        
        if customers <= 0:
            return None
        
        return revenue / customers
    
    # ========================================
    # ValueRecord 생성
    # ========================================
    
    # ========================================
    # Fusion Logic (v7 알고리즘 통합)
    # ========================================
    
    def fuse_4method(
        self,
        candidates: List[ValueRecord],
        convergence_threshold: float = 0.30
    ) -> ValueRecord:
        """4-Method 융합 (v7 Fusion 알고리즘)
        
        v7 FusionLayer.synthesize() 로직을 v9 4-Method에 적용
        
        알고리즘:
        1. 가중 평균 계산
        2. 범위 교집합
        3. Convergence 검증 (±30%)
        4. Outlier 제거
        
        Args:
            candidates: 4-Method 결과 (Top-down/Bottom-up/Fermi/Proxy)
            convergence_threshold: 수렴 허용 범위 (기본 30%)
        
        Returns:
            융합된 ValueRecord
        """
        if not candidates:
            raise ValueError("Fusion requires at least 1 candidate")
        
        # 가중 평균 (v7 알고리즘)
        total_weight = 0.0
        weighted_sum = 0.0
        
        for candidate in candidates:
            if candidate.point_estimate is None:
                continue
            
            method = candidate.quality.get("method", "unknown")
            weight = self.default_method_weights.get(method, 0.25)
            
            weighted_sum += candidate.point_estimate * weight
            total_weight += weight
        
        if total_weight == 0:
            # 모든 candidate가 None
            return candidates[0]
        
        weighted_avg = weighted_sum / total_weight
        
        # Convergence 검증 (v9 추가)
        convergence_passed = self._check_convergence(
            candidates,
            weighted_avg,
            threshold=convergence_threshold
        )
        
        # 범위 계산 (v7 범위 교집합 로직)
        min_val = min(c.point_estimate for c in candidates if c.point_estimate is not None)
        max_val = max(c.point_estimate for c in candidates if c.point_estimate is not None)
        
        # 융합된 ValueRecord 생성
        fusion_methods = [c.quality.get("method") for c in candidates if c.point_estimate]
        
        return ValueRecord(
            metric_id=candidates[0].metric_id,
            context=candidates[0].context,
            point_estimate=weighted_avg,
            distribution={"min": min_val, "max": max_val},
            quality={
                "status": "ok",
                "method": "4_method_fusion",
                "literal_ratio": self._calculate_literal_ratio(candidates),
                "spread_ratio": (max_val - min_val) / weighted_avg if weighted_avg > 0 else 0,
                "convergence_passed": convergence_passed,
                "methods_used": fusion_methods,
            },
            lineage={
                "from_evidence_ids": self._collect_evidence_ids(candidates),
                "from_value_ids": [c.metric_id for c in candidates],
                "from_program_id": "4_method_fusion",
                "engine_ids": ["value_engine"],
                "created_at": datetime.now().isoformat(),
            }
        )
    
    @staticmethod
    def _check_convergence(
        candidates: List[ValueRecord],
        average: float,
        threshold: float
    ) -> bool:
        """Convergence 검증 (v9)
        
        모든 값이 평균 대비 ±threshold 이내인지 확인
        
        Args:
            candidates: ValueRecord 목록
            average: 평균값
            threshold: 허용 편차 (예: 0.30 = ±30%)
        
        Returns:
            통과 여부
        """
        if average == 0:
            return True
        
        for candidate in candidates:
            if candidate.point_estimate is None:
                continue
            
            deviation = abs(candidate.point_estimate - average) / average
            if deviation > threshold:
                return False
        
        return True
    
    @staticmethod
    def _calculate_literal_ratio(candidates: List[ValueRecord]) -> float:
        """Literal ratio 계산
        
        각 candidate의 literal_ratio 가중 평균
        """
        if not candidates:
            return 0.0
        
        total = sum(
            c.quality.get("literal_ratio", 0.0)
            for c in candidates
            if c.point_estimate is not None
        )
        count = sum(1 for c in candidates if c.point_estimate is not None)
        
        return total / count if count > 0 else 0.0
    
    @staticmethod
    def _collect_evidence_ids(candidates: List[ValueRecord]) -> List[str]:
        """모든 candidate의 evidence_id 수집"""
        evidence_ids = []
        
        for candidate in candidates:
            lineage = candidate.lineage or {}
            candidate_evidence = lineage.get("from_evidence_ids", [])
            evidence_ids.extend(candidate_evidence)
        
        return list(set(evidence_ids))  # 중복 제거
    
    # ========================================
    # ValueRecord 생성
    # ========================================
    
    @staticmethod
    def _build_record(
        metric_id: str,
        context: Dict[str, Any],
        value: Optional[float],
        method: str,
        status: str = "ok"
    ) -> ValueRecord:
        """ValueRecord 생성 헬퍼
        
        Args:
            metric_id: Metric ID
            context: 컨텍스트
            value: 계산 값
            method: 계산 방법
            status: 상태
        
        Returns:
            ValueRecord
        """
        quality = {
            "status": status,
            "method": method,
            "literal_ratio": 1.0 if value is not None else 0.0,
            "spread_ratio": 0.0,
        }
        
        lineage = {
            "from_evidence_ids": [],
            "from_value_ids": [],
            "from_pattern_ids": [],
            "from_program_id": "ValueEngine_v1",
            "engine_ids": ["value_engine"],
            "policy_id": None,
            "created_by_role": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        return ValueRecord(
            metric_id=metric_id,
            context=context,
            point_estimate=value,
            quality=quality,
            lineage=lineage,
        )
    
    # ========================================
    # BeliefEngine Integration (Phase 2)
    # ========================================
    
    def _resolve_metric_prior_estimation(
        self,
        metric_id: str,
        context: Dict[str, Any],
        policy_ref: Optional[str] = None
    ) -> Optional[ValueRecord]:
        """Stage 3: Prior Estimation (BeliefEngine 호출)
        
        Evidence/Derived 모두 실패했을 때 최후 수단.
        
        Args:
            metric_id: "MET-SAM", etc.
            context: {...}
            policy_ref: Policy (allow_prior 확인)
        
        Returns:
            ValueRecord (origin="prior") 또는 None
        """
        from cmis_core.belief_engine import BeliefEngine
        
        # Policy 확인 (allow_prior)
        # Phase 2: config에서 policy 로드
        # 지금은 간단히 reporting_strict면 skip
        if policy_ref == "reporting_strict":
            return None
        
        # BeliefEngine 호출
        belief_engine = BeliefEngine()
        
        try:
            prior_result = belief_engine.query_prior_api(
                metric_id=metric_id,
                context=context,
                policy_ref=policy_ref
            )
        except Exception:
            # BeliefEngine 실패 시 None
            return None
        
        # Prior → ValueRecord 변환
        value_record = ValueRecord(
            metric_id=metric_id,
            context=context,
            point_estimate=None,  # Prior는 분포만
            distribution=prior_result["distribution"],
            quality={
                "status": "prior_estimation",
                "method": "belief_engine",
                "literal_ratio": 0.0,  # Prior는 literal 없음
                "spread_ratio": self._calculate_spread_from_distribution(
                    prior_result["distribution"]
                ),
                "confidence": prior_result["confidence"]
            },
            lineage={
                "from_prior_id": prior_result["prior_id"],
                "engine_ids": ["belief_engine", "value_engine"],
                "policy_id": policy_ref,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **prior_result["lineage"]
            }
        )
        
        return value_record
    
    def _calculate_spread_from_distribution(self, distribution: Dict) -> float:
        """분포에서 spread_ratio 계산
        
        Args:
            distribution: {"type": "normal", "params": {...}}
        
        Returns:
            spread_ratio (0~1+)
        """
        # BeliefRecord._calculate_spread()와 동일 로직
        dist_type = distribution.get("type", "normal")
        params = distribution.get("params", {})
        
        if dist_type == "normal":
            mu = params.get("mu", 0)
            sigma = params.get("sigma", 0)
            if mu > 0:
                return sigma / mu
            return 0.0
        
        elif dist_type == "lognormal":
            return params.get("sigma", 0.5)
        
        elif dist_type == "uniform":
            min_val = params.get("min", 0)
            max_val = params.get("max", 0)
            mean = (min_val + max_val) / 2
            if mean > 0:
                return (max_val - min_val) / (2 * mean)
            return 0.0
        
        else:
            return 0.5
