# Evidence Engine 설계안 개정 (v1 → v2)

**작성일**: 2025-12-09
**이전 버전**: Evidence_Engine_Core_Design.md
**개정 사유**: 아키텍처 리뷰 피드백 반영

---

## 개정 요약

### 핵심 변경사항

| 항목 | v1 설계 | v2 개정 | 이유 |
|------|---------|---------|------|
| **아키텍처** | EvidenceEngine 단일 클래스 | **Planner/Executor/Store/Policy 분리** | 책임 분리, 확장성 |
| **다중 Metric** | `List[MetricRequest] → EvidenceBundle` | `→ EvidenceMultiResult` | Metric별 bundle 필요 |
| **Prior 처리** | Tier 4/5로 포함 | **ValueEngine으로 분리** | Evidence vs Prior 경계 명확화 |
| **충분성 판단** | `bool` | **EvidenceSufficiency enum** | SUFFICIENT/PARTIAL/FAILED 구분 |
| **Policy 연계** | 독립 정의 | **config-driven (cmis.yaml)** | YAML과 코드 일관성 |
| **Tier 구조** | 5 tier | **3 tier + ValueEngine Prior** | official/curated/commercial만 |

### 유지되는 핵심 원칙

```
✓ Evidence-first, Prior-last
✓ Early Return (v7 85% Direct)
✓ Graceful Degradation
✓ Source-agnostic Interface
✓ Comprehensive Lineage
```

---

## 1. 개정된 아키텍처

### 1.1 전체 구조 (Planner/Executor/Store/Policy)

```
┌─────────────────────────────────────────────────────────────┐
│                    EvidenceEngine (Facade)                  │
│  ┌───────────────────────────────────────────────────┐     │
│  │  fetch_for_metrics(requests) → EvidenceMultiResult│     │
│  │  fetch_for_reality_slice(scope) → EvidenceBundle │     │
│  └───────────────────────────────────────────────────┘     │
│                           │                                 │
│              ┌────────────┼────────────┐                   │
│              ▼            ▼            ▼                   │
│      ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│      │ Planner  │  │ Executor │  │  Store   │            │
│      │ (plan)   │  │  (run)   │  │ (cache)  │            │
│      └──────────┘  └──────────┘  └──────────┘            │
│              │                                              │
│              ▼                                              │
│      ┌──────────────┐                                      │
│      │ PolicyEngine │ ← cmis.yaml quality_profiles        │
│      └──────────────┘                                      │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │    SourceRegistry            │
        │  ┌────────────────────────┐  │
        │  │ Tier 1: official       │  │ ← DART, KOSIS
        │  │ Tier 2: curated        │  │ ← 내부 검증 DB
        │  │ Tier 3: commercial     │  │ ← web_search (공개 웹에서 수집)
        │  └────────────────────────┘  │
        └──────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │    BaseDataSource            │
        │  (추상 인터페이스)            │
        └──────────────────────────────┘
```

**Prior/LLM 처리는 ValueEngine으로 분리**:
```
EvidenceEngine → empirical evidence만
ValueEngine.prior_estimation → structured_estimation + llm_baseline
```

### 1.2 핵심 클래스 역할

**EvidenceEngine (Facade)**
- Public API 제공
- Planner/Executor/Store 조율

**EvidencePlanner**
- MetricRequest → EvidencePlan 생성
- Tier/Source 우선순위 결정
- Policy 기반 제약 적용

**EvidenceExecutor**
- Plan 실행 (tier별 source 호출)
- Graceful Degradation
- Retry/Timeout 관리

**EvidenceStore**
- 캐시/영구 저장
- TTL 관리
- Lineage 추적

**PolicyEngine** (기존 CMIS 컴포넌트)
- quality_profiles 로드
- Tier 허용 여부 결정

---

## 2. 주요 타입 정의 개정

### 2.1 EvidenceMultiResult (신규)

**문제**: v1에서는 `List[MetricRequest] → EvidenceBundle` 구조로 인해 metric별 bundle 구분 불가

**해결**:
```python
from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime

@dataclass
class EvidenceMultiResult:
    """여러 Metric의 Evidence 묶음

    ValueEngine이 요청한 여러 MetricRequest에 대한
    Metric별 EvidenceBundle 컬렉션
    """
    bundles: Dict[str, EvidenceBundle]
    # key: metric_id (예: "MET-Revenue")
    # value: 해당 metric의 EvidenceBundle

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

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
```

### 2.2 EvidenceSufficiency (신규)

**문제**: v1에서는 `_evaluate_sufficiency() → bool`로 이분법적 판단만 가능

