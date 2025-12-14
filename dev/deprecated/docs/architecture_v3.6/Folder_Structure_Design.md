# CMIS 폴더 구조 설계

**작성일**: 2025-12-13
**버전**: v3.6.0
**목적**: schemas vs libraries vs config 구분 기준 명확화

---

## 1. 현재 상태 분석

### 1.1 cmis_contracts-and-registry_km.yaml 정의

```yaml
modules:
  schemas:           # 스키마 정의
    - ontology
    - ledgers
    - graphs (4개)
  
  libraries:         # 라이브러리
    - pattern_library
    - metrics_spec
    - domain_registry
    - policies
    - workflows
    - prompts
```

**문제**: 3-way 분리 (schemas/libraries/config) vs 실제 폴더 (schemas/config)

---

## 2. 구분 기준 제안

### 옵션 A: 3-way 분리 (권장) ⭐⭐⭐

**기준**: **용도 + 변경 빈도**

```
schemas/              # 데이터 구조 정의 (타입 시스템)
  - 변경: 거의 없음 (stable)
  - 예: ledgers, ontology, graph schemas
  - 역할: "무엇의 모양(shape)"

libraries/            # 도메인 데이터/지식
  - 변경: 가끔 (확장)
  - 예: patterns, metrics, domains
  - 역할: "구체적 정의/값"

config/               # 런타임 설정
  - 변경: 자주 (mutable)
  - 예: policies, workflows, prompts
  - 역할: "어떻게 실행"
```

**폴더 매핑**:

```
schemas/
├─ ledgers.yaml              # Ledger 구조
├─ ontology.yaml             # Primitive 정의
├─ reality_graph.yaml        # R-Graph 스키마
├─ pattern_graph.yaml        # P-Graph 스키마
├─ value_graph.yaml          # V-Graph 스키마
└─ decision_graph.yaml       # D-Graph 스키마

libraries/
├─ pattern_library.yaml      # 23개 Pattern 정의
├─ metrics_spec.yaml         # Metric 정의/공식
├─ domain_registry.yaml      # 도메인별 Trait
└─ prompt_library.yaml       # LLM 프롬프트 템플릿

config/
├─ policies.yaml             # Quality Profile
├─ workflows.yaml            # Canonical Workflows
├─ archetypes/               # Context Archetype
└─ sources.yaml              # Data Source 설정
```

**장점**:
- 명확한 구분 ✅
- 변경 빈도 격리 ✅
- 확장성 ✅

---

### 옵션 B: 2-way 분리 (단순)

**기준**: **정적 vs 동적**

```
schemas/              # 정적 (타입 + 데이터)
  - ledgers, ontology, graphs
  - patterns, metrics, domains

config/               # 동적 (설정)
  - policies, workflows
  - archetypes, sources
```

**단점**: schemas가 너무 비대

---

### 옵션 C: 세분화 (복잡)

```
types/                # 타입 정의
schemas/              # 스키마
data/                 # 정적 데이터
config/               # 설정
```

**단점**: 폴더 너무 많음

---

## 3. 권장 구조 (옵션 A)

### 3.1 폴더 구조

```
cmis/
├─ cmis.yaml                    # Contracts + Registry
│
├─ schemas/                     # 데이터 구조 (Type System)
│  ├─ ledgers.yaml
│  ├─ ontology.yaml
│  ├─ reality_graph.yaml
│  ├─ pattern_graph.yaml
│  ├─ value_graph.yaml
│  └─ decision_graph.yaml
│
├─ libraries/                   # 도메인 지식/데이터
│  ├─ pattern_library.yaml
│  ├─ metrics_spec.yaml
│  ├─ domain_registry.yaml
│  └─ prompt_library.yaml
│
├─ config/                      # 런타임 설정
│  ├─ policies.yaml
│  ├─ workflows.yaml
│  ├─ archetypes/
│  │  ├─ ARCH-digital_service_KR.yaml
│  │  └─ ...
│  └─ sources.yaml
│
├─ cmis_core/                   # 엔진
├─ cmis_cli/                    # CLI
└─ dev/                         # 개발
```

---

### 3.2 구분 기준표

