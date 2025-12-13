# CMIS 폴더 재구성 계획

**작성일**: 2025-12-13
**목표**: schemas vs libraries vs config 명확화
**현재 문제**: 모든 것이 config/에 혼재

---

## 1. 현재 상태

```
schemas/
└─ ledgers.yaml (1개만)

config/
├─ policies.yaml
├─ workflows.yaml
├─ archetypes/ (6개)
├─ patterns/ (23개)          ← libraries로 이동?
├─ domains/                  ← libraries로 이동?
├─ sources/
├─ domain_registry.yaml      ← libraries로 이동?
├─ umis_v9_*.yaml (6개)     ← deprecated?
└─ 기타
```

**문제**: config/에 모든 것이 혼재

---

## 2. 명확한 구분 기준

### schemas/ (타입 시스템)

**정의**: 데이터 **구조**
**변경**: 거의 없음 (breaking change)
**역할**: "X가 어떤 모양(shape)인가"

**예시**:
- Ledger 구조
- Graph 스키마 (Node/Edge 타입)
- Ontology Primitive

---

### libraries/ (도메인 지식)

**정의**: 구체적 **값/데이터**
**변경**: 가끔 (확장)
**역할**: "X의 구체적 인스턴스들"

**예시**:
- 23개 Pattern 정의
- Metric 정의 (TAM, SAM, ...)
- Domain-specific Trait
- Prompt 템플릿

---

### config/ (런타임 설정)

**정의**: **실행 방법**
**변경**: 자주 (튜닝)
**역할**: "어떻게 실행하나"

**예시**:
- Policy Mode
- Workflow Step
- Context Archetype
- Data Source 설정

---

## 3. 재구성 계획

### 3.1 폴더 구조 (목표)

```
schemas/
├─ ledgers.yaml ✅
├─ ontology.yaml (생성 필요)
├─ reality_graph.yaml (생성 필요)
├─ pattern_graph.yaml (생성 필요)
├─ value_graph.yaml (생성 필요)
└─ decision_graph.yaml (생성 필요)

libraries/
├─ patterns/ (이동: config/patterns/)
│  ├─ PAT-subscription_model.yaml
│  └─ ... (23개)
├─ domains/ (이동: config/domains/)
├─ pattern_library.yaml (통합 인덱스)
├─ metrics_spec.yaml (생성 필요)
├─ domain_registry.yaml (이동: config/)
└─ prompt_library.yaml (생성 필요)

config/
├─ policies.yaml ✅
├─ workflows.yaml ✅
├─ archetypes/ ✅
└─ sources/ ✅
```

---

### 3.2 이동 계획

**즉시 (Phase 1)**:
```bash
mkdir libraries

mv config/patterns/ libraries/
mv config/domains/ libraries/
mv config/domain_registry.yaml libraries/
```

**단기 (Phase 2)**:
```bash
# 신규 생성
libraries/pattern_library.yaml (patterns/ 인덱스)
libraries/metrics_spec.yaml (기존 cmis.yaml에서 추출)
```

**중기 (Phase 3)**:
```bash
# schemas/ 확장
schemas/ontology.yaml
schemas/*_graph.yaml (4개)
```

---

### 3.3 Deprecated 처리

**config/ 내 umis_v9_*.yaml (6개)**:

```bash
mv config/umis_v9_*.yaml dev/deprecated/config_v3.5/
```

**이유**: v9 명명, 사용 안 됨

---

## 4. 실행 계획

### Step 1: libraries/ 생성 및 이동

```bash
mkdir libraries

# 도메인 지식 이동
mv config/patterns/ libraries/
mv config/domains/ libraries/
mv config/domain_registry.yaml libraries/

# 인덱스 생성
cat > libraries/pattern_library.yaml <<EOF
patterns:
  - id: "PAT-subscription_model"
    file: "patterns/PAT-subscription_model.yaml"
  # ... (23개)
EOF
```

---

### Step 2: cmis.yaml 업데이트

```yaml
modules:
  libraries:
    pattern_library: "libraries/pattern_library.yaml"
    metrics_spec: "libraries/metrics_spec.yaml"
    domain_registry: "libraries/domain_registry.yaml"
```

---

### Step 3: Deprecated 정리

```bash
mkdir dev/deprecated/config_v3.5
mv config/umis_v9_*.yaml dev/deprecated/config_v3.5/
```

---

## 5. 최종 검증

### 명확성 체크

| 파일 | 분류 | 이유 |
|------|------|------|
| ledgers.yaml | schemas | 구조 정의 ✅ |
| patterns/ | libraries | 도메인 지식 ✅ |
| policies.yaml | config | 실행 설정 ✅ |
| archetypes/ | config | 실행 컨텍스트 ✅ |

**모두 명확!** ✅

---

## 6. Summary

**현재 문제**: config/에 모든 것 혼재

**해결책**: 3-way 분리
- schemas/ (타입)
- libraries/ (지식)
- config/ (설정)

**우선순위**:
- Phase 1 (폴더 생성/이동): ⭐⭐⭐ 즉시
- Phase 2 (파일 생성): ⭐⭐ 단기
- Phase 3 (schemas 확장): ⭐ 중기

**효과**:
- 명확성 ✅
- 유지보수성 ✅
- 확장성 ✅

---

**작성**: 2025-12-13
**권장**: Phase 1 즉시 실행
