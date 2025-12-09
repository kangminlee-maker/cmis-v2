# Evidence Engine 핵심 설계안

**작성일**: 2025-12-09
**목적**: Evidence Engine 핵심 클래스 구조 설계 (확장성, 견고성 중심)

---

## 1. 설계 철학

### 핵심 원칙 (v7 계승 + v9 확장)

```
1. Evidence-first, Prior-last
   - 증거가 있으면 증거 사용
   - 추정은 최후 수단

2. Early Return (v7 85% Direct 전략)
   - 상위 tier에서 충분한 증거 확보 시 즉시 반환
   - 불필요한 하위 tier 호출 방지 (비용/시간 절약)

3. Graceful Degradation
   - 상위 tier 실패 시 자연스럽게 하위 tier로 전환
   - 부분 실패 허용 (일부 source 실패해도 계속 진행)

4. Source-agnostic Interface
   - BaseDataSource 추상화로 connector 교체 가능
   - 새 source 추가 시 기존 코드 수정 불필요

5. Comprehensive Lineage
   - 모든 Evidence의 출처/품질/시간 추적
   - 재현 가능성 보장
```

### 외부 의존성 격리

```
- DART API 장애 → 다른 source로 대체
- LLM Provider 변경 → BaseDataSource 구현만 교체
- 새 정부통계 추가 → OfficialSource 확장
```

---

## 2. 아키텍처 계층

```
┌───────────────────────────────────────────────────────────────┐
│                    EvidenceEngine                             │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  fetch_for_metrics(metric_requests, policy)         │     │
│  │  fetch_for_reality_slice(scope, as_of)              │     │
│  └─────────────────────────────────────────────────────┘     │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐     │
│  │        _fetch_with_early_return(request)            │     │
│  │        - Tier 1 → Tier 2 → ... → Tier 5             │     │
│  │        - 충분한 evidence 확보 시 Early Return        │     │
│  └─────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────────┐
│                  SourceRegistry                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  register_source(source_id, tier, source_instance)  │     │
│  │  get_sources_by_tier(tier) → List[DataSource]       │     │
│  │  get_source(source_id) → DataSource                 │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  Tier 관리:                                                   │
│  - Tier 1: official (DART, KOSIS, Gov Stats)                 │
│  - Tier 2: curated_internal (내부 검증 DB)                    │
│  - Tier 3: commercial (Market Research, Consulting)          │
│  - Tier 4: structured_estimation (Pattern/공식 기반)          │
│  - Tier 5: llm_baseline (웹검색 + LLM)                        │
└───────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────────┐
│              BaseDataSource (Abstract)                        │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  fetch(request: EvidenceRequest) → EvidenceBundle   │     │
│  │  can_handle(request) → bool                         │     │
│  │  get_capabilities() → Dict                          │     │
│  └─────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────┘
           ↓              ↓              ↓              ↓
    ┌─────────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │Official │    │Curated   │   │Commercial│   │LLMBase   │
    │Source   │    │Source    │   │Source    │   │lineSource│
    └─────────┘    └──────────┘   └──────────┘   └──────────┘
```

---

## 3. 핵심 클래스 상세 설계

### 3.1 EvidenceEngine (Orchestrator)

**역할**:
- 상위 API 제공 (fetch_for_metrics, fetch_for_reality_slice)
- Early Return 로직 관리
- SourceRegistry와 EvidenceStore 조율

