---
**이력**: 2025-12-09 UMIS v9 → CMIS로 브랜드 변경
- Universal Market Intelligence → Contextual Market Intelligence
- v9 핵심 차별점 (Project Context Layer) 반영
---

# UMIS v9 – `structure_analysis` 프로덕션 v1 작업리스트 (Vertical Slice)

> 목표:  
> 한 도메인(예: `Adult_Language_Education_KR`)에 대해  
> `structure_analysis` 워크플로를 **작은 vertical slice**로 프로덕션 수준까지 구현한다.  
> (의존성 최소, 클린 코드, 오버엔지니어링 회피)

---

## 0. Scope & 성공 기준 정의

### 0-1. v1 Scope 확정

입력
- 필수
  - `domain_id` (예: `Adult_Language_Education_KR`)
  - `region` (예: `KR`)
- 선택
  - `segment` (없으면 전체)

처리
- World Engine
  - `world_engine.snapshot(domain_id, region, segment, as_of=None)` 호출
  - Reality seed 기반 R-Graph 스냅샷 생성
- Pattern Engine
  - `pattern_engine.match_patterns(snapshot.graph)` 호출 (간단 rule 기반)
- Value Engine
  - `value_engine.evaluate_metrics(snapshot.graph, metric_requests)` 호출
  - metric_requests는 `metric_sets.structure_core_economics` 중 일부 서브셋(e.g. N_customers, Revenue, Avg_price_per_unit)

출력
- 구조화된 결과 객체 `StructureAnalysisResult`
  - R-Graph 요약 (Actor/MoneyFlow/State)
  - 매칭된 패턴 목록 (간단 ID + 설명)
  - 핵심 Metric 값들
- (선택) 간단한 Markdown 리포트 1개
  - `Market_Structure_Snapshot_{domain_id}_{date}.md`

### 0-2. 성공 기준

- CLI에서 한 번으로 end-to-end 실행 가능:
  - `umis structure-analysis --domain Adult_Language_Education_KR --region KR`
- 코드 구조가 `umis_v9.yaml`의 스키마와 자연스럽게 align
- 새로운 도메인 추가 시
  - seed 파일 + 최소 설정만으로 동일 파이프라인 재사용 가능
- 외부 API/EvidenceEngine 없이도 (seed만으로) 의미 있는 결과 산출
- 유닛 테스트 + 최소 1개의 통합 테스트(E2E) 통과

---

## 1. 프로젝트 구조 / 공통 타입 정리

### 1-1. 모듈 구조

권장 디렉토리 구조(예시)

- `umis_v9_core/`
  - `config.py` (YAML 로더, 설정 로딩)
  - `graph.py` (InMemoryGraph 및 공통 Graph 인터페이스)
  - `world_engine.py` (WorldEngine v1)
  - `pattern_engine.py` (PatternEngine v1)
  - `value_engine.py` (ValueEngine v1)
  - `workflow_structure_analysis.py` (structure_analysis orchestrator)
  - `types.py` (공통 데이터 타입)
- `umis_v9_cli/`
  - `__main__.py` (CLI entrypoint: `umis`)
- `tests/`
  - `test_graph.py`
  - `test_world_engine.py`
  - `test_value_engine.py`
  - `test_pattern_engine.py`
  - `test_structure_analysis_workflow.py`

의존성
- 필수 라이브러리 최소화
  - `pyyaml` + 표준 라이브러리 정도 (파일 I/O, logging, dataclasses)
- v1에서는 DB, 메시지 큐, DI 프레임워크 등 도입 금지

### 1-2. 공통 Domain 타입 정의

`umis_v9_core/types.py` (또는 각 모듈 내에서 재사용)

- `Node`
  - `id: str`
  - `type: str`
  - `data: dict`
- `Edge`
  - `type: str`
  - `source: str`
  - `target: str`
  - `data: dict`
- `MetricRequest`
  - `metric_id: str`
  - `context: dict`
- `ValueRecord`
  - `metric_id: str`
  - `context: dict`
  - `point_estimate: Optional[float]`
  - `quality: dict`
  - `lineage: dict`
- `StructureAnalysisInput`
  - `domain_id: str`
  - `region: str`
  - `segment: Optional[str]`
