"""OutcomeStore (SQLite).

Outcome(OUT-*)는 LearningEngine이 참조하는 실행 결과 레코드입니다.

Phase 1 목표:
- Outcome 레코드를 sqlite에 저장/조회
- LearningEngine이 store 우선으로 로딩할 수 있도록 최소 API 제공
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from cmis_core.stores.sqlite_base import StoragePaths, connect_sqlite
from cmis_core.types import Outcome


class OutcomeStore:
    """Outcome(OUT-*) 저장소."""

    def __init__(self, *, project_root: Optional[Path] = None, db_path: Optional[Path] = None) -> None:
        self.paths = StoragePaths.resolve(project_root)
        self.db_path = db_path or (self.paths.db_dir / "outcomes.db")
        self.conn = connect_sqlite(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outcomes (
                outcome_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                project_context_id TEXT,
                related_strategy_id TEXT,
                as_of TEXT,
                record_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_project_context_id ON outcomes(project_context_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_related_strategy_id ON outcomes(related_strategy_id)")
        self.conn.commit()

    def save(self, outcome: Outcome) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(asdict(outcome), ensure_ascii=False)

        self.conn.execute(
            """
            INSERT OR REPLACE INTO outcomes (
                outcome_id, created_at, project_context_id, related_strategy_id, as_of, record_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                outcome.outcome_id,
                created_at,
                outcome.project_context_id,
                outcome.related_strategy_id,
                outcome.as_of,
                payload,
            ),
        )
        self.conn.commit()

    def get(self, outcome_id: str) -> Optional[Outcome]:
        cur = self.conn.execute(
            """
            SELECT record_json
            FROM outcomes
            WHERE outcome_id = ?
            """,
            (str(outcome_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        data: Dict[str, Any] = json.loads(row[0] or "{}")
        if not isinstance(data, dict):
            data = {}
        return Outcome(**data)

    def list_by_project_context(self, project_context_id: str) -> List[str]:
        """특정 프로젝트 컨텍스트에 연결된 outcome_id 목록."""

        cur = self.conn.execute(
            """
            SELECT outcome_id
            FROM outcomes
            WHERE project_context_id = ?
            ORDER BY created_at ASC
            """,
            (str(project_context_id),),
        )
        return [str(r[0]) for r in cur.fetchall()]

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
