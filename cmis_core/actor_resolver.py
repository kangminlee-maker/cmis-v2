"""Actor Resolver - Actor 동일성 판별 및 병합

Evidence에서 Actor 식별 시 중복 방지 및 병합 전략

2025-12-11: World Engine Phase B
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from difflib import SequenceMatcher

from .graph import InMemoryGraph, Node
from .types import EvidenceRecord


class ActorResolver:
    """Actor 동일성 판별 및 병합
    
    역할:
    1. Evidence context → 기존 Actor ID 또는 신규 ID
    2. Actor 중복 방지 (사업자등록번호, 증권코드, 회사명)
    3. 기존 Actor + 새 Evidence 병합
    
    우선순위:
    1. company_registration_number (사업자등록번호)
    2. stock_code (증권코드)
    3. company_name fuzzy matching (threshold 0.9+)
    """
    
    def __init__(self, reality_graph: InMemoryGraph):
        """
        Args:
            reality_graph: RealityGraphStore의 그래프
        """
        self.reality_graph = reality_graph
        
        # 인덱스 (빠른 조회)
        self._build_indexes()
    
    def _build_indexes(self) -> None:
        """Actor 인덱스 구축"""
        self.crn_index: Dict[str, str] = {}  # company_registration_number → actor_id
        self.stock_code_index: Dict[str, str] = {}  # stock_code → actor_id
        self.name_index: Dict[str, str] = {}  # normalized_name → actor_id
        
        for actor in self.reality_graph.nodes_by_type("actor"):
            actor_id = actor.id
            traits = actor.data.get("traits", {})
            
            # company_registration_number
            if "company_registration_number" in traits:
                crn = traits["company_registration_number"]
                self.crn_index[crn] = actor_id
            
            # stock_code
            if "stock_code" in traits:
                stock_code = traits["stock_code"]
                self.stock_code_index[stock_code] = actor_id
            
            # company name
            name = actor.data.get("name", "")
            if name:
                normalized = self._normalize_name(name)
                self.name_index[normalized] = actor_id
    
    def resolve_actor_id(
        self,
        evidence_context: Dict[str, Any]
    ) -> tuple[Optional[str], bool]:
        """Evidence context → 기존 Actor ID 또는 None
        
        Args:
            evidence_context: Evidence의 context 필드
        
        Returns:
            (actor_id, is_new)
            - actor_id: 기존 Actor ID 또는 None (신규 생성 필요)
            - is_new: True면 신규 생성, False면 기존 Actor
        """
        # 1. company_registration_number (최우선)
        if "company_registration_number" in evidence_context:
            crn = evidence_context["company_registration_number"]
            if crn in self.crn_index:
                return (self.crn_index[crn], False)
        
        # 2. stock_code
        if "stock_code" in evidence_context:
            stock_code = evidence_context["stock_code"]
            if stock_code in self.stock_code_index:
                return (self.stock_code_index[stock_code], False)
        
        # 3. company_name fuzzy matching
        if "company_name" in evidence_context:
            company_name = evidence_context["company_name"]
            similar_actor_id = self._find_similar_actor(company_name, threshold=0.9)
            if similar_actor_id:
                return (similar_actor_id, False)
        
        # 4. 신규 생성 필요
        return (None, True)
    
    def _find_similar_actor(
        self,
        company_name: str,
        threshold: float = 0.9
    ) -> Optional[str]:
        """Fuzzy matching으로 유사 Actor 찾기
        
        Args:
            company_name: 회사명
            threshold: 유사도 임계값 (0.9 = 90% 이상 일치)
        
        Returns:
            유사 Actor ID 또는 None
        """
        normalized_query = self._normalize_name(company_name)
        
        best_match_id = None
        best_score = 0.0
        
        for normalized_name, actor_id in self.name_index.items():
            score = SequenceMatcher(None, normalized_query, normalized_name).ratio()
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match_id = actor_id
        
        return best_match_id
    
    def _normalize_name(self, name: str) -> str:
        """회사명 정규화
        
        Args:
            name: 원본 회사명
        
        Returns:
            정규화된 회사명 (소문자, 공백 제거)
        """
        # 소문자 변환
        normalized = name.lower()
        
        # 공백 제거
        normalized = normalized.replace(" ", "")
        
        # 특수문자 제거
        normalized = normalized.replace("(주)", "")
        normalized = normalized.replace("주식회사", "")
        normalized = normalized.replace("㈜", "")
        normalized = normalized.replace(",", "")
        normalized = normalized.replace(".", "")
        
        return normalized
    
    def merge_actor_data(
        self,
        existing_actor: Node,
        evidence: EvidenceRecord
    ) -> Node:
        """기존 Actor + 새 Evidence 병합
        
        규칙:
        - traits: 합집합 (conflict 시 최신 Evidence 우선)
        - name: 기존 유지 (Evidence로 업데이트 안 함)
        - lineage: 추가
        
        Args:
            existing_actor: 기존 Actor 노드
            evidence: 새 Evidence
        
        Returns:
            업데이트된 Actor 노드
        """
        # traits 병합
        updated_traits = dict(existing_actor.data.get("traits", {}))
        new_traits = self._extract_traits_from_evidence(evidence)
        
        for key, value in new_traits.items():
            if key not in updated_traits:
                # 새 trait 추가
                updated_traits[key] = value
            else:
                # Conflict: 최신 Evidence 우선
                evidence_timestamp = evidence.as_of or evidence.timestamp
                existing_timestamp = existing_actor.data.get("last_updated", "1900-01-01")
                
                if evidence_timestamp and evidence_timestamp > existing_timestamp:
                    updated_traits[key] = value
        
        # lineage 추가
        lineage = existing_actor.data.get("lineage", {})
        evidence_ids = lineage.get("from_evidence_ids", [])
        
        if evidence.evidence_id not in evidence_ids:
            evidence_ids.append(evidence.evidence_id)
        
        lineage["from_evidence_ids"] = evidence_ids
        lineage["updated_at"] = evidence.timestamp
        
        # Actor 업데이트
        updated_data = dict(existing_actor.data)
        updated_data["traits"] = updated_traits
        updated_data["lineage"] = lineage
        updated_data["last_updated"] = evidence.as_of or evidence.timestamp
        
        existing_actor.data = updated_data
        
        return existing_actor
    
    def _extract_traits_from_evidence(
        self,
        evidence: EvidenceRecord
    ) -> Dict[str, Any]:
        """Evidence에서 Actor traits 추출
        
        Args:
            evidence: Evidence
        
        Returns:
            Traits dict
        """
        traits = {}
        context = evidence.context
        
        # company_registration_number
        if "company_registration_number" in context:
            traits["company_registration_number"] = context["company_registration_number"]
        
        # stock_code
        if "stock_code" in context:
            traits["stock_code"] = context["stock_code"]
        
        # industry
        if "industry" in context:
            traits["industry"] = context["industry"]
        
        # domain_expertise
        if "domain_expertise" in context:
            traits["domain_expertise"] = context["domain_expertise"]
        
        return traits
    
    def generate_new_actor_id(
        self,
        evidence_context: Dict[str, Any]
    ) -> str:
        """신규 Actor ID 생성
        
        Args:
            evidence_context: Evidence context
        
        Returns:
            새 Actor ID
        """
        # company_name 기반으로 ID 생성
        company_name = evidence_context.get("company_name", "Unknown")
        
        # 간단한 규칙: ACT-{정규화된 이름}
        normalized = self._normalize_name(company_name)
        
        # 충돌 방지: 카운터 추가
        base_id = f"ACT-{normalized[:20]}"  # 최대 20자
        actor_id = base_id
        counter = 1
        
        while self.reality_graph.get_node(actor_id) is not None:
            actor_id = f"{base_id}-{counter}"
            counter += 1
        
        return actor_id

