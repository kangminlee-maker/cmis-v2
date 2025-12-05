from __future__ import annotations

"""UMIS v9 POC: Adult Language KR 도메인 structure_analysis 데모.

이 스크립트는 아직 ValueEngine/Metric Resolver를 구현하지 않고,
Reality seed를 world_engine_poc로 로딩해 R-Graph 구조를 간단히 출력해본다.

참고:
- canonical_workflows.structure_analysis
- umis_v9_process_phases.yaml#structure_analysis
- umis_v9_agent_protocols.yaml
- umis_v9_validation_gates.yaml

나중에 Notebook이나 CLI에서 canonical_workflows.structure_analysis를
실제로 호출하는 예시로 확장할 수 있다.
"""

from pathlib import Path

from umis_v9_core.world_engine_poc import snapshot, PROCESS_PHASES_REF, AGENT_PROTOCOLS_REF, VALIDATION_GATES_REF


def main() -> None:
  domain_id = "Adult_Language_Education_KR"
  region = "KR"
  segment = "adult_language_general"

  print("=== UMIS v9 structure_analysis POC ===")
  print(f"- process_phases_ref     : {PROCESS_PHASES_REF}")
  print(f"- agent_protocols_ref    : {AGENT_PROTOCOLS_REF}")
  print(f"- validation_gates_ref   : {VALIDATION_GATES_REF}")

  snap = snapshot(domain_id=domain_id, region=region, segment=segment)

  print("\n=== Reality Snapshot Meta ===")
  print(snap.meta)

  graph = snap.graph

  print("\n=== Actors ===")
  for node in graph.nodes_by_type("actor"):
    print(f"- {node.id}: {node.data.get('name')} | kind={node.data.get('kind')} | traits={node.data.get('traits')}")

  print("\n=== Money Flows (actor_pays_actor edges) ===")
  for edge in graph.edges:
    if edge.type != "actor_pays_actor":
      continue
    print(f"- {edge.source} -> {edge.target} via {edge.data.get('via')}")

  print("\n=== States ===")
  for node in graph.nodes_by_type("state"):
    print(f"- {node.id}: {node.data.get('properties', {}).get('market_structure_notes')}")


if __name__ == "__main__":
  main()
