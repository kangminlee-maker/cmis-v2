# CMIS Architecture 문서 인덱스

**최종 업데이트**: 2025-12-14
**아키텍처 기준 버전**: CMIS v3.6.0 (엔진 Production + Orchestration 설계)

---

## 1. Active 문서 (dev/docs/architecture)

아래 문서들은 현재 아키텍처의 SSoT(정본) 또는 그에 준하는 설계 문서입니다.

### 1.1 Core (SSoT)

- `CMIS_Architecture_Blueprint_v3.6.0_km.md`
  - v3.6.0 기준 전체 아키텍처 단일 문서(사람용 SSoT)
  - 철학 v2 + 핵심 용어 + 폴더 구조 + planes/R-P-V-D/stores/ids/orchestration 요약
  - 기준 충돌 시 `cmis.yaml` 우선

- `CMIS_Orchestration_Kernel_Design.md`
  - Reconcile Loop 기반 Orchestration Kernel 설계
  - GoalGraph/TaskQueue/Ledgers/Verifier/Replanner/Governor

### 1.2 Interfaces

- `CMIS_Cursor_Agent_Interface_Design.md`
  - Cursor Agent를 5번째 인터페이스로 추가하는 설계
  - Orchestration Kernel과의 역할 분리(Interface adapter vs Kernel)

### 1.3 Engines & Supporting Design

- `BeliefEngine_Design_Enhanced.md`
  - BeliefEngine v1.0(Production Ready) 설계 요약 + Roadmap

- `World_Engine_Enhanced_Design.md`
- `PatternEngine_Design_Final.md`
- `StrategyEngine_Design_Enhanced.md`
- `LearningEngine_Design_Enhanced.md`
- `Workflow_CLI_Design_Enhanced.md`
- `Search_Strategy_Design_v2.md`

### 1.4 Cross-cutting

- `cmis_project_context_layer_design.md`
  - FocalActorContext 설계
  - Greenfield/Brownfield 정의

---

## 2. Deprecated 문서

### 2.1 v3.3_and_earlier

- 위치: `dev/deprecated/docs/architecture_v3.3_and_earlier/`
- 포함: v3.3 및 그 이전 중간본/구버전 설계/검토 문서

### 2.2 v3.4

- 위치: `dev/deprecated/docs/architecture_v3.4/`
- 포함: Blueprint v3.4 (통합 이전 버전)

### 2.3 v3.6 (문서 정리/통합)

- 위치: `dev/deprecated/docs/architecture_v3.6/`
- 목적: “하나의 설계 = 하나의 활성 문서” 원칙을 위해 보조/리뷰/플랜 문서를 통합 후 보존

---

## 3. 문서 버전 관리 규칙

- 업그레이드 시(예: v3.6 → v3.7):
  - 신규 문서 작성(필요 시 파일명에 신규 버전 반영)
  - 이전 버전 문서를 `dev/deprecated/docs/architecture_v{old_version}/`로 이동
  - 본 README 업데이트

---

## 4. 빠른 링크

- 전체 아키텍처(통합): `CMIS_Architecture_Blueprint_v3.6.0_km.md`
- Orchestration: `CMIS_Orchestration_Kernel_Design.md`
- Cursor 인터페이스: `CMIS_Cursor_Agent_Interface_Design.md`
