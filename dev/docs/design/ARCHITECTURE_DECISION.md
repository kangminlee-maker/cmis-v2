# CMIS v2 아키텍처 결정 문서

> **버전**: v1.0.0
> **작성일**: 2026-03-17
> **상태**: 결정 대기
> **대상 레포**: `https://github.com/kangminlee-maker/cmis-v2`
> **선행 문서**: `CMIS_RLM_BRIDGE_DESIGN.md` (v0.3.0, 탐색 문서로 재분류)
> **참고 레포**: `https://github.com/alexzhang13/rlm` (RLM), `https://github.com/kangminlee-maker/cmis` (CMIS v3.6.0)

---

## 1. 이 문서의 목적

`CMIS_RLM_BRIDGE_DESIGN.md`에 대한 8-Agent Panel Review(2026-03-17)에서, 설계 문서와 사용자 의도 사이에 근본적 불일치가 발견되었습니다:

- **사용자 의도**: CMIS를 RLM + KBD 기반으로 완전히 재구축
- **설계 문서**: 기존 cmis_core를 보존하면서 래핑 계층을 추가하는 점진적 확장

이 문서는 상세 설계에 선행하여 **아키텍처 수준의 결정**을 내립니다. 모든 후속 설계 문서는 여기서 내린 결정을 전제로 합니다.

---

## 2. 시스템 목적 (불변)

CMIS는 Market Intelligence OS입니다. 목적은 변하지 않습니다:

1. **시장 구조를 Graph-of-Graphs로 표현**: Reality(R) / Pattern(P) / Value(V) / Decision(D) 4개 그래프
2. **Understand → Discover → Decide → Learn 루프 실행**: 4개 Canonical Workflow
3. **Evidence-first 원칙**: 모든 결론에 검증 가능한 출처(lineage)
4. **재현/감사 가능**: 모든 실행 과정을 이벤트로 기록, 재현 가능

변하는 것은 **이 목적을 달성하는 아키텍처**입니다.

---

## 3. 결정 사항

### 결정 1: cmis_core의 위치

> **결정: (C) 핵심 로직을 추출하여 새 아키텍처 위에 재작성**

| 선택지 | 설명 | 판정 |
|--------|------|------|
| (A) cmis-v2에 복사하여 수정 가능하게 | cmis_core/ 전체를 cmis-v2에 복사 | 기각. 17,000줄의 레거시 구조를 그대로 가져옴 |
| (B) 외부 의존성으로 import만 | `from cmis_core import ...`으로 사용 | 기각. 탐색 문서(v0.3.0)의 접근법이었으나, 아키텍처 종속 발생 |
| **(C) 핵심 로직 추출 + 새 아키텍처 위 재작성** | 기존 엔진의 검증된 알고리즘을 참조하되, 새 타입 시스템(KBD) 위에서 재구현 | **채택** |

**근거**:
- 기존 9개 엔진의 알고리즘(4-Method Fusion, 23개 패턴 매칭, Reconcile Loop 등)은 377개 테스트로 검증됨 → 참조 가치 있음
- 기존 타입 시스템(`@dataclass` + `Dict[str, Any]`)은 KBD의 Pydantic 모델과 양립 불가 → 래핑이 아닌 재작성 필요
- 기존 YAML 자산(패턴 23개, 정책, 워크플로우, 도메인 정의)은 그대로 재사용 가능

**실질적 의미**:
- `cmis_core/`는 cmis-v2에 복사하지 않음. 원본 레포(`kangminlee-maker/cmis`)를 참조 문서로만 사용
- cmis-v2의 새 코드는 `ontology.yaml` → KBD 생성 타입 위에서 작성
- 기존 YAML 파일(`libraries/patterns/`, `config/policies.yaml`, `config/workflows.yaml`)은 cmis-v2로 복사하여 사용

### 결정 2: "기존 코드 변경 금지" 원칙

> **결정: 폐기. cmis-v2는 새 코드베이스이며, 원본 cmis 레포를 수정하지 않는다.**

