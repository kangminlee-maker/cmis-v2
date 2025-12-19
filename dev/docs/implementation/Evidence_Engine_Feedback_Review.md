# Evidence Engine 피드백 검토 결과

**검토일**: 2025-12-09
**피드백 출처**: 아키텍처 리뷰
**검토자**: CMIS 개발팀

---

## 1. 피드백 요약

### 핵심 평가

> "EvidenceEngine 설계는 CMIS v9 전체 철학과 잘 맞고, 완전히 갈아엎을 필요 없음.
> 다만 Planner/Executor/Store/Policy로 한 단계 더 쪼개고,
> 다중 Metric 처리/Policy 연계/Prior 분리를 명확히 하면 큰 이득."

### 제안된 개선사항 (총 10개)

| 우선순위 | 항목 | 반영 여부 |
|---------|------|----------|
| **상** | 1. 다중 Metric 처리 모델 | ✅ 반영 |
| **상** | 2. EvidencePolicy ↔ quality_profiles 연계 | ✅ 반영 |
| **상** | 3. Prior tier 역할 분리 | ✅ 옵션 A 채택 |
| **상** | 4. 충분성 판단 상태값 | ✅ 반영 |
| **상** | 5. Planner/Executor 분리 | ⚠️ 단계적 반영 |
| **중** | 6. SourceRegistry capability 라우팅 | ✅ 반영 |
| **중** | 7. 캐시 키/TTL 전략 | ✅ 반영 |
| **중** | 8. 병렬 호출 훅 | 📝 v2 예정 |
| **중하** | 9. value_kind 타입 계층 | ✅ 반영 |
| **하** | 10. trace 연계 포인트 | ✅ 반영 |

---

## 2. 주요 변경사항

### 2.1 다중 Metric 처리 (임팩트: 상)

**문제**:
- v1: `List[MetricRequest] → EvidenceBundle` (metric별 구분 불가)
- 캐싱도 첫 번째 요청 기준으로만 작동

**해결**:
```python
@dataclass
class EvidenceMultiResult:
    """여러 Metric의 Evidence 묶음"""
    bundles: Dict[str, EvidenceBundle]  # metric_id → bundle
    execution_summary: Dict[str, Any]

# API 변경
def fetch_for_metrics(
    requests: List[MetricRequest]
) -> EvidenceMultiResult:  # ← 변경
```

**효과**:
- ValueEngine이 metric별 bundle 개별 접근 가능
- 캐싱도 metric 단위로 정확히 작동
- Cross-metric reuse 가능

### 2.2 EvidencePolicy ↔ quality_profiles 연계 (임팩트: 상)

**문제**:
- cmis.yaml: `allow_prior`
- v1 설계: `allow_llm_baseline` (불일치)

**해결**:
```python
@dataclass
class EvidencePolicy:
    policy_id: str
    min_literal_ratio: float
    max_spread_ratio: float
    allow_prior: bool  # ← cmis.yaml과 일치

    @classmethod
    def from_config(cls, policy_id, config):
        """cmis.yaml에서 로드 (config-driven)"""
        profile = config.policies["quality_profiles"][policy_id]
        return cls(
            policy_id=policy_id,
            min_literal_ratio=profile["min_literal_ratio"],
            max_spread_ratio=profile["max_spread_ratio"],
            allow_prior=profile.get("allow_prior", False)
        )
```

**효과**:
- YAML ↔ 코드 일관성
- Evidence-first, Prior-last 원칙이 코드에서 enforce됨

### 2.3 Prior Tier 역할 분리 (임팩트: 상)

**문제**:
- v1: Tier 4/5에 structured_estimation/llm_baseline 포함
- Evidence vs Prior 경계 모호

**해결**: **옵션 A (깔끔 분리) 채택**

```
EvidenceEngine (empirical evidence만):
  - Tier 1: official (DART, KOSIS)
  - Tier 2: curated_internal
  - Tier 3: commercial

ValueEngine.prior_estimation:
  - Pattern 기반 추정
  - Belief 기반 추정
  - LLM baseline
```

