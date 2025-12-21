"""StoreFactory unit tests.

목표:
- StoreFactory가 StoragePaths/CMIS_STORAGE_ROOT 규칙을 따르는지 검증합니다.
- 각 store 생성이 정상 동작하고, 최소 동작(create/save/get)이 가능한지 확인합니다.
"""

from __future__ import annotations

from pathlib import Path

from cmis_core.stores import StoreFactory


def test_store_factory_paths_follow_storage_root(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    factory = StoreFactory(project_root=project_root)

    assert factory.paths.cmis_dir == tmp_path / ".cmis"
    assert factory.paths.db_dir == tmp_path / ".cmis" / "db"
    assert factory.paths.artifacts_dir == tmp_path / ".cmis" / "artifacts"


def test_store_factory_can_create_core_stores(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))
    factory = StoreFactory(project_root=project_root)

    run_store = factory.run_store()
    ledger_store = factory.ledger_store()
    art_store = factory.artifact_store()
    ctx_store = factory.focal_actor_context_store()
    out_store = factory.outcome_store()

    try:
        # 최소 동작: run 생성 + snapshot 저장 + artifact 저장
        run_store.create_run({"run_id": "RUN-test", "query": "q"})
        ledger_store.save_snapshot("RUN-test", {"hello": "world"}, {"overall_status": "ok"})
        aid = art_store.put_text("hello", kind="test")
        assert art_store.get_meta(aid) is not None

        # evidence cache store (memory)
        ev_store = factory.evidence_cache_store(backend_type="memory")
        assert ev_store is not None
    finally:
        run_store.close()
        ledger_store.close()
        art_store.close()
        ctx_store.close()
        out_store.close()

