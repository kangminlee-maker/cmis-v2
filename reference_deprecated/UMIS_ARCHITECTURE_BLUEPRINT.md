# UMIS Architecture Blueprint
**Universal Market Intelligence System - 시스템 설계도**

> 이 문서만으로 UMIS를 다시 만들 수 있는 완전한 아키텍처 설계도

---

## 🎯 System Philosophy

### What is UMIS?
시장 분석을 위한 **6-Agent 협업 시스템** + **4-Layer RAG 아키텍처** + **Excel 자동 생성**

**핵심 철학**:
1. **역할 분리**: 각 Agent는 명확한 단일 책임
2. **상호 검증**: 모든 산출물은 2-3명이 교차 검증
3. **완전한 추적성**: 모든 주장은 원본 데이터까지 역추적 가능
4. **단일 진실의 원천**: 값 추정은 Estimator만 수행
5. **학습하는 시스템**: 사용할수록 빠르고 정확해짐

### Core Capabilities
- ✅ **6-Agent 협업**: 역할 분담 및 상호 검증
- ✅ **Estimator 4-Stage Fusion**: 증거 우선, 재귀 제거, Budget 기반
- ✅ **Validator Priority**: 확정 데이터 우선 검색 (85% 처리)
- ✅ **Knowledge Graph**: 패턴 조합 자동 발견 (Neo4j)
- ✅ **System RAG**: 19개 도구 Key-based 검색 (4 Onboarding + 9 System + 6 Agent Complete)
- ✅ **Excel 자동 생성**: 3개 워크북 (9-11 시트), 100% 수식 기반
- ✅ **Native/External Mode**: Cursor LLM 직접 활용 or API 자동화
- ✅ **LLM Complete Abstraction**: Business logic에서 LLM 모드 분리

---

## 🏗️ System Architecture

### 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: BUSINESS LAYER                          │
│                    (사용자 대면 - 분석 산출물)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Observer │  │ Explorer │  │Quantifier│  │Validator │           │
│  │ (Albert) │  │ (Steve)  │  │  (Bill)  │  │ (Rachel) │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │             │             │             │                  │
│       └─────────────┴──────┬──────┴─────────────┘                  │
│                            │                                        │
│                   ┌────────▼────────┐                               │
│                   │   Estimator     │                               │
│                   │   (Fermi)       │ ◄── 값 추정 (협업 파트너)     │
│                   └────────┬────────┘                               │
│                            │                                        │
│                       ┌────▼────┐                                   │
│                       │Guardian │                                   │
│                       │(Stewart)│ ◄── 검증 & 메타 관리              │
│                       └─────────┘                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 2: RAG DATA LAYER                          │
│                    (지식 저장 및 검색)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Layer 1: Vector Indexes                                           │
│  ┌──────────────────┐  90% Rules   ┌──────────────────┐           │
│  │Canonical Index   │──────────────▶│Projected Index   │           │
│  │(CAN-*)           │  10% LLM      │(PRJ-*)           │           │
│  │                  │               │                  │           │
│  │정규화 청크        │               │Agent별 검색용 뷰  │           │
│  │업데이트용         │               │6개 Agent Views   │           │
│  └──────────────────┘               └──────────────────┘           │
│                                              │                      │
│  Layer 3: Knowledge Graph                    │                      │
│  ┌──────────────────────────────────────────▼─────┐                │
│  │Neo4j Graph Database                            │                │
│  │                                                 │                │
│  │(Pattern)-[COMBINES_WITH]->(Pattern)            │                │
│  │(Pattern)-[COUNTERS]->(Pattern)                 │                │
│  │                                                 │                │
│  │13 Nodes | 45 Relationships                     │                │
│  │Confidence: similarity × coverage × validation  │                │
│  └─────────────────────────────────────────────────┘                │
│                                                                     │
│  Layer 4: Memory                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │Query Memory  │  │Goal Memory   │  │RAE Memory    │            │
│  │(순환 감지)    │  │(목표 정렬)    │  │(평가 재사용)  │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 3: RAG RUNTIME LAYER                       │
│                    (실행 환경 및 정책)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Configuration Files:                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │projection_     │  │routing_policy  │  │runtime_config  │       │
│  │rules.yaml      │  │.yaml           │  │.yaml           │       │
│  │                │  │                │  │                │       │
│  │90% 규칙 기반   │  │Workflow 정의   │  │Circuit Breaker │       │
│  │10% LLM 학습    │  │4-Stage Fusion  │  │Fail-Safe       │       │
│  └────────────────┘  └────────────────┘  └────────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 💡 Core Concepts

