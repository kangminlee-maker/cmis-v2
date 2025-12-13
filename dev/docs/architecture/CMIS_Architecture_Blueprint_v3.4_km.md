# CMIS v3.4 아키텍처 블루프린트 (Philosophy-aligned Update)

**버전**: v3.4  
**업데이트**: 2025-12-12  
**상태**: Production Ready (엔진 구현 기준) / Blueprint Updated (철학 정렬)

---

## Executive Summary

CMIS (Contextual Market Intelligence System)는 시장/비즈니스 세계를 **Graph-of-Graphs (R/P/V/D)** 로 표현하고, **Understand → Discover → Decide → Learn** 루프로 시장 분석과 전략 설계를 수행하는 Market Intelligence OS입니다.

이번 업데이트의 핵심은 “기능 목록”을 늘리는 것이 아니라, **CMIS의 설계철학(증거·재현성·모델 중심·역할 분리·유한 컨텍스트 대응)** 이 시스템 구조에 **명시적으로 드러나도록** 블루프린트를 재정렬한 것입니다.

---

## 1. CMIS가 해결하는 문제

### 1.1 CMIS가 만드는 결과물

CMIS의 출력은 단순한 “답변 텍스트”가 아니라, 다음의 **재현 가능한 산출물 묶음**입니다.

- **세계(World) 설명**: R-Graph(현실 구조) 기반 구조/행위자/흐름 설명
- **변화(Change) 제안**: Pattern(메커니즘) 기반 변화 가설 및 적용 가능성
- **결과(Result) 예측/평가**: V-Graph(Metric) 기반 수치·분포·품질·불확실성
- **논증(Argument) 및 추적(Lineage)**: Evidence/Derived/Prior/Fusion 경로 및 출처/근거

즉, CMIS는 “시장 인사이트”를 **근거(증거) + 구조(모델) + 수치(값) + 결정(전략)** 으로 패키징합니다.

---

## 2. 설계 철학 및 컨셉 (요약 + 구성요소 매핑)

아래 철학은 “문구”가 아니라, **시스템 구성요소로 구현**되어야 합니다.

### 2.1 Model-first, Number-second

- **의미**: 숫자(ROI, TAM, 점유율)는 “세계 모델(구조/패턴)” 위에서 계산되는 결과입니다.
- **구현 요소**
  - R-Graph(World Engine)로 구조를 먼저 구성
  - P-Graph(Pattern Engine)로 반복 메커니즘을 인식
  - V-Graph(Value Engine)로 값을 계산(단순 산술이 아니라 “근거 기반 해결”)
  - D-Graph(Strategy Engine)로 목표/전략/행동을 구조화

### 2.2 Evidence-first, Prior-last

- **의미**: 가능한 한 **직접 Evidence**로 해결하고, 불가피할 때만 Prior/추정으로 넘어갑니다.
- **구현 요소**
  - Evidence Engine: 소스/티어/수집방식 명시 + Early Return
  - Value Engine: 4-Stage Resolution  
    `Direct Evidence → Derived → Prior → Fusion/Validation`
  - Policy Engine: 모드(Reporting/Decision/Exploration)에 따라 Prior 허용/차단

### 2.3 Re-runnability & Auditability (재현 가능성 + 감사 가능성)

- **의미**: “누가/언제 실행해도” 동일한 입력이면 동일한 결과를 재현할 수 있어야 합니다.
- **구현 요소**
  - Evidence Store: evidence_id + source_tier + retrieved_at + source_id + content_ref
  - Value Store: ValueRecord의 영구 저장 + lineage 참조
  - Graph Snapshots: as_of/segment 기준의 스냅샷을 안정적으로 재생성 가능
  - ID & Lineage Schema: 모든 산출물이 “어디서 왔는지”를 구조적으로 추적

> 용어를 굳이 쓰면, Substrate Plane(Stores/Graphs)이 CMIS의 “단일 진실의 원천(SoT)” 역할을 수행합니다.  
> 단, SoT는 “하나의 DB”를 뜻하는 게 아니라 **재현 가능한 정본(정의된 저장/식별/추적 규칙)** 을 뜻합니다.

