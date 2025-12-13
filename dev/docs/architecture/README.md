# CMIS Architecture 문서 인덱스

**최종 업데이트**: 2025-12-13
**버전**: CMIS v3.6.0 (Orchestration Kernel 설계)

---

## 📋 현재 문서 구조 (v3.6.0)

### 핵심 문서 (4개)

1. **cmis_philosophy_concept.md** ⭐⭐⭐
   - CMIS 10대 철학
   - 금지 규칙
   - 구성요소 매핑
   - enforced_by 명시

2. **CMIS_Architecture_Blueprint_v3.4_km.md** ⭐⭐⭐
   - 전체 아키텍처 개요
   - 4 Planes + Orchestration Runtime
   - Ledger 기반 설계 (Task + Progress)
   - 철학 정렬 재구성

3. **CMIS_Orchestration_Kernel_Design.md** ⭐⭐⭐
   - Reconcile Loop 설계 (Kubernetes 패턴)
   - Goal Predicate + Ledgers (2개)
   - Verifier + Replanner
   - LLM as PlanPatch Provider
   - Objective-Oriented 구현

4. **Blueprint_v3.4_Review.md** ⭐⭐
   - v3.4 Blueprint 검토 문서
   - Contracts YAML 검토
   - 보완 사항 정리
   - 참고용 유지

---

### 엔진별 설계 (7개)

1. **BeliefEngine_Design_Enhanced.md**
   - Prior/Belief 관리
   - Bayesian Update
   - Monte Carlo
   
   보조 문서:
   - BeliefEngine_Feedback_Review.md
   - BeliefEngine_Implementation_Complete.md
   - BeliefEngine_Future_Enhancements.md

2. **World_Engine_Enhanced_Design.md**
   - Reality Graph 관리
   - Greenfield/Brownfield
   - 필터링/서브그래프

3. **PatternEngine_Design_Final.md**
   - Trait 기반 매칭
   - Gap Discovery
   - Context Archetype

4. **StrategyEngine_Design_Enhanced.md**
   - Pattern → Strategy
   - Portfolio 최적화
   
   보조 문서:
   - StrategyEngine_Greenfield_Brownfield.md
   - StrategyEngine_Constraints_Design.md

5. **LearningEngine_Design_Enhanced.md**
   - Outcome 학습
   - 4-Learner 구조
   - ProjectContext 버전 관리

6. **Workflow_CLI_Design_Enhanced.md**
   - 8개 명령어
   - canonical_workflows 통합

7. **Search_Strategy_Design_v2.md**
   - Evidence 검색 전략

---

### 프로젝트 전체 (1개)

**cmis_project_context_layer_design.md**
- ProjectContext 설계
- Greenfield/Brownfield 정의

---

## 🗂️ 폴더 구조

```
dev/docs/architecture/
├─ README.md (본 문서)
│
├─ [핵심 문서 - 3개]
│  ├─ cmis_philosophy_concept.md ⭐
│  ├─ CMIS_Architecture_Blueprint_v3.4_km.md ⭐
│  └─ CMIS_Orchestration_Kernel_Design.md ⭐
│
├─ [엔진별 설계 - 7개]
│  ├─ BeliefEngine_Design_Enhanced.md
│  ├─ World_Engine_Enhanced_Design.md
│  ├─ PatternEngine_Design_Final.md
│  ├─ StrategyEngine_Design_Enhanced.md
│  ├─ LearningEngine_Design_Enhanced.md
│  ├─ Workflow_CLI_Design_Enhanced.md
│  └─ Search_Strategy_Design_v2.md
│
├─ [보조 문서 - 6개]
│  ├─ BeliefEngine_Feedback_Review.md
│  ├─ BeliefEngine_Implementation_Complete.md
│  ├─ BeliefEngine_Future_Enhancements.md
│  ├─ StrategyEngine_Greenfield_Brownfield.md
│  ├─ StrategyEngine_Constraints_Design.md
│  └─ cmis_project_context_layer_design.md
│
└─ [프로젝트 메타]
   └─ README.md

총 17개 문서 (active)
```

---

## 🗄️ Deprecated 문서

**위치**: `dev/deprecated/docs/architecture_v3.3_and_earlier/`

**통합 완료**: architecture + architecture_old → architecture_v3.3_and_earlier

**포함 문서** (25개):
- v3.3 Blueprint 및 Roadmap
- v1.0-v2.0 엔진 설계 (구버전)
- Orchestration 설계 중간본 (v1.1, v2.0)
- 철학 deprecated 버전
- 검토 문서 (일부)

**버전 관리 규칙** (.cursorrules에 추가):
- 새 버전 출시 시: dev/deprecated/docs/architecture_v{old_version}/ 생성
- 이전 버전 문서 이동
- 폴더명 = deprecated 문서의 버전
- 예: v3.4 → v3.5 시 architecture_v3.4/ 생성

---

## 🔍 빠른 검색

### 주제별

**철학**: `cmis_philosophy_concept.md`

**전체 아키텍처**: `CMIS_Architecture_Blueprint_v3.4_km.md`

**Orchestration**: `CMIS_Orchestration_Kernel_Design.md`

**엔진**:
- BeliefEngine: `BeliefEngine_Design_Enhanced.md`
- World: `World_Engine_Enhanced_Design.md`
- Pattern: `PatternEngine_Design_Final.md`
- Strategy: `StrategyEngine_Design_Enhanced.md`
- Learning: `LearningEngine_Design_Enhanced.md`
- Workflow: `Workflow_CLI_Design_Enhanced.md`

**Greenfield/Brownfield**: `StrategyEngine_Greenfield_Brownfield.md`

---

## 📊 문서 통계

```
핵심: 3개
엔진: 7개
보조: 6개
메타: 1개
━━━━━━━━━━━━━━
Active: 17개

Deprecated: 13개
```

---

## 🎯 v3.6.0 업데이트

**신규 추가**:
- Orchestration Kernel 설계
- Reconcile Loop 패턴
- LLM Patch Provider
- Goal Predicate

**철학 강화**:
- 철학 8: Objective-Oriented Orchestration
- enforced_by 명시
- 검증 가능성

**정리 완료**:
- v3.3 문서 → deprecated
- Interface 설계 중간본 → deprecated
- 검토 문서 → deprecated (보존)

---

**작성**: 2025-12-13
**버전**: v3.6.0
**상태**: 정리 완료 ✅