### 1. 6-Agent System (Business Layer)

#### Agent 역할 및 산출물

| Agent ID | Name | Role | 산출물 | 협업 방식 |
|----------|------|------|--------|----------|
| **observer** | Albert | 시장 구조 분석 | market_reality_report.md | 가치사슬 마진 → Estimator 협업 |
| **explorer** | Steve | 기회 발굴 (RAG) | OPP_*.md (기회 가설) | Pattern 검색 → Estimator 시장 규모 |
| **quantifier** | Bill | 계산 전문 (31개 방법론) | market_sizing.xlsx (10 sheets)<br>unit_economics.xlsx (10 sheets)<br>financial_projection.xlsx (11 sheets) | 필요 값 → Estimator 요청 후 계산 |
| **validator** | Rachel | 데이터 검증 + DART API | source_registry.yaml<br>DART 재무/공시 데이터 | 검증 대상 추정치 → Estimator 교차 검증 |
| **guardian** | Stewart | 프로세스 관리 (Meta-RAG) | .project_meta.yaml<br>deliverables_registry.yaml | 순환 감지, 목표 정렬, 평가 일관성 |
| **estimator** | **Fermi** | **값 추정 전문 (4-Stage Fusion)** | **EstimationResult** (값 + 근거 + certainty) | **협업 파트너 (모든 Agent가 호출)** |

**핵심 원칙**:
- **Agent ID 불변** (observer, explorer, quantifier, validator, guardian, estimator)
- **Name 변경 가능** (`config/agent_names.yaml`에서 커스터마이징)
- **상호 검증**: 각 산출물 2-3명 검증
- **MECE**: Estimator = 추정, Quantifier = 계산 (역할 명확 분리)

#### 데이터 흐름 (순차적 의존성)

```
Rachel (Validator) ─────► 확정 데이터 최우선
  ↓ SRC_YYYYMMDD_NNN     (85% 처리)
  │ source_registry.yaml
  │ - 신뢰도 평가 (0-100)
  │ - Definition Gap 분석
  │
  ├─► Fermi (Estimator) ◄── 협업 파트너 (모든 Agent가 호출)
  │   │ EstimationResult
  │   │ - 4-Stage Fusion (Evidence → Prior → Fermi → Fusion)
  │   │ - certainty: high/medium/low
  │   │ - source: Literal/Direct_RAG/Validator/Prior/Fermi/Fusion
  │   │ - reasoning_detail (완전한 근거)
  │   └─ 학습 시스템 (certainty=high → Direct RAG 편입)
  │
Bill (Quantifier)
  ↓ 계산 수행 (31개 방법론)
  │ market_sizing.xlsx
  │ - Assumptions: SRC_ID 참조 or EST-ID 참조
  │ - 필요 값 (ARPU, Churn 등) → Estimator 호출
  │ - 수신 결과로 계산 수행 (LTV = ARPU / Churn)
  │ - 4가지 Method → Convergence (±30%)
  │
Albert (Observer)
  ↓ 시장 구조 분석
  │ market_reality_report.md
  │ - 모든 주장에 SRC_ID 또는 EST-ID 참조
  │ - 가치사슬 마진 → Estimator 협업
  │ - 비효율성 정량화 (Quantifier + Estimator 협업)
  │
Steve (Explorer)
  ↓ 기회 가설
  │ OPP_*.md
  │ - RAG Pattern Search (Vector + Graph)
  │ - 기회 크기 → Estimator 협업 (Order of Magnitude)
  │ - 3명 검증 (Albert, Bill, Rachel)
  │
Stewart (Guardian)
  │ .project_meta.yaml
  │ deliverables_registry.yaml
  │ - Query Memory (순환 감지)
  │ - Goal Memory (목표 정렬)
  │ - RAE Memory (평가 일관성)
  └─ 검증 상태 집계, 품질 평가
```

### 2. Estimator 4-Stage Fusion Architecture

**핵심 철학**: "증거 우선 + 재귀 제거 + Budget 기반 탐색"

