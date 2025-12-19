"""CMIS Workflow Orchestrator

canonical_workflows 기반 워크플로우 실행

v2.0: Generic workflow run + Role/Policy 통합
2025-12-11: Workflow CLI Phase 1
"""

from __future__ import annotations

import time
import yaml
from pathlib import Path
from dataclasses import asdict
from typing import Optional, Dict, Any, List, Tuple, Union

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

        # Lazy engines (Phase 1: 생성 비용/의존성을 줄이기 위해 필요 시 생성)
        self._strategy_engine = None
        self._learning_engine = None

        # canonical_workflows 로딩
        self.workflows = self._load_canonical_workflows()

    def _get_strategy_engine(self):
        """StrategyEngine lazy loader."""
        if self._strategy_engine is None:
            from .strategy_engine import StrategyEngine

            self._strategy_engine = StrategyEngine(project_root=self.project_root)
        return self._strategy_engine

    def _get_learning_engine(self):
        """LearningEngine lazy loader."""
        if self._learning_engine is None:
            from .learning_engine import LearningEngine

            self._learning_engine = LearningEngine(config=self.config, project_root=self.project_root)
        return self._learning_engine

    @staticmethod
    def _coerce_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """CLI 등에서 들어온 입력을 best-effort로 타입 보정합니다.

        원칙:
        - Phase 1은 fail-open 입니다. 파싱 실패 시 원문 문자열을 유지합니다.
        - dict/list 형태는 YAML/JSON safe_load로 파싱을 시도합니다.
        - *_ids / outcome_ids는 콤마 구분 문자열을 리스트로 보정합니다.
        """
        out: Dict[str, Any] = {}

        for k, v in (inputs or {}).items():
            if isinstance(v, str):
                raw = v.strip()
                # list/dict 형태만 YAML/JSON 파싱 시도
                if raw.startswith("{") or raw.startswith("["):
                    try:
                        parsed = yaml.safe_load(raw)
                        out[k] = parsed
                        continue
                    except Exception:
                        pass

                if k.endswith("_ids") or k in {"outcome_ids", "strategy_ids"}:
                    if "," in raw:
                        out[k] = [s.strip() for s in raw.split(",") if s.strip()]
                        continue

                out[k] = v
            else:
                out[k] = v

        return out

    def _resolve_ref(self, value: Any, *, inputs: Dict[str, Any], prev: Dict[str, Any]) -> Any:
        """workflow ref 해석 (Phase 1).

        지원:
        - @input.<key>
        - @prev.<key>
        - @metric_sets.<set_name>
        """
        if not isinstance(value, str) or not value.startswith("@"):
            return value

        if value.startswith("@input."):
            key = value[len("@input.") :]
            return inputs.get(key)

        if value.startswith("@prev."):
            key = value[len("@prev.") :]
            return prev.get(key)

        if value.startswith("@metric_sets."):
            set_name = value[len("@metric_sets.") :]
            return list(self.config.get_metric_set(set_name))

        # 알 수 없는 ref는 그대로 반환 (fail-open)
        return value

    def _resolve_obj(self, obj: Any, *, inputs: Dict[str, Any], prev: Dict[str, Any]) -> Any:
        """dict/list를 포함해 재귀적으로 ref를 해석합니다."""
        if isinstance(obj, dict):
            return {k: self._resolve_obj(v, inputs=inputs, prev=prev) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._resolve_obj(v, inputs=inputs, prev=prev) for v in obj]
        return self._resolve_ref(obj, inputs=inputs, prev=prev)

    def _expand_metric_requests(
        self,
        metric_requests: Any,
        *,
        base_context: Dict[str, Any],
    ) -> List[MetricRequest]:
        """metric_requests 값을 MetricRequest 리스트로 확장합니다.

        지원 입력:
        - \"@metric_sets.<name>\" -> [\"MET-...\", ...]
        - [\"MET-...\", \"@metric_sets.<name>\", ...] (중첩 허용)
        """
        flat: List[str] = []

        def _flatten(x: Any) -> None:
            if x is None:
                return
            if isinstance(x, str):
                if x.startswith("@metric_sets."):
                    set_name = x[len("@metric_sets.") :]
                    flat.extend([str(m) for m in self.config.get_metric_set(set_name)])
                else:
                    flat.append(x)
                return
            if isinstance(x, list):
                for it in x:
                    _flatten(it)
                return
            # 그 외 타입은 무시(Phase 1 fail-open)

        _flatten(metric_requests)

        ctx = dict(base_context or {})
        return [MetricRequest(metric_id=str(mid), context=dict(ctx)) for mid in flat if mid]

    @staticmethod
    def _to_jsonable_value_records(value_records: List[Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for vr in value_records or []:
            try:
                out.append(
                    {
                        "metric_id": getattr(vr, "metric_id", None),
                        "context": getattr(vr, "context", None),
                        "point_estimate": getattr(vr, "point_estimate", None),
                        "distribution": getattr(vr, "distribution", None),
                        "distribution_ref": getattr(vr, "distribution_ref", None),
                        "quality": getattr(vr, "quality", None),
                        "lineage": getattr(vr, "lineage", None),
                    }
                )
            except Exception:
                continue
        return out

    @staticmethod
    def _to_jsonable_dataclass_list(items: List[Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for it in items or []:
            try:
                out.append(asdict(it))
            except Exception:
                continue
        return out

    def _execute_workflow_steps_v1(
        self,
        workflow_def: Dict[str, Any],
        *,
        inputs: Dict[str, Any],
        role_id: str,
        policy_mode: str,
    ) -> Dict[str, Any]:
        """canonical_workflows step을 순차 실행합니다 (Phase 1).

        반환값은 JSON 직렬화 가능해야 합니다(Workflow CLI가 json.dumps로 출력).
        """
        started = time.time()

        steps = workflow_def.get("steps", []) if isinstance(workflow_def, dict) else []
        if not isinstance(steps, list):
            steps = []

        # raw context (다음 step의 @prev 참조용)
        prev_raw: Dict[str, Any] = {}

        # json output context (최종 출력용)
        prev_json: Dict[str, Any] = {}

        step_reports: List[Dict[str, Any]] = []

        coerced_inputs = self._coerce_inputs(inputs)

        # base_context: MetricRequest 등에 들어갈 최소 context
        base_context = {
            "domain_id": coerced_inputs.get("domain_id"),
            "region": coerced_inputs.get("region"),
            "segment": coerced_inputs.get("segment"),
            "year": coerced_inputs.get("year"),
        }
        base_context = {k: v for k, v in base_context.items() if v is not None}

        for step in steps:
            if not isinstance(step, dict):
                continue
            step_id = str(step.get("step_id") or "")
            call = str(step.get("call") or "")
            with_params = step.get("with") if isinstance(step.get("with"), dict) else {}

            resolved_params = self._resolve_obj(with_params, inputs=coerced_inputs, prev=prev_raw)

            status = "ok"
            outputs_raw: Dict[str, Any] = {}
            outputs_json: Dict[str, Any] = {}
            error: Optional[str] = None

            try:
                if call == "world_engine.snapshot":
                    snapshot = self.world_engine.snapshot(
                        domain_id=resolved_params.get("domain_id"),
                        region=resolved_params.get("region"),
                        segment=resolved_params.get("segment"),
                        as_of=resolved_params.get("as_of"),
                        focal_actor_context_id=resolved_params.get("focal_actor_context_id"),
                    )
                    outputs_raw = {"reality_snapshot_ref": snapshot}
                    outputs_json = {
                        "reality_snapshot": {
                            "meta": dict(getattr(snapshot, "meta", {}) or {}),
                        }
                    }

                elif call == "pattern_engine.match_patterns":
                    snapshot = resolved_params.get("reality_snapshot_ref")
                    graph = getattr(snapshot, "graph", None)
                    matches = self.pattern_engine_v2.match_patterns(
                        graph,
                        focal_actor_context_id=resolved_params.get("focal_actor_context_id"),
                    )
                    outputs_raw = {"pattern_match_set_ref": matches, "pattern_matches": matches}
                    outputs_json = {"pattern_matches": self._to_jsonable_dataclass_list(matches)}

                elif call == "pattern_engine.discover_gaps":
                    snapshot = resolved_params.get("reality_snapshot_ref")
                    graph = getattr(snapshot, "graph", None)
                    precomputed = resolved_params.get("precomputed_matches")
                    gaps = self.pattern_engine_v2.discover_gaps(
                        graph,
                        focal_actor_context_id=resolved_params.get("focal_actor_context_id"),
                        precomputed_matches=precomputed,
                    )
                    outputs_raw = {"gap_set_ref": gaps, "gap_candidates": gaps}
                    outputs_json = {"gap_candidates": self._to_jsonable_dataclass_list(gaps)}

                elif call == "value_engine.evaluate_metrics":
                    # graph 확보: 명시적으로 전달되면 우선, 아니면 prev_raw에서 snapshot 사용
                    snapshot = resolved_params.get("reality_snapshot_ref") or prev_raw.get("reality_snapshot_ref")
                    graph = getattr(snapshot, "graph", None)
                    auto_snapshot = None
                    auto_snapshot_json = None
                    if graph is None:
                        # Phase 1 보정: workflow가 snapshot step을 포함하지 않는 경우,
                        # inputs의 domain_id/region으로 snapshot을 자동 생성합니다.
                        domain_id = coerced_inputs.get("domain_id")
                        region = coerced_inputs.get("region")
                        segment = coerced_inputs.get("segment")
                        focal_actor_context_id = resolved_params.get("focal_actor_context_id") or coerced_inputs.get("focal_actor_context_id")
                        if domain_id and region:
                            auto_snapshot = self.world_engine.snapshot(
                                domain_id=domain_id,
                                region=region,
                                segment=segment,
                                as_of="latest",
                                focal_actor_context_id=focal_actor_context_id,
                            )
                            graph = getattr(auto_snapshot, "graph", None)
                            auto_snapshot_json = {"meta": dict(getattr(auto_snapshot, "meta", {}) or {})}
                        else:
                            raise ValueError(
                                "value_engine.evaluate_metrics requires reality_snapshot_ref (or inputs domain_id+region for auto snapshot)"
                            )

                    mreqs = self._expand_metric_requests(
                        resolved_params.get("metric_requests"),
                        base_context=base_context,
                    )
                    policy_ref = str(resolved_params.get("policy_ref") or policy_mode)

                    value_records, value_program, metric_evals = self.value_engine.evaluate_metrics(
                        graph,
                        mreqs,
                        policy_ref=policy_ref,
                        focal_actor_context_id=resolved_params.get("focal_actor_context_id"),
                    )
                    outputs_raw = {
                        "value_bundle_ref": value_records,
                        "value_records": value_records,
                        "value_program": value_program,
                        "metric_evals": metric_evals,
                    }
                    outputs_json = {
                        "value_records": self._to_jsonable_value_records(value_records),
                        "value_program": (value_program if isinstance(value_program, dict) else {}),
                    }
                    if auto_snapshot is not None:
                        outputs_raw["reality_snapshot_ref"] = auto_snapshot
                        outputs_json["reality_snapshot"] = auto_snapshot_json or {}

                elif call == "strategy_engine.search_strategies":
                    constraints = resolved_params.get("constraints")
                    if not isinstance(constraints, dict):
                        constraints = {}

                    se = self._get_strategy_engine()
                    strategy_set_ref = se.search_strategies_api(
                        goal_id=str(resolved_params.get("goal_id") or ""),
                        constraints=constraints,
                        focal_actor_context_id=resolved_params.get("focal_actor_context_id"),
                    )
                    node = se.d_graph.get_node(strategy_set_ref)
                    strategy_ids = []
                    if node is not None and isinstance(getattr(node, "data", None), dict):
                        raw_ids = node.data.get("strategy_ids") or []
                        if isinstance(raw_ids, list):
                            strategy_ids = [str(x) for x in raw_ids]

                    outputs_raw = {
                        "strategy_set_ref": strategy_set_ref,
                        "strategy_ids": strategy_ids,
                    }
                    outputs_json = {
                        "strategy_set_ref": strategy_set_ref,
                        "strategy_ids": list(strategy_ids),
                    }

                elif call == "strategy_engine.evaluate_portfolio":
                    ids = resolved_params.get("strategy_ids")
                    if isinstance(ids, str):
                        ids = [s.strip() for s in ids.split(",") if s.strip()]
                    if not isinstance(ids, list):
                        ids = []

                    se = self._get_strategy_engine()
                    portfolio_eval_ref = se.evaluate_portfolio_api(
                        strategy_ids=[str(x) for x in ids],
                        policy_ref=str(resolved_params.get("policy_ref") or policy_mode),
                        focal_actor_context_id=resolved_params.get("focal_actor_context_id"),
                    )
                    outputs_raw = {"portfolio_eval_ref": portfolio_eval_ref}
                    outputs_json = {"portfolio_eval_ref": portfolio_eval_ref}

                elif call == "learning_engine.update_from_outcomes":
                    ids = resolved_params.get("outcome_ids")
                    if isinstance(ids, str):
                        ids = [s.strip() for s in ids.split(",") if s.strip()]
                    if not isinstance(ids, list):
                        ids = []

                    le = self._get_learning_engine()
                    res = le.update_from_outcomes_api([str(x) for x in ids])
                    outputs_raw = {"learning_results": res}
                    outputs_json = {"learning_results": (res if isinstance(res, dict) else {})}

                else:
                    raise ValueError(f"Unsupported workflow call: {call}")

            except Exception as e:
                status = "error"
                error = str(e)

            # update contexts
            prev_raw.update(outputs_raw)
            prev_json.update(outputs_json)

            step_reports.append(
                {
                    "step_id": step_id,
                    "call": call,
                    "status": status,
                    "error": error,
                    "outputs": outputs_json,
                }
            )

            if status != "ok":
                break

        result = {
            "meta": {
                "workflow_id": str(workflow_def.get("id") or ""),
                "role_id": role_id,
                "policy_mode": policy_mode,
                "execution_time_sec": (time.time() - started),
            },
            "steps": step_reports,
            "outputs": prev_json,
        }

        return result

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
            focal_actor_context_id=input_data.focal_actor_context_id,
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
            focal_actor_context_id=input_data.focal_actor_context_id,
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
            focal_actor_context_id=input_data.focal_actor_context_id,
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
                "focal_actor_context_id": input_data.focal_actor_context_id,
            },
            graph_overview=graph_overview,
            pattern_matches=pattern_matches,
            metrics=value_records,
            execution_time=execution_time,
        )

        print(f"\n[OK] structure_analysis 완료 ({execution_time:.2f}초)")

        return result

    def run_opportunity_discovery(
        self,
        domain_id: str,
        region: str,
        segment: Optional[str] = None,
        focal_actor_context_id: Optional[str] = None,
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
            focal_actor_context_id: FocalActorContext ID (선택)
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
            focal_actor_context_id=focal_actor_context_id,
        )

        print(f"   ✓ {snapshot.meta['num_actors']} actors loaded")

        # Step 2: Pattern Matching
        print(f"[2/4] Matching patterns...")
        pattern_matches = self.pattern_engine_v2.match_patterns(
            snapshot.graph,
            focal_actor_context_id=focal_actor_context_id,
        )

        print(f"   ✓ {len(pattern_matches)} patterns matched")

        # Step 3: Gap Discovery
        print(f"[3/4] Discovering gaps...")
        gaps = self.pattern_engine_v2.discover_gaps(
            snapshot.graph,
            focal_actor_context_id=focal_actor_context_id,
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
                "focal_actor_context_id": focal_actor_context_id,
                "execution_time": execution_time
            },
            "matched_patterns": pattern_matches,
            "gaps": gap_with_benchmarks,
            "total_gaps": len(gaps),
            "top_n": top_n,
            "completeness": "full"  # Phase 1: 항상 full
        }

        print(f"\n[OK] opportunity_discovery 완료 ({execution_time:.2f}초)")

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

        # Phase 1: 기존 구현(구조/기회)은 유지, 나머지는 step runner로 실행
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
            return self._execute_workflow_steps_v1(
                workflow_def,
                inputs=inputs,
                role_id=role_id,
                policy_mode=policy_mode,
            )

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
            focal_actor_context_id=inputs.get("focal_actor_context_id"),
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
            focal_actor_context_id=inputs.get("focal_actor_context_id"),
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
    focal_actor_context_id: Optional[str] = None,
) -> StructureAnalysisResult:
    """structure_analysis 실행 편의 함수

    Args:
        domain_id: 도메인 ID
        region: 지역
        segment: 세그먼트 (선택)
        as_of: 기준일 (선택)
        focal_actor_context_id: FocalActorContext ID (선택)

    Returns:
        StructureAnalysisResult
    """
    input_data = StructureAnalysisInput(
        domain_id=domain_id,
        region=region,
        segment=segment,
        as_of=as_of,
        focal_actor_context_id=focal_actor_context_id,
    )

    orchestrator = WorkflowOrchestrator()
    return orchestrator.run_structure_analysis(input_data)
