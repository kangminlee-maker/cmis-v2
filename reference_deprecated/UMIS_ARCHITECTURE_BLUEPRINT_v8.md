# UMIS v8 Architecture Blueprint (Value OS 설계)

Universal Market Intelligence System – v8 아키텍처 설계서 (완전 개정판)

본 문서는 v8 기준으로 **UMIS를 "결정 가능한 숫자(Decision-grade Numbers)를 생산하는 Value OS"**로 재정의한다.
이 문서 하나와 `umis_v8.yaml`만으로 v8 시스템의 상위 구조를 재구현할 수 있도록 설계한다.

---

## 1. System Philosophy – v8이 지향하는 것

- **정체성**: "시장/비즈니스 세계를 값(Value)과 관계(Graph)로 재표현하고, 의사결정에 사용할 수 있는 숫자를 생산하는 OS"
- **핵심 철학**
  - **Evidence-first, Prior-last**
    - 가능한 한 공식·데이터·구조에 기반한 값 생산을 우선한다.
    - LLM Prior는 진짜로 어쩔 수 없는 부족 구간만 메우는 Last Resort로 사용한다.
  - **Value Graph as the Core**
    - 세계를 문단(text)이 아니라 **값과 관계의 그래프(Value Graph)**로 본다.
    - 모든 숫자는 어떤 값들로부터 어떤 규칙으로 나왔는지 추적 가능해야 한다.
  - **Monotonic Improvability**
    - 새 데이터·공식·패턴을 추가할수록 과거 결론이 자동으로 개선될 수 있어야 한다.
  - **Plane Separation**
    - Interaction / Agent / Data / Compute+Governance Plane을 분리한다.
    - 각 Plane은 역할·책임·의존성이 명확해야 한다.
  - **Agent as Human-Analog**
    - Agent는 "엔진"이 아니라 **업무 역할을 가진 준-사람 단위**로 정의한다.
    - EvidenceCollector/ValueStore/Fusion 등은 "엔진(Engine)"으로 별도 취급한다.

---

## 2. High-level Architecture – 4 Planes

UMIS v8 전체는 다음 4개의 Plane으로 구성된다. 각 Plane은 `umis_v8.yaml.planes.*`에 1:1로 매핑된다.

1. **Interaction Plane**
   - 사람/시스템이 UMIS에게 질문하고 결과를 받는 계층
   - 예: CLI, Web UI, Notebook, API, Agent Call(@Observer, @Explorer 등)
2. **Agent Plane**
   - 도메인/업무 역할을 가진 에이전트 계층
   - 예: Observer, Explorer, Calculator, Estimator, Validator, Guardian
3. **Data Plane**
   - 외부 세계의 데이터를 수집/정규화/구조화하는 계층
   - 예: Canonical/Projected Index, Knowledge Graph, Raw YAML, Memory
4. **Compute & Governance Plane**
   - 값(Value)을 계산·추론하고, 품질/정책을 관리하는 계층
   - Value Engine, Fusion Engine, Policy System, Guardian/Validator가 포함된다.

시각화하면 다음과 같다.

```
[Interaction Plane]
  - CLI / Web / API / Notebook / Agent Calls
              │
              ▼
[Agent Plane]
  Observer / Explorer / Strategist (optional)
  Calculator / Estimator / Validator
  Guardian
              │   (value_engine.get 호출)
              ▼
[Compute & Governance Plane]
  Value Engine (Truth Factory 재정의)
    - Value Graph Manager
    - Evidence Engine
    - Compute Engine (Calculator / Estimator)
    - Fusion & Validation Engine
              │
              ▼
[Data Plane]
  Canonical / Projected / KG / Raw / Memory
```

---

## 3. Value Graph – UMIS v8의 중심 모델

### 3.1 개념 정의

- **Value Graph**
  - **노드(Node)**: Metric/변수/파라미터 (예: `TAM_Korea_EdTech_2025`, `ARPU_Premium`, `Churn_rate`)
  - **엣지(Edge)**:
    - 공식(Formula): `Revenue = Users × ARPU`
    - 경험 규칙(Heuristic): "구독형 SaaS에서 ARPU의 70%는 플랜 가격" 등
    - 추론 규칙(Inference): "이 패턴을 가진 시장은 일반적으로 Gross Margin 40–60%"
- **Value Candidate**
  - 하나의 Metric에 대해 다양한 방법론으로 계산하거나 추정한 **값 후보들의 집합**
  - 예: 공식 기반 값, interpolation, Fermi 추정, LLM Prior 등