```
┌─────────────────────────────────────────────┐
│ Stage 1: Evidence Collection               │
│ (<1s, 90-100% 정확도)                       │
│                                             │
│  - Literal: 프로젝트 명시 데이터           │
│  - Direct RAG: 학습된 규칙 (진화)          │
│  - Validator: 확정 데이터 (85% 처리!)      │
│  - Guardrails: 개념 기반 검증              │
│                                             │
│  certainty=high → 즉시 반환 (Early Return) │
└──────────────┬──────────────────────────────┘
               │ certainty < high
               ▼
┌─────────────────────────────────────────────┐
│ Stage 2: Generative Prior                  │
│ (~3s, 70-80% 정확도)                        │
│                                             │
│  LLM에게 직접 값 요청                       │
│  - 내부 지식 활용                           │
│  - 빠른 추정                                │
│  - certainty 자체 평가                      │
│                                             │
│  certainty=high → 반환                      │
└──────────────┬──────────────────────────────┘
               │ certainty < high
               ▼
┌─────────────────────────────────────────────┐
│ Stage 3: Structural Explanation (Fermi)    │
│ (~5s, 60-70% 정확도)                        │
│                                             │
│  구조적 분해 (재귀 없음, max_depth=2)       │
│  - Budget 기반 탐색                         │
│  - Standard/Aggressive/Minimal 모드         │
│  - 변수 분해 → Stage 1/2 재시도            │
│                                             │
│  certainty=high → 반환                      │
└──────────────┬──────────────────────────────┘
               │ certainty < high
               ▼
┌─────────────────────────────────────────────┐
│ Stage 4: Fusion & Validation                │
│ (<1s, 80-90% 정확도)                        │
│                                             │
│  모든 Stage 결과 가중 합성                  │
│  - Stage별 confidence 가중치               │
│  - 일관성 검증                              │
│  - 최종 certainty 계산                      │
│                                             │
│  → 최종 결과 반환                           │
└─────────────────────────────────────────────┘

총 커버리지: 100%
실패율: 0%
역할: 순수 추정 (계산은 Quantifier)
```

**Stage vs Phase 용어**:
- **Stage**: Estimator 전체 추정 단계 (1-4)
- **Step**: 각 Stage 내부 세부 단계 (예: Stage 3 내부 Step 1-4)

**Budget 관리 (Stage 3)**:
```yaml
modes:
  standard:    # 기본값
    max_llm_calls: 3
    max_depth: 2
    certainty_threshold: "medium"
  
  aggressive:  # 비용 무관
    max_llm_calls: 10
    max_depth: 3
    certainty_threshold: "high"
  
  minimal:     # 비용 최소화
    max_llm_calls: 1
    max_depth: 1
    certainty_threshold: "low"
```

### 3. 4-Layer RAG Architecture

#### Layer 1: Canonical Index (CAN-*)
```
목적: 정규화된 원본 청크 (업데이트용)
구조: Anchor Path + Content Hash
ID: CAN-{pattern}-{seq}

canonical_chunk_id: "CAN-baemin-001"
sections:
  - agent_view: explorer
    anchor_path: "platform_model.trigger_observations"
    content_hash: "sha256:ab123456..."
```

#### Layer 2: Projected Index (PRJ-*)
```
목적: Agent별 검색용 Materialized View
전략: on_demand (TTL 24h) → 고빈도면 persistent
ID: PRJ-{pattern}-{agent}-{seq}

projected_chunk_id: "PRJ-baemin-exp-001"
agent_view: "explorer"
canonical_chunk_id: "CAN-baemin-001"
explorer_pattern_id: "platform_business_model"
explorer_csf: ["network_effects", "switching_costs"]
materialization:
  strategy: "on_demand"
  cache_ttl_hours: 24
```

**Projection 메커니즘**: 90% 규칙 + 10% LLM 학습
```yaml
# config/projection_rules.yaml
field_rules:
  business_model:
    agents: [explorer]
    reason: "기회 발굴에 핵심"
  
  churn_rate:
    agents: [explorer, quantifier, guardian]
    reason: "구독 평가 + 계산 + 검증"
    learned: true  # LLM 3회 일관성 → 자동 규칙화
```

