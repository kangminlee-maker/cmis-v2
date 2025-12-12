# CMIS v3.3 아키텍처 블루프린트

**버전**: v3.3  
**업데이트**: 2025-12-11  
**상태**: Production Ready

---

## Executive Summary

CMIS (Contextual Market Intelligence System)는 **시장/비즈니스 세계를 Graph-of-Graphs로 표현**하고, **Understand → Discover → Decide → Learn 루프**를 통해 자동으로 시장을 분석하고 전략을 설계하는 Market Intelligence OS입니다.

**현재 상태**:
- **완성 엔진**: 8/9 (89%)
- **테스트**: 370/375 (98.7%)
- **Production Ready**: ✅

---

## 1. 시스템 개요

### 1.1 CMIS가 하는 일

**4단계 루프**:
```
1. Understand (이해)
   → 시장 구조, 패턴, 지표 파악

2. Discover (발굴)
   → 기회 자동 발굴 (Gap Discovery)

3. Decide (결정)
   → 전략 생성 및 평가

4. Learn (학습)
   → 실제 결과로부터 학습
   ↓
다시 1번으로 (지속 개선)
```

### 1.2 Graph-of-Graphs

**4개 그래프**:
- **R-Graph** (Reality): 시장 구조 (Actor, MoneyFlow, State)
- **P-Graph** (Pattern): 비즈니스 패턴 (23개 Pattern)
- **V-Graph** (Value): 지표/값 (Metric, ValueRecord)
- **D-Graph** (Decision): 전략/목표 (Goal, Strategy)

---

## 2. 완성 엔진 (8/9)

### 2.1 Evidence Engine v2.2 (100%)

**역할**: Evidence 수집 및 관리

**기능**:
- 6개 Source: DART, KOSIS, ECOS, WorldBank, Google, DuckDuckGo
- 3-Tier 시스템 (Official, Curated, Commercial)
- Early Return 전략
- SQLite 캐싱 (24시간)

**API**:
- `fetch_for_metrics(metric_requests)`
- `fetch_for_reality_slice(entity_type, context)`

---

### 2.2 Pattern Engine v2.0 (100%)

**역할**: 비즈니스 패턴 인식 및 Gap 발굴

**기능**:
- 23개 Pattern 정의 (5개 Family)
- Trait 기반 매칭
- Structure Fit + Execution Fit 이중 평가
- Gap Discovery
- Context Archetype (6개)

**API**:
- `match_patterns(graph, project_context_id)`
- `discover_gaps(graph, project_context_id)`

**Pattern 예시**:
- PAT-subscription_model
- PAT-platform_business_model
- PAT-network_effects
- PAT-freemium_model

---

### 2.3 Value Engine v2.0 (100%)

**역할**: Metric 계산 및 평가

**기능**:
- 4-Stage Resolution (Evidence → Derived → Prior → Fusion)
- Pattern Benchmark 연동
- Lineage 완전 추적

**API**:
- `evaluate_metrics(graph, metric_requests, policy_ref)`

**Metric 예시**:
- MET-Revenue, MET-N_customers
- MET-TAM, MET-SAM, MET-SOM
- MET-LTV, MET-CAC, MET-Churn_rate

---

### 2.4 World Engine v2.0 (100%) ⭐

**역할**: Reality Graph 구축 및 관리

**기능**:
- RealityGraphStore (세계 모델)
- ProjectOverlayStore (프로젝트별)
- as_of/segment 필터링
- ingest_project_context (Brownfield)
- ingest_evidence (동적 확장)
- 서브그래프 추출 (focal_actor 중심)
- 파일 백엔드, 캐싱
- 시계열 비교

**API**:
- `snapshot(domain_id, region, segment, as_of, project_context_id)`
- `ingest_project_context(project_context)`
- `ingest_evidence(domain_id, evidence_list)`

**Phase**:
- Phase A: Brownfield + 필터링
- Phase B: ingest_evidence (동적 확장)
- Phase C: 성능 최적화

---

### 2.5 Strategy Engine v1.0 (100%) ⭐

**역할**: 전략 생성 및 평가

**기능**:
- Pattern → Strategy 변환
- Greenfield/Brownfield 지원
- ROI/Risk 예측
- Portfolio 최적화
- Synergy/Conflict 분석
- PolicyEngine 통합

**API**:
- `search_strategies_api(goal_id, constraints, project_context_id)`
- `evaluate_portfolio_api(strategy_ids, policy_ref, project_context_id)`

**전략 생성**:
- Single Pattern
- Pattern Composition
- Gap-based

---

### 2.6 Learning Engine v1.0 (100%) ⭐