### 3.2 역할

- Value Graph는 UMIS v8의 **내부 세계 모델**이다.
- Value Engine은 Value Graph 위에서:
  - 필요한 노드/서브그래프를 탐색하고,
  - Evidence/공식/추정을 적용하여 Value Candidates를 생성하고,
  - Fusion/Validation을 거쳐 최종 **ValueRecord(VAL-*)**로 승격한다.

### 3.3 Metric 중심 설계

- v8에서는 Truth Factory를 **하나의 선형 파이프라인**이 아니라,
  **Metric 단위 미니-파이프라인들의 집합**으로 본다.
- 각 Metric은:
  - 어떤 Evidence 소스를 우선 사용할지,
  - 어떤 공식/계산을 적용할지,
  - Prior를 허용할지 여부,
  - 품질 기준(최소 literal 비율, 최대 스프레드 등)
  을 스스로 정의한다.

이 Metric 정의는 `umis_v8.yaml.compute_governance_plane.value_engine.metrics_spec`에 선언된다.

---

## 4. Interaction Plane – UMIS와 대화하는 방식

### 4.1 역할

- 인간/외부 시스템이 UMIS와 상호작용하는 모든 엔드포인트를 정의한다.
- 예시 인터페이스
  - CLI: `python scripts/query_rag.py`, `python scripts/query_system_rag.py`
  - Web/UI: 대시보드, 리포트 뷰어
  - API: REST/GraphQL/gRPC 등
  - Agent Call: "@Explorer, 구독 모델 패턴 찾아줘"

### 4.2 설계 원칙

- Interaction Plane은 **“무엇을 원하는가(What)”**에 집중해야 하고,
  **“어떻게 계산되는가(How)”**는 아래 Plane에 위임해야 한다.
- 모든 Interaction은 궁극적으로 `value_engine.get(metric_id, context, policy)` 호출로 수렴한다.

Mapping:
- `umis_v8.yaml.planes.interaction_plane` – 엔드포인트 종류, 주요 사용 시나리오, 권한 모델 등을 정의.

---

## 5. Agent Plane – 사람처럼 생각하는 역할 단위

### 5.1 주요 에이전트 (권장 기본 세트)

- **Observer (Albert)**
  - 역할: 시장 구조/가치사슬/행위자/메커니즘 관찰 및 서술
  - 산출물: `DEL-MARKET_REALITY_REPORT-*`
  - 숫자가 필요할 때마다 Value Engine에 질의
- **Explorer (Steve)**
  - 역할: 패턴/사례 기반 기회 발굴, Rough sizing, ROI 시사점 도출
  - 산출물: `DEL-OPP_PORTFOLIO-*`
  - Draft 단계에서는 Prior 허용, 최종 단계에서는 Value Engine을 통한 재계산 필수
- **(선택) Strategist**
  - 역할: 전략/포트폴리오 설계, 실행 계획 정리
  - 산출물: `DEL-STRATEGY_PLAYBOOK-*`

- **Calculator (Bill)**
  - 역할: 공식/분해/시나리오/수렴을 통한 값 후보(Value Candidates) 생성
  - Tracks: exact / convergence / fermi
- **Estimator (Fermi)**
  - 역할: 구조 기반 Prior Specialist (Last Resort)
  - 책임: LLM Prior를 이용해 부족 변수를 메운다. 재귀 금지.
- **Validator (Rachel)**
  - 역할: 데이터 정의/출처/신뢰도 검증, EvidenceBundle 강화
  - 책임: Official/Commercial/Curated 소스를 분류하고 신뢰도 평가
- **Guardian (Stewart)**
  - 역할: 정책/품질/토큰/순환/목표 정렬 감독
  - 산출물: 메타데이터, RAE 평가, Alert

### 5.2 Agent Plane의 원칙

- Agent는 **사람처럼 대화 가능한 역할 단위**로 설계한다.
- EvidenceCollector/ValueStore/FusionEngine은 Agent가 아니라 **Engine**이다.
- 모든 Business Layer Agent(Observer/Explorer/Strategist)는 **VAL-*만 직접 참조**한다.

Mapping:
- `umis_v8.yaml.planes.agent_plane.agents.*` – 각 에이전트의 역할/책임/산출물/제약 정의.
- `umis_v8.yaml.planes.agent_plane.workflows` – Observer/Explorer/Strategist 워크플로.

---

## 6. Data Plane – Evidence를 관리하는 층

### 6.1 구성 요소

