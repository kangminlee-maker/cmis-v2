"""UMIS v9 Workflow Orchestrator

structure_analysis 워크플로우 실행
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .types import StructureAnalysisInput, StructureAnalysisResult, MetricRequest
from .world_engine import WorldEngine
from .pattern_engine import PatternEngine
from .value_engine import ValueEngine
from .config import UMISConfig


class WorkflowOrchestrator:
    """Workflow Orchestrator - structure_analysis 실행
    
    3-Step 워크플로우:
    1. World Engine → R-Graph snapshot
    2. Pattern Engine → 패턴 매칭
    3. Value Engine → Metric 계산
    """
    
    def __init__(self, config: Optional[UMISConfig] = None, project_root: Optional[Path] = None):
        """
        Args:
            config: UMIS 설정
            project_root: 프로젝트 루트
        """
        if config is None:
            config = UMISConfig()
        
        self.config = config
        self.world_engine = WorldEngine(project_root)
        self.pattern_engine = PatternEngine()
        self.value_engine = ValueEngine(config)
    
    def run_structure_analysis(
        self,
        input_data: StructureAnalysisInput
    ) -> StructureAnalysisResult:
        """structure_analysis 워크플로우 실행
        
        Args:
            input_data: StructureAnalysisInput
        
        Returns:
            StructureAnalysisResult (R-Graph 구조 + Pattern + Metric)
        """
        start_time = time.time()
        
        # Step 1: R-Graph Snapshot
        print(f"[1/3] Loading R-Graph snapshot...")
        snapshot = self.world_engine.snapshot(
            domain_id=input_data.domain_id,
            region=input_data.region,
            segment=input_data.segment,
            as_of=input_data.as_of,
            project_context_id=input_data.project_context_id
        )
        
        # Graph overview 생성
        graph_overview = {
            "num_actors": snapshot.meta["num_actors"],
            "num_money_flows": snapshot.meta["num_money_flows"],
            "num_states": snapshot.meta.get("num_states", 0),
            "actor_types": self._count_actor_types(snapshot.graph),
            "total_money_flow_amount": self._sum_money_flows(snapshot.graph),
        }
        
        print(f"   ✓ {graph_overview['num_actors']} actors, {graph_overview['num_money_flows']} money flows")
        
        # Step 2: Pattern Matching
        print(f"[2/3] Matching patterns...")
        pattern_matches = self.pattern_engine.match_patterns(
            snapshot.graph,
            project_context_id=input_data.project_context_id
        )
        
        print(f"   ✓ {len(pattern_matches)} patterns matched")
        
        # Step 3: Metric Calculation
        print(f"[3/3] Calculating metrics...")
        
        # 핵심 Metric 계산
        metric_requests = [
            MetricRequest("MET-N_customers", {}),
            MetricRequest("MET-Revenue", {}),
            MetricRequest("MET-Avg_price_per_unit", {}),
        ]
        
        value_records, value_program = self.value_engine.evaluate_metrics(
            snapshot.graph,
            metric_requests,
            policy_ref="reporting_strict",
            project_context_id=input_data.project_context_id
        )
        
        print(f"   ✓ {len(value_records)} metrics calculated")
        
        # Result 조합
        execution_time = time.time() - start_time
        
        result = StructureAnalysisResult(
            meta={
                "domain_id": input_data.domain_id,
                "region": input_data.region,
                "segment": input_data.segment,
                "as_of": input_data.as_of or snapshot.meta.get("as_of"),
                "project_context_id": input_data.project_context_id,
            },
            graph_overview=graph_overview,
            pattern_matches=pattern_matches,
            metrics=value_records,
            execution_time=execution_time,
        )
        
        print(f"\n✅ structure_analysis 완료 ({execution_time:.2f}초)")
        
        return result
    
    @staticmethod
    def _count_actor_types(graph) -> Dict[str, int]:
        """Actor kind별 개수 집계"""
        counts = {}
        
        for actor in graph.nodes_by_type("actor"):
            kind = actor.data.get("kind", "unknown")
            counts[kind] = counts.get(kind, 0) + 1
        
        return counts
    
    @staticmethod
    def _sum_money_flows(graph) -> float:
        """MoneyFlow 총액 합산"""
        total = 0.0
        
        for mf in graph.nodes_by_type("money_flow"):
            quantity = mf.data.get("quantity", {})
            amount = quantity.get("amount")
            
            if isinstance(amount, (int, float)):
                total += float(amount)
        
        return total


# 편의 함수
def run_structure_analysis(
    domain_id: str,
    region: str,
    segment: Optional[str] = None,
    as_of: Optional[str] = None,
    project_context_id: Optional[str] = None
) -> StructureAnalysisResult:
    """structure_analysis 실행 편의 함수
    
    Args:
        domain_id: 도메인 ID
        region: 지역
        segment: 세그먼트 (선택)
        as_of: 기준일 (선택)
        project_context_id: 프로젝트 컨텍스트 (선택)
    
    Returns:
        StructureAnalysisResult
    """
    input_data = StructureAnalysisInput(
        domain_id=domain_id,
        region=region,
        segment=segment,
        as_of=as_of,
        project_context_id=project_context_id
    )
    
    orchestrator = WorkflowOrchestrator()
    return orchestrator.run_structure_analysis(input_data)
