"""Evidence Mapper - Evidence → R-Graph 변환

Evidence 타입별 R-Graph primitive 매핑

2025-12-11: World Engine Phase B
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from .graph import Node, Edge
from .types import EvidenceRecord
from .actor_resolver import ActorResolver


class EvidenceMapper:
    """Evidence → R-Graph 노드/엣지 변환
    
    Evidence 타입별 매핑:
    - 재무제표 (DART) → State
    - 시장규모 (KOSIS, 리서치) → State (market)
    - 고객수 (검색, API) → State
    - 회사 정보 (검색) → Actor
    - 거래 데이터 → MoneyFlow
    """
    
    def __init__(self, actor_resolver: ActorResolver):
        """
        Args:
            actor_resolver: ActorResolver
        """
        self.actor_resolver = actor_resolver
    
    def map_evidence(
        self,
        evidence: EvidenceRecord
    ) -> Union[Node, Edge, List[Node], None]:
        """Evidence → R-Graph 노드/엣지
        
        Args:
            evidence: Evidence
        
        Returns:
            Node, Edge, List[Node], 또는 None (매핑 불가)
        """
        source_id = evidence.source_id
        metric_id = evidence.metadata.get("metric_id", "")
        
        # 1. 재무제표 Evidence (DART)
        if source_id == "KR_DART_filings":
            return self._map_financial_statement(evidence)
        
        # 2. 시장규모 Evidence (KOSIS, 리서치)
        elif metric_id.startswith("MET-Market_size") or metric_id.startswith("MET-TAM"):
            return self._map_market_size(evidence)
        
        # 3. 고객수 Evidence
        elif metric_id.startswith("MET-N_customers"):
            return self._map_customer_count(evidence)
        
        # 4. 매출 Evidence
        elif metric_id.startswith("MET-Revenue"):
            return self._map_revenue(evidence)
        
        # 5. 회사 정보 Evidence (검색)
        elif source_id in ["google_search", "duckduckgo_search"]:
            return self._map_company_info(evidence)
        
        # 6. 거래 데이터
        elif "transaction" in metric_id.lower():
            return self._map_transaction(evidence)
        
        # 기타: 매핑 불가
        return None
    
    def _map_financial_statement(
        self,
        evidence: EvidenceRecord
    ) -> Optional[Node]:
        """재무제표 → State 노드
        
        Args:
            evidence: 재무제표 Evidence
        
        Returns:
            State 노드
        """
        context = evidence.context
        
        # Actor 식별
        actor_id, is_new = self.actor_resolver.resolve_actor_id(context)
        
        if actor_id is None:
            # 신규 Actor 생성 필요 (여기서는 State만 반환)
            actor_id = self.actor_resolver.generate_new_actor_id(context)
        
        # State 노드 생성
        state_id = f"STATE-{actor_id}-financial-{context.get('fiscal_year', 'unknown')}"
        
        properties = {
            "revenue": evidence.value,
            "fiscal_year": context.get("fiscal_year"),
            "source": "dart_filings"
        }
        
        # 추가 재무 정보
        if "profit" in context:
            properties["profit"] = context["profit"]
        if "gross_margin" in context:
            properties["gross_margin"] = context["gross_margin"]
        
        state = Node(
            id=state_id,
            type="state",
            data={
                "target_type": "actor",
                "target_id": actor_id,
                "as_of": context.get("fiscal_year", evidence.as_of),
                "properties": properties,
                "traits": {
                    "data_source": "official_filings"
                },
                "lineage": {
                    "from_evidence_ids": [evidence.evidence_id],
                    "source_tier": evidence.source_tier,
                    "created_at": datetime.now().isoformat()
                }
            }
        )
        
        return state
    
    def _map_market_size(
        self,
        evidence: EvidenceRecord
    ) -> Optional[Node]:
        """시장규모 → State (market) 노드
        
        Args:
            evidence: 시장규모 Evidence
        
        Returns:
            State 노드
        """
        context = evidence.context
        
        # Market segment ID 생성
        domain = context.get("domain_id", "unknown")
        region = context.get("region", "unknown")
        market_id = f"MARKET-{domain}-{region}"
        
        # State 노드
        state_id = f"STATE-{market_id}-size-{context.get('year', 'unknown')}"
        
        state = Node(
            id=state_id,
            type="state",
            data={
                "target_type": "market_segment",
                "target_id": market_id,
                "as_of": str(context.get("year", evidence.as_of)),
                "properties": {
                    "market_size": evidence.value,
                    "unit": context.get("unit", "KRW"),
                    "metric_id": evidence.metadata.get("metric_id")
                },
                "lineage": {
                    "from_evidence_ids": [evidence.evidence_id],
                    "source_tier": evidence.source_tier,
                    "created_at": datetime.now().isoformat()
                }
            }
        )
        
        return state
    
    def _map_customer_count(
        self,
        evidence: EvidenceRecord
    ) -> Optional[Node]:
        """고객수 → State 노드
        
        Args:
            evidence: 고객수 Evidence
        
        Returns:
            State 노드
        """
        context = evidence.context
        
        # Actor 식별
        actor_id, is_new = self.actor_resolver.resolve_actor_id(context)
        
        if actor_id is None:
            actor_id = self.actor_resolver.generate_new_actor_id(context)
        
        # State 노드
        state_id = f"STATE-{actor_id}-customers-{context.get('year', 'current')}"
        
        state = Node(
            id=state_id,
            type="state",
            data={
                "target_type": "actor",
                "target_id": actor_id,
                "as_of": evidence.as_of or datetime.now().date().isoformat(),
                "properties": {
                    "n_customers": evidence.value,
                    "metric_id": evidence.metadata.get("metric_id")
                },
                "lineage": {
                    "from_evidence_ids": [evidence.evidence_id],
                    "source_tier": evidence.source_tier,
                    "created_at": datetime.now().isoformat()
                }
            }
        )
        
        return state
    
    def _map_revenue(
        self,
        evidence: EvidenceRecord
    ) -> Optional[Node]:
        """매출 → State 노드
        
        Args:
            evidence: 매출 Evidence
        
        Returns:
            State 노드
        """
        context = evidence.context
        
        # Actor 식별
        actor_id, is_new = self.actor_resolver.resolve_actor_id(context)
        
        if actor_id is None:
            actor_id = self.actor_resolver.generate_new_actor_id(context)
        
        # State 노드
        state_id = f"STATE-{actor_id}-revenue-{context.get('year', 'current')}"
        
        state = Node(
            id=state_id,
            type="state",
            data={
                "target_type": "actor",
                "target_id": actor_id,
                "as_of": evidence.as_of or context.get("year"),
                "properties": {
                    "revenue": evidence.value,
                    "metric_id": evidence.metadata.get("metric_id"),
                    "unit": "KRW"
                },
                "lineage": {
                    "from_evidence_ids": [evidence.evidence_id],
                    "source_tier": evidence.source_tier,
                    "created_at": datetime.now().isoformat()
                }
            }
        )
        
        return state
    
    def _map_company_info(
        self,
        evidence: EvidenceRecord
    ) -> Optional[Node]:
        """회사 정보 (검색) → Actor 노드
        
        Args:
            evidence: 검색 Evidence
        
        Returns:
            Actor 노드
        """
        context = evidence.context
        
        # Actor 식별
        actor_id, is_new = self.actor_resolver.resolve_actor_id(context)
        
        if actor_id is None:
            # 신규 Actor 생성
            actor_id = self.actor_resolver.generate_new_actor_id(context)
            
            actor = Node(
                id=actor_id,
                type="actor",
                data={
                    "name": context.get("company_name", "Unknown"),
                    "kind": "company",
                    "traits": self.actor_resolver._extract_traits_from_evidence(evidence),
                    "created_at": datetime.now().isoformat(),
                    "lineage": {
                        "from_evidence_ids": [evidence.evidence_id],
                        "source_tier": evidence.source_tier,
                        "created_at": datetime.now().isoformat()
                    }
                }
            )
            
            return actor
        else:
            # 기존 Actor 업데이트 (ActorResolver에서 처리)
            return None
    
    def _map_transaction(
        self,
        evidence: EvidenceRecord
    ) -> Optional[Node]:
        """거래 데이터 → MoneyFlow 노드
        
        Args:
            evidence: 거래 Evidence
        
        Returns:
            MoneyFlow 노드
        """
        context = evidence.context
        
        payer_id = context.get("payer_id")
        payee_id = context.get("payee_id")
        
        if not payer_id or not payee_id:
            return None
        
        # MoneyFlow 노드
        mf_id = f"MFL-{payer_id}-{payee_id}-{context.get('timestamp', 'unknown')}"
        
        money_flow = Node(
            id=mf_id,
            type="money_flow",
            data={
                "payer_id": payer_id,
                "payee_id": payee_id,
                "quantity": {
                    "amount": evidence.value,
                    "unit": "KRW"
                },
                "timestamp": evidence.as_of or datetime.now().isoformat(),
                "recurrence": context.get("recurrence", "one_off"),
                "traits": {},
                "lineage": {
                    "from_evidence_ids": [evidence.evidence_id],
                    "source_tier": evidence.source_tier,
                    "created_at": datetime.now().isoformat()
                }
            }
        )
        
        return money_flow

