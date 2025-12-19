"""CSV ingest (BF-09a).

목표:
- 업로드 파일을 ART로 저장
- ImportRun(IMP) 생성
- CSV decode 결과로 preview summary를 만들고 ART로 저장
- ImportRun에 preview artifact를 attach하여 status=decoded로 갱신

주의(누출 방지):
- preview summary는 원문 행/대량 수치를 포함하지 않고 shape/통계 중심으로 구성합니다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import sqlite3

from cmis_core.brownfield.db import migrate_brownfield_db, open_brownfield_db
from cmis_core.brownfield.import_run_store import ImportRunStore
from cmis_core.brownfield.uow import UnitOfWork
from cmis_core.stores.artifact_store import ArtifactStore


@dataclass(frozen=True)
class CsvPreviewSummary:
    columns: List[str]
    row_count: int
    non_empty_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": list(self.columns),
            "row_count": int(self.row_count),
            "non_empty_counts": dict(self.non_empty_counts),
        }


def _decode_csv_to_preview(path: Path) -> CsvPreviewSummary:
    """CSV 파일을 스트리밍으로 읽어 preview용 요약만 생성합니다."""

    p = Path(path)
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return CsvPreviewSummary(columns=[], row_count=0, non_empty_counts={})

        columns = [str(c).strip() for c in header]
        non_empty = {c: 0 for c in columns}
        row_count = 0

        for row in reader:
            row_count += 1
            # do not store raw row values; only count non-empty per column
            for idx, col in enumerate(columns):
                if idx >= len(row):
                    continue
                if str(row[idx]).strip() != "":
                    non_empty[col] = int(non_empty.get(col, 0)) + 1

        return CsvPreviewSummary(columns=columns, row_count=row_count, non_empty_counts=non_empty)


def import_csv_file(
    *,
    project_root: Path,
    file_path: Path,
    mapping_ref: Optional[Dict[str, Any]] = None,
    ingest_policy_digest: Optional[str] = None,
    normalization_defaults_digest: Optional[str] = None,
    extractor_version: str = "csv_decoder@0.1.0",
    brownfield_conn: Optional[sqlite3.Connection] = None,
    artifact_store: Optional[ArtifactStore] = None,
) -> str:
    """CSV 파일을 import하고 ImportRun(IMP-*)를 반환합니다."""

    conn = brownfield_conn or open_brownfield_db(project_root=project_root)
    migrate_brownfield_db(conn)

    art_store = artifact_store or ArtifactStore(project_root=project_root)
    # dedupe=True: 동일 파일(sha256/size) 재업로드 시 동일 ART로 재사용하여 결정성에 유리
    upload_artifact_id = art_store.put_file(Path(file_path), kind="upload", mime_type="text/csv", dedupe=True)
    stored_path = art_store.get_path(upload_artifact_id)
    if stored_path is None:
        raise RuntimeError("Failed to resolve stored artifact path")

    preview = _decode_csv_to_preview(stored_path)

    imp_store = ImportRunStore(conn)
    uow = UnitOfWork(conn)

    with uow.transaction():
        imp_id = imp_store.create_staged(
            artifact_ids=[upload_artifact_id],
            mapping_ref=mapping_ref,
            extractor_version=extractor_version,
            ingest_policy_digest=ingest_policy_digest,
            normalization_defaults_digest=normalization_defaults_digest,
        )

        preview_artifact_id = art_store.put_json(
            preview.to_dict(),
            kind="brownfield_preview",
            meta={"import_run_id": imp_id, "upload_artifact_id": upload_artifact_id},
        )
        imp_store.attach_preview(imp_id, preview_artifact_id)

    return imp_id
