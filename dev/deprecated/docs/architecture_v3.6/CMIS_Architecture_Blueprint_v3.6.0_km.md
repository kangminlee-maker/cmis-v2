# CMIS Architecture Blueprint v3.6.0 (SSoT-aligned)

- **아키텍처 기준 버전**: v3.6.0
- **최종 업데이트**: 2025-12-14
- **상태**: 엔진 Production(문서 선언 기준) + Orchestration 설계(blueprint)
- **정본(SSoT)**: `cmis.yaml` (contracts/registry)

> 이 문서는 `cmis.yaml`을 사람이 읽기 쉬운 형태로 풀어쓴 아키텍처 블루프린트입니다.
> 문서/구현/설정이 충돌할 경우, 항상 `cmis.yaml`을 우선합니다.

---

## 0. 이 문서의 범위와 통합 정책

### 0.1 범위

- 본 문서는 CMIS의 **전체 아키텍처(planes/graphs/stores/ids/orchestration)**를 한 파일에서 이해할 수 있도록 정리합니다.
- 엔진별 상세 설계/구현 세부는 별도 문서(예: `World_Engine_Enhanced_Design.md`)를 참고하되, **정합성의 기준은 `cmis.yaml`**입니다.

### 0.2 통합(Consolidation) 원칙

- “철학/용어/폴더구조/블루프린트”가 여러 파일로 분절되며 생긴 중복과 버전 꼬임을 줄이기 위해, 이 문서가 **Core SSoT 문서(사람용)** 역할을 합니다.
- 기존 문서 중 일부는 **deprecated로 이동**하고, 본 문서에 핵심 내용을 흡수합니다(아래 11장 참고).

---

## 1. Executive Summary

CMIS(Contextual Market Intelligence System)는 시장/비즈니스 세계를 **Reality/Pattern/Value/Decision의 Graph-of-Graphs(R/P/V/D)**로 표현하고, **Understand → Discover → Decide → Learn** 루프를 실행하는 Market Intelligence OS입니다.

CMIS의 산출물은 단순한 텍스트 답변이 아니라, 다음을 포함하는 **재현 가능한 결과 번들**입니다.

- **세계(World) 설명**: R-Graph 스냅샷과 구조적 설명
- **변화(Change) 제안**: Pattern/Gap 기반 가설과 전략 후보
- **결과(Result) 예측/평가**: ValueRecord(분포/품질/lineage 포함)
- **논증(Argument) 및 추적(Lineage)**: evidence_id/value_id/run 기록을 통한 역추적

---

## 2. 핵심 철학(Principles) v2

아래 철학은 슬로건이 아니라, **구성요소와 규약으로 강제되는 설계 제약**입니다.

> 참고: `cmis.yaml`의 `cmis.philosophy.principles`는 “강제 가능한 경로(enforced_by)” 중심으로 일부 원칙을 계약 형태로 고정합니다.
> 본 문서는 운영/설계 관점에서 사용하는 10대 철학을 한 곳에 정리합니다.

### 2.1 Evidence-first, Prior-last

- **의미**: 가능한 한 Evidence로 해결하고, Prior/가정은 마지막 수단으로 제한합니다.
- **대표 강제 지점**: `cmis.yaml`의 `philosophy.principles[*].enforced_by` 중 `cognition_plane.engines.evidence_engine`, `cognition_plane.engines.value_engine.metric_resolver`, `cognition_plane.engines.policy_engine`

### 2.2 권위 있는 Substrate(SSoT) + Lineage

- **의미**: “진실”은 엔진/에이전트의 말이 아니라 **Store/Graph에 영속화된 ID/Lineage 객체**입니다.
- **대표 강제 지점**: `substrate_plane.single_source_of_truth`, `ids_and_lineage`, `orchestration_plane.run_audit_log`

### 2.3 Model-first, Number-second

- **의미**: 숫자는 세계 모델(Reality/Pattern)의 결과입니다.
- **대표 강제 지점**: `substrate_plane.graphs.reality_graph`, `cognition_plane.engines.world_engine`, `cognition_plane.engines.pattern_engine`, `cognition_plane.engines.value_engine`

### 2.4 Graph-of-Graphs (R/P/V/D 분리)

- **의미**: Reality/Pattern/Value/Decision은 생명주기와 검증 방식이 달라, **분리된 그래프**로 다루고 참조로 연결합니다.
- **대표 강제 지점**: `substrate_plane.graphs.{reality_graph,pattern_graph,value_graph,decision_graph}`

### 2.5 Trait 기반 Ontology (lock-in 최소화)

- **의미**: 라벨 고착을 피하고 Trait 조합으로 패턴/조건/역량을 정의합니다.
- **대표 강제 지점**: `modules.schemas.ontology`, `substrate_plane.graphs.pattern_graph`, `libraries.pattern_library`

### 2.6 Project Context는 1급 객체

