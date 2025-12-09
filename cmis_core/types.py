"""CMIS Core Types

Common dataclasses used across all v9 modules.
Based on umis_v9.yaml ontology and graph schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import hashlib
import uuid


# ========================================
# Graph Primitives
# ========================================

@dataclass
class Node:
    """Graph node (Actor/Event/Resource/MoneyFlow/Contract/State)"""
    id: str
    type: str  # "actor", "money_flow", "state", etc.
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """Graph edge (actor_pays_actor, event_triggers_money_flow, etc.)"""
    type: str
    source: str
    target: str
    data: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Metric & Value
# ========================================

@dataclass
class MetricRequest:
    """Metric 평가 요청"""
    metric_id: str  # "MET-Revenue", "MET-N_customers", etc.
    context: Dict[str, Any] = field(default_factory=dict)
    # context 예: {"domain_id": "Adult_Language_KR", "year": 2024}


@dataclass
class ValueRecord:
    """Metric 계산 결과 (V-Graph의 value_record 노드)"""
    metric_id: str
    context: Dict[str, Any]
    point_estimate: Optional[float] = None
    distribution: Optional[Dict[str, Any]] = None  # {"min": ..., "max": ...}
    quality: Dict[str, Any] = field(default_factory=dict)
    # quality 예: {"status": "ok", "method": "direct", "literal_ratio": 1.0}
    lineage: Dict[str, Any] = field(default_factory=dict)
    # lineage 예: {"from_evidence_ids": [...], "engine_ids": ["value_engine"]}


# ========================================
# Pattern Matching
# ========================================

@dataclass
class PatternMatch:
    """패턴 매칭 결과"""
    pattern_id: str  # "PAT-subscription_model", etc.
    description: str
    structure_fit_score: float  # 0.0 ~ 1.0
    execution_fit_score: Optional[float] = None  # project_context 있을 때만
    evidence: Dict[str, Any] = field(default_factory=dict)
    # evidence 예: {"source": "money_flow.traits.revenue_model", "node_ids": [...]}


@dataclass
class GapCandidate:
    """기회/갭 후보"""
    description: str
    related_pattern_ids: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Workflow Input/Output
# ========================================

@dataclass
class StructureAnalysisInput:
    """structure_analysis 워크플로우 입력"""
    domain_id: str
    region: str
    segment: Optional[str] = None
    as_of: Optional[str] = None
    project_context_id: Optional[str] = None  # Brownfield 모드 시


@dataclass
class StructureAnalysisResult:
    """structure_analysis 워크플로우 출력"""
    
    meta: Dict[str, Any] = field(default_factory=dict)
    # meta 예: {"domain_id": ..., "region": ..., "as_of": ...}
    
    graph_overview: Dict[str, Any] = field(default_factory=dict)
    # graph_overview 예:
    # {
    #   "num_actors": 7,
    #   "num_money_flows": 6,
    #   "actor_types": {"customer_segment": 2, "company": 5},
    #   "total_money_flow_amount": 290000000000
    # }
    
    pattern_matches: List[PatternMatch] = field(default_factory=list)
    
    metrics: List[ValueRecord] = field(default_factory=list)
    
    execution_time: Optional[float] = None  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용"""
        return {
            "meta": self.meta,
            "graph_overview": self.graph_overview,
            "pattern_matches": [
                {
                    "pattern_id": pm.pattern_id,
                    "description": pm.description,
                    "structure_fit_score": pm.structure_fit_score,
                    "execution_fit_score": pm.execution_fit_score,
                }
                for pm in self.pattern_matches
            ],
            "metrics": [
                {
                    "metric_id": vr.metric_id,
                    "point_estimate": vr.point_estimate,
                    "quality": vr.quality,
                }
                for vr in self.metrics
            ],
            "execution_time": self.execution_time,
        }


# ========================================
# Reality Graph Snapshot
# ========================================

@dataclass
class RealityGraphSnapshot:
    """World Engine snapshot 결과 (R-Graph 서브그래프)"""
    graph: Any  # InMemoryGraph (circular import 회피)
    meta: Dict[str, Any] = field(default_factory=dict)
    # meta 예: {"domain_id": ..., "seed_path": ..., "as_of": ...}


# ========================================
# Evidence Engine Types
# ========================================

class SourceTier(Enum):
    """Evidence source tier 정의
    
    Tier 우선순위 (상위 tier일수록 신뢰도 높음):
    1. official: 공식 통계/공시 (DART, KOSIS, Gov Stats)
    2. curated_internal: 내부 검증 데이터
    3. commercial: 상용 리서치 (Market Research, Consulting, Brokerage)
    
    주의: structured_estimation, llm_baseline은 ValueEngine.prior_estimation에서 처리
    """
    OFFICIAL = "official"
    CURATED_INTERNAL = "curated_internal"
    COMMERCIAL = "commercial"


