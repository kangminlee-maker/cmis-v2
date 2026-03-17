"""CMIS v2 Evidence Engine — Evidence collection and management.

MVP scope: Structures evidence requests and returns placeholder results.
Actual data source integration (KOSIS, DART, Google Search, etc.) is deferred
to subsequent phases.

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from cmis_v2.generated.validators import validate_metric_id

# ---------------------------------------------------------------------------
# Module-level store
# ---------------------------------------------------------------------------

_EVIDENCE_STORE: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def collect_evidence(
    query: str,
    domain_id: str = "",
    region: str = "KR",
    metric_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Collect evidence for the given query and domain context.

    MVP: Returns structured evidence request and placeholder results.
    Future: Will call actual data sources (KOSIS, DART, Google Search, etc.)

    Args:
        query: What to search for (e.g., "한국 성인 영어 교육 시장 규모")
        domain_id: Domain identifier (e.g., "Adult_Language_Education_KR")
        region: Region code (default "KR")
        metric_ids: Optional list of specific metric IDs to collect evidence for

    Returns:
        dict with evidence_id, query, records, sufficiency, lineage.
    """
    # Validate metric_ids if provided
    if metric_ids is not None:
        invalid = [m for m in metric_ids if not validate_metric_id(m)]
        if invalid:
            return {"error": f"Invalid metric IDs: {invalid}"}

    evidence_id = f"EVD-{uuid4().hex[:6]}"
    now = datetime.now().isoformat()

    # Build metric coverage map
    metric_coverage: dict[str, bool] = {}
    if metric_ids:
        for mid in metric_ids:
            metric_coverage[mid] = False

    result: dict[str, Any] = {
        "evidence_id": evidence_id,
        "query": query,
        "domain_id": domain_id,
        "region": region,
        "records": [],
        "sufficiency": {
            "total_records": 0,
            "by_tier": {"official": 0, "curated": 0, "commercial": 0},
            "metric_coverage": metric_coverage,
        },
        "lineage": {
            "engine": "evidence",
            "query": query,
            "timestamp": now,
        },
    }

    _EVIDENCE_STORE[evidence_id] = result
    return result


def add_record(
    evidence_id: str,
    source_tier: str,
    source_name: str,
    content: str,
    confidence: float = 0.5,
    metric_ids_covered: list[str] | None = None,
) -> dict[str, Any]:
    """Add an evidence record to an existing evidence collection.

    Used by LM after gathering information to populate evidence.

    Args:
        evidence_id: ID of the evidence collection to add to.
        source_tier: One of "official", "curated", "commercial".
        source_name: Human-readable source name.
        content: The evidence content/summary.
        confidence: Confidence score 0.0-1.0.
        metric_ids_covered: Optional list of metric IDs this record covers.

    Returns:
        The new record dict, or an error dict.
    """
    if evidence_id not in _EVIDENCE_STORE:
        return {"error": f"Evidence collection not found: {evidence_id}"}

    if source_tier not in ("official", "curated", "commercial"):
        return {"error": f"Invalid source_tier: {source_tier!r}. Must be one of: official, curated, commercial"}

    confidence = max(0.0, min(1.0, confidence))

    record_id = f"REC-{uuid4().hex[:6]}"
    now = datetime.now().isoformat()

    record: dict[str, Any] = {
        "record_id": record_id,
        "source_tier": source_tier,
        "source_name": source_name,
        "content": content,
        "confidence": confidence,
        "collected_at": now,
    }

    evd = _EVIDENCE_STORE[evidence_id]
    evd["records"].append(record)

    # Update sufficiency
    sufficiency = evd["sufficiency"]
    sufficiency["total_records"] = len(evd["records"])
    if source_tier in sufficiency["by_tier"]:
        sufficiency["by_tier"][source_tier] += 1

    # Update metric coverage
    if metric_ids_covered:
        for mid in metric_ids_covered:
            if mid in sufficiency["metric_coverage"]:
                sufficiency["metric_coverage"][mid] = True

    return record


def get_evidence(evidence_id: str) -> dict[str, Any]:
    """Retrieve an evidence collection by ID.

    Args:
        evidence_id: The evidence collection ID.

    Returns:
        The evidence dict, or an error dict.
    """
    if evidence_id not in _EVIDENCE_STORE:
        return {"error": f"Evidence collection not found: {evidence_id}"}
    return _EVIDENCE_STORE[evidence_id]
