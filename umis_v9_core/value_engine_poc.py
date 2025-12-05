from __future__ import annotations

"""UMIS v9 POC: 매우 단순한 value_engine 구현.

- InMemoryGraph + umis_v9.yaml의 metrics_spec 일부를 사용해
  Adult_Language_Education_KR 도메인에서 구조 분석에 필요한 몇 가지 Metric을 계산한다.
- 정식 ValueEngine/Metric Resolver의 구조를 모두 구현하지 않고,
  evaluate_metrics(metric_requests, policy_ref) 인터페이스만 POC 수준으로 맞춘다.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .graph import InMemoryGraph


@dataclass
class MetricRequest:
  metric_id: str
  context: Dict[str, Any]


@dataclass
class ValueRecord:
  metric_id: str
  context: Dict[str, Any]
  point_estimate: float | None
  quality: Dict[str, Any]
  lineage: Dict[str, Any]


class ValueEnginePOC:
  """value_engine.evaluate_metrics POC 버전.

  - 현재는 Adult_Language_Education_KR reality seed 기반 구조 분석에 필요한
    일부 Metric만 직접 계산한다.
  - 지원 Metric (도메인 한정, 연간 기준):
    - MET-Revenue: 수요 측 actor(고객 세그먼트) → 공급자 money_flow 합계
    - MET-N_customers: reality seed actor 메타데이터에서 추정한 고객 수
    - MET-Avg_price_per_unit: Revenue / N_customers (단순 연평균 단가)
  - 그 외 Metric은 point_estimate=None 과 함께 "not_implemented" 상태로 반환한다.
  """

  def __init__(self, config_path: str | Path = "umis_v9.yaml") -> None:
    self.config_path = Path(config_path)
    self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
    self.metrics_spec = self._index_metrics_spec(self.config)

  @staticmethod
  def _index_metrics_spec(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    metrics_by_id: Dict[str, Dict[str, Any]] = {}
    try:
      engines = config["umis_v9"]["planes"]["cognition_plane"]["engines"]
      vspec = engines["value_engine"]["metrics_spec"]
      for m in vspec.get("metrics", []):
        mid = m.get("metric_id")
        if mid:
          metrics_by_id[mid] = m
    except KeyError:
      # 스펙이 없으면 빈 dict로 둔다.
      pass
    return metrics_by_id

  def evaluate_metrics(
    self,
    graph: InMemoryGraph,
    metric_requests: List[MetricRequest],
    policy_ref: str = "reporting_strict",
  ) -> Tuple[List[ValueRecord], Dict[str, Any]]:
    """요청된 Metric들을 평가하고 ValueRecord 목록과 value_program_ref를 반환.

    POC에서는 policy_ref를 실제로 사용하지 않고 메타정보로만 남긴다.
    """

    results: List[ValueRecord] = []
    for req in metric_requests:
      metric_id = req.metric_id
      if metric_id == "MET-Revenue":
        value = self._compute_total_revenue(graph, req.context)
        record = self._build_record(metric_id, req.context, value, method="direct_from_seed")
      elif metric_id == "MET-N_customers":
        value = self._compute_n_customers(graph, req.context)
        record = self._build_record(metric_id, req.context, value, method="direct_from_seed")
      elif metric_id == "MET-Avg_price_per_unit":
        value = self._compute_avg_price_per_unit(graph, req.context)
        record = self._build_record(metric_id, req.context, value, method="derived_from_Revenue_and_N_customers")
      else:
        # 아직 구현되지 않은 Metric은 None과 not_implemented 상태로 반환.
        record = self._build_record(metric_id, req.context, None, method="not_implemented", status="not_implemented")

      results.append(record)

    value_program_ref: Dict[str, Any] = {
      "engine": "ValueEnginePOC",
      "policy_ref": policy_ref,
      "created_at": datetime.utcnow().isoformat(),
      "metric_ids": [r.metric_id for r in results],
    }
    return results, value_program_ref

  @staticmethod
  def _compute_total_revenue(graph: InMemoryGraph, context: Dict[str, Any]) -> float:
    """수요 측 actor(고객 세그먼트)에서 공급자에게 지불하는 money_flow 합계를 Revenue로 사용.

    - actor.kind == "customer_segment" 인 actor가 payer인 actor_pays_actor edge를 찾고,
      연결된 money_flow 노드의 quantity.amount를 모두 합산한다.
    """

    customer_actor_ids = {
      n.id
      for n in graph.nodes_by_type("actor")
      if n.data.get("kind") == "customer_segment"
    }

    total = 0.0
    for edge in graph.edges:
      if edge.type != "actor_pays_actor":
        continue
      if edge.source not in customer_actor_ids:
        continue
      mf_id = edge.data.get("via")
      if not mf_id:
        continue
      mf_node = graph.get_node(mf_id)
      if mf_node is None:
        continue
      quantity = mf_node.data.get("quantity") or {}
      amount = quantity.get("amount")
      if isinstance(amount, (int, float)):
        total += float(amount)

    return total

  @staticmethod
  def _compute_n_customers(graph: InMemoryGraph, context: Dict[str, Any]) -> float:
    """reality seed actor 메타데이터 기반 N_customers 추정.

    - 성인 개인 학습자: metadata.approx_population
    - 기업 고객: metadata.approx_company_count
    두 값을 합산해 "고객 단위"로 본다.
    """

    total_customers = 0.0
    for actor in graph.nodes_by_type("actor"):
      metadata = actor.data.get("metadata") or {}
      pop = metadata.get("approx_population")
      if isinstance(pop, (int, float)):
        total_customers += float(pop)
      company_cnt = metadata.get("approx_company_count")
      if isinstance(company_cnt, (int, float)):
        total_customers += float(company_cnt)

    return total_customers

  def _compute_avg_price_per_unit(self, graph: InMemoryGraph, context: Dict[str, Any]) -> float | None:
    """단순히 Revenue / N_customers로 연평균 단가를 계산.

    - N_customers가 0이거나 정의되지 않으면 None 반환.
    """

    revenue = self._compute_total_revenue(graph, context)
    n_customers = self._compute_n_customers(graph, context)
    if n_customers <= 0:
      return None
    return revenue / n_customers

  @staticmethod
  def _build_record(
    metric_id: str,
    context: Dict[str, Any],
    value: float | None,
    *,
    method: str,
    status: str = "ok",
  ) -> ValueRecord:
    """ValueRecord 헬퍼 생성 함수.

    - quality: literal_ratio/spread_ratio는 POC에서는 고정 값으로 두고,
      method/status를 메타데이터로 남긴다.
    """

    quality = {
      "status": status,
      "method": method,
      "literal_ratio": 1.0 if value is not None else 0.0,
      "spread_ratio": 0.0,
    }
    lineage = {
      "from_evidence_ids": [],
      "from_value_ids": [],
      "from_pattern_ids": [],
      "from_program_id": "ValueEnginePOC",
      "engine_ids": ["value_engine"],
      "policy_id": None,
      "created_by_role": None,
      "created_at": datetime.utcnow().isoformat(),
    }
    return ValueRecord(
      metric_id=metric_id,
      context=context,
      point_estimate=value,
      quality=quality,
      lineage=lineage,
    )