**효과**:
- "관측 Evidence" vs "Prior 추정" 경계 명확
- Lineage/검증 단계에서 설명 용이
- v9 철학 준수 (Evidence-first, Prior-last)

### 2.4 충분성 판단 상태값 (임팩트: 상)

**문제**:
- v1: `_evaluate_sufficiency() → bool` (이분법)
- Best-effort vs Strict 모드 구분 불가

**해결**:
```python
class EvidenceSufficiency(Enum):
    SUFFICIENT = "sufficient"  # 그대로 사용 가능
    PARTIAL = "partial"        # 부족하지만 사용 가능
    FAILED = "failed"          # 사용 불가

@dataclass
class EvidenceSufficiencyResult:
    status: EvidenceSufficiency
    reasons: List[str]
    summary: Dict[str, Any]
```

**효과**:
- ValueEngine/StrategyEngine이 모드 선택 가능
- 리포트 UI에 "부분 근거" 라벨 표시 가능

### 2.5 Planner/Executor 분리 (임팩트: 상)

**문제**:
- v1: EvidenceEngine 하나에 모든 책임 집중
- MetricRequest 변환, Tier 순회, Source 선택, 캐시, 품질 판단 혼재

**해결**: **4-Layer 분리 (단계적)**

```
EvidenceEngine (Facade)
  ├─ EvidencePlanner (plan 생성)
  ├─ EvidenceExecutor (plan 실행)
  └─ EvidenceStore (cache/persist)
```

**v1 적용**: Skeleton만 구현
**v2 적용**: 완전 분리 + 병렬 실행

**효과**:
- 책임 분리 → 테스트/확장 용이
- Metric별 우선순위 조정 가능
- 병렬 실행 준비

### 2.6 기타 개선사항

| 항목 | 변경 | 효과 |
|------|------|------|
| **SourceRegistry** | `find_capable_sources()` 강화 | Capability 기반 라우팅 |
| **캐시 키** | `_build_cache_key()` 정의 | Metric 단위 캐싱 |
| **value_kind** | `EvidenceValueKind` enum 추가 | 타입 체계 명확화 |
| **trace** | `debug_trace` 필드 추가 | MEM-store 연계 준비 |

---

## 3. 반영하지 않은 항목

### 3.1 병렬 호출 (v2 예정)

**이유**:
- v1 구현은 직렬로 충분
- v2에서 asyncio/ThreadPoolExecutor 도입 예정
- 설계 문서에는 훅 위치 명시

**v2 계획**:
```python
# Tier 내부 병렬 실행
results = await asyncio.gather(
    *[source.fetch(request) for source in tier_sources]
)
```

---

## 4. 설계 검증

### 4.1 핵심 원칙 준수

| 원칙 | v1 설계 | v2 개정 | 검증 |
|------|---------|---------|------|
| Evidence-first, Prior-last | ✅ | ✅ | Prior tier 분리로 더 명확 |
| Early Return | ✅ | ✅ | Executor에서 tier별 체크 |
| Graceful Degradation | ✅ | ✅ | try-except + continue |
| Source-agnostic | ✅ | ✅ | BaseDataSource 유지 |
| Lineage | ✅ | ✅ | debug_trace 추가 |

### 4.2 YAML 정합성

| YAML 항목 | v1 | v2 | 일치 여부 |
|-----------|----|----|----------|
| `quality_profiles` | allow_llm_baseline | allow_prior | ✅ 일치 |
| `data_sources` | 11개 정의 | Tier 1-3만 사용 | ✅ 일치 |
| `evidence_engine.api` | fetch_for_metrics | EvidenceMultiResult | ✅ 개선 |

### 4.3 확장성 검증

**새 Source 추가**:
```python
new_source = CustomSource(...)
registry.register_source("Custom", "commercial", new_source)
# → 기존 코드 수정 없이 자동 통합 ✅
```