**인터페이스**:
```python
class EvidenceEngine:
    """Evidence 수집 및 관리 엔진
    
    설계 원칙:
    - Evidence-first, Prior-last
    - Early Return (상위 tier 성공 시 즉시 반환)
    - Graceful Degradation (tier별 fallback)
    - Source-agnostic (BaseDataSource 추상화)
    """
    
    def __init__(
        self,
        config: CMISConfig,
        source_registry: SourceRegistry,
        evidence_store: EvidenceStore
    ):
        """
        Args:
            config: CMIS 설정
            source_registry: DataSource 레지스트리
            evidence_store: Evidence 저장소
        """
    
    def fetch_for_metrics(
        self,
        metric_requests: List[MetricRequest],
        policy_ref: str = "reporting_strict"
    ) -> EvidenceBundle:
        """Metric 평가를 위한 Evidence 수집
        
        Args:
            metric_requests: Metric 요청 목록
            policy_ref: 품질 정책 (reporting_strict/decision_balanced/exploration_friendly)
        
        Returns:
            EvidenceBundle (수집된 모든 Evidence)
        
        알고리즘:
            1. 각 MetricRequest를 EvidenceRequest로 변환
            2. Tier 1부터 순차적으로 fetch 시도
            3. 충분한 evidence 확보 시 Early Return
            4. 모든 tier 시도 후에도 부족하면 경고 포함 반환
        """
    
    def fetch_for_reality_slice(
        self,
        scope: Dict[str, Any],
        as_of: str
    ) -> EvidenceBundle:
        """Reality Graph 구성을 위한 Evidence 수집
        
        Args:
            scope: 시장/도메인 범위 (domain_id, region, segment 등)
            as_of: 기준 시점
        
        Returns:
            EvidenceBundle
        
        알고리즘:
            1. scope를 기반으로 필요한 Evidence 유형 결정
            2. Actor/MoneyFlow/State 정보를 위한 EvidenceRequest 생성
            3. fetch_for_metrics와 동일한 Early Return 로직
        """
    
    def _fetch_with_early_return(
        self,
        request: EvidenceRequest,
        policy: EvidencePolicy
    ) -> EvidenceBundle:
        """Early Return 로직 구현
        
        Args:
            request: Evidence 요청
            policy: 품질 정책
        
        Returns:
            EvidenceBundle
        
        알고리즘:
            1. Tier 1부터 순차 시도
            2. 각 tier에서 수집된 evidence 품질 평가
            3. policy.min_literal_ratio 충족 시 Early Return
            4. 충족 못하면 다음 tier 시도
            5. 모든 tier 소진 시 best-effort 반환
        """
    
    def _evaluate_sufficiency(
        self,
        bundle: EvidenceBundle,
        policy: EvidencePolicy
    ) -> bool:
        """Evidence 충분성 판단
        
        Args:
            bundle: 수집된 Evidence
            policy: 품질 정책
        
        Returns:
            충분한지 여부
        
        기준:
            - literal_ratio >= policy.min_literal_ratio
            - spread_ratio <= policy.max_spread_ratio
            - hard_constraint 위반 없음
        """
```

**핵심 로직: Early Return**
```python
# Pseudo-code
for tier in [1, 2, 3, 4, 5]:
    sources = source_registry.get_sources_by_tier(tier)
    
    for source in sources:
        if not source.can_handle(request):
            continue
        
        try:
            evidence = source.fetch(request)
            bundle.add_evidence(evidence)
            
            # Early Return 조건 체크
            if self._evaluate_sufficiency(bundle, policy):
                logger.info(f"Early Return at Tier {tier}")
                return bundle
        
        except Exception as e:
            logger.warning(f"Source {source.id} failed: {e}")
            continue  # Graceful degradation

# 모든 tier 소진
logger.warning("All tiers exhausted, returning best-effort")
return bundle
```

---

### 3.2 SourceRegistry (Source 관리)

**역할**:
- DataSource 등록/관리
- Tier별 source 그룹화
- Source 라우팅

**인터페이스**:
```python
class SourceRegistry:
    """DataSource 레지스트리
    
    역할:
    - Source 등록/조회
    - Tier별 source 그룹화
    - Source capability 매칭
    """
    
    def __init__(self):
        """초기화"""
        self._sources: Dict[str, DataSource] = {}
        self._sources_by_tier: Dict[str, List[DataSource]] = {
            "official": [],
            "curated_internal": [],
            "commercial": [],
            "structured_estimation": [],
            "llm_baseline": [],
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
            source_tier: Tier (official/curated_internal/...)
            source_instance: BaseDataSource 구현체
        """
    
    def get_sources_by_tier(self, tier: str) -> List[BaseDataSource]:
        """Tier별 source 목록 반환"""
    
    def get_source(self, source_id: str) -> Optional[BaseDataSource]:
        """Source ID로 조회"""
    
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
```

