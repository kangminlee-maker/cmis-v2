"""CMIS Workflow Orchestrator

canonical_workflows 기반 워크플로우 실행

v2.0: Generic workflow run + Role/Policy 통합
2025-12-11: Workflow CLI Phase 1
"""

from __future__ import annotations

import time
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List

from .types import (
    StructureAnalysisInput,
    StructureAnalysisResult,
    MetricRequest,
    GapCandidate
)
from .world_engine import WorldEngine
from .pattern_engine import PatternEngine
from .pattern_engine_v2 import PatternEngineV2
from .value_engine import ValueEngine
from .policy_engine import PolicyEngine
from .config import CMISConfig


class WorkflowOrchestrator:
    """Workflow Orchestrator v2

    역할:
    - canonical_workflows (YAML) 로딩 및 실행
    - role_id → policy_mode 해석
    - Generic workflow runner
    - Lineage 추적

    v1: structure_analysis만
    v2: Generic workflow run + canonical_workflows 통합
    """

    def __init__(
        self,
        config: Optional[CMISConfig] = None,
        project_root: Optional[Path] = None
    ):
        """
        Args:
            config: CMIS 설정
            project_root: 프로젝트 루트
        """
        if config is None:
            config = CMISConfig()

        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.config = config
        self.project_root = Path(project_root)

        # Policy Engine (v3.6.0)
        self.policy_engine = PolicyEngine(project_root)

        # Engines
        self.world_engine = WorldEngine(project_root)
        self.pattern_engine = PatternEngine()
        self.pattern_engine_v2 = PatternEngineV2()
        self.value_engine = ValueEngine(config)

        # canonical_workflows 로딩
        self.workflows = self._load_canonical_workflows()

    def _load_canonical_workflows(self) -> Dict[str, Any]:
        """canonical_workflows YAML 로딩

        v3.6.0: config/workflows.yaml로 분리

        Returns:
            workflow_id → workflow 정의 dict
        """
        workflows_yaml_path = self.project_root / "config" / "workflows.yaml"

        if not workflows_yaml_path.exists():
            print(f"Warning: workflows.yaml not found at {workflows_yaml_path}")
            return {}

        try:
            with open(workflows_yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            workflows_dict = data.get("canonical_workflows", {})

            return workflows_dict
        except Exception as e:
            print(f"Warning: Failed to load canonical_workflows: {e}")
            return {}

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

        value_records, value_program, metric_evals = self.value_engine.evaluate_metrics(
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

    def run_opportunity_discovery(
        self,
        domain_id: str,
        region: str,
        segment: Optional[str] = None,
        project_context_id: Optional[str] = None,
        top_n: int = 5,
        min_feasibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """opportunity_discovery 워크플로우 실행

        프로세스:
        1. World Engine → R-Graph snapshot
        2. Pattern Engine → 패턴 매칭
        3. Pattern Engine → Gap Discovery
        4. Value Engine → Gap별 Benchmark
        5. 정렬 및 Top-N

        Args:
            domain_id: 도메인 ID
            region: 지역
            segment: 세그먼트 (선택)
            project_context_id: 프로젝트 컨텍스트 (선택)
            top_n: 상위 N개 기회
            min_feasibility: 최소 feasibility (high|medium|low)

        Returns:
            Opportunity discovery 결과
        """
        start_time = time.time()

        # Step 1: R-Graph Snapshot
        print(f"[1/4] Loading R-Graph snapshot...")
        snapshot = self.world_engine.snapshot(
            domain_id=domain_id,
            region=region,
            segment=segment,
            as_of="latest",
            project_context_id=project_context_id
        )

        print(f"   ✓ {snapshot.meta['num_actors']} actors loaded")

        # Step 2: Pattern Matching
        print(f"[2/4] Matching patterns...")
        pattern_matches = self.pattern_engine_v2.match_patterns(
            snapshot.graph,
            project_context_id=project_context_id
        )

        print(f"   ✓ {len(pattern_matches)} patterns matched")

        # Step 3: Gap Discovery
        print(f"[3/4] Discovering gaps...")
        gaps = self.pattern_engine_v2.discover_gaps(
            snapshot.graph,
            project_context_id=project_context_id,
            precomputed_matches=pattern_matches
        )

        print(f"   ✓ {len(gaps)} gaps found")

        # Step 4: Feasibility 필터링
        if min_feasibility:
            feasibility_order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
            min_level = feasibility_order.get(min_feasibility, 0)

            gaps = [
                g for g in gaps
                if feasibility_order.get(g.feasibility, 0) >= min_level
            ]

            print(f"   ✓ {len(gaps)} gaps after feasibility filter (>= {min_feasibility})")

        # Top-N
        top_gaps = gaps[:top_n]

        # Step 5: Gap별 Benchmark (ValueEngine Prior 활용)
        print(f"[4/4] Calculating benchmarks for top {len(top_gaps)} gaps...")

        gap_with_benchmarks = []

        for gap in top_gaps:
            # Gap의 Pattern 조회
            pattern = self.pattern_engine_v2.get_pattern(gap.pattern_id)

            if pattern and pattern.benchmark_metrics:
                # Pattern benchmark → Prior
                benchmarks = {}
                for metric_id in pattern.benchmark_metrics[:3]:  # 상위 3개만
                    # TODO: ValueEngine Prior 활용
                    benchmarks[metric_id] = "N/A"

                gap_with_benchmarks.append({
                    "gap": gap,
                    "pattern": pattern,
                    "benchmarks": benchmarks
                })
            else:
                gap_with_benchmarks.append({
                    "gap": gap,
                    "pattern": pattern,
                    "benchmarks": {}
                })

        execution_time = time.time() - start_time

        result = {
            "meta": {
                "workflow_id": "opportunity_discovery",
                "domain_id": domain_id,
                "region": region,
                "segment": segment,
                "project_context_id": project_context_id,
                "execution_time": execution_time
            },
            "matched_patterns": pattern_matches,
            "gaps": gap_with_benchmarks,
            "total_gaps": len(gaps),
            "top_n": top_n,
            "completeness": "full"  # Phase 1: 항상 full
        }

        print(f"\n✅ opportunity_discovery 완료 ({execution_time:.2f}초)")

        return result

    def run_workflow(
        self,
        workflow_id: str,
        inputs: Dict[str, Any],
        role_id: Optional[str] = None,
        policy_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generic workflow 실행 (canonical_workflows 기반)

        프로세스:
        1. canonical_workflows에서 workflow 정의 로딩
        2. role_id → policy_mode 해석 (override 가능)
        3. workflow steps 순차 실행
        4. 결과 조합 및 lineage 기록

        Args:
            workflow_id: Workflow ID (예: "structure_analysis")
            inputs: 입력 dict (예: {"domain_id": "...", "region": "..."})
            role_id: Role 오버라이드 (None이면 workflow 기본값)
            policy_mode: Policy 오버라이드 (None이면 role 기본값)

        Returns:
            Workflow 결과

        Raises:
            ValueError: workflow_id 없음
        """
        # Workflow 정의 조회
        if workflow_id not in self.workflows:
            # 기본 제공 workflow인지 확인
            if workflow_id == "structure_analysis":
                return self._run_structure_analysis_from_inputs(inputs)
            elif workflow_id == "opportunity_discovery":
                return self._run_opportunity_discovery_from_inputs(inputs)
            else:
                raise ValueError(f"Unknown workflow_id: {workflow_id}")

        workflow_def = self.workflows[workflow_id]

        # role_id 결정
        if role_id is None:
            role_id = workflow_def.get("role_id", "structure_analyst")

        # policy_mode 결정 (PolicyEngine v2)
        if policy_mode is None:
            usage = workflow_def.get("usage")
            policy_mode = self.policy_engine.resolve_policy_id(role_id=role_id, usage=usage)

        # Generic 실행 (Phase 1: structure_analysis와 opportunity_discovery만)
        if workflow_id == "structure_analysis":
            return self._run_structure_analysis_from_inputs(
                inputs,
                role_id=role_id,
                policy_mode=policy_mode
            )
        elif workflow_id == "opportunity_discovery":
            return self._run_opportunity_discovery_from_inputs(
                inputs,
                role_id=role_id,
                policy_mode=policy_mode
            )
        else:
            return {
                "error": f"Workflow {workflow_id} not implemented yet",
                "workflow_id": workflow_id,
                "available": ["structure_analysis", "opportunity_discovery"]
            }

    def _run_structure_analysis_from_inputs(
        self,
        inputs: Dict[str, Any],
        role_id: str = "structure_analyst",
        policy_mode: str = "reporting_strict"
    ) -> Dict[str, Any]:
        """structure_analysis (generic 형식)"""
        input_data = StructureAnalysisInput(
            domain_id=inputs.get("domain_id"),
            region=inputs.get("region"),
            segment=inputs.get("segment"),
            as_of=inputs.get("as_of"),
            project_context_id=inputs.get("project_context_id")
        )

        result = self.run_structure_analysis(input_data)

        # Dict 변환 + role/policy 추가
        result_dict = result.to_dict()
        result_dict["meta"]["role_id"] = role_id
        result_dict["meta"]["policy_mode"] = policy_mode
        result_dict["meta"]["workflow_id"] = "structure_analysis"

        return result_dict

    def _run_opportunity_discovery_from_inputs(
        self,
        inputs: Dict[str, Any],
        role_id: str = "opportunity_designer",
        policy_mode: str = "exploration_friendly"
    ) -> Dict[str, Any]:
        """opportunity_discovery (generic 형식)"""
        result = self.run_opportunity_discovery(
            domain_id=inputs.get("domain_id"),
            region=inputs.get("region"),
            segment=inputs.get("segment"),
            project_context_id=inputs.get("project_context_id"),
            top_n=inputs.get("top_n", 5),
            min_feasibility=inputs.get("min_feasibility")
        )

        result["meta"]["role_id"] = role_id
        result["meta"]["policy_mode"] = policy_mode

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
