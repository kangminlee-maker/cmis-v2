"""Runtime storage doctor (local-first).

목표:
- 실제 인프라(Postgres/S3 등) 전환 전에도, 현재 런타임 스토리지(`.cmis/`)의
  무결성과 참조 관계가 깨지지 않았는지 빠르게 점검할 수 있어야 합니다.

주의:
- 이 모듈은 기본적으로 "빠른 모드"만 제공합니다.
  - SQLite는 `PRAGMA quick_check`로 최소 무결성 검사
  - Artifact는 메타(DB) ↔ 파일 존재 여부/크기만 점검(sha256 재계산은 하지 않음)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sqlite3

from cmis_core.stores.sqlite_base import StoragePaths


@dataclass(frozen=True)
class StorageDoctorResult:
    """스토리지 점검 결과."""

    ok: bool
    issues: List[str]
    warnings: List[str]
    summary: Dict[str, Any]


def run_storage_doctor(
    *,
    project_root: Optional[Path] = None,
    include_orphan_files: bool = False,
) -> StorageDoctorResult:
    """런타임 스토리지(.cmis)의 무결성/참조 관계를 점검합니다.

    Args:
        project_root: 프로젝트 루트(선택). CMIS_STORAGE_ROOT가 설정되어 있으면 그 값이 우선됩니다.
        include_orphan_files: artifacts 디렉토리의 "DB에 없는 파일"도 경고로 보고할지 여부(기본 False).

    Returns:
        StorageDoctorResult
    """

    paths = StoragePaths.resolve(project_root)
    issues: List[str] = []
    warnings: List[str] = []
    summary: Dict[str, Any] = {
        "storage_root": str(paths.storage_root),
        "cmis_dir": str(paths.cmis_dir),
        "checked": {},
    }

    # 1) SQLite 무결성 검사 (best-effort)
    db_paths = [
        paths.db_dir / "runs.db",
        paths.db_dir / "ledgers.db",
        paths.db_dir / "contexts.db",
        paths.db_dir / "outcomes.db",
        paths.db_dir / "artifacts.db",
        paths.db_dir / "brownfield.db",
        paths.evidence_cache_db_path,  # legacy
    ]

    sqlite_checked = 0
    sqlite_ok = 0
    for p in db_paths:
        if not p.exists():
            continue
        sqlite_checked += 1
        errs = _sqlite_quick_check(p)
        if errs:
            issues.extend(errs)
        else:
            sqlite_ok += 1

    summary["checked"]["sqlite"] = {"checked": sqlite_checked, "ok": sqlite_ok}

    # 2) Artifact meta ↔ 파일 존재 여부
    art_issues, art_warnings, art_summary = _check_artifacts(paths, include_orphan_files=include_orphan_files)
    issues.extend(art_issues)
    warnings.extend(art_warnings)
    summary["checked"]["artifacts"] = art_summary

    return StorageDoctorResult(ok=(len(issues) == 0), issues=issues, warnings=warnings, summary=summary)


def _sqlite_quick_check(db_path: Path) -> List[str]:
    """SQLite quick_check.

    Returns:
        문제 없으면 [], 있으면 issue 문자열 리스트
    """

    p = Path(db_path)
    if not p.exists():
        return []

    conn: Optional[sqlite3.Connection] = None
    try:
        # read-only (non-invasive)
        conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, check_same_thread=False)
        cur = conn.execute("PRAGMA quick_check")
        rows = [str(r[0]) for r in (cur.fetchall() or []) if r and r[0] is not None]

        if len(rows) == 1 and rows[0].strip().lower() == "ok":
            return []

        # quick_check may return multiple error strings
        out: List[str] = []
        for r in rows:
            out.append(f"sqlite_corrupt:{p.name}:{r}")
        return out or [f"sqlite_corrupt:{p.name}:unknown"]
    except Exception as e:
        return [f"sqlite_check_failed:{p.name}:{e}"]
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _check_artifacts(paths: StoragePaths, *, include_orphan_files: bool) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """ArtifactStore 무결성 점검(빠른 모드)."""

    issues: List[str] = []
    warnings: List[str] = []
    summary: Dict[str, Any] = {
        "artifacts_db": str(paths.db_dir / "artifacts.db"),
        "artifacts_dir": str(paths.artifacts_dir),
        "rows": 0,
        "missing_files": 0,
        "bad_paths": 0,
        "orphan_files": 0,
    }

    db_path = paths.db_dir / "artifacts.db"
    if not db_path.exists():
        return issues, warnings, summary

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)

        if not _sqlite_has_table(conn, "artifacts"):
            warnings.append("artifact_store_table_missing:artifacts")
            return issues, warnings, summary

        cols = _sqlite_table_columns(conn, "artifacts")
        required = {"artifact_id", "file_path"}
        if not required.issubset(cols):
            warnings.append(f"artifact_store_schema_missing_cols:{sorted(list(required - cols))}")
            return issues, warnings, summary

        # Optional checks
        has_size = "size_bytes" in cols
        expected_paths: set[str] = set()

        cur = conn.execute("SELECT artifact_id, file_path, size_bytes FROM artifacts") if has_size else conn.execute("SELECT artifact_id, file_path, NULL FROM artifacts")
        rows = cur.fetchall() or []
        summary["rows"] = len(rows)

        for artifact_id, file_path, size_bytes in rows:
            aid = str(artifact_id)
            fp_raw = str(file_path or "")
            if not fp_raw:
                summary["bad_paths"] += 1
                issues.append(f"artifact_missing_path:{aid}")
                continue

            fp = Path(fp_raw)
            if not fp.is_absolute():
                # best-effort: interpret relative to artifacts_dir
                fp = (paths.artifacts_dir / fp).resolve()
            expected_paths.add(str(fp))

            try:
                if not fp.exists():
                    summary["missing_files"] += 1
                    issues.append(f"artifact_missing_file:{aid}:{fp}")
                    continue
                if has_size and size_bytes is not None:
                    try:
                        actual = fp.stat().st_size
                        if int(size_bytes) != int(actual):
                            warnings.append(f"artifact_size_mismatch:{aid}:meta={int(size_bytes)} actual={int(actual)}")
                    except Exception:
                        pass
            except Exception as e:
                issues.append(f"artifact_path_check_failed:{aid}:{e}")

        if include_orphan_files:
            try:
                actual_files = [p for p in paths.artifacts_dir.glob("*") if p.is_file()]
                orphan = [p for p in actual_files if str(p) not in expected_paths]
                summary["orphan_files"] = len(orphan)
                # 경고만: 자동 삭제는 사용자가 명시적으로 실행해야 함
                for p in orphan[:20]:
                    warnings.append(f"artifact_orphan_file:{p}")
                if len(orphan) > 20:
                    warnings.append(f"artifact_orphan_file:... and {len(orphan) - 20} more")
            except Exception as e:
                warnings.append(f"artifact_orphan_scan_failed:{e}")
    except Exception as e:
        warnings.append(f"artifact_store_check_failed:{e}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    return issues, warnings, summary


def _sqlite_has_table(conn: sqlite3.Connection, table: str) -> bool:
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (str(table),))
        row = cur.fetchone()
        return bool(row)
    except Exception:
        return False


def _sqlite_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return {str(r[1]) for r in (cur.fetchall() or []) if r and r[1] is not None}
    except Exception:
        return set()

