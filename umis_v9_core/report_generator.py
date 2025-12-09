"""UMIS v9 Report Generator

Markdown 리포트 생성
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .types import StructureAnalysisResult


def format_number(num: float) -> str:
    """숫자 포맷팅 (억/조 단위)"""
    if num >= 1_000_000_000_000:
        return f"{num / 1_000_000_000_000:.1f}조원"
    elif num >= 100_000_000:
        return f"{num / 100_000_000:.0f}억원"
    elif num >= 10_000:
        return f"{num / 10_000:.0f}만"
    else:
        return f"{num:,.0f}"


def generate_structure_report(
    result: StructureAnalysisResult,
    output_path: Optional[str] = None
) -> str:
    """Structure Analysis 리포트 생성
    
    Args:
        result: StructureAnalysisResult
        output_path: 출력 파일 경로 (None이면 문자열만 반환)
    
    Returns:
        Markdown 문자열 (3개 섹션: Overview/Patterns/Metrics)
    """
    lines = []
    
    # Header
    lines.append(f"# Market Structure Snapshot")
    lines.append(f"")
    lines.append(f"**도메인**: {result.meta['domain_id']}")
    lines.append(f"**지역**: {result.meta['region']}")
    if result.meta.get('segment'):
        lines.append(f"**세그먼트**: {result.meta['segment']}")
    if result.meta.get('as_of'):
        lines.append(f"**기준일**: {result.meta['as_of']}")
    lines.append(f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    
    # Section 1: Overview
    lines.append(f"## 1. Market Structure Overview")
    lines.append(f"")
    lines.append(f"### R-Graph 구조")
    lines.append(f"")
    lines.append(f"| 항목 | 개수 |")
    lines.append(f"|------|------|")
    lines.append(f"| Actors | {result.graph_overview['num_actors']}개 |")
    lines.append(f"| Money Flows | {result.graph_overview['num_money_flows']}개 |")
    lines.append(f"| States | {result.graph_overview.get('num_states', 0)}개 |")
    lines.append(f"| **총 Money Flow 규모** | **{format_number(result.graph_overview.get('total_money_flow_amount', 0))}** |")
    lines.append(f"")
    
    # Actor 종류
    if result.graph_overview.get('actor_types'):
        lines.append(f"### Actor 종류")
        lines.append(f"")
        for kind, count in result.graph_overview['actor_types'].items():
            lines.append(f"- **{kind}**: {count}개")
        lines.append(f"")
    
    lines.append(f"---")
    lines.append(f"")
    
    # Section 2: Patterns
    lines.append(f"## 2. 감지된 비즈니스 패턴")
    lines.append(f"")
    
    if result.pattern_matches:
        for i, pm in enumerate(result.pattern_matches, 1):
            lines.append(f"### Pattern {i}: {pm.pattern_id}")
            lines.append(f"")
            lines.append(f"**설명**: {pm.description}")
            lines.append(f"")
            lines.append(f"**구조 적합도**: {pm.structure_fit_score:.2f}")
            lines.append(f"")
            if pm.evidence.get('node_ids'):
                lines.append(f"**근거**: {len(pm.evidence['node_ids'])}개 노드")
            lines.append(f"")
    else:
        lines.append(f"(패턴 감지 없음)")
        lines.append(f"")
    
    lines.append(f"---")
    lines.append(f"")
    
    # Section 3: Metrics
    lines.append(f"## 3. 핵심 Metric")
    lines.append(f"")
    lines.append(f"| Metric ID | 값 | 계산 방법 | 상태 |")
    lines.append(f"|-----------|-----|----------|------|")
    
    for vr in result.metrics:
        if vr.point_estimate is not None:
            value_str = format_number(vr.point_estimate)
        else:
            value_str = "N/A"
        
        method = vr.quality.get('method', 'unknown')
        status = vr.quality.get('status', 'unknown')
        
        lines.append(f"| {vr.metric_id} | {value_str} | {method} | {status} |")
    
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    
    # Footer
    lines.append(f"**생성**: UMIS v9 Structure Analysis v1")
    lines.append(f"**실행 시간**: {result.execution_time:.2f}초")
    lines.append(f"")
    
    markdown = "\n".join(lines)
    
    # 파일 저장 (선택)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"✅ 리포트 저장: {output_path}")
    
    return markdown
