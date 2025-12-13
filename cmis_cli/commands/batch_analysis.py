"""batch-analysis 명령어

여러 도메인/시장 일괄 분석 (병렬 처리)

2025-12-11: Workflow CLI Phase 2
"""

from __future__ import annotations

import sys
import yaml
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmis_core.workflow import WorkflowOrchestrator


def run_single_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """단일 Job 실행

    Args:
        job: Job 설정

    Returns:
        Job 결과
    """
    try:
        orchestrator = WorkflowOrchestrator()

        workflow_id = job.get("workflow_id", "structure_analysis")
        inputs = job.get("inputs", {})

        # 실행
        result = orchestrator.run_workflow(
            workflow_id=workflow_id,
            inputs=inputs
        )

        # Completeness 판단
        completeness = "full"
        missing_items = []

        if "error" in result:
            completeness = "failed"
        elif isinstance(result, dict):
            # Metrics 확인
            metrics = result.get("metrics", [])
            if isinstance(metrics, list):
                for m in metrics:
                    metric_id = m.metric_id if hasattr(m, 'metric_id') else m.get("metric_id")
                    value = m.point_estimate if hasattr(m, 'point_estimate') else m.get("point_estimate")

                    if value is None:
                        missing_items.append(metric_id)

                if missing_items:
                    completeness = "partial"

        return {
            "job": job,
            "status": "completed",
            "completeness": completeness,
            "missing_items": missing_items,
            "result": result
        }

    except Exception as e:
        return {
            "job": job,
            "status": "failed",
            "error_code": "ENGINE_ERROR",
            "error_message": str(e)
        }


def cmd_batch_analysis(args):
    """batch-analysis 명령 실행

    Args:
        args: Argparse args
    """
    print("=" * 60)
    print("CMIS - Batch Analysis")
    print("=" * 60)
    print()

    # Config 로딩
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"[ERROR] Config 파일 없음: {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    jobs = config.get("jobs", [])

    if not jobs:
        print("[ERROR] Jobs 없음")
        return

    print(f"총 {len(jobs)}개 작업")
    print()

    # 병렬 실행
    results = []

    if args.parallel:
        # 병렬
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(run_single_job, job): i for i, job in enumerate(jobs)}

            for future in as_completed(futures):
                job_idx = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    # 진행 상황
                    status = result["status"]
                    completeness = result.get("completeness", "unknown")

                    if status == "completed":
                        if completeness == "full":
                            print(f"[{len(results)}/{len(jobs)}] Job {job_idx+1} ✓ (완료)")
                        elif completeness == "partial":
                            print(f"[{len(results)}/{len(jobs)}] Job {job_idx+1} [WARN] (부분 완료)")
                        else:
                            print(f"[{len(results)}/{len(jobs)}] Job {job_idx+1} ✓")
                    else:
                        print(f"[{len(results)}/{len(jobs)}] Job {job_idx+1} [FAIL] (실패)")

                except Exception as e:
                    print(f"[{len(results)+1}/{len(jobs)}] Job {job_idx+1} [FAIL] (예외: {e})")
    else:
        # 순차 실행
        for i, job in enumerate(jobs):
            print(f"[{i+1}/{len(jobs)}] 실행 중...")
            result = run_single_job(job)
            results.append(result)

            if result["status"] == "completed":
                print(f"  ✓ 완료 ({result.get('completeness', 'full')})")
            else:
                print("  [FAIL] 실패")

    print()
    print("=" * 60)
    print("요약")
    print("=" * 60)
    print()

    # 요약
    completed = [r for r in results if r["status"] == "completed"]
    failed = [r for r in results if r["status"] == "failed"]

    full = [r for r in completed if r.get("completeness") == "full"]
    partial = [r for r in completed if r.get("completeness") == "partial"]

    print(f"총 작업: {len(jobs)}개")
    print(f"  ✓ 완료: {len(completed)}개")
    print(f"    - Full: {len(full)}개")
    print(f"    - Partial: {len(partial)}개")
    print(f"  [FAIL] 실패: {len(failed)}개")
    print()

    # 결과 저장
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, result in enumerate(results):
            job = result["job"]
            output_file = job.get("output", f"result_{i+1}.json")
            output_path = output_dir / output_file

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        print(f"[OK] 결과 저장: {output_dir}")


