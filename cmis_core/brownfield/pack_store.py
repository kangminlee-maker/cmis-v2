"""BrownfieldPackStore (BPK) — append-only pack index (BF-08).

BrownfieldPack(BPK-...-vN)는 Brownfield 내부 데이터(CUB/PRJ 등)의 "참조 묶음"입니다.

원칙:
- Pack은 데이터 복제를 하지 않습니다. bundle/prj의 (id,digest,as_of) 같은 ref만 포함합니다.
- Pack은 append-only 버전입니다. 업데이트는 새 pack_version을 생성합니다.
- RUN의 pinning anchor는 PRJ vN이지만, Pack은 "선택 UX"와 "재사용"을 지원합니다.

MVP 범위(BF-08):
- packs 테이블에 spec_json 저장
- append-only versioning
- as_of_selector 기반으로 bundle 선택(최소 latest_validated/fixed_date/user_select)
- verify_pack: pack이 참조하는 CUB digest 검증
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional, Tuple

from cmis_core.brownfield.curated_store import CuratedBundleStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.digest import canonical_json


@dataclass(frozen=True)
class BrownfieldPackRecord:
    pack_id: str
    pack_version: int
    created_at: str
    spec: Dict[str, Any]


@dataclass(frozen=True)
class PackVerifyResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_as_of(s: str) -> Optional[date]:
    raw = str(s).strip()
    if not raw:
        return None

    # Allow YYYY-MM-DD (preferred)
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


def _bundle_as_of_key(bundle: Dict[str, Any]) -> Tuple[int, str]:
    """정렬/선택용 as_of key.

    Returns:
        (has_date, raw)
    """

    raw = str(bundle.get("as_of") or "")
    d = _parse_as_of(raw)
    if d is None:
        return (0, raw)
    return (1, d.isoformat())


def select_bundle_from_pack_spec(
    *,
    pack_spec: Dict[str, Any],
    as_of_selector: str = "latest_validated",
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Pack spec에서 bundle 엔트리(=ref dict)를 선택합니다."""

    spec = dict(pack_spec or {})
    bundles = spec.get("bundles")
    if not isinstance(bundles, list) or not bundles:
        raise ValueError("pack_spec.bundles is empty")

    entries: List[Dict[str, Any]] = [b for b in bundles if isinstance(b, dict)]
    if not entries:
        raise ValueError("pack_spec.bundles has no dict entries")

    mode = str(as_of_selector).strip()
    if mode not in {"latest_validated", "fixed_date", "user_select"}:
        raise ValueError(f"Unknown as_of_selector: {as_of_selector}")

    # Best-effort validated filter
    validated = [b for b in entries if str(b.get("status") or "validated") == "validated"]
    candidates = validated if validated else entries

    if mode == "latest_validated":
        # prefer as_of ordering, else list order
        by_date = [b for b in candidates if _parse_as_of(str(b.get("as_of") or "")) is not None]
        if by_date:
            by_date.sort(key=_bundle_as_of_key)
            return dict(by_date[-1])
        return dict(candidates[-1])

    # fixed_date / user_select require an as_of pivot
    pivot = str(as_of).strip() if as_of is not None else ""
    pivot_date = _parse_as_of(pivot)
    if not pivot_date:
        raise ValueError("as_of must be provided as YYYY-MM-DD for fixed_date/user_select")

    with_dates = []
    for b in candidates:
        d = _parse_as_of(str(b.get("as_of") or ""))
        if d is None:
            continue
        with_dates.append((d, b))

    if not with_dates:
        raise ValueError("No bundles with parseable as_of in pack_spec")

    # pick closest <= pivot; if none, pick earliest
    with_dates.sort(key=lambda x: x[0])
    le = [pair for pair in with_dates if pair[0] <= pivot_date]
    if le:
        return dict(le[-1][1])
    return dict(with_dates[0][1])


