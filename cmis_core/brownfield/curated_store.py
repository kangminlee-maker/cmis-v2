"""Curated stores (BF-05).

CUR( CuratedDatum ) / CUB( CuratedBundle )는 Brownfield 내부 데이터의 정본(SSoT)입니다.

원칙:
- CUR: 원자 데이터(테이블/시계열/statement/kv/model)
- CUB: 커밋 스냅샷 단위(여러 CUR를 묶음)
- digest는 ID가 아니라 content digest 중심으로 계산
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional, Tuple

from cmis_core.digest import canonical_digest, canonical_json


@dataclass(frozen=True)
class CuratedDatumRecord:
    datum_id: str
    datum_type: str
    semantic_key: str
    as_of: Optional[str]
    period_range: Optional[str]
    schema_version: Optional[int]
    payload_json: Optional[Dict[str, Any]]
    payload_ref_artifact_id: Optional[str]
    cur_payload_digest: str
    lineage: Dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class CuratedBundleRecord:
    bundle_id: str
    bundle_digest: str
    import_run_id: Optional[str]
    as_of: Optional[str]
    schema_version: Optional[int]
    normalization_defaults_digest: Optional[str]
    ingest_policy_digest: Optional[str]
    mapping_ref: Optional[Dict[str, Any]]
    extractor_version: Optional[str]
    patch_chain_digests: List[str]
    curated_items: List[Dict[str, Any]]
    quality_summary: Optional[Dict[str, Any]]
    created_at: str


class CuratedDatumStore:
    """brownfield.db curated_data 스토어."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def put(
        self,
        *,
        datum_type: str,
        semantic_key: str,
        payload: Optional[Dict[str, Any]] = None,
        payload_ref_artifact_id: Optional[str] = None,
        as_of: Optional[str] = None,
        period_range: Optional[str] = None,
        schema_version: Optional[int] = 1,
        lineage: Optional[Dict[str, Any]] = None,
        cur_payload_digest: Optional[str] = None,
    ) -> Tuple[str, str]:
        """CUR을 저장합니다.

        Returns:
            (datum_id, cur_payload_digest)
        """

        if payload is None and payload_ref_artifact_id is None:
            raise ValueError("Either payload or payload_ref_artifact_id must be provided")

        payload_obj = payload or {}
        digest = str(cur_payload_digest) if cur_payload_digest is not None else canonical_digest(payload_obj)
        sv = int(schema_version) if schema_version is not None else 1

        existing = self._find_existing(digest=digest, semantic_key=semantic_key, schema_version=sv)
        if existing is not None:
            return existing, digest

        did = f"CUR-{uuid.uuid4().hex[:10]}"
        created_at = self._now()

        payload_json_str: Optional[str]
        if payload is not None:
            payload_json_str = canonical_json(payload_obj)
        else:
            payload_json_str = None

        lineage_obj = dict(lineage or {})
        lineage_json_str = canonical_json(lineage_obj)

        self.conn.execute(
            """
            INSERT INTO curated_data(
                datum_id, datum_type, semantic_key, as_of, period_range, schema_version,
                payload_json, payload_ref_artifact_id, cur_payload_digest, lineage_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                did,
                str(datum_type),
                str(semantic_key),
                str(as_of) if as_of is not None else None,
                str(period_range) if period_range is not None else None,
                sv,
                payload_json_str,
                str(payload_ref_artifact_id) if payload_ref_artifact_id is not None else None,
                digest,
                lineage_json_str,
                created_at,
            ),
        )
        return did, digest

    def get(self, datum_id: str) -> Optional[CuratedDatumRecord]:
        cur = self.conn.execute(
            """
            SELECT
                datum_type, semantic_key, as_of, period_range, schema_version,
                payload_json, payload_ref_artifact_id, cur_payload_digest, lineage_json, created_at
            FROM curated_data
            WHERE datum_id = ?
            """,
            (str(datum_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        (
            datum_type,
            semantic_key,
            as_of,
            period_range,
            schema_version,
            payload_json_str,
            payload_ref_artifact_id,
            cur_payload_digest,
            lineage_json_str,
            created_at,
        ) = row

        payload_obj: Optional[Dict[str, Any]]
        if payload_json_str:
            try:
                pj = json.loads(payload_json_str)
            except Exception:
                pj = {}
            payload_obj = pj if isinstance(pj, dict) else {}
        else:
            payload_obj = None

        try:
            lin = json.loads(lineage_json_str or "{}")
        except Exception:
            lin = {}
        lineage_obj = lin if isinstance(lin, dict) else {}

        return CuratedDatumRecord(
            datum_id=str(datum_id),
            datum_type=str(datum_type),
            semantic_key=str(semantic_key),
            as_of=str(as_of) if as_of is not None else None,
            period_range=str(period_range) if period_range is not None else None,
            schema_version=int(schema_version) if schema_version is not None else None,
            payload_json=payload_obj,
            payload_ref_artifact_id=str(payload_ref_artifact_id) if payload_ref_artifact_id is not None else None,
            cur_payload_digest=str(cur_payload_digest),
            lineage=lineage_obj,
            created_at=str(created_at),
        )

    def find_datum_id(self, *, cur_payload_digest: str, semantic_key: str, schema_version: int = 1) -> Optional[str]:
        """(cur_payload_digest, semantic_key, schema_version)로 datum_id를 조회합니다.

        주의:
        - curated_items는 digest 중심이므로, bundle→datum 링크를 복원할 때 사용합니다.
        """

        return self._find_existing(digest=str(cur_payload_digest), semantic_key=str(semantic_key), schema_version=int(schema_version))

    def _find_existing(self, *, digest: str, semantic_key: str, schema_version: int) -> Optional[str]:
        cur = self.conn.execute(
            """
            SELECT datum_id
            FROM curated_data
            WHERE cur_payload_digest = ? AND semantic_key = ? AND schema_version = ?
            LIMIT 1
            """,
            (str(digest), str(semantic_key), int(schema_version)),
        )
        row = cur.fetchone()
        if not row:
            return None
        return str(row[0])


class CuratedBundleStore:
    """brownfield.db curated_bundles 스토어."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def compute_bundle_digest(cub_digest_input: Dict[str, Any]) -> str:
        """CUB.bundle_digest를 계산합니다.

        규칙:
        - curated_items는 semantic_key 기준으로 정렬하여 digest 입력을 고정합니다.
        - patch_chain_digests는 적용 순서를 보존합니다(정렬 금지).
        """

        inp = dict(cub_digest_input or {})
        items = inp.get("curated_items")
        if isinstance(items, list):
            sortable = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                # digest input은 ID가 아니라 content 중심이어야 하므로, 허용 필드만 남깁니다.
                sk = str(it.get("semantic_key"))
                cleaned: Dict[str, Any] = {
                    "semantic_key": sk,
                    "cur_payload_digest": str(it.get("cur_payload_digest")),
                }
                if "cur_schema_version" in it and it.get("cur_schema_version") is not None:
                    cleaned["cur_schema_version"] = int(it.get("cur_schema_version"))
                sortable.append((sk, cleaned))
            sortable.sort(key=lambda x: x[0])
            inp["curated_items"] = [v for _, v in sortable]

        return canonical_digest(inp)

    def put(
        self,
        *,
        cub_digest_input: Dict[str, Any],
        import_run_id: Optional[str] = None,
        as_of: Optional[str] = None,
        normalization_defaults_digest: Optional[str] = None,
        ingest_policy_digest: Optional[str] = None,
        mapping_ref: Optional[Dict[str, Any]] = None,
        extractor_version: Optional[str] = None,
        patch_chain_digests: Optional[List[str]] = None,
        curated_items: Optional[List[Dict[str, Any]]] = None,
        quality_summary: Optional[Dict[str, Any]] = None,
        schema_version: Optional[int] = 1,
    ) -> Tuple[str, str]:
        """CUB을 저장합니다(sha256 digest로 dedupe).

        Returns:
            (bundle_id, bundle_digest)
        """

        digest_input = dict(cub_digest_input or {})
        bundle_digest = self.compute_bundle_digest(digest_input)

        existing = self._find_existing(bundle_digest=bundle_digest)
        if existing is not None:
            return existing, bundle_digest

        bid = f"CUB-{uuid.uuid4().hex[:10]}"
        created_at = self._now()

        patch_chain = [str(x) for x in (patch_chain_digests or [])]
        items = curated_items or digest_input.get("curated_items") or []
        if not isinstance(items, list):
            items = []

        # 저장도 정렬된 형태로 고정(verify/diff 대비) + digest 입력과 동일한 허용 필드만 저장
        sortable_items = []
        for it in items:
            if not isinstance(it, dict):
                continue
            sk = str(it.get("semantic_key"))
            cleaned: Dict[str, Any] = {
                "semantic_key": sk,
                "cur_payload_digest": str(it.get("cur_payload_digest")),
            }
            if "cur_schema_version" in it and it.get("cur_schema_version") is not None:
                cleaned["cur_schema_version"] = int(it.get("cur_schema_version"))
            sortable_items.append((sk, cleaned))
        sortable_items.sort(key=lambda x: x[0])
        stored_items = [v for _, v in sortable_items]

        self.conn.execute(
            """
            INSERT INTO curated_bundles(
                bundle_id, bundle_digest, import_run_id, as_of, schema_version,
                normalization_defaults_digest, ingest_policy_digest, mapping_ref_json, extractor_version,
                patch_chain_digests_json, curated_items_json, quality_summary_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bid,
                bundle_digest,
                str(import_run_id) if import_run_id is not None else None,
                str(as_of) if as_of is not None else None,
                int(schema_version) if schema_version is not None else None,
                str(normalization_defaults_digest) if normalization_defaults_digest is not None else None,
                str(ingest_policy_digest) if ingest_policy_digest is not None else None,
                json.dumps(mapping_ref, ensure_ascii=False) if mapping_ref is not None else None,
                str(extractor_version) if extractor_version is not None else None,
                json.dumps(patch_chain, ensure_ascii=False),
                json.dumps(stored_items, ensure_ascii=False),
                json.dumps(quality_summary, ensure_ascii=False) if quality_summary is not None else None,
                created_at,
            ),
        )
        return bid, bundle_digest

    def get(self, bundle_id: str) -> Optional[CuratedBundleRecord]:
        cur = self.conn.execute(
            """
            SELECT
                bundle_digest, import_run_id, as_of, schema_version,
                normalization_defaults_digest, ingest_policy_digest, mapping_ref_json, extractor_version,
                patch_chain_digests_json, curated_items_json, quality_summary_json, created_at
            FROM curated_bundles
            WHERE bundle_id = ?
            """,
            (str(bundle_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        (
            bundle_digest,
            import_run_id,
            as_of,
            schema_version,
            normalization_defaults_digest,
            ingest_policy_digest,
            mapping_ref_json,
            extractor_version,
            patch_chain_digests_json,
            curated_items_json,
            quality_summary_json,
            created_at,
        ) = row

        mapping_ref: Optional[Dict[str, Any]]
        if mapping_ref_json:
            try:
                mr = json.loads(mapping_ref_json)
            except Exception:
                mr = None
            mapping_ref = mr if isinstance(mr, dict) else None
        else:
            mapping_ref = None

        try:
            chain = json.loads(patch_chain_digests_json or "[]")
        except Exception:
            chain = []
        if not isinstance(chain, list):
            chain = []

        try:
            items = json.loads(curated_items_json or "[]")
        except Exception:
            items = []
        if not isinstance(items, list):
            items = []

        quality: Optional[Dict[str, Any]]
        if quality_summary_json:
            try:
                q = json.loads(quality_summary_json)
            except Exception:
                q = None
            quality = q if isinstance(q, dict) else None
        else:
            quality = None

        return CuratedBundleRecord(
            bundle_id=str(bundle_id),
            bundle_digest=str(bundle_digest),
            import_run_id=str(import_run_id) if import_run_id is not None else None,
            as_of=str(as_of) if as_of is not None else None,
            schema_version=int(schema_version) if schema_version is not None else None,
            normalization_defaults_digest=str(normalization_defaults_digest) if normalization_defaults_digest is not None else None,
            ingest_policy_digest=str(ingest_policy_digest) if ingest_policy_digest is not None else None,
            mapping_ref=mapping_ref,
            extractor_version=str(extractor_version) if extractor_version is not None else None,
            patch_chain_digests=[str(x) for x in chain],
            curated_items=[it for it in items if isinstance(it, dict)],
            quality_summary=quality,
            created_at=str(created_at),
        )

    def _find_existing(self, *, bundle_digest: str) -> Optional[str]:
        cur = self.conn.execute(
            "SELECT bundle_id FROM curated_bundles WHERE bundle_digest = ? LIMIT 1",
            (str(bundle_digest),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return str(row[0])