탐색 문서의 "CMIS 코드 변경 금지" 원칙은 (B) import 접근법의 전제였습니다. (C) 재작성을 채택했으므로 이 원칙은 적용되지 않습니다.

대신 다음 원칙을 적용합니다:
- **원본 보존**: `kangminlee-maker/cmis` 레포는 수정하지 않음 (참조 전용)
- **YAML 자산 재사용**: 패턴, 정책, 워크플로우 YAML은 cmis-v2로 복사하여 사용
- **알고리즘 참조**: 기존 엔진의 Python 코드를 참조하여 새 타입 시스템 위에 재구현

### 결정 3: 실행 엔진

> **결정: RLM이 유일한 실행 엔진. OrchestrationKernel의 Reconcile Loop를 RLM의 REPL 반복 루프로 대체**

기존 CMIS의 실행 구조:
```
사용자 → CLI/Cursor → OrchestrationKernel.execute(RunRequest)
                        → GoalBuilder → Verifier → Replanner → TaskExecutor
                        → WorkflowOrchestrator → 개별 엔진 호출
```

cmis-v2의 실행 구조:
```
사용자 → python -m cmis_v2.runner "시장 분석 요청"
          → RLM.completion(prompt)
            → LM이 REPL에서 코드 작성
              → custom_tools로 엔진 함수 호출
              → 중간 결과를 보고 다음 행동 결정
              → rlm_query()로 복잡한 하위 작업 위임
            → FINAL_VAR(최종 결과)
```

**대체 매핑**:

| 기존 CMIS 컴포넌트 | cmis-v2 대체 | 근거 |
|-------------------|-------------|------|
| OrchestrationKernel | RLM의 REPL 반복 루프 | LM이 직접 실행 흐름을 제어 |
| GoalBuilder (키워드 기반) | LM의 자연어 이해 | 키워드 규칙 대신 LM이 query를 직접 해석 |
| Replanner (규칙 기반) | LM의 적응적 코드 작성 | 규칙 기반 재계획 대신 LM이 결과를 보고 판단 |
| Verifier (Predicate 평가) | PolicyEngine 게이트 + LM 판단 | 정책 검증은 도구로 제공, 목표 충족 판단은 LM |
| Governor (예산/Stall) | RLM의 max_budget + max_timeout + max_iterations | RLM 내장 제한으로 대체 |
| TaskExecutor | RLM의 custom_tools 직접 호출 | LM이 도구를 직접 선택하여 호출 |
| WorkflowOrchestrator | LM의 코드 흐름 | 고정 Workflow 대신 LM이 상황에 맞게 구성 |

**보존되는 것**:
- PolicyEngine의 정책 게이트 8종 → 도구로 노출하여 LM이 호출
- Evidence-first 원칙 → 도구 수준에서 lineage 추적 강제
- 이벤트 기록 → 모든 도구 호출을 자동 기록

### 결정 4: KBD 적용 범위

> **결정: Phase 1부터 전체 적용. 새 코드는 처음부터 KBD 타입 위에서 작성**

탐색 문서에서는 "Phase 1은 bridge/에서만, Phase 2~3에서 점진적 마이그레이션"이었습니다. 재작성을 채택했으므로, 새 코드는 처음부터 KBD 타입을 사용합니다.

```
schemas/ontology.yaml (단일 정의 원천)
    │
    ▼ generate_from_ontology.py
    │
    ├── cmis_v2/generated/types.py     ← Pydantic 모델 + Literal 타입
    ├── cmis_v2/generated/validators.py ← 검증 함수 (자동 생성)
    └── docs/ontology-map.md            ← 역색인

cmis_v2/의 모든 모듈은 cmis_v2/generated/ 타입을 사용
```

"점진적 마이그레이션"은 불필요합니다. 새 코드베이스이므로 처음부터 올바른 타입을 사용합니다.

### 결정 5: 모듈 구조

> **결정: `bridge/` 명칭을 폐기. cmis-v2 자체가 새 시스템**

