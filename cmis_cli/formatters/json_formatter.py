"""JSON Formatter

Lineage 포함 JSON 출력

2025-12-11: Workflow CLI Phase 1
"""

from __future__ import annotations

import json
from typing import Any, Dict
from datetime import datetime


def format_json(
    result: Dict[str, Any],
    include_lineage: bool = True,
    pretty: bool = True
) -> str:
    """결과를 JSON으로 포맷팅
    
    Args:
        result: 워크플로우 결과
        include_lineage: Lineage 포함 여부
        pretty: 정렬 출력 여부
    
    Returns:
        JSON 문자열
    """
    output = {
        "meta": result.get("meta", {}),
        "inputs": result.get("inputs", {}),
        "graph_overview": result.get("graph_overview", {}),
        "pattern_matches": [],
        "metrics": [],
        "completeness": result.get("completeness", "unknown")
    }
    
    # Pattern matches
    for pm in result.get("pattern_matches", []):
        pattern_dict = {
            "pattern_id": pm.pattern_id if hasattr(pm, 'pattern_id') else pm.get("pattern_id"),
            "description": pm.description if hasattr(pm, 'description') else pm.get("description"),
            "combined_score": pm.combined_score if hasattr(pm, 'combined_score') else pm.get("combined_score")
        }
        
        if include_lineage and hasattr(pm, 'evidence'):
            pattern_dict["evidence"] = pm.evidence
        
        output["pattern_matches"].append(pattern_dict)
    
    # Metrics
    for vr in result.get("metrics", []):
        metric_dict = {
            "metric_id": vr.metric_id if hasattr(vr, 'metric_id') else vr.get("metric_id"),
            "point_estimate": vr.point_estimate if hasattr(vr, 'point_estimate') else vr.get("point_estimate"),
            "quality": vr.quality if hasattr(vr, 'quality') else vr.get("quality", {})
        }
        
        if include_lineage and hasattr(vr, 'lineage'):
            metric_dict["lineage"] = vr.lineage
        
        output["metrics"].append(metric_dict)
    
    # JSON 변환
    if pretty:
        return json.dumps(output, ensure_ascii=False, indent=2, default=str)
    else:
        return json.dumps(output, ensure_ascii=False, default=str)