**확장성**: 새 source 추가
```python
# 새 source 추가 예시
new_source = MyCustomSource(api_key="...")
registry.register_source(
    source_id="MyCustom",
    source_tier="commercial",
    source_instance=new_source
)
# → 기존 코드 수정 없이 자동 통합
```

---

### 3.3 BaseDataSource (추상 인터페이스)

**역할**:
- 모든 DataSource의 공통 인터페이스
- Source-agnostic 설계 보장
- 외부 의존성 격리

**인터페이스**:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class SourceTier(Enum):
    """Source tier 정의"""
    OFFICIAL = "official"
    CURATED_INTERNAL = "curated_internal"
    COMMERCIAL = "commercial"
    STRUCTURED_ESTIMATION = "structured_estimation"
    LLM_BASELINE = "llm_baseline"


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
    ) -> EvidenceBundle:
        """Evidence 수집
        
        Args:
            request: Evidence 요청
        
        Returns:
            EvidenceBundle
        
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
    
    def _build_evidence_record(
        self,
        value: Any,
        confidence: float,
        metadata: Dict[str, Any]
    ) -> EvidenceRecord:
        """EvidenceRecord 생성 헬퍼
        
        Args:
            value: 값
            confidence: 신뢰도 (0.0 ~ 1.0)
            metadata: 메타데이터
        
        Returns:
            EvidenceRecord
        """
        return EvidenceRecord(
            evidence_id=self._generate_evidence_id(),
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=value,
            confidence=confidence,
            metadata=metadata,
            retrieved_at=datetime.utcnow().isoformat()
        )
```

**확장 예시**: DART Source
```python
class DARTSource(BaseDataSource):
    """DART API connector"""
    
    def __init__(self, api_key: str):
        super().__init__(
            source_id="DART",
            source_tier=SourceTier.OFFICIAL,
            capabilities={
                "provides": ["financial_statements", "company_filings"],
                "regions": ["KR"],
                "data_types": ["numeric", "categorical"]
            }
        )
        self.api_key = api_key
        self.connector = DARTConnector(api_key)  # 기존 dart_connector.py 재사용
    
    def fetch(self, request: EvidenceRequest) -> EvidenceBundle:
        """DART에서 Evidence 수집"""
        # DARTConnector 호출 + EvidenceRecord 생성
        ...
    
    def can_handle(self, request: EvidenceRequest) -> bool:
        """DART가 처리 가능한지 확인"""
        required_caps = request.required_capabilities
        
        # 지역 확인
        if request.context.get("region") != "KR":
            return False
        
        # 데이터 타입 확인
        if not any(cap in self.capabilities["provides"] for cap in required_caps):
            return False
        
        return True
```

---

### 3.4 EvidenceRequest / EvidenceBundle / EvidenceRecord (타입 정의)

**설계 원칙**:
- MetricRequest → EvidenceRequest 변환
- EvidenceBundle: 여러 source의 evidence 묶음
- EvidenceRecord: 개별 evidence 레코드

**타입 정의**:
```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class EvidenceRequest:
    """Evidence 수집 요청
    
    MetricRequest에서 변환되거나
    Reality Graph용으로 직접 생성
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
    evidence_id: str  # "EVD-{uuid}"
    source_tier: str  # "official", "commercial", etc.
    source_id: str  # "DART", "KOSIS", etc.
    
    # 데이터
    value: Any  # 숫자, 문자열, 딕셔너리 등
    value_type: str = "unknown"  # "numeric", "categorical", "range", "distribution"
    
    # 품질
    confidence: float = 0.0  # 0.0 ~ 1.0
    
    # 메타데이터
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 예: {"subject": "...", "year": 2024, "url": "..."}
    
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Lineage
    lineage: Dict[str, Any] = field(default_factory=dict)
    # 예: {"query": "...", "response_time_ms": 123}


