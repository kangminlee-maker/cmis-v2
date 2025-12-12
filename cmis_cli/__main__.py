"""CMIS CLI - Command Line Interface

v2.0: Generic workflow run + Role/Policy 통합

Usage:
    cmis structure-analysis --domain ... --region ...
    cmis opportunity-discovery --domain ... --region ...
    cmis workflow run <workflow_id> --input key=value

2025-12-11: Workflow CLI Phase 1
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cmis_cli.commands import (
    cmd_structure_analysis,
    cmd_opportunity_discovery,
    cmd_workflow_run,
    cmd_compare_contexts,
    cmd_batch_analysis,
    cmd_report_generate,
    cmd_cache_manage,
    cmd_config_validate
)


# (cmd_structure_analysis는 commands/structure_analysis.py로 이동)


def main():
    """메인 진입점"""
    parser = argparse.ArgumentParser(
        description="CMIS - Contextual Market Intelligence System v3.2",
        epilog="자세한 정보: cmis <command> --help"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # ========== workflow run (Generic) ==========
    workflow_parser = subparsers.add_parser(
        'workflow',
        help='Generic workflow runner'
    )
    workflow_subparsers = workflow_parser.add_subparsers(dest='workflow_command')
    
    run_parser = workflow_subparsers.add_parser(
        'run',
        help='Run canonical workflow'
    )
    run_parser.add_argument(
        'workflow_id',
        help='Workflow ID (structure_analysis, opportunity_discovery)'
    )
    run_parser.add_argument(
        '--input',
        action='append',
        help='Input key=value (예: --input domain_id=Test)'
    )
    run_parser.add_argument('--role', help='Role override')
    run_parser.add_argument('--policy', help='Policy override')
    run_parser.add_argument('--output', help='출력 파일')
    run_parser.add_argument('--dry-run', action='store_true', help='실행 계획만 출력')
    
    # ========== structure-analysis ==========
    sa_parser = subparsers.add_parser(
        'structure-analysis',
        help='시장 구조 분석'
    )
    sa_parser.add_argument('--domain', required=True, help='도메인 ID')
    sa_parser.add_argument('--region', required=True, help='지역')
    sa_parser.add_argument('--segment', help='세그먼트')
    sa_parser.add_argument('--as-of', dest='as_of', help='기준일')
    sa_parser.add_argument('--project-context', dest='project_context', help='프로젝트 컨텍스트 ID')
    sa_parser.add_argument('--role', help='Role (기본: structure_analyst)')
    sa_parser.add_argument('--policy', help='Policy (기본: reporting_strict)')
    sa_parser.add_argument('--output', help='출력 파일')
    sa_parser.add_argument('--dry-run', action='store_true', help='실행 계획만')
    
    # ========== opportunity-discovery ==========
    od_parser = subparsers.add_parser(
        'opportunity-discovery',
        help='기회 발굴 및 Gap 분석'
    )
    od_parser.add_argument('--domain', required=True, help='도메인 ID')
    od_parser.add_argument('--region', required=True, help='지역')
    od_parser.add_argument('--segment', help='세그먼트')
    od_parser.add_argument('--project-context', dest='project_context', help='프로젝트 컨텍스트 ID')
    od_parser.add_argument('--top-n', dest='top_n', type=int, default=5, help='상위 N개 기회')
    od_parser.add_argument('--min-feasibility', dest='min_feasibility', 
                           choices=['high', 'medium', 'low'], help='최소 feasibility')
    od_parser.add_argument('--role', help='Role (기본: opportunity_designer)')
    od_parser.add_argument('--policy', help='Policy (기본: exploration_friendly)')
    od_parser.add_argument('--output', help='출력 파일')
    od_parser.add_argument('--dry-run', action='store_true', help='실행 계획만')
    
    # ========== compare-contexts ==========
    cc_parser = subparsers.add_parser(
        'compare-contexts',
        help='분석 컨텍스트 비교'
    )
    cc_parser.add_argument(
        '--context1',
        required=True,
        help='Context 1 (예: domain:Adult_Language,region:KR)'
    )
    cc_parser.add_argument(
        '--context2',
        required=True,
        help='Context 2 (예: domain:Adult_Language,region:KR,project_context:PRJ-001)'
    )
    cc_parser.add_argument('--output', help='출력 파일')
    cc_parser.add_argument('--format', default='table', 
                           choices=['table', 'json', 'markdown'], help='출력 형식')
    
    # ========== batch-analysis ==========
    batch_parser = subparsers.add_parser(
        'batch-analysis',
        help='일괄 분석 (병렬 처리)'
    )
    batch_parser.add_argument('--config', required=True, help='Batch config YAML')
    batch_parser.add_argument('--output-dir', dest='output_dir', help='출력 디렉토리')
    batch_parser.add_argument('--parallel', action='store_true', help='병렬 실행')
    batch_parser.add_argument('--workers', type=int, default=4, help='병렬 작업 수')
    
    # ========== report-generate ==========
    report_parser = subparsers.add_parser(
        'report-generate',
        help='보고서 생성'
    )
    report_parser.add_argument('--input', required=True, help='분석 결과 JSON')
    report_parser.add_argument('--template', required=True, 
                               choices=['structure_analysis', 'opportunity_discovery'],
                               help='템플릿')
    report_parser.add_argument('--output', help='출력 파일')
    report_parser.add_argument('--format', default='markdown',
                              choices=['markdown', 'html', 'pdf'], help='출력 형식')
    report_parser.add_argument('--include-lineage', dest='include_lineage',
                              action='store_true', help='Lineage 포함')
    
    # ========== cache-manage ==========
    cache_parser = subparsers.add_parser(
        'cache-manage',
        help='캐시 관리'
    )
    cache_parser.add_argument('--status', action='store_true', help='캐시 상태')
    cache_parser.add_argument('--clear', action='store_true', help='캐시 클리어')
    cache_parser.add_argument('--stats', action='store_true', help='캐시 통계')
    cache_parser.add_argument('--type', choices=['evidence', 'snapshots', 'results', 'all'],
                             help='캐시 타입')
    
    # ========== config-validate ==========
    validate_parser = subparsers.add_parser(
        'config-validate',
        help='설정 검증'
    )
    validate_parser.add_argument('--file', help='Config 파일 (기본: cmis.yaml)')
    validate_parser.add_argument('--check-seeds', dest='check_seeds', action='store_true')
    validate_parser.add_argument('--check-patterns', dest='check_patterns', action='store_true')
    validate_parser.add_argument('--check-workflows', dest='check_workflows', action='store_true')
    validate_parser.add_argument('--check-all', dest='check_all', action='store_true')
    
    # Parse
    args = parser.parse_args()
    
    # Dispatch
    if args.command == 'workflow':
        if args.workflow_command == 'run':
            cmd_workflow_run(args)
        else:
            workflow_parser.print_help()
    elif args.command == 'structure-analysis':
        cmd_structure_analysis(args)
    elif args.command == 'opportunity-discovery':
        cmd_opportunity_discovery(args)
    elif args.command == 'compare-contexts':
        cmd_compare_contexts(args)
    elif args.command == 'batch-analysis':
        cmd_batch_analysis(args)
    elif args.command == 'report-generate':
        cmd_report_generate(args)
    elif args.command == 'cache-manage':
        cmd_cache_manage(args)
    elif args.command == 'config-validate':
        cmd_config_validate(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
