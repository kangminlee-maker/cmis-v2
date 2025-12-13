# Workflow CLI 설계 문서 (Enhanced)

**작성일**: 2025-12-11
**버전**: v1.1 (피드백 반영)
**기반**: Workflow_CLI_Design.md + 피드백
**상태**: 설계 완료

---

## Executive Summary

이 문서는 Workflow CLI 설계에 다음을 추가한 고도화 버전입니다:

1. **Canonical Workflows와 1:1 매핑** - YAML 스펙 기반 실행
2. **Role/Policy 연계 명확화** - role_plane + policy_engine 통합
3. **용어 충돌 해결** - scenario 용어 정리
4. **캐시 경계 명확화** - 엔진 레벨 vs CLI 레벨
5. **보고서 Lineage** - "세계·변화·결과·논증 구조"
6. **Batch 부분성 처리** - completeness 레벨
7. **Generic workflow run** - 확장 가능한 구조

---

## 1. 설계 철학 (Enhanced)

### 1.1 핵심 원칙

**CMIS 철학 준수**:
- **Model-first, Number-second**
- **Evidence-first, Prior-last**
- **모든 답 = (세계, 변화, 결과, 논증 구조)**
- **Monotonic Improvability & Re-runnability**
- **Agent = Persona(Role) + Workflow + View**

**CLI의 역할**:
- Interaction Plane의 1급 인터페이스
- canonical_workflows의 **실행기 (Runner)**
- role_plane + policy_engine과 연계
- 엔진 결과의 thin layer UI

**설계 원칙**:
1. **Declarative over Imperative**: cmis.yaml이 소스 오브 트루스
2. **Role-aware**: 각 명령어는 role_id와 연결
3. **Policy-driven**: policy_engine.modes 활용
4. **Lineage-first**: 모든 결과에 출처 명시
5. **Graceful Degradation**: 부분 실패 허용

---

## 2. 아키텍처 (Enhanced)

### 2.1 CMIS와의 매핑

```
CMIS Layer                    CLI Component
────────────────────────────────────────────────
Interaction Plane      →      CLI Interface
                              (cmis <command>)

canonical_workflows    →      WorkflowOrchestrator
                              (YAML 기반 실행)

role_plane            →      Role Manager
                              (role_id 해석)

policy_engine         →      Policy Resolver
                              (policy_mode 적용)

cognition_plane       →      Engine Layer
(engines)                     (world/pattern/value)

substrate_plane       →      Data Layer
(graphs, stores)              (R/P/V-Graph, stores)
```

### 2.2 계층 구조 (Refined)

```
┌──────────────────────────────────────────────┐
│          CLI Interface                        │
│  cmis workflow run <workflow_id>             │
│  cmis <role> <workflow>  (sugar)             │
└──────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│      Workflow Orchestrator                    │
│  - Load canonical_workflows (YAML)           │
│  - Resolve role → policy                     │
│  - Execute workflow steps                    │
│  - Track lineage                             │
└──────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │ World  │  │Pattern │  │ Value  │
   │ Engine │  │ Engine │  │ Engine │
   └────────┘  └────────┘  └────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│        Output Formatter + Lineage            │
│  - Console (rich)                            │
│  - JSON (with lineage)                       │
│  - Markdown (세계·변화·결과·논증)           │
└──────────────────────────────────────────────┘
```

---

## 3. Canonical Workflows 통합

### 3.1 WorkflowOrchestrator 설계 원칙

**YAML 기반 실행**:
```python
class WorkflowOrchestrator:
    """
    역할:
    - canonical_workflows (YAML) 로딩
    - workflow_id 기반 실행
    - role_id → policy_mode 해석
    - 엔진 간 데이터 전달
    """

    def __init__(self, config_path: Optional[Path] = None):
        # canonical_workflows 로딩
        self.workflows = load_canonical_workflows(config_path)
        self.role_registry = load_role_plane(config_path)
        self.policy_engine = PolicyEngine(config_path)

    def run_workflow(
        self,
        workflow_id: str,
        inputs: Dict[str, Any],
        role_id: Optional[str] = None,
        policy_mode: Optional[str] = None
    ) -> WorkflowResult:
        """
        Generic workflow 실행

        프로세스:
        1. canonical_workflows에서 workflow 정의 로딩
        2. role_id → policy_mode 해석 (override 가능)
        3. workflow steps 순차 실행
        4. 결과 조합 및 lineage 기록
        """
```

