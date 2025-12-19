"""Markdown Formatter

"세계·변화·결과·논증 구조" 보고서 생성

2025-12-11: Workflow CLI Phase 1
"""

from __future__ import annotations

from typing import Any, Dict
from datetime import datetime


def format_markdown(
    result: Dict[str, Any],
    include_lineage: bool = True
) -> str:
    """결과를 Markdown 보고서로 포맷팅

    4-Part 구조:
    - Part 1: 현실 구조 (세계)
    - Part 2: 반복 패턴 (메커니즘)
    - Part 3: 핵심 지표 (결과)
    - Part 4: 논증 구조 (근거) - Lineage

    Args:
        result: 워크플로우 결과
        include_lineage: Lineage 섹션 포함 여부

    Returns:
        Markdown 문자열
    """
    lines = []

    # Header
    lines.append("# Structure Analysis Report")
    lines.append("")

    meta = result.get("meta", {})
    lines.append(f"**도메인**: {meta.get('domain_id', 'Unknown')}")
    lines.append(f"**지역**: {meta.get('region', 'Unknown')}")
    lines.append(f"**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")

    pattern_matches = result.get("pattern_matches", [])
    if pattern_matches:
        top_pattern = pattern_matches[0]
        pattern_id = top_pattern.pattern_id if hasattr(top_pattern, 'pattern_id') else top_pattern.get("pattern_id")
        lines.append(f"이 시장은 **{pattern_id}** 특징을 보입니다.")
    else:
        lines.append("이 시장의 구조를 분석했습니다.")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Part 1: 현실 구조 (세계)
    lines.append("## Part 1: 현실 구조 (세계)")
    lines.append("")

    graph_overview = result.get("graph_overview", {})

    lines.append("### R-Graph Overview")
    lines.append("")
    lines.append(f"- **Actors**: {graph_overview.get('num_actors', 0)}개")
    lines.append(f"- **Money Flows**: {graph_overview.get('num_money_flows', 0)}개")
    lines.append(f"- **States**: {graph_overview.get('num_states', 0)}개")
    lines.append("")

    # Actor 분포
    if graph_overview.get('actor_types'):
        lines.append("### Actor 분포")
        lines.append("")
        lines.append("| 종류 | 개수 |")
        lines.append("|------|------|")

        for kind, count in graph_overview['actor_types'].items():
            lines.append(f"| {kind} | {count}개 |")

        lines.append("")

    lines.append("---")
    lines.append("")

    # Part 2: 반복 패턴 (메커니즘)
    lines.append("## Part 2: 반복 패턴 (메커니즘)")
    lines.append("")

    lines.append("### 감지된 패턴")
    lines.append("")

    for pm in pattern_matches:
        pattern_id = pm.pattern_id if hasattr(pm, 'pattern_id') else pm.get("pattern_id")
        description = pm.description if hasattr(pm, 'description') else pm.get("description")
        score = pm.combined_score if hasattr(pm, 'combined_score') else pm.get("combined_score", 0)

        lines.append(f"### {pattern_id} (적합도: {score:.2f})")
        lines.append("")
        lines.append(description)
        lines.append("")

    if not pattern_matches:
        lines.append("*감지된 패턴 없음*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Part 3: 핵심 지표 (결과)
    lines.append("## Part 3: 핵심 지표 (결과)")
    lines.append("")

    metrics = result.get("metrics", [])

    if metrics:
        lines.append("| Metric | 값 | 품질 |")
        lines.append("|--------|-----|------|")

        for vr in metrics:
            metric_id = vr.metric_id if hasattr(vr, 'metric_id') else vr.get("metric_id")
            value = vr.point_estimate if hasattr(vr, 'point_estimate') else vr.get("point_estimate")
            quality = vr.quality if hasattr(vr, 'quality') else vr.get("quality", {})

            if value is not None:
                formatted_value = f"{value:,.0f}"
                status = quality.get("status", "unknown")
                lines.append(f"| {metric_id} | {formatted_value} | {status} |")
            else:
                lines.append(f"| {metric_id} | N/A | - |")

        lines.append("")
    else:
        lines.append("*Metric 없음*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Part 4: 논증 구조 (근거) - Lineage
    if include_lineage:
        lines.append("## Part 4: 논증 구조 (근거)")
        lines.append("")

        lines.append("### Metric Lineage")
        lines.append("")

        for vr in metrics:
            metric_id = vr.metric_id if hasattr(vr, 'metric_id') else vr.get("metric_id")
            value = vr.point_estimate if hasattr(vr, 'point_estimate') else vr.get("point_estimate")
            quality = vr.quality if hasattr(vr, 'quality') else vr.get("quality", {})
            lineage = vr.lineage if hasattr(vr, 'lineage') else vr.get("lineage", {})

            if value is not None:
                formatted_value = f"{value:,.0f}"
            else:
                formatted_value = "N/A"

            confidence = quality.get("confidence", 0)

            lines.append(f"**{metric_id}** ({formatted_value}, 신뢰도 {confidence:.2f}):")
            lines.append("")

            # Resolution method
            method = quality.get("method", "unknown")
            lines.append(f"- 방법: {method}")

            # Formula (derived인 경우)
            if "formula" in lineage:
                lines.append(f"- 공식: {lineage['formula']}")

            # Evidence
            if "from_evidence_ids" in lineage:
                evidence_ids = lineage["from_evidence_ids"]
                if evidence_ids:
                    lines.append(f"- Evidence: {', '.join(evidence_ids[:3])}")

            # Engine
            if "engine_ids" in lineage:
                engine_ids = lineage["engine_ids"]
                if engine_ids:
                    lines.append(f"- 사용 엔진: {', '.join(engine_ids)}")

            lines.append("")

        if not metrics:
            lines.append("*Metric 없음*")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**완성도**: {result.get('completeness', 'unknown')}")

    return "\n".join(lines)
