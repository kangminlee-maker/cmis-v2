"""CMIS v2 Evidence Engine — Evidence collection and management.

Phase 2: Integrates real data sources (OpenAI web search) alongside
placeholder stubs for KOSIS and DART.

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
# Available sources
# ---------------------------------------------------------------------------

_AVAILABLE_SOURCES = frozenset({"web_search", "kosis", "dart"})
_DEFAULT_SOURCES = ["web_search"]

# ---------------------------------------------------------------------------
# Data source adapters
# ---------------------------------------------------------------------------


def _search_via_openai(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search the web using OpenAI Responses API with web_search_preview tool.

    Uses the OPENAI_API_KEY environment variable. Returns empty list on
    failure (graceful degradation).
    """
    try:
        import os

        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return []

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search_preview"}],
            input=(
                f"Search for market data and statistics about: {query}\n"
                f"Return up to {max_results} key findings with source URLs."
            ),
        )

        # Extract text content from response
        records: list[dict[str, Any]] = []
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        # Parse annotations for URLs
                        urls: list[str] = []
                        if hasattr(content, "annotations") and content.annotations:
                            for ann in content.annotations:
                                if hasattr(ann, "url"):
                                    urls.append(ann.url)

                        records.append({
                            "record_id": f"REC-{uuid4().hex[:6]}",
                            "source_tier": "web",
                            "source_name": "openai_web_search",
                            "title": query,
                            "content": content.text[:2000],
                            "urls": urls[:max_results],
                            "confidence": 0.5,
                            "collected_at": datetime.now().isoformat(),
                        })

        return records
    except Exception:
        return []  # graceful degradation