- **Canonical Index (CAN-*)**
  - 정규화된 원본 청크 저장소
  - anchor_path + content_hash 기반 식별
- **Projected Index (PRJ-*)**
  - Agent/Task별 검색 뷰
  - `config/projection_rules.yaml`에 기반해 Canonical에서 파생
- **Knowledge Graph (GND-/GED-*)**
  - 개념/패턴/관계/수치 간의 그래프
  - curated YAML 기반 온보딩, `source_tier_1b_curated_internal`로 분류
- **Raw/Structured Data**
  - YAML/CSV/JSON, DART, 상업 리포트 등
- **Memory (MEM-/RAE-*)**
  - Query/Goal/RAE Evaluation 기록
  - 순환/목표 이탈/품질 패턴 분석에 사용

### 6.2 Source Tier

- 외부 세계 데이터의 우선순위를 정의한다.
- 기본 값(예시, `umis_v8.yaml.data_plane.data_sources.source_tier`):
  - 1: official – 정부/공식 통계, DART, 국제기구
  - 1b: curated_internal – 검수된 패턴/KG YAML
  - 2: commercial – 검증된 상업 리포트/증권사
  - 3: structured_estimation – Truth Engine 기반 구조적 추정 결과
  - 4: llm_baseline – 일반 LLM 지식(Prior)

Mapping:
- `umis_v8.yaml.planes.data_plane.*` – RAG/KG/Memory 구조 및 데이터 우선순위 정의.

---

## 7. Compute & Governance Plane – Value Engine

Compute & Governance Plane은 **값을 계산/추론하고 품질을 보증하는 핵심 엔진**이다.

### 7.1 Value Engine 개념

- **Value Engine = Truth Factory의 v8 재정의**
- API:
  - `value_engine.get(metric_id, context, policy) -> ValueRecord(VAL-*)`
- 내부 구성:
  1. Value Graph Manager
  2. Evidence Engine
  3. Compute Engine (Calculator / Estimator)
  4. Fusion & Validation Engine

Mapping:
- `umis_v8.yaml.compute_governance_plane.value_engine.*`

### 7.2 Origin Level (계산 내부 레벨)

- Data Plane의 source_tier와 혼동하지 않기 위해, 계산 파이프라인 내부 레벨을 별도로 정의한다.
- 예: `umis_v8.yaml.compute_governance_plane.value_engine.terminology.origin_level`:
  - level_1_official – Validator/Official 값
  - level_1b_curated – EvidenceCollector/Curated Internal
  - level_2_validated – Validator가 추가 검증한 값
  - level_3_calculated – Calculator(Fermi/공식) 산출
  - level_4_prior – Estimator Prior

### 7.3 Value Engine 기본 파이프라인 (기본값)

Value Engine은 Metric별로 다른 파이프라인을 지원하지만, 기본 순서는 다음과 같다.

1. **Evidence Collection (Evidence Engine)**
   - Data Plane에서 EvidenceBundle 생성
   - source_tier 우선순위와 latency/cost 프로파일을 고려
2. **Structured Calculation (Compute Engine – Calculator)**
   - 공식/분해/시나리오/수렴을 통해 Value Candidates 생성
3. **Prior Filling (Compute Engine – Estimator)**
   - 부족 변수에 한해 구조 기반 Prior 생성
   - 재귀 금지, hard_bounds 준수
4. **Fusion & Validation (Fusion Engine + Governance)**
   - Evidence/Calculated/Prior 후보들을 정책 기반으로 합성
   - Validator/Guardian 정책을 적용해 품질/리스크 체크
   - 최종 ValueRecord(VAL-*)로 승격

Metric별로 이 기본 파이프라인을 override/축소/확장할 수 있다.

---

## 8. Metrics Spec – Metric 단위 미니 파이프라인

### 8.1 목적

- 각 Metric이 **어떤 Evidence/공식/Prior/품질 기준**을 사용하는지 명시적으로 정의한다.
- Metric 정의만 보면 Value Engine이 어떻게 작동하는지 이해할 수 있어야 한다.

### 8.2 스켈레톤 구조 (개념)

`umis_v8.yaml.compute_governance_plane.value_engine.metrics_spec`는 대략 다음과 같은 구조를 가진다.

