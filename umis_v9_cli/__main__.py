"""UMIS v9 CLI - Command Line Interface

Usage:
    umis structure-analysis --domain Adult_Language_Education_KR --region KR
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from umis_v9_core.workflow import run_structure_analysis


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
    """structure-analysis 명령 실행"""
    print("=" * 60)
    print("UMIS v9 - Structure Analysis v1")
    print("=" * 60)
    print()
    
    result = run_structure_analysis(
        domain_id=args.domain,
        region=args.region,
        segment=args.segment,
        as_of=args.as_of
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
        print(f"✅ 결과 저장: {output_path}")


def main():
    """메인 진입점"""
    parser = argparse.ArgumentParser(
        description="UMIS v9 - Universal Market Intelligence System v9"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # structure-analysis 명령
    sa_parser = subparsers.add_parser(
        'structure-analysis',
        help='시장 구조 분석'
    )
    sa_parser.add_argument(
        '--domain',
        required=True,
        help='도메인 ID (예: Adult_Language_Education_KR)'
    )
    sa_parser.add_argument(
        '--region',
        required=True,
        help='지역 (예: KR)'
    )
    sa_parser.add_argument(
        '--segment',
        default=None,
        help='세그먼트 (선택)'
    )
    sa_parser.add_argument(
        '--as-of',
        default=None,
        help='기준일 (선택, 예: 2025-12-05)'
    )
    sa_parser.add_argument(
        '--output',
        default=None,
        help='JSON 출력 파일 경로 (선택)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'structure-analysis':
        cmd_structure_analysis(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
