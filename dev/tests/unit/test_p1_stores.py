"""P1 stores (Phase 1) unit tests.

목표:
- ProjectContextStore(FocalActorContext) 저장/조회
- OutcomeStore 저장/조회
- ArtifactStore 저장/메타 조회
- context_binding / learning_engine 의 store 우선 로딩 확인
"""

from __future__ import annotations

from pathlib import Path

from cmis_core.context_binding import resolve_focal_actor_context_binding
from cmis_core.learning_engine import LearningEngine
from cmis_core.stores import ArtifactStore, OutcomeStore, ProjectContextStore
from cmis_core.types import FocalActorContext, Outcome


def test_project_context_store_roundtrip_versions(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    store = ProjectContextStore(project_root=project_root)

    v1 = FocalActorContext(
        project_context_id="PRJ-test-v1",
        version=1,
        previous_version_id=None,
        scope={"domain_id": "Adult_Language_Education_KR"},
        assets_profile={},
        baseline_state={},
        focal_actor_id=None,
        constraints_profile={},
        preference_profile={},
        lineage={},
    )
    store.save(v1)

    latest = store.get_latest("PRJ-test")
    assert latest is not None
    assert latest.project_context_id == "PRJ-test-v1"
    assert latest.version == 1

    v2 = FocalActorContext(
        project_context_id="PRJ-test-v2",
        version=2,
        previous_version_id=v1.project_context_id,
        scope=v1.scope,
        assets_profile=v1.assets_profile,
        baseline_state={"as_of": "2025-12-14"},
        focal_actor_id=None,
        constraints_profile=v1.constraints_profile,
        preference_profile=v1.preference_profile,
        lineage={"from_outcome_ids": ["OUT-1"]},
    )
    store.save(v2)

    latest2 = store.get_latest("PRJ-test")
    assert latest2 is not None
    assert latest2.project_context_id == "PRJ-test-v2"
    assert latest2.version == 2

    by_v1 = store.get_by_version("PRJ-test", 1)
    assert by_v1 is not None
    assert by_v1.project_context_id == "PRJ-test-v1"

    assert store.list_versions("PRJ-test") == [1, 2]

    store.close()


def test_outcome_store_roundtrip(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    store = OutcomeStore(project_root=project_root)

    out = Outcome(
        outcome_id="OUT-1",
        related_strategy_id=None,
        related_scenario_id=None,
        project_context_id="PRJ-test",
        as_of="2025-12-14",
        metrics={"MET-Revenue": 1234.0},
    )
    store.save(out)

    loaded = store.get("OUT-1")
    assert loaded is not None
    assert loaded.outcome_id == "OUT-1"
    assert loaded.metrics.get("MET-Revenue") == 1234.0

    store.close()


def test_artifact_store_put_json_and_meta(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    store = ArtifactStore(project_root=project_root)
    aid = store.put_json({"hello": "world"}, kind="test")

    meta = store.get_meta(aid)
    assert meta is not None
    assert meta["artifact_id"] == aid

    file_path = Path(meta["file_path"])
    assert file_path.exists()
    assert file_path.name.endswith(".json")

    store.close()


def test_context_binding_prefers_store_record(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    store = ProjectContextStore(project_root=project_root)
    v1 = FocalActorContext(
        project_context_id="PRJ-bind-v1",
        version=1,
        scope={},
        assets_profile={},
        baseline_state={},
        focal_actor_id=None,
        constraints_profile={},
        preference_profile={},
        lineage={},
    )
    store.save(v1)
    store.close()

    binding = resolve_focal_actor_context_binding("PRJ-bind", project_root=project_root)
    assert binding.context_id == "PRJ-bind-v1"
    assert binding.version == 1


def test_learning_engine_loads_from_stores(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    outcome_store = OutcomeStore(project_root=project_root)
    ctx_store = ProjectContextStore(project_root=project_root)

    out = Outcome(
        outcome_id="OUT-2",
        related_strategy_id=None,
        related_scenario_id=None,
        project_context_id="PRJ-learn",
        as_of="2025-12-14",
        metrics={"MET-N_customers": 42},
    )
    outcome_store.save(out)

    ctx = FocalActorContext(
        project_context_id="PRJ-learn-v1",
        version=1,
        scope={},
        assets_profile={},
        baseline_state={},
        focal_actor_id=None,
        constraints_profile={},
        preference_profile={},
        lineage={},
    )
    ctx_store.save(ctx)

    engine = LearningEngine(
        project_root=project_root,
        outcome_store=outcome_store,
        project_context_store=ctx_store,
    )

    loaded_out = engine._load_outcome("OUT-2")
    assert loaded_out is not None
    assert loaded_out.outcome_id == "OUT-2"

    loaded_ctx = engine._load_project_context("PRJ-learn")
    assert loaded_ctx is not None
    assert loaded_ctx.project_context_id == "PRJ-learn-v1"

    outcome_store.close()
    ctx_store.close()
