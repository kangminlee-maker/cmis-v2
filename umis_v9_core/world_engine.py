"""UMIS v9 World Engine v1

Evidence → R-Graph 변환 및 snapshot 생성
v1: Reality seed 기반만 (EvidenceEngine 미사용)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from .graph import InMemoryGraph
from .types import RealityGraphSnapshot


# v9 스펙 참조
PROCESS_PHASES_REF = "umis_v9_process_phases.yaml#structure_analysis"
AGENT_PROTOCOLS_REF = "umis_v9_agent_protocols.yaml"
VALIDATION_GATES_REF = "umis_v9_validation_gates.yaml#gate_types"


class WorldEngine:
    """World Engine v1 - Reality seed → R-Graph 변환
    
    v1 범위:
    - Reality seed YAML 로딩
    - Actor/MoneyFlow/State 노드 생성
    - actor_pays_actor edge 생성
    - snapshot() API
    
    v2+ 예정:
    - Evidence Engine 연동
    - LLM 기반 구조 추출
    - On-demand R-Graph 구축
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Args:
            project_root: 프로젝트 루트 경로 (None이면 자동 탐색)
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = Path(project_root)
        self.seeds_dir = self.project_root / "seeds"
        
        # domain_registry 로드
        self.domain_registry = self._load_domain_registry()
    
    def _load_domain_registry(self) -> Dict[str, Any]:
        """domain_registry.yaml 로드"""
        registry_path = self.project_root / "domain_registry.yaml"
        
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
        
        root = data.get("umis_v9_reality_seed", {})
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
        project_context_id: Optional[str] = None
    ) -> RealityGraphSnapshot:
        """R-Graph snapshot 생성 (v1: seed 기반만)
        
        Args:
            domain_id: 도메인 ID (예: "Adult_Language_Education_KR")
            region: 지역 (예: "KR")
            segment: 세그먼트 (선택)
            as_of: 기준일 (선택)
            project_context_id: 프로젝트 컨텍스트 ID (선택, Brownfield)
        
        Returns:
            RealityGraphSnapshot
        
        Raises:
            FileNotFoundError: seed 파일이 없을 때
            NotImplementedError: v1에서 지원하지 않는 domain_id
        
        Note:
            v1에서는 segment, as_of, project_context_id는 meta에만 기록하고
            실제 필터링/확장은 수행하지 않음 (v2+에서 구현)
        """
        seed_path = self._get_seed_path(domain_id)
        
        if not seed_path.exists():
            raise FileNotFoundError(
                f"Reality seed not found for domain_id={domain_id!r}\n"
                f"Expected path: {seed_path}\n"
                f"Registered domains: {[d['domain_id'] for d in self.domain_registry.get('domains', [])]}"
            )
        
        snapshot = self.load_reality_seed(seed_path)
        
        # Meta 정보 업데이트
        snapshot.meta.update({
            "domain_id": domain_id,
            "region": region,
            "segment": segment,
            "as_of": as_of,
            "project_context_id": project_context_id,
        })
        
        return snapshot


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