**역할**: 학습 및 시스템 개선

**기능**:
- Outcome vs 예측 비교
- Pattern Benchmark 학습 (Context별)
- ProjectContext 업데이트 (버전 관리)
- Metric Belief 조정
- Outlier 감지

**API**:
- `update_from_outcomes_api(outcome_ids)`
- `update_project_context_from_outcome_api(outcome_id, project_context_id)`

**4-Learner**:
- OutcomeComparator
- PatternLearner
- MetricLearner
- ContextLearner

---

### 2.7 Workflow CLI (100%) ⭐

**역할**: 명령줄 인터페이스

**명령어** (8개):
1. `structure-analysis`: 시장 구조 분석
2. `opportunity-discovery`: 기회 발굴
3. `compare-contexts`: 컨텍스트 비교
4. `workflow run`: Generic workflow 실행
5. `batch-analysis`: 일괄 분석 (병렬)
6. `report-generate`: 보고서 생성
7. `cache-manage`: 캐시 관리
8. `config-validate`: 설정 검증

**특징**:
- canonical_workflows 통합
- Role/Policy 옵션
- Lineage 포함 출력

---

## 3. Greenfield vs Brownfield

### 3.1 정의

**Greenfield**:
- '나' 없이 시장 전체를 neutral하게 분석
- ProjectContext 없음
- 최소 제약 (자본, 시간)만 입력 가능

**Brownfield**:
- '나'(focal_actor) 관점에서 분석
- ProjectContext 있음 (baseline_state, assets_profile, constraints)
- 실행 가능한 전략만

### 3.2 모든 엔진에서 지원

- World Engine: `project_context_id` 옵션
- Pattern Engine: Execution Fit 계산
- Strategy Engine: `greenfield_constraints` vs `project_context`
- Learning Engine: ProjectContext 업데이트

---

## 4. 데이터 흐름

### 4.1 Understand 단계

```
Evidence → World Engine → R-Graph
                ↓
         Pattern Engine → Pattern Matches
                ↓
         Value Engine → Metrics
```

### 4.2 Discover 단계

```
R-Graph + Pattern Matches
         ↓
   Pattern Engine
         ↓
   Gap Candidates (기회)
```

### 4.3 Decide 단계

```
Pattern + Gap + Goal
         ↓
   Strategy Engine
         ↓
   Strategy + Portfolio
```

### 4.4 Learn 단계

```
Outcome (실제 결과)
         ↓
   Learning Engine
         ↓
Pattern Benchmark 업데이트
ProjectContext 업데이트
         ↓
   (Understand로 돌아감)
```

---

## 5. 구현 현황

### 5.1 완성 (8/9)

| 엔진 | 완성도 | 코드 | 테스트 |
|------|--------|------|--------|
| Evidence Engine | 100% | 완성 | ✅ |
| Pattern Engine | 100% | 완성 | ✅ |
| Value Engine | 100% | 완성 | ✅ |
| World Engine | 100% | 4,110 | 56/56 |
| Search Strategy | 100% | 완성 | ✅ |
| Workflow CLI | 100% | 2,370 | 19/19 |
| Strategy Engine | 100% | 2,150 | 29/29 |
| Learning Engine | 100% | 1,500 | 14/14 |

**완성률**: 89%

### 5.2 테스트

```
전체: 370/375 (98.7%)
- 통과: 370
- 실패: 5 (Google API IP 제한)
- Skip: 3
```

---

## 6. 실무 활용

### 6.1 시장 분석

```bash
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR
```

### 6.2 기회 발굴

```bash
cmis opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  --budget 1000000000 \
  --top-n 5
```

### 6.3 전략 생성 (Brownfield)

```bash
cmis workflow run strategy_design \
  --input domain_id=Adult_Language_Education_KR \
  --input goal_id=GOAL-growth \
  --input project_context_id=PRJ-my-company
```

---

## 7. 설계 철학

### 7.1 핵심 원칙

1. **Model-first, Number-second**
2. **Evidence-first, Prior-last**
3. **Graph-of-Graphs** (R/P/V/D)
4. **Trait 기반** (Ontology lock-in 최소화)
5. **모든 답 = 세계·변화·결과·논증**
6. **Monotonic Improvability**

### 7.2 구현 원칙

1. **API 레벨 분리** (Public / Orchestration / Core)
2. **cmis.yaml 정렬** (스펙 기반)
3. **Lineage 추적** (완전한 출처)
4. **안전장치** (sample_size, outlier, rollback)

---

**작성**: 2025-12-11
**버전**: CMIS v3.3
**상태**: Production Ready ✅

**CMIS Architecture Blueprint v3.3**
