"""compare-contexts 명령어

여러 분석 컨텍스트 비교 (Greenfield vs Brownfield, 시점 비교 등)

2025-12-11: Workflow CLI Phase 1
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmis_core.workflow import WorkflowOrchestrator


def parse_context_string(context_str: str) -> dict:
    """Context 문자열 파싱
    
    Args:
        context_str: "domain:Adult_Language,region:KR,segment:office_worker"
    
    Returns:
        {"domain_id": "Adult_Language", "region": "KR", "segment": "office_worker"}
    """
    context = {}
    
    for part in context_str.split(","):
        if ":" in part:
            key, value = part.split(":", 1)
            key = key.strip()
            value = value.strip()
            
            # domain → domain_id 변환
            if key == "domain":
                context["domain_id"] = value
            elif key == "project_context":
                context["project_context_id"] = value
            else:
                context[key] = value
    
    return context


def cmd_compare_contexts(args):
    """compare-contexts 명령 실행
    
    Args:
        args: Argparse args
    """
    print("=" * 60)
    print("CMIS - Compare Contexts")
    print("=" * 60)
    print()
    
    # Context 파싱
    context1 = parse_context_string(args.context1)
    context2 = parse_context_string(args.context2)
    
    print(f"Context 1: {context1}")
    print(f"Context 2: {context2}")
    print()
    
    # Orchestrator
    orchestrator = WorkflowOrchestrator()
    
    # Context 1 실행
    print("[1/2] Analyzing Context 1...")
    result1 = orchestrator.run_workflow(
        workflow_id="structure_analysis",
        inputs=context1
    )
    
    print(f"   ✓ {len(result1.get('pattern_matches', []))} patterns")
    
    # Context 2 실행
    print("[2/2] Analyzing Context 2...")
    result2 = orchestrator.run_workflow(
        workflow_id="structure_analysis",
        inputs=context2
    )
    
    print(f"   ✓ {len(result2.get('pattern_matches', []))} patterns")
    print()
    
    # 비교
    print("=" * 60)
    print("비교 결과")
    print("=" * 60)
    print()
    
    # Graph 비교
    print("[R-Graph 구조]")
    print(f"{'':20s} {'Context 1':>15s} {'Context 2':>15s} {'Delta':>15s}")
    print("-" * 70)
    
    def get_graph_stat(result, key):
        return result.get("graph_overview", {}).get(key, 0)
    
    actors1 = get_graph_stat(result1, "num_actors")
    actors2 = get_graph_stat(result2, "num_actors")
    print(f"{'Actors':20s} {actors1:>15d} {actors2:>15d} {actors2-actors1:>+15d}")
    
    mf1 = get_graph_stat(result1, "num_money_flows")
    mf2 = get_graph_stat(result2, "num_money_flows")
    print(f"{'Money Flows':20s} {mf1:>15d} {mf2:>15d} {mf2-mf1:>+15d}")
    
    print()
    
    # Pattern 비교
    print("[패턴 비교]")
    
    # result가 dict인 경우와 객체인 경우 모두 처리
    pm_list1 = result1.get("pattern_matches", []) if isinstance(result1, dict) else result1.pattern_matches
    pm_list2 = result2.get("pattern_matches", []) if isinstance(result2, dict) else result2.pattern_matches
    
    patterns1 = {
        pm.get("pattern_id") if isinstance(pm, dict) else pm.pattern_id
        for pm in pm_list1
    }
    patterns2 = {
        pm.get("pattern_id") if isinstance(pm, dict) else pm.pattern_id
        for pm in pm_list2
    }
    
    common = patterns1 & patterns2
    only1 = patterns1 - patterns2
    only2 = patterns2 - patterns1
    
    print(f"공통 패턴: {len(common)}개")
    for pid in list(common)[:3]:
        print(f"  ✓ {pid}")
    
    if only1:
        print(f"\nContext 1만: {len(only1)}개")
        for pid in list(only1)[:3]:
            print(f"  • {pid}")
    
    if only2:
        print(f"\nContext 2만: {len(only2)}개")
        for pid in list(only2)[:3]:
            print(f"  • {pid}")
    
    print()
    
    # Metrics 비교
    print("[Metrics 비교]")
    print(f"{'Metric':25s} {'Context 1':>15s} {'Context 2':>15s} {'변화':>15s}")
    print("-" * 75)
    
    # Metric 추출
    def get_metric_value(result, metric_id):
        metrics = result.get("metrics", []) if isinstance(result, dict) else result.metrics
        
        for vr in metrics:
            vr_metric_id = vr.get("metric_id") if isinstance(vr, dict) else vr.metric_id
            if vr_metric_id == metric_id:
                return vr.get("point_estimate") if isinstance(vr, dict) else vr.point_estimate
        return None
    
    for metric_id in ["MET-N_customers", "MET-Revenue"]:
        val1 = get_metric_value(result1, metric_id)
        val2 = get_metric_value(result2, metric_id)
        
        if val1 is not None and val2 is not None:
            change_pct = ((val2 - val1) / val1 * 100) if val1 > 0 else 0
            print(f"{metric_id:25s} {val1:>15,.0f} {val2:>15,.0f} {change_pct:>+14.1f}%")
        else:
            print(f"{metric_id:25s} {'N/A':>15s} {'N/A':>15s} {'N/A':>15s}")
    
    print()
    
    # JSON 저장
    if args.output:
        comparison = {
            "context1": {
                "inputs": context1,
                "results": result1
            },
            "context2": {
                "inputs": context2,
                "results": result2
            },
            "comparison": {
                "graph": {
                    "actors": {"context1": actors1, "context2": actors2, "delta": actors2 - actors1},
                    "money_flows": {"context1": mf1, "context2": mf2, "delta": mf2 - mf1}
                },
                "patterns": {
                    "common": list(common),
                    "only_context1": list(only1),
                    "only_context2": list(only2)
                }
            }
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 비교 결과 저장: {args.output}")