탐색 문서의 `bridge/`는 "기존 CMIS와 RLM 사이의 연결 계층"이었습니다. 재작성에서는 연결 계층이 아니라 시스템 자체입니다.

```
cmis-v2/
├── schemas/
│   └── ontology.yaml                  ← 단일 정의 원천
│
├── cmis_v2/                            ← 새 시스템 (bridge/ 아님)
│   ├── generated/                      ← KBD 자동 생성
│   │   ├── types.py                    ← Pydantic 모델 + Literal
│   │   └── validators.py              ← 검증 함수
│   │
│   ├── engines/                        ← 9개 엔진 재구현
│   │   ├── evidence.py                 ← Evidence 수집 (기존 EvidenceEngine 참조)
│   │   ├── world.py                    ← R-Graph 구축 (기존 WorldEngine 참조)
│   │   ├── pattern.py                  ← 패턴 매칭 (기존 PatternEngineV2 참조)
│   │   ├── value.py                    ← 4-Method Fusion (기존 ValueEngine 참조)
│   │   ├── strategy.py                 ← 전략 탐색 (기존 StrategyEngine 참조)
│   │   ├── policy.py                   ← 정책 게이트 (기존 PolicyEngine 참조)
│   │   ├── belief.py                   ← Prior/Belief 관리 (기존 BeliefEngine 참조)
│   │   ├── learning.py                 ← 학습 루프 (기존 LearningEngine 참조)
│   │   └── __init__.py
│   │
│   ├── tools.py                        ← 엔진 → RLM custom_tools 변환
│   ├── project.py                      ← 프로젝트 관리 (다중 Run 컨테이너)
│   ├── events.py                       ← 통합 이벤트 시스템
│   ├── stores/                         ← 데이터 저장 (SQLite)
│   │   ├── run_store.py
│   │   ├── artifact_store.py
│   │   └── ...
│   ├── system_prompt.py                ← RLM 시스템 프롬프트 (ontology에서 동적 생성)
│   └── runner.py                       ← 사용자 진입점
│
├── scripts/
│   ├── generate_from_ontology.py       ← 온톨로지 → 코드 생성기
│   └── validate_patterns.py            ← 패턴 YAML 검증
│
├── libraries/                          ← YAML 자산 (기존 CMIS에서 복사)
│   ├── patterns/                       ← 23개+ 비즈니스 패턴
│   ├── domains/                        ← 도메인 정의
│   └── metrics_spec.yaml              ← 메트릭 정의
│
├── config/                             ← 설정 (기존 CMIS에서 복사)
│   ├── policies.yaml                   ← 정책 팩 (3모드 × 5프로필)
│   └── workflows.yaml                  ← Canonical Workflow 정의
│
├── projects/                           ← 프로젝트별 작업 공간
│
├── docs/
│   └── ontology-map.md                 ← 자동 생성. 개념 ↔ 코드 역색인
│
├── dev/
│   ├── docs/design/                    ← 설계 문서
│   │   ├── ARCHITECTURE_DECISION.md    ← 이 문서
│   │   └── CMIS_RLM_BRIDGE_DESIGN.md  ← 탐색 문서 (참조용 보존)
│   └── tests/
│
├── pyproject.toml                      ← mypy strict + pydantic
└── requirements.txt
```

### 결정 6: 엔진 재구현 범위와 순서

> **결정: MVP 4개 엔진 먼저, 나머지 5개는 후속**

9개 엔진을 한번에 재구현하는 것은 비현실적입니다. MVP에 필수적인 엔진과 후속 엔진을 구분합니다.

**MVP (Phase 1) — 시장 구조 분석 1건을 완료할 수 있는 최소 구성:**

| 엔진 | 이유 |
|------|------|
| `evidence.py` | 데이터 수집 없이 분석 불가 |
| `world.py` | R-Graph 없이 시장 구조 표현 불가 |
| `pattern.py` | 패턴 매칭이 CMIS의 핵심 차별점 |
| `value.py` | 메트릭 정량화 없이 분석 결과 불완전 |

