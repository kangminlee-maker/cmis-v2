"""Task execution for OrchestrationKernel.

주의:
- Cursor IDE 내부 도구(파일/터미널/웹)는 CMIS가 직접 호출하지 않습니다.
- 여기서의 실행은 CMIS 엔진/워크플로우 호출로 제한됩니다.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import time

from cmis_core.config import CMISConfig
from cmis_core.policy_engine import PolicyEngine
from cmis_core.types import MetricRequest, SourceTier
from cmis_core.workflow import WorkflowOrchestrator
from cmis_core.world_engine import WorldEngine
from cmis_core.value_engine import ValueEngine
from cmis_core.evidence_engine import EvidenceEngine, SourceRegistry
from cmis_core.evidence_store import create_evidence_store

from cmis_core.evidence.kosis_source import KOSISSource
from cmis_core.evidence.ecos_source import ECOSSource
from cmis_core.evidence.worldbank_source import WorldBankSource
from cmis_core.evidence.google_search_source import GoogleSearchSource

from .task import Task, TaskType


def build_default_source_registry(config: CMISConfig, enable_stub_source: bool = False) -> SourceRegistry:
    """기본 SourceRegistry 구성 (가능한 소스는 등록, 불가능하면 스킵).

    Args:
        config: CMISConfig (tool_and_resource_registry 기반 제약 반영)
        enable_stub_source: 테스트/개발용 stub source를 추가할지 여부
    """
    registry = SourceRegistry()

    tool_ids = set(config.list_tool_ids() or [])
    allow_http_fetch = ("http_fetch" in tool_ids) or (not tool_ids)
    allow_web_search = ("web_search" in tool_ids) or (not tool_ids)

    # Optional: stub source (테스트용)
    if enable_stub_source:
        # Stub-only 모드: 외부 네트워크/API 호출을 피하기 위해 네트워크 소스를 비활성화합니다.
        # (Cursor Agent Interface v2 테스트/회귀 러너에서 재현성을 우선합니다.)
        allow_http_fetch = False
        allow_web_search = False

        from cmis_core.evidence.sources import StubSource

        stub = StubSource(
            source_id="STUB",
            source_tier=SourceTier.CURATED_INTERNAL,
            stub_data={"value": 1234.0, "note": "stub"},
        )
        registry.register_source(stub.source_id, stub.source_tier.value, stub)

    # Official: KOSIS/ECOS/WorldBank (키 없으면 constructor에서 실패할 수 있음)
    if allow_http_fetch:
        for ctor, tier in [
            (lambda: KOSISSource(), SourceTier.OFFICIAL),
            (lambda: ECOSSource(), SourceTier.OFFICIAL),
            (lambda: WorldBankSource(), SourceTier.OFFICIAL),
        ]:
            try:
                src = ctor()
                registry.register_source(src.source_id, tier.value, src)
            except Exception:
                # 환경(API key 등) 미설정 시 graceful skip
                continue

    # Web: Google Search (선택)
    if allow_web_search:
        try:
            gs = GoogleSearchSource()
            registry.register_source(gs.source_id, gs.source_tier.value, gs)
        except Exception:
            pass

    return registry


class TaskExecutor:
    """Task 타입별 실행기"""

    def __init__(
        self,
        *,
        project_root: Optional[Path] = None,
        policy_engine: Optional[PolicyEngine] = None,
        workflow_orchestrator: Optional[WorkflowOrchestrator] = None,
        world_engine: Optional[WorldEngine] = None,
        evidence_engine: Optional[EvidenceEngine] = None,
        value_engine: Optional[ValueEngine] = None,
        enable_stub_source: bool = False,
    ) -> None:
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.project_root = Path(project_root)

        self.config = CMISConfig(self.project_root / "cmis.yaml")

        self.policy_engine = policy_engine or PolicyEngine(project_root=self.project_root)
        self.workflow_orchestrator = workflow_orchestrator or WorkflowOrchestrator(project_root=self.project_root)

        self.world_engine = world_engine or WorldEngine(project_root=self.project_root)

        if evidence_engine is None:
            registry = build_default_source_registry(self.config, enable_stub_source=enable_stub_source)
            evidence_store = create_evidence_store(backend_type="memory")
            evidence_engine = EvidenceEngine(self.config, registry, evidence_store=evidence_store)
        self.evidence_engine = evidence_engine

        self.value_engine = value_engine or ValueEngine(self.config, evidence_engine=self.evidence_engine)

    def execute(self, task: Task, run_context: Dict[str, Any], *, role_id: str, policy_id: str) -> Dict[str, Any]:
        start = time.time()

        if task.task_type == TaskType.RUN_WORKFLOW:
            wf_id = str(task.inputs.get("workflow_id"))
            inputs = dict(task.inputs.get("inputs") or {})
            # run_context 기본값을 inputs에 보강 (explicit input 우선)
            for k in ["domain_id", "region", "segment", "as_of", "project_context_id", "goal_id", "constraints"]:
                if k not in inputs and k in run_context:
                    inputs[k] = run_context[k]

            workflow_result = self.workflow_orchestrator.run_workflow(
                workflow_id=wf_id,
                inputs=inputs,
                role_id=role_id,
                policy_mode=policy_id,
            )

            return {
                "task_type": task.task_type.value,
                "workflow_id": wf_id,
                "workflow_result": workflow_result,
                "time_sec": time.time() - start,
            }

        if task.task_type == TaskType.COLLECT_EVIDENCE:
            metric_ids = list(task.inputs.get("target_metrics", []))
            force_refresh = bool(task.inputs.get("force_refresh", False))

            metric_requests = [MetricRequest(metric_id=m, context=self._metric_context(run_context)) for m in metric_ids]

            evidence_multi = self.evidence_engine.fetch_for_metrics(
                metric_requests=metric_requests,
                policy_ref=policy_id,
                use_cache=(not force_refresh),
            )

            evidence_ids = []
            for b in evidence_multi.bundles.values():
                for r in b.records:
                    evidence_ids.append(r.evidence_id)

            tool_calls = self._summarize_tool_calls_from_evidence_multi(evidence_multi)
            return {
                "task_type": task.task_type.value,
                "target_metrics": metric_ids,
                "evidence_ids": evidence_ids,
                "evidence_summary": evidence_multi.get_evidence_bundle_summary(),
                "tool_calls": tool_calls,
                "time_sec": time.time() - start,
            }

        if task.task_type == TaskType.COMPUTE_METRIC:
            metric_id = str(task.inputs.get("metric_id"))
            metric_context = self._metric_context(run_context)
            metric_req = MetricRequest(metric_id=metric_id, context=metric_context)

            # 1) Evidence 요약(PolicyEngine gate 입력용) 확보
            evidence_multi = self.evidence_engine.fetch_for_metrics(
                metric_requests=[metric_req],
                policy_ref=policy_id,
                use_cache=True,
            )
            evidence_summary = evidence_multi.get_evidence_bundle_summary()
            tool_calls = self._summarize_tool_calls_from_evidence_multi(evidence_multi)

            # 2) Graph snapshot 확보 (없어도 되지만, derived/fallback에 필요)
            snapshot = self._get_snapshot(run_context)

            # 3) ValueEngine 계산 (MetricEval 포함)
            value_records, value_program, metric_evals = self.value_engine.evaluate_metrics(
                snapshot.graph,
                [metric_req],
                policy_ref=policy_id,
                project_context_id=run_context.get("project_context_id"),
                use_evidence_engine=True,
            )

            value_record = value_records[0] if value_records else None
            metric_eval = metric_evals[0] if metric_evals else None

            # 4) Policy gates 평가 (metric 단위)
            policy_batch = self.policy_engine.evaluate_metrics(policy_id, evidence_summary, metric_evals)
            policy_check = policy_batch.by_metric.get(metric_id)

            return {
                "task_type": task.task_type.value,
                "metric_id": metric_id,
                "value_record": (None if value_record is None else asdict(value_record)),
                "metric_eval": (None if metric_eval is None else asdict(metric_eval)),
                "policy_check": (None if policy_check is None else policy_check.to_dict()),
                "evidence_summary": evidence_summary,
                "tool_calls": tool_calls,
                "value_program": value_program,
                "time_sec": time.time() - start,
            }

        return {
            "task_type": task.task_type.value,
            "error": f"Unsupported task_type: {task.task_type.value}",
            "time_sec": time.time() - start,
        }

    @staticmethod
    def _metric_context(run_context: Dict[str, Any]) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        for k in ["domain_id", "region", "segment", "year", "as_of", "company_name"]:
            if k in run_context and run_context[k] is not None:
                context[k] = run_context[k]
        return context

    def _get_snapshot(self, run_context: Dict[str, Any]):
        domain_id = run_context.get("domain_id")
        region = run_context.get("region")
        if not domain_id or not region:
            raise ValueError("domain_id and region are required to snapshot reality graph")

        segment = run_context.get("segment")
        as_of = run_context.get("as_of") or "latest"
        project_context_id = run_context.get("project_context_id")

        return self.world_engine.snapshot(
            domain_id=str(domain_id),
            region=str(region),
            segment=(None if segment is None else str(segment)),
            as_of=str(as_of),
            project_context_id=(None if project_context_id is None else str(project_context_id)),
        )

    def _tool_safety(self, tool_id: str) -> Optional[str]:
        tool = None
        if hasattr(self.config, "get_tool"):
            tool = self.config.get_tool(tool_id)
        if isinstance(tool, dict) and tool.get("safety"):
            return str(tool.get("safety"))
        return None

    @staticmethod
    def _map_source_to_tool_id(source_id: str) -> str:
        sid = str(source_id or "")
        if sid == "GoogleSearch":
            return "web_search"
        if sid == "STUB":
            return "python_runtime"
        return "http_fetch"

    def _summarize_tool_calls_from_evidence_multi(self, evidence_multi: Any) -> list[Dict[str, Any]]:
        """Evidence 결과로부터 tool call 요약을 생성합니다 (Phase 1 best-effort)."""
        bundles = getattr(evidence_multi, "bundles", None)
        if not isinstance(bundles, dict):
            return []

        counts: Dict[tuple[str, str, str], int] = {}
        for b in bundles.values():
            records = getattr(b, "records", None)
            if not isinstance(records, list):
                continue
            for r in records:
                source_id = str(getattr(r, "source_id", "") or "")
                source_tier = str(getattr(r, "source_tier", "") or "")
                tool_id = self._map_source_to_tool_id(source_id)
                key = (tool_id, source_id, source_tier)
                counts[key] = counts.get(key, 0) + 1

        ts = datetime.now(timezone.utc).isoformat()
        out: list[Dict[str, Any]] = []
        for (tool_id, source_id, source_tier), n in sorted(counts.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
            out.append(
                {
                    "ts": ts,
                    "tool_id": tool_id,
                    "operation": "evidence_fetch",
                    "source_id": source_id,
                    "source_tier": source_tier,
                    "count": n,
                    "safety": self._tool_safety(tool_id),
                }
            )

        return out[:20]

