# CMIS CLI 명령어 레퍼런스

**생성일**: 2025-12-21 10:20:00
**목적**: 모든 CLI 명령어 사용법

---

## batch_analysis

### 모듈 설명

```
batch-analysis 명령어

여러 도메인/시장 일괄 분석 (병렬 처리)

2025-12-11: Workflow CLI Phase 2
```

---

## brownfield

### 모듈 설명

```
brownfield 관련 명령어 (BF-13).

MVP:
- `cmis brownfield import <file>`
- `cmis brownfield preview IMP-...`
- `cmis brownfield validate IMP-... --policy-mode ...`
- `cmis brownfield commit IMP-... --policy-mode ... [--focal-actor-context-base-id PRJ-...]`

주의(누출 방지):
- preview/validation 출력은 원문 행/대량 수치를 포함하지 않는 요약(ART)만 다룹니다.
```

---

## cache_manage

### 모듈 설명

```
cache-manage 명령어

Evidence/Result 캐시 관리

2025-12-11: Workflow CLI Phase 2
```

---

## compare_contexts

### 모듈 설명

```
compare-contexts 명령어

여러 분석 컨텍스트 비교 (Greenfield vs Brownfield, 시점 비교 등)

2025-12-11: Workflow CLI Phase 1
```

---

## config_validate

### 모듈 설명

```
config-validate 명령어

YAML 설정 검증 (Cross-reference 포함)

2025-12-11: Workflow CLI Phase 2
```

---

## context

### 모듈 설명

```
context 관련 명령어.

MVP:
- `cmis context verify PRJ-...-vN`
```

---

## cursor

### 모듈 설명

```
Cursor Agent Interface commands (cmis cursor ...).

Cursor IDE 안에서 Agent가 호출하기 좋은 '프로토콜(커맨드)'을 제공합니다.
정본은 CMIS stores(SQLite)에 저장되고, Cursor UX는 `.cmis/runs/<run_id>/` export(view)를 열람합니다.
```

---

## db_manage

### 모듈 설명

```
db-manage 명령어

런타임 스토리지(`.cmis/`)의 마이그레이션/리셋을 수행합니다.

- migrate: legacy key(project_context_id 등) -> focal_actor_context_id 계열로 변환
  - 대상(존재하는 경우):
    - `.cmis/db/*.db` (runs/ledgers/contexts/outcomes/artifacts 등)
    - `.cmis/evidence_cache.db` (legacy EvidenceStore sqlite backend)
    - `.cmis/value_store/*.json` (PriorManager)
- reset: `.cmis` 런타임 스토어를 백업 후 초기화
  - 기본 포함: `.cmis/db`, `.cmis/runs`, `.cmis/artifacts`, `.cmis/value_store`, `.cmis/cache`, `.cmis/evidence_cache.db`
```

---

## eval_run

### 모듈 설명

```
Eval Harness CLI command.
```

---

## opportunity_discovery

### 모듈 설명

```
opportunity-discovery 명령어

기회 발굴 및 Gap 분석

2025-12-11: Workflow CLI Phase 1
```

---

## report_generate

### 모듈 설명

```
report-generate 명령어

분석 결과를 보고서로 변환 (Lineage 포함)

2025-12-11: Workflow CLI Phase 2
```

---

## run

### 모듈 설명

```
Run inspection commands (cmis run ...).

Phase 1에서는 Cursor UX를 위해 '열람/설명' 위주로 제공하고,
streaming/follow/replay/approve는 Phase 2+에서 확장합니다.
```

---

## structure_analysis

### 모듈 설명

```
structure-analysis 명령어

시장 구조 분석

2025-12-11: Workflow CLI Phase 1
```

---

## workflow_run

### 모듈 설명

```
Generic workflow run 명령어

canonical_workflows 직접 실행

2025-12-11: Workflow CLI Phase 1
```

---
