# Workflow CLI 피드백 검토 및 반영 보고

**작성일**: 2025-12-11
**기반**: Workflow_CLI_Design.md 피드백
**상태**: ✅ 검토 및 반영 완료

---

## Executive Summary

Workflow CLI 설계에 대한 7개 주요 피드백을 검토하고 모두 반영했습니다.

**결론**:
- 기존 구조는 CMIS 철학과 잘 맞음
- 대수술 불필요, 설계 레벨 보강으로 충분
- Enhanced 버전 작성 완료

---

## 피드백 검토 및 반영

### 1. Canonical Workflows와 1:1 매핑 명시 ✅

**피드백**:
- WorkflowOrchestrator가 canonical_workflows의 **실행 러너**가 되어야 함
- YAML 정의와 코드 동기화 필요
- Generic `workflow run` 고려

**반영 내용**:

**1) Generic run_workflow() 설계**:
```python
class WorkflowOrchestrator:
    def __init__(self):
        self.workflows = load_canonical_workflows()  # YAML 로딩
        self.role_registry = load_role_plane()
        self.policy_engine = PolicyEngine()

    def run_workflow(
        workflow_id: str,
        inputs: Dict,
        role_id: Optional[str] = None,
        policy_mode: Optional[str] = None
    ):
        """
        Generic workflow 실행
        - canonical_workflows YAML 기반
        - role → policy 자동 해석
        """
```

**2) 특화 함수는 Wrapper**:
```python
def run_structure_analysis(inputs):
    return self.run_workflow(
        workflow_id="structure_analysis",
        inputs=inputs,
        role_id="structure_analyst",
        policy_mode="reporting_strict"
    )
```

**3) CLI 명령어**:
```bash
# Generic run (Phase 2)
cmis workflow run structure_analysis --input domain_id=... --input region=...

# Sugar command (Phase 1, 기존 유지)
cmis structure-analysis --domain ... --region ...
```

**4) 진화 경로 (Migration Path)**:
- Phase 1-1: 기존 구조 유지
- Phase 1-2: Generic run 추가
- Phase 2: 기존은 wrapper
- Phase 3: YAML 자동 인식

**문서 위치**: Enhanced Design § 3, § 10.1

---

### 2. Role / Policy 연계 명확화 ✅

**피드백**:
- 각 워크플로우의 role_id, policy_mode 명시 필요
- CLI 옵션으로 override 지원
- role_plane + policy_engine 연결

**반영 내용**:

**1) 워크플로우-Role-Policy 매핑 테이블**:
| workflow_id | CLI 명령어 | role_id | policy_mode |
|-------------|-----------|---------|-------------|
| structure_analysis | structure-analysis | structure_analyst | reporting_strict |
| opportunity_discovery | opportunity-discovery | opportunity_designer | exploration_friendly |
| strategy_design | strategy-design | strategy_architect | decision_balanced |

**2) CLI 옵션 추가**:
```bash
cmis structure-analysis \
  --domain ... \
  --role structure_analyst \    # 기본값 오버라이드 가능
  --policy reporting_strict     # 기본값 오버라이드 가능
```

**3) Policy 효과 명시**:
- `reporting_strict`: Evidence만, 보수적
- `exploration_friendly`: Prior 허용, 탐색적
- `decision_balanced`: Evidence + Prior 균형

**4) WorkflowOrchestrator 통합**:
```python
policy_ref = policy_engine.resolve_policy(
    role_id=role_id_from_cli_or_default,
    usage="reporting" / "decision" / "exploration"
)
```

**문서 위치**: Enhanced Design § 5

---

### 3. scenario 용어 충돌 해결 ✅

**피드백**:
- `compare-scenarios`의 scenario가 D-Graph scenario와 충돌
- context 또는 slice로 용어 변경 권장

**반영 내용**:

**1) 명령어 변경**:
- **Before**: `compare-scenarios`
- **After**: `compare-contexts`

