"""DataOverridePatch store + applier (BF-06).

DataOverridePatch(DOP-*)는 "추출 파이프라인을 고치기 어려운 경우"를 위한 최후 수단입니다.

핵심 계약:
- Patch는 append-only(새 CUB 생성)로 반영되어야 하며, digest/lineage에 반영됩니다.
- reporting_strict 모드에서는 DOP 적용 시 승인(approved_by/approved_at) 요건을 강제합니다.
- patch_digest는 patch_id/created_at/승인 메타에 의존하지 않고 결정적으로 계산됩니다.

주의:
- 본 모듈은 "값의 의미"(row_key/period_range 등)를 해석하지 않습니다.
  target_path는 JSON Pointer(RFC 6901)로 해석되며, payload_json에 직접 적용합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional, Tuple

from cmis_core.brownfield.curated_store import CuratedBundleStore, CuratedDatumStore
from cmis_core.brownfield.uow import UnitOfWork
from cmis_core.digest import canonical_digest, canonical_json


_ALLOWED_OPS = {"set", "add", "multiply", "delete"}


@dataclass(frozen=True)
class DataOverridePatchRecord:
    """DataOverridePatch 레코드."""

    patch_id: str
    applies_to_bundle_id: str
    applies_to_datum_id: Optional[str]
    operation: str
    target_path: str
    value: Any
    reason_ref: str
    approved_by: Optional[str]
    approved_at: Optional[str]
    patch_digest: str
    created_at: str


class DataOverridePatchStore:
    """brownfield.db의 dop_patches 테이블 스토어."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def compute_patch_digest(
        *,
        applies_to_bundle_id: str,
        applies_to_datum_id: Optional[str],
        operation: str,
        target_path: str,
        value: Any,
        reason_ref: str,
    ) -> str:
        """patch_digest를 결정적으로 계산합니다.

        patch_digest는 데이터 변경 의미(적용 대상 + 연산 + 경로 + 값 + reason_ref)를 대표합니다.
        승인 메타(approved_*)/created_at/patch_id는 digest 입력에 포함하지 않습니다.
        """

        op = str(operation).strip().lower()
        if op not in _ALLOWED_OPS:
            raise ValueError(f"Unsupported DOP operation: {operation}")

        path = str(target_path)
        if not path.startswith("/"):
            raise ValueError("target_path must be a JSON Pointer starting with '/'")

        rr = str(reason_ref).strip()
        if not rr:
            raise ValueError("reason_ref is required")

        payload = {
            "applies_to_bundle_id": str(applies_to_bundle_id),
            "applies_to_datum_id": str(applies_to_datum_id) if applies_to_datum_id is not None else None,
            "operation": op,
            "target_path": path,
            "value": value,
            "reason_ref": rr,
        }
        return canonical_digest(payload)

    def create(
        self,
        *,
        applies_to_bundle_id: str,
        applies_to_datum_id: Optional[str],
        operation: str,
        target_path: str,
        value: Any,
        reason_ref: str,
        approved_by: Optional[str] = None,
        approved_at: Optional[str] = None,
        patch_id: Optional[str] = None,
    ) -> DataOverridePatchRecord:
        """DOP를 생성합니다.

        동일 patch_digest가 이미 존재하면 기존 레코드를 반환합니다.
        """

        digest = self.compute_patch_digest(
            applies_to_bundle_id=applies_to_bundle_id,
            applies_to_datum_id=applies_to_datum_id,
            operation=operation,
            target_path=target_path,
            value=value,
            reason_ref=reason_ref,
        )

        existing = self.get_by_digest(digest)
        if existing is not None:
            return existing

        pid = str(patch_id) if patch_id is not None else f"DOP-{uuid.uuid4().hex[:10]}"
        created_at = self._now()

        op = str(operation).strip().lower()
        tp = str(target_path)
        rr = str(reason_ref).strip()

        value_json = canonical_json(value)

        self.conn.execute(
            """
            INSERT INTO dop_patches(
                patch_id, applies_to_bundle_id, applies_to_datum_id,
                operation, target_path, value_json,
                reason_ref, approved_by, approved_at,
                patch_digest, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pid,
                str(applies_to_bundle_id),
                str(applies_to_datum_id) if applies_to_datum_id is not None else None,
                op,
                tp,
                value_json,
                rr,
                str(approved_by) if approved_by is not None else None,
                str(approved_at) if approved_at is not None else None,
                str(digest),
                created_at,
            ),
        )

        return DataOverridePatchRecord(
            patch_id=str(pid),
            applies_to_bundle_id=str(applies_to_bundle_id),
            applies_to_datum_id=str(applies_to_datum_id) if applies_to_datum_id is not None else None,
            operation=op,
            target_path=tp,
            value=value,
            reason_ref=rr,
            approved_by=str(approved_by) if approved_by is not None else None,
            approved_at=str(approved_at) if approved_at is not None else None,
            patch_digest=str(digest),
            created_at=str(created_at),
        )

    def approve(
        self,
        *,
        patch_id: str,
        approved_by: str,
        approved_at: Optional[str] = None,
    ) -> None:
        """DOP를 승인 처리합니다."""

        by = str(approved_by).strip()
        if not by:
            raise ValueError("approved_by is required")

        at = str(approved_at).strip() if approved_at is not None else self._now()

        self.conn.execute(
            "UPDATE dop_patches SET approved_by = ?, approved_at = ? WHERE patch_id = ?",
            (by, at, str(patch_id)),
        )

    def get(self, patch_id: str) -> Optional[DataOverridePatchRecord]:
        cur = self.conn.execute(
            """
            SELECT
                applies_to_bundle_id, applies_to_datum_id,
                operation, target_path, value_json,
                reason_ref, approved_by, approved_at,
                patch_digest, created_at
            FROM dop_patches
            WHERE patch_id = ?
            """,
            (str(patch_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        (
            applies_to_bundle_id,
            applies_to_datum_id,
            operation,
            target_path,
            value_json,
            reason_ref,
            approved_by,
            approved_at,
            patch_digest,
            created_at,
        ) = row

        try:
            value = json.loads(value_json)
        except Exception:
            value = None

        return DataOverridePatchRecord(
            patch_id=str(patch_id),
            applies_to_bundle_id=str(applies_to_bundle_id),
            applies_to_datum_id=str(applies_to_datum_id) if applies_to_datum_id is not None else None,
            operation=str(operation),
            target_path=str(target_path),
            value=value,
            reason_ref=str(reason_ref),
            approved_by=str(approved_by) if approved_by is not None else None,
            approved_at=str(approved_at) if approved_at is not None else None,
            patch_digest=str(patch_digest),
            created_at=str(created_at),
        )

    def get_by_digest(self, patch_digest: str) -> Optional[DataOverridePatchRecord]:
        cur = self.conn.execute(
            "SELECT patch_id FROM dop_patches WHERE patch_digest = ? LIMIT 1",
            (str(patch_digest),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self.get(str(row[0]))

    def list_for_bundle(self, applies_to_bundle_id: str) -> List[DataOverridePatchRecord]:
        cur = self.conn.execute(
            """
            SELECT patch_id
            FROM dop_patches
            WHERE applies_to_bundle_id = ?
            ORDER BY created_at ASC
            """,
            (str(applies_to_bundle_id),),
        )
        rows = cur.fetchall() or []
        out: List[DataOverridePatchRecord] = []
        for (pid,) in rows:
            rec = self.get(str(pid))
            if rec is not None:
                out.append(rec)
        return out


def compute_patch_chain_digest(patch_chain_digests: List[str]) -> str:
    """patch_chain_digests의 digest(=patches_digest)를 계산합니다."""

    chain = [str(d) for d in (patch_chain_digests or [])]
    return canonical_digest({"patch_chain_digests": chain})


def _json_pointer_tokens(pointer: str) -> List[str]:
    p = str(pointer)
    if p == "":
        return []
    if not p.startswith("/"):
        raise ValueError("JSON pointer must start with '/'")

    # RFC 6901
    tokens = p.lstrip("/").split("/")
    out: List[str] = []
    for t in tokens:
        out.append(t.replace("~1", "/").replace("~0", "~"))
    return out


def _get_parent_and_key(obj: Any, tokens: List[str]) -> Tuple[Any, Optional[Any]]:
    if not tokens:
        return obj, None

    cur = obj
    for t in tokens[:-1]:
        if isinstance(cur, dict):
            if t not in cur:
                raise KeyError(f"Missing key in path: {t}")
            cur = cur[t]
            continue
        if isinstance(cur, list):
            try:
                idx = int(t)
            except Exception as e:
                raise KeyError(f"List index must be int token (got: {t})") from e
            if idx < 0 or idx >= len(cur):
                raise IndexError(f"List index out of range: {idx}")
            cur = cur[idx]
            continue
        raise TypeError(f"Unsupported container type in path traversal: {type(cur).__name__}")

    last = tokens[-1]
    if isinstance(cur, list):
        try:
            last = int(last)
        except Exception as e:
            raise KeyError(f"List index must be int token (got: {last})") from e
    return cur, last


def _apply_patch_to_payload(*, payload: Any, operation: str, target_path: str, value: Any) -> Any:
    op = str(operation).strip().lower()
    if op not in _ALLOWED_OPS:
        raise ValueError(f"Unsupported DOP operation: {operation}")

    tokens = _json_pointer_tokens(str(target_path))

    # root replace
    if not tokens:
        if op == "set":
            return value
        raise ValueError("Only 'set' is allowed for root path")

    parent, key = _get_parent_and_key(payload, tokens)

    if isinstance(parent, dict):
        k = str(key)
        if op == "set":
            parent[k] = value
            return payload
        if op == "delete":
            if k not in parent:
                raise KeyError(f"Missing key for delete: {k}")
            del parent[k]
            return payload
        if k not in parent:
            raise KeyError(f"Missing key for numeric op: {k}")
        cur_val = parent[k]
    elif isinstance(parent, list):
        idx = int(key)  # type: ignore[arg-type]
        if idx < 0 or idx >= len(parent):
            raise IndexError(f"List index out of range: {idx}")
        if op == "set":
            parent[idx] = value
            return payload
        if op == "delete":
            parent.pop(idx)
            return payload
        cur_val = parent[idx]
    else:
        raise TypeError(f"Unsupported parent container type: {type(parent).__name__}")

    if not isinstance(cur_val, (int, float)):
        raise TypeError(f"Target value is not numeric for op={op}: {type(cur_val).__name__}")
    if not isinstance(value, (int, float)):
        raise TypeError(f"Patch value is not numeric for op={op}: {type(value).__name__}")

    if op == "add":
        new_val = cur_val + value
    elif op == "multiply":
        new_val = cur_val * value
    else:
        raise ValueError(f"Unsupported numeric op: {op}")

    if isinstance(parent, dict):
        parent[str(key)] = new_val
    else:
        parent[int(key)] = new_val  # type: ignore[index]
    return payload


def apply_data_override_patches_to_bundle(
    *,
    conn: sqlite3.Connection,
    base_bundle_id: str,
    patch_ids: List[str],
    policy_mode: str = "reporting_strict",
) -> Tuple[str, str]:
    """DOP를 적용하여 새 CUB를 생성합니다.

    Args:
        conn: brownfield.db connection
        base_bundle_id: 대상 CUB-*
        patch_ids: 적용할 DOP-* 목록(순서 보존)
        policy_mode: reporting_strict|decision_balanced|exploration_friendly

    Returns:
        (new_bundle_id, new_bundle_digest)
    """

    if not patch_ids:
        raise ValueError("patch_ids is empty")

    store = DataOverridePatchStore(conn)
    bundle_store = CuratedBundleStore(conn)
    datum_store = CuratedDatumStore(conn)
    uow = UnitOfWork(conn)

    base = bundle_store.get(str(base_bundle_id))
    if base is None:
        raise KeyError(f"Unknown bundle_id: {base_bundle_id}")

    # resolve patches (in given order)
    patches: List[DataOverridePatchRecord] = []
    for pid in patch_ids:
        rec = store.get(str(pid))
        if rec is None:
            raise KeyError(f"Unknown patch_id: {pid}")
        if str(rec.applies_to_bundle_id) != str(base_bundle_id):
            raise ValueError(
                f"Patch applies_to_bundle_id mismatch: patch={rec.patch_id}, expected={base_bundle_id}, got={rec.applies_to_bundle_id}"
            )
        patches.append(rec)

    # strict gate: approvals required
    mode = str(policy_mode)
    if mode == "reporting_strict":
        missing = [p.patch_id for p in patches if not p.approved_by or not p.approved_at]
        if missing:
            raise ValueError(f"DOP approval required in reporting_strict (missing: {missing})")

    # duplicate check
    already = set([str(x) for x in (base.patch_chain_digests or [])])
    for p in patches:
        if str(p.patch_digest) in already:
            raise ValueError(f"Patch already applied in base bundle: {p.patch_id}")

    # build datum_id -> semantic_key mapping (bundle items do not store datum_id by design)
    item_schema_versions: Dict[str, int] = {}
    item_digests: Dict[str, str] = {}
    for it in base.curated_items or []:
        if not isinstance(it, dict):
            continue
        sk = str(it.get("semantic_key"))
        dg = str(it.get("cur_payload_digest"))
        sv = int(it.get("cur_schema_version") or 1)
        if sk:
            item_digests[sk] = dg
            item_schema_versions[sk] = sv

    if not item_digests:
        raise ValueError("Base bundle has no curated_items")

    datum_id_by_semantic_key: Dict[str, str] = {}
    semantic_key_by_datum_id: Dict[str, str] = {}
    for sk, dg in item_digests.items():
        did = datum_store.find_datum_id(cur_payload_digest=dg, semantic_key=sk, schema_version=item_schema_versions.get(sk, 1))
        if did is None:
            raise RuntimeError(f"Failed to resolve datum_id for semantic_key={sk}")
        datum_id_by_semantic_key[sk] = did
        semantic_key_by_datum_id[did] = sk

    # plan patches per semantic_key
    per_key_patches: Dict[str, List[DataOverridePatchRecord]] = {}
    for p in patches:
        if p.applies_to_datum_id is None:
            # minimal MVP: allow implicit target when bundle has exactly 1 item
            if len(datum_id_by_semantic_key) == 1:
                sk = next(iter(datum_id_by_semantic_key.keys()))
            else:
                raise ValueError(f"applies_to_datum_id is required when bundle has multiple items (patch={p.patch_id})")
        else:
            sk = semantic_key_by_datum_id.get(str(p.applies_to_datum_id))
            if sk is None:
                raise ValueError(
                    f"Patch datum_id not in base bundle: patch={p.patch_id}, datum_id={p.applies_to_datum_id}"
                )

        per_key_patches.setdefault(sk, []).append(p)

    def _apply_no_tx() -> Tuple[str, str]:
        new_items: List[Dict[str, Any]] = [dict(it) for it in (base.curated_items or []) if isinstance(it, dict)]
        new_item_by_key: Dict[str, Dict[str, Any]] = {
            str(it.get("semantic_key")): it for it in new_items if it.get("semantic_key")
        }

        for sk, p_list in per_key_patches.items():
            did = datum_id_by_semantic_key[sk]
            datum = datum_store.get(did)
            if datum is None:
                raise RuntimeError(f"CUR not found: {did}")
            if datum.payload_json is None:
                raise ValueError(f"DOP apply supports payload_json only in MVP (datum_id={did})")

            # apply patches sequentially on a copy
            payload_obj = json.loads(json.dumps(datum.payload_json))
            for p in p_list:
                payload_obj = _apply_patch_to_payload(
                    payload=payload_obj,
                    operation=p.operation,
                    target_path=p.target_path,
                    value=p.value,
                )

            # lineage append
            lineage = dict(datum.lineage or {})
            patches_meta = lineage.get("patches")
            if not isinstance(patches_meta, list):
                patches_meta = []
            patches_meta = list(patches_meta)
            for p in p_list:
                patches_meta.append(
                    {
                        "patch_id": str(p.patch_id),
                        "patch_digest": str(p.patch_digest),
                        "reason_ref": str(p.reason_ref),
                    }
                )
            lineage["patches"] = patches_meta
            lineage["patched_from"] = {"datum_id": str(did), "cur_payload_digest": str(datum.cur_payload_digest)}

            new_did, new_digest = datum_store.put(
                datum_type=str(datum.datum_type),
                semantic_key=str(datum.semantic_key),
                payload=payload_obj,
                payload_ref_artifact_id=datum.payload_ref_artifact_id,
                as_of=str(datum.as_of) if datum.as_of is not None else None,
                period_range=str(datum.period_range) if datum.period_range is not None else None,
                schema_version=int(datum.schema_version) if datum.schema_version is not None else 1,
                lineage=lineage,
            )

            item = new_item_by_key.get(sk)
            if item is None:
                raise RuntimeError(f"Bundle item not found for semantic_key={sk}")
            item["cur_payload_digest"] = str(new_digest)
            item["cur_schema_version"] = int(item_schema_versions.get(sk, 1))
            # optional link meta: do not affect CUB digest input
            item["cur_datum_id"] = str(new_did)

        patch_chain = list(base.patch_chain_digests or []) + [str(p.patch_digest) for p in patches]
        cub_digest_input = {
            "schema_version": int(base.schema_version) if base.schema_version is not None else 1,
            "normalization_defaults_digest": base.normalization_defaults_digest,
            "ingest_policy_digest": base.ingest_policy_digest,
            "mapping_ref": base.mapping_ref,
            "extractor_version": base.extractor_version,
            "patch_chain_digests": patch_chain,
            "curated_items": new_items,
        }

        new_bundle_id, new_bundle_digest = bundle_store.put(
            cub_digest_input=cub_digest_input,
            import_run_id=base.import_run_id,
            as_of=base.as_of,
            normalization_defaults_digest=base.normalization_defaults_digest,
            ingest_policy_digest=base.ingest_policy_digest,
            mapping_ref=base.mapping_ref,
            extractor_version=base.extractor_version,
            patch_chain_digests=patch_chain,
            curated_items=new_items,
            quality_summary=base.quality_summary,
            schema_version=int(base.schema_version) if base.schema_version is not None else 1,
        )
        return str(new_bundle_id), str(new_bundle_digest)

    # apply in one transaction when possible: create new CUR(s) + new CUB
    if getattr(conn, "in_transaction", False):
        new_bundle_id, new_bundle_digest = _apply_no_tx()
    else:
        with uow.transaction():
            new_bundle_id, new_bundle_digest = _apply_no_tx()

    return str(new_bundle_id), str(new_bundle_digest)
