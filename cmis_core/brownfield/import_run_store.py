"""ImportRunStore (BF-04).

ImportRun(IMP)은 Brownfield ingest 실행 단위를 나타내며, 상태 머신으로 관리합니다.

상태(권장):
- staged: 파일/입력 수집 완료
- decoded: decode 완료(preview 생성 가능)
- validated: validate 완료(결정 pass/warn_only 포함)
- rejected: validate 결과 fail
- committed: CUR/CUB/PRJ 생성 완료
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from cmis_core.digest import canonical_digest


@dataclass(frozen=True)
class ImportRunRecord:
    import_run_id: str
    status: str
    created_at: str
    artifact_ids: List[str]
    mapping_ref: Optional[Dict[str, Any]]
    extractor_version: Optional[str]
    ingest_policy_digest: Optional[str]
    normalization_defaults_digest: Optional[str]
    patches_digest: Optional[str]
    input_fingerprint: str
    preview_report_artifact_id: Optional[str]
    validation_report_artifact_id: Optional[str]
    validation_decision: Optional[str]
    committed_bundle_id: Optional[str]
    notes: Optional[str]


class ImportRunStore:
    """brownfield.db의 import_runs 테이블 스토어."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def compute_input_fingerprint(
        *,
        artifact_ids: List[str],
        mapping_ref: Optional[Dict[str, Any]],
        extractor_version: Optional[str],
        ingest_policy_digest: Optional[str],
        normalization_defaults_digest: Optional[str],
        patches_digest: Optional[str],
    ) -> str:
        """결정성 입력 fingerprint를 계산합니다.

        주의: artifact_ids는 순서 의미가 없으므로 정렬하여 digest 입력을 고정합니다.
        """

        payload = {
            "artifact_ids": sorted([str(a) for a in (artifact_ids or [])]),
            "mapping_ref": mapping_ref or None,
            "extractor_version": extractor_version or None,
            "ingest_policy_digest": ingest_policy_digest or None,
            "normalization_defaults_digest": normalization_defaults_digest or None,
            "patches_digest": patches_digest or None,
        }
        return canonical_digest(payload)

    def create_staged(
        self,
        *,
        artifact_ids: List[str],
        mapping_ref: Optional[Dict[str, Any]] = None,
        extractor_version: Optional[str] = None,
        ingest_policy_digest: Optional[str] = None,
        normalization_defaults_digest: Optional[str] = None,
        patches_digest: Optional[str] = None,
        input_fingerprint: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """staged 상태의 ImportRun을 생성합니다."""

        rid = f"IMP-{uuid.uuid4().hex[:10]}"
        created_at = self._now()
        fp = (
            str(input_fingerprint)
            if input_fingerprint is not None
            else self.compute_input_fingerprint(
                artifact_ids=artifact_ids,
                mapping_ref=mapping_ref,
                extractor_version=extractor_version,
                ingest_policy_digest=ingest_policy_digest,
                normalization_defaults_digest=normalization_defaults_digest,
                patches_digest=patches_digest,
            )
        )

        self.conn.execute(
            """
            INSERT INTO import_runs(
                import_run_id, status, created_at,
                artifact_ids_json, mapping_ref_json,
                extractor_version, ingest_policy_digest, normalization_defaults_digest, patches_digest,
                input_fingerprint,
                validation_report_artifact_id, validation_decision,
                preview_report_artifact_id,
                committed_bundle_id,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                "staged",
                created_at,
                json.dumps(sorted([str(a) for a in (artifact_ids or [])]), ensure_ascii=False),
                json.dumps(mapping_ref, ensure_ascii=False) if mapping_ref is not None else None,
                str(extractor_version) if extractor_version is not None else None,
                str(ingest_policy_digest) if ingest_policy_digest is not None else None,
                str(normalization_defaults_digest) if normalization_defaults_digest is not None else None,
                str(patches_digest) if patches_digest is not None else None,
                str(fp),
                None,
                None,
                None,
                None,
                str(notes) if notes is not None else None,
            ),
        )
        return rid

    def get(self, import_run_id: str) -> Optional[ImportRunRecord]:
        cur = self.conn.execute(
            """
            SELECT
                status, created_at, artifact_ids_json, mapping_ref_json,
                extractor_version, ingest_policy_digest, normalization_defaults_digest, patches_digest,
                input_fingerprint,
                preview_report_artifact_id,
                validation_report_artifact_id, validation_decision,
                committed_bundle_id,
                notes
            FROM import_runs
            WHERE import_run_id = ?
            """,
            (str(import_run_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        (
            status,
            created_at,
            artifact_ids_json,
            mapping_ref_json,
            extractor_version,
            ingest_policy_digest,
            normalization_defaults_digest,
            patches_digest,
            input_fingerprint,
            preview_report_artifact_id,
            validation_report_artifact_id,
            validation_decision,
            committed_bundle_id,
            notes,
        ) = row

        try:
            artifact_ids = json.loads(artifact_ids_json or "[]")
        except Exception:
            artifact_ids = []
        if not isinstance(artifact_ids, list):
            artifact_ids = []

        mapping_ref: Optional[Dict[str, Any]]
        if mapping_ref_json:
            try:
                mr = json.loads(mapping_ref_json)
            except Exception:
                mr = None
            mapping_ref = mr if isinstance(mr, dict) else None
        else:
            mapping_ref = None

        return ImportRunRecord(
            import_run_id=str(import_run_id),
            status=str(status),
            created_at=str(created_at),
            artifact_ids=[str(a) for a in artifact_ids],
            mapping_ref=mapping_ref,
            extractor_version=str(extractor_version) if extractor_version is not None else None,
            ingest_policy_digest=str(ingest_policy_digest) if ingest_policy_digest is not None else None,
            normalization_defaults_digest=str(normalization_defaults_digest) if normalization_defaults_digest is not None else None,
            patches_digest=str(patches_digest) if patches_digest is not None else None,
            input_fingerprint=str(input_fingerprint),
            preview_report_artifact_id=str(preview_report_artifact_id) if preview_report_artifact_id is not None else None,
            validation_report_artifact_id=str(validation_report_artifact_id) if validation_report_artifact_id is not None else None,
            validation_decision=str(validation_decision) if validation_decision is not None else None,
            committed_bundle_id=str(committed_bundle_id) if committed_bundle_id is not None else None,
            notes=str(notes) if notes is not None else None,
        )

    def attach_preview(self, import_run_id: str, preview_report_artifact_id: str) -> None:
        """preview artifact를 연결하고 상태를 decoded로 갱신합니다."""

        rec = self.get(import_run_id)
        if rec is None:
            raise KeyError(f"Unknown import_run_id: {import_run_id}")
        if rec.status not in {"staged", "decoded"}:
            raise ValueError(f"Invalid status transition to decoded from {rec.status}")

        self.conn.execute(
            "UPDATE import_runs SET status = ?, preview_report_artifact_id = ? WHERE import_run_id = ?",
            ("decoded", str(preview_report_artifact_id), str(import_run_id)),
        )

    def attach_validation(self, import_run_id: str, validation_report_artifact_id: str, decision: str) -> None:
        """validation report artifact를 연결하고 decision에 따라 상태를 갱신합니다."""

        dec = str(decision)
        if dec not in {"pass", "fail", "warn_only"}:
            raise ValueError(f"Unknown validation decision: {decision}")

        rec = self.get(import_run_id)
        if rec is None:
            raise KeyError(f"Unknown import_run_id: {import_run_id}")
        if rec.status not in {"staged", "decoded", "validated", "rejected"}:
            raise ValueError(f"Invalid status transition to validated/rejected from {rec.status}")

        status = "rejected" if dec == "fail" else "validated"
        self.conn.execute(
            """
            UPDATE import_runs
            SET status = ?, validation_report_artifact_id = ?, validation_decision = ?
            WHERE import_run_id = ?
            """,
            (status, str(validation_report_artifact_id), dec, str(import_run_id)),
        )

    def mark_committed(self, import_run_id: str, committed_bundle_id: str) -> None:
        """commit 완료로 표시합니다."""

        rec = self.get(import_run_id)
        if rec is None:
            raise KeyError(f"Unknown import_run_id: {import_run_id}")
        if rec.status != "validated":
            raise ValueError(f"Cannot commit import_run in status={rec.status}")

        self.conn.execute(
            "UPDATE import_runs SET status = ?, committed_bundle_id = ? WHERE import_run_id = ?",
            ("committed", str(committed_bundle_id), str(import_run_id)),
        )