#### Layer 3: Knowledge Graph (GND-*, GED-*)
```
Database: Neo4j
Nodes: 13개 (Pattern, Industry, etc.)
Edges: 45개 (COMBINES_WITH, COUNTERS, etc.)
ID: GND-{pattern}-{seq}, GED-{rel}-{seq}

(GND-platform-001)-[COMBINES_WITH]->(GND-subscription-001)
relationship_type: COMBINES_WITH
confidence:
  similarity: 0.92
  coverage: 0.10
  validation: true
  overall: 0.85
evidence_ids: ["CAN-amazon-001", "PRJ-spotify-exp-002"]
```

#### Layer 4: Memory (MEM-*, RAE-*, EST-*)
```
Query Memory (MEM-query-*): 순환 감지
Goal Memory (MEM-goal-*): 목표 정렬
RAE Index (RAE-eval-*): Guardian 평가 재사용
Estimation Results (EST-*): Estimator 추정 결과
```

### 4. ID Namespace System

**양방향 추적 가능**한 12개 Prefix:

| Prefix | 의미 | 예시 | 소유자 |
|--------|------|------|--------|
| **SRC-** | 데이터 출처 | SRC_20241031_001 | Rachel (Validator) |
| **EST-** | Estimator 추정 결과 | EST-churn-001 | Fermi (Estimator) |
| **ASM-** | 가정 | ASM_001 | Bill (Quantifier) |
| **OPP-** | 기회 가설 | OPP_20241031_001 | Steve (Explorer) |
| **DEL-** | 산출물 | DEL_20241031_001 | Stewart (Guardian) |
| **CAN-** | Canonical 청크 | CAN-baemin-001 | RAG System |
| **PRJ-** | Projected 청크 | PRJ-baemin-exp-001 | RAG System |
| **GND-** | Graph 노드 | GND-platform-001 | Neo4j |
| **GED-** | Graph 간선 | GED-plat-sub-001 | Neo4j |
| **MEM-** | Memory | MEM-query-001 | Guardian |
| **RAE-** | RAE 평가 | RAE-eval-001 | Guardian |
| **tool:** | System RAG 도구 | tool:estimator:estimate | System |

**추적 예시**:
```
OPP_20241031_001.md: "피아노 구독 서비스 SAM 270억"
  ← Bill market_sizing.xlsx (4 methods 수렴)
    ← ASM_001 = 1,500억
      ← SRC_20241031_001 (신뢰도 85/100)
        ← Rachel source_registry.yaml
          ← https://example.com/piano-market-report
    ← EST_001 (Estimator: 학원 비중 30%)
      ← SRC_20241031_012 (서울 샘플, 신뢰도 75/100)
```

### 5. LLM Complete Abstraction

**철학**: "Business Logic은 LLM 모드를 모른다"

```
┌─────────────────────────────────────────┐
│     Business Logic (Estimator)          │
│                                         │
│  estimate(question, context)            │
│    → LLMProvider (interface)            │
│       ↓                                 │
└───────┼─────────────────────────────────┘
        │
        ├─► CursorLLMProvider (Native)
        │     - 비용: $0
        │     - 품질: 최고
        │     - 자동화: 불가
        │
        └─► ExternalLLMProvider (External)
              - 비용: $3-10/1M tokens
              - 품질: 중상
              - 자동화: 가능
```

**LLMProvider Interface**:
```python
class LLMProvider(ABC):
    @abstractmethod
    def get_llm(self, task_type: TaskType) -> BaseLLM:
        """TaskType에 맞는 LLM 인스턴스 반환"""
        pass

class BaseLLM(ABC):
    @abstractmethod
    def estimate(self, question: str, context: Context) -> EstimationResult:
        pass
    
    @abstractmethod
    def decompose(self, question: str) -> DecompositionResult:
        pass
    
    @abstractmethod
    def evaluate_certainty(self, value: Any, evidence: Dict) -> str:
        pass
```

**TaskType 기반 모델 선택**:
```python
class TaskType(Enum):
    PRIOR_ESTIMATION = "prior_estimation"       # Stage 2
    FERMI_DECOMPOSITION = "fermi_decomposition" # Stage 3
    FUSION_VALIDATION = "fusion_validation"     # Stage 4
```

**config/model_configs.yaml**:
```yaml
# TaskType별 파라미터 자동 조정
o1-mini:
  reasoning_effort:
    default: medium
    task_overrides:
      explorer: high          # 깊은 연결성 고찰 → 창의성
      stage_3_fermi: high     # 정밀한 분해 필요

gpt-4o-mini:
  temperature:
    default: 0.7
    task_overrides:
      explorer: 0.9           # 다양한 가설 탐색
      stage_2_prior: 0.3      # 안정적인 추정
```

