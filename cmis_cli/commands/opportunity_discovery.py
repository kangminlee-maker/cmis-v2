"""opportunity-discovery 명령어

기회 발굴 및 Gap 분석

2025-12-11: Workflow CLI Phase 1
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmis_core.workflow import WorkflowOrchestrator


def cmd_opportunity_discovery(args):
    """opportunity-discovery 명령 실행
    
    Args:
        args: Argparse args
    """
    # --dry-run
    if args.dry_run:
        print("[DRY RUN MODE]")
        print(f"Workflow: opportunity_discovery")
        print(f"Domain: {args.domain}")
        print(f"Region: {args.region}")
        print(f"Top N: {args.top_n}")
        print(f"Role: {args.role or 'opportunity_designer (default)'}")
        print(f"Policy: {args.policy or 'exploration_friendly (default)'}")
        print()
        return
    
    print("=" * 60)
    print("CMIS - Opportunity Discovery")
    print("=" * 60)
    print()
    
    orchestrator = WorkflowOrchestrator()
    
    result = orchestrator.run_opportunity_discovery(
        domain_id=args.domain,
        region=args.region,
        segment=args.segment,
        project_context_id=args.project_context,
        top_n=args.top_n,
        min_feasibility=args.min_feasibility
    )
    
    print()
    print("=" * 60)
    print("결과")
    print("=" * 60)
    print()
    
    # Meta
    print(f"도메인: {result['meta']['domain_id']}")
    print(f"지역:   {result['meta']['region']}")
    print()
    
    # Matched Patterns
    print(f"[매칭된 패턴] ({len(result['matched_patterns'])}개)")
    for pm in result['matched_patterns'][:5]:  # 상위 5개
        print(f"  ✓ {pm.pattern_id} (적합도: {pm.combined_score:.2f})")
    print()
    
    # Gaps
    print(f"[발견된 기회] ({result['total_gaps']}개 중 상위 {result['top_n']}개)")
    for i, gap_info in enumerate(result['gaps'], 1):
        gap = gap_info['gap']
        pattern = gap_info['pattern']
        
        print(f"{i}. {gap.pattern_id}")
        if pattern:
            print(f"   {pattern.description}")
        print(f"   Expected Level: {gap.expected_level}")
        print(f"   Feasibility: {gap.feasibility}")
        if gap.execution_fit_score is not None:
            print(f"   Execution Fit: {gap.execution_fit_score:.2f}")
        
        # Benchmarks
        if gap_info['benchmarks']:
            print(f"   Benchmarks: {', '.join(gap_info['benchmarks'].keys())}")
        print()
    
    # 실행 시간
    print(f"실행 시간: {result['meta']['execution_time']:.2f}초")
    print()
    
    # JSON 저장
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            # Gap 객체를 dict로 변환
            output_result = {
                "meta": result["meta"],
                "matched_patterns": [
                    {
                        "pattern_id": pm.pattern_id,
                        "description": pm.description,
                        "combined_score": pm.combined_score
                    }
                    for pm in result["matched_patterns"]
                ],
                "gaps": [
                    {
                        "pattern_id": g["gap"].pattern_id,
                        "description": g["gap"].description,
                        "expected_level": g["gap"].expected_level,
                        "feasibility": g["gap"].feasibility,
                        "execution_fit_score": g["gap"].execution_fit_score,
                        "benchmarks": g["benchmarks"]
                    }
                    for g in result["gaps"]
                ],
                "total_gaps": result["total_gaps"],
                "completeness": result["completeness"]
            }
            
            json.dump(output_result, f, ensure_ascii=False, indent=2)
        print(f"✅ 결과 저장: {output_path}")