```yaml
metrics_spec:
  defaults:
    quality_requirements:
      min_literal_ratio: 0.5
      max_spread_ratio: 0.5
    allow_prior: true

  metrics:
    - id: "TAM_Korea_EdTech_2025"
      category: "market_size"
      dimensions: ["country", "sector", "year"]
      default_context:
        country: "KR"
        sector: "EdTech"
        year: 2025
      pipeline:
        stages: ["evidence_official", "structured_calculation", "fusion"]
        allow_prior: false
      quality_requirements:
        min_literal_ratio: 0.7
        max_spread_ratio: 0.3
      notes:
        - "신규 시장이 아니므로 Prior 사용을 금지한다."

    - id: "TAM_Global_NewCategory_2030"
      category: "market_size"
      dimensions: ["region", "year"]
      pipeline:
        stages: ["evidence_wide", "structured_calculation", "prior", "fusion"]
        allow_prior: true
      quality_requirements:
        min_literal_ratio: 0.3
        max_spread_ratio: 0.7
      notes:
        - "신규/불확실 시장으로 Prior 사용 허용, policy_tag=experimental 우선 적용."
```

실제 구현에서는 Metric 수백 개를 이 스펙에 따라 선언하고, Value Engine은 이 선언을 해석해 Value Graph를 실행한다.

---

## 9. Governance – Guardian/Validator와 Policy System

### 9.1 Validator

- 역할: 데이터 정의/출처/신뢰도 검증, EvidenceBundle 강화
- 책임:
  - Official/Commercial/Curated 소스를 분류하고 source_tier 할당
  - origin_level_1/1b/2 값 생산

### 9.2 Guardian

- 역할: 정책/품질/토큰/순환/목표 정렬 감독
- 책임:
  - Fact-check Gate 운영 (ValueRecord 승격 전 검증)
  - 정책 기반 품질 지표 관리
    - min_literal_ratio, min_convergence_methods, max_spread_ratio 등
  - Estimation vs 현실 데이터 비교 (후행 검증)

### 9.3 Policy System

- `policies.yaml` 또는 `umis_v8.yaml.compute_governance_plane.policies`에서 정의.
- 예시 정책 축:
  - 모드: evidence_only / evidence_preferred / exploration_first
  - 용도: reporting / decision / exploration
  - 허용 Prior 비중, 허용 스프레드, 최소 literal 비율 등

---

## 10. File & Config Map (v8 기준)

v8에서는 다음과 같은 파일 구성을 목표로 한다. 초기 skeleton 단계에서는 일부만 존재할 수 있다.

- `umis_v8.yaml`
  - 시스템 메타 + 4 Planes 정의 + Value Engine + Metrics Spec skeleton
- `config/schema_registry.yaml`
  - EvidenceBundle, TruthCandidate, EstimationResult, ValueRecord, MetricSpec 등 스키마
- `config/projection_rules.yaml`
  - Canonical → Projected 규칙, Agent별 검색 뷰 정의
- `config/runtime.yaml`
  - LLM 라우팅, 모드(evidence_only/hybrid/rag_full), Circuit Breaker, Fail-safe 정책
- `config/policies.yaml` (또는 `umis_v8.yaml` 내 `compute_governance_plane.policies`)
  - Guardian/Validator 정책, Fact-check Gate 규칙

---

## 11. Migration Note – v7에서 v8으로의 개념 전환

- **Truth Factory → Value Engine**
  - v7의 4-Stage Fusion Estimator 중심 구조에서, v8은 Value Graph/Value Engine 중심 구조로 전환한다.
- **Estimator 역할 축소·정제**
  - v7: Estimator가 Evidence/Prior/Fermi/Fusion 대부분을 소유
  - v8: Estimator는 Prior Specialist + 일부 구조 추론에 집중, Fusion은 전역 엔진으로 분리
- **Quantifier → Calculator**
  - 이름/역할을 Calculator로 표준화, 공식/분해/수렴 허브로 재정의
- **Value Store(VAL-*)의 강화**
  - v7에서도 실질적으로 존재하던 "최종 값" 개념을, v8에서 명시적인 Value Store 레이어로 승격

---

## 12. 이 문서의 목표

- 이 문서는 v8 기준으로 UMIS를 **Value Graph 기반의 4-Plane 아키텍처**로 정의한다.
- 구현자는 이 문서와 `umis_v8.yaml` 스켈레톤만으로:
  - Plane/Agent/Data/Value Engine/Metric Spec의 경계를 이해하고,
  - 각 Plane을 독립적으로 구현/테스트/확장할 수 있어야 한다.
- 세부 스키마/정책/워크플로는 `umis_v8.yaml` 및 `config/*.yaml`에 위임하며,
  각 파일은 이 Blueprint와 1:1로 개념이 대응되도록 유지한다.
