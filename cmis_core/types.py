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
class PatternSpec:
    """Pattern 정의 (v1.1 - 13개 필드)

    Pattern은 Trait 조합 + Graph 구조로 정의됩니다.
    Ontology lock-in 최소화를 위해 고정 타입이 아닌 Trait 기반 정의.
    """
    pattern_id: str
    name: str
    family: str  # "business_model_patterns", "value_chain_patterns", etc.
    description: str

    # Trait 제약
    trait_constraints: Dict[str, Any]
    # {
    #   "money_flow": {
    #     "required_traits": {"revenue_model": "subscription"},
    #     "optional_traits": {"recurrence": ["monthly", "yearly"]}
    #   }
    # }

    # Graph 구조 제약
    graph_structure: Dict[str, Any]
    # {
    #   "requires": [
    #     {"node_type": "money_flow", "min_count": 1}
    #   ]
    # }

    # 정량 제약 (선택)
    quantitative_bounds: Optional[Dict[str, Any]] = None

    # Pattern 관계
    composes_with: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    specializes: Optional[str] = None

    # Benchmark (ValueEngine 연동)
    benchmark_metrics: List[str] = field(default_factory=list)

    # Context Archetype 적합성
    suited_for_contexts: List[str] = field(default_factory=list)

    # ===== v1.1 추가: Execution Fit 계산용 =====
    required_capabilities: List[Dict[str, Any]] = field(default_factory=list)
    required_assets: Dict[str, Any] = field(default_factory=dict)
    constraint_checks: List[str] = field(default_factory=list)


@dataclass
class PatternMatch:
    """패턴 매칭 결과 (v1.1 - 8개 필드)"""
    pattern_id: str
    description: str

    # 점수
    structure_fit_score: float  # 0.0 ~ 1.0
    execution_fit_score: Optional[float] = None  # project_context 있을 때만
    combined_score: float = 0.0  # structure × execution (or structure if no execution)

    # 증거
    evidence: Dict[str, Any] = field(default_factory=dict)

    # ===== v1.1 추가: Instance 정보 =====
    anchor_nodes: Dict[str, List[str]] = field(default_factory=dict)
    # {"actor": ["ACT-001"], "money_flow": ["MFL-101"]}

    instance_scope: Optional[Dict[str, Any]] = None
    # {"domain": "education", "focal_actor": "ACT-001"}


@dataclass
class GapCandidate:
    """기회/갭 후보"""
    pattern_id: str  # 추가: 어떤 Pattern이 누락됐는지
    description: str
    expected_level: str = "common"  # "core", "common", "rare"
    feasibility: str = "unknown"  # "high", "medium", "low", "unknown"
    execution_fit_score: Optional[float] = None
    related_pattern_ids: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Focal Actor Context (formerly: ProjectContext)
# ========================================

@dataclass
class FocalActorContext:
    """Focal Actor Context (확장 버전 - Phase A + Learning).

    의도:
    - 기존 명칭(ProjectContext)은 ProjectLedger/Workflow task 등 "실행 단위" 개념과 혼동될 여지가 큽니다.
    - 본 객체는 "프로젝트 실행 계획"이 아니라, Brownfield에서 focal actor(우리/클라이언트)의
      자산/제약/선호/기준상태를 포함하는 '컨텍스트 레코드(PRJ-*)'입니다.

    NOTE:
    - 실제 구현은 cmis.yaml의 project_context_store(추후 focal_actor_context_store로 개명 가능) 스키마를 참조합니다.
    """
    project_context_id: str

    # Version (Learning Phase 2)
    version: int = 1
    previous_version_id: Optional[str] = None

    # Scope
    scope: Dict[str, Any] = field(default_factory=dict)

    # Assets Profile
    assets_profile: Dict[str, Any] = field(default_factory=dict)

    # Baseline State
    baseline_state: Dict[str, Any] = field(default_factory=dict)

    # focal_actor_id
    focal_actor_id: Optional[str] = None

    # Constraints Profile
    constraints_profile: Dict[str, Any] = field(default_factory=dict)

    # Preference Profile
    preference_profile: Dict[str, Any] = field(default_factory=dict)

    # Lineage (Learning Phase 2)
    lineage: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "from_outcome_ids": [...],
    #   "updated_at": "...",
    #   "updated_by": "learning_engine"
    # }


