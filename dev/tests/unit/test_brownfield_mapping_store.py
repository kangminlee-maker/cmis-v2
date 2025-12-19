"""BF-03: MappingStore tests."""

from __future__ import annotations

from pathlib import Path

from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.mapping_store import MappingStore


def test_mapping_store_create_get_and_bump(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    conn = open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    store = MappingStore(conn)

    spec_v1 = {
        "normalization_defaults": {"currency": "KRW", "unit": "million_KRW"},
        "bindings": [{"sheet": "P&L", "range": "A1:C10", "columns": {"year": "A", "revenue": "B"}}],
    }
    mid1, ver1, digest1 = store.create(spec_v1)
    assert mid1.startswith("MAP-")
    assert ver1 == 1
    assert digest1.startswith("sha256:")

    rec1 = store.get(mid1, ver1)
    assert rec1 is not None
    assert rec1.mapping_digest == digest1
    assert rec1.spec == spec_v1

    # idempotent create (same spec -> reuse)
    mid2, ver2, digest2 = store.create({"mapping_id": "IGNORED", "mapping_version": 999, **spec_v1})
    assert (mid2, ver2, digest2) == (mid1, ver1, digest1)

    # bump version
    spec_v2 = dict(spec_v1)
    spec_v2["normalization_defaults"] = {"currency": "USD", "unit": "million_USD"}
    mid3, ver3, digest3 = store.bump_version(mid1, spec_v2)
    assert mid3 == mid1
    assert ver3 == 2
    assert digest3 != digest1

    latest = store.get_latest(mid1)
    assert latest is not None
    assert latest.mapping_version == 2
    assert latest.spec == spec_v2

    conn.close()