### 2.4 Graph-of-Graphs: R/P/V/D

- **의미**: 시장 인텔리전스는 단일 그래프로 끝나지 않습니다. 현실/패턴/값/결정이 서로 다른 규칙을 가집니다.
- **구현 요소**
  - R-Graph: 행위자/거래/상태/흐름
  - P-Graph: 반복 메커니즘(패턴)과 조합/충돌 관계
  - V-Graph: Metric, ValueRecord, Formula, Empirical relation
  - D-Graph: Goal, Strategy, Scenario, Action (결정 공간)

### 2.5 Trait 기반 설계 (Ontology lock-in 최소화)

- **의미**: “산업별 고정 스키마”로 잠기지 않고, trait 조합으로 패턴/역량/조건을 정의합니다.
- **구현 요소**
  - Ontology primitives + core traits + domain traits
  - Pattern Engine: trait/구조 기반 매칭
  - ProjectContext: capability_traits 기반 execution fit

### 2.6 Agent = Persona + Workflow + View (엔진이 아님)

- **의미**: Agent는 “추론 엔진”이 아니라, **역할(관점)과 workflow(절차)와 출력 형태(view)** 를 고정하는 인터페이스입니다.
- **구현 요소**
  - Role Plane: structure_analyst / opportunity_designer / strategy_architect / numerical_modeler / reality_monitor
  - Canonical Workflows: 역할별 대표 실행 절차(재현 가능한 실행 단위)
  - Policy Engine: 역할/용도에 맞는 품질/리스크 게이트 제공

> 이 원칙은 “간결함” 때문이 아니라,  
> **테스트 가능성, 재현 가능성, 책임 소재(어느 엔진이 무엇을 했는지)** 를 확보하기 위한 구조적 선택입니다.

### 2.7 Ledger-based Orchestration (유한 컨텍스트 대응)

- **의미**: 컨텍스트 윈도우가 유한한 이상, 시스템은 “상태를 명시적으로 기록”해야 합니다.
- **구현 요소 (두 종류 Ledger)**
  1) **Project Ledger (지속)**: 프로젝트/시장 분석의 사실·증거·산출물 저장  
     → Substrate Plane(Stores/Graphs)가 담당  
  2) **Progress Ledger (진행)**: 실행 계획/단계/상태/재시도/스톨 감지 기록  
     → Workflow Runtime(Orchestrator) + Memory/Run Store가 담당

---

## 3. 아키텍처 개요: 4 Planes + Orchestration Runtime

CMIS는 “엔진 나열”이 아니라, 아래와 같은 **plane 분리**로 설계됩니다.

