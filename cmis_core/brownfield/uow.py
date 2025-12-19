"""Brownfield UnitOfWork / Transaction manager (BF-02b).

목표:
- Brownfield commit(IMP/CUR/CUB/...)을 단일 트랜잭션으로 묶어
  "반쯤 커밋된 상태"를 방지합니다.

주의:
- 이 UnitOfWork는 단일 sqlite3.Connection을 전제로 합니다.
- Store 구현은 트랜잭션 내부에서 conn.commit()을 호출하지 않아야 합니다.
"""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3
from typing import Iterator


class UnitOfWork:
    """SQLite 트랜잭션 UnitOfWork."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """BEGIN/COMMIT/ROLLBACK를 보장합니다."""

        try:
            self.conn.execute("BEGIN")
            yield self.conn
            self.conn.commit()
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise
