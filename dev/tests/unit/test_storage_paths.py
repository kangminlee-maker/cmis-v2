"""StoragePaths / local backends path rules unit tests.

목표:
- CMIS_STORAGE_ROOT + StoragePaths 규칙이 모든 런타임 경로를 안정적으로 결정하는지 확인합니다.
- 실제 인프라(Postgres/S3 등)로 전환하기 전, 로컬 구현이 일관된 경로 규칙을 갖는지 회귀를 방지합니다.
"""

from __future__ import annotations

from pathlib import Path

from cmis_core.stores.sqlite_base import StoragePaths
from cmis_core.reality_graph_backend import RealityGraphBackend
from cmis_core.evidence_store import SQLiteBackend


def test_storage_paths_resolve_creates_expected_dirs(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    paths = StoragePaths.resolve(project_root)

    assert paths.storage_root == tmp_path
    assert paths.cmis_dir == tmp_path / ".cmis"
    assert paths.db_dir == tmp_path / ".cmis" / "db"
    assert paths.runs_dir == tmp_path / ".cmis" / "runs"
    assert paths.artifacts_dir == tmp_path / ".cmis" / "artifacts"
    assert paths.cache_dir == tmp_path / ".cmis" / "cache"
    assert paths.results_dir == tmp_path / ".cmis" / "cache" / "results"
    assert paths.reality_graphs_dir == tmp_path / ".cmis" / "reality_graphs"
    assert paths.value_store_dir == tmp_path / ".cmis" / "value_store"
    assert paths.evidence_cache_db_path == tmp_path / ".cmis" / "evidence_cache.db"

    # directories are guaranteed
    for p in [
        paths.cmis_dir,
        paths.db_dir,
        paths.runs_dir,
        paths.artifacts_dir,
        paths.cache_dir,
        paths.results_dir,
        paths.reality_graphs_dir,
        paths.value_store_dir,
    ]:
        assert p.exists()
        assert p.is_dir()


def test_reality_graph_backend_default_dir_uses_storage_paths(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    paths = StoragePaths.resolve(project_root)
    backend = RealityGraphBackend(project_root=project_root)
    assert backend.storage_dir == paths.reality_graphs_dir
    assert backend.storage_dir.exists()
    assert backend.storage_dir.is_dir()


def test_evidence_sqlite_backend_default_db_path_uses_storage_paths(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    paths = StoragePaths.resolve(project_root)
    backend = SQLiteBackend(project_root=project_root)
    assert backend.db_path == paths.evidence_cache_db_path
    assert backend.db_path.exists()

    try:
        backend.conn.close()
    except Exception:
        pass