class EvidenceValueKind(Enum):
    """Evidence 값 타입"""
    RAW_DOCUMENT = "raw_document"
    NUMERIC = "numeric"
    TABLE = "table"
    EXTRACTED_METRIC = "extracted_metric"
    RANGE = "range"
    DISTRIBUTION = "distribution"


class EvidenceSufficiency(Enum):
    """Evidence 충분성 상태"""
    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class EvidenceRequest:
    """Evidence 수집 요청
    
    MetricRequest에서 변환되거나 Reality Graph용으로 직접 생성
    """
    request_id: str
    request_type: str  # "metric", "reality_slice", "actor_info", etc.
    
    # Metric 요청 시
    metric_id: Optional[str] = None
    
    # Reality Graph 요청 시
    entity_type: Optional[str] = None  # "actor", "money_flow", "state"
    
    # 공통
    context: Dict[str, Any] = field(default_factory=dict)
    # context 예: {"domain_id": "...", "region": "KR", "year": 2024}
    
    required_capabilities: List[str] = field(default_factory=list)
    # 예: ["financial_statements", "market_size_reports"]
    
    quality_requirements: Dict[str, Any] = field(default_factory=dict)
    # 예: {"min_confidence": 0.8, "max_age_days": 365}


@dataclass
class EvidenceRecord:
    """개별 Evidence 레코드
    
    하나의 source에서 수집된 하나의 evidence
    """
    evidence_id: str
    source_tier: str  # "official", "curated_internal", "commercial"
    source_id: str  # "DART", "KOSIS", etc.
    
    # 데이터
    value: Any
    value_kind: EvidenceValueKind = EvidenceValueKind.NUMERIC
    schema_ref: Optional[str] = None
    # 예: "dart_filings_v1", "market_research_report_v1"
    
    # 품질
    confidence: float = 0.0
    
    # 메타데이터
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 예: {"subject": "...", "year": 2024, "url": "..."}
    
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Lineage
    lineage: Dict[str, Any] = field(default_factory=dict)
    # 예: {"query": "...", "response_time_ms": 123}


@dataclass
class EvidenceBundle:
    """여러 source의 Evidence 묶음
    
    EvidenceEngine.fetch_for_metrics()의 기본 반환 단위
    (하나의 EvidenceRequest에 대응)
    """
    request: EvidenceRequest
    
    records: List[EvidenceRecord] = field(default_factory=list)
    
    # 집계 품질 지표
    quality_summary: Dict[str, Any] = field(default_factory=dict)
    # 예: {"literal_ratio": 0.8, "spread_ratio": 0.2, "num_sources": 3}
    
    # 메타데이터
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_time_ms: Optional[float] = None
    
    # Debug trace (MEM-store 연계)
    debug_trace: List[Dict[str, Any]] = field(default_factory=list)
    # 예: [
    #   {"tier": 1, "source": "DART", "status": "success", "time_ms": 123},
    #   {"tier": 2, "source": "KOSIS", "status": "failed", "error": "timeout"}
    # ]
    
    def add_evidence(self, record: EvidenceRecord):
        """Evidence 추가"""
        self.records.append(record)
    
    def add_trace(self, tier: int, source_id: str, status: str, **kwargs):
        """Trace 추가"""
        self.debug_trace.append({
            "tier": tier,
            "source": source_id,
            "status": status,
            **kwargs
        })
    
    def get_best_record(self) -> Optional[EvidenceRecord]:
        """가장 신뢰도 높은 record 반환"""
        if not self.records:
            return None
        return max(self.records, key=lambda r: r.confidence)
    
    def get_records_by_tier(self, tier: str) -> List[EvidenceRecord]:
        """Tier별 record 필터링"""
        return [r for r in self.records if r.source_tier == tier]
    
    def calculate_quality_summary(self):
        """품질 지표 계산
        
        - literal_ratio: 상위 tier (official/curated) 비율
        - spread_ratio: 값 분산 정도
        - num_sources: source 개수
        """
        if not self.records:
            self.quality_summary = {
                "literal_ratio": 0.0,
                "spread_ratio": 0.0,
                "num_sources": 0
            }
            return
        
        # literal_ratio: official/curated 비율
        literal_count = sum(
            1 for r in self.records
            if r.source_tier in ["official", "curated_internal"]
        )
        literal_ratio = literal_count / len(self.records)
        
        # spread_ratio: 숫자 값의 분산
        numeric_values = [
            r.value for r in self.records
            if isinstance(r.value, (int, float))
        ]
        
        if len(numeric_values) >= 2:
            avg = sum(numeric_values) / len(numeric_values)
            spread_ratio = (max(numeric_values) - min(numeric_values)) / avg if avg > 0 else 0
        else:
            spread_ratio = 0.0
        
        self.quality_summary = {
            "literal_ratio": literal_ratio,
            "spread_ratio": spread_ratio,
            "num_sources": len(set(r.source_id for r in self.records))
        }