@dataclass
class ContextArchetype:
    """Context Archetype (간소화 버전)

    특정 시장/산업의 전형적인 특징과 Expected Pattern Set
    """
    archetype_id: str
    name: str
    description: str

    # 판별 기준
    criteria: Dict[str, Any]
    # {"region": "KR", "domain": "education", "delivery_channel": "online"}

    # Expected Pattern Set
    expected_patterns: Dict[str, List[Dict]]
    # {
    #   "core": [{"pattern_id": "PAT-...", "weight": 0.9}],
    #   "common": [...],
    #   "rare": [...]
    # }

    # 신뢰도 (determine_context_archetype에서 설정)
    confidence: float = 1.0


# ========================================
# Search Strategy Types (v2.0)
# ========================================

@dataclass
class SearchContext:
    """검색 Context (통합 모델)

    검색 전략 수립에 필요한 모든 정보
    """
    # 기본
    domain_id: str
    region: str
    metric_id: str
    year: int

    # 언어 (다국어 검색)
    language: str = "auto"  # "ko", "en", "ja", "auto"

    # 정책
    policy_mode: str = "decision_balanced"

    # 선택적
    data_source_id: Optional[str] = None
    segment: Optional[str] = None

    # Budget
    max_queries: int = 5
    max_total_time: int = 30  # seconds
    max_cost_per_metric: float = 0.01  # USD


@dataclass
class SearchStep:
    """검색 단계"""
    data_source_id: str
    base_query_template: str
    use_llm_query: bool
    num_queries: int
    languages: List[str]
    timeout_sec: int
    priority: int = 1


@dataclass
class SearchPlan:
    """검색 계획"""
    metric_id: str
    context: SearchContext
    steps: List[SearchStep]
    total_budget: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResultQuality:
    """쿼리 결과 품질 평가"""
    score: float  # 0.0 ~ 1.0

    # 기본 지표
    has_numbers: bool
    num_numbers: int
    year_match: bool

    # Source
    source_tier: str
    source_id: str

    # 언어
    language: str
    query: str

    # 평가 상세
    metric_relevance: float = 0.5
    temporal_relevance: float = 0.5
    numeric_confidence: float = 0.5

    # 메타
    notes: Dict[str, Any] = field(default_factory=dict)


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

    # Context (Phase B 추가)
    context: Dict[str, Any] = field(default_factory=dict)
    # 예: {"company_name": "...", "domain_id": "...", "region": "..."}

    # 시간 정보 (Phase B 추가)
    as_of: Optional[str] = None  # 데이터 기준일
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())  # 수집 시점

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

    def get_evidence_bundle_summary(self) -> Dict[str, Any]:
        """
        PolicyEngine v2용 EvidenceBundleSummary 생성

        Returns:
            {
                "num_sources": int,
                "source_tiers_used": List[str],
                "max_age_days": int
            }
        """
        if not self.bundles:
            return {
                "num_sources": 0,
                "source_tiers_used": [],
                "max_age_days": 0
            }

        # 모든 bundle의 records 수집
        all_records = []
        for bundle in self.bundles.values():
            all_records.extend(bundle.records)

        if not all_records:
            return {
                "num_sources": 0,
                "source_tiers_used": [],
                "max_age_days": 0
            }

        # num_sources (unique source_id)
        unique_sources = set(r.source_id for r in all_records)
        num_sources = len(unique_sources)

        # source_tiers_used (unique tiers)
        source_tiers_used = sorted(list(set(r.source_tier for r in all_records)))

        # max_age_days (timestamp 기반 계산)
        from datetime import datetime as dt, timezone
        now = dt.now(timezone.utc)

        max_age_days = 0
        for record in all_records:
            try:
                record_time = dt.fromisoformat(record.retrieved_at.replace('Z', '+00:00'))
                age_days = (now - record_time).days
                max_age_days = max(max_age_days, age_days)
            except:
                pass

        return {
            "num_sources": num_sources,
            "source_tiers_used": source_tiers_used,
            "max_age_days": max_age_days
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


# ========================================
# Strategy & Decision (D-Graph)
# ========================================

@dataclass
class Goal:
    """목표 정의 (D-Graph goal 노드)

    cmis.yaml decision_graph.goal 스키마 기반
    """
    goal_id: str
    name: str
    description: str = ""

    # Target Metrics
    target_metrics: List[Dict[str, Any]] = field(default_factory=list)
    # [{"metric_id": "MET-Revenue", "operator": ">", "value": 10000000000, "horizon": "3y"}]

    target_horizon: str = "3y"
    project_context_id: Optional[str] = None
    scope: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Strategy:
    """전략 정의 (D-Graph strategy 노드)"""
    strategy_id: str
    name: str
    description: str = ""

    pattern_composition: List[str] = field(default_factory=list)
    action_set: List[Dict[str, Any]] = field(default_factory=list)
    expected_outcomes: Dict[str, Any] = field(default_factory=dict)

    execution_fit_score: Optional[float] = None
    adjusted_score: Optional[float] = None

    risks: List[Dict[str, Any]] = field(default_factory=list)
    created_from: str = "pattern_combination"
    source_patterns: List[str] = field(default_factory=list)
    lineage: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioEvaluation:
    """Portfolio 평가 결과"""
    portfolio_id: str
    strategy_ids: List[str]

    aggregate_roi: float = 0.0
    aggregate_risk: float = 0.0
    combined_score: float = 0.0

    synergies: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)

    policy_ref: str = "decision_balanced"
    project_context_id: Optional[str] = None
    lineage: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Learning & Outcome