---

## 🔄 Data Flow & Workflows

### Explorer Workflow (RAG + Graph + Estimator)

```
Input: triggers = ["구독 모델 트렌드"]
  ↓
Step 1: Pattern Search (Vector + Graph)
  - Vector Search: projected_index (agent_view=explorer)
    → subscription_model, platform_model
  - Graph Search: Neo4j
    → (Platform)-[COMBINES_WITH]->(Subscription)
  
  Output: matched_patterns
  ↓
Step 2: Case Search
  Filter: chunk_type = "success_case", pattern_id = "subscription_model"
  Output: success_cases = [Netflix, Spotify, Adobe]
  ↓
Step 3: Estimator Collaboration (조건부)
  Condition: needs_estimation (시장 규모 필요)
  
  estimator.estimate("피아노 구독 시장 크기는?")
  → Stage 1-4 자동 시도
  → EstimationResult {value, certainty, source, reasoning_detail}
  
  Output: estimation_result
  ↓
Step 4: Hypothesis Generation
  Input: [patterns, cases, estimation_result]
  Memory Check: query_memory (순환 감지)
  
  Generate: hypothesis = {
    title: "피아노 구독 서비스",
    pattern: "subscription_model",
    evidence: [Netflix 사례, Spotify 사례],
    market_size_estimate: estimation_result,
    validation_protocol: [...]
  }
  
  Output: OPP_*.md
```

### Canonical → Projected → Graph 흐름

```
1. Canonical Index 빌드
   scripts/build_canonical_index.py
   ├─ umis_business_model_patterns.yaml 읽기
   ├─ 각 패턴마다:
   │  ├─ Anchor Path 추출
   │  ├─ Content Hash 계산 (SHA-256)
   │  └─ Lineage 생성
   └─ ChromaDB canonical_index에 저장
      → CAN-subscription-001, CAN-platform-001

2. Projected Index 빌드 (on-demand)
   scripts/build_projected_index.py
   ├─ Canonical 청크 로드
   ├─ 각 청크마다:
   │  ├─ config/projection_rules.yaml 적용 (90%)
   │  ├─ LLM 판단 (10%, 규칙 없는 필드)
   │  │  → data/llm_projection_log.jsonl 로깅
   │  │  → 3회 일관성 → 자동 규칙화
   │  └─ Agent별 동적 필드 추가
   └─ ChromaDB projected_index에 저장
      materialization: {strategy: "on_demand", TTL: 24h}

3. Knowledge Graph 빌드
   scripts/build_knowledge_graph.py
   ├─ config/pattern_relationships.yaml 읽기
   ├─ Nodes 생성: GND-platform-001
   ├─ Edges 생성: GED-plat-sub-001
   │  confidence: {similarity, coverage, validation, overall}
   │  evidence_ids, provenance
   └─ Neo4j에 저장
```

### Circuit Breaker (Fail-Safe)

```
정상:
  Vector Search → Success
  failure_count = 0, state = CLOSED

실패 1회:
  Vector Search → Timeout (30초)
  failure_count = 1
  Fallback: yaml_only

실패 2회:
  failure_count = 2
  Fallback: yaml_only

실패 3회 (임계값):
  failure_count = 3
  state = OPEN (회로 차단!)
  → 모든 요청 즉시 실패 (60초간)

60초 후:
  state = HALF_OPEN
  시험 요청 → Success
  failure_count = 0
  state = CLOSED (정상 복구)
```

---

## 🎓 Design Principles

### 1. 스키마 설계 원칙

✅ **DO**:
- ID는 불변 (observer, CAN-*, PRJ-*)
- Name은 변경 가능 (`config/agent_names.yaml`)
- 모든 데이터에 Lineage (from, via, evidence_ids)
- Anchor Path (안정) > Line Range (불안정)
- Content Hash로 변경 감지

❌ **DON'T**:
- Line Range 사용 (파일 수정 시 깨짐)
- 하드코딩된 Agent Name (폴더명 등)
- ID 없는 데이터 (추적 불가)

### 2. Projection 전략

- **90% 규칙 기반**: 성능, 일관성
- **10% LLM 판단**: 유연성, 학습
- **3회 일관성 → 규칙화**: 자동 개선

### 3. 캐싱 전략

