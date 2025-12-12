# CMIS Architecture 문서 인덱스

**최종 업데이트**: 2025-12-12
**버전**: CMIS v3.5.0 (100% Complete)

---

## 📋 엔진별 설계 문서 (최신 버전만)

### 1. BeliefEngine v1.0 🆕
**파일**: `BeliefEngine_Design_Enhanced.md`
**상태**: ✅ Production Ready
**라인**: 1,225줄
**보조 문서**:
- `BeliefEngine_Feedback_Review.md` - 피드백 검토
- `BeliefEngine_Implementation_Complete.md` - 구현 완료
- `BeliefEngine_Future_Enhancements.md` - v1.1+ 계획

### 2. World Engine v2.0
**파일**: `World_Engine_Enhanced_Design.md`
**상태**: ✅ Production Ready
**라인**: 1,085줄
**주요 내용**:
- Phase A/B/C 설계
- Greenfield/Brownfield 지원
- 필터링, 서브그래프 추출

### 3. Pattern Engine v2.0
**파일**: `PatternEngine_Design_Final.md`
**상태**: ✅ Production Ready
**라인**: 900줄
**주요 내용**:
- Trait 기반 매칭
- Gap Discovery
- Context Archetype

### 4. Strategy Engine v1.0
**파일**: `StrategyEngine_Design_Enhanced.md`
**상태**: ✅ Production Ready
**라인**: 1,500줄
**보조 문서**:
- `StrategyEngine_Greenfield_Brownfield.md` - 모드별 설계
- `StrategyEngine_Constraints_Design.md` - 제약 조건

### 5. Learning Engine v1.0
**파일**: `LearningEngine_Design_Enhanced.md`
**상태**: ✅ Production Ready
**라인**: 840줄
**주요 내용**:
- 4-Learner 구조
- Outcome 비교
- ProjectContext 버전 관리

### 6. Workflow CLI
**파일**: `Workflow_CLI_Design_Enhanced.md`
**상태**: ✅ Production Ready
**라인**: 1,230줄
**주요 내용**:
- 8개 명령어
- canonical_workflows 통합

### 7. Search Strategy v2.0
**파일**: `Search_Strategy_Design_v2.md`
**상태**: ✅ Production Ready

---

## 📖 프로젝트 전체 문서

### CMIS 전체 아키텍처
1. **`CMIS_Architecture_Blueprint_v3.3.md`** (358줄)
   - 4 Planes 아키텍처
   - Graph-of-Graphs
   - 9개 엔진 개요

2. **`CMIS_Implementation_Status_v3.3.md`** (600줄)
   - 구현 현황
   - 엔진별 상태
   - 테스트 통계

3. **`CMIS_Roadmap_v3.3.md`** (400줄)
   - Phase별 개발 계획
   - Milestone

### 철학 및 컨셉
4. **`cmis_philosophy_concept.md`**
   - CMIS 철학
   - 핵심 원칙

5. **`cmis_project_context_layer_design.md`**
   - Project Context 설계
   - Greenfield/Brownfield

---

## 🗂️ 폴더 구조

```
dev/docs/architecture/
├─ README.md (본 문서)
│
├─ [엔진별 설계 - 최신]
│  ├─ BeliefEngine_Design_Enhanced.md ⭐
│  ├─ World_Engine_Enhanced_Design.md
│  ├─ PatternEngine_Design_Final.md
│  ├─ StrategyEngine_Design_Enhanced.md
│  ├─ LearningEngine_Design_Enhanced.md
│  ├─ Workflow_CLI_Design_Enhanced.md
│  └─ Search_Strategy_Design_v2.md
│
├─ [보조 문서]
│  ├─ BeliefEngine_Feedback_Review.md
│  ├─ BeliefEngine_Implementation_Complete.md
│  ├─ BeliefEngine_Future_Enhancements.md
│  ├─ StrategyEngine_Greenfield_Brownfield.md
│  └─ StrategyEngine_Constraints_Design.md
│
└─ [프로젝트 전체]
   ├─ CMIS_Architecture_Blueprint_v3.3.md
   ├─ CMIS_Implementation_Status_v3.3.md
   ├─ CMIS_Roadmap_v3.3.md
   ├─ cmis_philosophy_concept.md
   └─ cmis_project_context_layer_design.md
```

---

## 🗄️ Deprecated 문서

**위치**: `dev/deprecated/docs/architecture_old/`

구버전 파일들:
- `LearningEngine_Design.md` → Enhanced 버전으로 대체
- `Strategy_Engine_Design.md` → Enhanced 버전으로 대체
- `Workflow_CLI_Design.md` → Enhanced 버전으로 대체
- `CMIS_LLM_Infrastructure_Design.md` → 구 설계
- `CMIS_LLM_Infrastructure_Revision.md` → 구 설계

---

## 📊 문서 통계

```
엔진별 설계: 7개 (최신)
보조 문서: 5개
프로젝트 전체: 5개
━━━━━━━━━━━━━━━━━━━━
총 17개 (active)

Deprecated: 5개
```

---

## 🔍 빠른 검색

### 엔진 찾기
- **BeliefEngine**: `BeliefEngine_Design_Enhanced.md`
- **World Engine**: `World_Engine_Enhanced_Design.md`
- **Pattern Engine**: `PatternEngine_Design_Final.md`
- **Value Engine**: `CMIS_Architecture_Blueprint_v3.3.md` (Section 참조)
- **Strategy Engine**: `StrategyEngine_Design_Enhanced.md`
- **Learning Engine**: `LearningEngine_Design_Enhanced.md`
- **Workflow**: `Workflow_CLI_Design_Enhanced.md`
- **Search**: `Search_Strategy_Design_v2.md`

### 주제별 찾기
- **Greenfield/Brownfield**: `StrategyEngine_Greenfield_Brownfield.md`
- **제약 조건**: `StrategyEngine_Constraints_Design.md`
- **철학**: `cmis_philosophy_concept.md`
- **Project Context**: `cmis_project_context_layer_design.md`
- **Future**: `BeliefEngine_Future_Enhancements.md`

---

**작성**: 2025-12-12
**버전**: v3.5.0
**상태**: 정리 완료 ✅