**2) 용어 정리 테이블**:
| 용어 | 의미 | 위치 | 예시 |
|------|------|------|------|
| context | snapshot 인자 셋 | CLI | domain, region, project_context |
| slice | R-Graph 서브그래프 | WorldEngine | focal_actor 2-hop |
| scenario | 전략/가정 세트 | D-Graph | SCN-aggressive-growth |

**3) 향후 명령어 분리**:
```bash
# Context 비교 (현재)
cmis compare-contexts \
  --context1 "domain:...,region:..." \
  --context2 "domain:...,project_context:PRJ-001"

# Scenario 비교 (미래, D-Graph)
cmis strategy-scenarios-compare \
  --scenario1 SCN-001 \
  --scenario2 SCN-002
```

**문서 위치**: Enhanced Design § 4.4

---

### 4. 캐시 경계 명확화 ✅

**피드백**:
- CLI 캐시 vs 엔진 캐시 경계 명확화 필요
- CLI는 엔진 store의 관리 UI 역할

**반영 내용**:

**1) 캐시 레이어 구분 테이블**:
| 캐시 타입 | Backing Store | 관리 주체 | CLI 역할 |
|----------|--------------|----------|---------|
| Evidence | evidence_store (SQLite) | EvidenceEngine | 조회/클리어 UI |
| Value | value_store | ValueEngine | 조회 UI |
| Snapshot | GraphCache (인메모리) | WorldEngine | 조회/클리어 |
| Result | 파일 시스템 (JSON) | CLI | 완전 관리 |

**2) cache-manage 상세화**:
```bash
# Evidence 캐시 (엔진 레벨)
cmis cache-manage --status --type evidence
→ EvidenceEngine.cache.stats()

# Snapshot 캐시 (WorldEngine)
cmis cache-manage --clear --type snapshots
→ WorldEngine.cache.clear()

# Result 캐시 (CLI 레벨만)
cmis cache-manage --clear --type results
→ rm ~/.cmis/cache/results/*
```

**3) 설계 원칙**:
- CLI는 엔진 캐시의 **관리 UI**
- Payload는 엔진 store에 위임
- CLI 전용 캐시는 최소화 (result index만)

**문서 위치**: Enhanced Design § 8

---

### 5. 보고서 "세계·변화·결과·논증 구조" ✅

**피드백**:
- 보고서 템플릿에서 4개 구조 명시 필요
- Evidence & Lineage 섹션 강제
- resolution_protocol 요약

**반영 내용**:

**1) 강제 섹션 (4-Part Structure)**:
```markdown
## Part 1: 현실 구조 (세계)
- R-Graph Overview
- Actor 분포
- 거래 관계

## Part 2: 반복 패턴 (메커니즘)
- 감지된 패턴
- 패턴 조합

## Part 3: 핵심 지표 (결과)
- 시장 규모
- 경제성 지표

## Part 4: 논증 구조 (근거)
- Evidence Summary
- Metric Lineage
- 불확실성 및 한계
```

**2) Lineage 상세 포함**:
```markdown
### Metric Lineage

**MET-Revenue** (120억, 신뢰도 0.85):
- 방법: derived
- 공식: N_customers × ARPU
- Evidence:
  - EVD-KOSIS-001: N_customers (official, 0.95)
  - EVD-Search-123: ARPU (search, 0.70)
- 계산: 150,000 × 8,000원 = 120억
```

**3) --include-lineage 옵션**:
```bash
cmis report-generate \
  --input analysis.json \
  --template structure_analysis \
  --include-lineage  # Lineage 상세 포함
```

**문서 위치**: Enhanced Design § 6.2

---

### 6. Batch 부분성 처리 전략 ✅

**피드백**:
- 일부 job 실패 시 처리 전략 구체화
- completeness 레벨 도입

**반영 내용**:

**1) Completeness 레벨**:
- `full`: 모든 단계/metric 성공
- `partial`: 일부 metric 실패하지만 분석 가능
- `failed`: 워크플로우 실행 실패

