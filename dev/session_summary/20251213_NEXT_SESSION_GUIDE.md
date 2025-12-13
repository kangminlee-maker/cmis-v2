# 2025-12-13 세션 요약 및 다음 세션 가이드

**작성일**: 2025-12-13

## 이번 세션에서 완료한 것

### 1) Ledger 용어/키 전면 단일화

- **결정**: CMIS 문제공간 뷰는 `ProjectLedger`, 실행 단위는 `Task`/`Step`로 분리
- **결과**:
  - `task_ledger/TaskLedger` 관련 참조를 repo 전체에서 제거
  - 런 산출물(export)은 `project_ledger.yaml`로 고정
  - SQLite `ledger_store` 스키마도 `project_ledger_json`으로 전환

### 2) ProjectContext 혼동 제거: FocalActorContext + Binding 분리

- **결정**:
  - PRJ-* 레코드(버전/SoT/권한/lineage 포함)는 `FocalActorContext`로 명확화
  - 엔진 주입(integration) 형태는 `FocalActorContextBinding`으로 분리
- **구현**:
  - `cmis_core/context_binding.py` 추가
  - Pattern/Gap/World/Strategy 쪽에서 binding 기반으로 실행되도록 정리

### 3) OrchestrationKernel을 중심으로 올리기(Phase 1 강화)

- **ProjectLedger 확장(스펙 필드 채움)**:
  - `goal_graph`, `success_predicates`, `scope`, `constraints`, `evidence_plan`, `open_questions`, `artifact_refs`
- **ProgressLedger 확장(제어판 필드 채움)**:
  - `step_index`, `step_status`, `stall_count`, `diff_reports`, `next_step_suggestion`, `last_engine_calls`, `last_tool_calls`
- **Verifier/Replanner 연결**:
  - evidence lineage 부족/간단 consistency 이슈를 diff로 만들고 재계산/재수집 태스크로 연결

### 4) 스펙/레지스트리 정합성 자동 검증

- `cmis.yaml`은 registry/contract 중심 유지
- `python3 -m cmis_cli config-validate --check-registry`로 참조 존재성/fragment 검증

## 핵심 설계 결정(다음 세션에서 반드시 기억)

- **Substrate(Stores/Graphs) = 정본(System of Record)**
- **ProjectLedger = 정본을 가리키는 프로젝트 단위 인덱스/포인터 뷰**
- **FocalActorContext(PRJ-*) = Brownfield 중심의 컨텍스트 레코드(모델)**
- **FocalActorContextBinding = 엔진 주입(integration) 레이어**
- **OrchestrationKernel = Reconcile Loop의 중심**

## 다음 세션에서 해야 할 나머지 작업(우선순위)

### A. Orchestration Kernel 심화(시스템 중심화)

- **GoalGraph/Success Predicates 정교화**
  - 현재는 Phase 1 최소 구조(단일 goal 노드) 중심
  - D-Graph 연동/goal_graph 확장(브랜치/의존성/부분 완료)
- **Evidence plan / Open questions 생성 규칙 강화**
  - missing/lineage/consistency 유형별로 질문/계획이 ProjectLedger에 남도록 규칙 추가
- **Tool/Resource registry 실행 연결**
  - `tool_and_resource_registry`를 실제 실행 경로에 연결(안전 호출/제약)

### B. 품질/회귀 방지(Eval Harness)

- **목표**: monotonic improvability를 운영 규칙으로 강제
- **구현 후보**:
  - `eval/regression_suite.yaml`, `eval/canary_domains.yaml`을 읽어 실행하는 러너
  - 최소 지표:
    - prior 사용률
    - policy gate 실패율
    - evidence hit rate
  - 결과를 run_store에 기록하고, 임계치 위반 시 FAIL로 차단

### C. Belief Engine 역할 명시(안전한 Prior)

- **Prior는 마지막 수단**을 구조로 강제:
  - prior 분포를 참조 가능한 `distribution_ref`로 분리
  - prior 채택/기각의 정책 근거를 run/decision log에 강제 기록
  - prior 기반 값은 export 산출물에 추정임을 강제 표기

## 다음 세션 시작 체크리스트(빠른 재개)

- **정합성 검사**:
  - `python3 -m cmis_cli config-validate --check-registry --check-patterns --check-workflows`
- **핵심 테스트**:
  - `pytest -q dev/tests/unit/test_cursor_agent_interface_v2.py dev/tests/unit/test_spec_registry_consistency.py`

## 주요 파일(컨텍스트 앵커)

- **Contracts/Registry**: `cmis.yaml`
- **Ledger schema**: `schemas/ledgers.yaml`
- **Kernel**: `cmis_core/orchestration/kernel.py`, `ledgers.py`, `verifier.py`, `replanner.py`
- **Stores/View**: `cmis_core/stores/run_store.py`, `cmis_core/stores/ledger_store.py`, `cmis_core/run_exporter.py`
- **Focal context**: `cmis_core/types.py` (`FocalActorContext`), `cmis_core/context_binding.py`
- **CLI**: `cmis_cli/commands/cursor.py`, `cmis_cli/commands/config_validate.py`