**특화 함수는 Wrapper**:
```python
def run_structure_analysis(self, inputs):
    """
    structure_analysis의 thin wrapper

    실제로는:
    return self.run_workflow(
        workflow_id="structure_analysis",
        inputs=inputs,
        role_id="structure_analyst",  # 기본값
        policy_mode="reporting_strict"  # 기본값
    )
    """
```

### 3.2 canonical_workflows 매핑 테이블

| workflow_id | CLI 명령어 | role_id | policy_mode | 상태 |
|-------------|-----------|---------|-------------|------|
| structure_analysis | structure-analysis | structure_analyst | reporting_strict | ✅ 구현 |
| opportunity_discovery | opportunity-discovery | opportunity_designer | exploration_friendly | 🔄 Phase 1 |
| strategy_design | strategy-design | strategy_architect | decision_balanced | ⏳ 미래 |
| reality_monitoring | reality-monitoring | reality_monitor | reporting_strict | ⏳ 미래 |

**구현 원칙**:
1. 각 CLI 명령어는 **canonical_workflows의 wrapper**
2. workflow_id, role_id, policy_mode는 **YAML 정의와 동기화**
3. 새 workflow 추가 시 YAML만 업데이트 → CLI 자동 인식

---

## 4. 워크플로우 명령어 설계 (Enhanced)

### 4.1 Generic workflow run (Phase 2)

**목적**: canonical_workflows 직접 실행

**명령어**:
```bash
cmis workflow run <workflow_id> \
  --input key=value \
  [--role ROLE_ID] \
  [--policy POLICY_MODE] \
  [--output FILE]
```

**예시**:
```bash
# structure_analysis 실행
cmis workflow run structure_analysis \
  --input domain_id=Adult_Language_Education_KR \
  --input region=KR \
  --input segment=office_worker

# 커스텀 policy
cmis workflow run structure_analysis \
  --input domain_id=... \
  --policy exploration_friendly
```

**구현**:
```python
def cmd_workflow_run(args):
    orchestrator = WorkflowOrchestrator()

    result = orchestrator.run_workflow(
        workflow_id=args.workflow_id,
        inputs=parse_inputs(args.input),
        role_id=args.role,
        policy_mode=args.policy
    )

    format_output(result, args.format)
```

---

### 4.2 structure-analysis (기존 + Enhanced)

**명령어**:
```bash
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  [--segment office_worker] \
  [--as-of 2025-12-05] \
  [--project-context PRJ-001] \
  [--role structure_analyst] \
  [--policy reporting_strict] \
  [--output report.json] \
  [--format json|markdown|console]
```

**새 옵션 (Enhanced)**:
- `--role ROLE_ID`: role 오버라이드 (기본: structure_analyst)
- `--policy POLICY_MODE`: policy 오버라이드 (기본: reporting_strict)

**내부 구현**:
```python
def cmd_structure_analysis(args):
    # Generic workflow run으로 위임
    return orchestrator.run_workflow(
        workflow_id="structure_analysis",
        inputs={
            "domain_id": args.domain,
            "region": args.region,
            "segment": args.segment,
            "as_of": args.as_of,
            "project_context_id": args.project_context
        },
        role_id=args.role or "structure_analyst",
        policy_mode=args.policy or "reporting_strict"
    )
```

---

### 4.3 opportunity-discovery (Enhanced)

**명령어**:
```bash
cmis opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  [--project-context PRJ-001] \
  [--role opportunity_designer] \
  [--policy exploration_friendly] \
  [--top-n 5] \
  [--min-feasibility high|medium]
```

**canonical_workflows 매핑**:
```yaml
opportunity_discovery:
  role_id: opportunity_designer
  policy_ref: exploration_friendly
  steps:
    - call: world_engine.snapshot
    - call: pattern_engine.discover_gaps
    - call: value_engine.evaluate_metrics
```

