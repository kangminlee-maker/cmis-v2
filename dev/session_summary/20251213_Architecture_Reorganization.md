# 2025-12-13 세션: Architecture 재구성 및 v3.6.0 설계

**날짜**: 2025-12-13
**주요 작업**: 
- 철학 v2 정렬
- Blueprint v3.4 작성
- Orchestration Kernel 설계
- cmis.yaml 재구성 (Contracts + Registry)
- 문서 정리

---

## 🎯 주요 성과

### 1. 철학 v2 완성

**파일**: `cmis_philosophy_concept.md`

**10대 철학**:
1. Evidence-first, Prior-last
2. 권위 있는 Substrate (SSoT)
3. Model-first, Number-second
4. Graph-of-Graphs (R/P/V/D)
5. Trait 기반 Ontology
6. Project Context 1급
7. 세계-변화-결과-논증
8. **Objective-Oriented Orchestration** (신규!)
9. Agent = Persona + Workflow
10. Monotonic Improvability

**핵심**: enforced_by 명시 (철학 → 구성요소 매핑)

---

### 2. Blueprint v3.4 작성

**파일**: `CMIS_Architecture_Blueprint_v3.4_km.md`

**핵심 개선**:
- 철학 정렬 재구성
- Ledger 기반 설계 (Project + Progress)
- 재현성/감사 강조
- 검증 체크리스트

---

### 3. Orchestration Kernel 설계

**파일**: `CMIS_Orchestration_Kernel_Design.md`

**패러다임**: Reconcile Loop (Kubernetes)

**5개 핵심 추상화**:
1. GoalGraph (D-Graph 활용)
2. TaskQueue
3. Ledgers (Project + Progress, 2개)
4. Verifier (Predicate → Diff)
5. Replanner (부분 재계획)

**LLM**: PlanPatch 제안자 (검증 후 적용)

---

### 4. cmis.yaml 재구성

**Before**: 모놀리식 (2,063줄)

**After**: Contracts + Registry (735줄)
- 철학 명시
- 외부 모듈 참조
- Registries

**외부 파일** (신규):
- `schemas/ledgers.yaml` (158줄)
- `config/policies.yaml` (90줄)
- `config/workflows.yaml` (115줄)

**구버전**: `dev/deprecated/cmis_v3.5.yaml`

---

### 5. 용어 결정

**파일**: `Terminology_Decision.md`

**결정**:
1. **orchestration_plane + kernel** (이중 구조)
   - Plane: 아키텍처 레벨
   - Kernel: 구현 레벨

2. **Project Ledger** (not Task)
   - 명확성 (혼동 방지)
   - CMIS 맥락 적합

---

### 6. 문서 정리

**Deprecated 통합**:
```
architecture/
architecture_old/
→ architecture_v3.3_and_earlier/ (25개 통합)
```

**Active 문서**: 18개 (정리됨)

**복구**: Blueprint_v3.4_Review.md (참고용)

---

## 📊 통계

### 코드
```
cmis.yaml: 2,063줄 → 735줄 (-65%)
외부 YAML: 0개 → 3개 (363줄)
```

### 문서
```
신규: 5개
  - cmis_philosophy_concept.md (v2)
  - CMIS_Architecture_Blueprint_v3.4_km.md
  - CMIS_Orchestration_Kernel_Design.md
  - Terminology_Decision.md
  - Blueprint_v3.4_Review.md (검토)

Deprecated: 8개 → architecture_v3.3_and_earlier/
```

### 파일 정리
```
Active: 18개 (architecture)
Deprecated: 25개 (통합)
```

---

## 🏗️ 최종 구조

```
cmis/
├─ cmis.yaml (v3.6.0 Contracts)
├─ schemas/
│  └─ ledgers.yaml
├─ config/
│  ├─ policies.yaml
│  └─ workflows.yaml
├─ dev/
│  ├─ docs/architecture/ (18개)
│  └─ deprecated/
│     ├─ cmis_v3.5.yaml
│     └─ docs/architecture_v3.3_and_earlier/ (25개)
└─ .cursorrules (버전 관리 규칙 추가)
```

---

## 🎯 핵심 결정

1. **YAML 역할**: 구현 스펙 ❌ → Contracts + Registry ✅
2. **Orchestration**: Plane (구조) + Kernel (실행)
3. **Ledgers**: Project (상태) + Progress (제어)
4. **버전 관리**: 버전별 폴더 (architecture_v{version})

---

## 📝 다음 단계

### v3.6.0 구현 (예정)
1. OrchestrationKernel 구현
2. ProjectLedger, ProgressLedger 구현
3. Verifier, Replanner 구현
4. LLMPatchProvider 구현

### 문서 완성
1. 외부 YAML 파일 확장
2. Glossary 추가
3. 구현 가이드

---

**작성**: 2025-12-13
**버전**: CMIS v3.6.0 (설계)
**상태**: 재구성 완료 ✅