**새 Metric 추가**:
```python
# metrics_spec에만 추가
{
  "metric_id": "MET-NewMetric",
  "direct_evidence_sources": ["DART", "NewSource"]
}
# → Planner가 자동으로 우선순위 적용 ✅
```

**Policy 추가**:
```python
# cmis.yaml에만 추가
quality_profiles:
  new_strict:
    min_literal_ratio: 0.9
    allow_prior: false
# → EvidencePolicy.from_config()가 자동 로드 ✅
```

---

## 5. 구현 로드맵

### Phase 1: 타입 정의 (1-2일)

- [x] 피드백 검토 완료
- [ ] types.py 확장
  - [ ] EvidenceMultiResult
  - [ ] EvidenceSufficiency
  - [ ] EvidencePolicy (config-driven)
  - [ ] EvidenceValueKind
  - [ ] EvidenceBundle (debug_trace 추가)

### Phase 2: 핵심 클래스 (3-5일)

- [ ] EvidencePlanner (skeleton)
- [ ] EvidenceExecutor
- [ ] EvidenceEngine (Facade)
- [ ] SourceRegistry 강화

### Phase 3: Connector (2-3일)

- [ ] BaseDataSource 인터페이스
- [ ] DARTSource (기존 dart_connector 통합)
- [ ] OfficialSource 스텁
- [ ] CommercialSource 스텁

### Phase 4: 통합/테스트 (2-3일)

- [ ] EvidenceStore 구현
- [ ] ValueEngine 연동
- [ ] Unit tests
- [ ] Integration test

**총 예상 기간**: 8-13일

---

## 6. 리스크 및 대응

### 6.1 설계 복잡도 증가

**리스크**:
- Planner/Executor 분리로 초기 구현 복잡도 상승
- "단순한 코드"가 여러 모듈로 분리

**대응**:
- v1에서는 Planner/Executor skeleton만 구현
- 핵심 로직은 Executor에 집중
- v2에서 점진적 개선

### 6.2 Prior tier 분리 영향

**리스크**:
- evidence_store에 structured_estimation/llm_baseline 가정한 코드 존재 가능

**대응**:
- ValueEngine prior_estimation 결과도 EvidenceRecord로 저장 가능
- `source_tier="prior"` 태깅으로 명확히 구분
- 기존 설계와 호환성 유지

### 6.3 ValueEngine 연동 변경

**리스크**:
- EvidenceMultiResult 도입으로 ValueEngine 인터페이스 변경 필요

**대응**:
- ValueEngine.evaluate_metrics() 시그니처는 유지
- MetricResolver 내부에서만 EvidenceEngine 호출 로직 수정
- 기존 테스트는 대부분 유지 가능

---

## 7. 결론

### 7.1 피드백 반영 결과

- **10개 항목 중 9개 반영** (1개는 v2 예정)
- **임팩트 상 항목 100% 반영**
- **YAML 정합성 확보**
- **v9 철학 준수 강화**

### 7.2 설계 품질 개선

| 측면 | v1 | v2 | 개선도 |
|------|----|----|--------|
| 확장성 | 중 | 상 | ↑↑ |
| 견고성 | 상 | 상 | → |
| 명확성 | 중 | 상 | ↑ |
| 테스트 용이성 | 중 | 상 | ↑ |
| YAML 일관성 | 중 | 상 | ↑↑ |

### 7.3 다음 단계

1. **Evidence_Engine_Design_Revision.md** 기반 구현 시작
2. **Phase 1 (타입 정의)** 완료 후 리뷰
3. **Phase 2-3** 병렬 진행
4. **Phase 4** 통합 테스트 및 ValueEngine 연동

---

**검토 완료**: 2025-12-09
**승인 상태**: ✅ 구현 진행 승인
**다음 문서**: Evidence_Engine_Implementation_Guide.md