@dataclass
class EvidenceBundle:
    """여러 source의 Evidence 묶음
    
    EvidenceEngine.fetch_for_metrics()의 반환값
    """
    request: EvidenceRequest
    
    records: List[EvidenceRecord] = field(default_factory=list)
    
    # 집계 품질 지표
    quality_summary: Dict[str, Any] = field(default_factory=dict)
    # 예: {"literal_ratio": 0.8, "spread_ratio": 0.2, "num_sources": 3}
    
    # 메타데이터
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    execution_time_ms: Optional[float] = None
    
    def add_evidence(self, record: EvidenceRecord):
        """Evidence 추가"""
        self.records.append(record)
    
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
```

---

### 3.5 EvidenceStore (저장/조회/캐싱)

**역할**:
- Evidence 영구 저장
- 중복 조회 방지 (캐싱)
- Lineage 관리

**인터페이스**:
```python
class EvidenceStore:
    """Evidence 저장소
    
    역할:
    - Evidence 영구 저장 (EvidenceRecord → evidence_store)
    - 캐싱 (동일 요청 재사용)
    - Lineage 추적
    """
    
    def __init__(self, storage_backend: Any):
        """
        Args:
            storage_backend: 저장소 백엔드 (SQLite, PostgreSQL, S3 등)
        """
        self.storage = storage_backend
        self._cache: Dict[str, EvidenceBundle] = {}
    
    def save(self, bundle: EvidenceBundle):
        """EvidenceBundle 저장
        
        Args:
            bundle: 저장할 EvidenceBundle
        """
    
    def get(
        self,
        request: EvidenceRequest,
        max_age_seconds: Optional[int] = None
    ) -> Optional[EvidenceBundle]:
        """캐시/저장소에서 조회
        
        Args:
            request: Evidence 요청
            max_age_seconds: 최대 허용 age (None이면 무제한)
        
        Returns:
            저장된 EvidenceBundle (없거나 너무 오래되면 None)
        """
    
    def invalidate_cache(self, pattern: str):
        """캐시 무효화
        
        Args:
            pattern: 무효화할 request pattern (예: "metric_id:MET-Revenue")
        """
```

**캐싱 전략**:
```python
# Pseudo-code
def fetch_for_metrics(requests, policy):
    bundle = EvidenceBundle(request=requests[0])
    
    # 1. 캐시 확인
    cached = evidence_store.get(requests[0], max_age_seconds=86400)  # 1일
    if cached:
        logger.info("Cache hit")
        return cached
    
    # 2. 실제 fetch
    bundle = self._fetch_with_early_return(requests[0], policy)
    
    # 3. 저장
    evidence_store.save(bundle)
    
    return bundle
```

---

## 4. Error Handling 전략

### 4.1 예외 계층

```python
class EvidenceEngineError(Exception):
    """Base exception"""
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
```

### 4.2 Graceful Degradation

```python
# Pseudo-code
try:
    evidence = dart_source.fetch(request)
    bundle.add_evidence(evidence)
except SourceNotAvailableError:
    logger.warning("DART unavailable, trying next source")
    # → 다음 source 시도
except DataNotFoundError:
    logger.info("DART has no data for this request")
    # → 다음 source 시도
except Exception as e:
    logger.error(f"Unexpected error from DART: {e}")
    # → 다음 source 시도

# 모든 source 실패해도 빈 bundle 반환 (crash 방지)
return bundle  # 빈 records는 downstream에서 처리
```

---

## 5. 확장 시나리오

### 5.1 새 DataSource 추가

```python
# 1. BaseDataSource 구현
class NewResearchSource(BaseDataSource):
    def __init__(self, api_key: str):
        super().__init__(
            source_id="NewResearch",
            source_tier=SourceTier.COMMERCIAL,
            capabilities={"provides": ["market_size_reports"], "regions": ["KR", "US"]}
        )
        self.api_key = api_key
    
    def fetch(self, request):
        # API 호출 로직
        ...
    
    def can_handle(self, request):
        # capability 매칭
        ...

