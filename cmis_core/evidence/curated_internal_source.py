"""CuratedEvidenceSource (BF-14).

Brownfield curated store(CUR/CUB/PRJ/BPK)를 EvidenceEngine의 curated_internal tier로 연결합니다.

의도:
- 외부 API/웹검색 전에 "내부 curated"에서 값을 찾을 수 있으면 우선 사용합니다.
- 단, 어떤 값을 어디에서 읽을지(semantic_key/field_path)는 계약으로 명시되어야 합니다.

현재 구현(저복잡도, 안전한 최소):
- request.context에 아래 키 중 하나가 있을 때만 동작
  - focal_actor_context_id: PRJ-...(-vN 권장)
  - brownfield_pack_id: BPK-...
- semantic_key 결정 규칙
  1) context.curated_semantic_key가 있으면 사용
  2) 없으면 metric_id(+ year/as_of)를 이용해 기본 규칙으로 생성
     - kv:metric:<metric_id>:<year>
     - kv:metric:<metric_id>:as_of=<YYYY-MM-DD>
- 값 추출 규칙
  - context.curated_json_pointer("/a/b") 또는 context.curated_field("revenue")가 있으면 그 경로에서 numeric을 추출
  - 없으면 payload_json["value"](numeric) 우선

주의:
- 본 소스는 "테이블 파싱/정규화"를 수행하지 않습니다.
  (그 책임은 Brownfield ingest/mapping 단계에 있으며, 여기서는 ref 기반 조회만 합니다.)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cmis_core.brownfield.curated_store import CuratedBundleStore, CuratedDatumStore
from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.pack_store import BrownfieldPackStore, select_bundle_from_pack_spec
from cmis_core.brownfield.semantic_key import make as make_semantic_key
from cmis_core.evidence_engine import BaseDataSource, DataNotFoundError, SourceNotAvailableError
from cmis_core.stores.focal_actor_context_store import FocalActorContextStore
from cmis_core.types import EvidenceRecord, EvidenceRequest, EvidenceValueKind, FocalActorContext, SourceTier
from cmis_core.digest import canonical_digest


def _split_versioned_id(raw: str) -> Tuple[str, Optional[int]]:
    pid = str(raw or "").strip()
    if not pid:
        return "", None
    if "-v" not in pid:
        return pid, None
    base, _, tail = pid.rpartition("-v")
    if not base:
        return pid, None
    try:
        ver = int(tail)
    except Exception:
        return pid, None
    return base, ver


def _json_pointer_tokens(pointer: str) -> list[str]:
    p = str(pointer)
    if p == "":
        return []
    if not p.startswith("/"):
        raise ValueError("JSON pointer must start with '/'")
    tokens = p.lstrip("/").split("/")
    out: list[str] = []
    for t in tokens:
        out.append(t.replace("~1", "/").replace("~0", "~"))
    return out


def _extract_json_pointer(payload: Any, pointer: str) -> Any:
    tokens = _json_pointer_tokens(pointer)
    cur = payload
    for t in tokens:
        if isinstance(cur, dict):
            cur = cur.get(t)
            continue
        if isinstance(cur, list):
            try:
                idx = int(t)
            except Exception:
                return None
            if idx < 0 or idx >= len(cur):
                return None
            cur = cur[idx]
            continue
        return None
    return cur


class CuratedEvidenceSource(BaseDataSource):
    """Brownfield curated store 기반 curated_internal Evidence source."""

    def __init__(self, *, project_root: Path) -> None:
        super().__init__(
            source_id="CURATED",
            source_tier=SourceTier.CURATED_INTERNAL,
            capabilities={"provides": ["*"], "regions": ["*"], "data_types": ["numeric", "table"]},
        )
        self.project_root = Path(project_root)

    def can_handle(self, request: EvidenceRequest) -> bool:
        if str(request.request_type) != "metric":
            return False
        if not request.metric_id:
            return False
        ctx = request.context or {}
        return ("focal_actor_context_id" in ctx) or ("brownfield_pack_id" in ctx)

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        ctx = request.context or {}

        prj_id = str(ctx.get("focal_actor_context_id") or "").strip()
        pack_id = str(ctx.get("brownfield_pack_id") or "").strip()

        if not prj_id and not pack_id:
            raise DataNotFoundError("curated_internal requires focal_actor_context_id or brownfield_pack_id")

        # Resolve bundle from PRJ or BPK
        bundle_id: Optional[str] = None
        bundle_digest_expected: Optional[str] = None

        if prj_id:
            prj = self._load_prj(prj_id)
            primary = prj.lineage.get("primary_source_bundle") if isinstance(prj.lineage, dict) else None
            if not isinstance(primary, dict):
                raise DataNotFoundError("PRJ missing lineage.primary_source_bundle")
            bundle_id = str(primary.get("bundle_id") or "").strip()
            bundle_digest_expected = str(primary.get("bundle_digest") or "").strip()
            if not bundle_id or not bundle_digest_expected:
                raise DataNotFoundError("PRJ primary_source_bundle must include bundle_id and bundle_digest")

        if (bundle_id is None) and pack_id:
            bundle_id, bundle_digest_expected = self._select_bundle_from_pack(pack_id=pack_id, ctx=ctx)

        if not bundle_id:
            raise DataNotFoundError("Failed to resolve curated bundle")

        # Open brownfield DB and locate datum
        conn = open_brownfield_db(project_root=self.project_root)
        try:
            migrate_brownfield_db(conn)
            bundle_store = CuratedBundleStore(conn)
            datum_store = CuratedDatumStore(conn)

            bundle = bundle_store.get(bundle_id)
            if bundle is None:
                raise DataNotFoundError(f"CUB not found: {bundle_id}")

            if bundle_digest_expected and str(bundle.bundle_digest) != str(bundle_digest_expected):
                raise DataNotFoundError(
                    f"CUB digest mismatch: expected={bundle_digest_expected}, actual={bundle.bundle_digest} (bundle_id={bundle_id})"
                )

            semantic_key = self._resolve_semantic_key(request)

            # Find matching curated item
            item = None
            for it in bundle.curated_items or []:
                if not isinstance(it, dict):
                    continue
                if str(it.get("semantic_key")) == semantic_key:
                    item = it
                    break

            if item is None:
                raise DataNotFoundError(f"semantic_key not found in CUB: {semantic_key}")

            cur_digest = str(item.get("cur_payload_digest") or "").strip()
            schema_version = int(item.get("cur_schema_version") or 1)
            if not cur_digest:
                raise DataNotFoundError("cur_payload_digest missing in curated item")

            datum_id = datum_store.find_datum_id(cur_payload_digest=cur_digest, semantic_key=semantic_key, schema_version=schema_version)
            if datum_id is None:
                raise DataNotFoundError(f"CUR not found for semantic_key={semantic_key}")

            datum = datum_store.get(datum_id)
            if datum is None:
                raise DataNotFoundError(f"CUR not found: {datum_id}")

            payload = datum.payload_json
            if not isinstance(payload, dict):
                raise DataNotFoundError("CUR payload_json is not a dict")

            value = self._extract_numeric_value(payload, ctx, metric_id=str(request.metric_id))

            evidence_digest = canonical_digest(
                {"bundle_digest": str(bundle.bundle_digest), "semantic_key": semantic_key, "metric_id": str(request.metric_id)}
            )
            short = str(evidence_digest).split(":", 1)[-1][:10]

            return EvidenceRecord(
                evidence_id=f"EVD-CURATED-{short}",
                source_tier=self.source_tier.value,
                source_id=self.source_id,
                value=value,
                value_kind=EvidenceValueKind.NUMERIC,
                schema_ref="brownfield_curated_kv_v1",
                confidence=0.95,
                metadata={
                    "focal_actor_context_id": prj_id or None,
                    "brownfield_pack_id": pack_id or None,
                    "bundle_id": str(bundle_id),
                    "bundle_digest": str(bundle.bundle_digest),
                    "datum_id": str(datum_id),
                    "cur_payload_digest": str(datum.cur_payload_digest),
                    "semantic_key": semantic_key,
                },
                context=dict(ctx),
                as_of=str(ctx.get("as_of") or "") or None,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                lineage={
                    "curated_bundle": {"bundle_id": str(bundle_id), "bundle_digest": str(bundle.bundle_digest)},
                    "curated_datum": {"datum_id": str(datum_id), "semantic_key": semantic_key, "cur_payload_digest": str(datum.cur_payload_digest)},
                },
            )
        except DataNotFoundError:
            raise
        except Exception as e:
            raise SourceNotAvailableError(f"curated_internal error: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _load_prj(self, prj_id: str) -> FocalActorContext:
        store = FocalActorContextStore(project_root=self.project_root)
        try:
            base, ver = _split_versioned_id(prj_id)
            if ver is None:
                rec = store.get_latest(base)
            else:
                rec = store.get_by_version(base, ver)
            if rec is None:
                raise DataNotFoundError(f"PRJ not found: {prj_id}")
            return rec
        finally:
            store.close()

    def _select_bundle_from_pack(self, *, pack_id: str, ctx: Dict[str, Any]) -> Tuple[str, str]:
        conn = open_brownfield_db(project_root=self.project_root)
        try:
            migrate_brownfield_db(conn)
            store = BrownfieldPackStore(conn)
            pack = store.get_latest(pack_id)
            if pack is None:
                raise DataNotFoundError(f"Pack not found: {pack_id}")

            spec = pack.spec or {}
            selector = ctx.get("as_of_selector")
            if selector is None:
                selector = (spec.get("as_of_selector") or {}).get("mode") if isinstance(spec.get("as_of_selector"), dict) else None
            selector_mode = str(selector or "latest_validated")

            pivot = ctx.get("as_of")
            picked = select_bundle_from_pack_spec(pack_spec=spec, as_of_selector=selector_mode, as_of=str(pivot) if pivot is not None else None)
            bid = str(picked.get("bundle_id") or "").strip()
            bd = str(picked.get("bundle_digest") or "").strip()
            if not bid or not bd:
                raise DataNotFoundError("Selected pack bundle is missing bundle_id/bundle_digest")
            return bid, bd
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _resolve_semantic_key(self, request: EvidenceRequest) -> str:
        ctx = request.context or {}
        sk = ctx.get("curated_semantic_key")
        if sk:
            return str(sk)

        metric_id = str(request.metric_id or "").strip()
        if not metric_id:
            raise DataNotFoundError("metric_id is required")

        year = ctx.get("year")
        if year is not None and str(year).strip() != "":
            return make_semantic_key(datum_type="kv", entity="metric", name=metric_id, period=str(year))

        as_of = ctx.get("as_of")
        if as_of is not None and str(as_of).strip() != "":
            return make_semantic_key(datum_type="kv", entity="metric", name=metric_id, as_of=str(as_of))

        raise DataNotFoundError("curated_semantic_key or year/as_of is required to resolve semantic_key")

    @staticmethod
    def _extract_numeric_value(payload: Dict[str, Any], ctx: Dict[str, Any], *, metric_id: str) -> float:
        ptr = ctx.get("curated_json_pointer")
        if ptr:
            v = _extract_json_pointer(payload, str(ptr))
            if isinstance(v, (int, float)):
                return float(v)
            raise DataNotFoundError(f"Non-numeric value at curated_json_pointer: {ptr}")

        field = ctx.get("curated_field")
        if field:
            v = payload.get(str(field))
            if isinstance(v, (int, float)):
                return float(v)
            raise DataNotFoundError(f"Non-numeric value at curated_field: {field}")

        v = payload.get("value")
        if isinstance(v, (int, float)):
            return float(v)

        v2 = payload.get(metric_id)
        if isinstance(v2, (int, float)):
            return float(v2)

        raise DataNotFoundError("No numeric value found in CUR payload (expected 'value' or explicit field)")