class BrownfieldPackStore:
    """brownfield.db packs 테이블 스토어."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, spec: Dict[str, Any], pack_id: Optional[str] = None) -> Tuple[str, int]:
        """Pack v1을 생성합니다."""

        pid = str(pack_id) if pack_id is not None else f"BPK-{uuid.uuid4().hex[:8]}"
        if not pid.startswith("BPK-"):
            raise ValueError("pack_id must start with 'BPK-'")

        created_at = _now()
        payload = canonical_json(dict(spec or {}))

        self.conn.execute(
            "INSERT INTO packs(pack_id, pack_version, created_at, spec_json) VALUES (?, ?, ?, ?)",
            (pid, 1, created_at, payload),
        )
        return pid, 1

    def append_version(self, *, pack_id: str, spec: Dict[str, Any]) -> Tuple[str, int]:
        """Pack의 새 버전을 append-only로 생성합니다."""

        latest = self.get_latest(str(pack_id))
        next_ver = 1 if latest is None else (int(latest.pack_version) + 1)

        created_at = _now()
        payload = canonical_json(dict(spec or {}))

        self.conn.execute(
            "INSERT INTO packs(pack_id, pack_version, created_at, spec_json) VALUES (?, ?, ?, ?)",
            (str(pack_id), int(next_ver), created_at, payload),
        )
        return str(pack_id), int(next_ver)

    def get(self, pack_id: str, pack_version: int) -> Optional[BrownfieldPackRecord]:
        cur = self.conn.execute(
            """
            SELECT created_at, spec_json
            FROM packs
            WHERE pack_id = ? AND pack_version = ?
            """,
            (str(pack_id), int(pack_version)),
        )
        row = cur.fetchone()
        if not row:
            return None

        created_at, spec_json = row
        try:
            spec = json.loads(spec_json or "{}")
        except Exception:
            spec = {}
        if not isinstance(spec, dict):
            spec = {}

        return BrownfieldPackRecord(
            pack_id=str(pack_id),
            pack_version=int(pack_version),
            created_at=str(created_at),
            spec=spec,
        )

    def get_latest(self, pack_id: str) -> Optional[BrownfieldPackRecord]:
        cur = self.conn.execute(
            """
            SELECT pack_version
            FROM packs
            WHERE pack_id = ?
            ORDER BY pack_version DESC
            LIMIT 1
            """,
            (str(pack_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self.get(str(pack_id), int(row[0]))

    def list_versions(self, pack_id: str) -> List[int]:
        cur = self.conn.execute(
            "SELECT pack_version FROM packs WHERE pack_id = ? ORDER BY pack_version ASC",
            (str(pack_id),),
        )
        return [int(r[0]) for r in (cur.fetchall() or [])]


def verify_pack(
    *,
    project_root: Any,
    pack_id: str,
    pack_version: Optional[int] = None,
    brownfield_conn: Optional[sqlite3.Connection] = None,
) -> PackVerifyResult:
    """Pack이 참조하는 CUB들이 존재하며 digest가 일치하는지 검증합니다."""

    errors: List[str] = []
    warnings: List[str] = []

    conn = brownfield_conn or open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    store = BrownfieldPackStore(conn)
    rec = store.get_latest(pack_id) if pack_version is None else store.get(pack_id, int(pack_version))
    if rec is None:
        return PackVerifyResult(ok=False, errors=[f"Pack not found: {pack_id}{'' if pack_version is None else f'-v{pack_version}'}"], warnings=[])

    bundles = rec.spec.get("bundles")
    if not isinstance(bundles, list) or not bundles:
        errors.append("pack_spec.bundles is empty")
        return PackVerifyResult(ok=False, errors=errors, warnings=warnings)

    bundle_store = CuratedBundleStore(conn)

    for idx, b in enumerate([x for x in bundles if isinstance(x, dict)]):
        bundle_id = b.get("bundle_id")
        bundle_digest_expected = b.get("bundle_digest")
        if not bundle_id or not bundle_digest_expected:
            errors.append(f"bundle entry missing bundle_id/bundle_digest (idx={idx})")
            continue

        cub = bundle_store.get(str(bundle_id))
        if cub is None:
            errors.append(f"CUB not found: {bundle_id}")
            continue

        if str(cub.bundle_digest) != str(bundle_digest_expected):
            errors.append(
                f"CUB digest mismatch: expected={bundle_digest_expected}, actual={cub.bundle_digest} (bundle_id={bundle_id})"
            )

    return PackVerifyResult(ok=(len(errors) == 0), errors=errors, warnings=warnings)
