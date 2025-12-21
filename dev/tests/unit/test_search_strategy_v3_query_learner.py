"""Search Strategy v3 QueryLearner unit tests (SSV3-12)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cmis_core.search_v3.query_learner import QueryLearnerV1
from cmis_core.search_v3.trace import SearchEvent
from cmis_core.stores import ArtifactStore


def test_query_learner_records_and_proposes(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    store = ArtifactStore(project_root=project_root)
    learner = QueryLearnerV1(artifact_store=store)

    events = [
        SearchEvent(
            event_id="EVT-1",
            search_run_id="SRCH-test",
            ts="2025-12-21T00:00:00Z",
            type="QueryGenerated",
            phase_id="generic_web",
            payload={
                "provider_id": "GenericWebSearch",
                "language": "ko",
                "region": "KR",
                "query_request_digest": "sha256:q1",
                "query_artifact_id": "ART-search_v3_query-abc",
                "generator": {"templates_used": ["{domain} {region} market size {year}"]},
            },
            budget_delta=None,
        ),
        SearchEvent(
            event_id="EVT-2",
            search_run_id="SRCH-test",
            ts="2025-12-21T00:00:01Z",
            type="SerpFetched",
            phase_id="generic_web",
            payload={
                "provider_id": "GenericWebSearch",
                "query_request_digest": "sha256:q1",
                "serp_artifact_id": "ART-search_v3_serp-xyz",
                "serp_digest": "sha256:serp1",
                "hit_count": 2,
            },
            budget_delta=None,
        ),
        SearchEvent(
            event_id="EVT-3",
            search_run_id="SRCH-test",
            ts="2025-12-21T00:00:02Z",
            type="DocumentFetched",
            phase_id="generic_web",
            payload={
                "url": "https://example.com/doc1",
                "canonical_url": "https://example.com/doc1",
                "doc_id": "DOC-1",
                "artifact_id": "ART-search_v3_doc-111",
                "content_digest": "sha256:doc1",
            },
            budget_delta=None,
        ),
        SearchEvent(
            event_id="EVT-4",
            search_run_id="SRCH-test",
            ts="2025-12-21T00:00:03Z",
            type="GateEvaluated",
            phase_id="generic_web",
            payload={"status": "met"},
            budget_delta=None,
        ),
        SearchEvent(
            event_id="EVT-5",
            search_run_id="SRCH-test",
            ts="2025-12-21T00:00:04Z",
            type="RunCompleted",
            phase_id=None,
            payload={"status": "success"},
            budget_delta=None,
        ),
    ]

    aid = learner.record_search_run(
        search_run_id="SRCH-test",
        metric_id="MET-TAM",
        policy_ref="decision_balanced",
        registry_digest="sha256:reg",
        initial_plan_digest="sha256:plan0",
        plan_digest_chain=["sha256:plan0"],
        events=events,
        trace_envelope_artifact_id="ART-search_v3_trace_envelope-aaa",
        events_artifact_id="ART-search_v3_events-bbb",
        run_summary={"queries_used": 1, "fetches_used": 1, "evidence_ids": []},
    )

    meta = store.get_meta(aid)
    assert meta is not None
    p = Path(str(meta["file_path"]))
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["metric_id"] == "MET-TAM"
    assert data["policy_ref"] == "decision_balanced"
    assert isinstance(data.get("attempts"), list) and len(data["attempts"]) == 1
    assert data["attempts"][0]["query_artifact_id"] == "ART-search_v3_query-abc"
    # ref-only: learner payload에는 query_text 자체를 복제하지 않음
    forbidden_keys = {"query", "query_text", "title", "snippet", "html", "raw_html", "raw_text"}
    assert forbidden_keys.isdisjoint(_collect_keys(data))

    proposal = learner.propose_registry_update(lookback_days=365)
    recs = proposal.get("recommendations") or {}
    assert "MET-TAM|decision_balanced" in recs
    templates = (recs["MET-TAM|decision_balanced"].get("templates") or [])
    assert any(t.get("template") == "{domain} {region} market size {year}" for t in templates)

    store.close()


def _collect_keys(obj: Any) -> set[str]:
    """중첩된 dict/list에서 key 이름을 수집합니다."""

    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(str(k))
            keys |= _collect_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            keys |= _collect_keys(v)
    return keys


