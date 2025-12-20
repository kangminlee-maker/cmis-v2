"""Search Strategy v3 trace/event writer unit tests (SSV3-02)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cmis_core.search_v3.trace import RefOnlyViolationError, SearchTraceWriter
from cmis_core.stores import ArtifactStore


def test_trace_writer_rejects_query_text_in_payload() -> None:
    w = SearchTraceWriter(search_run_id="SRCH-test")
    with pytest.raises(RefOnlyViolationError):
        w.emit(
            "QueryGenerated",
            phase_id="generic_web",
            payload={"query": "raw query text must not be stored in events"},
        )


def test_trace_writer_allows_ref_only_payload() -> None:
    w = SearchTraceWriter(search_run_id="SRCH-test")
    ev = w.emit(
        "QueryGenerated",
        phase_id="generic_web",
        payload={
            "provider_id": "GenericWebSearch",
            "query_request_digest": "sha256:abc",
            "query_artifact_id": "ART-query-1",
        },
    )
    assert ev.search_run_id == "SRCH-test"
    assert len(w.events) == 1


def test_trace_writer_flushes_events_jsonl_to_artifact_store(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    store = ArtifactStore(project_root=project_root)
    w = SearchTraceWriter(search_run_id="SRCH-test")
    w.emit(
        "SerpFetched",
        phase_id="generic_web",
        payload={
            "provider_id": "GenericWebSearch",
            "query_request_digest": "sha256:q",
            "serp_artifact_id": "ART-serp-1",
            "serp_digest": "sha256:s",
            "hits": [{"url": "https://example.com", "canonical_url": "https://example.com", "rank": 1}],
        },
    )

    aid = w.flush_events_jsonl(store)
    meta = store.get_meta(aid)
    assert meta is not None
    p = Path(meta["file_path"])
    assert p.exists()
    assert p.suffix == ".jsonl"

    content = p.read_text(encoding="utf-8")
    assert content.count("\n") >= 1

    store.close()
