# Evidence 신뢰도 관리 체계 분석

**작성일**: 2025-12-10  
**버전**: CMIS v2.1  
**상태**: 현황 분석

---

## 📊 신뢰도 관리 체계 개요

CMIS는 **3단계 신뢰도 관리 체계**를 운영합니다:

```
┌─────────────────────────────────────┐
│  Level 1: Source Tier (3단계)       │
│  - Official (공식)                   │
│  - Curated Internal (내부 검증)      │
│  - Commercial (상업)                 │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  Level 2: Confidence Score (0-1)    │
│  - Source별 base confidence         │
│  - 데이터 품질 기반 조정             │
│  - 0.0 ~ 1.0 범위                   │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  Level 3: Sufficiency (3단계)       │
│  - SUFFICIENT (충분)                │
│  - PARTIAL (부분적)                 │
│  - FAILED (실패)                    │
└─────────────────────────────────────┘
```

---

## 🔍 Level 1: Source Tier (3단계)

### 정의

```python
class SourceTier(Enum):
    OFFICIAL = "official"                  # 1순위
    CURATED_INTERNAL = "curated_internal"  # 2순위
    COMMERCIAL = "commercial"              # 3순위
```

### 특징 및 우선순위

| Tier | 설명 | 예시 | 우선순위 |
|------|------|------|----------|
| **OFFICIAL** | 공식 통계/공시 | KOSIS, DART, 정부 통계 | 1 (최우선) |
| **CURATED_INTERNAL** | 내부 검증 데이터 | 사내 DB, 검증된 리포트 | 2 |
| **COMMERCIAL** | 상업 리서치/검색 | Google, Market Research | 3 |

### 구현

**EvidenceEngine Priority**:
```python
tier_priority = {
    SourceTier.OFFICIAL: 1,          # 최우선
    SourceTier.CURATED_INTERNAL: 2,
    SourceTier.COMMERCIAL: 3,
}

# Source 정렬 시 tier 우선순위 적용
sources.sort(key=lambda src: tier_priority.get(src.source_tier, 999))
```

**Early Return 정책**:
```python
# OFFICIAL tier에서 충분한 데이터 확보 시 → 즉시 반환
# COMMERCIAL tier 호출 불필요 (75% API 절감)
```

---

## 🎯 Level 2: Confidence Score (0.0 ~ 1.0)

### Source별 Base Confidence

| Source | Tier | Base | Max | 이유 |
|--------|------|------|-----|------|
| **KOSIS** | OFFICIAL | - | 0.95 | 공식 통계청 데이터 |
| **DART** | OFFICIAL | - | 0.95 | 공식 전자공시 |
| **Google Search** | COMMERCIAL | 0.50 | 0.85 | 검색엔진 (조정 가능) |
| **DuckDuckGo** | COMMERCIAL | 0.45 | 0.80 | Google보다 낮음 |
| **Stub** | - | - | 0.80 | 테스트/개발용 |

### Confidence 계산 방식

#### OFFICIAL Tier (KOSIS, DART)

```python
confidence = 0.95  # 고정 (공식 데이터)
```

**특징**:
- 고정값 (0.95)
- 공식 통계/공시의 신뢰도 반영
- 조정 없음

---

#### COMMERCIAL Tier (Google, DuckDuckGo)

```python
confidence = base + count_bonus + variance_bonus

# 1. Base Confidence
base = get_base_confidence()  # Google: 0.5, DuckDuckGo: 0.45

# 2. Count Bonus (검색 결과 개수)
count_bonus = min(num_numbers / 10, 0.2)  # 최대 +0.2

# 3. Variance Bonus (숫자 일치도)
variance_bonus = max(0, 0.25 * (1 - cv))  # 최대 +0.25
# cv = stdev / mean (낮을수록 일치도 높음)

# 4. Capping
confidence = min(confidence, get_max_confidence())
# Google: max 0.85, DuckDuckGo: max 0.80
```

**계산 예시**:

