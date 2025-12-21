"""Search Strategy v3 trace verifier (SSV3-11).

목표:
- trace envelope + events.jsonl(ART) 기반으로 최소 재현성/정합성을 검증합니다.
- ref-only 원칙에 따라, 검증 대상은 모두 ART 참조/다이제스트입니다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from cmis_core.stores.artifact_store import ArtifactStore


def verify_search_v3_trace(
    store: ArtifactStore,
    *,
    trace_envelope_artifact_id: str,
    events_artifact_id: str,
) -> List[str]:
    """Search v3 trace artifacts를 검증하고, 문제 목록을 반환합니다."""

    issues: List[str] = []

    env_path = store.get_path(trace_envelope_artifact_id)
    if env_path is None or not env_path.exists():
        issues.append("missing_trace_envelope_artifact")
        return issues

    events_path = store.get_path(events_artifact_id)
    if events_path is None or not events_path.exists():
        issues.append("missing_events_artifact")
        return issues

    envelope = _read_json(env_path)
    if not isinstance(envelope, dict):
        issues.append("invalid_trace_envelope_json")
        return issues

    initial = envelope.get("initial_plan_digest")
    final = envelope.get("final_plan_digest")
    chain = envelope.get("plan_digest_chain")
    if not isinstance(chain, list) or not chain:
        issues.append("missing_plan_digest_chain")
    else:
        if initial and chain[0] != initial:
            issues.append("plan_digest_chain_head_mismatch")
        if final and chain[-1] != final:
            issues.append("plan_digest_chain_tail_mismatch")

    # Events scan: referenced artifacts must exist
    for ev in _iter_ndjson(events_path):
        if not isinstance(ev, dict):
            issues.append("invalid_event_json")
            continue
        typ = str(ev.get("type") or "")
        payload = ev.get("payload") or {}
        if not isinstance(payload, dict):
            continue

        if typ == "QueryGenerated":
            _require_artifact_ref(store, payload.get("query_artifact_id"), issues, "missing_query_artifact")

        if typ == "SerpFetched":
            _require_artifact_ref(store, payload.get("serp_artifact_id"), issues, "missing_serp_artifact")

        if typ == "DocumentFetched":
            _require_artifact_ref(store, payload.get("artifact_id"), issues, "missing_document_artifact")

        if typ == "LinkExtracted":
            _require_artifact_ref(store, payload.get("links_artifact_id"), issues, "missing_links_artifact")

        if typ == "EvidenceCommitted":
            src_refs = payload.get("source_refs") or {}
            if isinstance(src_refs, dict):
                qids = src_refs.get("quote_artifact_ids") or []
                if isinstance(qids, list):
                    for aid in qids:
                        _require_artifact_ref(store, aid, issues, "missing_quote_artifact")

    return sorted(set(issues))


def _require_artifact_ref(store: ArtifactStore, aid: Any, issues: List[str], issue_code: str) -> None:
    if not aid:
        issues.append(issue_code)
        return
    p = store.get_path(str(aid))
    if p is None or not p.exists():
        issues.append(issue_code)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iter_ndjson(path: Path) -> List[Any]:
    out: List[Any] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                out.append(None)
    except Exception:
        return []
    return out
