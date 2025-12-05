from __future__ import annotations

"""UMIS v9 POC: 매우 단순한 pattern_engine 구현.

- reality_graph (InMemoryGraph)만 사용해서 Adult_Language_Education_KR 도메인에서
  몇 가지 대표 패턴과 갭 후보를 찾아본다.
- 실제 pattern_graph/Pattern 노드 스키마 전체를 구현하지 않고,
  POC에서 structure_analysis에 바로 쓸 수 있는 최소 기능만 제공한다.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from .graph import InMemoryGraph


@dataclass
class PatternMatch:
  pattern_id: str
  description: str
  score: float
  evidence: Dict[str, Any]


@dataclass
class GapCandidate:
  description: str
  related_pattern_ids: List[str]
  evidence: Dict[str, Any]


class PatternEnginePOC:
  """pattern_engine.match_patterns / discover_gaps POC 버전.

  - Adult_Language_Education_KR reality seed에 특화된 매우 단순한 휴리스틱만 사용한다.
  - 정식 엔진에서는 pattern_graph / value_chain_templates / pattern_benchmarks와
    연동되어야 한다.
  """

  def match_patterns(self, graph: InMemoryGraph) -> List[PatternMatch]:
    """R-Graph에서 몇 가지 대표 패턴을 휴리스틱하게 매칭.

    현재는 다음 두 가지만 감지한다.
    - PAT-subscription_model: revenue_model == "subscription" money_flow가 존재할 때
    - PAT-platform_business_model: institution_type == "online_platform" actor가 존재할 때
    """

    matches: List[PatternMatch] = []

    has_subscription = False
    for node in graph.nodes_by_type("money_flow"):
      traits = node.data.get("traits") or {}
      if traits.get("revenue_model") == "subscription":
        has_subscription = True
        break

    if has_subscription:
      matches.append(
        PatternMatch(
          pattern_id="PAT-subscription_model",
          description="수강료/이용료가 반복 결제 구조를 가지는 구독형 BM 패턴.",
          score=1.0,
          evidence={"source": "money_flow.traits.revenue_model == 'subscription'"},
        )
      )

    has_platform = False
    for actor in graph.nodes_by_type("actor"):
      traits = actor.data.get("traits") or {}
      if traits.get("institution_type") == "online_platform":
        has_platform = True
        break

    if has_platform:
      matches.append(
        PatternMatch(
          pattern_id="PAT-platform_business_model",
          description="공급자-플랫폼-수요자 구조를 가지는 플랫폼 BM 패턴.",
          score=1.0,
          evidence={"source": "actor.traits.institution_type == 'online_platform'"},
        )
      )

    return matches

  def discover_gaps(self, graph: InMemoryGraph) -> List[GapCandidate]:
    """R-Graph의 state 노드에서 entry_strategy_clues를 읽어 간단한 갭 후보 생성.

    - seeds/Adult_Language_Education_KR_reality_seed.yaml의 states.properties.entry_strategy_clues를
      그대로 GapCandidate로 노출한다.
    - 실제 구현에서는 pattern_graph 및 decision_graph와 연결되어야 한다.
    """

    gaps: List[GapCandidate] = []

    for state in graph.nodes_by_type("state"):
      props = state.data.get("properties") or {}
      clues: List[str] = props.get("entry_strategy_clues") or []
      if not clues:
        continue

      for clue in clues:
        gaps.append(
          GapCandidate(
            description=clue,
            related_pattern_ids=["PAT-subscription_model", "PAT-platform_business_model"],
            evidence={
              "state_id": state.id,
              "field": "properties.entry_strategy_clues",
            },
          )
        )

    return gaps