**Phase 2 — 기회 발굴 + 전략 설계:**

| 엔진 | 이유 |
|------|------|
| `strategy.py` | 전략 설계 Workflow 실행에 필수 |
| `policy.py` | 정책 게이트 없이 품질 보증 불가 |

**Phase 3 — 학습 루프 + 고급 기능:**

| 엔진 | 이유 |
|------|------|
| `belief.py` | Prior/사전 확률 관리 |
| `learning.py` | 분석 결과 축적 및 시스템 개선 |

각 Phase는 이전 Phase의 엔진이 작동하는 상태에서 추가됩니다.

### 결정 7: 도구 노출 원칙

> **결정: 구현된 모든 엔진을 RLM 도구로 노출. Tier 분류 대신, 모든 도구에 이벤트 기록을 포함**

탐색 문서의 "Tier 1(Kernel 경유) / Tier 2(엔진 직접)" 분류를 폐기합니다. Kernel을 RLM으로 대체했으므로, 모든 엔진은 LM이 직접 호출합니다.

대신 다음 원칙을 적용합니다:
- **모든 도구 호출은 이벤트로 기록**: Evidence-first 원칙을 도구 수준에서 강제
- **모든 도구는 ontology 타입을 사용**: KBD 강제력이 도구 경계에서 끊어지지 않음
- **정책 검증은 별도 도구로 제공**: LM이 결과를 검증할지 여부를 판단하되, 검증 도구는 항상 사용 가능

### 결정 8: 이벤트 시스템 통합

> **결정: 프로젝트 수준 + Run 수준 이벤트를 하나의 이벤트 시스템으로 통합**

탐색 문서에서는 프로젝트 이벤트(`events.ndjson`)와 Run 이벤트(RunStore SQLite)가 분리되어 있었습니다. 재구축에서는 하나의 이벤트 시스템을 사용합니다.

```python
# cmis_v2/events.py
# 모든 이벤트는 project_id + run_id + event_type + payload로 구성
# 저장: SQLite (단일 DB)
# 조회: project_id로 필터 → 프로젝트 수준
#       run_id로 필터 → Run 수준
#       project_id + run_id → 전체 이력
```

상관 ID로 `project_id`를 사용하여 RLM 로그, 프로젝트 이벤트, 엔진 호출을 연결합니다.

### 결정 9: ontology.yaml 스키마

> **결정: ontology.yaml의 목표 스키마를 확정**

탐색 문서에서 ontology.yaml의 스키마가 미정의였습니다. 다음을 확정합니다:

```yaml
ontology:
  version: "1.0.0"

  node_types:
    {name}:
      description: string (필수)
      required_traits: list[string] (필수)
      optional_traits: list[string] (선택, 기본 [])

  edge_types:                          # 탐색 문서에서 누락되었던 것
    {name}:
      description: string (필수)
      source: node_type_name (필수)
      target: node_type_name (필수)
      via: node_type_name (선택)       # 중간 노드가 있는 경우

  trait_definitions:
    {name}:
      type: "boolean" | "enum" | "string" | "number" (필수)
      description: string (필수)
      values: list[string] (type=enum일 때 필수)
      used_by: list[node_type_name] (필수)
      bounds: {min, max} (type=number일 때 선택)

  metrics:
    {MET-ID}:
      description: string (필수)
      unit: "currency" | "ratio" | "count" | "percentage" | "index" (필수)
      aggregation: "sum" | "weighted_average" | "latest" (필수)
      bounds: {min, max} (선택)
      required_evidence_tier: list[string] (선택)
      policy_overrides: {mode: {param: value}} (선택)

  policy_schema:
    modes: list[string] (필수)
    profile_types: list[string] (필수)

  workflow_schema:
    canonical_workflows: list[string] (필수)
    {workflow_id}:
      description: string (필수)
      keywords: list[string] (필수)    # 시스템 프롬프트 자동 생성에 사용
      default_policy: string (필수)
```

