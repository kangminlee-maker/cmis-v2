# PatternEngine 하드코딩 전수 검토

**작성일**: 2025-12-10
**목적**: PatternEngine 하드코딩 식별
**범위**: PatternEngine 전체 (9개 파일 + 27개 YAML)

---

## 📋 검토 대상

### Core 파일 (6개)
- pattern_engine_v2.py (146 라인)
- pattern_library.py (332 라인)
- pattern_matcher.py (369 라인)
- pattern_scorer.py (431 라인)
- context_archetype.py (251 라인)
- gap_discoverer.py (207 라인)
- pattern_benchmark.py (155 라인)

### YAML 정의 (27개)
- Pattern YAML: 23개
- Archetype YAML: 4개

**총 7개 파일, 1,900+ 라인 + 2,420 라인 YAML**

---

## 🔍 발견된 하드코딩

### 🟡 Medium: 매직 넘버 (가중치)

#### 1. pattern_scorer.py - Structure Fit 가중치

**위치**: Line 106-126

**현재**:
```python
def calculate_structure_fit(pattern, trait_result, structure_result):
    trait_score = calculate_trait_score(...)
    structure_score = ...

    # 가중치 하드코딩
    final_score = (trait_score * 0.6) + (structure_score * 0.4)
```

**문제**:
- Trait: 60%, Graph: 40% 고정
- 조정 시 코드 수정

**개선 방안**:
```yaml
# config/pattern_scoring_weights.yaml
structure_fit:
  trait_weight: 0.6
  graph_weight: 0.4

execution_fit:
  capability_weight: 0.5
  constraint_weight: 0.3
  asset_weight: 0.2
```

**우선순위**: ⭐⭐ (중간)
**이유**: 가중치는 실험적 조정이 필요할 수 있음

---

#### 2. pattern_scorer.py - Execution Fit 가중치

**위치**: Line 135-145

**현재**:
```python
execution_fit = (
    capability_score * 0.5 +
    constraint_score * 0.3 +
    asset_score * 0.2
)
```

**개선**: 위와 동일 (YAML 외부화)

**우선순위**: ⭐⭐ (중간)

---

#### 3. pattern_matcher.py - Optional traits bonus

**위치**: Line 360

**현재**:
```python
optional_bonus = (optional_matched / optional_total) * 0.1  # 고정
```

**개선**: YAML 외부화

**우선순위**: ⭐ (낮음)

---

### 🟡 Medium: 순서 매핑

#### 4. gap_discoverer.py - level_order, feasibility_order

**위치**: Line 193-194

**현재**:
```python
level_order = {"core": 3, "common": 2, "rare": 1}
feasibility_order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
```

**문제**:
- 순서 우선순위 하드코딩
- 함수 내부에서 매번 생성

**개선 방안**:
```python
# 클래스 변수로 이동
class GapDiscoverer:
    LEVEL_ORDER = {"core": 3, "common": 2, "rare": 1}
    FEASIBILITY_ORDER = {"high": 3, "medium": 2, "low": 1, "unknown": 0}

# 또는 YAML
# config/pattern_sorting.yaml
sorting:
  level_order:
    core: 3
    common: 2
    rare: 1
  feasibility_order:
    high: 3
    medium: 2
    low: 1
    unknown: 0
```

**우선순위**: ⭐⭐ (중간)

---

### 🟢 Good: 이미 YAML 기반

#### ✅ Pattern 정의 (23개 YAML)

**상태**: 완벽 ✅
- 모든 Pattern이 YAML로 정의됨
- 코드 수정 불필요
- 확장성 무한대

#### ✅ Context Archetype (4개 YAML)

**상태**: 완벽 ✅
- Archetype도 YAML
- Expected Pattern Set도 YAML

#### ✅ Pattern 관계 (composes_with, conflicts_with)

**상태**: 양호 ✅
- YAML에 정의
- PatternLibrary가 P-Graph로 컴파일

---

## 📊 PatternEngine 하드코딩 요약