**2) Batch 결과 구조**:
```json
{
  "summary": {
    "total_jobs": 10,
    "completed": 7,
    "partial": 2,
    "failed": 1
  },
  "jobs": [
    {
      "job_id": 1,
      "completeness": "full",
      "output_file": "result_1.json"
    },
    {
      "job_id": 2,
      "completeness": "partial",
      "missing_items": ["MET-Market_size", "MET-CAC"],
      "output_file": "result_2.json"
    },
    {
      "job_id": 3,
      "completeness": "failed",
      "error_code": "EVIDENCE_INSUFFICIENT"
    }
  ]
}
```

**3) 에러 코드 체계**:
- `EVIDENCE_INSUFFICIENT`
- `ENGINE_ERROR`
- `TIMEOUT`
- `VALIDATION_ERROR`

**4) --continue-on-error 옵션**:
```bash
cmis batch-analysis \
  --config batch.yaml \
  --continue-on-error  # 실패 무시하고 계속
```

**문서 위치**: Enhanced Design § 4.5, § 7.2

---

### 7. config-validate 범위 확장 ✅

**피드백**:
- CMIS 스펙 전체 검증으로 확장
- Cross-reference 검증

**반영 내용**:

**1) 검증 범위 확장**:
```bash
cmis config-validate \
  [--check-seeds] \
  [--check-patterns] \
  [--check-metrics] \
  [--check-workflows]  # 신규
  [--check-all]        # Cross-reference 포함
```

**2) --check-workflows (신규)**:
- canonical_workflows 정의 검증
- 참조 엔진 API 존재 확인
- metric_sets 참조 검증
- role_id, policy_ref 존재 확인

**3) --check-all (확장)**:
- 전체 검증
- **Cross-reference** 검증:
  - Pattern.benchmark_metrics → metrics_spec 존재
  - Workflow.metric_sets → metrics_spec 존재
  - Role.primary_engines → engines 존재
  - Trait keys → ontology.traits 존재

**4) 출력 예시**:
```
✓ Cross-references:
  - Pattern → Metrics: 23/23 OK
  - Workflow → Engines: 4/4 OK
  - Workflow → Metric_sets: 4/4 OK
  - Role → Engines: 5/5 OK
  - Traits → Ontology: 45/45 OK

❌ Warnings:
  - MET-CAC in pattern but no formula
  - workflow 'custom' not in canonical_workflows
```

**문서 위치**: Enhanced Design § 4.8

---

## 추가 개선 사항

### 8. Generic workflow run 구조 ✅

**대안 1 반영**:
- `cmis workflow run <workflow_id>` 명령어 추가
- canonical_workflows 자동 인식
- 확장 가능한 구조

**장점**:
- YAML 추가만으로 새 workflow 지원
- 코드-YAML 동기화
- Declarative 철학

**문서 위치**: Enhanced Design § 4.1, § 10.1

---

### 9. Role-aware CLI (선택적) ✅

**대안 2 반영**:
- Role 중심 진입점 옵션
- 향후 확장으로 문서화

**명령어**:
```bash
# Phase 1: Role 옵션
cmis structure-analysis --role structure_analyst

# Phase 2: Role 중심 진입점 (sugar)
cmis as structure-analyst run structure-analysis

# Phase 3: Role 기본 워크플로우
cmis structure-analyst  # → 기본 워크플로우
```

**문서 위치**: Enhanced Design § 10.2

---

### 10. 기타 고려사항

**a) memory_store / query_trace 연결**:
- 각 CLI 실행을 query_trace로 기록
- 향후 학습/분석 기반

**b) Plugin System**:
- cmis_cli/plugins/ 구조
- 도메인별 커스텀 workflow

**c) Interactive Mode (REPL)**:
- `cmis repl`
- 반복 대화형 분석

**문서 위치**: Enhanced Design § 13 (향후 확장)

---

## 설계 결정 사항 (ADR)

### ADR-1: canonical_workflows를 소스 오브 트루스로

**결정**: YAML 기반 실행, Generic run_workflow()

**이유**:
- 코드-YAML 동기화
- 장기 유지보수성

**문서**: Enhanced Design § 11

---

### ADR-2: scenario → context 용어 변경

**결정**: compare-contexts

**이유**:
- D-Graph scenario 충돌 방지
- 의미 명확화

---

### ADR-3: CLI는 엔진 캐시 관리 UI