```text
┌─────────────────────────────────────────────────────────────┐
│ Interaction Plane (CLI / API / Web / Notebook)              │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Role Plane (Agent = Persona + Workflow + View)              │
│  - roles, policies, canonical workflows                     │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Orchestration Runtime (Workflow Executor + Ledgers)         │
│  - Project Ledger(참조) + Progress Ledger(관리)             │
│  - 정책 적용, 스톨/재시도/부분 재실행, 결과 번들링          │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Cognition Plane (Engines)                                   │
│  Evidence / World / Pattern / Value / Strategy / Learning   │
│  + Policy (cross-cutting)                                   │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Substrate Plane (Graphs + Stores = 재현 가능한 정본)         │
│  R/P/V/D Graphs + Evidence/Value/Project/Outcome/Memory     │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Graph-of-Graphs (R/P/V/D)

### 4.1 R-Graph (Reality Graph)

- **목적**: 시장 현실의 구조/행위자/흐름/상태를 표현
- **대표 노드**: Actor, Event, Resource, MoneyFlow, Contract, State
- **특징**
  - as_of(시점) slicing 지원
  - segment/region 컨텍스트 필터링
  - ProjectContext(우리 회사/프로젝트) overlay 지원

### 4.2 P-Graph (Pattern Graph)

- **목적**: 반복되는 비즈니스 메커니즘/패턴과 관계(조합/충돌)
- **특징**
  - Trait 기반 패턴 정의
  - composes_with / conflicts_with 등 관계 모델링
  - Context archetype을 통한 적용 조건 정리

### 4.3 V-Graph (Value Graph)

- **목적**: Metric, ValueRecord, Formula 관계를 표현
- **특징**
  - ValueRecord는 point estimate 뿐 아니라 **분포/품질/lineage**를 포함
  - Derived/Empirical 관계를 그래프로 표현(계산/검증 경로 명시)

### 4.4 D-Graph (Decision Graph)

- **목적**: Goal/Strategy/Scenario/Action을 구조화하여 결정 공간을 표현
- **특징**
  - 전략은 Pattern(또는 Gap)의 조합으로 정의 가능
  - 시나리오는 “가정 세트”와 연결되어 ValueEngine 시뮬레이션과 연동

---

## 5. Stores (재현 가능한 Project Ledger의 핵심)

### 5.1 Evidence Store

- 외부 데이터/문서/리포트 등 Evidence를 저장
- 최소 요구 필드(권장):
  - evidence_id, source_tier(official/curated/commercial…), source_id, retrieved_at
  - url_or_path(가능한 경우), content_ref(원문/파싱본), metadata(도메인/연도/정의)

### 5.2 Value Store

- ValueRecord(VAL-*)의 영구 저장소
- “계산 결과”가 아니라 **근거·품질·추적 포함 산출물**을 저장합니다.

### 5.3 Project Context Store

- Brownfield 분석의 기준점(우리 회사/프로젝트)을 저장
- baseline_state(현재 상태)와 assets_profile(역량)과 constraints_profile(제약)을 포함
- Outcome 반영 시 버전업(learning-driven versioning)

### 5.4 Outcome Store

- 실제 실행 결과(성과)를 기록
- LearningEngine이 예측 vs 실제 차이를 학습하는 입력

### 5.5 Memory / Run Store (권장 확장)

- Progress Ledger의 저장처
- 최소한 아래를 남길 수 있어야 합니다.
  - workflow_run_id, role_id, policy_ref
  - step list(status/result), stall_count, partial_replan 기록
  - 실행 시점, 사용된 evidence/value/pattern/strategy 참조

---

## 6. Cognition Plane: Engines (역할 + 핵심 API)

> 원칙: “엔진”은 계산/추론을 담당하고, “Role/Workflow”는 사용 절차와 출력 형태를 고정합니다.

### 6.1 Evidence Engine

**역할**: Evidence 수집/정규화/번들링

**핵심**
- Source tier: Official / Curated / Commercial 등
- Early Return + Cache
- (권장) 검색/쿼리 확장은 Evidence Engine 내부 전략 모듈로 포함

**API**
- `fetch_for_metrics(metric_requests, policy_ref) → evidence_bundle_ref`
- `fetch_for_reality_slice(scope, as_of) → evidence_bundle_ref`

---

### 6.2 World Engine

**역할**: Evidence를 R-Graph로 정규화하고 snapshot 제공

**핵심**
- RealityGraphStore + ProjectOverlay(프로젝트별 관점)
- as_of / segment / region 필터
- project_context 투영(ingest_project_context)
- evidence 반영(ingest_evidence)

**API**
- `snapshot(domain_id, region, segment, as_of, project_context_id?)`
- `ingest_project_context(project_context_id)`
- `ingest_evidence(domain_id, evidence_list|ids)`

---

### 6.3 Pattern Engine

**역할**: R/P-Graph 기반 패턴 인식 + 갭 발굴

**핵심**
- Structure Fit (시장 구조 적합)
- Execution Fit (Brownfield에서 실행 가능성; capability_traits 기반)
- Gap Discovery(있어야 하는데 없는 메커니즘)

**API**
- `match_patterns(graph_slice_ref, project_context_id?)`
- `discover_gaps(graph_slice_ref, project_context_id?)`

---

### 6.4 Value Engine

**역할**: Metric 해결(계산/추론/검증) 및 ValueRecord 생성

**핵심**
- 4-Stage Resolution  
  1) Direct Evidence  
  2) Derived (Formula + World snapshot)  
  3) Prior Estimation (마지막 수단)  
  4) Fusion/Validation (품질/일관성 검증)
- Lineage 완전 추적
- Policy에 따른 quality gates 적용

**API**
- `evaluate_metrics(metric_requests, policy_ref, project_context_id?)`
- `simulate_scenario(scenario_id, policy_ref, project_context_id?)`

---

### 6.5 Strategy Engine

**역할**: Goal/Pattern/Reality/Value 기반 전략 후보 탐색 및 평가

**핵심**
- Pattern → Strategy 변환(단일/조합/갭 기반)
- Greenfield/Brownfield 분리
- Execution Fit + ROI/Risk + Portfolio 최적화

**API**
- `search_strategies(goal_id, constraints, project_context_id?)`
- `evaluate_portfolio(strategy_ids, policy_ref, project_context_id?)`

---

### 6.6 Learning Engine

**역할**: Outcome 기반 시스템 개선(패턴/메트릭/프로젝트 컨텍스트)

**핵심**
- 예측 vs 실제 비교(OutcomeComparator)
- Pattern benchmark 갱신(PatternLearner)
- Metric belief/quality 조정(MetricLearner)
- ProjectContext 버전업(ContextLearner)

**API**
- `update_from_outcomes(outcome_ids)`
- `update_project_context_from_outcome(outcome_id, project_context_id)`

---

### 6.7 Policy Engine (cross-cutting)

**역할**: 품질/리스크/허용치 정책을 모든 엔진에 제공

**정책 모드 예시**
- reporting_strict: Evidence 중심, prior 최소/불가
- decision_balanced: Evidence 우선, prior 제한적 허용
- exploration_friendly: 탐색용, prior/패턴 활용 허용

---

## 7. Greenfield vs Brownfield (정의/동작 차이)

### 7.1 정의 (핵심 기준)

- **Greenfield**: “나(ProjectContext)” 없이 시장을 중립적으로 분석  
  - ProjectContext 없음, focal_actor 없음  
  - 단, **최소 제약(자본/기간/팀 규모)** 는 입력 가능
- **Brownfield**: “나(ProjectContext)” 관점에서 분석  
  - ProjectContext 있음, focal_actor 있음  
  - 제약/자산/기준선(baseline_state) 반영

> Greenfield ≠ 신규, Brownfield ≠ 확장  
> 핵심은 “나(ProjectContext)의 존재 여부”입니다.

### 7.2 엔진별 차이

- Pattern Engine
  - Greenfield: Structure Fit 중심
  - Brownfield: Structure Fit + Execution Fit
- Strategy Engine
  - Greenfield: ROI/리스크 중심 + 최소 제약 필터
  - Brownfield: Execution Fit + 제약 반영 + baseline 기반 ROI
- Value Engine
  - Brownfield: 프로젝트 레벨 메트릭(MET-Base_Revenue_for_project 등) 계산 가능

---

## 8. Orchestration Runtime: Canonical Workflows + Ledgers

### 8.1 Canonical Workflows (역할별 표준 절차)

CMIS는 “임의의 프롬프트”보다, 아래 워크플로를 **재현 가능한 실행 단위**로 둡니다.

```yaml
structure_analysis:
  role: structure_analyst
  steps:
    - world_engine.snapshot
    - pattern_engine.match_patterns
    - value_engine.evaluate_metrics (reporting_strict)

