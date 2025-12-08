## UMIS v9 아키텍처 블루프린트 (2025-12-05 기준)

### 0. 문서 목적

이 문서는 UMIS v9의 **전체 서비스 아키텍처**와 **현재 구현 현황**을 한눈에 볼 수 있도록 정리한 블루프린트다.

- **비기술 리더**는 이 문서 상단 섹션만 읽어도
  - UMIS v9가 어떤 일을 하는 시스템인지
  - 어떤 흐름으로 시장을 이해하고 기회를 찾는지
  - 지금 어느 정도까지 구현되었는지를 이해할 수 있다.
- **기술 담당자/아키텍트**는 하단의 스펙/POC 코드 설명을 통해
  - 실제 YAML 스키마 구조와
  - `umis_v9_core` POC 모듈들의 역할
  - 확장 시 고려해야 할 기술 포인트를 파악할 수 있다.

현재 POC의 대표 질문은 다음과 같다.

- "**한국 성인 어학교육 시장** 구조를 알고 싶어. Top-N 플레이어 구조 + 돈의 흐름에 따른 전후방 가치사슬도 함께 확인해줘. 진입 전략 후보 2–3개도 확인해보자."

---

## 1. 상위 레벨 개념 아키텍처 (비기술 관점)

### 1.1 네 가지 Plane

UMIS v9는 전체 시스템을 네 개의 Plane으로 나눈다.

- **Interaction Plane**: 사람이 시스템을 사용하는 인터페이스
  - CLI, Notebook, Web App, API 등
  - 예: 분석가는 Notebook에서 구조 분석 노트를 작성하고, 경영진은 Web App에서 결과 리포트를 본다.

- **Role Plane**: 역할(에이전트) 정의 레이어
  - 예: `structure_analyst`(구조 분석), `opportunity_designer`(기회 발굴), `strategy_architect`(전략 설계), `numerical_modeler`(수치 모델링), `reality_monitor`(현실 모니터링)
  - 이들은 **사람/앱의 Persona + Workflow**를 의미할 뿐, 엔진 자체는 아니다.

- **Substrate Plane**: 데이터를 어떻게 표현할지 정의하는 레이어
  - 현실/패턴/값/결정을 네 가지 그래프로 표현한다.
  - Evidence(근거), Outcome(실적), Value(계산 결과), Memory(학습/메모리), **Project Context(프로젝트별 사용자 상황)** 저장소도 이 레이어에 포함된다.

- **Cognition Plane**: 실제로 생각하고, 계산하고, 학습하는 엔진 레이어
  - Evidence Engine, World Engine, Pattern Engine, Value Engine, Strategy Engine, Learning Engine, Policy Engine 등으로 구성된다.

### 1.2 네 가지 그래프 (R/P/V/D)

- **Reality Graph (R-Graph)**
  - 실제 시장 세계를 표현하는 그래프
  - Actor(회사, 고객 세그먼트 등), Event, Resource, Money Flow, Contract, State 노드와 그 관계로 구성
  - 예: "성인 개인 학습자 → 오프라인 학원에 연간 1500억 결제" 같은 돈의 흐름이 Money Flow + Actor 간 Edge로 표현된다.

- **Pattern Graph (P-Graph)**
  - 반복되는 비즈니스 패턴과 문맥의 그래프
  - 예: 구독형 BM, 플랫폼 BM, 프랜차이즈 BM, 7 Powers에서 말하는 다양한 방어력 패턴 등

- **Value Graph (V-Graph)**
  - Metric(지표), ValueRecord(값), Parameter(파라미터)와 이들 사이의 관계
  - 예: `MET-Revenue`, `MET-SAM`, `MET-LTV` 같은 지표와, 이들을 계산하는 공식/경험적 관계

- **Decision Graph (D-Graph)**
  - Goal, Hypothesis, Strategy, Scenario, Action 노드로 전략 의사결정 구조를 표현
  - 예: "3년 내 성인 어학 시장에서 니치 X에서 점유율 10%"라는 Goal과, 이를 달성하기 위한 전략 포트폴리오.

