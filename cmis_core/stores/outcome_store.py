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
        # NOTE: 런타임(.cmis) 스토어는 개발 중 스키마 변경이 있을 수 있습니다.
        # focal_actor_context_id 컬럼이 없는 이전 스키마가 존재하면 가능한 범위에서 마이그레이션합니다.
        try:
            cur = self.conn.execute("PRAGMA table_info(outcomes)")
            cols = [row[1] for row in cur.fetchall() or []]
        except Exception:
            cols = []

        if cols and "focal_actor_context_id" not in cols:
            if "project_context_id" in cols:
                # data-preserving migration: recreate table with new column and copy values
                self.conn.execute("DROP TABLE IF EXISTS outcomes_new")
                self.conn.execute(
                    """
                    CREATE TABLE outcomes_new (
                        outcome_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        focal_actor_context_id TEXT,
                        related_strategy_id TEXT,
                        as_of TEXT,
                        record_json TEXT NOT NULL
                    )
                    """
                )
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO outcomes_new (
                        outcome_id, created_at, focal_actor_context_id, related_strategy_id, as_of, record_json
                    )
                    SELECT outcome_id, created_at, project_context_id, related_strategy_id, as_of, record_json
                    FROM outcomes
                    """
                )
                self.conn.execute("DROP TABLE IF EXISTS outcomes")
                self.conn.execute("ALTER TABLE outcomes_new RENAME TO outcomes")
                self.conn.commit()
            else:
                # unknown legacy schema: last resort reset
                self.conn.execute("DROP TABLE IF EXISTS outcomes")
                self.conn.execute("DROP INDEX IF EXISTS idx_outcomes_focal_actor_context_id")
                self.conn.execute("DROP INDEX IF EXISTS idx_outcomes_related_strategy_id")
                self.conn.commit()

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outcomes (
                outcome_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                focal_actor_context_id TEXT,
                related_strategy_id TEXT,
                as_of TEXT,
                record_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_focal_actor_context_id ON outcomes(focal_actor_context_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_related_strategy_id ON outcomes(related_strategy_id)")
        self.conn.commit()

        # record_json 내 legacy key(project_context_id) → focal_actor_context_id 마이그레이션(best-effort)
        try:
            cur = self.conn.execute("SELECT outcome_id, focal_actor_context_id, record_json FROM outcomes")
            rows = cur.fetchall() or []
        except Exception:
            rows = []

        updated = 0
        for outcome_id, fac_id, record_json in rows:
            try:
                data: Dict[str, Any] = json.loads(record_json or "{}")
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            changed = False
            if "project_context_id" in data:
                if "focal_actor_context_id" not in data:
                    data["focal_actor_context_id"] = data.get("project_context_id")
                data.pop("project_context_id", None)
                changed = True

            # column value sync (only if missing)
            if (fac_id is None or fac_id == "") and data.get("focal_actor_context_id"):
                fac_id = data.get("focal_actor_context_id")
                changed = True

            if not changed:
                continue

            self.conn.execute(
                "UPDATE outcomes SET focal_actor_context_id = ?, record_json = ? WHERE outcome_id = ?",
                (fac_id, json.dumps(data, ensure_ascii=False), str(outcome_id)),
            )
            updated += 1

        if updated:
            self.conn.commit()

    def save(self, outcome: Outcome) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(asdict(outcome), ensure_ascii=False)

        self.conn.execute(
            """
            INSERT OR REPLACE INTO outcomes (
                outcome_id, created_at, focal_actor_context_id, related_strategy_id, as_of, record_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                outcome.outcome_id,
                created_at,
                outcome.focal_actor_context_id,
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

    def list_by_focal_actor_context(self, focal_actor_context_id: str) -> List[str]:
        """특정 FocalActorContext에 연결된 outcome_id 목록."""

        cur = self.conn.execute(
            """
            SELECT outcome_id
            FROM outcomes
            WHERE focal_actor_context_id = ?
            ORDER BY created_at ASC
            """,
            (str(focal_actor_context_id),),
        )
        return [str(r[0]) for r in cur.fetchall()]

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
