"""CMIS Evidence Engine

Evidence 수집 및 관리 엔진 (v2 개정판)

설계 원칙:
- Evidence-first, Prior-last
- Early Return (상위 tier 성공 시 즉시 반환)
- Graceful Degradation (부분 실패 허용)
- Source-agnostic Interface
- Comprehensive Lineage

아키텍처:
- EvidenceEngine: Facade (public API)
- EvidencePlanner: Plan 생성
- EvidenceExecutor: Plan 실행
- SourceRegistry: Source 관리
- EvidenceStore: 캐싱/저장
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .config import CMISConfig
from .types import (
    MetricRequest,
    EvidenceRequest,
    EvidenceRecord,
    EvidenceBundle,
    EvidenceMultiResult,
    EvidenceSufficiency,
    EvidenceSufficiencyResult,
    EvidencePolicy,
    SourceTier,
)


# ========================================
# Exceptions
# ========================================

class EvidenceEngineError(Exception):
    """Base exception for Evidence Engine"""
    pass


class SourceNotAvailableError(EvidenceEngineError):
    """Source 접근 불가 (API down, 네트워크 등)"""
    pass


class DataNotFoundError(EvidenceEngineError):
    """요청한 데이터 없음"""
    pass


class SourceTimeoutError(EvidenceEngineError):
    """Source timeout"""
    pass


class InsufficientEvidenceError(EvidenceEngineError):
    """모든 tier 시도 후에도 evidence 부족"""
    pass


# ========================================
# BaseDataSource (추상 인터페이스)
# ========================================

from abc import ABC, abstractmethod


class BaseDataSource(ABC):
    """DataSource 추상 인터페이스

    모든 connector는 이 인터페이스 구현 필수
    """

    def __init__(
        self,
        source_id: str,
        source_tier: SourceTier,
        capabilities: Dict[str, Any]
    ):
        """
        Args:
            source_id: Source 고유 ID
            source_tier: Tier
            capabilities: 제공 가능한 데이터 타입/도메인
        """
        self.source_id = source_id
        self.source_tier = source_tier
        self.capabilities = capabilities

    @abstractmethod
    def fetch(
        self,
        request: EvidenceRequest
    ) -> EvidenceRecord:
        """Evidence 수집

        Args:
            request: Evidence 요청

        Returns:
            EvidenceRecord

        Raises:
            SourceNotAvailableError: Source 접근 불가
            DataNotFoundError: 요청한 데이터 없음
            SourceTimeoutError: Timeout
        """
        pass

    @abstractmethod
    def can_handle(
        self,
        request: EvidenceRequest
    ) -> bool:
        """요청 처리 가능 여부

        Args:
            request: Evidence 요청

        Returns:
            처리 가능 여부

        기준:
            - capabilities와 request.required_capabilities 매칭
            - 도메인/지역 지원 여부
            - 데이터 타입 지원 여부
        """
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """Capability 반환"""
        return self.capabilities


# ========================================
# SourceRegistry
# ========================================

class SourceRegistry:
    """DataSource 레지스트리

    역할:
    - Source 등록/조회
    - Tier별 source 그룹화
    - Capability 기반 매칭
    """

    def __init__(self):
        """초기화"""
        self._sources: Dict[str, BaseDataSource] = {}
        self._sources_by_tier: Dict[str, List[BaseDataSource]] = {
            "official": [],
            "curated_internal": [],
            "commercial": [],
        }

    def register_source(
        self,
        source_id: str,
        source_tier: str,
        source_instance: BaseDataSource
    ):
        """Source 등록

        Args:
            source_id: Source 고유 ID (예: "DART", "KOSIS")
            source_tier: Tier (official/curated_internal/commercial)
            source_instance: BaseDataSource 구현체
        """
        self._sources[source_id] = source_instance

        if source_tier in self._sources_by_tier:
            self._sources_by_tier[source_tier].append(source_instance)

    def get_sources_by_tier(self, tier: str) -> List[BaseDataSource]:
        """Tier별 source 목록 반환"""
        return self._sources_by_tier.get(tier, [])

    def get_source(self, source_id: str) -> Optional[BaseDataSource]:
        """Source ID로 조회"""
        return self._sources.get(source_id)

    def find_capable_sources(
        self,
        request: EvidenceRequest
    ) -> List[BaseDataSource]:
        """요청을 처리 가능한 source 목록 반환

        Args:
            request: Evidence 요청

        Returns:
            can_handle() == True인 source 목록 (tier 순서)
        """
        capable = []

        for source in self._sources.values():
            if not source.can_handle(request):
                continue

            # Capability 매칭 체크
            if not self._match_capabilities(source, request):
                continue

            capable.append(source)

        # Tier 순서로 정렬
        tier_priority = {
            SourceTier.OFFICIAL: 1,
            SourceTier.CURATED_INTERNAL: 2,
            SourceTier.COMMERCIAL: 3,
        }
        capable.sort(key=lambda src: tier_priority.get(src.source_tier, 999))

        return capable

    def _match_capabilities(
        self,
        source: BaseDataSource,
        request: EvidenceRequest
    ) -> bool:
        """Source capability와 request 매칭

        체크:
        - provides: request.required_capabilities와 교집합
        - regions: request.context.region 지원
        """
        caps = source.get_capabilities()

        # 1. provides 체크
        provides = set(caps.get("provides", []))
        required = set(request.required_capabilities)

        # "*" wildcard 지원
        if "*" in provides:
            # wildcard source는 모든 요청 처리 가능
            pass
        elif required and not (provides & required):
            # 교집합 없음
            return False

        # 2. region 체크
        regions = caps.get("regions", [])
        request_region = request.context.get("region")

        if regions and request_region:
            if request_region not in regions and "*" not in regions:
                return False

        return True


# ========================================
# EvidencePlan
# ========================================

from dataclasses import dataclass, field


@dataclass
class EvidencePlan:
    """Evidence 수집 계획"""
    request: EvidenceRequest
    tier_groups: Dict[int, List[BaseDataSource]]
    # {1: [DART, KOSIS], 2: [...], 3: [...]}

    policy: EvidencePolicy
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ========================================
# EvidencePlanner
# ========================================

class EvidencePlanner:
    """Evidence 수집 계획 생성

    책임:
    - EvidenceRequest → EvidencePlan 생성
    - Tier/Source 우선순위 결정
    - Policy 기반 제약 적용
    """

    def __init__(
        self,
        source_registry: SourceRegistry,
        config: CMISConfig
    ):
        self.source_registry = source_registry
        self.config = config

    def build_plan(
        self,
        request: EvidenceRequest,
        policy: EvidencePolicy
    ) -> EvidencePlan:
        """Evidence 수집 계획 생성

        Args:
            request: Evidence 요청
            policy: 품질 정책

        Returns:
            EvidencePlan
        """
        # 1. Capability 기반 source 필터링
        capable_sources = self.source_registry.find_capable_sources(request)

        # 2. Policy 기반 tier 필터링
        allowed_sources = [
            src for src in capable_sources
            if src.source_tier.value in policy.allowed_tiers
        ]

        # 3. Tier별 그룹화 + 우선순위 정렬
        tier_groups = self._group_by_tier(allowed_sources)

        # 4. Metric별 우선순위 조정
        if request.metric_id:
            tier_groups = self._apply_metric_priority(
                request.metric_id,
                tier_groups
            )

        # 5. Plan 생성
        return EvidencePlan(
            request=request,
            tier_groups=tier_groups,
            policy=policy
        )

    def _group_by_tier(
        self,
        sources: List[BaseDataSource]
    ) -> Dict[int, List[BaseDataSource]]:
        """Tier별 source 그룹화

        Returns:
            {1: [DART, KOSIS], 2: [InternalDB], 3: [MarketResearch]}
        """
        tier_map = {
            SourceTier.OFFICIAL: 1,
            SourceTier.CURATED_INTERNAL: 2,
            SourceTier.COMMERCIAL: 3,
        }

        groups = {1: [], 2: [], 3: []}

        for src in sources:
            tier_num = tier_map.get(src.source_tier, 3)
            groups[tier_num].append(src)

        return groups

    def _apply_metric_priority(
        self,
        metric_id: str,
        tier_groups: Dict[int, List[BaseDataSource]]
    ) -> Dict[int, List[BaseDataSource]]:
        """Metric별 source 우선순위 조정

        예: MET-Revenue는 DART > Brokerage > Commercial 순서
        """
        # metrics_spec에서 direct_evidence_sources 순서 조회
        metrics = self.config.metrics
        metric_spec = metrics.get(metric_id)
        if not metric_spec:
            return tier_groups

        priority_sources = metric_spec.direct_evidence_sources

        # Tier 내부에서 priority_sources 순서로 정렬
        for tier_num in tier_groups:
            tier_groups[tier_num] = sorted(
                tier_groups[tier_num],
                key=lambda src: (
                    priority_sources.index(src.source_id)
                    if src.source_id in priority_sources
                    else 999
                )
            )

        return tier_groups


# ========================================
# EvidenceExecutor
# ========================================

class EvidenceExecutor:
    """Evidence 수집 실행

    책임:
    - Plan 실행 (tier별 source 호출)
    - Early Return 로직
    - Graceful Degradation
    - Retry/Timeout 관리
    """

    def __init__(self, source_registry: SourceRegistry):
        self.source_registry = source_registry

    def run(
        self,
        plan: EvidencePlan,
        policy: EvidencePolicy
    ) -> EvidenceBundle:
        """Plan 실행

        Args:
            plan: Evidence 수집 계획
            policy: 품질 정책

        Returns:
            EvidenceBundle
        """
        bundle = EvidenceBundle(request=plan.request)
        start_time = time.time()

        # Tier 1부터 순차 실행
        for tier_num in sorted(plan.tier_groups.keys()):
            sources = plan.tier_groups[tier_num]

            # Tier 내부 source 호출 (v1: 직렬, v2: 병렬 예정)
            for source in sources:
                # Timeout 체크
                elapsed = time.time() - start_time
                if elapsed > policy.max_total_time_seconds:
                    bundle.add_trace(
                        tier_num, source.source_id, "skipped",
                        reason="timeout"
                    )
                    break

                # Source 호출
                try:
                    # Optional: policy-aware fetch (Search v3 등에서 사용)
                    if hasattr(source, "fetch_with_policy"):
                        evidence = source.fetch_with_policy(plan.request, policy)  # type: ignore[attr-defined]
                    else:
                        evidence = source.fetch(plan.request)
                    bundle.add_evidence(evidence)
                    bundle.add_trace(
                        tier_num, source.source_id, "success",
                        time_ms=(time.time() - start_time) * 1000
                    )

                except (SourceNotAvailableError, DataNotFoundError) as e:
                    bundle.add_trace(
                        tier_num, source.source_id, "failed",
                        error=str(e)
                    )
                    continue  # Graceful degradation

                except Exception as e:
                    bundle.add_trace(
                        tier_num, source.source_id, "error",
                        error=str(e)
                    )
                    continue

            # Early Return 체크
            bundle.calculate_quality_summary()
            sufficiency = self._evaluate_sufficiency(bundle, policy)

            if sufficiency.status == EvidenceSufficiency.SUFFICIENT:
                break  # Early Return

            if sufficiency.status == EvidenceSufficiency.PARTIAL:
                if policy.best_effort_mode:
                    break  # PARTIAL도 허용

        # 실행 시간 기록
        bundle.execution_time_ms = (time.time() - start_time) * 1000

        return bundle

    def _evaluate_sufficiency(
        self,
        bundle: EvidenceBundle,
        policy: EvidencePolicy
    ) -> EvidenceSufficiencyResult:
        """Evidence 충분성 판단

        Returns:
            EvidenceSufficiencyResult
        """
        reasons = []
        summary = bundle.quality_summary

        # 1. literal_ratio 체크
        literal_ratio = summary.get("literal_ratio", 0.0)
        if literal_ratio < policy.min_literal_ratio:
            reasons.append(
                f"literal_ratio too low ({literal_ratio:.2f} < {policy.min_literal_ratio})"
            )

        # 2. spread_ratio 체크
        spread_ratio = summary.get("spread_ratio", 0.0)
        if spread_ratio > policy.max_spread_ratio:
            reasons.append(
                f"spread_ratio too high ({spread_ratio:.2f} > {policy.max_spread_ratio})"
            )

        # 3. 최소 source 개수
        num_sources = summary.get("num_sources", 0)
        if num_sources < 1:
            reasons.append("no sources")

        # 4. 상태 결정
        if not reasons:
            status = EvidenceSufficiency.SUFFICIENT
        elif num_sources >= 1 and literal_ratio >= 0.3:
            # 최소 기준은 충족 (부분 사용 가능)
            status = EvidenceSufficiency.PARTIAL
        else:
            status = EvidenceSufficiency.FAILED

        return EvidenceSufficiencyResult(
            status=status,
            reasons=reasons,
            summary=summary
        )


# ========================================
# EvidenceEngine (Facade)
# ========================================

class EvidenceEngine:
    """Evidence 수집 Facade

    책임:
    - Public API 제공
    - Planner/Executor/Store 조율
    - Policy 기반 제약 적용
    """

    def __init__(
        self,
        config: CMISConfig,
        source_registry: SourceRegistry,
        evidence_store: Optional[Any] = None  # EvidenceStore
    ):
        self.config = config
        self.source_registry = source_registry

        # Evidence Store
        if evidence_store is None:
            from .evidence_store import create_evidence_store
            evidence_store = create_evidence_store(backend_type="memory")

        self.evidence_store = evidence_store

        # 내부 컴포넌트
        self.planner = EvidencePlanner(source_registry, config)
        self.executor = EvidenceExecutor(source_registry)

    def fetch_for_metrics(
        self,
        metric_requests: List[MetricRequest],
        policy_ref: str = "reporting_strict",
        use_cache: bool = True
    ) -> EvidenceMultiResult:
        """Metric 평가를 위한 Evidence 수집

        Args:
            metric_requests: Metric 요청 목록
            policy_ref: 품질 정책 ID
            use_cache: 캐시 사용 여부 (기본 True)

        Returns:
            EvidenceMultiResult (metric별 EvidenceBundle)
        """
        # 1. Policy 로드
        policy = EvidencePolicy.from_config(policy_ref, self.config)

        # 2. Metric별로 처리
        bundles = {}
        cache_hits = 0

        for req in metric_requests:
            # 2.1 캐시 확인
            if use_cache:
                cached = self.evidence_store.get(
                    req,
                    max_age_seconds=86400  # 1일
                )

                if cached:
                    bundles[req.metric_id] = cached
                    cache_hits += 1
                    continue

            # 2.2 EvidenceRequest 생성
            evidence_request = self._metric_to_evidence_request(req)

            # 2.3 Plan 생성
            plan = self.planner.build_plan(evidence_request, policy)

            # 2.4 실행
            bundle = self.executor.run(plan, policy)

            # 2.5 캐시에 저장
            if use_cache:
                self.evidence_store.save(bundle)

            bundles[req.metric_id] = bundle

        # 3. 결과 생성
        return EvidenceMultiResult(
            bundles=bundles,
            execution_summary={
                "total_requests": len(metric_requests),
                "cache_hits": cache_hits,
                "cache_misses": len(metric_requests) - cache_hits,
                "total_time_ms": sum(
                    b.execution_time_ms for b in bundles.values()
                    if b.execution_time_ms
                )
            }
        )

    def fetch_for_reality_slice(
        self,
        scope: Dict[str, Any],
        as_of: str,
        policy_ref: str = "reporting_strict"
    ) -> List[EvidenceRecord]:
        """Reality Graph 구성을 위한 Evidence 수집 (개선)

        WorldEngine이 Reality Graph를 구성할 때 사용.
        Scope에 필요한 모든 Evidence 유형을 자동으로 수집.

        Args:
            scope: {"domain_id": "...", "region": "...", "segment": "..."}
            as_of: 기준 시점 (year)
            policy_ref: 정책

        Returns:
            EvidenceRecord 리스트 (Actor, MoneyFlow, State 관련)
        """
        domain_id = scope.get("domain_id", "")
        region = scope.get("region", "KR")
        segment = scope.get("segment")

        # 1. 모든 Source에게 "이 scope에서 뭘 제공할 수 있나요?" 물어보기
        # (하드코딩 대신 동적 발견)

        # Scope 기반 범용 EvidenceRequest 생성
        scope_request = EvidenceRequest(
            request_id=f"reality-scope-{uuid.uuid4().hex[:8]}",
            request_type="reality_slice",
            context={
                "domain_id": domain_id,
                "region": region,
                "segment": segment,
                "year": as_of
            },
            required_capabilities=["*"]  # 모든 capability
        )

        # 2. Capable sources 찾기
        capable_sources = self.source_registry.find_capable_sources(scope_request)

        if not capable_sources:
            return []

        # 3. 각 Source에서 가능한 모든 Evidence 수집
        all_evidence = []

        for source in capable_sources:
            # Source가 제공 가능한 Evidence 유형 확인
            provides = source.get_capabilities().get("provides", [])

            # 각 capability에 대해 Evidence 수집 시도
            for capability in provides:
                # Capability → Metric 매핑 (동적)
                metric_id = self._capability_to_metric(capability, scope)

                if not metric_id:
                    continue

                # MetricRequest 생성
                metric_req = MetricRequest(
                    metric_id=metric_id,
                    context={
                        "domain_id": domain_id,
                        "region": region,
                        "segment": segment,
                        "year": as_of
                    }
                )

                try:
                    # 개별 수집 (Graceful degradation)
                    result = self.fetch_for_metrics([metric_req], policy_ref)

                    for bundle in result.bundles.values():
                        all_evidence.extend(bundle.evidence_list)

                except Exception as e:
                    # 실패해도 계속 진행
                    print(f"Warning: Failed {capability} from {source.source_id}: {e}")
                    continue

        return all_evidence

    def _capability_to_metric(
        self,
        capability: str,
        scope: Dict[str, Any]
    ) -> Optional[str]:
        """Capability → Metric ID 매핑 (동적, cmis.yaml 기반)

        Args:
            capability: Source capability (예: "population_by_age")
            scope: Scope 정보

        Returns:
            Metric ID or None
        """
        # cmis.yaml metrics_spec에서 동적 생성
        if not hasattr(self, '_capability_mapping_cache'):
            self._capability_mapping_cache = self._build_capability_mapping()

        return self._capability_mapping_cache.get(capability)

    def _build_capability_mapping(self) -> Dict[str, str]:
        """cmis.yaml metrics_spec에서 Capability → Metric 매핑 동적 생성

        단일 진실의 원천: cmis.yaml

        Returns:
            {capability: metric_id}
        """
        mapping = {}

        # metrics_spec에서 추출
        for metric_id, spec in self.config.metrics.items():
            # direct_evidence_sources가 capability 리스트
            sources = spec.direct_evidence_sources

            for source_capability in sources:
                # 첫 번째 매핑 우선 (중복 시)
                if source_capability not in mapping:
                    mapping[source_capability] = metric_id

        # Fallback: 일반적인 매핑 (cmis.yaml에 없을 경우)
        fallback = {
            "population_by_age": "MET-N_customers",
            "household_income_distribution": "MET-N_customers",
            "market_data": "MET-TAM",
            "long_tail_facts": "MET-TAM"
        }

        for cap, metric in fallback.items():
            if cap not in mapping:
                mapping[cap] = metric

        return mapping


    def _metric_to_evidence_request(
        self,
        metric_req: MetricRequest
    ) -> EvidenceRequest:
        """MetricRequest → EvidenceRequest 변환"""
        # metrics_spec에서 direct_evidence_sources 조회
        metrics = self.config.metrics
        metric_spec = metrics.get(metric_req.metric_id)

        required_caps = metric_spec.direct_evidence_sources if metric_spec else []

        return EvidenceRequest(
            request_id=f"REQ-{metric_req.metric_id}-{uuid.uuid4().hex[:8]}",
            request_type="metric",
            metric_id=metric_req.metric_id,
            context=metric_req.context,
            required_capabilities=required_caps,
            quality_requirements={}
        )
