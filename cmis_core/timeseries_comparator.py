"""Timeseries Comparator - 시계열 비교

여러 as_of 시점의 R-Graph 비교 및 변화 추적

2025-12-11: World Engine Phase C
"""

from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime

from .types import RealityGraphSnapshot
from .graph import InMemoryGraph


class TimeseriesComparator:
    """시계열 비교 도구

    여러 시점의 snapshot 비교
    """

    def __init__(self):
        """초기화"""
        pass

    def compare_snapshots(
        self,
        snapshots: List[RealityGraphSnapshot],
        metric_key: str = "revenue"
    ) -> Dict[str, Any]:
        """여러 snapshot 비교

        Args:
            snapshots: 시점별 snapshot 리스트
            metric_key: 비교할 metric (properties의 key)

        Returns:
            비교 결과
        """
        if len(snapshots) < 2:
            return {"error": "At least 2 snapshots required"}

        # 시점별 정렬
        sorted_snapshots = sorted(
            snapshots,
            key=lambda s: s.meta.get("as_of", "1900-01-01")
        )

        results = []

        for snapshot in sorted_snapshots:
            as_of = snapshot.meta.get("as_of", "unknown")

            # State에서 metric 추출
            metric_values = []

            for state in snapshot.graph.nodes_by_type("state"):
                properties = state.data.get("properties", {})
                if metric_key in properties:
                    metric_values.append(properties[metric_key])

            # 평균/합계
            if metric_values:
                total = sum(metric_values)
                avg = total / len(metric_values)
            else:
                total = 0
                avg = 0

            results.append({
                "as_of": as_of,
                "count": len(metric_values),
                "total": total,
                "average": avg
            })

        # 변화율 계산
        for i in range(1, len(results)):
            prev_total = results[i-1]["total"]
            curr_total = results[i]["total"]

            if prev_total > 0:
                growth = (curr_total - prev_total) / prev_total
                results[i]["growth_rate"] = growth
            else:
                results[i]["growth_rate"] = None

        return {
            "snapshots": results,
            "metric_key": metric_key,
            "num_periods": len(results)
        }

    def detect_structural_changes(
        self,
        snapshot1: RealityGraphSnapshot,
        snapshot2: RealityGraphSnapshot
    ) -> Dict[str, Any]:
        """구조적 변화 탐지

        Args:
            snapshot1: 이전 시점
            snapshot2: 이후 시점

        Returns:
            변화 정보
        """
        graph1 = snapshot1.graph
        graph2 = snapshot2.graph

        # Actor 변화
        actors1 = {a.id for a in graph1.nodes_by_type("actor")}
        actors2 = {a.id for a in graph2.nodes_by_type("actor")}

        new_actors = actors2 - actors1
        removed_actors = actors1 - actors2

        # MoneyFlow 변화
        mf1 = {mf.id for mf in graph1.nodes_by_type("money_flow")}
        mf2 = {mf.id for mf in graph2.nodes_by_type("money_flow")}

        new_mf = mf2 - mf1
        removed_mf = mf1 - mf2

        return {
            "as_of": {
                "from": snapshot1.meta.get("as_of"),
                "to": snapshot2.meta.get("as_of")
            },
            "actors": {
                "total_before": len(actors1),
                "total_after": len(actors2),
                "new": len(new_actors),
                "removed": len(removed_actors),
                "new_ids": list(new_actors)[:5]  # 최대 5개
            },
            "money_flows": {
                "total_before": len(mf1),
                "total_after": len(mf2),
                "new": len(new_mf),
                "removed": len(removed_mf)
            }
        }


def compare_timeseries(
    world_engine,
    domain_id: str,
    region: str,
    as_of_list: List[str],
    metric_key: str = "revenue"
) -> Dict[str, Any]:
    """시계열 비교 편의 함수

    Args:
        world_engine: WorldEngine
        domain_id: 도메인 ID
        region: 지역
        as_of_list: 시점 리스트 (예: ["2022", "2023", "2024"])
        metric_key: 비교할 metric

    Returns:
        비교 결과
    """
    snapshots = []

    for as_of in as_of_list:
        snapshot = world_engine.snapshot(
            domain_id=domain_id,
            region=region,
            as_of=as_of
        )
        snapshots.append(snapshot)

    comparator = TimeseriesComparator()
    return comparator.compare_snapshots(snapshots, metric_key)
