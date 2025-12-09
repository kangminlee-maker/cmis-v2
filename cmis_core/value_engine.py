"""CMIS Value Engine

Metric 계산 및 Fusion 엔진
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from .graph import InMemoryGraph
from .types import MetricRequest, ValueRecord
from .config import CMISConfig


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
    
    def __init__(self, config: Optional[CMISConfig] = None):
        """
        Args:
            config: UMIS 설정 (None이면 기본 로드)
        """
        if config is None:
            config = CMISConfig()
        
        self.config = config
        self.metrics = config.metrics
        
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
        project_context_id: Optional[str] = None
    ) -> Tuple[List[ValueRecord], Dict[str, Any]]:
        """Metric 평가
        
        Args:
            graph: R-Graph
            metric_requests: Metric 요청 목록
            policy_ref: 품질 정책
            project_context_id: 프로젝트 컨텍스트 (선택)
        
        Returns:
            (value_records, value_program)
        """
        results = []
        
        for req in metric_requests:
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
            "engine": "ValueEngine_v1",
            "policy_ref": policy_ref,
            "project_context_id": project_context_id,
            "created_at": datetime.utcnow().isoformat(),
            "metric_ids": [r.metric_id for r in results],
        }
        
        return results, value_program
    
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
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return ValueRecord(
            metric_id=metric_id,
            context=context,
            point_estimate=value,
            quality=quality,
            lineage=lineage,
        )