**policy 효과**:
- `exploration_friendly`: Prior 사용 허용, 추정 범위 넓음
- `reporting_strict`: Evidence만 사용, 보수적 추정

---

### 4.4 compare-contexts (용어 변경)

**기존**: `compare-scenarios` (D-Graph scenario와 충돌)
**변경**: `compare-contexts` 또는 `compare-slices`

**명령어**:
```bash
cmis compare-contexts \
  --context1 "domain:Adult_Language_Education_KR,region:KR" \
  --context2 "domain:Adult_Language_Education_KR,region:KR,project_context:PRJ-001" \
  [--output comparison.json] \
  [--format table|json|markdown]
```

**용어 정리**:
| 용어 | 의미 | 위치 |
|------|------|------|
| **context** | WorldEngine.snapshot 인자 셋 | CLI |
| **slice** | R-Graph 서브그래프 | WorldEngine |
| **scenario** | D-Graph 전략/가정 세트 | StrategyEngine |

**설계 노트**:
```
향후 D-Graph Scenario 비교 명령어:
  cmis strategy-scenarios-compare \
    --scenario1 SCN-001 \
    --scenario2 SCN-002
```

---

### 4.5 batch-analysis (Enhanced)

**명령어**:
```bash
cmis batch-analysis \
  --config batch_config.yaml \
  [--output-dir ./results] \
  [--parallel] \
  [--workers 4] \
  [--continue-on-error]
```

**batch_config.yaml (Enhanced)**:
```yaml
jobs:
  - workflow_id: structure_analysis  # canonical_workflows ID
    inputs:
      domain_id: Adult_Language_Education_KR
      region: KR
    role_id: structure_analyst  # 선택
    policy_mode: reporting_strict  # 선택
    output: adult_lang_kr.json

  - workflow_id: opportunity_discovery
    inputs:
      domain_id: Online_Tutoring_KR
      region: KR
    output: online_tutoring_kr.json
```

**결과 구조 (Enhanced)**:
```json
{
  "summary": {
    "total_jobs": 10,
    "completed": 7,
    "partial": 2,
    "failed": 1,
    "execution_time": 123.45
  },
  "jobs": [
    {
      "job_id": 1,
      "workflow_id": "structure_analysis",
      "status": "completed",
      "completeness": "full",
      "output_file": "adult_lang_kr.json"
    },
    {
      "job_id": 2,
      "workflow_id": "structure_analysis",
      "status": "completed",
      "completeness": "partial",
      "missing_items": ["MET-Market_size", "MET-CAC"],
      "output_file": "result_2.json"
    },
    {
      "job_id": 3,
      "workflow_id": "opportunity_discovery",
      "status": "failed",
      "error_code": "EVIDENCE_INSUFFICIENT",
      "error_message": "No evidence sources available for domain"
    }
  ]
}
```

**Completeness 레벨**:
- `full`: 모든 단계/metric 성공
- `partial`: 일부 metric 실패하지만 분석 가능
- `failed`: 워크플로우 실행 실패

**에러 코드**:
- `EVIDENCE_INSUFFICIENT`: Evidence 부족
- `ENGINE_ERROR`: 엔진 실행 오류
- `TIMEOUT`: 시간 초과
- `VALIDATION_ERROR`: 입력 검증 실패

---

### 4.6 report-generate (Enhanced)

**명령어**:
```bash
cmis report-generate \
  --input analysis_result.json \
  --template structure_analysis \
  [--output report.md] \
  [--format markdown|html|pdf] \
  [--include-lineage]
```

**템플릿 구조 (Enhanced)**:

**structure_analysis 템플릿**:
```markdown
# Structure Analysis Report

## Executive Summary
[세계 모델 요약]

## 1. 현실 구조 (세계)
### R-Graph 구조
- Actors, MoneyFlows, States

### Actor 분포
[테이블]

## 2. 감지된 패턴 (변화의 메커니즘)
### 핵심 패턴
- Pattern ID, 설명, 적합도

### 패턴 조합
- composes_with, conflicts_with

## 3. 핵심 Metrics (결과)
### 시장 규모
[값, 단위, 신뢰도]

### 경제 지표
[테이블]

## 4. Evidence & Lineage (논증 구조)
### 사용된 Evidence
- Source 리스트
- Tier 분포
- Confidence 요약

### Metric Resolution
- MET-Revenue: derived (공식 A + Evidence EVD-001)
- MET-Market_size: direct_evidence (KOSIS, confidence 0.95)

### Lineage
- 각 Metric의 resolution_protocol
- 사용된 Evidence ID
- 계산 경로

## 5. 제약 및 한계
- Evidence 부족 항목
- 불확실성 높은 Metric
- 권장 추가 조사
```

**--include-lineage 옵션**:
```markdown
## Lineage Details

### MET-Revenue
- Resolution: derived
- Formula: MET-N_customers × MET-ARPU
- Evidence:
  - MET-N_customers: EVD-KOSIS-001 (official, 0.95)
  - MET-ARPU: EVD-Search-123 (search, 0.6)
- Confidence: 0.77 (0.95 × 0.6 × quality_factor)

### MET-Market_size
- Resolution: direct_evidence
- Source: KOSIS (official tier)
- Evidence: EVD-KOSIS-045
- Confidence: 0.95
- As of: 2024-12-31
```

---

### 4.7 cache-manage (Enhanced)

**명령어**:
```bash
# 캐시 상태
cmis cache-manage --status

# 캐시 클리어
cmis cache-manage --clear [--type evidence|results|all] [--domain DOMAIN]

# 캐시 통계
cmis cache-manage --stats [--verbose]
```

**캐시 경계 명확화**:

| 캐시 타입 | Backing Store | 관리 주체 | CLI 역할 |
|----------|--------------|----------|---------|
| Evidence | evidence_store (SQLite) | EvidenceEngine | 조회/클리어 UI |
| Value | value_store | ValueEngine | 조회 UI |
| Snapshot | GraphCache (인메모리) | WorldEngine | 조회/클리어 |
| Result | 파일 시스템 (JSON) | CLI | 완전 관리 |

**--type 옵션 상세**:
```bash
# Evidence 캐시 (evidence_store)
cmis cache-manage --clear --type evidence
→ EvidenceEngine.cache.clear()

# Result 캐시 (CLI 레벨, JSON 파일)
cmis cache-manage --clear --type results
→ rm -rf ~/.cmis/cache/results/*

# All
cmis cache-manage --clear --type all
→ evidence_store + snapshot_cache + result_files
```

**설계 원칙**:
- CLI는 엔진 캐시의 **관리 UI**
- Payload는 엔진 store에 위임
- CLI 전용 캐시는 최소화 (result index만)

---

### 4.8 config-validate (Enhanced)

**명령어**:
```bash
cmis config-validate \
  [--file cmis.yaml] \
  [--check-seeds] \
  [--check-patterns] \
  [--check-metrics] \
  [--check-workflows] \
  [--check-all]
```

**검증 범위 (Enhanced)**:

**1. Basic (기본)**:
- YAML 구문 검증
- 필수 필드 존재 확인