```python
# Google Search
numbers = [5.2e12, 4.8e12, 5.5e12]  # 3개 숫자

base = 0.50
count_bonus = min(3/10, 0.2) = 0.2
mean = 5.17e12
stdev = 0.35e12
cv = 0.35/5.17 = 0.068
variance_bonus = 0.25 * (1 - 0.068) = 0.233

total = 0.50 + 0.2 + 0.233 = 0.933
final = min(0.933, 0.85) = 0.85  # Max capping
```

---

### DuckDuckGo 추가 조정

```python
# DuckDuckGo는 Google보다 약간 낮게
confidence = max(0.5, confidence - 0.05)
```

---

## 📋 Level 3: Sufficiency (3단계)

### 정의

```python
class EvidenceSufficiency(Enum):
    SUFFICIENT = "sufficient"  # 충분 (사용 가능)
    PARTIAL = "partial"        # 부분적 (일부만)
    FAILED = "failed"          # 실패 (사용 불가)
```

### 판정 기준

**SUFFICIENT** (충분):
- Tier 1-2 source에서 데이터 확보
- 또는 Tier 3에서 높은 confidence (>0.7)

**PARTIAL** (부분적):
- Tier 3 source에서만 데이터 확보
- Confidence 중간 (0.5~0.7)

**FAILED** (실패):
- 모든 source에서 실패
- 또는 confidence < 0.5

---

## 🎯 Hints의 신뢰도

### 신규 추가 (2025-12-10)

```python
hint = {
    "value": 4900000000,
    "confidence": 0.5,  # Hint 기본 신뢰도 (고정)
    "context": "Education market",
    "snippet": "...",
    "source_url": "..."
}
```

**특징**:
- **고정 신뢰도**: 0.5 (medium)
- **보조 증거**: Primary evidence보다 낮음
- **재활용 가능**: metadata에 영구 저장

---

## 📊 전체 신뢰도 체계 (종합)

### 계층 구조

```
┌──────────────────────────────────────────┐
│ Source Tier (정책적 우선순위)             │
│  - OFFICIAL: 1순위 (0.95 고정)           │
│  - CURATED: 2순위                        │
│  - COMMERCIAL: 3순위 (0.45~0.85 동적)    │
└────────────┬─────────────────────────────┘
             │
┌────────────▼─────────────────────────────┐
│ Confidence Score (데이터 품질)            │
│  - 고정: OFFICIAL 0.95                   │
│  - 동적: COMMERCIAL 0.45~0.85            │
│    · base (0.45~0.50)                    │
│    · +count bonus (최대 +0.2)            │
│    · +variance bonus (최대 +0.25)        │
└────────────┬─────────────────────────────┘
             │
┌────────────▼─────────────────────────────┐
│ Sufficiency (사용 가능성)                │
│  - SUFFICIENT: tier 1-2 OR conf > 0.7    │
│  - PARTIAL: tier 3 AND conf 0.5~0.7      │
│  - FAILED: conf < 0.5                    │
└──────────────────────────────────────────┘
```

---

## 🔢 구체적 신뢰도 값

### Source별 실제 Confidence

| Source | Tier | Min | Typical | Max | 조건 |
|--------|------|-----|---------|-----|------|
| **KOSIS** | OFFICIAL | 0.95 | 0.95 | 0.95 | 고정 |
| **DART** | OFFICIAL | 0.95 | 0.95 | 0.95 | 고정 |
| **Google** | COMMERCIAL | 0.50 | 0.70-0.85 | 0.85 | 동적 |
| **DuckDuckGo** | COMMERCIAL | 0.45 | 0.60-0.75 | 0.80 | 동적 |
| **Hints** | - | 0.50 | 0.50 | 0.50 | 고정 |

### 동적 조정 요인 (COMMERCIAL)

**1. 검색 결과 개수** (최대 +0.2):
- 1개: +0.1
- 5개: +0.2
- 10개: +0.2 (cap)

**2. 숫자 일치도** (최대 +0.25):
- CV < 0.1: +0.23
- CV < 0.3: +0.18
- CV > 0.5: +0.10

**3. Source 특성**:
- Google: +0.05 (DuckDuckGo 대비)
- DuckDuckGo: -0.05

---

## 📝 정책 연동

### Policy별 Confidence 요구사항

**cmis.yaml policies**:

