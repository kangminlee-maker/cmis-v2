from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .graph import InMemoryGraph


# v9 상위 YAML들과의 느슨한 연결 (참조용 메타데이터)
PROCESS_PHASES_REF = "umis_v9_process_phases.yaml#structure_analysis"
AGENT_PROTOCOLS_REF = "umis_v9_agent_protocols.yaml"
VALIDATION_GATES_REF = "umis_v9_validation_gates.yaml#gate_types"


@dataclass
class RealityGraphSnapshot:
  """R-Graph 서브그래프 스냅샷 POC 표현.

  실제 구현에서는 graph_slice_ref 같은 핸들을 사용할 수 있지만,
  POC에서는 그냥 인메모리 그래프 객체를 그대로 들고 있는다.

  이 스냅샷은 canonical_workflows.structure_analysis 에서
  `world_engine.snapshot` 결과로 사용될 R-Graph 조각의 최소 모델이다.
  """

  graph: InMemoryGraph
  meta: Dict[str, Any]


def _load_yaml(path: Path) -> Dict[str, Any]:
  with path.open("r", encoding="utf-8") as f:
    return yaml.safe_load(f)


def load_reality_seed(path: str | Path) -> RealityGraphSnapshot:
  """Reality seed YAML을 읽어 R-Graph POC 스냅샷으로 변환.

  현재는 `seeds/Adult_Language_Education_KR_reality_seed.yaml` 포맷만 가정한다.
  - actors: ACT-* 노드를 reality_graph.actor 타입으로 생성
  - money_flows: MFL-* 노드를 reality_graph.money_flow 타입으로 생성하고
    actor_pays_actor edge를 추가
  - states: STA-* 노드를 reality_graph.state 타입으로 생성
  """

  path = Path(path)
  data = _load_yaml(path)
  root = data.get("umis_v9_reality_seed") or {}

  graph = InMemoryGraph()

  # actors
  for actor in root.get("actors", []):
    actor_id = actor["actor_id"]
    node_data = {k: v for k, v in actor.items() if k != "actor_id"}
    graph.upsert_node(actor_id, "actor", node_data)

  # money_flows + actor_pays_actor edges
  for mf in root.get("money_flows", []):
    mf_id = mf["money_flow_id"]
    payer_id = mf["payer_id"]
    payee_id = mf["payee_id"]
    quantity = mf.get("quantity", {})
    traits = mf.get("traits", {})
    node_data = {
      "quantity": quantity,
      "traits": traits,
    }
    graph.upsert_node(mf_id, "money_flow", node_data)
    graph.add_edge(
      edge_type="actor_pays_actor",
      source=payer_id,
      target=payee_id,
      data={"via": mf_id},
    )

  # states
  for state in root.get("states", []):
    state_id = state["state_id"]
    node_data = {k: v for k, v in state.items() if k != "state_id"}
    graph.upsert_node(state_id, "state", node_data)

  meta = {
    "seed_path": str(path),
    "domain_id": root.get("meta", {}).get("domain_id"),
    "as_of": root.get("meta", {}).get("as_of"),
  }

  return RealityGraphSnapshot(graph=graph, meta=meta)


def snapshot(domain_id: str, region: str | None = None, segment: str | None = None, as_of: str | None = None) -> RealityGraphSnapshot:
  """world_engine.snapshot POC 버전.

  - 실제 구현에서는 EvidenceEngine을 호출해 on-demand로 R-Graph를 채우겠지만,
    여기서는 도메인 전용 seed YAML을 그대로 로딩한다.
  - 현재는 Adult_Language_Education_KR 도메인만 지원한다.

  참고:
  - canonical_workflows.structure_analysis
  - umis_v9_process_phases.yaml#structure_analysis
  """

  # 간단 매핑 (향후 domain_registry 기반으로 일반화 가능)
  if domain_id == "Adult_Language_Education_KR":
    seed_path = Path("seeds/Adult_Language_Education_KR_reality_seed.yaml")
    if not seed_path.exists():
      raise FileNotFoundError(f"Reality seed not found: {seed_path}")
    return load_reality_seed(seed_path)

  raise NotImplementedError(f"snapshot POC: domain_id={domain_id!r} 는 아직 지원하지 않습니다.")
