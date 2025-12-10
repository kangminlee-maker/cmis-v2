# PatternEngine 설계 핵심 요약

**작성일**: 2025-12-10  
**문서**: Executive Summary

---

## 🎯 핵심 설계 철학

### CMIS 철학 100% 반영

PatternEngine은 **Trait 기반 패턴 정의**로 Ontology lock-in을 최소화하고,  
**Evidence-first 원칙**으로 R-Graph의 관찰된 구조를 우선합니다.

```
Pattern = Trait 조합 + Graph 구조
(고정 타입 ❌, 확장 가능한 조합 ✅)
```

---

## 🏗️ 아키텍처 핵심

### 3-Layer 구조

```
PatternEngine (Facade)
    ↓
PatternMatcher + GapDiscoverer
    ↓
PatternLibrary (23+ Patterns)
```

### 핵심 알고리즘

**2-Stage Scoring**:
1. **Structure Fit** (모든 경우): R-Graph 구조 적합도
2. **Execution Fit** (Brownfield만): 실행 가능성

**Combined Score** = structure_fit × execution_fit

---

## 📊 Pattern 체계

### 5개 Family, 23개 Pattern

| Family | Pattern 수 | 예시 |
|--------|-----------|------|
| Business Model | 6개 | 구독형, 플랫폼, 프리미엄 |
| Value Chain | 5개 | 수직통합, 자산경량화 |
| Growth Mechanism | 5개 | 네트워크효과, 바이럴 |
| Competitive Structure | 4개 | 시장집중, 승자독식 |
| Revenue Architecture | 3개 | 반복수익, 사용량기반 |

### Pattern 정의 예시

```yaml
pattern:
  pattern_id: "PAT-subscription_model"
  
  # Trait 조합
  trait_constraints:
    money_flow:
      required_traits:
        revenue_model: "subscription"
        payment_recurs: true
  
  # Benchmark
  quantitative_bounds:
    churn_rate: [0.03, 0.08]
    gross_margin: [0.60, 0.85]
```

---

## 🔑 핵심 결정 사항

### ✅ 결정 1: Trait 기반 정의

**선택**: Trait 조합 (고정 타입 ❌)

**이유**:
- CMIS 철학 부합
- 확장성 (새 Pattern 추가 시 Ontology 수정 불필요)
- 도메인별 Pattern 추가 용이

### ✅ 결정 2: 2-Stage Scoring

**선택**: Structure Fit + Execution Fit

**이유**:
- Greenfield: Structure Fit만으로 객관적 분석
- Brownfield: Execution Fit로 실행 가능성 고려
- CMIS 철학: Evidence-first (구조 우선)

### ✅ 결정 3: Template-based Gap Discovery

**선택**: Context Archetype → Expected Patterns → Gap

**이유**:
- 체계적 Gap 탐지
- 도메인/지역별 차이 반영
- Feasibility 평가 가능

---

## 🚀 구현 전략

### 단계별 접근 (총 6주)

**Week 1-2**: Core Infrastructure
- PatternSpec, PatternLibrary
- Trait-based matching

**Week 3-4**: Scoring & Gap Discovery
- Structure Fit, Execution Fit
- Context Archetype, Gap 탐지

**Week 5-6**: Pattern Library + Integration
- 23개 Pattern 정의
- ValueEngine, StrategyEngine 연동

---

## 💡 차별화 포인트

### 1. Trait 기반 확장성

기존 시스템: Pattern = 고정 타입 → Ontology 수정 필요

**CMIS**: Pattern = Trait 조합 → 무한 확장 가능

### 2. Brownfield 지원

기존 시스템: 구조 분석만

**CMIS**: Project Context 기반 **실행 가능성** 평가

### 3. Learning 연동

기존 시스템: 정적 Benchmark

**CMIS**: Outcome 기반 **자동 Benchmark 조정**

---

## 🔗 시스템 연동

### ValueEngine

Pattern Benchmark → Metric Prior Estimation

```python
# Pattern이 Metric 계산의 Prior 제공
churn_rate = estimate_metric(
    "MET-Churn_rate",
    pattern_benchmark="PAT-subscription_model"  # [0.03, 0.08]
)
```

### StrategyEngine

Matched Patterns + Gap Patterns → Strategy Candidates

```python
# Gap Pattern을 전략으로 전환
strategy = create_strategy(
    base_patterns=["PAT-subscription_model"],
    target_patterns=["PAT-network_effects"],  # Gap
    feasibility="high"
)
```

---

## 📊 예상 성과

### 정량적 목표

- **23개 Pattern** 정의 완료
- **90%+ 매칭 정확도** (Structure Fit)
- **15+ Gap 후보** 발굴 (Opportunity Discovery)

### 정성적 가치

- **체계적 패턴 분석**: 경험에 의존 → 데이터 기반
- **기회 발굴 자동화**: Manual → Systematic
- **실행 가능성 평가**: Project Context 기반

---

## ⚠️ 주의사항

### 설계 시 고려한 리스크

1. **Pattern 정의 품질**: 23개 Pattern을 정확히 정의해야 함
   - **대응**: Benchmark 데이터, 도메인 전문가 검증

2. **매칭 성능**: N×P 복잡도 (노드×패턴)
   - **대응**: Trait Index, Pattern Cache

3. **Learning 복잡성**: Outcome 기반 학습이 복잡함
   - **대응**: Phase 5로 후순위 (MVP 제외)

---

## 🎯 성공 기준

### MVP (Phase 1-3 완료 시점)

- [ ] 5개 Pattern 매칭 작동
- [ ] Structure Fit 점수 검증
- [ ] Gap Discovery 기본 작동

### Production Ready (Phase 4-5 완료 시점)

- [ ] 23개 Pattern 전체 작동
- [ ] ValueEngine 연동 완료
- [ ] StrategyEngine 연동 완료
- [ ] E2E 테스트 통과

---

## 🚦 다음 액션

### 1. 설계 리뷰 (즉시)

**검토 항목**:
- [ ] CMIS 철학 부합성 (Trait 기반, Evidence-first)
- [ ] 아키텍처 타당성 (3-Layer 구조)
- [ ] 구현 가능성 (6주 일정)
- [ ] 연동 전략 (ValueEngine, StrategyEngine)

### 2. Spike 착수 (승인 후 즉시)

**목표**: 5개 Pattern으로 Core 검증

**작업**:
1. PatternSpec dataclass
2. 5개 Pattern YAML (각 Family 1개)
3. Trait-based matching 기본 구현
4. Structure Fit 알고리즘 POC

**기간**: 1주

### 3. 본 구현 (Spike 성공 시)

**Phase 1-3**: 3주 (Core + Scoring + Gap Discovery)  
**Phase 4-5**: 3주 (Pattern Library + Integration)

---

## 📚 참고 문서

- **상세 설계**: `PatternEngine_Design_Blueprint.md`
- **CMIS 철학**: `cmis.yaml` (philosophy 섹션)
- **Pattern Graph**: `cmis.yaml` (pattern_graph 섹션)
- **기존 구현**: `cmis_core/pattern_engine.py` (POC)

---

**작성**: 2025-12-10  
**다음 단계**: 설계 리뷰 → Spike → 본 구현

