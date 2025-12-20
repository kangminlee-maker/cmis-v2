"""Search Strategy v3 trace/event writer (SSV3-02).

설계 원칙:
- SearchProgressLedger는 append-only 이벤트 스트림을 기본으로 합니다.
- ledger/event에는 원문/대량 텍스트를 저장하지 않습니다(ref-only).
- 원문(쿼리 텍스트, SERP raw, 문서 본문/HTML/PDF, 인용)은 ArtifactStore(ART-*)로만 저장합니다.

Design source:
- dev/docs/architecture/Search_Strategy_Design_v3.md (섹션 2, 1.0 ref-only 규칙)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, Iterable, List, Optional

from cmis_core.stores.artifact_store import ArtifactStore


class RefOnlyViolationError(ValueError):
    """ref-only 계약 위반(원문/대량 데이터가 event/ledger payload에 포함됨)."""


# NOTE:
# - "content_digest"처럼 정상 필드가 있기 때문에 substring 기반 금지는 하지 않습니다.
# - key "title"/"snippet"/"query" 등 명확히 원문 포함 가능성이 큰 key만 금지합니다.
FORBIDDEN_PAYLOAD_KEYS = {
    # query text
    "query",
    "query_text",
    # SERP raw fields
    "title",
    "snippet",
    # document raw
    "html",
    "raw_html",
    "text",
    "raw_text",
    "content",
    "raw_content",
    # bytes/raw
    "bytes",
    "raw_bytes",
    "pdf_bytes",
    # quotes
    "span_quote",
    "quote",
}


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def assert_ref_only_payload(obj: Any, *, where: str = "payload") -> None:
    """payload 내 금지 key가 포함되어 있지 않은지 재귀적으로 검증합니다."""

    for path, key in _iter_dict_keys(obj):
        if key in FORBIDDEN_PAYLOAD_KEYS:
            raise RefOnlyViolationError(f"ref-only violation: forbidden key '{key}' at {where}.{path}")


def _iter_dict_keys(obj: Any, *, _path: str = "") -> Iterable[tuple[str, str]]:
    """dict key를 (path, key) 형태로 재귀적으로 순회합니다."""

    if isinstance(obj, dict):
        for k, v in obj.items():
            k_str = str(k)
            next_path = f"{_path}.{k_str}" if _path else k_str
            yield (next_path, k_str)
            yield from _iter_dict_keys(v, _path=next_path)
        return

    if isinstance(obj, list):
        for i, v in enumerate(obj):
            next_path = f"{_path}[{i}]" if _path else f"[{i}]"
            yield from _iter_dict_keys(v, _path=next_path)
        return


@dataclass(frozen=True)
class SearchEvent:
    """SearchProgressLedger event (append-only)."""

    event_id: str
    search_run_id: str
    ts: str
    type: str
    phase_id: Optional[str]
    payload: Dict[str, Any] = field(default_factory=dict)
    budget_delta: Optional[Dict[str, Any]] = None


class SearchTraceWriter:
    """SearchStrategy v3 event writer.

    - emit()은 append-only로 이벤트를 누적합니다.
    - flush_events_jsonl()은 이벤트 목록을 NDJSON(JSONL)로 ART에 저장합니다.
    """

    def __init__(self, *, search_run_id: str, enforce_ref_only: bool = True) -> None:
        self.search_run_id = str(search_run_id)
        self.enforce_ref_only = bool(enforce_ref_only)
        self._events: List[SearchEvent] = []

    @property
    def events(self) -> List[SearchEvent]:
        return list(self._events)

    def emit(
        self,
        event_type: str,
        *,
        phase_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        budget_delta: Optional[Dict[str, Any]] = None,
        ts: Optional[str] = None,
    ) -> SearchEvent:
        payload_dict = dict(payload or {})

        if self.enforce_ref_only:
            assert_ref_only_payload(payload_dict)

        ev = SearchEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:12]}",
            search_run_id=self.search_run_id,
            ts=str(ts) if ts is not None else _utc_now_iso_z(),
            type=str(event_type),
            phase_id=str(phase_id) if phase_id is not None else None,
            payload=payload_dict,
            budget_delta=(dict(budget_delta) if budget_delta is not None else None),
        )
        self._events.append(ev)
        return ev

    def to_jsonl(self) -> str:
        """현재 누적 이벤트를 NDJSON(JSONL) 문자열로 직렬화합니다."""

        lines: List[str] = []
        for ev in self._events:
            lines.append(
                json.dumps(
                    {
                        "event_id": ev.event_id,
                        "search_run_id": ev.search_run_id,
                        "ts": ev.ts,
                        "type": ev.type,
                        "phase_id": ev.phase_id,
                        "payload": ev.payload,
                        "budget_delta": ev.budget_delta,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
        return "\n".join(lines) + ("\n" if lines else "")

    def flush_events_jsonl(self, store: ArtifactStore, *, kind: str = "search_v3_events") -> str:
        """events.jsonl을 ART로 저장하고 artifact_id를 반환합니다."""

        jsonl = self.to_jsonl()
        aid = store.put_bytes(
            jsonl.encode("utf-8"),
            kind=kind,
            mime_type="application/x-ndjson",
            original_filename="events.jsonl",
            meta={"search_run_id": self.search_run_id},
            dedupe=False,
        )
        return aid