- **의미**: Greenfield/Brownfield 차이를 텍스트가 아닌 **프로젝트 컨텍스트 객체**로 표현합니다.
- **대표 강제 지점**: `substrate_plane.stores.focal_actor_context_store`, `cognition_plane.engines.world_engine.snapshot(focal_actor_context_id)`, `cognition_plane.engines.strategy_engine.search_strategies(focal_actor_context_id)`

### 2.7 모든 답은 “세계-변화-결과-논증” 패키지

- **의미**: 결론만이 아니라, 전제된 세계/가정된 변화/계산된 결과/근거와 계보를 함께 제공합니다.
- **대표 강제 지점(권장)**: `artifact_store` + `run_store` + `ids_and_lineage` 규약, 출력 포맷(Interface/View)

### 2.8 Objective-Oriented Orchestration (동적 재설계)

- **의미**: 고정 프로세스가 아니라 목표 달성을 중심으로, 검증/차이(Diff)/재계획을 반복합니다.
- **대표 강제 지점**: `orchestration_plane.orchestrator.lifecycle`, `orchestration_plane.replanning.triggers`, `orchestration_plane.verifier`

### 2.9 Agent = Persona + Workflow + View (엔진 아님)

- **의미**: Agent/Role은 엔진이 아니라 **관점+절차+출력 형태**를 고정하는 제약입니다.
- **대표 강제 지점**: `planes.role_plane.roles`, `orchestration_plane.workflow_binding`, `role_plane.invariants`

### 2.10 Monotonic Improvability & Re-runnability

- **의미**: Outcome이 누적되면 더 좋아져야 하고, 동일 입력이면 재실행 가능한 구조여야 합니다.
- **대표 강제 지점**: `cognition_plane.engines.learning_engine`, `observability.eval_harness`, `substrate_plane.stores.run_store`

---

## 3. 핵심 용어(Glossary)

- **Orchestration Plane**: 아키텍처 레벨의 실행 제어 계층(문서/YAML/다이어그램)
- **Orchestration Kernel**: 구현/런타임 레벨의 실행 핵(코드/클래스)
- **Project Ledger**: 프로젝트/시장 분석의 상태 참조(문제 공간 작업기억)
- **Progress Ledger**: 실행 프로세스 제어 상태(스텝/상태/스톨/재시도/다음 액션)
- **Task(실행 단위)**: TaskQueue/TaskGraph에서 실행되는 작업 노드

> “Task Ledger” 용어는 실행 단위 task와 혼동될 수 있어, CMIS에서는 **Project Ledger**를 기본 용어로 사용합니다.

---

## 4. 리포지토리 구조: schemas / libraries / config

CMIS는 YAML/지식/설정을 변경 빈도와 역할에 따라 3개 축으로 분리합니다.