**해결**:
```python
from enum import Enum

class EvidenceSufficiency(Enum):
    """Evidence 충분성 상태"""
    SUFFICIENT = "sufficient"     # 그대로 사용 가능
    PARTIAL = "partial"           # 부족하지만 사용 가능
    FAILED = "failed"             # 사용 불가

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
```

### 2.3 EvidencePolicy (개정)

**문제**: v1 설계와 cmis.yaml의 quality_profiles 불일치

**해결**: config-driven 구조
```python
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
    def from_config(cls, policy_id: str, config: CMISConfig) -> "EvidencePolicy":
        """cmis.yaml에서 policy 로드

        Args:
            policy_id: "reporting_strict" 등
            config: CMISConfig

        Returns:
            EvidencePolicy
        """
        profile = config.policies["quality_profiles"][policy_id]

        allowed_tiers = ["official", "curated_internal", "commercial"]
        if profile.get("allow_prior", False):
            # Prior 허용 시에도 EvidenceEngine에서는 처리 안 함
            # → ValueEngine에서 prior_estimation 호출
            pass

        return cls(
            policy_id=policy_id,
            min_literal_ratio=profile["min_literal_ratio"],
            max_spread_ratio=profile["max_spread_ratio"],
            allow_prior=profile.get("allow_prior", False),
            allowed_tiers=allowed_tiers,
            best_effort_mode=(policy_id == "exploration_friendly")
        )
```

### 2.4 EvidenceValueKind (신규)

**문제**: v1의 `value: Any`는 타입 구분 불명확

**해결**:
```python
class EvidenceValueKind(Enum):
    """Evidence 값 타입"""
    RAW_DOCUMENT = "raw_document"      # 원문 문서
    NUMERIC = "numeric"                # 단일 숫자
    TABLE = "table"                    # 표/다중 값
    EXTRACTED_METRIC = "extracted_metric"  # 문서에서 추출된 metric
    RANGE = "range"                    # 범위 (min, max)
    DISTRIBUTION = "distribution"      # 분포

@dataclass
class EvidenceRecord:
    """개별 Evidence 레코드 (개정)"""
    evidence_id: str
    source_tier: str
    source_id: str

    # 데이터 (타입 명확화)
    value: Any
    value_kind: EvidenceValueKind  # 타입 명시
    schema_ref: Optional[str] = None
    # 예: "dart_filings_v1", "market_research_report_v1"

    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    lineage: Dict[str, Any] = field(default_factory=dict)
```

### 2.5 EvidenceBundle (개정)

**변경**: debug_trace 필드 추가
```python
@dataclass
class EvidenceBundle:
    """여러 source의 Evidence 묶음 (개정)"""
    request: EvidenceRequest
    records: List[EvidenceRecord] = field(default_factory=list)
    quality_summary: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    execution_time_ms: Optional[float] = None

    # 신규: Debug trace (MEM-store 연계)
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
```

---

## 3. 핵심 클래스 상세 설계 (개정)

### 3.1 EvidenceEngine (Facade)

```python
class EvidenceEngine:
    """Evidence 수집 Facade (개정)

    책임:
    - Public API 제공
    - Planner/Executor/Store 조율
    - Policy 기반 제약 적용
    """

    def __init__(
        self,
        config: CMISConfig,
        source_registry: SourceRegistry,
        evidence_store: EvidenceStore,
        policy_engine: PolicyEngine  # 신규: PolicyEngine 주입
    ):
        self.config = config
        self.source_registry = source_registry
        self.evidence_store = evidence_store
        self.policy_engine = policy_engine

        # 내부 컴포넌트
        self.planner = EvidencePlanner(source_registry, config)
        self.executor = EvidenceExecutor(source_registry)

    def fetch_for_metrics(
        self,
        metric_requests: List[MetricRequest],
        policy_ref: str = "reporting_strict"
    ) -> EvidenceMultiResult:
        """Metric 평가를 위한 Evidence 수집 (개정)

        Args:
            metric_requests: Metric 요청 목록
            policy_ref: 품질 정책 ID

        Returns:
            EvidenceMultiResult (metric별 EvidenceBundle)
        """
        # 1. Policy 로드
        policy = EvidencePolicy.from_config(policy_ref, self.config)

        # 2. Metric별로 처리
        bundles = {}

        for req in metric_requests:
            # 2.1 캐시 확인
            cached = self.evidence_store.get(
                req,
                max_age_seconds=86400  # 1일
            )

            if cached:
                bundles[req.metric_id] = cached
                continue

            # 2.2 Plan 생성
            evidence_request = self._metric_to_evidence_request(req)
            plan = self.planner.build_plan(evidence_request, policy)

            # 2.3 실행
            bundle = self.executor.run(plan, policy)

            # 2.4 저장
            self.evidence_store.save(bundle)
            bundles[req.metric_id] = bundle

        # 3. 결과 생성
        return EvidenceMultiResult(bundles=bundles)

    def _metric_to_evidence_request(
        self,
        metric_req: MetricRequest
    ) -> EvidenceRequest:
        """MetricRequest → EvidenceRequest 변환"""
        # metrics_spec에서 direct_evidence_sources 조회
        metric_spec = self.config.metrics.get(metric_req.metric_id)

        required_caps = []
        if metric_spec:
            required_caps = metric_spec.get("direct_evidence_sources", [])

        return EvidenceRequest(
            request_id=f"REQ-{metric_req.metric_id}-{uuid.uuid4().hex[:8]}",
            request_type="metric",
            metric_id=metric_req.metric_id,
            context=metric_req.context,
            required_capabilities=required_caps,
            quality_requirements={}
        )
```