- `StructureAnalysisResult`
  - `meta: dict`
  - `graph_overview: dict`
  - `pattern_matches: list`
  - `metrics: list[ValueRecord]`

설계 원칙
- dataclass 기반으로 단순/명확하게
- persistence/DB 교체가 필요해도 interface 변경 최소화될 정도로만 추상화

---

## 2. 그래프 레이어 v1 – InMemoryGraph + R-Graph 매핑

### 2-1. InMemoryGraph 구현

`umis_v9_core/graph.py`

기능
- 인메모리 기반의 최소 그래프 기능 구현
- 노드/엣지 타입과 데이터는 그대로 dict로 보관

인터페이스
- `upsert_node(node_id, node_type, data)`
  - 존재하면 data 업데이트, 없으면 새로 추가
- `add_edge(edge_type, source_id, target_id, data)`
- `get_node(node_id) -> Node | None`
- `nodes_by_type(node_type) -> List[Node]`
- `neighbors(node_id, edge_type=None, direction="out") -> List[Node]`

테스트
- `test_graph.py`
  - 노드 추가/업데이트/조회 테스트
  - 엣지 추가 후 neighbors 조회 테스트

### 2-2. R-Graph 타입 매핑 레이어

R-Graph Primitive (from `umis_v9.yaml`)

- actor
- event
- resource
- money_flow
- contract
- state

매핑 전략
- node_type 문자열은 YAML 스키마와 동일 사용
  - 예: `"actor"`, `"money_flow"`
- `data` 필드 안에 `ontology.primitives` 규격대로 dict 저장
- 별도 dataclass 정의 예:
  - `ActorNode`, `MoneyFlowNode`, `StateNode`
  - 하지만 v1에서는 굳이 클래스를 나누지 않고 type 필드만으로 처리해도 OK

테스트
- seed YAML → Graph 변환 → 다시 YAML 직렬화했을 때 의미 손실 없는지 확인

---

## 3. World Engine v1 – snapshot(domain_id, region, segment, as_of)

### 3-1. Reality Seed Loader

파일 위치/규칙
- `seeds/{domain_id}_reality_seed.yaml`
  - 예: `seeds/Adult_Language_Education_KR_reality_seed.yaml`

내용 예시
- `actors:`
- `money_flows:`
- `states:`

구현
- `load_reality_seed(domain_id) -> dict`
  - 파일 없음 → 명시적 예외 (v1에서 EvidenceEngine 호출 안 함)
- seed dict → `InMemoryGraph`로 변환
  - 각 섹션을 Node/Edge로 옮기기

### 3-2. snapshot 함수

시그니처
- `snapshot(domain_id: str, region: str, segment: Optional[str], as_of: Optional[date]) -> RealityGraphSnapshot`

`RealityGraphSnapshot`
- `graph: InMemoryGraph`
- `meta: {"domain_id": ..., "region": ..., "segment": ..., "as_of": ...}`

동작
- seed 기반 R-Graph 구성
- v1에서 `segment`, `as_of`는 filtering 안 하고 meta에만 기록
  - 복잡한 time-slicing / segment-filter는 후속 버전에서

테스트
- `test_world_engine.py`
  - `snapshot("Adult_Language_Education_KR", "KR", None, None)`
  - 노드/엣지 개수가 seed와 일치하는지 확인

### 3-3. Logging/에러 처리

- seed 로딩 시작/종료 로그
- 주요 통계 (actor 수, money_flow 수 등)
- seed 미존재 일 경우:
  - `ValueError` 또는 커스텀 예외
  - "No reality seed for domain_id=..." 메시지 포함

---

## 4. Value Engine v1 – 핵심 Metric 서브셋

### 4-1. Metrics Spec 로더

`umis_v9_core/config.py` 또는 `value_engine.py` 내부

- `umis_v9.yaml`에서 다음 정보 로딩
  - `value_engine.metrics_spec.metrics` (전체 목록)
  - `value_engine.metrics_spec.metric_sets.structure_core_economics`
- v1에서는 실제 구현할 Metric만 상수로 정해도 OK
  - 예: `SUPPORTED_METRICS = {"MET-N_customers", "MET-Revenue", "MET-Avg_price_per_unit"}`

