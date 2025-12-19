"""CMIS World Engine

Evidence → R-Graph 변환 및 snapshot 생성

Phase A: RealityGraphStore + ProjectOverlay + 필터링
2025-12-11: World Engine v2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from .graph import InMemoryGraph
from .types import RealityGraphSnapshot, FocalActorContext, EvidenceRecord
from typing import List
from .context_binding import FocalActorContextBinding
from .reality_graph_store import (
    RealityGraphStore,
    apply_as_of_filter,
    apply_segment_filter
)
from .project_overlay_store import (
    ProjectOverlayStore,
    ingest_focal_actor_context as ingest_focal_ctx,
    merge_graphs,
    extract_subgraph
)


# v9 스펙 참조
PROCESS_PHASES_REF = "umis_v9_process_phases.yaml#structure_analysis"
AGENT_PROTOCOLS_REF = "umis_v9_agent_protocols.yaml"
VALIDATION_GATES_REF = "umis_v9_validation_gates.yaml#gate_types"


class WorldEngine:
    """World Engine v2 - Phase A/B/C

    기능:
    - RealityGraphStore (Global Reality)
    - ProjectOverlayStore (Per-Project)
    - as_of/segment 필터링
    - ingest_focal_actor_context
    - 서브그래프 추출
    - ingest_evidence
    - snapshot() API (통합)

    Phase A: Brownfield + 필터링
    Phase B: ingest_evidence (동적 확장)
    Phase C: 성능 최적화 (백엔드, 캐싱, 인덱싱)
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        use_backend: bool = False,
        use_cache: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Args:
            project_root: 프로젝트 루트 경로 (None이면 자동 탐색)
            use_backend: 파일 시스템 백엔드 사용 (Phase C)
            use_cache: snapshot 캐싱 사용 (Phase C)
            cache_ttl: 캐시 유효 시간 (초, 기본 1시간)
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = Path(project_root)
        # seeds 폴더 위치 (dev/examples/seeds)
        self.seeds_dir = self.project_root / "dev" / "examples" / "seeds"
        # Fallback: 루트 seeds (하위 호환)
        if not self.seeds_dir.exists():
            self.seeds_dir = self.project_root / "seeds"

        # domain_registry 로드
        self.domain_registry = self._load_domain_registry()

        # RealityGraphStore (Global)
        self.reality_store = RealityGraphStore(
            use_backend=use_backend
        )

        # ProjectOverlayStore (Per-Project)
        self.overlay_store = ProjectOverlayStore()

        # Cache (Phase C)
        self.use_cache = use_cache
        self.cache: Optional[GraphCache] = None

        if use_cache:
            from .reality_graph_backend import GraphCache
            self.cache = GraphCache(ttl_seconds=cache_ttl)

    def _load_domain_registry(self) -> Dict[str, Any]:
        """domain_registry.yaml 로드"""
        registry_path = self.project_root / "config" / "domain_registry.yaml"

        if not registry_path.exists():
            return {"domains": []}

        with open(registry_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return data.get("umis_v9_domain_registry", {})

    def _get_seed_path(self, domain_id: str) -> Path:
        """domain_id에 해당하는 seed 파일 경로 찾기"""

        # domain_registry에서 확인
        for domain in self.domain_registry.get("domains", []):
            if domain.get("domain_id") == domain_id:
                # seed 파일 경로 (규칙: seeds/{domain_id}_reality_seed.yaml)
                return self.seeds_dir / f"{domain_id}_reality_seed.yaml"

        # 기본 경로
        return self.seeds_dir / f"{domain_id}_reality_seed.yaml"

    def load_reality_seed(self, path: Path) -> RealityGraphSnapshot:
        """Reality seed YAML → R-Graph 변환

        Args:
            path: seed YAML 파일 경로

        Returns:
            RealityGraphSnapshot

        Raises:
            FileNotFoundError: seed 파일이 없을 때
        """
        if not path.exists():
            raise FileNotFoundError(f"Reality seed not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        root = data.get("cmis_reality_seed", {})
        graph = InMemoryGraph()

        # Actors
        for actor in root.get("actors", []):
            actor_id = actor["actor_id"]
            node_data = {k: v for k, v in actor.items() if k != "actor_id"}
            graph.upsert_node(actor_id, "actor", node_data)

        # Money Flows + Edges
        for mf in root.get("money_flows", []):
            mf_id = mf["money_flow_id"]
            payer_id = mf["payer_id"]
            payee_id = mf["payee_id"]
            quantity = mf.get("quantity", {})
            traits = mf.get("traits", {})
            recurrence = mf.get("recurrence")

            node_data = {
                "payer_id": payer_id,
                "payee_id": payee_id,
                "quantity": quantity,
                "traits": traits,
                "recurrence": recurrence,
            }
            graph.upsert_node(mf_id, "money_flow", node_data)

            # actor_pays_actor edge
            graph.add_edge(
                edge_type="actor_pays_actor",
                source=payer_id,
                target=payee_id,
                data={"via": mf_id}
            )

        # States
        for state in root.get("states", []):
            state_id = state["state_id"]
            node_data = {k: v for k, v in state.items() if k != "state_id"}
            graph.upsert_node(state_id, "state", node_data)

        # Meta 정보
        meta = {
            "seed_path": str(path),
            "domain_id": root.get("meta", {}).get("domain_id"),
            "as_of": root.get("meta", {}).get("as_of"),
            "num_actors": len(list(graph.nodes_by_type("actor"))),
            "num_money_flows": len(list(graph.nodes_by_type("money_flow"))),
            "num_states": len(list(graph.nodes_by_type("state"))),
        }

        return RealityGraphSnapshot(graph=graph, meta=meta)

    def snapshot(
        self,
        domain_id: str,
        region: str,
        segment: Optional[str] = None,
        as_of: Optional[str] = None,
        focal_actor_context_id: Optional[str] = None,
        slice_spec: Optional[Dict[str, Any]] = None
    ) -> RealityGraphSnapshot:
        """R-Graph snapshot 생성 (v2: 필터링 + Brownfield + 캐싱)

        프로세스:
        1. 캐시 확인 (Phase C)
        2. RealityGraphStore에서 기본 그래프 로딩 (또는 seed ingestion)
        3. as_of 필터링
        4. segment 필터링
        5. ProjectOverlay 적용 (Brownfield)
        6. 서브그래프 추출 (Brownfield, slice_spec 지원)
        7. 캐시 저장 (Phase C)

        Args:
            domain_id: 도메인 ID (예: "Adult_Language_Education_KR")
            region: 지역 (예: "KR")
            segment: 세그먼트 (선택)
            as_of: 기준일 (선택, "latest" 가능)
            focal_actor_context_id: FocalActorContext ID (선택, Brownfield)
            slice_spec: 서브그래프 커스터마이즈 (Phase C)
                       {"n_hops": 3, "include_competitors": True}

        Returns:
            RealityGraphSnapshot

        Raises:
            FileNotFoundError: seed 파일이 없을 때
        """
        # 0. 캐시 확인 (Phase C)
        if self.use_cache and self.cache:
            cache_key = self.cache.get_cache_key(
                domain_id, region, segment, as_of, focal_actor_context_id
            )
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        # 1. RealityGraphStore에서 기본 그래프 로딩
        if not self.reality_store.has_domain(domain_id):
            # seed ingestion
            seed_path = self._get_seed_path(domain_id)

            if not seed_path.exists():
                raise FileNotFoundError(
                    f"Reality seed not found for domain_id={domain_id!r}\n"
                    f"Expected path: {seed_path}\n"
                    f"Registered domains: {[d['domain_id'] for d in self.domain_registry.get('domains', [])]}"
                )

            self.reality_store.ingest_seed(domain_id, seed_path)

        base_graph = self.reality_store.get_graph(domain_id)

        # 2. as_of 필터링
        filtered_graph = apply_as_of_filter(base_graph, as_of)

        # 3. segment 필터링
        filtered_graph = apply_segment_filter(filtered_graph, segment)

        # 4. ProjectOverlay 적용 (Brownfield)
        if focal_actor_context_id:
            overlay = self.overlay_store.get_overlay(focal_actor_context_id)

            if overlay:
                # Overlay 결합
                combined_graph = merge_graphs(filtered_graph, overlay)

                # 5. 서브그래프 추출 (focal_actor 중심)
                # slice_spec 지원 (Phase C)
                n_hops = 2
                included_edge_types = None

                if slice_spec:
                    n_hops = slice_spec.get("n_hops", 2)

                    # include_competitors 옵션
                    if not slice_spec.get("include_competitors", True):
                        # actor_competes_with_actor 제외
                        included_edge_types = [
                            "actor_pays_actor",
                            "actor_serves_actor",
                            "actor_offers_resource",
                            "actor_has_contract_with_actor"
                        ]

                final_graph = extract_subgraph(
                    combined_graph,
                    focal_actor_id=overlay.focal_actor_id,
                    n_hops=n_hops,
                    included_edge_types=included_edge_types
                )
            else:
                # Overlay 없으면 전체 그래프
                final_graph = filtered_graph
        else:
            # Greenfield
            final_graph = filtered_graph

        # Meta 정보
        base_meta = self.reality_store.get_meta(domain_id)

        meta = {
            **base_meta,
            "domain_id": domain_id,
            "region": region,
            "segment": segment,
            "as_of": as_of,
            "focal_actor_context_id": focal_actor_context_id,
            "num_actors": len(list(final_graph.nodes_by_type("actor"))),
            "num_money_flows": len(list(final_graph.nodes_by_type("money_flow"))),
            "num_states": len(list(final_graph.nodes_by_type("state"))),
        }

        result = RealityGraphSnapshot(graph=final_graph, meta=meta)

        # 캐시 저장 (Phase C)
        if self.use_cache and self.cache:
            self.cache.put(cache_key, result)

        return result

    def ingest_focal_actor_context(
        self,
        focal_context: FocalActorContext
    ) -> tuple[str, list[str]]:
        """FocalActorContext(record) → ProjectOverlay 투영

        Args:
            focal_context: FocalActorContext

        Returns:
            (focal_actor_id, updated_node_ids)
        """
        binding = FocalActorContextBinding.from_record(focal_context)
        return ingest_focal_ctx(binding, self.overlay_store)

    def ingest_evidence(
        self,
        domain_id: str,
        evidence_list: List[EvidenceRecord]
    ) -> List[str]:
        """Evidence → RealityGraphStore 반영

        프로세스:
        1. ActorResolver로 Actor 식별/생성
        2. EvidenceMapper로 Evidence → 노드 변환
        3. 기존 노드 업데이트 또는 신규 추가
        4. Lineage 기록

        Args:
            domain_id: 도메인 ID
            evidence_list: Evidence 리스트

        Returns:
            updated_node_ids: 업데이트된 노드 ID 리스트
        """
        return self.reality_store.ingest_evidence(domain_id, evidence_list)


# 편의 함수 (하위 호환)
def snapshot(
    domain_id: str,
    region: Optional[str] = None,
    segment: Optional[str] = None,
    as_of: Optional[str] = None
) -> RealityGraphSnapshot:
    """World Engine snapshot 편의 함수"""
    engine = WorldEngine()
    return engine.snapshot(domain_id, region or "KR", segment, as_of)