**결정**: 엔진 store 활용, CLI 전용 캐시 최소화

**이유**:
- 진실의 단일 소스
- 아키텍처 일관성

---

### ADR-4: 보고서 4-Part 구조 강제

**결정**: 세계·변화·결과·논증

**이유**:
- CMIS 철학 구현
- Lineage 투명성

---

### ADR-5: Batch completeness 레벨

**결정**: full | partial | failed

**이유**:
- 부분 실패 허용
- Graceful Degradation

---

## 변경 요약

### 기존 설계 (v1.0)

**장점**:
- 명확한 계층 구조
- 7개 워크플로우 명령어
- 4종 출력 포맷

**한계**:
- canonical_workflows와 코드 중복 가능
- Role/Policy 연계 미흡
- scenario 용어 충돌
- 캐시 경계 불명확

---

### Enhanced 설계 (v1.1)

**개선**:
1. ✅ **Generic workflow run** - YAML 기반 실행
2. ✅ **Role/Policy 옵션** - 기본값 + override
3. ✅ **용어 정리** - context/slice/scenario 분리
4. ✅ **캐시 레이어 구분** - 엔진 vs CLI 명확화
5. ✅ **Lineage 강제** - 보고서 4-Part 구조
6. ✅ **Completeness 레벨** - full/partial/failed
7. ✅ **Cross-reference 검증** - config-validate 확장

**추가**:
- ADR 문서화 (5개)
- 진화 경로 (Migration Path)
- 향후 확장 (REPL, Plugin)

---

## 구현 우선순위 (Enhanced)

### Phase 1: Core + Workflows (1.5주)

**Week 1**:
1. WorkflowOrchestrator 고도화 (2일)
   - canonical_workflows YAML 로딩
   - Generic run_workflow()
   - role → policy 해석

2. CLI 구조 개선 (2일)
   - Role/Policy 옵션
   - --dry-run 구현

3. opportunity-discovery (1일)
   - WorkflowOrchestrator 활용

**Week 2 (0.5주)**:
4. compare-contexts (1일)
5. 테스트 (1일)

---

### Phase 2: Batch + Reports (1주)

**작업**:
1. batch-analysis (completeness 포함)
2. report-generate (Lineage 강제)
3. cache-manage (엔진 연계)

---

### Phase 3: Advanced (1주)

**작업**:
1. config-validate 확장 (Cross-reference)
2. Rich console 출력
3. 문서화

---

## 피드백 반영 체크리스트

### 구조적 반영

- [x] Canonical Workflows 1:1 매핑
- [x] Generic workflow run 설계
- [x] YAML 기반 실행 원칙
- [x] 특화 함수는 wrapper

### 기능적 반영

- [x] Role/Policy 옵션 추가
- [x] scenario → context 용어 변경
- [x] 캐시 레이어 구분
- [x] Completeness 레벨 도입

### 품질적 반영

- [x] 보고서 4-Part 구조
- [x] Lineage 섹션 강제
- [x] Cross-reference 검증
- [x] ADR 문서화

---

## 최종 파일

### 생성된 문서

1. **Workflow_CLI_Design_Enhanced.md** (약 1,500 라인)
   - 피드백 7개 완전 반영
   - ADR 5개 추가
   - 진화 경로 명시

2. **WORKFLOW_CLI_FEEDBACK_REVIEW.md** (현재 문서)
   - 피드백 검토 내역
   - 반영 상세
   - 변경 요약

---

## 다음 단계

### Option 1: Workflow CLI Phase 1 구현

**작업**:
- WorkflowOrchestrator 고도화
- opportunity-discovery
- Role/Policy 통합

**예상 시간**: 1.5주

---

### Option 2: StrategyEngine 설계 먼저

**이유**:
- strategy_design workflow 정의 필요
- CLI 구현 시 StrategyEngine API 참조

**예상 시간**: 1주 (설계)

---

**작성**: 2025-12-11
**상태**: 피드백 검토 및 반영 완료 ✅
**결과**: Enhanced Design v1.1
**다음**: Phase 1 구현 또는 StrategyEngine 설계