- **기본**: on_demand (TTL 24h)
- **고빈도 (10회+)**: persistent (영구)
- **저빈도**: TTL 만료 → 재생성

### 4. Fail-Safe 계층 (다층 방어)

- **Level 1**: Fallback (vector_fail → yaml_only)
- **Level 2**: Mode Toggle (hybrid → yaml_only)
- **Level 3**: Circuit Breaker (3회 실패 → 60초 차단)

### 5. Single Source of Truth

**원칙**: "모든 값/데이터 추정은 Estimator만 수행"

```
✅ Quantifier: 계산 OK, 추정 NO → Estimator 호출
✅ Validator: 검증 OK, 추정 NO → Estimator 호출
✅ Observer: 관찰 OK, 추정 NO → Estimator 호출
✅ Explorer: 가설 OK, 추정 NO → Estimator 호출
✅ Guardian: 평가 OK, 추정 NO → Estimator 호출
✅ Estimator: 추정 OK (유일한 권한)
```

**효과**:
1. **데이터 일관성**: 같은 질문 → 같은 답 (보장)
2. **학습 효율**: 모든 추정이 한 곳에 축적
3. **근거 추적**: 추정값의 출처 명확, 재현 가능

---

## 🏗️ Implementation Details

### 핵심 파일 구조

```
umis/
├── umis.yaml                          # 메인 가이드 (Cursor Rules)
├── umis_core.yaml                     # 압축 INDEX (AI 빠른 참조)
│
├── config/                            # 설정 파일 중앙 관리
│   ├── agent_names.yaml               # Agent 이름 커스터마이징
│   ├── model_configs.yaml             # LLM 모델 설정 (TaskType별 파라미터)
│   ├── schema_registry.yaml           # RAG 레이어 스키마
│   ├── projection_rules.yaml          # Canonical → Projected 변환 규칙
│   ├── routing_policy.yaml            # Workflow 정의
│   ├── runtime.yaml                   # 실행 모드 (Circuit Breaker)
│   ├── pattern_relationships.yaml     # Knowledge Graph 관계 정의
│   └── tool_registry.yaml             # System RAG 도구 레지스트리 (19개)
│
├── umis_rag/                          # 핵심 패키지
│   ├── core/                          # 핵심 시스템
│   │   ├── llm_interface.py           # LLMProvider, BaseLLM, TaskType
│   │   ├── llm_cursor.py              # Native 모드 구현
│   │   ├── llm_external.py            # External 모드 구현
│   │   ├── llm_provider_factory.py    # LLMProvider 팩토리
│   │   ├── model_configs.py           # Model Config 시스템
│   │   ├── model_router.py            # TaskType별 모델 선택
│   │   ├── schema.py                  # Pydantic 스키마
│   │   ├── layer_manager.py           # 3-Layer 관리
│   │   └── circuit_breaker.py         # Circuit Breaker
│   │
│   ├── agents/                        # 6-Agent 시스템
│   │   ├── observer.py
│   │   ├── explorer.py
│   │   ├── quantifier.py
│   │   ├── validator.py
│   │   ├── guardian.py
│   │   └── estimator/                 # Estimator (4-Stage Fusion)
│   │       ├── estimator.py           # 통합 인터페이스
│   │       ├── evidence_collector.py  # Stage 1
│   │       ├── prior_estimator.py     # Stage 2
│   │       ├── fermi_estimator.py     # Stage 3
│   │       ├── fusion_layer.py        # Stage 4
│   │       ├── models.py              # 데이터 모델 (Context, Budget, etc.)
│   │       └── compat.py              # Legacy 호환성
│   │
│   ├── graph/                         # Knowledge Graph
│   │   ├── schema_initializer.py
│   │   ├── connection.py
│   │   ├── hybrid_search.py           # Vector + Graph
│   │   ├── context_enricher.py        # Rich Context 생성
│   │   └── confidence_calculator.py
│   │
│   ├── guardian/                      # Meta-RAG
│   │   ├── meta_rag.py
│   │   ├── memory.py
│   │   ├── query_memory.py
│   │   ├── goal_memory.py
│   │   └── rae_memory.py
│   │
│   └── projection/                    # Projection
│       ├── hybrid_projector.py        # 90% 규칙 + 10% LLM
│       └── ttl_manager.py
│
├── dev_docs/                          # 개발 문서
│   ├── SESSION_CLOSURE_PROTOCOL.yaml  # 세션 마무리 프로토콜 (8단계)
│   ├── session_summaries/             # 세션 서머리 (11개 섹션)
│   └── CONTEXT_WINDOW_STRATEGY.md     # 컨텍스트 윈도우 전략
│
└── scripts/                           # 실행 스크립트
    ├── 01_convert_yaml.py             # YAML → JSONL
    ├── 02_build_index.py              # RAG 빌드 통합
    ├── build_canonical_index.py
    ├── build_projected_index.py
    ├── build_knowledge_graph.py
    ├── build_system_knowledge.py      # System RAG 빌드
    ├── query_system_rag.py            # System RAG 검색
    └── sync_umis_to_rag.py            # umis.yaml → RAG 동기화 (Onboarding 자동 생성)
```