# ========================================

@dataclass
class Outcome:
    """실제 실행 결과 (outcome_store)

    Strategy/Scenario 실행 후 실제 측정된 결과
    """
    outcome_id: str

    # 연결
    related_strategy_id: Optional[str] = None
    related_scenario_id: Optional[str] = None
    project_context_id: Optional[str] = None

    # 실제 측정 시점
    as_of: str = ""

    # 실제 Metric 값
    metrics: Dict[str, Any] = field(default_factory=dict)
    # {"MET-Revenue": 12000000000, "MET-N_customers": 150000}

    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    # {"domain_id": "...", "region": "...", "segment": "..."}

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningResult:
    """학습 결과"""
    learning_id: str
    outcome_id: str

    # 비교 결과
    comparisons: List[Dict[str, Any]] = field(default_factory=list)

    # 업데이트
    updates: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "pattern_benchmarks": [...],
    #   "metric_formulas": [...],
    #   "confidence_adjustments": [...]
    # }

    # 학습 품질
    learning_quality: Dict[str, Any] = field(default_factory=dict)

    # Lineage
    lineage: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Belief & Prior (BeliefEngine)
# ========================================

@dataclass
class BeliefRecord:
    """Belief/Prior Distribution 통합 레코드

    BeliefEngine에서 관리하는 Metric에 대한 Prior/Posterior Distribution.
    Evidence가 부족할 때 최후 수단으로 사용.

    Usage:
        # Pattern 기반 Prior 생성
        prior = BeliefRecord(
            belief_id="PRIOR-abc123",
            metric_id="MET-SAM",
            context={"domain_id": "...", "region": "KR"},
            distribution={"type": "lognormal", "params": {...}},
            confidence=0.5,
            source="pattern_benchmark",
            observations=[],
            n_observations=0,
            created_at="2025-12-12T10:00:00Z",
            updated_at="2025-12-12T10:00:00Z",
            lineage={"from_pattern_ids": ["PAT-001"]}
        )

        # Outcome 기반 Belief 업데이트
        updated = BeliefRecord(
            belief_id="BELIEF-def456",
            metric_id="MET-SAM",
            context={"domain_id": "...", "region": "KR"},
            distribution={"type": "normal", "params": {...}},
            confidence=0.85,
            source="learned",
            observations=[{"value": 50000, "weight": 1.0, "source": "OUT-001"}],
            n_observations=1,
            created_at="2025-12-12T10:00:00Z",
            updated_at="2025-12-12T11:00:00Z",
            lineage={"from_prior_id": "PRIOR-abc123", "from_outcome_ids": ["OUT-001"]}
        )
    """

    # 식별
    belief_id: str  # "BELIEF-xxxx" 또는 "PRIOR-xxxx"
    metric_id: str  # "MET-SAM", "MET-TAM", etc.
    context: Dict[str, Any]  # {"domain_id": "...", "region": "...", "segment": "..."}

    # Distribution
    distribution: Dict[str, Any]
    # {
    #   "type": "normal" | "lognormal" | "uniform" | "beta" | "empirical",
    #   "params": {"mu": 50000, "sigma": 10000} | {...},
    #   "percentiles": {"p10": ..., "p50": ..., "p90": ...}  # optional
    # }

    confidence: float  # 0.0 ~ 1.0
    # - 0.1: Uninformative prior (매우 넓은 분포)
    # - 0.5: Pattern benchmark 기반
    # - 0.7: Domain expert 기반
    # - 0.85+: 여러 observation 기반 학습된 belief

    source: str
    # "pattern_benchmark" | "uninformative" | "learned" | "domain_expert"

    # Observations (업데이트용)
    observations: List[Dict[str, Any]]
    # [
    #   {"value": 50000, "weight": 1.0, "source": "EVD-001"},
    #   {"value": 48000, "weight": 0.8, "source": "OUT-002"},
    #   ...
    # ]

    n_observations: int  # 누적 관측 횟수

    # 시간
    created_at: str  # ISO datetime
    updated_at: str  # ISO datetime

    # Lineage
    lineage: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "from_evidence_ids": ["EVD-001", ...],  # Evidence 기반 관측
    #   "from_outcome_ids": ["OUT-001", ...],   # Outcome 기반 관측
    #   "from_prior_id": "PRIOR-abc123",        # 이전 Prior/Belief
    #   "from_pattern_ids": ["PAT-001", ...],   # Pattern Benchmark
    #   "engine_ids": ["belief_engine"],
    #   "created_at": "...",
    #   "policy_adjustment": "reporting_strict_conservative"  # Policy 조정
    # }

    def to_dict(self) -> Dict[str, Any]:
        """Dict로 직렬화 (JSON 저장용)"""
        return {
            "belief_id": self.belief_id,
            "metric_id": self.metric_id,
            "context": self.context,
            "distribution": self.distribution,
            "confidence": self.confidence,
            "source": self.source,
            "observations": self.observations,
            "n_observations": self.n_observations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "lineage": self.lineage
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BeliefRecord":
        """Dict에서 복원"""
        return cls(
            belief_id=data["belief_id"],
            metric_id=data["metric_id"],
            context=data["context"],
            distribution=data["distribution"],
            confidence=data["confidence"],
            source=data["source"],
            observations=data.get("observations", []),
            n_observations=data.get("n_observations", 0),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            lineage=data.get("lineage", {})
        )

    def to_value_record(self) -> Dict[str, Any]:
        """ValueRecord 형식으로 변환 (value_store 저장용)

        BeliefRecord를 value_store에 저장할 때 사용.
        origin="prior" 또는 "learned"로 구분.

        Returns:
            ValueRecord 호환 dict
        """
        return {
            "value_id": f"VAL-{self.belief_id}",
            "metric_id": self.metric_id,
            "context": self.context,
            "point_estimate": None,  # Prior는 분포만 사용
            "distribution": self.distribution,
            "quality": {
                "literal_ratio": 0.0,  # Prior는 literal evidence 없음
                "spread_ratio": self._calculate_spread(),
                "confidence": self.confidence
            },
            "origin": "prior" if self.source in ["pattern_benchmark", "uninformative", "domain_expert"] else "learned",
            "lineage": self.lineage,
            "stored_at": self.updated_at
        }

    def _calculate_spread(self) -> float:
        """분포의 spread_ratio 계산 (간이 버전)

        Returns:
            spread_ratio (0~1+)
        """
        if self.distribution.get("type") == "normal":
            params = self.distribution.get("params", {})
            mu = params.get("mu", 0)
            sigma = params.get("sigma", 0)
            if mu > 0:
                return sigma / mu  # Coefficient of Variation
            return 0.0

        elif self.distribution.get("type") == "lognormal":
            # Lognormal은 sigma 파라미터가 spread
            params = self.distribution.get("params", {})
            return params.get("sigma", 0.5)

        elif self.distribution.get("type") == "uniform":
            # Uniform은 범위
            params = self.distribution.get("params", {})
            min_val = params.get("min", 0)
            max_val = params.get("max", 0)
            mean = (min_val + max_val) / 2
            if mean > 0:
                return (max_val - min_val) / (2 * mean)
            return 0.0

        else:
            # 기타 분포는 0.5 기본값
            return 0.5
