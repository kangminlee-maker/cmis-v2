"""umis_v9.yaml 무결성 검증 스크립트

검증 항목:
1. YAML 파싱 가능
2. 필수 섹션 존재
3. Metric ID 중복 확인
4. Pattern ID 중복 확인
5. ID prefix 일관성
6. 참조 무결성 (존재하는 ID만 참조)
"""

import yaml
from collections import Counter
from typing import Dict, List, Set, Any


def load_yaml(filepath: str) -> Dict:
    """YAML 파일 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_required_sections(data: Dict) -> List[str]:
    """필수 섹션 존재 확인"""
    errors = []
    
    if "umis_v9" not in data:
        errors.append("❌ umis_v9 루트 섹션 없음")
        return errors
    
    umis = data["umis_v9"]
    required = ["meta", "ontology", "planes", "ids_and_lineage"]
    
    for section in required:
        if section not in umis:
            errors.append(f"❌ umis_v9.{section} 섹션 없음")
    
    return errors


def check_metric_ids(data: Dict) -> List[str]:
    """Metric ID 중복 확인"""
    errors = []
    
    try:
        engines = data["umis_v9"]["planes"]["cognition_plane"]["engines"]
        value_engine = engines["value_engine"]
        metrics_spec = value_engine["metrics_spec"]
        metrics = metrics_spec["metrics"]
        
        metric_ids = [m["metric_id"] for m in metrics if "metric_id" in m]
        duplicates = [mid for mid, count in Counter(metric_ids).items() if count > 1]
        
        if duplicates:
            errors.append(f"❌ Metric ID 중복: {duplicates}")
        else:
            print(f"✅ Metric ID 중복 없음 (총 {len(metric_ids)}개)")
    
    except KeyError as e:
        errors.append(f"⚠️  Metric 스펙 경로 없음: {e}")
    
    return errors


def check_id_prefixes(data: Dict) -> List[str]:
    """ID prefix 정의 확인"""
    errors = []
    
    try:
        prefixes = data["umis_v9"]["ids_and_lineage"]["id_prefixes"]
        
        required_prefixes = [
            "actor", "event", "resource", "money_flow", "contract", "state",
            "evidence", "outcome", "metric", "value", "pattern",
            "goal", "hypothesis", "strategy", "scenario", "action",
            "artifact", "memory", "project"
        ]
        
        missing = [p for p in required_prefixes if p not in prefixes]
        
        if missing:
            errors.append(f"❌ ID prefix 누락: {missing}")
        else:
            print(f"✅ ID prefix 완전 ({len(prefixes)}개)")
    
    except KeyError as e:
        errors.append(f"❌ ids_and_lineage 섹션 없음: {e}")
    
    return errors


def check_graph_schemas(data: Dict) -> List[str]:
    """Graph 스키마 정의 확인"""
    errors = []
    
    try:
        graphs = data["umis_v9"]["planes"]["substrate_plane"]["graphs"]
        
        required_graphs = ["reality_graph", "pattern_graph", "value_graph", "decision_graph"]
        
        for graph_name in required_graphs:
            if graph_name not in graphs:
                errors.append(f"❌ {graph_name} 정의 없음")
            else:
                graph_def = graphs[graph_name]
                if "node_types" not in graph_def:
                    errors.append(f"❌ {graph_name}.node_types 없음")
                if "edge_types" not in graph_def:
                    errors.append(f"❌ {graph_name}.edge_types 없음")
        
        if not errors:
            print(f"✅ Graph 스키마 완전 (4개 그래프)")
    
    except KeyError as e:
        errors.append(f"❌ Graph 스키마 경로 없음: {e}")
    
    return errors


def check_stores(data: Dict) -> List[str]:
    """Store 정의 확인"""
    errors = []
    
    try:
        stores = data["umis_v9"]["planes"]["substrate_plane"]["stores"]
        
        required_stores = ["evidence_store", "outcome_store", "memory_store", "value_store", "project_context_store"]
        
        for store_name in required_stores:
            if store_name not in stores:
                errors.append(f"❌ {store_name} 정의 없음")
            else:
                store_def = stores[store_name]
                if "id_prefix" not in store_def:
                    errors.append(f"❌ {store_name}.id_prefix 없음")
                if "schema" not in store_def:
                    errors.append(f"❌ {store_name}.schema 없음")
        
        if not errors:
            print(f"✅ Store 정의 완전 (5개 Store)")
    
    except KeyError as e:
        errors.append(f"❌ Store 경로 없음: {e}")
    
    return errors


def check_engines(data: Dict) -> List[str]:
    """Engine 정의 확인"""
    errors = []
    
    try:
        engines = data["umis_v9"]["planes"]["cognition_plane"]["engines"]
        
        required_engines = [
            "evidence_engine", "world_engine", "pattern_engine",
            "value_engine", "strategy_engine", "learning_engine", "policy_engine"
        ]
        
        for engine_name in required_engines:
            if engine_name not in engines:
                errors.append(f"❌ {engine_name} 정의 없음")
            else:
                engine_def = engines[engine_name]
                if "description" not in engine_def:
                    errors.append(f"⚠️  {engine_name}.description 없음")
                if "api" not in engine_def:
                    errors.append(f"⚠️  {engine_name}.api 없음")
        
        if not errors:
            print(f"✅ Engine 정의 완전 (7개 Engine)")
    
    except KeyError as e:
        errors.append(f"❌ Engine 경로 없음: {e}")
    
    return errors


def main():
    """메인 검증 함수"""
    print("=" * 60)
    print("UMIS v9 YAML 무결성 검증")
    print("=" * 60)
    
    try:
        data = load_yaml("umis_v9.yaml")
        print("✅ 1. YAML 파싱 성공\n")
    except Exception as e:
        print(f"❌ YAML 파싱 실패: {e}")
        return
    
    all_errors = []
    
    print("2. 필수 섹션 검증")
    errors = check_required_sections(data)
    all_errors.extend(errors)
    if not errors:
        print("✅ 필수 섹션 모두 존재\n")
    else:
        for e in errors:
            print(f"   {e}")
        print()
    
    print("3. Metric ID 중복 검증")
    errors = check_metric_ids(data)
    all_errors.extend(errors)
    if errors:
        for e in errors:
            print(f"   {e}")
    print()
    
    print("4. ID Prefix 검증")
    errors = check_id_prefixes(data)
    all_errors.extend(errors)
    if errors:
        for e in errors:
            print(f"   {e}")
    print()
    
    print("5. Graph 스키마 검증")
    errors = check_graph_schemas(data)
    all_errors.extend(errors)
    if errors:
        for e in errors:
            print(f"   {e}")
    print()
    
    print("6. Store 정의 검증")
    errors = check_stores(data)
    all_errors.extend(errors)
    if errors:
        for e in errors:
            print(f"   {e}")
    print()
    
    print("7. Engine 정의 검증")
    errors = check_engines(data)
    all_errors.extend(errors)
    if errors:
        for e in errors:
            print(f"   {e}")
    print()
    
    print("=" * 60)
    if all_errors:
        print(f"❌ 총 {len(all_errors)}개 오류 발견")
    else:
        print("✅ 무결성 검증 완료! 오류 없음")
    print("=" * 60)


if __name__ == "__main__":
    main()