@dataclass
class EvidenceMultiResult:
    """여러 Metric의 Evidence 묶음
    
    ValueEngine이 요청한 여러 MetricRequest에 대한
    Metric별 EvidenceBundle 컬렉션
    """
    bundles: Dict[str, EvidenceBundle]
    # key: metric_id (예: "MET-Revenue")
    # value: 해당 metric의 EvidenceBundle
    
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    execution_summary: Dict[str, Any] = field(default_factory=dict)
    # 예: {
    #   "total_requests": 3,
    #   "successful": 2,
    #   "partial": 1,
    #   "total_time_ms": 1234
    # }
    
    def get_bundle(self, metric_id: str) -> Optional[EvidenceBundle]:
        """Metric별 bundle 조회"""
        return self.bundles.get(metric_id)
    
    def get_overall_quality(self) -> Dict[str, Any]:
        """전체 품질 지표 집계"""
        if not self.bundles:
            return {"literal_ratio": 0.0, "spread_ratio": 0.0}
        
        avg_literal = sum(
            b.quality_summary.get("literal_ratio", 0.0)
            for b in self.bundles.values()
        ) / len(self.bundles)
        
        avg_spread = sum(
            b.quality_summary.get("spread_ratio", 0.0)
            for b in self.bundles.values()
        ) / len(self.bundles)
        
        return {
            "literal_ratio": avg_literal,
            "spread_ratio": avg_spread,
            "num_metrics": len(self.bundles)
        }


@dataclass
class EvidenceSufficiencyResult:
    """Evidence 충분성 판단 결과"""
    status: EvidenceSufficiency
    reasons: List[str] = field(default_factory=list)
    # 예: ["literal_ratio too low (0.3 < 0.5)", "only 1 source"]
    
    summary: Dict[str, Any] = field(default_factory=dict)
    # 예: {"literal_ratio": 0.3, "spread_ratio": 0.8, "num_sources": 1}
    
    def is_usable(self) -> bool:
        """사용 가능 여부 (SUFFICIENT or PARTIAL)"""
        return self.status in [
            EvidenceSufficiency.SUFFICIENT,
            EvidenceSufficiency.PARTIAL
        ]


@dataclass
class EvidencePolicy:
    """Evidence 품질 정책 (cmis.yaml에서 로드)
    
    cmis.yaml의 policies.quality_profiles와 1:1 매핑
    """
    policy_id: str
    # "reporting_strict" | "decision_balanced" | "exploration_friendly"
    
    # Quality requirements (cmis.yaml에서 로드)
    min_literal_ratio: float
    max_spread_ratio: float
    allow_prior: bool  # structured_estimation + llm_baseline 허용 여부
    
    # Tier 제어
    allowed_tiers: List[str] = field(default_factory=lambda: [
        "official", "curated_internal", "commercial"
    ])
    # allow_prior=False면 structured_estimation/llm_baseline 제외
    
    # Execution 제어
    max_attempts_per_tier: int = 3
    max_total_time_seconds: int = 30
    best_effort_mode: bool = False
    # True면 PARTIAL도 허용, False면 SUFFICIENT만 허용
    
    @classmethod
    def from_config(cls, policy_id: str, config: Any) -> "EvidencePolicy":
        """cmis.yaml에서 policy 로드
        
        Args:
            policy_id: "reporting_strict" 등
            config: CMISConfig
        
        Returns:
            EvidencePolicy
        """
        # config.policies에서 quality_profiles 조회
        if hasattr(config, 'policies'):
            quality_profiles = config.policies.get('quality_profiles', {})
        else:
            quality_profiles = {}
        
        profile = quality_profiles.get(policy_id, {})
        
        # 기본값 설정 (profile이 없을 경우)
        if not profile:
            # 기본 policy 값
            default_profiles = {
                "reporting_strict": {
                    "min_literal_ratio": 0.7,
                    "max_spread_ratio": 0.3,
                    "allow_prior": False
                },
                "decision_balanced": {
                    "min_literal_ratio": 0.5,
                    "max_spread_ratio": 0.5,
                    "allow_prior": True
                },
                "exploration_friendly": {
                    "min_literal_ratio": 0.3,
                    "max_spread_ratio": 0.7,
                    "allow_prior": True
                }
            }
            profile = default_profiles.get(policy_id, {
                "min_literal_ratio": 0.5,
                "max_spread_ratio": 0.5,
                "allow_prior": False
            })
        
        allowed_tiers = ["official", "curated_internal", "commercial"]
        
        return cls(
            policy_id=policy_id,
            min_literal_ratio=profile.get("min_literal_ratio", 0.5),
            max_spread_ratio=profile.get("max_spread_ratio", 0.5),
            allow_prior=profile.get("allow_prior", False),
            allowed_tiers=allowed_tiers,
            best_effort_mode=(policy_id == "exploration_friendly")
        )
