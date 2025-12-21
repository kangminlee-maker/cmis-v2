# CMIS Core Types 및 스키마

**생성일**: 2025-12-21 10:20:00
**목적**: CMIS 시스템의 모든 데이터 타입 및 스키마 정의

---

## 1. Core Types (types.py)

**파일**: `cmis_core/types.py`

```
CMIS Core Types

Common dataclasses used across all v9 modules.
Based on umis_v9.yaml ontology and graph schemas.
```

### 1.1 주요 데이터 클래스

#### `Node`

**설명**: Graph node (Actor/Event/Resource/MoneyFlow/Contract/State)

#### `Edge`

**설명**: Graph edge (actor_pays_actor, event_triggers_money_flow, etc.)

#### `MetricRequest`

**설명**: Metric 평가 요청

#### `ValueRecord`

**설명**: Metric 계산 결과 (V-Graph의 value_record 노드)

#### `PatternSpec`

**설명**: Pattern 정의 (v1.1 - 13개 필드)

Pattern은 Trait 조합 + Graph 구조로 정의됩니다.
Ontology lock-in 최소화를 위해 고정 타입이 아닌 Trait 기반 정의.

#### `PatternMatch`

**설명**: 패턴 매칭 결과 (v1.1 - 8개 필드)

#### `GapCandidate`

**설명**: 기회/갭 후보

#### `FocalActorContext`

**설명**: Focal Actor Context (확장 버전 - Phase A + Learning).

의도:
- 기존 명칭(ProjectContext)은 ProjectLedger/Workflow task 등 "실행 단위" 개념과 혼동될 여지가 큽니다.
- 본 객체는 "프로젝트 실행 계획"이 아니라, Brownfield에서 focal actor(우리/클라이언트)의
  자산/제약/선호/기준상태를 포함하는 '컨텍스트 레코드(PRJ-*)'입니다.

NOTE:
- cmis.yaml의 store key는 `focal_actor_context_store`이며,
  구현체는 `FocalActorContextStore`(cmis_core/stores/focal_actor_context_store.py)입니다.

#### `ContextArchetype`

**설명**: Context Archetype (간소화 버전)

특정 시장/산업의 전형적인 특징과 Expected Pattern Set

#### `SearchContext`

**설명**: 검색 Context (통합 모델)

검색 전략 수립에 필요한 모든 정보

#### `SearchStep`

**설명**: 검색 단계

#### `SearchPlan`

**설명**: 검색 계획

#### `QueryResultQuality`

**설명**: 쿼리 결과 품질 평가

#### `StructureAnalysisInput`

**설명**: structure_analysis 워크플로우 입력

#### `StructureAnalysisResult`

**설명**: structure_analysis 워크플로우 출력

**주요 메서드**:

- `def to_dict(self) -> Dict[(str, Any)]`
  - JSON 직렬화용

#### `RealityGraphSnapshot`

**설명**: World Engine snapshot 결과 (R-Graph 서브그래프)

#### `SourceTier`

**설명**: Evidence source tier 정의

Tier 우선순위 (상위 tier일수록 신뢰도 높음):
1. official: 공식 통계/공시 (DART, KOSIS, Gov Stats)
2. curated_internal: 내부 검증 데이터
3. commercial: web_search 기반 공개 자료 (컨설팅/증권사 리포트 등 포함 가능)

주의: structured_estimation, llm_baseline은 ValueEngine.prior_estimation에서 처리

**상속**: `Enum`

#### `EvidenceValueKind`

**설명**: Evidence 값 타입

**상속**: `Enum`

#### `EvidenceSufficiency`

**설명**: Evidence 충분성 상태

**상속**: `Enum`

#### `EvidenceRequest`

**설명**: Evidence 수집 요청

MetricRequest에서 변환되거나 Reality Graph용으로 직접 생성

#### `EvidenceRecord`

**설명**: 개별 Evidence 레코드

하나의 source에서 수집된 하나의 evidence

#### `EvidenceBundle`

**설명**: 여러 source의 Evidence 묶음

EvidenceEngine.fetch_for_metrics()의 기본 반환 단위
(하나의 EvidenceRequest에 대응)

**주요 메서드**:

- `def add_evidence(self, record: EvidenceRecord)`
  - Evidence 추가
- `def add_trace(self, tier: int, source_id: str, status: str)`
  - Trace 추가
- `def get_best_record(self) -> Optional[EvidenceRecord]`
  - 가장 신뢰도 높은 record 반환
- `def get_records_by_tier(self, tier: str) -> List[EvidenceRecord]`
  - Tier별 record 필터링
- `def calculate_quality_summary(self)`
  - 품질 지표 계산

#### `EvidenceMultiResult`

**설명**: 여러 Metric의 Evidence 묶음

ValueEngine이 요청한 여러 MetricRequest에 대한
Metric별 EvidenceBundle 컬렉션

**주요 메서드**:

- `def get_bundle(self, metric_id: str) -> Optional[EvidenceBundle]`
  - Metric별 bundle 조회
- `def get_overall_quality(self) -> Dict[(str, Any)]`
  - 전체 품질 지표 집계
- `def get_evidence_bundle_summary(self) -> Dict[(str, Any)]`
  - PolicyEngine v2용 EvidenceBundleSummary 생성

#### `EvidenceSufficiencyResult`

**설명**: Evidence 충분성 판단 결과

**주요 메서드**:

- `def is_usable(self) -> bool`
  - 사용 가능 여부 (SUFFICIENT or PARTIAL)

#### `EvidencePolicy`

**설명**: Evidence 품질 정책 (cmis.yaml에서 로드)

cmis.yaml의 policies.quality_profiles와 1:1 매핑

**주요 메서드**:

- `def from_config(cls, policy_id: str, config: Any) -> EvidencePolicy`
  - cmis.yaml에서 policy 로드

#### `Goal`

**설명**: 목표 정의 (D-Graph goal 노드)

cmis.yaml decision_graph.goal 스키마 기반

#### `Strategy`

**설명**: 전략 정의 (D-Graph strategy 노드)

#### `PortfolioEvaluation`

**설명**: Portfolio 평가 결과

#### `Outcome`

**설명**: 실제 실행 결과 (outcome_store)

Strategy/Scenario 실행 후 실제 측정된 결과

#### `LearningResult`

**설명**: 학습 결과

---

## 2. 스키마 정의 (schemas/)

### 2.6 decision_graph.yaml

**경로**: `schemas/decision_graph.yaml`

**구조**:

```yaml
schema_version: 1
description: Decision Graph (D-Graph) schema. Placeholder v1.
graph:
  id: ...
  name: ...
  ontology_ref: ...
  node_types: ...
  edge_types: ...
```

### 2.2 ledgers.yaml

**경로**: `schemas/ledgers.yaml`

**구조**:

```yaml
ledgers:
  project_ledger: ...
  progress_ledger: ...
```

### 2.1 ontology.yaml

**경로**: `schemas/ontology.yaml`

**구조**:

```yaml
schema_version: 1
description: CMIS ontology schema (traits/capabilities/node types). Placeholder v1.
ontology:
  node_types: ...
  capability_taxonomy: ...
  trait_keys: ...
```

### 2.4 pattern_graph.yaml

**경로**: `schemas/pattern_graph.yaml`

**구조**:

```yaml
schema_version: 1
description: Pattern Graph (P-Graph) schema. Placeholder v1.
graph:
  id: ...
  name: ...
  ontology_ref: ...
  node_types: ...
  edge_types: ...
  # ... (1개 더)
```

### 2.5 reality_graph.yaml

**경로**: `schemas/reality_graph.yaml`

**구조**:

```yaml
schema_version: 1
description: Reality Graph (R-Graph) schema. Placeholder v1.
graph:
  id: ...
  name: ...
  ontology_ref: ...
  node_types: ...
  edge_types: ...
```

### 2.3 value_graph.yaml

**경로**: `schemas/value_graph.yaml`

**구조**:

```yaml
schema_version: 1
description: Value Graph (V-Graph) schema. Placeholder v1.
graph:
  id: ...
  name: ...
  ontology_ref: ...
  node_types: ...
  edge_types: ...
  # ... (1개 더)
```

---

이 문서는 CMIS의 모든 타입 정의를 포함합니다.