### 1.3 대표 Workflow: 구조 분석(structure_analysis)

`structure_analysis`는 특정 시장의 구조/메커니즘 및 핵심 economics를 이해하기 위한 대표 Workflow다.

- **1단계 – Reality Snapshot**
  - World Engine이 Evidence/seed를 읽어 현재 시장을 R-Graph로 표현한다.
  - Adult Language POC에서는 `seeds/Adult_Language_Education_KR_reality_seed.yaml`을 그대로 읽어 구조를 만든다.

- **2단계 – Pattern 매칭**
  - Pattern Engine이 R-Graph를 보고 구독형 BM, 플랫폼 BM 등 대표 패턴을 인식한다.
  - 또한, 진입 전략 힌트 같은 갭 후보도 함께 제안한다.

- **3단계 – Metric 계산**
  - Value Engine이 R-Graph와 Metric 스펙(TAM/SAM/N_customers/Revenue 등)을 기반으로 주요 수치를 계산하거나 추정한다.

이 세 단계 결과를 바탕으로, 구조 분석 리포트나 기회 포트폴리오, 전략 시나리오 설계가 이루어진다.

---

## 2. 스펙 파일 구조 (YAML 설계 레벨)

### 2.1 `umis_v9.yaml` – 코어 스키마

`umis_v9.yaml`은 v9 시스템의 **최상위 스펙 파일**로, 전체 Ontology/Planes/Graphs/Engines/IDs/Policies/Workflows를 정의한다.

주요 섹션:

- **`umis_v9.meta`**: 버전, 설명, 레퍼런스 문서
- **`ontology`**: actor/event/resource/money_flow/contract/state/trait/quantity 등의 공통 Primitive 정의, **capability_traits** (조직 역량 Trait 체계)
- **`planes`**:
  - `interaction_plane`: CLI, Notebook, Web App, API 인터페이스 정의
  - `role_plane`: Role ID/설명/주요 엔진/기본 policy 모드
  - `substrate_plane.graphs`: R/P/V/D 그래프 구조
  - `substrate_plane.stores`: Evidence/Outcome/Memory/Value/**Project Context** 저장소 스키마
  - `substrate_plane.data_sources`: KOSIS, DART 등 외부 데이터 소스 정의
  - `cognition_plane.engines`: evidence/world/pattern/value/strategy/learning/policy 엔진 인터페이스 정의
- **`ids_and_lineage`**: 각 객체 ID Prefix, lineage 공통 스키마
- **`policies.quality_profiles`**: reporting_strict / decision_balanced / exploration_friendly 품질/리스크 프로필
- **`canonical_workflows`**: structure_analysis / opportunity_discovery / strategy_design / reality_monitoring 상위 Workflow 정의

현재 v9 POC에서는 이 스펙을 **직접 코드에서 일부 파싱**해 사용한다 (예: ValueEnginePOC가 metrics_spec를 읽어 Metric ID를 인지).

### 2.2 프로세스/에이전트/검증 스펙

- **`umis_v9_process_phases.yaml`**
  - `canonical_workflows.structure_analysis`를 **14개 Phase**로 세분화한 파일 (Greenfield)
  - `structure_analysis_for_project`를 **15개 Phase**로 확장 (Brownfield: **PH00** + PH01-PH14)
  - 예: `PH00_project_context_setup`(프로젝트 컨텍스트 설정, Brownfield 전용), `PH01_market_definition`(시장 정의), `PH02_domain_classification`, `PH05_player_identification`, `PH07_market_sizing`, `PH13_validation_gate`, `PH14_report_generation` 등
  - 각 Phase는 다음 정보를 가진다.
    - `owner` Role, 예상 `duration`
    - `inputs` / `activities` / `outputs`
    - `validation` 및 `success_criteria`

- **`umis_v9_agent_protocols.yaml`**
  - Role 간 협업 패턴을 정리한 파일 (v7 6-Agent 시스템의 역할을 v9 Role Plane에 맞게 일반화)
  - 예시 패턴:
    - `data_collection_request` (structure_analyst → reality_monitor)
    - `structure_to_numerical_support` (structure_analyst → numerical_modeler)
    - `opportunity_sizing_request` (opportunity_designer → numerical_modeler)
    - `structure_validation_request` (structure_analyst → numerical_modeler/reality_monitor)
  - 각 패턴에 대해 트리거(어느 Workflow/Phase에서 호출되는지), 요청 템플릿, 예상 산출물, 품질 힌트 등을 명시.

- **`umis_v9_validation_gates.yaml`**
  - 품질 보증을 위한 공통 검증 게이트 정의
  - Gate 타입 예시:
    - `mece_validation`: Needs/Domain/BM 분류의 ME/CE 검증
    - `four_method_convergence`: SAM 4-Method ±30% 수렴 여부 검증
    - `data_reliability_validation`: 데이터 신뢰도(평균 ≥70%) 및 SRC/Evidence ID 부여 확인
    - `summation_validation`: BM/도메인별 합산이 전체와 ±5% 이내 일치하는지 확인
    - `three_validator_gate`: numerical_modeler / reality_monitor / structure_analyst 3자의 최종 검증 매트릭스

### 2.3 전략/가치사슬/벤치마크 스펙

- **`umis_v9_strategic_frameworks.yaml`**
  - 전략 설계에 사용하는 대표 프레임워크를 Pattern/Decision Graph와 연결
  - 예:
    - `porter_5_forces`: 경쟁 구조 분석, 관련 Pattern(`PAT-market_concentration` 등)과 HHI/TopN share Metric 연결
    - `tam_sam_som`: 시장경계/TAM→SAM→SOM 프레임워크, `MET-TAM/MET-SAM/MET-SOM/MET-N_customers`와 매핑
    - `seven_powers`: 장기 방어력 평가, 7 Powers 관련 Pattern + 수익성/방어력 Metric과 연계
    - `blue_ocean_canvas`: 가치요소 재구성(Eliminate-Reduce-Raise-Create), `PAT-value_innovation`과 연결

- **`umis_v9_value_chain_templates.yaml`**
  - BM/도메인별 R-Graph 상 가치사슬 구조를 해석하기 위한 템플릿
  - 예:
    - `offline_academy_value_chain`: 콘텐츠 제작 → 마케팅/수강생 모집 → 수업 제공 → 고정비(임대/시설), 각 단계와 연결된 Metric 정의 (인건비/마케팅비/OPEX 등)
    - `online_platform_value_chain`: 공급자 온보딩 → 거래 처리/결제 → 플랫폼 인프라/지원, 수수료/매출/OPEX/감가상각 Metric과 연결

- **`umis_v9_pattern_benchmarks.yaml`**
  - 비즈니스 패턴별 전형적인 Metric 범위/특징 요약 (v7 Benchmarks 요약판)
  - 예:
    - `PAT-subscription_model`: 월 이탈률(Churn) 1–8%, Gross Margin 60–85% 등
    - `PAT-platform_business_model`: 플랫폼 수수료율 5–30%, Top3 매출 집중도 50–90%
    - `PAT-franchise_model`: 로열티 비율 관련 메모 등 (도메인별 값은 후속 작업에서 채움)

---

## 3. POC 코드 구조 (구현 현황)

### 3.1 그래프/월드 엔진 POC

- **`umis_v9_core/graph.py` – `InMemoryGraph`**
  - 매우 단순한 인메모리 그래프 구현
  - Node: `id`, `type`, `data`
  - Edge: `type`, `source`, `target`, `data`
  - 주요 메서드
    - `upsert_node(node_id, node_type, data)`
    - `add_edge(edge_type, source, target, data)`
    - `nodes_by_type(node_type)`
    - `neighbors(node_id, edge_type=None)`

- **`umis_v9_core/world_engine_poc.py` – `snapshot`**
  - `RealityGraphSnapshot(graph: InMemoryGraph, meta: Dict[str, Any])` 데이터클래스
  - `load_reality_seed(path)`
    - `seeds/Adult_Language_Education_KR_reality_seed.yaml`을 읽어
      - ACT-* → `actor` 노드
      - MFL-* → `money_flow` 노드 + `actor_pays_actor` edge
      - STA-* → `state` 노드로 변환
  - `snapshot(domain_id, region, segment, as_of)`
    - 현재는 `Adult_Language_Education_KR`만 지원
    - 나중에는 `domain_registry.yaml` 기반 일반화 예정
  - 상단에 v9 스펙 Ref 상수 정의
    - `PROCESS_PHASES_REF = "umis_v9_process_phases.yaml#structure_analysis"`
    - `AGENT_PROTOCOLS_REF = "umis_v9_agent_protocols.yaml"`
    - `VALIDATION_GATES_REF = "umis_v9_validation_gates.yaml#gate_types"`

- **`seeds/Adult_Language_Education_KR_reality_seed.yaml`**
  - Adult Language 도메인 R-Graph POC용 Reality seed
  - Actor 예시
    - 성인 개인 학습자(자비부담), 기업 고객, 오프라인 학원 Top3, 온라인 플랫폼 Top3, 대학 부설, 기업 교육 제공사 등
  - Money Flow 예시
    - 성인 개인 → 오프라인 학원/온라인 플랫폼, 기업 → 교육 제공사, 공급자 → 콘텐츠 제작사, 플랫폼 → 결제 플랫폼 등
  - State 예시
    - 시장 구조/집중도/롱테일 구조/핵심 비용 드라이버/진입 전략 힌트 등

### 3.2 Pattern Engine POC

- **`umis_v9_core/pattern_engine_poc.py` – `PatternEnginePOC`**
  - `match_patterns(graph: InMemoryGraph) -> List[PatternMatch]`
    - 구독형 BM 패턴 감지
      - `money_flow.traits.revenue_model == "subscription"` 존재 여부
      - 매칭 시 `pattern_id="PAT-subscription_model"`로 PatternMatch 반환
    - 플랫폼 BM 패턴 감지
      - `actor.traits.institution_type == "online_platform"` 존재 여부
      - 매칭 시 `pattern_id="PAT-platform_business_model"`로 PatternMatch 반환
  - `discover_gaps(graph: InMemoryGraph) -> List[GapCandidate]`
    - Reality seed의 `state.properties.entry_strategy_clues` 항목을 읽어
    - 각 힌트를 GapCandidate로 변환
      - 관련 패턴: `PAT-subscription_model`, `PAT-platform_business_model`
      - evidence: 어떤 state에서 나온 힌트인지 기록
  - 정식 Pattern Engine의 축소판으로, R-Graph만 보고 간단 패턴/갭을 제시하는 수준

### 3.3 Value Engine POC

- **`umis_v9_core/value_engine_poc.py` – `ValueEnginePOC`**
  - 타입 정의
    - `MetricRequest(metric_id, context)`
    - `ValueRecord(metric_id, context, point_estimate, quality, lineage)`
  - 초기화
    - `ValueEnginePOC(config_path="umis_v9.yaml")`
    - `umis_v9.yaml`에서 `value_engine.metrics_spec.metrics`를 파싱해 Metric 스펙을 인덱싱
  - 핵심 메서드: `evaluate_metrics(graph, metric_requests, policy_ref="reporting_strict")`
    - 현재 POC 지원 Metric
      - `MET-Revenue`
        - `actor.kind == "customer_segment"`인 payer → 공급자 `actor_pays_actor` edge를 따라가서
          연결된 `money_flow.quantity.amount`를 모두 합산 (연간 매출 근사치)
      - `MET-N_customers`
        - Reality seed에서
          - 성인 개인 학습자의 `metadata.approx_population`
          - 기업 고객의 `metadata.approx_company_count`
          을 합산해 전체 고객 수 근사
      - `MET-Avg_price_per_unit`
        - `Revenue / N_customers`로 연평균 단가 계산 (N_customers가 0이면 None)
    - 그 외 Metric
      - 아직 구현되지 않은 Metric은 `point_estimate=None`, `quality.status="not_implemented"`로 반환
  - `ValueRecord.quality`/`lineage`
    - POC에서는
      - `literal_ratio = 1.0`(직접 계산) 또는 `0.0`(미구현)
      - `spread_ratio = 0.0`
    - `lineage`에는 ValueEnginePOC 실행 정보와 엔진 ID(`"value_engine"`)를 남겨, v9의 lineage 스키마와 형식을 맞춘다.

### 3.4 POC 데모 스크립트

- **`examples_structure_analysis_poc.py`**
  - 역할: Adult Language 도메인에 대해 최소한의 structure_analysis 데모 실행
  - 현재 동작
    - 상단에 참조 정보 출력
      - `umis_v9_process_phases.yaml#structure_analysis`
      - `umis_v9_agent_protocols.yaml`
      - `umis_v9_validation_gates.yaml`
    - `world_engine_poc.snapshot` 호출로 Reality Snapshot 로딩
    - Actors / Money Flows / States 구조를 콘솔에 출력
  - 향후 확장
    - `PatternEnginePOC`와 `ValueEnginePOC`를 여기에 통합해
      - 구조 + 패턴 + 핵심 Metric까지 한 번에 출력하는 end-to-end structure_analysis POC로 확장 가능

---

## 4. 구현 현황 요약

### 4.1 스펙 vs 구현

- **스펙 작성 완료 (YAML)**
  - 코어 스키마: `umis_v9.yaml`
  - 프로세스/에이전트/검증: `umis_v9_process_phases.yaml`, `umis_v9_agent_protocols.yaml`, `umis_v9_validation_gates.yaml`
  - 전략/가치사슬/벤치마크: `umis_v9_strategic_frameworks.yaml`, `umis_v9_value_chain_templates.yaml`, `umis_v9_pattern_benchmarks.yaml`

- **POC 구현 완료 (Python)**
  - R-Graph: `umis_v9_core/graph.py`
  - World Engine POC: `umis_v9_core/world_engine_poc.py`
  - Pattern Engine POC: `umis_v9_core/pattern_engine_poc.py`
  - Value Engine POC: `umis_v9_core/value_engine_poc.py`
  - Demo: `examples_structure_analysis_poc.py`

- **아직 미구현(설계만 존재)**
  - Evidence Engine 실제 구현 및 외부 데이터 소스 연동
  - 정식 Pattern Engine (pattern_graph + value_chain_templates + 전략 프레임워크 연동, **execution_fit_score** 계산)
  - 정식 Value Engine (Metric Resolver 전체 Stage 및 모든 Metric 구현, **project-level Metric** 지원)
  - Strategy Engine / Learning Engine / Policy Engine의 런타임 수준 구현
  - **Project Context Layer** (PH00 Phase, focal_actor R-Graph 구성, Brownfield/Greenfield 워크플로우 분기)

### 4.2 Adult Language POC에서 실제로 할 수 있는 일

- Reality seed 기반으로
  - 주요 Actor/돈의 흐름/상태(시장 구조/집중도/롱테일/비용 드라이버/진입 전략 힌트)를 시각적으로 이해할 수 있다.
- 간단한 Pattern 인식
  - 구독형 BM, 플랫폼 BM 패턴 존재 여부를 자동으로 파악할 수 있다.
- 기본적인 Metric 계산
  - Adult Language 시장의 총 매출(근사)과 고객 수, 평균 단가 수준을 Reality seed에서 바로 계산할 수 있다.

---

## 5. 향후 확장 방향 (요약)

- **Evidence Engine v0**
  - KOSIS/DART/Web Evidence를 실제로 연동해 Reality/Value를 seed 기반이 아니라 외부 데이터로 채우기
  - **내부 데이터 연동** (ERP/CRM/재무 시스템 → Evidence Store → Project Context)

- **Pattern/Value/Strategy 엔진 정식 구현**
  - Pattern Engine: `pattern_graph`, `umis_v9_strategic_frameworks.yaml`, `umis_v9_value_chain_templates.yaml`, `umis_v9_pattern_benchmarks.yaml`와 긴밀히 연동
    - **structure_fit_score + execution_fit_score** 이중 평가 구현
  - Value Engine: MET-TAM/SAM/SOM/N_customers/Revenue/Unit Economics 전반을 4-Stage Metric Resolver로 평가
    - **market-level + project-level Metric** 분리 계산
  - Strategy Engine: Goal/Pattern/Reality/Value를 이용해 전략 후보 생성 및 포트폴리오 평가
    - **Project Context 제약/선호 자동 반영**

- **Project Context Layer 구현** (신규)
  - PH00 Phase 실행기 (조직 현황 구조화 → focal_actor R-Graph 구성)
  - Greenfield/Brownfield/Hybrid 워크플로우 분기 로직
  - Capability-Pattern 매칭 엔진
  - Project-aware Metric 계산 (Baseline/Scenario/Delta)

- **End-to-end Workflow 실행기**
  - `umis_v9_process_phases.yaml`를 실제로 실행하는 Workflow Executor
  - `umis_v9_agent_protocols.yaml`/`umis_v9_validation_gates.yaml`에 따라 자동으로 협업/검증을 orchestrate
  - **structure_analysis_for_project** / **opportunity_discovery_for_project** 워크플로우 구현

---

## 6. Project Context Layer (2025-12-05 추가)

### 6.1 핵심 개념

v9는 시장 분석뿐 아니라 **"특정 조직의 관점에서"** 기회/전략을 평가할 수 있도록 Project Context Layer를 제공한다.

**주요 구성 요소**:
- **project_context_store**: 프로젝트별 사용자/조직 상황 저장소 (PRJ- prefix)
- **focal_actor**: R-Graph의 Actor 중 분석 주체 조직
- **capability_traits**: 조직 역량을 Trait 기반으로 표현 (Ontology lock-in 방지)
- **mode**: greenfield / brownfield / hybrid 구분

### 6.2 Greenfield vs Brownfield

**Greenfield (기존 워크플로우)**:
- 입력: domain_id, region만 필요
- 출력: 시장 전체 구조 분석
- 예: "한국 성인 어학교육 시장은 어떻게 생겼는가?"

**Brownfield (확장 워크플로우)**:
- 입력: domain_id, region + **project_context_id**
- 출력: 시장 구조 + **focal_actor 위치/기회/실행 가능성**
- 예: "우리 오프라인 학원 체인이 이 시장에서 디지털 전환하려면?"

### 6.3 PatternEngine 이중 평가

**structure_fit_score**:
- 시장 구조에 이 패턴이 얼마나 적합한가? (기존)

**execution_fit_score**:
- 이 조직이 이 패턴을 실행할 수 있는가? (신규)
- Project Context의 capability_traits, constraints 기반

### 6.4 ValueEngine Project-level Metric

**market-level Metric**:
- MET-TAM, MET-SAM (시장 전체)

**project-level Metric**:
- MET-SOM_for_project (이 조직이 가져갈 수 있는 파이)
- MET-Base_Revenue_for_project (현재)
- MET-Scenario_Revenue_for_project (전략 실행 시)
- MET-Delta_Revenue_for_project (증분)

**참조 문서**:
- `umis_v9_project_context_layer_design.md`: 상세 설계
- `UMIS_v9_Project_Context_Philosophy_Alignment.md`: 철학 정합성 분석
- `examples/project_context_examples.yaml`: 입력 예시 3가지

---

이 블루프린트는 현재 v9 POC의 "살아있는 설계도" 역할을 하며, 스펙과 구현이 확장될 때마다 함께 유지보수되는 것을 전제로 한다.