테스트
- `test_value_engine.py`
  - YAML 로딩 후 `SUPPORTED_METRICS`가 실제 metrics_spec에 존재하는지 확인

### 4-2. Metric Resolver v1 (Direct + 단순 Derived)

v1 범위
- EvidenceEngine 호출, Prior/Fusion/Validation은 제외 (stub)
- seed 기반 R-Graph에서 직접 계산 가능한 Metric만 처리

구현 대상 Metric (예시)

1. `MET-N_customers`
   - 손쉬운 근사: R-Graph `actor` 중 `kind == "customer_segment"`인 노드들의  
     `data["metadata"]["approx_population"]` 합산
2. `MET-Revenue`
   - `money_flow` 노드의 `quantity.amount` 합산
   - 방향: `customer_segment → provider` 타입의 MoneyFlow만 필터링
3. `MET-Avg_price_per_unit`
   - `Revenue / N_customers`
   - N_customers == 0이면 `None` 처리 + quality에 status 기록

API
- `evaluate_metrics(graph: InMemoryGraph, metric_requests: List[MetricRequest], policy_ref: str) -> Tuple[List[ValueRecord], dict]`

Quality/Lineage
- v1 기본값
  - `quality = {"status": "ok", "literal_ratio": 1.0, "spread_ratio": 0.0}`
  - `lineage = {"from_evidence_ids": [], "engine_ids": ["value_engine"], "policy_id": policy_ref, "created_by_role": None, "created_at": now}`

테스트
- `test_value_engine.py`
  - 작은 R-Graph fixture로 Revenue/N_customers/Avg_price_per_unit 계산 검증

---

## 5. Pattern Engine v1 – 최소 Rule 기반 매칭

### 5-1. 패턴 정의 방법 (v1)

v1에서는 PatternGraph/YAML 전체를 도입하지 않고, 코드에 간단 rule로 정의

예시 패턴
- `PAT-subscription_model`
  - `money_flow.traits.revenue_model == "subscription"` 존재 여부
- `PAT-platform_business_model`
  - `actor.traits.institution_type == "online_platform"` 존재 여부

출력 구조
- `PatternMatch`
  - `pattern_id: str`
  - `structure_fit_score: float` (0~1, v1에서는 1.0 또는 0.0)
  - `evidence_node_ids: List[str]`

### 5-2. match_patterns 구현

- `match_patterns(graph: InMemoryGraph) -> List[PatternMatch]`
  - 모든 `money_flow` 노드 스캔
    - `revenue_model == "subscription"`이 하나라도 있으면 `PAT-subscription_model` 매칭
  - 모든 `actor` 노드 스캔
    - `institution_type == "online_platform"`이 있으면 `PAT-platform_business_model` 매칭

테스트
- `test_pattern_engine.py`
  - Fixture 그래프에서 패턴 존재/부재 케이스 각각 테스트

---

## 6. 구조 분석 워크플로 오케스트레이터

### 6-1. run_structure_analysis 진입점

`umis_v9_core/workflow_structure_analysis.py`

함수 시그니처
- `run_structure_analysis(input: StructureAnalysisInput) -> StructureAnalysisResult`

내부 단계
1. WorldEngine
   - `snapshot = world_engine.snapshot(domain_id, region, segment, as_of=None)`
2. PatternEngine
   - `pattern_matches = pattern_engine.match_patterns(snapshot.graph)`
3. ValueEngine
   - `metric_requests` 구성 (예: N_customers, Revenue, Avg_price_per_unit)
   - `value_records, program_trace = value_engine.evaluate_metrics(snapshot.graph, metric_requests, policy_ref="reporting_strict")`
4. 결과 합치기
   - R-Graph 요약: Actor 수, MoneyFlow 수, 주요 Actor 이름 등
   - Pattern 목록: pattern_id/설명
   - Metrics: ValueRecord 전체
   - `StructureAnalysisResult`에 담아 반환

### 6-2. StructureAnalysisResult 스키마

- `meta`
  - `{"domain_id": ..., "region": ..., "segment": ..., "as_of": ...}`
- `graph_overview`
  - `{"num_actors": ..., "num_money_flows": ..., "actor_types": ...}`