### 3.2 EvidencePlanner (신규)

```python
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
            policy=policy,
            created_at=datetime.utcnow().isoformat()
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
            "official": 1,
            "curated_internal": 2,
            "commercial": 3
        }

        groups = {1: [], 2: [], 3: []}

        for src in sources:
            tier_num = tier_map.get(src.source_tier.value, 3)
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
        metric_spec = self.config.metrics.get(metric_id)
        if not metric_spec:
            return tier_groups

        priority_sources = metric_spec.get("direct_evidence_sources", [])

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

@dataclass
class EvidencePlan:
    """Evidence 수집 계획"""
    request: EvidenceRequest
    tier_groups: Dict[int, List[BaseDataSource]]
    # {1: [DART, KOSIS], 2: [...], 3: [...]}

    policy: EvidencePolicy
    created_at: str
```

### 3.3 EvidenceExecutor (신규)

```python
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
        """Evidence 충분성 판단 (개정)

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
```

---

## 4. Prior 처리 분리 (옵션 A 채택)

### 4.1 설계 결정

**문제**: v1에서는 Tier 4/5에 structured_estimation/llm_baseline을 두어 경계 모호

**해결**: **EvidenceEngine = empirical evidence만** 처리

```
EvidenceEngine:
  - Tier 1: official (DART, KOSIS, Gov Stats)
  - Tier 2: curated_internal (내부 검증 DB)
  - Tier 3: commercial (web_search: 공개 리포트/문서/기사)

ValueEngine.prior_estimation:
  - Pattern 기반 추정 (PatternEngine 호출)
  - Belief 기반 추정 (BeliefEngine 호출)
  - LLM baseline (웹검색 + LLM)
```

### 4.2 EvidenceRecord 태깅

Prior 결과를 evidence_store에 저장할 경우에도 명확한 태깅:

```python
# ValueEngine에서 prior 결과를 EvidenceRecord로 저장 시
evidence_record = EvidenceRecord(
    evidence_id="EVD-...",
    source_tier="prior",  # ← 명확한 구분
    source_id="pattern_engine",
    value=estimated_value,
    value_kind=EvidenceValueKind.EXTRACTED_METRIC,
    metadata={
        "kind": "prior",
        "method": "pattern_based",
        "derived_from": ["PAT-subscription_model", "MET-ARPU"]
    },
    confidence=0.6,
    lineage={
        "engine": "value_engine",
        "stage": "prior_estimation"
    }
)
```

### 4.3 EvidencePolicy와 연계

```python
# reporting_strict: allow_prior=False
# → ValueEngine이 prior_estimation 단계 스킵

# decision_balanced: allow_prior=True
# → ValueEngine이 prior_estimation 실행

# EvidenceEngine은 항상 empirical만 수집
```

---

## 5. SourceRegistry 강화

### 5.1 Capability 기반 라우팅

```python
class SourceRegistry:
    """DataSource 레지스트리 (강화)"""

    def find_capable_sources(
        self,
        request: EvidenceRequest
    ) -> List[BaseDataSource]:
        """Capability 기반 source 필터링

        Args:
            request: Evidence 요청

        Returns:
            처리 가능한 source 목록 (tier 순서)
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
        capable.sort(key=lambda src: self._tier_priority(src.source_tier))

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
        - data_types: 지원 데이터 타입
        """
        caps = source.get_capabilities()

        # 1. provides 체크
        provides = set(caps.get("provides", []))
        required = set(request.required_capabilities)

        if required and not (provides & required):
            return False

        # 2. region 체크
        regions = caps.get("regions", [])
        request_region = request.context.get("region")

        if regions and request_region:
            if request_region not in regions and "*" not in regions:
                return False

        return True
```

