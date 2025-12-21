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
    cmd_db_manage,
    cmd_config_validate,
    cmd_context_verify,
    cmd_brownfield_import,
    cmd_brownfield_preview,
    cmd_brownfield_validate,
    cmd_brownfield_commit,
    cmd_brownfield_reconcile,
    cmd_llm_benchmark_run,
    cmd_llm_benchmark_report,
    cmd_llm_benchmark_list_suites,
    cmd_cursor_init,
    cmd_cursor_doctor,
    cmd_cursor_manifest,
    cmd_cursor_bootstrap,
    cmd_cursor_ask,
    cmd_run_explain,
    cmd_run_open,
    cmd_eval_run,
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

    workflow_run_parser = workflow_subparsers.add_parser(
        'run',
        help='Run canonical workflow'
    )
    workflow_run_parser.add_argument(
        'workflow_id',
        help='Workflow ID (structure_analysis, opportunity_discovery)'
    )
    workflow_run_parser.add_argument(
        '--input',
        action='append',
        help='Input key=value (예: --input domain_id=Test)'
    )
    workflow_run_parser.add_argument('--role', help='Role override')
    workflow_run_parser.add_argument('--policy', help='Policy override')
    workflow_run_parser.add_argument('--output', help='출력 파일')
    workflow_run_parser.add_argument('--dry-run', action='store_true', help='실행 계획만 출력')

    # ========== structure-analysis ==========
    sa_parser = subparsers.add_parser(
        'structure-analysis',
        help='시장 구조 분석'
    )
    sa_parser.add_argument('--domain', required=True, help='도메인 ID')
    sa_parser.add_argument('--region', required=True, help='지역')
    sa_parser.add_argument('--segment', help='세그먼트')
    sa_parser.add_argument('--as-of', dest='as_of', help='기준일')
    sa_parser.add_argument('--focal-actor-context-id', dest='focal_actor_context_id', help='FocalActorContext ID (PRJ-*)')
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
    od_parser.add_argument('--focal-actor-context-id', dest='focal_actor_context_id', help='FocalActorContext ID (PRJ-*)')
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
        help='Context 2 (예: domain:Adult_Language,region:KR,focal_actor_context_id:PRJ-001)'
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
    cache_parser.add_argument('--project-root', dest='project_root', help='프로젝트 루트 (기본: cwd)')
    cache_parser.add_argument('--status', action='store_true', help='캐시 상태')
    cache_parser.add_argument('--clear', action='store_true', help='캐시 클리어')
    cache_parser.add_argument('--stats', action='store_true', help='캐시 통계')
    cache_parser.add_argument('--type', choices=['evidence', 'snapshots', 'results', 'all'],
                             help='캐시 타입')

    # ========== db-manage ==========
    db_parser = subparsers.add_parser(
        'db-manage',
        help='런타임 스토리지(.cmis) 마이그레이션/리셋'
    )
    db_parser.add_argument('--project-root', dest='project_root', help='프로젝트 루트 (기본: cwd)')
    db_parser.add_argument('--migrate', action='store_true', help='project_context_id 등 legacy key 마이그레이션')
    db_parser.add_argument('--reset', action='store_true', help='.cmis 런타임 스토어 초기화(db/runs/artifacts/value_store/cache 등)')
    db_parser.add_argument('--reconcile', action='store_true', help='brownfield outbox 처리(예: PRJ publish)')
    db_parser.add_argument('--retry-failed', dest='retry_failed', action='store_true', help='reconcile 시 failed 항목도 재시도')
    db_parser.add_argument('--limit', type=int, default=50, help='reconcile 처리 개수 제한')
    db_parser.add_argument('--import-run-id', dest='import_run_id', help='reconcile 대상 ImportRun(IMP-...) (선택)')
    db_parser.add_argument('--no-backup', dest='no_backup', action='store_true', help='reset 시 백업하지 않음 (위험)')
    db_parser.add_argument('--keep-runs', dest='keep_runs', action='store_true', help='reset 시 .cmis/runs 유지')
    db_parser.add_argument('--skip-reexport', dest='skip_reexport', action='store_true', help='migrate 후 run export 생략')

    # ========== config-validate ==========
    validate_parser = subparsers.add_parser(
        'config-validate',
        help='설정 검증'
    )
    validate_parser.add_argument('--file', help='Config 파일 (기본: cmis.yaml)')
    validate_parser.add_argument('--check-seeds', dest='check_seeds', action='store_true')
    validate_parser.add_argument('--check-patterns', dest='check_patterns', action='store_true')
    validate_parser.add_argument('--check-workflows', dest='check_workflows', action='store_true')
    validate_parser.add_argument('--check-registry', dest='check_registry', action='store_true')
    validate_parser.add_argument('--check-all', dest='check_all', action='store_true')

    # ========== eval-run ==========
    eval_parser = subparsers.add_parser(
        "eval-run",
        help="Run eval harness (regression/canary)"
    )
    eval_parser.add_argument("--suite", default="eval/regression_suite.yaml", help="Regression suite YAML")
    eval_parser.add_argument("--canary", default="eval/canary_domains.yaml", help="Canary domains YAML (optional)")
    eval_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")
    eval_parser.add_argument(
        "--enable-stub-source",
        dest="enable_stub_source",
        action="store_true",
        help="외부 API 없이 stub source만 사용",
    )

    # ========== cursor ==========
    cursor_parser = subparsers.add_parser(
        "cursor",
        help="Cursor Agent Interface commands"
    )
    cursor_subparsers = cursor_parser.add_subparsers(dest="cursor_command")

    cursor_init_parser = cursor_subparsers.add_parser("init", help="Initialize Cursor run folders")
    cursor_init_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    cursor_doctor_parser = cursor_subparsers.add_parser("doctor", help="Validate environment/config for Cursor")
    cursor_doctor_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    cursor_manifest_parser = cursor_subparsers.add_parser("manifest", help="Print CMIS capability manifest (JSON)")
    cursor_manifest_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    cursor_bootstrap_parser = cursor_subparsers.add_parser("bootstrap", help="Onboarding: init + doctor + manifest (+ optional smoke run)")
    cursor_bootstrap_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")
    cursor_bootstrap_parser.add_argument("--no-env", dest="no_env", action="store_true", help=".env 생성/수정을 건너뜀")
    cursor_bootstrap_parser.add_argument("--force-env", dest="force_env", action="store_true", help="기존 .env를 env.example로 덮어씀 (위험)")
    cursor_bootstrap_parser.add_argument("--print-manifest", dest="print_manifest", action="store_true", help="manifest JSON을 stdout에도 출력")
    cursor_bootstrap_parser.add_argument("--smoke-run", dest="smoke_run", action="store_true", help="간단 smoke run 실행")
    cursor_bootstrap_parser.add_argument("--smoke-query", dest="smoke_query", default="CMIS bootstrap smoke run", help="smoke run query")
    cursor_bootstrap_parser.add_argument("--domain", default="Adult_Language_Education_KR", help="smoke run domain")
    cursor_bootstrap_parser.add_argument("--region", default="KR", help="smoke run region")
    cursor_bootstrap_parser.add_argument("--segment", help="smoke run segment")
    cursor_bootstrap_parser.add_argument("--policy", default="exploration_friendly", help="smoke run policy")
    cursor_bootstrap_parser.add_argument("--max-iterations", dest="max_iterations", type=int, default=1)
    cursor_bootstrap_parser.add_argument("--max-time-sec", dest="max_time_sec", type=int, default=30)

    cursor_ask_parser = cursor_subparsers.add_parser("ask", help="Run orchestration kernel and export run artifacts")
    cursor_ask_parser.add_argument("query", help="사용자 질문")
    cursor_ask_parser.add_argument("--domain", required=True, help="도메인 ID")
    cursor_ask_parser.add_argument("--region", required=True, help="지역")
    cursor_ask_parser.add_argument("--segment", help="세그먼트")
    cursor_ask_parser.add_argument("--as-of", dest="as_of", help="기준일(as_of)")
    cursor_ask_parser.add_argument("--focal-actor-context-id", dest="focal_actor_context_id", help="FocalActorContext ID (PRJ-*)")
    cursor_ask_parser.add_argument("--role", help="Role override")
    cursor_ask_parser.add_argument("--policy", help="Policy override")
    cursor_ask_parser.add_argument(
        "--mode",
        default="autopilot",
        choices=["autopilot", "approval_required", "manual"],
        help="Run mode"
    )
    cursor_ask_parser.add_argument("--max-iterations", dest="max_iterations", type=int, default=20)
    cursor_ask_parser.add_argument("--max-time-sec", dest="max_time_sec", type=int, default=300)
    cursor_ask_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    # ========== run ==========
    run_group_parser = subparsers.add_parser("run", help="Run inspection helpers (Cursor-friendly)")
    run_subparsers = run_group_parser.add_subparsers(dest="run_command")

    run_explain_parser = run_subparsers.add_parser("explain", help="Explain decisions for a run")
    run_explain_parser.add_argument("run_id", help="RUN-... ID")
    run_explain_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    run_open_parser = run_subparsers.add_parser("open", help="Export and print run folder path")
    run_open_parser.add_argument("run_id", help="RUN-... ID")
    run_open_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    # ========== context ==========
    context_parser = subparsers.add_parser("context", help="Context helpers (verify, etc)")
    context_subparsers = context_parser.add_subparsers(dest="context_command")

    context_verify_parser = context_subparsers.add_parser("verify", help="Verify PRJ-...-vN against Brownfield contracts")
    context_verify_parser.add_argument("focal_actor_context_id", help="FocalActorContext ID (PRJ-...-vN)")
    context_verify_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    # ========== brownfield ==========
    brownfield_parser = subparsers.add_parser("brownfield", help="Brownfield ingest/curation helpers (MVP)")
    brownfield_subparsers = brownfield_parser.add_subparsers(dest="brownfield_command")

    bf_import_parser = brownfield_subparsers.add_parser("import", help="Import a local file (CSV/XLSX MVP)")
    bf_import_parser.add_argument("file", help="입력 파일 경로(.csv/.xlsx)")
    bf_import_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")
    bf_import_parser.add_argument("--mapping-id", dest="mapping_id", help="Mapping ID (MAP-*)")
    bf_import_parser.add_argument("--mapping-version", dest="mapping_version", type=int, help="Mapping version")
    bf_import_parser.add_argument("--ingest-policy-digest", dest="ingest_policy_digest", help="Ingest policy digest (optional)")
    bf_import_parser.add_argument(
        "--normalization-defaults-digest",
        dest="normalization_defaults_digest",
        help="Normalization defaults digest (optional)",
    )
    bf_import_parser.add_argument(
        "--extractor-version",
        dest="extractor_version",
        help="Extractor version label (기본: 확장자 기반 자동 선택)",
    )

    bf_preview_parser = brownfield_subparsers.add_parser("preview", help="Print preview summary for an ImportRun")
    bf_preview_parser.add_argument("import_run_id", help="ImportRun ID (IMP-...)")
    bf_preview_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    bf_validate_parser = brownfield_subparsers.add_parser(
        "validate",
        help="Validate an ImportRun and attach ValidationReport(ART)",
    )
    bf_validate_parser.add_argument("import_run_id", help="ImportRun ID (IMP-...)")
    bf_validate_parser.add_argument(
        "--policy-mode",
        dest="policy_mode",
        default="reporting_strict",
        choices=["reporting_strict", "decision_balanced", "exploration_friendly"],
        help="Commit gating policy mode",
    )
    bf_validate_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    bf_commit_parser = brownfield_subparsers.add_parser(
        "commit",
        help="Commit a validated ImportRun (creates CUB + PRJ)",
    )
    bf_commit_parser.add_argument("import_run_id", help="ImportRun ID (IMP-...)")
    bf_commit_parser.add_argument(
        "--policy-mode",
        dest="policy_mode",
        default="reporting_strict",
        choices=["reporting_strict", "decision_balanced", "exploration_friendly"],
        help="Commit gating policy mode",
    )
    bf_commit_parser.add_argument(
        "--focal-actor-context-base-id",
        dest="focal_actor_context_base_id",
        help="PRJ base id (e.g., PRJ-mycase)",
    )
    bf_commit_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    bf_reconcile_parser = brownfield_subparsers.add_parser(
        "reconcile",
        help="Process Brownfield outbox (publish PRJ, etc.)",
    )
    bf_reconcile_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")
    bf_reconcile_parser.add_argument("--import-run-id", dest="import_run_id", help="ImportRun ID (IMP-...) (optional)")
    bf_reconcile_parser.add_argument("--retry-failed", dest="retry_failed", action="store_true", help="failed 항목도 재시도")
    bf_reconcile_parser.add_argument("--limit", type=int, default=50, help="처리 개수 제한")

    # ========== llm ==========
    llm_parser = subparsers.add_parser(
        "llm",
        help="LLM model management commands",
    )
    llm_subparsers = llm_parser.add_subparsers(dest="llm_command")

    llm_bench_parser = llm_subparsers.add_parser(
        "benchmark",
        help="LLM benchmark commands",
    )
    llm_bench_subparsers = llm_bench_parser.add_subparsers(dest="bench_command")

    llm_bench_list_parser = llm_bench_subparsers.add_parser(
        "list-suites",
        help="List benchmark suites",
    )
    llm_bench_list_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    llm_bench_run_parser = llm_bench_subparsers.add_parser(
        "run",
        help="Run benchmark suite",
    )
    llm_bench_run_parser.add_argument("--suite", required=True, help="Suite ID")
    llm_bench_run_parser.add_argument("--llm-mode", dest="llm_mode", default="auto", choices=["auto", "mock", "openai"], help="LLM mode")
    llm_bench_run_parser.add_argument("--dry-run", action="store_true", help="실행 없이 계획/저장 경로만 확인")
    llm_bench_run_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

    llm_bench_report_parser = llm_bench_subparsers.add_parser(
        "report",
        help="Show benchmark run summary",
    )
    llm_bench_report_parser.add_argument("--run", dest="run_id", required=True, help="BENCH-... run id")
    llm_bench_report_parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: cwd)")

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
    elif args.command == 'db-manage':
        cmd_db_manage(args)
    elif args.command == 'config-validate':
        cmd_config_validate(args)
    elif args.command == "eval-run":
        cmd_eval_run(args)
    elif args.command == "cursor":
        if args.cursor_command == "init":
            cmd_cursor_init(args)
        elif args.cursor_command == "doctor":
            cmd_cursor_doctor(args)
        elif args.cursor_command == "manifest":
            cmd_cursor_manifest(args)
        elif args.cursor_command == "bootstrap":
            cmd_cursor_bootstrap(args)
        elif args.cursor_command == "ask":
            cmd_cursor_ask(args)
        else:
            cursor_parser.print_help()
    elif args.command == "run":
        if args.run_command == "explain":
            cmd_run_explain(args)
        elif args.run_command == "open":
            cmd_run_open(args)
        else:
            run_group_parser.print_help()
    elif args.command == "context":
        if args.context_command == "verify":
            cmd_context_verify(args)
        else:
            context_parser.print_help()
    elif args.command == "brownfield":
        if args.brownfield_command == "import":
            cmd_brownfield_import(args)
        elif args.brownfield_command == "preview":
            cmd_brownfield_preview(args)
        elif args.brownfield_command == "validate":
            cmd_brownfield_validate(args)
        elif args.brownfield_command == "commit":
            cmd_brownfield_commit(args)
        elif args.brownfield_command == "reconcile":
            cmd_brownfield_reconcile(args)
        else:
            brownfield_parser.print_help()
    elif args.command == "llm":
        if args.llm_command == "benchmark":
            if args.bench_command == "run":
                cmd_llm_benchmark_run(args)
            elif args.bench_command == "report":
                cmd_llm_benchmark_report(args)
            elif args.bench_command == "list-suites":
                cmd_llm_benchmark_list_suites(args)
            else:
                llm_bench_parser.print_help()
        else:
            llm_parser.print_help()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