- **schemas/**: 타입 시스템(거의 변경 없음, breaking 가능)
- **libraries/**: 도메인 지식(가끔 확장)
- **config/**: 런타임 설정(자주 튜닝)

`cmis.yaml`은 “상위 계약/레지스트리”만 유지하고, 대형 정의는 외부 파일로 분리합니다.

```text
cmis.yaml                 # Contracts + Registry
schemas/                  # 타입 시스템
libraries/                # 도메인 지식
config/                   # 런타임 설정
cmis_core/                # 엔진 구현
cmis_cli/                 # CLI
```

대표 매핑(`cmis.yaml`의 `modules`):

- `schemas.ledgers` → `schemas/ledgers.yaml`
- `libraries.pattern_library` → `libraries/patterns/`
- `config.policies` → `config/policies.yaml`
- `config.workflows` → `config/workflows.yaml`

---

## 5. 아키텍처 개요: Planes + Orchestration

CMIS는 “엔진 나열”이 아니라, plane 분리로 책임과 진실의 위치를 고정합니다.

```text
┌─────────────────────────────────────────────────────────────┐
│ Interaction Plane (CLI / API / Web / Notebook)              │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Role Plane (Agent = Persona + Workflow + View)              │
│  - roles, allowed_workflows, allowed_calls, invariants       │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Orchestration Plane (Kernel + Ledgers + Verifier + Replan)   │
│  - run lifecycle, audit log, tool registry, workflow binding │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Cognition Plane (Engines)                                   │
│  Evidence / World / Pattern / Value / Strategy / Learning    │
│  + Policy / Belief (cross-cutting)                           │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Substrate Plane (Graphs + Stores = 재현 가능한 정본)         │
│  R/P/V/D Graphs + Stores + IDs/Lineage + Run/Audit           │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Substrate Plane (SSoT)

### 6.1 SSoT 규칙

`cmis.yaml`의 `substrate_plane.single_source_of_truth.rules`를 요약하면:

- 모든 입력/출력은 **ID/Ref로만 전달**합니다.
- 원문/원데이터는 `evidence_store`(및 `document_store`)에 저장합니다.
- 정규화/추출/계산 산출물은 별도 객체로 저장하고 lineage로 연결합니다.
- 핵심 수치/주장은 `evidence_id` 또는 `value_id`로 역추적 가능해야 합니다.

### 6.2 Stores

대표 store(발췌):

- `evidence_store`: 원문/원데이터/메타데이터/획득방식 저장
- `document_store`: 대용량 원문 스냅샷/첨부파일
- `graph_store`: R/P/V/D 그래프 및 스냅샷
- `value_store`: ValueRecord(VAL-*) 영속화(append-only 권장)
- `focal_actor_context_store`: FocalActorContext(PRJ-*) 버전 관리
- `outcome_store`: Outcome(OUT-*) 저장
- `ledger_store`: Project/Progress Ledger 영속화 및 리플레이
- `artifact_store`: 리포트/차트/중간 산출물(ART-*) 저장
- `run_store`: 실행(RUN-*) 감사 로그

### 6.3 Graph-of-Graphs (R/P/V/D)

- **R-Graph (Reality)**: Actor/Event/Resource/MoneyFlow/Contract/State 중심
- **P-Graph (Pattern)**: 패턴 정의, composes/conflicts, trait 기반 제약
- **V-Graph (Value)**: Metric/ValueRecord/Formula/Empirical relation
- **D-Graph (Decision)**: Goal/Hypothesis/Strategy/Scenario/Action

---

## 7. Cognition Plane (Engines)

### 7.1 공통 계약(Contract)

`cmis.yaml`의 `cognition_plane.engine_contracts` 요약:

- 동일 입력/정책/증거 스냅샷이면 결과가 재현 가능해야 합니다.
- 숨은 상태를 store 밖에 두지 않습니다.
- 출력은 lineage를 포함한 ref로 반환합니다.

### 7.2 엔진 역할(요약)

- **Policy Engine**: 정책(quality/risk/evidence 우선순위) 결정
- **Evidence Engine**: Evidence 수집/정규화/중복제거/번들링
- **World Engine**: Evidence → R-Graph 정규화, snapshot 제공
- **Pattern Engine**: 패턴 매칭/갭 탐지
- **Value Engine**: Metric resolver(4-stage), ValueRecord 생성/검증
- **Strategy Engine**: Goal/Pattern/Reality/Value 기반 전략 생성/평가
- **Learning Engine**: Outcome 기반 업데이트(패턴/메트릭/컨텍스트/신념)
- **Belief Engine**: Prior/신념 분포 제공 및 학습 반영(보조 신호)

---

## 8. Role Plane (Agent)

Role은 엔진이 아니라 **허용된 워크플로/호출/기본 정책**을 고정합니다.

`cmis.yaml`의 `planes.role_plane`에서 최소한 다음이 보장됩니다.

- **allowed_workflows**: role이 실행할 수 있는 workflow
- **allowed_calls**: role이 호출할 수 있는 엔진 API
- **invariants**:
  - role_cannot_write_stores_directly
  - role_cannot_bypass_policy_engine
  - role_is_not_engine

---

## 9. Orchestration Plane (Kernel, Ledgers, Verifier, Replan)

`cmis.yaml`의 `orchestration_plane` 요약:

### 9.1 Orchestrator lifecycle

- init_run → build_project_ledger → plan_steps → execute_steps → verify_and_replan → publish_artifacts → archive_run

### 9.2 Replanning

- stall_threshold 기반 스톨 감지
- verifier_failed / new_evidence_arrived / policy_gate_blocked / user_constraints_changed 등 트리거로 재계획

### 9.3 Ledgers

- **Project Ledger**: goal_graph, predicates, scope/constraints, evidence_plan, assumptions, artifact_refs
- **Progress Ledger**: step_index/status, stall_count, last_calls, diff_reports, next_step_suggestion

### 9.4 Verifier

- evidence_lineage_check: 핵심 주장은 evidence_id/value_id로 역추적 가능
- policy_quality_gate: policy_ref의 품질 요구 충족
- consistency_check: 상충 값은 diff 후 fusion 규칙 적용

### 9.5 Tool/Resource registry

- tool/environment/role을 1급 리소스로 등록하고 정책으로 안전하게 호출합니다.

---

## 10. End-to-end 흐름: Understand → Discover → Decide → Learn

- **Understand**: Evidence 수집 → World snapshot(R) → Pattern match(P) → Metric 평가(V)
- **Discover**: Gap 탐지(P) + sizing(V)
- **Decide**: Goal(D) 기반 전략 탐색/평가(D↔V)
- **Learn**: Outcome 기록 → 학습(L) → pattern/metric/context/belief 업데이트

---

## 11. 문서 정리: deprecated 처리 내역

본 블루프린트(v3.6.0)로 통합되며 아래 문서들은 deprecated로 이동합니다.

- `dev/deprecated/docs/architecture_v3.4/CMIS_Architecture_Blueprint_v3.4_km.md`
- `dev/deprecated/docs/architecture_v3.6/cmis_philosophy_concept.md`
- `dev/deprecated/docs/architecture_v3.6/Folder_Structure_Design.md`
- `dev/deprecated/docs/architecture_v3.6/Terminology_Decision.md`

Deprecated 문서의 보관 위치는 `dev/deprecated/docs/` 하위 버전 폴더를 따릅니다.