def _search_kosis(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search KOSIS (Korea Statistical Information Service).

    Requires KOSIS_API_KEY environment variable.
    Returns official statistical data as evidence records.
    source_tier: "official", confidence: 0.8
    """
    import os

    api_key = os.environ.get("KOSIS_API_KEY")
    if not api_key:
        return []  # graceful: no key = no results

    try:
        import json
        import urllib.parse
        import urllib.request

        params = urllib.parse.urlencode({
            "method": "getList",
            "apiKey": api_key,
            "format": "json",
            "jsonSite": "Y",
            "searchNm": query,
            "numOfRows": str(max_results),
        })
        url = f"https://kosis.kr/openapi/statisticsData.do?{params}"

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        records: list[dict[str, Any]] = []
        items = data if isinstance(data, list) else data.get("items", data.get("row", []))
        if not isinstance(items, list):
            items = []

        for item in items[:max_results]:
            records.append({
                "record_id": f"REC-{uuid4().hex[:6]}",
                "source_tier": "official",
                "source_name": "kosis",
                "title": item.get("TBL_NM", item.get("statNm", str(item)[:100])),
                "content": str(item),
                "confidence": 0.8,
                "collected_at": datetime.now().isoformat(),
            })
        return records
    except Exception:
        return []


def _search_dart(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search DART (Korea Financial Supervisory Service disclosures).

    Requires DART_API_KEY environment variable.
    Returns corporate disclosure data as evidence records.
    source_tier: "official", confidence: 0.85
    """
    import os

    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        return []

    try:
        import json
        import urllib.parse
        import urllib.request

        params = urllib.parse.urlencode({
            "crtfc_key": api_key,
            "corp_name": query,
            "page_count": str(max_results),
        })
        url = f"https://opendart.fss.or.kr/api/list.json?{params}"

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        records: list[dict[str, Any]] = []
        items = data.get("list", [])
        for item in items[:max_results]:
            records.append({
                "record_id": f"REC-{uuid4().hex[:6]}",
                "source_tier": "official",
                "source_name": "dart",
                "title": item.get("report_nm", ""),
                "content": (
                    f"{item.get('corp_name', '')} - "
                    f"{item.get('report_nm', '')} "
                    f"({item.get('rcept_dt', '')})"
                ),
                "confidence": 0.85,
                "collected_at": datetime.now().isoformat(),
            })
        return records
    except Exception:
        return []


_SOURCE_ADAPTERS: dict[str, Any] = {
    "web_search": _search_via_openai,
    "kosis": _search_kosis,
    "dart": _search_dart,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def collect_evidence(
    query: str,
    domain_id: str = "",
    region: str = "KR",
    metric_ids: list[str] | None = None,
    sources: list[str] | None = None,
    project_id: str = "",
) -> dict[str, Any]:
    """Collect evidence for the given query and domain context.

    Searches configured data sources and aggregates results into
    evidence records.

    Args:
        query: What to search for (e.g., "한국 성인 영어 교육 시장 규모")
        domain_id: Domain identifier (e.g., "Adult_Language_Education_KR")
        region: Region code (default "KR")
        metric_ids: Optional list of specific metric IDs to collect evidence for
        sources: Data sources to query. Options: "web_search", "kosis", "dart".
                 None means auto-select (defaults to web_search via OpenAI).

    Returns:
        dict with evidence_id, query, records, sufficiency, lineage.
    """
    # Validate metric_ids if provided
    if metric_ids is not None:
        invalid = [m for m in metric_ids if not validate_metric_id(m)]
        if invalid:
            return {"error": f"Invalid metric IDs: {invalid}"}

    # Resolve sources
    source_list = sources if sources is not None else _DEFAULT_SOURCES
    invalid_sources = [s for s in source_list if s not in _AVAILABLE_SOURCES]
    if invalid_sources:
        return {"error": f"Unknown sources: {invalid_sources}. Available: {sorted(_AVAILABLE_SOURCES)}"}

    evidence_id = f"EVD-{uuid4().hex[:6]}"
    now = datetime.now().isoformat()

    # Build metric coverage map
    metric_coverage: dict[str, bool] = {}
    if metric_ids:
        for mid in metric_ids:
            metric_coverage[mid] = False

    # Collect from each source
    all_records: list[dict[str, Any]] = []
    source_errors: dict[str, str] = {}

    for src in source_list:
        adapter = _SOURCE_ADAPTERS.get(src)
        if adapter is None:
            continue
        try:
            records = adapter(query)
            all_records.extend(records)
        except Exception as e:
            source_errors[src] = str(e)
            # Graceful degradation: continue with other sources

    # Compute sufficiency
    by_tier: dict[str, int] = {"official": 0, "curated": 0, "commercial": 0, "web": 0}
    for rec in all_records:
        tier = rec.get("source_tier", "")
        if tier in by_tier:
            by_tier[tier] += 1

    result: dict[str, Any] = {
        "evidence_id": evidence_id,
        "query": query,
        "domain_id": domain_id,
        "region": region,
        "records": all_records,
        "sufficiency": {
            "total_records": len(all_records),
            "by_tier": by_tier,
            "metric_coverage": metric_coverage,
        },
        "lineage": {
            "engine": "evidence",
            "query": query,
            "sources_queried": source_list,
            "source_errors": source_errors if source_errors else None,
            "timestamp": now,
        },
    }

    _EVIDENCE_STORE[evidence_id] = result
    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "evidence", evidence_id, result)
    return result


def add_record(
    evidence_id: str,
    source_tier: str,
    source_name: str,
    content: str,
    confidence: float = 0.5,
    metric_ids_covered: list[str] | None = None,
    project_id: str = "",
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
        if project_id:
            from cmis_v2.engine_store import load_engine_data
            loaded = load_engine_data(project_id, "evidence", evidence_id)
            if loaded is not None:
                _EVIDENCE_STORE[evidence_id] = loaded
        if evidence_id not in _EVIDENCE_STORE:
            return {"error": f"Evidence collection not found: {evidence_id}"}

    if source_tier not in ("official", "curated", "commercial", "web"):
        return {"error": f"Invalid source_tier: {source_tier!r}. Must be one of: official, curated, commercial, web"}

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

    if project_id:
        from cmis_v2.engine_store import save_engine_data
        save_engine_data(project_id, "evidence", evidence_id, evd)

    return record


def get_evidence(evidence_id: str, project_id: str = "") -> dict[str, Any]:
    """Retrieve an evidence collection by ID.

    Args:
        evidence_id: The evidence collection ID.
        project_id: Optional project ID for file-based lookup.

    Returns:
        The evidence dict, or an error dict.
    """
    if evidence_id in _EVIDENCE_STORE:
        return _EVIDENCE_STORE[evidence_id]
    if project_id:
        from cmis_v2.engine_store import load_engine_data
        data = load_engine_data(project_id, "evidence", evidence_id)
        if data is not None:
            _EVIDENCE_STORE[evidence_id] = data
            return data
    return {"error": f"Evidence collection not found: {evidence_id}"}