opportunity_discovery:
  role: opportunity_designer
  steps:
    - world_engine.snapshot
    - pattern_engine.discover_gaps
    - value_engine.evaluate_metrics (exploration_friendly)

strategy_design:
  role: strategy_architect
  steps:
    - strategy_engine.search_strategies
    - strategy_engine.evaluate_portfolio (decision_balanced)

reality_monitoring:
  role: reality_monitor
  steps:
    - learning_engine.update_from_outcomes
    - value_engine.evaluate_metrics (reporting_strict)
```

### 8.2 Ledger 설계 (Project + Progress)

**Project Ledger (지속 / 재현성의 기반)**
- EvidenceStore, ValueStore, Graph Snapshots(R/P/V/D), ProjectContext, Strategy/Scenario 산출물

**Progress Ledger (진행 / 유한 컨텍스트 대응)**
- workflow_run 단위로:
  - 현재 단계, 완료 여부, 다음 호출, 스톨 감지, 재시도/부분 재실행 기록
  - 사용된 policy_ref/role_id 기록
  - 참조한 evidence_id/value_id/pattern_id/strategy_id 링크 유지

> “Progress Ledger를 어디에 저장하느냐”는 구현 선택입니다.  
> 하지만 “Progress Ledger가 존재해야 한다”는 구조적 요구입니다.

---

## 9. 데이터 흐름 (Understand → Discover → Decide → Learn)

### 9.1 Understand

```text
EvidenceEngine → EvidenceStore
        ↓