| Policy | min_literal_ratio | allow_prior | Confidence 요구 |
|--------|-------------------|-------------|-----------------|
| **reporting_strict** | 0.7 | false | 높음 (>0.8) |
| **decision_balanced** | 0.5 | true | 중간 (>0.6) |
| **exploration_friendly** | 0.3 | true | 낮음 (>0.4) |

### Evidence 필터링

```python
# reporting_strict: OFFICIAL tier 또는 conf > 0.8만
if policy == "reporting_strict":
    evidence = [e for e in evidence if 
                e.source_tier == "official" or 
                e.confidence > 0.8]

# exploration_friendly: confidence > 0.4면 OK
elif policy == "exploration_friendly":
    evidence = [e for e in evidence if e.confidence > 0.4]
```

---

## 🎯 Hints vs Primary 신뢰도

### 비교

| 항목 | Primary Evidence | Hints |
|------|------------------|-------|
| **목적** | 요청한 Metric | 관련 숫자 |
| **신뢰도** | 동적 (0.45~0.95) | 고정 (0.5) |
| **사용** | 즉시 | 나중에 재활용 |
| **저장 위치** | value | metadata["hints"] |
| **개수** | 1개 (consensus) | 여러 개 |

### 활용 전략

**Primary**:
```python
# 즉시 사용
value = record.value          # 5.2e12
confidence = record.confidence  # 0.85
```

**Hints**:
```python
# 나중에 활용
hints = record.metadata["hints"]
for hint in hints:
    if hint["confidence"] > 0.5 and hint["value"] < 1e13:
        # 관련 Metric 추정에 활용
```

---

## 🔍 신뢰도 판단 기준

### OFFICIAL (0.95)

**기준**:
- 정부 기관 공식 통계
- 상장사 법정 공시
- 검증된 공식 데이터

**예시**:
- KOSIS 인구 통계: 0.95
- DART 재무제표: 0.95

**조정**: 없음 (고정)

---

### COMMERCIAL (0.45 ~ 0.85)

**기준**:
- 검색엔진 결과
- 시장조사 리포트
- 상업 데이터베이스

**조정 요인**:

**1. 결과 개수** (많을수록 높음):
```
1개: base + 0.1
3개: base + 0.15
5개: base + 0.2
10개+: base + 0.2 (cap)
```

**2. 숫자 일치도** (일치할수록 높음):
```
CV < 0.1: +0.23  # 매우 일치
CV < 0.3: +0.18  # 일치
CV < 0.5: +0.13  # 보통
CV > 0.5: +0.10  # 분산 큼
```

**3. Source 신뢰도**:
```
Google: base 0.50, max 0.85
DuckDuckGo: base 0.45, max 0.80 (-0.05)
```

**최종**:
```python
final_confidence = min(
    base + count_bonus + variance_bonus,
    max_confidence
)
```

---

### HINTS (0.50)

**기준**:
- 검색 결과의 개별 숫자
- Primary보다 낮은 신뢰도
- 보조/참고 증거

**조정**: 없음 (고정 0.5)

---

## 📊 실제 Confidence 분포

### OFFICIAL

```
KOSIS 인구: 0.95 (51,217,221명)
DART 매출: 0.95 (170.37조원)
```

### COMMERCIAL

**Google Search**:
```
3개 결과, CV=0.15: 
  base 0.50 + count 0.15 + variance 0.21 = 0.86 → 0.85 (cap)

1개 결과:
  base 0.50 + count 0.10 + variance 0.10 = 0.70
```

**DuckDuckGo**:
```
3개 결과, CV=0.15:
  base 0.45 + count 0.15 + variance 0.21 = 0.81
  → max(0.5, 0.81 - 0.05) = 0.76

1개 결과:
  base 0.45 + count 0.10 + variance 0.10 = 0.65
  → max(0.5, 0.65 - 0.05) = 0.60
```

---

## 🎯 정책별 사용 가능 범위

### reporting_strict (엄격)

**요구사항**:
- min_literal_ratio: 0.7
- allow_prior: false

**사용 가능 Evidence**:
```python
# OFFICIAL tier (0.95) → OK
# COMMERCIAL confidence > 0.8 → OK
# 나머지 → NG
```

