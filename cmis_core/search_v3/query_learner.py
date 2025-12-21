"""Search Strategy v3 QueryLearner v1 (SSV3-12).

목표:
- Search v3 실행(trace)에서 "query 단위 시도" 요약을 생성해 저장합니다.
- 런타임에서 registry를 즉시 변경하지 않고, lookback 기반으로 "오프라인 registry 업데이트 제안"만 생성합니다.

핵심 원칙:
- 온라인 변경(automatic online mutation) 0
- ref-only: query_text/snippet/html 등 원문/대량 텍스트를 이 요약에 복제하지 않습니다.
  (query_artifact_id 등 참조만 저장)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cmis_core.search_v3.trace import SearchEvent
from cmis_core.stores.artifact_store import ArtifactStore


@dataclass(frozen=True)
class QueryAttemptSummary:
    """단일 query 시도의 요약(학습용).

    NOTE:
    - query 문자열 자체는 포함하지 않습니다. (query_artifact_id로 참조)
    """

    phase_id: Optional[str]
    provider_id: str
    language: str
    region: str
    query_request_digest: str
    query_artifact_id: str
    templates_used: List[str] = field(default_factory=list)
    serp_artifact_id: Optional[str] = None
    serp_digest: Optional[str] = None
    serp_hit_count: Optional[int] = None
    docs_fetched: int = 0
    gate_status: Optional[str] = None


class QueryLearnerV1:
    """QueryLearner v1.

    - record_search_run(): SearchTraceWriter 이벤트에서 query-attempt 요약을 생성해 ART로 저장
    - propose_registry_update(): lookback 기반으로 query_template 성능 요약/제안 생성(오프라인)
    """

    def __init__(
        self,
        *,
        artifact_store: ArtifactStore,
        kind: str = "search_v3_query_learner",
    ) -> None:
        self.artifacts = artifact_store
        self.kind = str(kind)

    # -------------------------
    # Recording
    # -------------------------

    def record_search_run(
        self,
        *,
        search_run_id: str,
        metric_id: str,
        policy_ref: str,
        registry_digest: str,
        initial_plan_digest: str,
        plan_digest_chain: List[str],
        events: List[SearchEvent],
        trace_envelope_artifact_id: str,
        events_artifact_id: str,
        run_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Search run의 이벤트로부터 learner 요약을 생성해 저장하고 artifact_id를 반환합니다."""

        attempts = self._summarize_query_attempts(events)
        payload: Dict[str, Any] = {
            "schema_version": 1,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "search_run_id": str(search_run_id),
            "metric_id": str(metric_id),
            "policy_ref": str(policy_ref),
            "registry_digest": str(registry_digest),
            "initial_plan_digest": str(initial_plan_digest),
            "plan_digest_chain": list(plan_digest_chain),
            "trace_envelope_artifact_id": str(trace_envelope_artifact_id),
            "events_artifact_id": str(events_artifact_id),
            "attempts": [self._attempt_to_dict(a) for a in attempts],
            "run_summary": dict(run_summary or {}),
        }
        return self.artifacts.put_json(payload, kind=self.kind)

    @staticmethod
    def _attempt_to_dict(a: QueryAttemptSummary) -> Dict[str, Any]:
        return {
            "phase_id": a.phase_id,
            "provider_id": a.provider_id,
            "language": a.language,
            "region": a.region,
            "query_request_digest": a.query_request_digest,
            "query_artifact_id": a.query_artifact_id,
            "templates_used": list(a.templates_used),
            "serp_artifact_id": a.serp_artifact_id,
            "serp_digest": a.serp_digest,
            "serp_hit_count": a.serp_hit_count,
            "docs_fetched": int(a.docs_fetched),
            "gate_status": a.gate_status,
        }

    def _summarize_query_attempts(self, events: List[SearchEvent]) -> List[QueryAttemptSummary]:
        """SearchEvent stream을 query-attempt 단위로 요약합니다."""

        attempts: List[QueryAttemptSummary] = []
        cur: Optional[QueryAttemptSummary] = None

        for ev in list(events or []):
            typ = str(getattr(ev, "type", "") or "")
            phase_id = getattr(ev, "phase_id", None)
            payload = getattr(ev, "payload", {}) or {}
            if not isinstance(payload, dict):
                payload = {}

            if typ == "QueryGenerated":
                # flush previous attempt
                if cur is not None:
                    attempts.append(cur)

                templates_used = payload.get("generator", {}).get("templates_used", []) if isinstance(payload.get("generator"), dict) else []
                if not isinstance(templates_used, list):
                    templates_used = []

                cur = QueryAttemptSummary(
                    phase_id=(str(phase_id) if phase_id is not None else None),
                    provider_id=str(payload.get("provider_id") or ""),
                    language=str(payload.get("language") or ""),
                    region=str(payload.get("region") or ""),
                    query_request_digest=str(payload.get("query_request_digest") or ""),
                    query_artifact_id=str(payload.get("query_artifact_id") or ""),
                    templates_used=[str(t) for t in templates_used if str(t).strip()],
                )
                continue

            if cur is None:
                # 아직 query-attempt가 시작되지 않았으면 스킵
                continue

            if typ == "SerpFetched":
                qd = str(payload.get("query_request_digest") or "")
                if qd and cur.query_request_digest and qd != cur.query_request_digest:
                    # 다른 query digest면 무시(방어)
                    continue
                cur = replace(
                    cur,
                    serp_artifact_id=(str(payload.get("serp_artifact_id") or "") or None),
                    serp_digest=(str(payload.get("serp_digest") or "") or None),
                    serp_hit_count=int(payload.get("hit_count") or 0),
                )
                continue

            if typ == "DocumentFetched":
                cur = replace(cur, docs_fetched=int(cur.docs_fetched) + 1)
                continue

            if typ == "GateEvaluated":
                cur = replace(cur, gate_status=(str(payload.get("status") or "") or None))
                continue

        if cur is not None:
            attempts.append(cur)

        # Drop obviously broken rows (missing digests/refs)
        out: List[QueryAttemptSummary] = []
        for a in attempts:
            if not a.query_request_digest or not a.query_artifact_id:
                continue
            out.append(a)
        return out

    # -------------------------
    # Proposal (offline)
    # -------------------------

    def propose_registry_update(self, *, lookback_days: int = 30, limit: int = 2000) -> Dict[str, Any]:
        """최근 lookback_days 동안의 learner 요약을 기반으로 registry 업데이트 제안을 생성합니다.

        반환값은 제안(리포트)이며, 런타임 registry를 직접 수정하지 않습니다.
        """

        since = datetime.now(timezone.utc) - timedelta(days=max(0, int(lookback_days)))
        since_iso = since.isoformat()

        records = self._load_records_since(since_iso, limit=limit)
        stats = self._aggregate(records)

        return {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lookback_days": int(lookback_days),
            "kind": self.kind,
            "recommendations": stats,
        }

    def _load_records_since(self, since_iso: str, *, limit: int) -> List[Dict[str, Any]]:
        """ArtifactStore에서 learner records를 조회/로딩합니다."""

        cur = self.artifacts.conn.execute(
            """
            SELECT artifact_id, created_at, file_path
            FROM artifacts
            WHERE kind = ? AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (self.kind, str(since_iso), int(limit)),
        )
        rows = cur.fetchall() or []
        out: List[Dict[str, Any]] = []
        for aid, created_at, file_path in rows:
            try:
                text = Path(str(file_path)).read_text(encoding="utf-8")
                data = json.loads(text or "{}")
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            data["_artifact_id"] = str(aid)
            data["_created_at"] = str(created_at)
            out.append(data)
        return out

    @staticmethod
    def _aggregate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """template별 단순 성능 집계를 만들고, 유지/검토/드랍 후보를 제안합니다."""

        # key: (metric_id, policy_ref, template)
        agg: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        for rec in records:
            metric_id = str(rec.get("metric_id") or "")
            policy_ref = str(rec.get("policy_ref") or "")
            attempts = rec.get("attempts") or []
            if not metric_id or not policy_ref or not isinstance(attempts, list):
                continue

            for a in attempts:
                if not isinstance(a, dict):
                    continue
                templates = a.get("templates_used") or []
                if not isinstance(templates, list) or not templates:
                    continue
                template = str(templates[0] or "").strip()
                if not template:
                    continue

                k = (metric_id, policy_ref, template)
                row = agg.get(k)
                if row is None:
                    row = {
                        "metric_id": metric_id,
                        "policy_ref": policy_ref,
                        "template": template,
                        "attempts": 0,
                        "with_hits": 0,
                        "with_docs": 0,
                        "gate_met": 0,
                    }
                    agg[k] = row

                row["attempts"] += 1

                hit_count = a.get("serp_hit_count")
                if isinstance(hit_count, int) and hit_count > 0:
                    row["with_hits"] += 1

                docs = a.get("docs_fetched")
                if isinstance(docs, int) and docs > 0:
                    row["with_docs"] += 1

                if str(a.get("gate_status") or "") == "met":
                    row["gate_met"] += 1

        # derive rates + action
        grouped: Dict[str, Dict[str, Any]] = {}
        for (metric_id, policy_ref, _template), row in agg.items():
            key = f"{metric_id}|{policy_ref}"
            bucket = grouped.get(key)
            if bucket is None:
                bucket = {"metric_id": metric_id, "policy_ref": policy_ref, "templates": []}
                grouped[key] = bucket

            attempts = int(row.get("attempts") or 0)
            with_hits = int(row.get("with_hits") or 0)
            gate_met = int(row.get("gate_met") or 0)
            hit_rate = (with_hits / attempts) if attempts else 0.0
            gate_met_rate = (gate_met / attempts) if attempts else 0.0

            action, rationale = _suggest_action(attempts, hit_rate, gate_met_rate)
            bucket["templates"].append(
                {
                    **row,
                    "hit_rate": round(hit_rate, 4),
                    "gate_met_rate": round(gate_met_rate, 4),
                    "action": action,
                    "rationale_codes": rationale,
                }
            )

        # sort templates per group
        for bucket in grouped.values():
            bucket["templates"] = sorted(
                list(bucket.get("templates") or []),
                key=lambda x: (-float(x.get("gate_met_rate") or 0.0), -float(x.get("hit_rate") or 0.0), -int(x.get("attempts") or 0)),
            )
        return grouped


def _suggest_action(attempts: int, hit_rate: float, gate_met_rate: float) -> tuple[str, List[str]]:
    """단순 룰 기반 action 제안."""

    a = int(attempts)
    hr = float(hit_rate)
    gr = float(gate_met_rate)

    if a >= 5 and hr < 0.1:
        return "consider_drop", ["low_hit_rate", "enough_samples"]
    if a >= 5 and gr >= 0.2:
        return "keep", ["gate_met_rate_ok", "enough_samples"]
    return "review", ["insufficient_signal"]