---

## 6. EvidenceStore 캐시 전략

### 6.1 캐시 키 정의

```python
class EvidenceStore:
    """Evidence 저장소 (개정)"""

    def _build_cache_key(
        self,
        request: EvidenceRequest
    ) -> str:
        """캐시 키 생성

        키 구성:
        - metric_id (or entity_type)
        - context (domain_id, region, year 등)
        - quality_requirements (normalize)
        """
        if request.metric_id:
            key_base = f"metric:{request.metric_id}"
        else:
            key_base = f"entity:{request.entity_type}"

        # Context 정규화 (순서 무관)
        context_items = sorted(request.context.items())
        context_str = "|".join(f"{k}={v}" for k, v in context_items)

        # 최종 키
        cache_key = f"{key_base}|{context_str}"

        return hashlib.sha256(cache_key.encode()).hexdigest()[:16]

    def get(
        self,
        request: Union[EvidenceRequest, MetricRequest],
        max_age_seconds: Optional[int] = None
    ) -> Optional[EvidenceBundle]:
        """캐시/저장소에서 조회 (개정)

        Args:
            request: Evidence/Metric 요청
            max_age_seconds: 최대 허용 age (TTL)

        Returns:
            저장된 EvidenceBundle (없거나 만료되면 None)
        """
        # MetricRequest → EvidenceRequest 변환
        if isinstance(request, MetricRequest):
            request = self._metric_to_evidence_request(request)

        cache_key = self._build_cache_key(request)

        # 1. 메모리 캐시 확인
        if cache_key in self._cache:
            cached = self._cache[cache_key]

            # TTL 체크
            if max_age_seconds:
                age = self._calculate_age(cached)
                if age > max_age_seconds:
                    del self._cache[cache_key]
                    return None

            return cached

        # 2. 영구 저장소 조회 (TODO: 구현)
        # stored = self.storage.get(cache_key)
        # ...

        return None
```

---

## 7. 병렬 호출 훅 (v2 예정)

v1 구현은 직렬, v2에서 병렬 도입 예정:

```python
# v2 예정 (현재는 TODO)
class EvidenceExecutor:
    def run(self, plan, policy):
        # Tier 내부 병렬 실행
        for tier_num in sorted(plan.tier_groups.keys()):
            sources = plan.tier_groups[tier_num]

            # v2: asyncio 또는 ThreadPoolExecutor 사용
            # results = await asyncio.gather(
            #     *[self._fetch_from_source(src, plan.request) for src in sources]
            # )

            # v1: 직렬
            for source in sources:
                ...
```

---

## 8. 변경 이력 및 다음 단계

### 8.1 v1 → v2 변경 요약

| 항목 | 변경 | 파일 |
|------|------|------|
| 타입 | EvidenceMultiResult, EvidenceSufficiency 추가 | types.py |
| 아키텍처 | Planner/Executor 분리 | evidence_engine.py |
| Policy | config-driven, allow_prior 명확화 | config.py, types.py |
| Prior | Tier 4/5 제거, ValueEngine으로 분리 | evidence_engine.py |
| 캐시 | 캐시 키/TTL 전략 명시 | evidence_store.py |
| Trace | debug_trace 필드 추가 | types.py |

### 8.2 구현 우선순위 (v1)

**Phase 1**: 타입 정의 (1-2일)
- [ ] EvidenceMultiResult
- [ ] EvidenceSufficiency
- [ ] EvidencePolicy (config-driven)
- [ ] EvidenceValueKind

**Phase 2**: 핵심 클래스 (3-5일)
- [ ] EvidencePlanner
- [ ] EvidenceExecutor
- [ ] EvidenceEngine (Facade)
- [ ] SourceRegistry 강화

**Phase 3**: Connector 구현 (2-3일)
- [ ] DARTSource (기존 dart_connector 통합)
- [ ] OfficialSource 스텁 (KOSIS 등)
- [ ] CommercialSource 스텁

**Phase 4**: 통합 및 테스트 (2-3일)
- [ ] EvidenceStore 구현
- [ ] ValueEngine 연동
- [ ] Unit/Integration tests

### 8.3 v2 추가 개선 (향후)

- [ ] Tier 내부 병렬 실행 (asyncio)
- [ ] Rate limiting
- [ ] Partial cache reuse
- [ ] MEM-store trace 연계

---

**개정 완료**: 2025-12-09
**다음 문서**: Evidence_Engine_Implementation_v1.md (구현 가이드)