- `pattern_matches`
  - `List[{"pattern_id": ..., "structure_fit_score": ..., "evidence_node_ids": [...]}]`
- `metrics`
  - `List[ValueRecord]`

테스트
- `test_structure_analysis_workflow.py`
  - POC seed로 실행 후:
    - actor 수/flow 수가 0이 아닌지
    - metrics 리스트에 N_customers/Revenue/Avg_price_per_unit가 포함되어 있는지
    - pattern_matches가 리스트 형태로 온전한지

---

## 7. CLI / 간단 Report 출력

### 7-1. CLI 명령

`umis_v9_cli/__main__.py`

- 명령 예:
  - `umis structure-analysis --domain Adult_Language_Education_KR --region KR --segment adult_language_general`
- 동작
  - 인자 파싱 → StructureAnalysisInput 생성
  - `run_structure_analysis` 호출
  - 결과를 콘솔에 요약 출력:
    - Actor/MoneyFlow 개수
    - 주요 패턴 리스트
    - Metric 값 테이블

### 7-2. Markdown Report v1 (옵션)

간단 템플릿 예 (문자열 포매팅)

- 제목: `# Market Structure Snapshot – {domain_id} ({region})`
- 섹션
  - "1. Overview" – actor/money_flow 요약
  - "2. Patterns" – pattern_matches 요약
  - "3. Core Metrics" – N_customers / Revenue / Avg_price_per_unit 표

렌더 함수
- `render_structure_report(result: StructureAnalysisResult) -> str`
- v1에서는 narrative 최소, 표/리스트 위주

---

## 8. 테스트 전략

### 8-1. 유닛 테스트

- `test_graph.py`
  - Node/Edge 추가/조회
- `test_world_engine.py`
  - seed 로드 → snapshot → 노드/엣지 개수 검증
- `test_value_engine.py`
  - 인공 그래프에서 Metric 계산 검증
- `test_pattern_engine.py`
  - 패턴 매칭 규칙 검증

### 8-2. 통합 테스트 (E2E)

- `test_structure_analysis_workflow.py`
  - 입력: Adult_Language_Education_KR + KR
  - 실행: `run_structure_analysis(...)`
  - 검증:
    - `result.graph_overview["num_actors"] > 0`
    - `MET-N_customers`, `MET-Revenue`에 해당하는 ValueRecord 존재
    - pattern_matches 길이가 0 이상

---

## 9. 오버 엔지니어링 방지 가이드

### 9-1. 의존성/플랫폼

- v1에서 하지 말 것
  - Graph DB 연동 (Neo4j 등)
  - ORMs, MQ, 복잡한 설정/플러그인 시스템
  - Workflow 엔진/DSL (Airflow, Temporal 등)
- v1에서 해도 되는 것
  - YAML 파싱
  - 간단한 dataclass & 함수형 설계
  - CLI 옵션 파싱 (argparse 정도)

### 9-2. 스펙 vs 구현

- `umis_v9.yaml`은 완전하지만, v1 구현은 그 중 일부만 사용
- 사용하지 않는 필드는 굳이 코드에서 다루지 않기
- EvidenceEngine/StrategyEngine/LearningEngine은 stub 또는 미사용

### 9-3. NotImplemented 패턴

- 아직 범위 밖인 기능은 억지로 우회해서 만들지 말고,
  - 명시적으로 `NotImplementedError` 혹은 quality.status="not_implemented"를 설정
- 이로써 설계와 구현의 gap이 어디인지 분명하게 유지

---

## 10. 다음 단계용 메모 (v1 이후)

v1이 안정화되면 다음 Vertical Slice로 확장:

- EvidenceEngine v0
  - 외부 데이터 소스 1개(KOSIS 혹은 DART)만 실제 연동해 seed를 보강
- PatternEngine 고도화
  - PatternGraph/YAML 도입, value_chain_templates, strategic_frameworks와 연동
- 구조 분석 보고서 자동 생성 고도화
  - 14 Phase 중 일부를 직접 자동화
  - MemoryStore/ArtifactStore와 연결
- Project Context 통합 (`project_context_store`)
  - Brownfield/Greenfield 차이를 반영하는 `structure_analysis_for_project` 확장

---