`generate_from_ontology.py`는 이 스키마의 **모든 섹션**에서 코드를 생성합니다:
- `node_types` → `NodeType` Literal + `OntologyNode` Pydantic 모델
- `edge_types` → `EdgeType` Literal + `OntologyEdge` Pydantic 모델
- `trait_definitions` → trait enum Literal 타입들
- `metrics` → `MetricId` Literal + `METRIC_REGISTRY`
- `policy_schema` → `PolicyMode` Literal
- `workflow_schema` → `WorkflowId` Literal + 키워드 매핑 (system_prompt에 자동 주입)

### 결정 10: 프로젝트 ID 체계

> **결정: `{name}-{date}-{uuid6}` 형식으로 고유성 보장**

탐색 문서의 `{name}-{date}` 형식은 같은 날 같은 이름으로 ID 충돌이 발생합니다.

```python
project_id = f"{name}-{date_str}-{uuid4().hex[:6]}"
# 예: ev-charging-korea-20260317-a1b2c3
```

---

## 4. 결정하지 않는 것 (후속 결정으로 미룸)

| 항목 | 미루는 이유 | 결정 시점 |
|------|-----------|---------|
| 외부 온톨로지 매핑 (FIBO, SNOMED 등) | 현재 단일 도메인(시장 분석)에 집중 | 다중 도메인 지원 시 |
| Docker 격리 실행 | Phase 1은 신뢰 환경에서 LocalREPL 사용 | 프로덕션 배포 시 |
| 도메인별 trait scoping | 현재 단일 도메인 | 다중 도메인 지원 시 |
| Persistent RLM 모드 | MVP에서 불필요 | 대화형 분석 지원 시 |
| trait 네임스페이스 | 현재 충돌 위험 없음 | 외부 체계 통합 시 |

---

## 5. 구현 순서 (수정)

탐색 문서의 "Phase A(KBD) + Phase B(Bridge) 병렬" 구조를 폐기하고, 단일 흐름으로 재구성합니다.

### Phase 0: 기반 (1주)

| 작업 | 산출물 |
|------|--------|
| ontology.yaml 완성 | `schemas/ontology.yaml` (결정 9의 스키마) |
| 생성기 구현 | `scripts/generate_from_ontology.py` |
| 자동 생성 실행 | `cmis_v2/generated/types.py`, `validators.py` |
| 패턴 검증 스크립트 | `scripts/validate_patterns.py` |
| YAML 자산 복사 | `libraries/`, `config/` |
| pyproject.toml (mypy strict) | 프로젝트 설정 |
| 이벤트 시스템 | `cmis_v2/events.py` |
| 프로젝트 관리 | `cmis_v2/project.py` |

### Phase 1: MVP (2~3주)

| 작업 | 산출물 | 참조 |
|------|--------|------|
| Evidence 엔진 | `cmis_v2/engines/evidence.py` | `cmis_core/evidence_engine.py` |
| World 엔진 (R-Graph) | `cmis_v2/engines/world.py` | `cmis_core/world_engine.py` |
| Pattern 엔진 | `cmis_v2/engines/pattern.py` | `cmis_core/pattern_engine_v2.py` |
| Value 엔진 (4-Method Fusion) | `cmis_v2/engines/value.py` | `cmis_core/value_engine.py` |
| RLM 도구 등록 | `cmis_v2/tools.py` |
| 시스템 프롬프트 (ontology에서 동적) | `cmis_v2/system_prompt.py` |
| Runner | `cmis_v2/runner.py` |
| **검증**: "한국 성인 영어 교육 시장 구조 분석" 1건 완료 |

### Phase 2: 전략 + 정책 (2주)

| 작업 | 산출물 |
|------|--------|
| Strategy 엔진 | `cmis_v2/engines/strategy.py` |
| Policy 엔진 (게이트 8종) | `cmis_v2/engines/policy.py` |
| **검증**: "시장 기회 발굴 → 전략 설계" 연결 실행 |

### Phase 3: 학습 + 고급 (2주)

