"""structure-analysis 명령어

시장 구조 분석

2025-12-11: Workflow CLI Phase 1
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmis_core.workflow import run_structure_analysis


def format_number(num: float) -> str:
    """숫자 포맷팅 (억/조 단위)"""
    if num >= 1_000_000_000_000:  # 조
        return f"{num / 1_000_000_000_000:.1f}조"
    elif num >= 100_000_000:  # 억
        return f"{num / 100_000_000:.0f}억"
    elif num >= 10_000:  # 만
        return f"{num / 10_000:.0f}만"
    else:
        return f"{num:,.0f}"


def cmd_structure_analysis(args):
    """structure-analysis 명령 실행

    Args:
        args: Argparse args
    """
    # --dry-run
    if args.dry_run:
        print("[DRY RUN MODE]")
        print(f"Workflow: structure_analysis")
        print(f"Domain: {args.domain}")
        print(f"Region: {args.region}")
        print(f"Role: {args.role or 'structure_analyst (default)'}")
        print(f"Policy: {args.policy or 'reporting_strict (default)'}")
        print()
        return

    print("=" * 60)
    print("CMIS - Structure Analysis")
    print("=" * 60)
    print()

    result = run_structure_analysis(
        domain_id=args.domain,
        region=args.region,
        segment=args.segment,
        as_of=args.as_of,
        focal_actor_context_id=args.focal_actor_context_id,
    )

    print()
    print("=" * 60)
    print("결과")
    print("=" * 60)
    print()

    # Meta
    print(f"도메인: {result.meta['domain_id']}")
    print(f"지역:   {result.meta['region']}")
    if result.meta.get('segment'):
        print(f"세그먼트: {result.meta['segment']}")
    print()

    # Graph Overview
    print("[R-Graph 구조]")
    print(f"  Actors:      {result.graph_overview['num_actors']}개")
    print(f"  Money Flows: {result.graph_overview['num_money_flows']}개")
    print(f"  States:      {result.graph_overview.get('num_states', 0)}개")
    print()

    # Actor Types
    if result.graph_overview.get('actor_types'):
        print("  Actor 종류:")
        for kind, count in result.graph_overview['actor_types'].items():
            print(f"    - {kind}: {count}개")
        print()

    # Patterns
    print("[감지된 패턴]")
    for pm in result.pattern_matches:
        print(f"  ✓ {pm.pattern_id}")
        print(f"    {pm.description}")
        print(f"    적합도: {pm.structure_fit_score:.2f}")
    print()

    # Metrics
    print("[핵심 Metric]")
    for vr in result.metrics:
        if vr.point_estimate is not None:
            formatted = format_number(vr.point_estimate)
            print(f"  {vr.metric_id}: {formatted}")
        else:
            print(f"  {vr.metric_id}: (미구현)")
    print()

    # 실행 시간
    print(f"실행 시간: {result.execution_time:.2f}초")
    print()

    # JSON 저장 (선택적)
    if args.output:
        import json
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"[OK] 결과 저장: {output_path}")