### Configuration 핵심 설정

#### 실행 모드 (config/runtime.yaml)

```yaml
mode: rag_full  # yaml_only / hybrid / rag_full

layers:
  vector: true      # ChromaDB Vector RAG
  graph: true       # Neo4j Knowledge Graph
  memory: true      # Guardian Memory
  meta: true        # Meta-RAG
  estimator: true   # Estimator 4-Stage

circuit_breaker:
  enabled: true
  failure_threshold: 3
  timeout_seconds: 30
  recovery_timeout: 60
```

#### Projection 학습 (config/projection_rules.yaml)

```yaml
learning:
  enabled: true
  min_occurrences: 3         # 3회 이상 → 규칙화
  confidence_threshold: 0.9  # LLM 판단 일관성 90%+

llm_log_path: "data/llm_projection_log.jsonl"
```

---

## 🚀 Getting Started

### 빠른 시작

```bash
# 1. 설치
python setup/setup.py

# 2. 환경 변수 설정
cp env.template .env
# .env 파일에서 LLM_MODE와 API 키 설정

# 3. RAG 빌드
python scripts/02_build_index.py --agent explorer

# 4. Cursor에서 사용
@Explorer, 시장 분석해줘
@Fermi, B2B SaaS ARPU는?
```

### 사용 예시

```python
from umis_rag.agents.estimator import EstimatorRAG

estimator = EstimatorRAG()

# Stage 1-4 자동 선택
result = estimator.estimate("B2B SaaS Churn Rate는?", domain="B2B_SaaS")

print(f"값: {result.value}")
print(f"확신도: {result.certainty}")
print(f"소스: {result.source}")
print(f"근거: {result.reasoning_detail}")
```

---

## 📚 References

### 핵심 문서
- `umis.yaml`: 메인 가이드 (Cursor Rules, 6,800+ 줄)
- `umis_core.yaml`: 압축 INDEX (System RAG용)
- `config/schema_registry.yaml`: RAG 레이어 스키마
- `config/model_configs.yaml`: LLM 모델 설정
- `config/tool_registry.yaml`: System RAG 도구 레지스트리 (auto-sync)

### 아키텍처 문서
- `LLM_ABSTRACTION_v7_11_0.md`: LLM Complete Abstraction 상세
- `LLM_STRATEGY.md`: LLM 전략 및 최적화
- `MIGRATION_GUIDE_v7_11_0.md`: v7.11.0 마이그레이션 가이드

### 개발 가이드
- `dev_docs/SESSION_CLOSURE_PROTOCOL.yaml`: 세션 마무리 프로토콜 (8단계, 1,460줄)
- `dev_docs/CONTEXT_WINDOW_STRATEGY.md`: 컨텍스트 윈도우 전략
- `dev_docs/session_summaries/`: 과거 세션 기록 (11개 섹션 구조)

### 사용자 가이드
- `INSTALL.md`: 설치 가이드
- `ESTIMATOR_USER_GUIDE_v7_11_0.md`: Estimator 사용법
- `BUDGET_CONFIGURATION_GUIDE.md`: Budget 설정 (Stage 3)
- `SYSTEM_RAG_GUIDE.md`: System RAG 사용법
- `docs/guides/CURSOR_AUTO_SETUP.md`: Cursor 자동 설치
- `docs/guides/CURSOR_SYSTEM_COMMANDS.md`: 시스템 명령어

---

*이 문서는 UMIS의 "살아있는 설계도"입니다.*  
*시스템의 핵심 아키텍처와 철학을 담고 있으며, 이 문서만으로 UMIS를 재구현할 수 있습니다.*