| 작업 | 산출물 |
|------|--------|
| Belief 엔진 | `cmis_v2/engines/belief.py` |
| Learning 엔진 | `cmis_v2/engines/learning.py` |
| **검증**: 분석 결과 축적 → 재분석 시 정확도 향상 확인 |

---

## 6. 탐색 문서의 유효 자산

`CMIS_RLM_BRIDGE_DESIGN.md`에서 재사용하는 부분:

| 섹션 | 용도 | 재사용 방식 |
|------|------|-----------|
| 섹션 2 (CMIS 실사 결과) | 기존 엔진의 구현 수준 파악 | 엔진 재구현 시 참조 |
| 섹션 3 (RLM 참조 정보) | RLM custom_tools 인터페이스 | tools.py 설계에 직접 사용 |
| 섹션 10.3 (Pydantic + mypy) | 온톨로지 타입 강제 방식 | generated/ 구현에 직접 사용 |
| 섹션 10.5 (생성기 코드) | generate_from_ontology.py 골격 | 확장하여 사용 (edge_types, validators, system_prompt 추가) |

**폐기하는 부분**:
- 섹션 5 (Bridge 모듈 상세 설계) — `bridge/` 구조 자체를 폐기
- 섹션 7 (기존 코드와의 관계) — "변경하지 않는 것" 제약 폐기
- 섹션 8 (구현 작업 순서) — 이 문서의 섹션 5로 대체

---

## 7. 위험 요소

| 위험 | 영향 | 대응 |
|------|------|------|
| 9개 엔진 재구현 범위가 과대 | 일정 초과 | Phase 분리로 MVP 우선 |
| RLM의 LM이 도구를 잘못 사용 | 분석 품질 저하 | 시스템 프롬프트에 오류 복구 규칙 포함. 정책 검증 도구 제공 |
| ontology.yaml 스키마 변경 시 기존 데이터 비호환 | 데이터 손실 | 프로젝트 manifest에 ontology_version 포함. 마이그레이션 규칙 정의 |
| rlm_query() 자식 RLM의 custom_tools 상속 불확실 | 시나리오 실행 불가 | RLM 소스 코드 확인 후 설계에 반영 |
| LocalREPL에서 LM이 임의 코드 실행 | 보안 위험 | Phase 1은 신뢰 환경 전제. 프로덕션에서 DockerREPL 전환 |

---

## 부록: 8-Agent Panel Review 발견 항목 → 결정 매핑

| Review 발견 | 이 문서에서의 해소 |
|------------|----------------|
| "설계가 래핑이지 재구축이 아님" (pragmatics, coverage) | 결정 1(C): 핵심 로직 추출 + 재작성 |
| "코드 변경 금지" 원칙 잔존 (logic F1) | 결정 2: 폐기 |
| "Bridge" 명칭 부적절 (semantics) | 결정 5: `bridge/` 폐기, `cmis_v2/` 직접 사용 |
| OntologyEdge 자동 생성 누락 (logic, structure, evolution) | 결정 9: edge_types 섹션 추가 |
| system_prompt 메트릭 하드코딩 (logic, structure, dependency) | 결정 9: workflow_schema.keywords로 자동 주입 |
| validators.py 자동 생성 불일치 (logic, structure) | 결정 4: validators.py도 자동 생성 |
| StrategyEngine 도구 누락 (structure, coverage) | 결정 6: Phase 2에 포함, 결정 7: 전 엔진 노출 |
| 프로젝트 ID 충돌 (evolution) | 결정 10: UUID 접미사 |
| Run 간 데이터 전달 부재 (pragmatics, coverage) | 결정 8: 통합 이벤트 + 프로젝트 컨텍스트로 해결 (상세 설계는 후속) |
| LM 오류 복구 규칙 부재 (coverage) | 위험 요소로 식별, 시스템 프롬프트에 포함 예정 |
| 온톨로지 버전 마이그레이션 (evolution) | 위험 요소로 식별, manifest에 version 포함 |