| 항목 | schemas/ | libraries/ | config/ |
|------|----------|-----------|---------|
| **역할** | 타입/구조 정의 | 도메인 지식/데이터 | 런타임 설정 |
| **변경 빈도** | 거의 없음 | 가끔 (확장) | 자주 |
| **예시** | ledgers, graphs | patterns, metrics | policies, workflows |
| **의존** | 없음 | schemas 참조 | schemas + libraries 참조 |
| **버전 관리** | 엄격 (breaking) | 중간 (backward) | 느슨 (hotfix) |

---

### 3.3 파일별 분류

| 파일 | 현재 위치 | 권장 위치 | 이유 |
|------|-----------|----------|------|
| ledgers.yaml | schemas/ | **schemas/** ✅ | 구조 정의 |
| ontology.yaml | (없음) | **schemas/** | Primitive 타입 |
| *_graph.yaml | (없음) | **schemas/** | Graph 스키마 |
| pattern_library.yaml | config/ | **libraries/** | 도메인 지식 |
| metrics_spec.yaml | (없음) | **libraries/** | Metric 정의 |
| domain_registry.yaml | config/ | **libraries/** | 도메인 Trait |
| policies.yaml | config/ | **config/** ✅ | 런타임 정책 |
| workflows.yaml | config/ | **config/** ✅ | 실행 설정 |
| archetypes/ | config/ | **config/** ✅ | 실행 컨텍스트 |

---

## 4. 마이그레이션 계획

### Phase 1: 폴더 생성

```bash
mkdir libraries
```

### Phase 2: 기존 파일 이동

```bash
# config/ → libraries/
mv config/pattern_library.yaml libraries/
mv config/domain_registry.yaml libraries/

# (미래) 신규 생성
# libraries/metrics_spec.yaml
# libraries/prompt_library.yaml
```

### Phase 3: cmis.yaml 업데이트

```yaml
modules:
  schemas:
    ledgers: "schemas/ledgers.yaml"
    ontology: "schemas/ontology.yaml"
    # ...
  
  libraries:
    pattern_library: "libraries/pattern_library.yaml"
    metrics_spec: "libraries/metrics_spec.yaml"
    # ...
  
  config:
    policies: "config/policies.yaml"
    workflows: "config/workflows.yaml"
    # ...
```

---

## 5. 권장사항

### 5.1 즉시 (Phase 1)

```bash
mkdir libraries
```

**이유**: 향후 확장 준비

---

### 5.2 단기 (Phase 2)

**이동**:
- config/archetypes/ → 유지 (설정이 맞음)
- pattern_library → libraries/ (지식 데이터)

---

### 5.3 중기 (파일 생성)

**schemas/**:
- ontology.yaml
- reality_graph.yaml
- pattern_graph.yaml
- value_graph.yaml
- decision_graph.yaml

**libraries/**:
- metrics_spec.yaml
- domain_registry.yaml
- prompt_library.yaml

---

## 6. 최종 구조 (권장)

```
cmis/
├─ schemas/           # 타입 시스템 (6-7개)
│  ├─ ledgers.yaml
│  ├─ ontology.yaml
│  └─ *_graph.yaml (4개)
│
├─ libraries/         # 도메인 지식 (3-4개)
│  ├─ pattern_library.yaml
│  ├─ metrics_spec.yaml
│  ├─ domain_registry.yaml
│  └─ prompt_library.yaml
│
└─ config/            # 런타임 설정 (4-5개)
   ├─ policies.yaml
   ├─ workflows.yaml
   ├─ archetypes/
   └─ sources.yaml
```

**명확한 3-way 분리!**

---

## 7. Summary

### 구분 기준

```
schemas/    = "What is the shape?" (타입)
libraries/  = "What are the values?" (지식)
config/     = "How to run?" (설정)
```

### 변경 빈도

```
schemas/    → 거의 없음 (breaking change)
libraries/  → 가끔 (확장)
config/     → 자주 (튜닝)
```

### 의존성

```
schemas/    → 독립
libraries/  → schemas 참조
config/     → schemas + libraries 참조
```

---

**작성**: 2025-12-13
**권장**: 3-way 분리 (schemas/libraries/config)
**우선순위**: ⭐⭐ (명확성)