# 2. Registry에 등록
registry.register_source("NewResearch", "commercial", NewResearchSource(api_key))

# → 기존 EvidenceEngine 코드 수정 없이 자동 통합
```

### 5.2 새 Tier 추가

```python
# 예: "real_time" tier 추가 (API 실시간 호출)
registry._sources_by_tier["real_time"] = []

# Early Return 로직에서 tier 순서만 조정
tier_order = ["real_time", "official", "curated_internal", ...]
```

### 5.3 외부 LLM Provider 변경

```python
# LLMBaselineSource만 교체
class NewLLMSource(BaseDataSource):
    def __init__(self, provider: str):
        super().__init__(
            source_id=f"LLM_{provider}",
            source_tier=SourceTier.LLM_BASELINE,
            capabilities={"provides": ["long_tail_facts"], "regions": ["*"]}
        )
        self.provider = provider  # "openai", "anthropic", "custom"
    
    def fetch(self, request):
        # 새 provider API 호출
        ...

# Registry에 등록
registry.register_source("LLM_new", "llm_baseline", NewLLMSource("anthropic"))
```

---

## 6. 품질 보장 메커니즘

### 6.1 EvidencePolicy

```python
@dataclass
class EvidencePolicy:
    """Evidence 품질 정책
    
    PolicyEngine에서 resolve_policy()로 반환
    """
    policy_id: str  # "reporting_strict", "decision_balanced", "exploration_friendly"
    
    # 품질 요구사항
    min_literal_ratio: float  # 상위 tier 최소 비율
    max_spread_ratio: float  # 값 분산 최대 허용
    allow_llm_baseline: bool  # LLM baseline 허용 여부
    
    # Tier별 최대 시도 횟수
    max_attempts_per_tier: int = 3
    
    # Timeout
    max_total_time_seconds: int = 30
```

### 6.2 품질 검증

```python
def _evaluate_sufficiency(bundle, policy):
    """Evidence 충분성 판단"""
    bundle.calculate_quality_summary()
    
    # 1. literal_ratio 체크
    if bundle.quality_summary["literal_ratio"] < policy.min_literal_ratio:
        return False
    
    # 2. spread_ratio 체크
    if bundle.quality_summary["spread_ratio"] > policy.max_spread_ratio:
        return False
    
    # 3. 최소 source 개수
    if bundle.quality_summary["num_sources"] < 1:
        return False
    
    return True
```

---

## 7. 다음 단계

### Phase 1: 핵심 구조 구현 (TODO 1-4)
1. EvidenceEngine 클래스 구현
2. SourceRegistry 구현
3. BaseDataSource + 타입 정의 (EvidenceRequest/Bundle/Record)
4. EvidencePolicy + Early Return 로직

### Phase 2: Connector 구현 (TODO 5-7)
5. DART Source (기존 dart_connector.py 통합)
6. KOSIS/Gov Stats Source (스텁)
7. WebSearch Source (스텁)

### Phase 3: 통합 및 테스트 (TODO 8-12)
8. EvidenceStore 구현
9. Lineage 추적
10. Unit tests
11. Integration test
12. ValueEngine 통합 (MetricResolver에서 EvidenceEngine 호출)

---

## 8. 설계 검증 체크리스트

- [ ] **확장성**: 새 source 추가 시 기존 코드 수정 불필요
- [ ] **견고성**: 일부 source 실패해도 시스템 계속 작동
- [ ] **성능**: Early Return으로 불필요한 API 호출 방지
- [ ] **추적성**: 모든 Evidence의 출처/품질/시간 기록
- [ ] **테스트 가능**: Mock source로 unit test 가능
- [ ] **재사용성**: BaseDataSource 인터페이스로 다양한 connector 지원

---

**변경 이력**:
- 2025-12-09: 초안 작성 (Evidence Engine 핵심 설계)

