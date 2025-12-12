"""Generic workflow run 명령어

canonical_workflows 직접 실행

2025-12-11: Workflow CLI Phase 1
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmis_core.workflow import WorkflowOrchestrator


def cmd_workflow_run(args):
    """workflow run 명령 실행
    
    Args:
        args: Argparse args
    """
    print("=" * 60)
    print(f"CMIS - Workflow Run: {args.workflow_id}")
    print("=" * 60)
    print()
    
    # inputs 파싱
    inputs = {}
    if args.input:
        for input_str in args.input:
            if "=" in input_str:
                key, value = input_str.split("=", 1)
                inputs[key] = value
    
    # role/policy
    role_id = args.role if hasattr(args, 'role') else None
    policy_mode = args.policy if hasattr(args, 'policy') else None
    
    # --dry-run
    if args.dry_run:
        print("[DRY RUN MODE]")
        print(f"Workflow ID: {args.workflow_id}")
        print(f"Inputs: {inputs}")
        print(f"Role: {role_id or '(default)'}")
        print(f"Policy: {policy_mode or '(default)'}")
        print()
        print("실행 계획:")
        print("  1. Load canonical_workflows YAML")
        print("  2. Resolve role → policy")
        print("  3. Execute workflow steps")
        print("  4. Format output")
        print()
        return
    
    # 실행
    orchestrator = WorkflowOrchestrator()
    
    result = orchestrator.run_workflow(
        workflow_id=args.workflow_id,
        inputs=inputs,
        role_id=role_id,
        policy_mode=policy_mode
    )
    
    # 출력
    print()
    print("=" * 60)
    print("결과")
    print("=" * 60)
    print()
    
    if "error" in result:
        print(f"❌ 오류: {result['error']}")
        if "available" in result:
            print(f"사용 가능: {result['available']}")
        return
    
    # JSON 출력
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 파일 저장
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 결과 저장: {args.output}")