| 항목 | 위치 | 타입 | 우선순위 | 상태 |
|------|------|------|----------|------|
| Structure Fit 가중치 | pattern_scorer.py | 매직 넘버 | ⭐⭐ | 개선 권장 |
| Execution Fit 가중치 | pattern_scorer.py | 매직 넘버 | ⭐⭐ | 개선 권장 |
| Optional bonus | pattern_matcher.py | 매직 넘버 | ⭐ | 선택 |
| level_order | gap_discoverer.py | Dict | ⭐⭐ | 개선 권장 |
| feasibility_order | gap_discoverer.py | Dict | ⭐⭐ | 개선 권장 |
| **Pattern 정의** | **YAML** | **외부화** | - | ✅ **완벽** |
| **Archetype 정의** | **YAML** | **외부화** | - | ✅ **완벽** |

---

## 🎯 PatternEngine vs Evidence Engine

### Evidence Engine

```
하드코딩: 8개 (모두 개선 완료)
YAML 외부화: 5개 파일
확장성: 무한대
```

### PatternEngine

```
하드코딩: 5개 (매직 넘버/순서)
YAML 외부화: 27개 파일 (Pattern/Archetype)
확장성: 이미 우수
```

**결론**: PatternEngine은 이미 YAML 기반으로 잘 설계됨 ✅

---

## 💡 PatternEngine 개선 권장

### Priority 1: Scoring 가중치 YAML화 (선택)

**현재**:
```python
final_score = (trait_score * 0.6) + (structure_score * 0.4)
```

**개선**:
```yaml
# config/pattern_scoring_weights.yaml
structure_fit:
  trait_weight: 0.6
  graph_weight: 0.4

execution_fit:
  capability_weight: 0.5
  constraint_weight: 0.3
  asset_weight: 0.2

optional_bonus: 0.1
```

**이유**:
- 실험적 조정 가능
- A/B 테스트 용이
- 도메인별 다른 가중치 가능

**우선순위**: ⭐⭐ (낮음-중간)
**예상**: 1일

---

### Priority 2: 순서 매핑 상수화 (선택)

**현재**:
```python
def _sort_gaps(gaps):
    level_order = {"core": 3, "common": 2, "rare": 1}
    # 함수 내부에서 매번 생성
```

**개선**:
```python
class GapDiscoverer:
    # 클래스 상수
    LEVEL_ORDER = {"core": 3, "common": 2, "rare": 1}
    FEASIBILITY_ORDER = {"high": 3, "medium": 2, "low": 1}

    def _sort_gaps(self, gaps):
        # 재사용
        gaps.sort(key=lambda g: self.LEVEL_ORDER.get(g.expected_level))
```

**우선순위**: ⭐ (낮음)
**예상**: 0.5일

---

## 📊 종합 평가

### Evidence Engine

**Before**: 8개 하드코딩
**After**: 0개 (모두 YAML화) ✅

**평가**: 완전 개선됨

---

### PatternEngine

**하드코딩**: 5개 (매직 넘버/순서)
**YAML 기반**: 27개 파일

**평가**: 이미 우수, 선택적 개선만 필요

---

## 🎯 권장 사항

### PatternEngine (현재 상태)

**✅ 강점**:
- Pattern 정의: 100% YAML ✅
- Archetype 정의: 100% YAML ✅
- 확장성: 무한대 ✅
- 코드 품질: 우수 ✅

**⚠️ 개선 가능**:
- Scoring 가중치: 매직 넘버 (선택적 개선)
- 순서 매핑: 함수 내부 (미미한 이슈)

**결론**: **즉시 개선 불필요**, 선택적 개선만 고려

---

### 우선순위 비교

| 엔진 | 하드코딩 심각도 | 개선 시급성 |
|------|----------------|-------------|
| **Evidence Engine** | 🔴 높음 | ⭐⭐⭐⭐⭐ 즉시 |
| **PatternEngine** | 🟢 낮음 | ⭐⭐ 선택적 |

---

## 📝 결론

### Evidence Engine

- **완료**: 8개 하드코딩 모두 제거 ✅
- **상태**: 완전 동적화

### PatternEngine

- **현황**: 이미 YAML 기반으로 우수 ✅
- **하드코딩**: 5개 (매직 넘버, 낮은 우선순위)
- **조치**: 선택적 개선 (Scoring 가중치 YAML화)

**전체 평가**: PatternEngine은 이미 잘 설계되어 있음 ✅

---

**작성**: 2025-12-10
**결론**: PatternEngine 즉시 개선 불필요, 현재 상태 양호