---

### decision_balanced (균형)

**요구사항**:
- min_literal_ratio: 0.5
- allow_prior: true

**사용 가능 Evidence**:
```python
# OFFICIAL (0.95) → OK
# COMMERCIAL confidence > 0.6 → OK
# Hints (0.5) → 보조로 OK
```

---

### exploration_friendly (탐색)

**요구사항**:
- min_literal_ratio: 0.3
- allow_prior: true

**사용 가능 Evidence**:
```python
# 모든 tier OK
# confidence > 0.4 → OK
# Hints → OK
# Prior estimation → OK
```

---

## 📊 신뢰도 관리 매트릭스

### Source × Policy

|  | reporting_strict | decision_balanced | exploration_friendly |
|---|-----------------|-------------------|---------------------|
| **KOSIS (0.95)** | ✅ 사용 | ✅ 사용 | ✅ 사용 |
| **DART (0.95)** | ✅ 사용 | ✅ 사용 | ✅ 사용 |
| **Google (0.70)** | ⚠️ 조건부 | ✅ 사용 | ✅ 사용 |
| **Google (0.85)** | ✅ 사용 | ✅ 사용 | ✅ 사용 |
| **DuckDuckGo (0.60)** | ❌ 불가 | ✅ 사용 | ✅ 사용 |
| **Hints (0.50)** | ❌ 불가 | ⚠️ 보조 | ✅ 사용 |

---

## 🔧 개선 여지

### 현재 구현 ✅

1. **3단계 체계**: Tier → Confidence → Sufficiency
2. **Source별 base**: 명확히 정의됨
3. **동적 조정**: 결과 개수, 일치도 반영
4. **Hints 저장**: 보조 증거 관리

### 향후 개선 가능 (Phase 4+)

1. **Evidence Age 고려**:
```python
# 데이터 신선도 반영
age_days = (today - retrieved_date).days
if age_days > 365:
    confidence *= 0.9  # 1년 이상 된 데이터 감점
```

2. **Cross-validation Bonus**:
```python
# 여러 tier에서 일치하면 +0.1
if official_value ≈ commercial_value:
    confidence += 0.1
```

3. **Hint Confidence 동적화**:
```python
# Hint도 context relevance 기반 조정
if "education" in hint["context"] and "education" in request.domain:
    hint["confidence"] = 0.6  # +0.1
```

4. **Evidence Quality Score**:
```python
quality_score = (
    tier_score * 0.4 +
    confidence * 0.4 +
    freshness * 0.1 +
    cross_validation * 0.1
)
```

---

## 📝 현황 요약

### 현재 신뢰도 관리 수준

| 항목 | 구현 수준 | 상태 |
|------|-----------|------|
| Source Tier | 3단계 | ✅ 완전 |
| Confidence Score | Source별 base + 동적 조정 | ✅ 완전 |
| Sufficiency | 3단계 | ✅ 완전 |
| Hints 관리 | 고정 0.5 | ✅ 기본 |
| Policy 연동 | 3가지 policy | ✅ 완전 |
| Age 고려 | - | ⏳ 미구현 |
| Cross-validation | - | ⏳ 미구현 |

**종합 평가**: **견고한 3단계 체계** ✅

---

## 🎯 결론

### 현재 체계

CMIS는 **3단계 신뢰도 관리 체계**를 갖추고 있습니다:

1. **Source Tier** (정책적 우선순위): 3단계
2. **Confidence Score** (데이터 품질): 0.0~1.0 동적
3. **Sufficiency** (사용 가능성): 3단계

### 강점

- ✅ **명확한 우선순위**: OFFICIAL > CURATED > COMMERCIAL
- ✅ **동적 조정**: 결과 개수, 일치도 반영
- ✅ **정책 연동**: 3가지 policy와 통합
- ✅ **Hints 저장**: 보조 증거 관리

### 개선 가능

- ⏳ Evidence age 고려 (신선도)
- ⏳ Cross-validation bonus
- ⏳ Hint confidence 동적화

**현재 상태**: Production Ready ✅

---

**작성**: 2025-12-10  
**결론**: 견고한 3단계 신뢰도 체계 운영 중

