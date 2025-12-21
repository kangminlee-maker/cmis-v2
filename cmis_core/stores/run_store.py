"""RunStore (SQLite).

정본(run_store)은 다음을 보관합니다.
- run 메타(request 스냅샷 요약)
- events stream
- decision log stream
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sqlite3
from datetime import datetime, timezone

from .sqlite_base import StoragePaths, connect_sqlite


class RunStore:
    """SQLite 기반 RunStore"""

    def __init__(self, *, project_root: Optional[Path] = None, db_path: Optional[Path] = None) -> None:
        self.paths = StoragePaths.resolve(project_root)
        self.db_path = db_path or (self.paths.db_dir / "runs.db")
        self.conn = connect_sqlite(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT,
                interface_id TEXT,
                query TEXT,
                role_id TEXT,
                policy_id TEXT,
                run_mode TEXT,
                context_json TEXT,
                summary_json TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_ts ON run_events(ts)")

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_run_decisions_run_id ON run_decisions(run_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_run_decisions_ts ON run_decisions(ts)")
        self.conn.commit()

    # ---------- Write API ----------

    def create_run(self, run: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_id, started_at, status, interface_id, query, role_id, policy_id, run_mode, context_json, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.get("run_id"),
                run.get("started_at") or datetime.now(timezone.utc).isoformat(),
                run.get("status"),
                run.get("interface_id"),
                run.get("query"),
                run.get("role_id"),
                run.get("policy_id"),
                run.get("run_mode"),
                json.dumps(run.get("context") or {}, ensure_ascii=False),
                json.dumps(run.get("summary") or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def append_event(self, run_id: str, event: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO run_events (run_id, ts, type, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                run_id,
                event.get("ts") or datetime.now(timezone.utc).isoformat(),
                event.get("type", "unknown"),
                json.dumps(event.get("payload") or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def append_decision(self, run_id: str, decision: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO run_decisions (run_id, ts, type, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                run_id,
                decision.get("ts") or datetime.now(timezone.utc).isoformat(),
                decision.get("type", "unknown"),
                json.dumps(decision.get("payload") or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def append_llm_selection_decision(self, run_id: str, payload: Dict[str, Any]) -> None:
        """LLM 모델 선택 결정을 run_decisions에 기록합니다.

        목적(비개발자 설명):
        - LLM 호출 자체는 비결정적일 수 있지만, "어떤 모델을 왜 골랐는지"는 항상 남아야 합니다.
        - 이후 리플레이/감사에서 동일 effective_policy/registry 조건이면 동일 선택이었는지 확인할 수 있습니다.

        저장 원칙:
        - run_store에는 프롬프트/응답 원문을 넣지 않습니다(민감 정보 가능).
        - 이 payload에는 digest, model_id, rationale_codes 같은 "참조/요약"만 포함해야 합니다.
        """

        safe_payload = dict(payload or {})
        self.append_decision(
            run_id,
            {
                "type": "llm_selection_decision",
                "ts": datetime.now(timezone.utc).isoformat(),
                "payload": safe_payload,
            },
        )

    def finalize_run(self, run_id: str, status: str, summary: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            UPDATE runs
            SET status = ?, ended_at = ?, summary_json = ?
            WHERE run_id = ?
            """,
            (
                status,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(summary or {}, ensure_ascii=False),
                run_id,
            ),
        )
        self.conn.commit()

    # ---------- Read API ----------

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            """
            SELECT run_id, started_at, ended_at, status, interface_id, query, role_id, policy_id, run_mode, context_json, summary_json
            FROM runs
            WHERE run_id = ?
            """,
            (run_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        (
            rid,
            started_at,
            ended_at,
            status,
            interface_id,
            query,
            role_id,
            policy_id,
            run_mode,
            context_json,
            summary_json,
        ) = row

        return {
            "run_id": rid,
            "started_at": started_at,
            "ended_at": ended_at,
            "status": status,
            "interface_id": interface_id,
            "query": query,
            "role_id": role_id,
            "policy_id": policy_id,
            "run_mode": run_mode,
            "context": json.loads(context_json or "{}"),
            "summary": json.loads(summary_json or "{}"),
        }

    def list_events(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            """
            SELECT ts, type, payload_json
            FROM run_events
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        )
        out: List[Dict[str, Any]] = []
        for ts, typ, payload_json in cur.fetchall():
            out.append({"ts": ts, "type": typ, "payload": json.loads(payload_json or "{}")})
        return out

    def list_decisions(self, run_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            """
            SELECT ts, type, payload_json
            FROM run_decisions
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        )
        out: List[Dict[str, Any]] = []
        for ts, typ, payload_json in cur.fetchall():
            out.append({"ts": ts, "type": typ, "payload": json.loads(payload_json or "{}")})
        return out

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