**2. --check-seeds**:
- seeds/*.yaml 파일 존재
- 스키마 일치 (cmis_reality_seed)
- Actor/MoneyFlow 필수 필드

**3. --check-patterns**:
- config/patterns/*.yaml 로딩
- trait_constraints 형식
- pattern 관계 (composes_with, conflicts_with) 검증

**4. --check-metrics**:
- metrics_spec의 모든 metric_id 존재
- value_graph.metric 노드와 일치
- formula 참조 metric 존재 확인

**5. --check-workflows (신규)**:
- canonical_workflows 정의 검증
- 참조하는 엔진 API 존재 확인
- metric_sets 참조 검증
- role_id, policy_ref 존재 확인

**6. --check-all**:
- 전체 검증
- Cross-reference 확인
  - Pattern의 benchmark_metrics → metrics_spec
  - Workflow의 metric_sets → metrics_spec
  - Role의 primary_engines → engines 존재

**출력 (Enhanced)**:
```
✓ YAML 구문: OK
✓ Seeds: 1/1 passed
✓ Patterns: 23/23 passed
✓ Metrics: 45/45 passed
✓ Workflows: 4/4 passed

✓ Cross-references:
  - Pattern → Metrics: 23/23 OK
  - Workflow → Engines: 4/4 OK
  - Role → Engines: 5/5 OK

❌ Warnings:
  - MET-CAC referenced in pattern but no formula
  - workflow 'custom_analysis' not in canonical_workflows

Overall: PASS (with 2 warnings)
```

---

## 5. Role & Policy 통합

### 5.1 Role 기반 옵션

**모든 워크플로우 공통 옵션 (Enhanced)**:
```bash
--role ROLE_ID             # role 오버라이드
--policy POLICY_MODE       # policy 오버라이드
--dry-run                  # 실행 계획만 출력 (policy 포함)
```

**Role 기본값 테이블**:
| CLI 명령어 | 기본 role_id | 기본 policy_mode |
|-----------|--------------|------------------|
| structure-analysis | structure_analyst | reporting_strict |
| opportunity-discovery | opportunity_designer | exploration_friendly |
| strategy-design | strategy_architect | decision_balanced |
| batch-analysis | (job별) | (job별) |

### 5.2 Policy 효과 예시

**reporting_strict**:
- Evidence만 사용
- Prior 사용 최소화
- 보수적 추정
- 불확실성 명시

**exploration_friendly**:
- Prior 사용 허용
- 추정 범위 넓음
- 가능성 탐색

**decision_balanced**:
- Evidence + Prior 균형
- 의사결정 지원 최적화

**CLI 사용 예시**:
```bash
# 보수적 분석
cmis structure-analysis \
  --domain ... \
  --policy reporting_strict

# 탐색적 분석 (같은 도메인, 다른 policy)
cmis structure-analysis \
  --domain ... \
  --policy exploration_friendly
```

---

## 6. 출력 포맷 설계 (Enhanced)

### 6.1 JSON 출력 (Lineage 포함)

**구조**:
```json
{
  "meta": {
    "workflow_id": "structure_analysis",
    "role_id": "structure_analyst",
    "policy_mode": "reporting_strict",
    "version": "1.0",
    "timestamp": "2025-12-11T12:00:00Z",
    "execution_time": 1.23
  },
  "inputs": {
    "domain_id": "Adult_Language_Education_KR",
    "region": "KR"
  },
  "graph_overview": {...},
  "pattern_matches": [...],
  "metrics": [
    {
      "metric_id": "MET-Revenue",
      "point_estimate": 120000000000,
      "quality": {"status": "ok", "confidence": 0.85},
      "lineage": {
        "resolution_method": "derived",
        "formula": "MET-N_customers × MET-ARPU",
        "evidence_ids": ["EVD-001", "EVD-002"],
        "engine_ids": ["value_engine"]
      }
    }
  ],
  "completeness": "full",
  "warnings": []
}
```

**Lineage 필드**:
- `resolution_method`: direct_evidence | derived | prior_estimation
- `formula`: 사용된 공식 (derived인 경우)
- `evidence_ids`: 사용된 Evidence
- `engine_ids`: 관여한 엔진

---

### 6.2 Markdown 보고서 (Enhanced)

**"세계·변화·결과·논증 구조" 반영**:

```markdown
# Structure Analysis Report

## Executive Summary
[현재 시장 구조 요약]

---

## Part 1: 현실 구조 (세계)

### R-Graph Overview
- 12 actors, 8 money flows

### 시장 구조 맵
[Actor 분포, 거래 관계]

---

## Part 2: 반복 패턴 (메커니즘)

### 감지된 패턴
- PAT-subscription_model (0.85)
- PAT-network_effects (0.72)

### 패턴 조합
- subscription + network_effects (composes_with)

---

## Part 3: 핵심 지표 (결과)

### 시장 규모
- 5조원 (2024 기준)

### 경제성 지표
| Metric | 값 | 신뢰도 |
|--------|-----|--------|
| Revenue | 120억 | 0.85 |
| N_customers | 15만 | 0.90 |

---

## Part 4: 논증 구조 (근거)

### Evidence Summary
- Official: 3개 (KOSIS, DART)
- Research: 2개 (업계 보고서)
- Search: 5개 (Google)

### Metric Lineage

**MET-Revenue** (120억, 신뢰도 0.85):
- 방법: derived
- 공식: N_customers × ARPU
- Evidence:
  - EVD-KOSIS-001: N_customers (official, 0.95)
  - EVD-Search-123: ARPU (search, 0.70)
- 계산: 150,000 × 8,000원 = 120억

**MET-Market_size** (5조, 신뢰도 0.95):
- 방법: direct_evidence
- Source: KOSIS 공식 통계
- Evidence: EVD-KOSIS-045
- As of: 2024-12-31

### 불확실성 및 한계
- MET-CAC: Evidence 부족 (신뢰도 0.3, Prior 사용)
- MET-Churn_rate: Pattern benchmark 사용
```

**강제 섹션**:
- Part 1: 세계 (R-Graph)
- Part 2: 변화 (Pattern)
- Part 3: 결과 (Metric)
- Part 4: 논증 (Evidence + Lineage)

---

## 7. 에러 처리 전략 (Enhanced)

### 7.1 에러 계층

**1. Input Validation Error**:
```
❌ 입력 오류: 필수 인자 누락 '--domain'

사용법: cmis structure-analysis --domain DOMAIN --region REGION

도움말: cmis structure-analysis --help
```

**2. Workflow Execution Error**:
```
❌ 워크플로우 실행 오류

단계: pattern_engine.match_patterns
오류: IndexError at pattern_matcher.py:123

해결:
  1. --verbose로 상세 로그 확인
  2. --dry-run으로 실행 계획 확인
  3. GitHub 이슈 등록
```

**3. Partial Completion**:
```
⚠️  부분 완료: 일부 Metric 계산 실패

성공: 8/10 metrics
실패:
  - MET-Market_size: EVIDENCE_INSUFFICIENT
  - MET-CAC: FORMULA_NOT_IMPLEMENTED

결과는 부분적입니다.
Completeness: partial
출력 파일: result.json (meta.completeness="partial")
```

### 7.2 Batch 에러 처리

**--continue-on-error 옵션**:
```bash
cmis batch-analysis \
  --config batch.yaml \
  --continue-on-error  # 실패 job 무시하고 계속
```

**없으면**: 첫 실패 시 중단
**있으면**: 모든 job 시도 후 요약

**출력**:
```
[1/10] structure_analysis (Adult_Language) ✓ (1.2s)
[2/10] structure_analysis (Online_Tutoring) ⚠️  partial (2.3s)
[3/10] opportunity_discovery (Test_Market) ❌ EVIDENCE_INSUFFICIENT
[4/10] ...

Summary:
  ✓ Completed: 7/10
  ⚠️  Partial: 2/10
  ❌ Failed: 1/10

Details: batch_summary.json
```

---

## 8. 캐시 설계 (Enhanced)

### 8.1 캐시 레이어 구분

```
┌─────────────────────────────────────────┐
│   CLI Result Cache (파일)               │
│   - workflow 실행 결과 index            │
│   - TTL: 1시간                          │
└─────────────────────────────────────────┘
                  │ 참조
                  ▼
┌─────────────────────────────────────────┐
│   Engine-level Caches                   │
│   - evidence_store (SQLite, 24h)        │
│   - value_store                         │
│   - snapshot_cache (GraphCache, 1h)     │
└─────────────────────────────────────────┘
```

**CLI Result Cache**:
- 저장 위치: `~/.cmis/cache/results/`
- 내용: workflow 결과 파일 경로 + 메타
- TTL: 1시간

**구조**:
```json
{
  "cache_key": "structure_analysis|Adult_Language|KR|none|none",
  "result_file": "~/.cmis/cache/results/SA-001.json",
  "cached_at": "2025-12-11T12:00:00Z",
  "ttl_expires_at": "2025-12-11T13:00:00Z",
  "completeness": "full"
}
```

**cache-manage 상세**:
```bash
# Evidence 캐시 (엔진 레벨)
cmis cache-manage --status --type evidence
→ EvidenceEngine.cache.stats()

# Result 캐시 (CLI 레벨)
cmis cache-manage --status --type results
→ CLI result index 조회

# Snapshot 캐시 (WorldEngine)
cmis cache-manage --clear --type snapshots
→ WorldEngine.cache.clear()
```

---

## 9. 구현 계획 (Enhanced)

### 9.1 Phase 1: Core + Workflows (1.5주)

**Week 1**:
1. **WorkflowOrchestrator 고도화** (2일)
   - canonical_workflows YAML 로딩
   - role_id → policy_mode 해석
   - Generic run_workflow()
   - Lineage 추적

2. **CLI 구조 개선** (2일)
   - cmis_cli/commands/ 모듈화
   - Role/Policy 옵션 추가
   - --dry-run 구현

3. **opportunity-discovery 구현** (1일)
   - WorkflowOrchestrator 활용
   - Gap Discovery → Value Benchmark
   - 출력 포맷

**Week 2 (0.5주)**:
4. **compare-contexts 구현** (1일)
   - 2개 context snapshot 비교
   - Delta 계산
   - 테이블 출력

5. **테스트** (1일)
   - 10개 테스트

**결과**:
- Generic workflow run ✅
- opportunity-discovery ✅
- compare-contexts ✅

---

### 9.2 Phase 2: Batch + Reports (1주)

**작업**:
1. **batch-analysis** (2일)
   - YAML config 파서
   - 병렬 실행
   - completeness 레벨
   - 에러 요약

2. **report-generate** (2일)
   - Markdown 템플릿 (세계·변화·결과·논증)
   - Lineage 섹션
   - HTML 변환

3. **cache-manage** (1일)
   - 엔진 캐시 연계
   - 통계 조회

4. **테스트** (1일)
   - 8개 테스트

---

### 9.3 Phase 3: Advanced (1주)

**작업**:
1. **config-validate 확장** (2일)
   - Cross-reference 검증
   - Workflow 검증

2. **출력 포맷 개선** (2일)
   - Rich console (진행 바, 색상)
   - CSV export

3. **문서화** (2일)
   - CLI Guide
   - 사용 예시

4. **테스트** (1일)
   - 6개 테스트

---

## 10. 진화 경로 (Migration Path)

### 10.1 현재 → Generic Workflow Run

**Phase 1-1**: 기존 구조 유지
```bash
cmis structure-analysis --domain ... --region ...
```

**Phase 1-2**: Generic run 추가
```bash
cmis workflow run structure_analysis --input domain_id=... --input region=...
```

**Phase 2**: 기존 명령어는 wrapper
```python
def cmd_structure_analysis(args):
    return cmd_workflow_run(
        workflow_id="structure_analysis",
        inputs_from_args(args)
    )
```

**Phase 3**: canonical_workflows 자동 인식
```bash
# YAML에 새 workflow 추가
cmis workflow run custom_analysis --input ...
# → 자동 실행 가능
```

### 10.2 현재 → Role-aware CLI

**Phase 1**: Role 옵션만 추가
```bash
cmis structure-analysis --domain ... --role structure_analyst
```

**Phase 2**: Role 중심 진입점 (sugar)
```bash
cmis as structure-analyst run structure-analysis --domain ...
```

**Phase 3**: Role별 기본 워크플로우
```bash
cmis structure-analyst  # → 기본 워크플로우 실행
```

---

## 11. 설계 결정 사항 (ADR)

### ADR-1: canonical_workflows를 소스 오브 트루스로

**결정**: WorkflowOrchestrator는 YAML 기반 실행

**이유**:
- YAML과 코드 동기화
- 워크플로우 추가 시 YAML만 업데이트
- Declarative over Imperative

**대안**: 각 워크플로우마다 파이썬 함수
**선택 이유**: 장기 유지보수성

---

### ADR-2: scenario → context/slice 용어 변경

**결정**: compare-contexts로 명명

**이유**:
- D-Graph scenario와 충돌 방지
- 의미 명확화 (snapshot context)

**대안**: 그대로 유지하고 문서에만 명시
**선택 이유**: 용어 일관성

---

### ADR-3: CLI는 엔진 캐시의 관리 UI

**결정**: CLI 전용 캐시 최소화, 엔진 store 활용

**이유**:
- 진실의 단일 소스
- 엔진과 일관성
- 데이터 중복 최소화

**대안**: CLI 독립 캐시
**선택 이유**: 아키텍처 일관성

---

### ADR-4: 보고서는 "세계·변화·결과·논증" 구조 강제

**결정**: 모든 템플릿에 4개 섹션 필수

**이유**:
- CMIS 철학 구현
- Lineage 투명성
- 신뢰도 평가 가능

---

### ADR-5: Batch completeness 레벨 도입

**결정**: full | partial | failed

**이유**:
- 부분 실패 허용
- 결과 신뢰도 명시
- 후처리 가능

---

## 12. 설계 검증 체크리스트

### CMIS 철학 부합성

- [x] **Model-first**: R-Graph 우선 출력
- [x] **Evidence-first**: Lineage 필수 포함
- [x] **모든 답 = 세계·변화·결과·논증**: 보고서 구조
- [x] **Monotonic Improvability**: Policy 변경 가능, 재실행 지원
- [x] **Agent = Role + Workflow**: Role 옵션 지원

### cmis.yaml 정합성

- [x] canonical_workflows 매핑
- [x] role_plane 연계
- [x] policy_engine 활용
- [x] Interaction Plane 구현

### 확장성

- [x] 새 workflow 추가 용이
- [x] 커스텀 템플릿 지원
- [x] 플러그인 가능 구조

---

## 13. 향후 확장 (Roadmap)

### Phase 4: Interactive Mode (선택)

**명령어**:
```bash
cmis repl
```

**REPL 모드**:
```
CMIS> load-context PRJ-001
✓ Loaded: focal_actor=ACT-my-company

CMIS> run structure-analysis domain=Adult_Language_KR
[실행...]

CMIS> show last-metrics
[테이블 출력]

CMIS> run opportunity-discovery --top-n 3
[실행...]

CMIS> compare last-2-results
[비교 테이블]
```

**효과**:
- 반복 분석 편의
- 탐색적 워크플로우

---

### Phase 5: Plugin System

**구조**:
```
cmis_cli/plugins/
├── education_kr/
│   ├── workflows.yaml
│   └── commands.py
└── saas_global/
    ├── workflows.yaml
    └── commands.py
```

**사용**:
```bash
cmis workflow run education_kr.custom_analysis --input ...
```

---

## 14. 피드백 반영 요약

### 반영된 7개 주요 피드백

1. ✅ **Canonical Workflows 1:1 매핑** → YAML 기반 실행, generic run
2. ✅ **Role/Policy 연계** → 옵션 추가, 기본값 테이블
3. ✅ **scenario 용어 충돌** → compare-contexts로 변경
4. ✅ **캐시 경계** → 엔진 store 활용, CLI는 UI
5. ✅ **보고서 논증 구조** → Lineage 섹션 강제
6. ✅ **Batch completeness** → full/partial/failed 레벨
7. ✅ **config-validate 확장** → Cross-reference 검증

### 추가 개선

8. ✅ **ADR 문서화** → 5개 설계 결정
9. ✅ **진화 경로** → Migration path 명시
10. ✅ **향후 확장** → REPL, Plugin system

---

## 15. 다음 단계

### 우선순위 1: Phase 1 구현 (즉시)

**작업**:
- WorkflowOrchestrator 고도화
- opportunity-discovery 구현
- Role/Policy 옵션

**예상 시간**: 1.5주

### 우선순위 2: Phase 2 구현

**작업**:
- batch-analysis
- report-generate (Lineage 포함)

**예상 시간**: 1주

---

**작성**: 2025-12-11
**상태**: 설계 완료 (Enhanced)
**기반**: Workflow_CLI_Design.md + 피드백 7개 반영
**다음**: Phase 1 구현 착수

**Workflow CLI v1.1 설계 완성!**