WorldEngine.ingest/snapshot → R-Graph slice
        ↓
PatternEngine.match_patterns → Pattern Matches
        ↓
ValueEngine.evaluate_metrics → ValueRecords (V-Graph + ValueStore)
```

### 9.2 Discover

```text
R-Graph slice + P-Graph
        ↓
PatternEngine.discover_gaps
        ↓
Gap Candidates + (추가 Metric 평가: sizing)
```

### 9.3 Decide

```text
Goal(D-Graph) + Pattern/Gap + ValueRecords
        ↓
StrategyEngine.search_strategies
        ↓
Strategy candidates + Portfolio evaluation
        ↓
(옵션) Scenario 생성 → ValueEngine.simulate_scenario
```

### 9.4 Learn

```text
OutcomeStore(실제 결과)
        ↓
LearningEngine.update_from_outcomes
        ↓
Pattern benchmarks / Metric belief / ProjectContext versioning
        ↓
(Understand로 루프)
```

---

## 10. 품질/신뢰성 메커니즘

### 10.1 Evidence 품질

- Source tier로 신뢰도/목적 분리 (Official/Curated/Commercial/…)
- retrieved_at, 정의/범위(metadata), 원문(content_ref) 보관
- (권장) 동일 Evidence에 대한 재수집/비교 지원

### 10.2 Value 품질

- quality profile(예: min_literal_ratio, max_spread_ratio)
- policy 모드에 따른 prior 허용/차단
- fusion/validation 단계에서 논리적 상하한, 일관성 체크

### 10.3 재현성/감사

- 모든 주요 객체: ID prefix + lineage
- workflow run 기록: “무엇을 호출했고 무엇이 생성되었는지”를 남김
- 캐시/early return도 “왜 그 결론이 났는지”를 가리지 않도록 lineage에 표시

---

## 11. 구현 현황 (v3.3 baseline)

> 아래는 구현 기준 현황(기존 블루프린트 기준)을 유지하되, 구조 설명을 철학 정렬 관점에서 재배치했습니다.

- Evidence Engine: 완료
- Pattern Engine: 완료
- Value Engine: 완료
- World Engine: 완료
- Strategy Engine: 완료
- Learning Engine: 완료
- Workflow CLI: 완료
- Search Strategy: 완료

테스트 현황과 운영 이슈(예: 외부 API 제한)는 별도 운영 문서로 관리하는 것을 권장합니다.

---

## 12. 실무 활용 예시 (CLI)

```bash
# 1) 구조 분석 (Greenfield)
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR

# 2) 기회 발굴
cmis opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  --budget 1000000000 \
  --top-n 5

# 3) 전략 설계 (Brownfield)
cmis workflow run strategy_design \
  --input domain_id=Adult_Language_Education_KR \
  --input goal_id=GOAL-growth \
  --input project_context_id=PRJ-my-company
```

---

## 13. 체크리스트: “철학이 구조로 구현되었나?”

- [ ] Evidence-first가 ValueEngine 파이프라인과 Policy에 의해 강제되는가?
- [ ] Evidence/Value/Graph/Context가 재현 가능한 저장 구조를 갖는가?
- [ ] Agent(Role)는 엔진 로직을 숨기지 않고, workflow+policy를 표준화하는가?
- [ ] Greenfield/Brownfield가 “ProjectContext 유무”로 일관되게 동작하는가?
- [ ] Workflow run의 Progress Ledger가 남아 재실행/부분 재실행이 가능한가?
- [ ] 모든 결과(숫자/전략/갭)가 lineage로 추적 가능한가?

---

**CMIS Architecture Blueprint v3.4 (Philosophy-aligned Update)**  
**작성**: 2025-12-12
