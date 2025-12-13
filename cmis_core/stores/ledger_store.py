"""LedgerStore (SQLite).

정본(ledger_store)은 run_id별로 ProjectLedger/ProgressLedger 스냅샷을 저장합니다.
Cursor UX는 이 스냅샷을 `.cmis/runs/<run_id>/`로 export(view)하여 소비합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json
from datetime import datetime, timezone

from .sqlite_base import StoragePaths, connect_sqlite


class LedgerStore:
    """SQLite 기반 LedgerStore"""

    def __init__(self, *, project_root: Optional[Path] = None, db_path: Optional[Path] = None) -> None:
        self.paths = StoragePaths.resolve(project_root)
        self.db_path = db_path or (self.paths.db_dir / "ledgers.db")
        self.conn = connect_sqlite(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        # NOTE: 실행 아티팩트는 런타임(.cmis)이며, 개발 중 스키마 변경이 있을 수 있습니다.
        # project_ledger_json 컬럼이 없는 이전 스키마가 존재하면 테이블을 재생성합니다(스냅샷은 폐기).
        try:
            cur = self.conn.execute("PRAGMA table_info(ledger_snapshots)")
            cols = [row[1] for row in cur.fetchall() or []]
        except Exception:
            cols = []

        if cols and "project_ledger_json" not in cols:
            self.conn.execute("DROP TABLE IF EXISTS ledger_snapshots")
            self.conn.execute("DROP INDEX IF EXISTS idx_ledger_run_id")
            self.conn.execute("DROP INDEX IF EXISTS idx_ledger_ts")
            self.conn.commit()

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                project_ledger_json TEXT NOT NULL,
                progress_ledger_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_run_id ON ledger_snapshots(run_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_ts ON ledger_snapshots(ts)")
        self.conn.commit()

    def save_snapshot(self, run_id: str, project_ledger: Dict[str, Any], progress_ledger: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO ledger_snapshots (run_id, ts, project_ledger_json, progress_ledger_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                run_id,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(project_ledger, ensure_ascii=False),
                json.dumps(progress_ledger, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def get_latest_snapshot(self, run_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            """
            SELECT ts, project_ledger_json, progress_ledger_json
            FROM ledger_snapshots
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (run_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        ts, project_json, progress_json = row
        project_ledger = json.loads(project_json or "{}")
        progress_ledger = json.loads(progress_json or "{}")
        return {
            "ts": ts,
            "project_ledger": project_ledger,
            "progress_ledger": progress_ledger,
        }

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

