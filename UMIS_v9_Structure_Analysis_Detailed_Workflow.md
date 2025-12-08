# UMIS v9: Structure Analysis 워크플로우 상세 작동 과정

**문서 목적**: v7.x Market Reality Report와 동일한 결과물을 v9에서 생성하는 워크플로우의 엔진/그래프 레벨 상세 작동 설명

**참조**:
- v7.x 결과물: `reference/output/market_reality_report_v7.x/Market_Reality_Report_Final.md`
- v9 워크플로우 정의: `umis_v9_process_phases.yaml`
- v9 협업 프로토콜: `umis_v9_agent_protocols.yaml`
- v9 검증 게이트: `umis_v9_validation_gates.yaml`

**워크플로우 종류**:
- **structure_analysis** (Greenfield): 시장 전체 분석, 14 Phases (PH01-PH14)
- **structure_analysis_for_project** (Brownfield): 시장 + 조직 통합 분석, 15 Phases (**PH00** + PH01-PH14)

---

## 전체 워크플로우 아키텍처

### 입력

**사용자 질문 (Interaction Plane)**:
```
"한국 성인 어학교육 시장 구조를 알고 싶어.
Top-N 플레이어 구조 + 돈의 흐름에 따른 전후방 가치사슬도 함께 확인해줘.
진입 전략 후보 2-3개도 확인해보자."
```

### 출력

**Market Reality Report (최종 산출물)**:
- Executive Summary (핵심 수치, BM별 구조, Top 10 플레이어)
- 시장 정의 및 범위 (Needs 분류, 포함/제외 기준)
- 시장 규모 분석 (전체/BM별/도메인별, 4-Method Convergence)
- 주요 플레이어 분석 (Top-N별 매출/강점/약점)
- 가치사슬 구조 (BM별 돈의 흐름, 마진 구조)
- 경쟁구조 분석 (CR3, HHI, 진입장벽, 교섭력)
- 시장 트렌드 및 전망
- 데이터 추적성 (SRC-/EST-/ASM- Registry)
- 검증 결과 (MECE, 4-Method, 3자 검증)
- 결론 및 전략적 시사점

### 핵심 실행 흐름

```
[사용자 질문]
    ↓
[Interaction Plane] → CLI/Notebook에서 structure_analysis 워크플로우 호출
    ↓
[Role Plane] → Structure Analyst가 14-Phase 워크플로우 실행 주도
    ↓                (필요시 Numerical Modeler, Reality Monitor와 협업)
[Cognition Plane] → World/Pattern/Value/Policy Engine 순차 실행
    ↓
[Substrate Plane] → R-Graph 구축 → P-Graph 매칭 → V-Graph 계산
    ↓                → Evidence/Value Store 업데이트
[Final Output] → Market Reality Report.md
```

---

## Phase 1: 시장 정의 및 경계 설정

### 목표
Needs 중심 시장 정의, 포함/제외 범위 명확화, MECE 가능 구조 수립

### v9 실행 흐름

#### 1.1 Role Plane: Structure Analyst 시작

**입력**:
- 사용자 질문: "한국 성인 어학교육 시장..."

**Structure Analyst가 하는 일**:
1. 질문을 파싱해 `domain_id`, `region`, `segment` 추출
   - domain_id: "Adult_Language_Education_KR"
   - region: "KR"
   - segment: "adult_language_general"

2. `umis_v9_process_phases.yaml#PH01_market_definition` Phase 시작
3. Needs 분류 템플릿 로드 (A-D 카테고리)

#### 1.2 Cognition Plane: World Engine - Reality Snapshot 준비

**World Engine 호출**:
```python
snapshot = world_engine.snapshot(
    domain_id="Adult_Language_Education_KR",
    region="KR",
    segment="adult_language_general",
    as_of="2025-12-05"
)
```

**World Engine 내부 동작**:

1. **domain_registry.yaml 확인**
   - `Adult_Language_Education_KR` 도메인이 등록되어 있는지 확인
   - 해당 도메인 설정 파일: `umis_v9_domain_AdultLanguage_KR.yaml`

2. **Reality seed 확인**
   - `seeds/Adult_Language_Education_KR_reality_seed.yaml` 존재 여부 확인
   - 이미 존재하면 → 로딩
   - 없으면 → Evidence Engine 호출 (Phase 5에서 상세)

3. **R-Graph 초기 구성**
   - seed에서 Actor/MoneyFlow/State 노드 생성
   - 하지만 Phase 1에서는 아직 **빈 템플릿 수준**만 사용

#### 1.3 Substrate Plane: Needs 분류 Artifact 생성

**Artifact 생성 (ART-needs_classification)**:

Structure Analyst가 다음을 수행:

1. **Needs 템플릿 적용**
   - A. 경제활동 (Professional): 50-60%
   - B. 생활/문화 (Personal): 30-40%
   - C. 자기계발: 5-10%
   - D. 조직: 10-15%

2. **포함/제외 기준 정의**
   ```yaml
   market_boundary:
     included:
       - transaction_subjects: ["B2C", "B2B", "B2G"]
       - age_range: "19세 이상"
       - languages: "모든 외국어"
       - formats: ["온라인", "오프라인", "하이브리드", "독학"]
     excluded:
       - "초중고 사교육"
       - "외국인 대상 한국어 교육"
       - "해외 어학연수 현지 수강료"
       - "대학 정규 학비 내 어학 수업"
   ```

3. **Memory Store 기록**
   ```yaml
   memory_id: "MEM-needs_classification_20251205"
   memory_type: "query_trace"
   content:
     needs_categories: ["A_professional", "B_personal", "C_development", "D_organizational"]
     market_scope: "Adult Language Education KR"
   ```

#### 1.4 Validation: MECE 자체 검증

**Policy Engine - mece_validation gate 적용**:
- umis_v9_validation_gates.yaml#mece_validation 규칙 로드
- Needs 분류가 ME(상호 배타적) 인지 확인
- CE(전체 포괄적) 인지 확인 (합계 100%)

**검증 결과**:
- ✅ ME: 각 Needs가 하나의 카테고리에만 속함
- ✅ CE: A+B+C+D = 100%
- **Status**: PASS → Phase 2로 진행

---

## Phase 2: 도메인 MECE 분류

### 목표
언어별(영어, 중국어, 일본어 등) 도메인 분류 및 점유율 추정

### v9 실행 흐름

#### 2.1 Pattern Engine: 도메인 Trait 추출

**Pattern Engine 호출**:
```python
domain_traits = pattern_engine.extract_domain_traits(
    graph_slice_ref=snapshot.graph,
    domain_axis="language"
)
```

**Pattern Engine 내부 동작**:

1. **Pattern Graph에서 domain archetype 탐색**
   - `umis_v9_strategic_frameworks.yaml`에서 언어 도메인 분류 템플릿 로드
   - Context Archetype 노드: "Adult_Language_KR_English", "Adult_Language_KR_Chinese" 등

2. **R-Graph State 노드에서 힌트 추출**
   - Reality seed의 State 노드 확인:
   ```yaml
   state_id: "STA-market_language_distribution"
   properties:
     english_share: 0.75
     chinese_share: 0.125
     japanese_share: 0.075
     others_share: 0.05
   ```

3. **도메인별 Actor 매핑**
   - R-Graph의 Actor 노드들을 언어별로 그룹핑
   - Actor traits에서 `primary_language` 필드 확인

#### 2.2 Artifact 생성: 15개 언어 도메인

**Structure Analyst가 산출물 작성**:

```yaml
artifact_id: "ART-domain_classification"
format: "structured_yaml"
domains:
  tier_1:
    - language: "영어"
      market_share: 0.75
      estimated_market_size: "7,500억원"  # Phase 7에서 확정
      reasoning: "압도적 수요, 모든 BM 중심"
    - language: "중국어"
      market_share: 0.125
      estimated_market_size: "1,250억원"
      reasoning: "對중 비즈니스, HSK"
    - language: "일본어"
      market_share: 0.075
      estimated_market_size: "750억원"
      reasoning: "문화, JLPT"
  tier_2:
    - language: "스페인어"
      market_share: 0.015
    # ... (나머지 언어)
```

#### 2.3 Validation: MECE + 합계 100% 검증

**Policy Engine 검증**:
- 합계: 75% + 12.5% + 7.5% + ... = 100%
- ✅ PASS

---

## Phase 3-4: BM 분류 프레임워크 및 전수조사

### 목표
23개 비즈니스 모델 MECE 분류 및 상세 정의

### v9 실행 흐름

#### 3.1 Pattern Engine: BM 분류 축 정의

**Pattern Engine - BM Framework 로드**:

1. **umis_v9_strategic_frameworks.yaml 참조**
   - Porter 5 Forces, Blue Ocean Canvas 등 전략 프레임워크에서 BM 분류 힌트

2. **3-Axis Framework 구성**:
   ```yaml
   bm_classification_axes:
     delivery:
       - "offline"
       - "online"
       - "hybrid"
     interaction:
       - "1_to_1"
       - "1_to_many"
       - "self_learning"
       - "platform"
     transaction:
       - "B2C"
       - "B2B"
       - "B2G"
   ```

3. **23개 BM 매트릭스 생성**
   - 각 축 조합으로 가능한 BM 나열
   - Edge case 검토 (온라인 스터디, 교환 학습 제외 등)

#### 3.2 Pattern Graph: BM Pattern 노드 생성

**Substrate Plane - Pattern Graph 업데이트**:

각 BM에 대해 Pattern 노드 생성:

```yaml
# 예시: 오프라인 종합 학원
pattern_id: "PAT-offline_academy_comprehensive"
name: "오프라인 종합 학원 BM"
pattern_family_id: "offline_education"
constraints:
  required_traits:
    delivery_channel: "offline"
    interaction_type: "1_to_many"
    revenue_model: "subscription"
    requires_physical_presence: true
  typical_characteristics:
    - "선불 수강권 구조"
    - "강사 인건비 비중 높음 (40-50%)"
    - "주요 상권 임대료 부담 (20-30%)"
```

**총 23개 Pattern 노드** 생성되어 Pattern Graph에 추가됨

#### 3.3 Artifact 생성: BM 완전 목록

```yaml
artifact_id: "ART-bm_complete_list"
total_bm_count: 23
bm_groups:
  - group_id: "offline_academy"
    group_name: "오프라인 학원형"
    bm_list:
      - bm_id: "BM-01"
        name: "종합 학원"
        pattern_ref: "PAT-offline_academy_comprehensive"
      - bm_id: "BM-02"
        name: "전문 학원 (시험)"
        pattern_ref: "PAT-offline_academy_specialized"
      # ...
```

---

## Phase 5: 주요 플레이어 식별 및 데이터 수집

### 목표
BM별 Top 플레이어 목록 작성, 외부 데이터 수집

### v9 실행 흐름

#### 5.1 Agent 협업: Structure → Reality Monitor

**umis_v9_agent_protocols.yaml#data_collection_request 프로토콜 실행**:

**Structure Analyst → Reality Monitor 요청**:
```yaml
collaboration_pattern: "data_collection_request"
from_role: "structure_analyst"
to_role: "reality_monitor"
request:
  workflow_id: "structure_analysis"
  phase_id: "PH05_player_identification"
  priority: "HIGH"
  target_data:
    - item: "YBM넷 매출"
      source_candidates: ["DART", "사업보고서"]
      reliability_target: "≥90%"
    - item: "링글 매출"
      source_candidates: ["투자 발표", "언론 보도"]
      reliability_target: "≥80%"
    - item: "야나두 매출"
      source_candidates: ["IR 발표", "언론 보도"]
      reliability_target: "≥80%"
    # ... (Top 50+ 플레이어)
```

#### 5.2 Evidence Engine: 외부 데이터 수집

**Reality Monitor가 Evidence Engine 호출**:

```python
evidence_bundle = evidence_engine.fetch_for_reality_slice(
    scope={
        "domain_id": "Adult_Language_Education_KR",
        "data_type": "player_revenue",
        "target_companies": ["YBM넷", "링글", "야나두", ...]
    },
    policy_ref="reporting_strict"
)
```

**Evidence Engine 내부 동작**:

1. **Data Sources 선택** (umis_v9.yaml#substrate_plane.data_sources):
   - `KR_DART_filings`: YBM넷 상장사 매출
   - `Industry_Media_and_Conferences`: 링글/야나두 발표 자료
   - `Brokerage_Research`: 증권사 리포트
   - `Commercial_Market_Research`: 시장조사 리포트

2. **API/웹 검색 실행**:
   ```python
   # DART API 호출
   dart_response = fetch_dart_api(
       company_name="YBM넷",
       report_type="annual",
       year=2023
   )

   # 웹 검색 (링글)
   web_search_results = search_web(
       query="링글 매출 2024 상반기",
       sources=["언론", "IR 발표"]
   )
   ```

3. **Evidence 정규화**:
   각 결과를 Evidence Store 스키마로 변환:
   ```yaml
   evidence_id: "EVD-20251205-001"
   source_tier: "official"  # DART
   url_or_path: "https://dart.fss.or.kr/..."
   content_ref: "YBM넷 2023 사업보고서"
   metadata:
     company: "YBM넷"
     year: 2023
     metric: "annual_revenue"
     value: 817억원
     reliability: 95
   retrieved_at: "2025-12-05T10:30:00"
   source_id: "KR_DART_filings"
   ```

4. **Evidence Store 저장**:
   - 총 20-30개 Evidence 수집
   - 각각 SRC-ID 부여

#### 5.3 World Engine: R-Graph에 Actor 노드 추가

**Evidence → R-Graph 투영**:

World Engine이 수집된 Evidence를 기반으로 R-Graph 업데이트:

```python
world_engine.ingest_evidence(
    evidence_ids=["EVD-20251205-001", "EVD-20251205-002", ...]
)
```

**내부 동작**:

1. **Actor 노드 생성/업데이트**:
   ```yaml
   # YBM넷 Actor 노드
   actor_id: "ACT-YBM_Net"
   kind: "company"
   name: "YBM넷"
   traits:
     domain_id: "Adult_Language_Education_KR"
     institution_type: "offline_academy"
     delivery_channel: "offline"
     bm_pattern: "PAT-offline_academy_comprehensive"
   metadata:
     confirmed_revenue_2023: 817억원
     evidence_id: "EVD-20251205-001"
     estimated_language_education_revenue: 500억원  # 전체의 60%
   ```

2. **MoneyFlow 노드 추가**:
   ```yaml
   money_flow_id: "MFL-customers_to_YBM"
   payer_id: "ACT-AdultLearners_SelfPaid"
   payee_id: "ACT-YBM_Net"
   quantity:
     amount: 500000000000  # 500억원
     currency: "KRW"
     per: "year"
   traits:
     revenue_model: "subscription"
   ```

3. **actor_pays_actor Edge 생성**:
   - Source: ACT-AdultLearners_SelfPaid
   - Target: ACT-YBM_Net
   - Via: MFL-customers_to_YBM

**결과**: R-Graph가 Top 50+ 플레이어로 채워짐

#### 5.4 Artifact 생성: 플레이어 목록

```yaml
artifact_id: "ART-player_list"
total_players: 50+
top_10:
  - rank: 1
    actor_id: "ACT-YBM_Net"
    name: "YBM넷 (어학 부문)"
    estimated_revenue: 500억원
    bm_pattern: "PAT-offline_academy_comprehensive"
    evidence_id: "EVD-20251205-001"
    reliability: 95
  - rank: 2
    actor_id: "ACT-Yanadoo"
    name: "야나두"
    estimated_revenue: 430억원
    bm_pattern: "PAT-online_vod_course"
    evidence_id: "EVD-20251205-003"
    reliability: 85
  # ...
```

---

## Phase 6: 가치사슬 구조 맵핑

### 목표
BM별 돈의 흐름 추적, 가치사슬 단계 식별, 마진 구조 파악

### v9 실행 흐름

#### 6.1 Pattern Engine: 가치사슬 템플릿 로드

**umis_v9_value_chain_templates.yaml 참조**:

```python
value_chain_template = pattern_engine.load_value_chain_template(
    bm_pattern="PAT-offline_academy_comprehensive"
)
```

**템플릿 내용**:
```yaml
template_id: "offline_academy_value_chain"
stages:
  - stage_id: "content_production"
    label: "콘텐츠 제작/교재 개발"
    typical_actors: ["publisher", "content_creator"]
    typical_cost_ratio: 0.10-0.15
    key_metrics: ["MET-Royalty_expenses"]
  - stage_id: "marketing_acquisition"
    label: "마케팅/수강생 모집"
    typical_cost_ratio: 0.20-0.30
    key_metrics: ["MET-Advertising_marketing_expenses", "MET-CAC"]
  - stage_id: "delivery_operations"
    label: "수업 제공/운영"
    typical_cost_ratio: 0.40-0.50
    key_metrics: ["MET-Personnel_expenses", "MET-COGS"]
  - stage_id: "overheads"
    label: "임대료/고정비"
    typical_cost_ratio: 0.20-0.30
    key_metrics: ["MET-OPEX"]
```

#### 6.2 World Engine: 가치사슬 R-Graph 구조 매핑

**R-Graph에서 MoneyFlow 추적**:

1. **Upstream 추적** (공급자 → 학원):
   ```
   ACT-ContentCreators_Publishers
       ↓ (MFL-academy_to_publisher: 교재비/로열티)
   ACT-YBM_Net
   ```

2. **Midstream** (학원 내부):
   ```
   ACT-YBM_Net
       → Personnel: 강사 인건비 40-50%
       → Facilities: 임대료 20-30%
       → Marketing: 광고비 10-15%
   ```

3. **Downstream** (학원 → 고객):
   ```
   ACT-YBM_Net
       ↓ (MFL-customers_to_YBM: 수강료)
   ACT-AdultLearners_SelfPaid
   ```

#### 6.3 Agent 협업: Structure → Numerical Modeler

**umis_v9_agent_protocols.yaml#structure_to_numerical_support**:

```yaml
request:
  from_role: "structure_analyst"
  to_role: "numerical_modeler"
  payload:
    market_segment: "Adult_Language_Education_KR"
    value_chain_stage: "delivery_operations"
    metric_ids:
      - "MET-Personnel_expenses"
      - "MET-Gross_margin"
      - "MET-Operating_margin"
    time_horizon: "2023-2024"
```

**Numerical Modeler → Value Engine 호출** (Phase 7에서 상세)

#### 6.4 Artifact 생성: 가치사슬 맵

```yaml
artifact_id: "ART-value_chain_map"
bm_id: "BM-01"
bm_name: "오프라인 종합 학원"
value_chain_flow: |
  [학습자] → [학원] → [강사 40-50%] + [교재 10-15%] + [임대료 20-30%]
            (100%)      순이익 10-20%
margin_structure:
  revenue: 100%
  cogs:
    personnel: 40-50%
    content_royalty: 10-15%
  opex:
    rent: 20-30%
    marketing: 10-15%
  operating_margin: 10-20%
```

---

## Phase 7: 시장규모 추정 (4-Method Convergence)

### 목표
전체/BM별/도메인별 시장 규모를 4가지 방법으로 추정하고 ±30% 내 수렴

### v9 실행 흐름

#### 7.1 Numerical Modeler 주도 + Value Engine 실행

**Value Engine - Metric Resolver 호출**:

```python
value_records, value_program = value_engine.evaluate_metrics(
    graph=snapshot.graph,
    metric_requests=[
        MetricRequest(metric_id="MET-TAM", context={"domain": "Adult_Language_KR", "year": 2024}),
        MetricRequest(metric_id="MET-SAM", context={"domain": "Adult_Language_KR", "year": 2024}),
        MetricRequest(metric_id="MET-N_customers", context={"domain": "Adult_Language_KR", "year": 2024}),
    ],
    policy_ref="decision_balanced"
)
```

#### 7.2 Metric Resolver - 4-Stage 실행 (MET-SAM 예시)

**umis_v9.yaml#value_engine.metrics_spec.metrics에 정의된 MET-SAM resolution_protocol 적용**:

##### Stage 1: Direct Evidence

**EvidenceEngine.fetch_for_metrics 호출**:
```python
evidence_bundle = evidence_engine.fetch_for_metrics(
    metric_requests=[{"metric_id": "MET-SAM", "context": {...}}],
    policy_ref="decision_balanced"
)
```

**검색 대상**:
- Commercial_Market_Research: 시장조사 리포트
- Consulting_Firm_Reports: 컨설팅사 리포트
- Brokerage_Research: 증권사 애널리스트 리포트

**결과**:
- 직접적인 "한국 성인 어학교육 시장 규모" 통계 없음
- Direct Evidence: **실패**

##### Stage 2: Derived / 계산 단계

**umis_v9.yaml에 정의된 4가지 Method 적용**:

**Method 1: Top-down**
```yaml
method: "top_down"
formula: "SAM = 상위 시장 × 세그먼트 비율"
inputs:
  - metric_id: "MET-elearning_market_KR"
    value: 8,500억원
    source: "EVD-20251205-004 (IMARC Group)"
  - assumed_share: 0.15-0.20
calculation: |
  SAM = 8,500억 × 0.175 (중간값)
      = 1,487억원
result: 1,500억원
quality:
  literal_ratio: 0.7
  spread_ratio: 0.3
  method: "top_down"
```

**Method 2: Bottom-up (Top 플레이어 합산)**

Value Engine이 R-Graph에서 Actor 매출 집계:

```python
# R-Graph 쿼리
top_players_revenue = sum([
    actor.metadata.get("estimated_revenue")
    for actor in graph.nodes_by_type("actor")
    if actor.data.get("kind") == "company"
    and actor.data.get("traits", {}).get("domain_id") == "Adult_Language_Education_KR"
])
```

결과:
```yaml
method: "bottom_up"
inputs:
  top_10_total: 3,400억원
  assumed_market_share: 0.30-0.40
calculation: |
  SAM = 3,400억 ÷ 0.35 (중간값)
      = 9,714억원
result: 10,000억원
quality:
  literal_ratio: 0.75  # 실제 매출 기반
  spread_ratio: 0.25
  method: "bottom_up"
```

**Method 3: Fermi 분해**

Metric Resolver가 LLM + 통계 데이터로 Fermi 추정:

```yaml
method: "fermi"
decomposition: "SAM = 성인 인구 × 학습 참여율 × 연간 지출액"
inputs:
  adult_population_kr: 42,000,000
    source: "EVD-20251205-010 (KOSIS)"
  learning_participation_rate: 0.15
    assumption: "ASM-20251205-001"
  annual_spending_per_learner: 200,000원
    assumption: "ASM-20251205-002"
calculation: |
  SAM = 42,000,000 × 0.15 × 200,000
      = 1,260,000,000,000원
result: 12,600억원
quality:
  literal_ratio: 0.7
  spread_ratio: 0.4
  method: "fermi"
```

**Method 4: Proxy (일본 시장 비교)**

```yaml
method: "proxy_validation"
inputs:
  japan_market_size: 2,500억엔
    source: "EVD-20251205-015 (일본 통계)"
  adjustment_factors:
    - gdp_ratio: 0.35  # 한국 GDP / 일본 GDP
    - population_ratio: 0.38
calculation: |
  SAM_proxy = 2,500억엔 × 140원/엔 × 0.365 (평균 조정계수)
           = 127,750억원
result: 18,000억원
quality:
  literal_ratio: 0.6
  spread_ratio: 0.5
  method: "proxy"
```

##### Stage 3: Fusion & Validation

**4-Method 가중 평균**:

```python
# umis_v9.yaml에 정의된 가중치 적용
methods = [
    {"method": "top_down", "value": 1500, "weight": 0.2, "quality": 0.7},
    {"method": "bottom_up", "value": 10000, "weight": 0.4, "quality": 0.75},
    {"method": "fermi", "value": 13000, "weight": 0.3, "quality": 0.7},
    {"method": "proxy", "value": 18000, "weight": 0.1, "quality": 0.6},
]

weighted_average = sum(m["value"] * m["weight"] for m in methods)
# = 1500*0.2 + 10000*0.4 + 13000*0.3 + 18000*0.1
# = 300 + 4000 + 3900 + 1800 = 10,000억원
```

**수렴 범위 검증** (umis_v9_validation_gates.yaml#four_method_convergence):

```yaml
convergence_check:
  weighted_average: 10,000억원
  acceptable_range: "±30%"
  actual_range: [7,000억 ~ 13,000억]
  deviation_from_average:
    - top_down: -85% (outlier)
    - bottom_up: 0%
    - fermi: +30%
    - proxy: +80% (outlier)
```

**결과**:
- Top-down과 Proxy는 outlier로 판단
- Bottom-up과 Fermi가 ±30% 내 수렴
- ✅ PASS (조건부: outlier 제거 후)

**최종 ValueRecord 생성**:

```yaml
value_id: "VAL-SAM_AdultLanguage_KR_2024"
metric_id: "MET-SAM"
context:
  domain: "Adult_Language_Education_KR"
  year: 2024
  region: "KR"
point_estimate: 10000억원
distribution:
  type: "range"
  min: 7000억원
  max: 13000억원
  confidence_interval: 0.7
quality:
  status: "ok"
  method: "4_method_fusion"
  literal_ratio: 0.75
  spread_ratio: 0.30
  convergence_passed: true
lineage:
  from_evidence_ids:
    - "EVD-20251205-001"  # YBM넷 매출
    - "EVD-20251205-002"  # 링글 매출
    - "EVD-20251205-003"  # 야나두 매출
    - "EVD-20251205-004"  # e-러닝 시장
    - "EVD-20251205-010"  # KOSIS 인구
  from_value_ids: []
  from_pattern_ids: ["PAT-offline_academy_comprehensive", "PAT-online_vod_course"]
  from_program_id: "value_program_20251205_001"
  engine_ids: ["value_engine", "evidence_engine"]
  policy_id: "decision_balanced"
  created_by_role: "numerical_modeler"
  created_at: "2025-12-05T14:30:00"
```

#### 7.3 BM별/도메인별 규모 계산

**동일한 Metric Resolver를 반복 실행**:

BM별:
- MET-Revenue_BM01 (종합 학원)
- MET-Revenue_BM02 (전문 학원)
- ...

도메인별:
- MET-Revenue_English
- MET-Revenue_Chinese
- ...

각각 R-Graph Actor 그룹 집계 + Pattern 기반 비율 추정

#### 7.4 Artifact 생성: 시장규모 추정 결과

```yaml
artifact_id: "ART-market_size_estimate"
total_market:
  value: 10,000억원
  range: [7,000억 ~ 13,000억]
  reliability: 75%
  asm_id: "ASM-20251205-100"
bm_breakdown:
  - bm_id: "BM-01"
    bm_name: "오프라인 종합 학원"
    market_size: 1,950억원
    share: 19.5%
    asm_id: "ASM-20251205-110"
  - bm_id: "BM-02"
    bm_name: "전문 학원 (시험)"
    market_size: 800억원
    share: 8.0%
    asm_id: "ASM-20251205-120"
  # ...
domain_breakdown:
  - language: "영어"
    market_size: 7,500억원
    share: 75.0%
  - language: "중국어"
    market_size: 1,250억원
    share: 12.5%
  # ...
```

---

## Phase 8-11: 경쟁구조, 교섭력, 거래구조, 시장집중도

### 목표
Porter 5 Forces 기반 경쟁 분석

### v9 실행 흐름

#### 8.1 Pattern Engine: 전략 프레임워크 로드

**umis_v9_strategic_frameworks.yaml#porter_5_forces**:

```python
framework = pattern_engine.load_strategic_framework(
    framework_id="porter_5_forces"
)
```

**프레임워크 구조**:
```yaml
framework_id: "porter_5_forces"
category: "competition_structure"
suggests_goal_metrics:
  - "MET-HHI_revenue"
  - "MET-Top3_revenue_share"
  - "MET-Operating_margin"
pattern_links:
  - "PAT-market_concentration"
  - "PAT-platform_power"
```

#### 8.2 Value Engine: 경쟁 Metric 계산

**Metric 요청**:
```python
competition_metrics = value_engine.evaluate_metrics(
    graph=snapshot.graph,
    metric_requests=[
        MetricRequest("MET-HHI_revenue", context={"bm": "BM-01"}),
        MetricRequest("MET-Top3_revenue_share", context={"bm": "BM-01"}),
        MetricRequest("MET-Top5_revenue_share", context={"bm": "BM-01"}),
    ],
    policy_ref="reporting_strict"
)
```

**Value Engine 내부 동작 (MET-HHI_revenue)**:

1. **R-Graph에서 BM-01 Actor 매출 수집**:
   ```python
   bm01_actors = [
       actor for actor in graph.nodes_by_type("actor")
       if "PAT-offline_academy_comprehensive" in actor.data.get("traits", {}).get("bm_pattern")
   ]

   revenues = [actor.metadata.get("estimated_revenue") for actor in bm01_actors]
   total_revenue = sum(revenues)
   ```

2. **HHI 계산**:
   ```python
   market_shares = [r / total_revenue for r in revenues]
   hhi = sum(s**2 for s in market_shares) * 10000
   # HHI = 800 (중간 집중도)
   ```

3. **ValueRecord 생성**:
   ```yaml
   value_id: "VAL-HHI_BM01"
   metric_id: "MET-HHI_revenue"
   point_estimate: 800
   quality:
     literal_ratio: 1.0  # R-Graph 직접 계산
     spread_ratio: 0.0
   ```

#### 8.3 교섭력 분석 (Pattern 기반)

**Pattern Engine - 교섭력 패턴 인식**:

```python
bargaining_patterns = pattern_engine.match_patterns(
    graph_slice_ref=snapshot.graph,
    pattern_family="bargaining_power"
)
```

**패턴 매칭 결과**:
- 강사/튜터 교섭력: "PAT-supplier_bargaining_high" (스타 강사)
- 학습자 교섭력: "PAT-buyer_bargaining_low" (개인 구매)
- B2B 고객: "PAT-buyer_bargaining_high" (대량 구매)

#### 8.4 Artifact 생성: 경쟁구조 분석

```yaml
artifact_id: "ART-competition_analysis"
bm_analysis:
  - bm_id: "BM-01"
    bm_name: "종합 학원"
    competition_intensity: "높음"
    metrics:
      cr3: 40%
      hhi: 800
      top_players_dominance: "중간"
    barriers_to_entry: "중간"
    price_competition: "높음"
    supplier_bargaining: "중간-높음"
    buyer_bargaining: "낮음-중간"
  # ...
```

---

## Phase 12: MECE 검증

### 목표
모든 분류 MECE 재검증, 합산 검증

### v9 실행 흐름

#### 12.1 Policy Engine: Validation Gates 실행

**umis_v9_validation_gates.yaml#summation_validation**:

```python
validation_result = policy_engine.validate(
    gate_type="summation_validation",
    artifacts=[
        "ART-domain_classification",
        "ART-bm_complete_list",
        "ART-market_size_estimate"
    ]
)
```

**검증 로직**:

1. **BM별 합산**:
   ```
   Σ(BM 시장 규모) = 10,000억
   전체 시장 = 10,000억
   차이 = 0% ✅
   ```

2. **도메인별 합산**:
   ```
   Σ(도메인 시장 규모) = 7,500 + 1,250 + 750 + ... = 10,000억
   전체 시장 = 10,000억
   차이 = 0% ✅
   ```

3. **Tolerance 확인**:
   - 허용 범위: ±5%
   - 실제 차이: 0%
   - ✅ PASS

---

## Phase 13: 최종 검증 게이트 (3자 검증)

### 목표
Numerical Modeler, Reality Monitor, Structure Analyst 3자 체크리스트 검증

### v9 실행 흐름

#### 13.1 Agent 협업: Structure → Numerical/Reality

**umis_v9_agent_protocols.yaml#structure_validation_request**:

```yaml
validation_request:
  from_role: "structure_analyst"
  to_roles: ["numerical_modeler", "reality_monitor"]
  trigger:
    workflow_id: "structure_analysis"
    phase_id: "PH13_validation_gate"
  artifacts_for_validation:
    - "ART-market_size_estimate"
    - "ART-value_chain_map"
    - "ART-competition_analysis"
    - "Market_Reality_Report_Draft"
```

#### 13.2 Numerical Modeler 체크리스트

**umis_v9_validation_gates.yaml#three_validator_gate.numerical_modeler_checklist**:

```yaml
validator: "numerical_modeler"
checklist:
  - item_id: "calc_logic"
    check: "공식이 맞는가? 4-Method 수렴 여부는?"
    validation_method: |
      1. Value Graph에서 formula edge 검증
      2. 4-Method 수렴 ±30% 확인
      3. Lineage 추적 가능 확인
    result: "✅ PASS"
    notes: "Bottom-up과 Fermi가 ±30% 내 수렴, outlier 제외 처리 완료"

  - item_id: "convergence"
    check: "SAM/TAM 추정이 ±30% 범위 내인가?"
    result: "✅ PASS"

  - item_id: "summation"
    check: "BM별 = 도메인별 = 전체가 ±5% 이내 일치하는가?"
    result: "✅ PASS"
    notes: "차이 0%"
```

#### 13.3 Reality Monitor 체크리스트

```yaml
validator: "reality_monitor"
checklist:
  - item_id: "source_quality"
    check: "evidence_id/source_id와 신뢰도 메타데이터가 모두 있는가?"
    validation_method: |
      1. Evidence Store에서 EVD-* 목록 확인
      2. 각 Evidence의 reliability 필드 확인
      3. 평균 신뢰도 계산
    result: "✅ PASS"
    average_reliability: 75%
    total_evidence_count: 25
    evidence_without_id: 0

  - item_id: "traceability"
    check: "모든 주장에 lineage.from_evidence_ids가 연결되어 있는가?"
    validation_method: |
      1. Value Store에서 VAL-* 목록 확인
      2. 각 ValueRecord.lineage.from_evidence_ids 확인
    result: "✅ PASS"
    traceability_coverage: 100%
```

#### 13.4 Structure Analyst 체크리스트

```yaml
validator: "structure_analyst"
checklist:
  - item_id: "goal_alignment"
    check: "보고서 결론이 초기 분석 목적과 일치하는가?"
    original_question: |
      "한국 성인 어학교육 시장 구조를 알고 싶어.
       Top-N 플레이어 구조 + 가치사슬도 함께 확인해줘."
    report_coverage:
      - "✅ 시장 구조 (Needs/BM/Domain 분류)"
      - "✅ Top-N 플레이어 (Top 10 + 50+ 목록)"
      - "✅ 가치사슬 (BM별 돈의 흐름)"
    result: "✅ PASS"

  - item_id: "umis_principles"
    check: "Evidence-first, Model-first 원칙을 충실히 따랐는가?"
    evidence_first_check:
      - "✅ DART/공식 발표 우선 활용"
      - "✅ Prior는 데이터 갭에만 사용"
      - "✅ 모든 추정에 근거 명시"
    model_first_check:
      - "✅ 숫자는 항상 BM/도메인 구조 전제"
      - "✅ R-Graph 기반 계산"
    result: "✅ PASS"

  - item_id: "overall_quality"
    check: "논리적 비약/누락 없이 독립적인 검토자가 이해 가능한가?"
    result: "✅ PASS (A급 품질)"
```

#### 13.5 최종 검증 결과

```yaml
validation_gate: "three_validator_gate"
status: "PASS"
validators:
  - role: "numerical_modeler"
    status: "PASS"
    passed_items: 3/3
  - role: "reality_monitor"
    status: "PASS"
    passed_items: 2/2
  - role: "structure_analyst"
    status: "PASS"
    passed_items: 3/3
overall: "✅ 3명 모두 통과"
timestamp: "2025-12-05T16:00:00"
```

---

## Phase 14: Market Reality Report 작성

### 목표
모든 Artifact 통합, 최종 리포트 생성

### v9 실행 흐름

#### 14.1 Structure Analyst: 리포트 템플릿 로드

**Template**:
- umis_v9_process_phases.yaml#PH14_report_generation
- template: "market_reality_report_template"

#### 14.2 Artifact 통합

**Memory Store에서 모든 Artifact 수집**:

```python
artifacts = memory_store.query(
    memory_type="project_artifact",
    project_id="Adult_Language_Education_KR_structure_analysis"
)
```

**수집된 Artifact**:
- ART-needs_classification
- ART-domain_classification
- ART-bm_framework
- ART-bm_complete_list
- ART-player_list
- ART-value_chain_map
- ART-market_size_estimate
- ART-competition_analysis
- (총 15개+ Artifact)

#### 14.3 리포트 섹션 생성

**Executive Summary**:
- Value Store에서 핵심 Metric 조회:
  - VAL-SAM_AdultLanguage_KR_2024: 1조원
  - VAL-Top10_revenue_share: 34%
  - VAL-HHI_BM01: 800

**Section 1: 시장 정의**:
- ART-needs_classification → Markdown 변환

**Section 2: 시장 규모**:
- ART-market_size_estimate → Table 생성
- 4-Method 상세 설명
- Lineage 기반 근거 추가

**Section 3-6**: (동일한 방식으로 각 Artifact → Markdown)

**Section 7: 데이터 추적성**:

```markdown
### 7.1 Source Registry

| SRC-ID | 출처 | 신뢰도 | 데이터 |
|--------|------|--------|--------|
| EVD-20251205-001 | DART (YBM넷) | 95 | 2023 매출 817억 |
| EVD-20251205-002 | 링글 발표 | 85 | 2024 상반기 100억 |
| EVD-20251205-003 | 야나두 발표 | 85 | 2024 1Q 107억 |
...

### 7.2 Assumption Registry

| ASM-ID | 가정 | 근거 |
|--------|------|------|
| ASM-20251205-100 | 전체 시장 1조원 | 4-Method 수렴 |
| ASM-20251205-110 | 종합학원 1,950억 | Top 플레이어 합산 |
...

### 7.3 Estimation Registry

(ValueRecord lineage 기반 자동 생성)
```

#### 14.4 최종 Markdown 생성

```python
report = structure_analyst.generate_report(
    template="market_reality_report_template",
    artifacts=artifacts,
    value_records=value_records,
    evidence_records=evidence_records
)
```

**출력**:
- `Market_Reality_Report_Final.md`
- 548줄 Markdown 문서
- v7.x 결과물과 동일한 구조

---

## 전체 워크플로우 요약

### 입력 → 출력 흐름

```
[사용자 질문: "한국 성인 어학교육 시장..."]
  ↓
[PH01] Needs 분류 → ART-needs_classification
  ↓
[PH02] 도메인 분류 → ART-domain_classification
  ↓
[PH03-04] BM 분류 → ART-bm_framework, ART-bm_complete_list
  ↓
[PH05] 플레이어 식별
  → Evidence Engine → 외부 데이터 수집 (DART, 웹 검색)
  → World Engine → R-Graph 구축 (Actor/MoneyFlow 노드 추가)
  → ART-player_list
  ↓
[PH06] 가치사슬 맵핑
  → Pattern Engine → 가치사슬 템플릿 로드
  → World Engine → MoneyFlow 추적
  → ART-value_chain_map
  ↓
[PH07] 시장규모 추정
  → Value Engine (Metric Resolver)
    → Stage 1: Direct Evidence (실패)
    → Stage 2: Derived (4-Method)
      - Top-down
      - Bottom-up (R-Graph 집계)
      - Fermi (LLM + 통계)
      - Proxy (일본 비교)
    → Stage 3: Fusion (4-Method 가중 평균)
    → Stage 4: Validation (±30% 수렴 확인)
  → Value Store 저장 (VAL-SAM, VAL-TAM, ...)
  → ART-market_size_estimate
  ↓
[PH08-11] 경쟁/교섭력/집중도
  → Pattern Engine → Porter 5 Forces 프레임워크
  → Value Engine → HHI, CR3 계산
  → ART-competition_analysis
  ↓
[PH12] MECE 검증
  → Policy Engine → summation_validation gate
  → ✅ PASS
  ↓
[PH13] 3자 검증 게이트
  → Numerical Modeler: 계산 논리, 수렴, 합산 ✅
  → Reality Monitor: 출처 품질, 추적성 ✅
  → Structure Analyst: 목표 정렬, UMIS 원칙, 품질 ✅
  → ✅ 3명 모두 통과
  ↓
[PH14] 리포트 생성
  → 모든 Artifact 통합
  → Markdown 템플릿 적용
  → Market_Reality_Report_Final.md (548줄)
  ↓
[최종 산출물]
```

---

## 핵심 차별점: v7 vs v9

### v7.x 방식

**Agent 중심**:
- Observer(Albert), Validator(Rachel), Quantifier(Bill), Estimator(Fermi), Guardian(Stewart)
- 각 Agent가 독립적으로 문서/데이터 작성
- 문서 기반 협업 (Markdown, YAML 파일 교환)

**데이터 흐름**:
- 텍스트 중심 (Markdown 리포트)
- 숫자는 문서 내 테이블/목록
- 추적성: SRC-/EST-/ASM- ID를 수동으로 부여

**한계**:
- "세계 구조"가 문서에 흩어짐
- 그래프 구조로 표현되지 않음
- 재사용/자동화 어려움

### v9 방식

**Engine + Graph 중심**:
- Role은 "사람 관점의 얼굴"일 뿐
- 실제 작업은 World/Pattern/Value Engine이 수행
- R-Graph/P-Graph/V-Graph가 구조화된 세계 모델

**데이터 흐름**:
- 그래프 중심 (R-Graph: Actor/MoneyFlow, V-Graph: Metric/ValueRecord)
- 숫자는 ValueRecord로 lineage 포함 저장
- 추적성: 자동으로 lineage 필드에 기록

**장점**:
- 구조화된 세계 모델 → 재사용/확장 용이
- 동일한 R-Graph로 다른 질문에도 답변 가능
- 패턴 기반 아날로지 (SaaS → 오프라인 건물관리)
- 학습 가능 (LearningEngine으로 Pattern/Metric 업데이트)

---

## 실행 예시 (Python 코드)

```python
from umis_v9_core import (
    WorldEngine, PatternEngine, ValueEngine, PolicyEngine,
    StructureAnalystRole
)

# 1. 워크플로우 초기화
analyst = StructureAnalystRole(
    workflow_id="structure_analysis",
    config_path="umis_v9.yaml"
)

# 2. 사용자 질문 입력
user_query = """
한국 성인 어학교육 시장 구조를 알고 싶어.
Top-N 플레이어 구조 + 돈의 흐름에 따른 전후방 가치사슬도 함께 확인해줘.
"""

# 3. 워크플로우 실행
report = analyst.execute(
    query=user_query,
    domain_id="Adult_Language_Education_KR",
    region="KR",
    policy_mode="reporting_strict"
)

# 4. 결과 출력
print(f"Report generated: {report.output_path}")
print(f"Total evidence: {len(report.evidence_ids)}")
print(f"Total metrics calculated: {len(report.value_records)}")
print(f"Validation status: {report.validation_status}")

# 출력 예시:
# Report generated: Market_Reality_Report_Final.md
# Total evidence: 25
# Total metrics calculated: 47
# Validation status: PASS (3/3 validators)
```

---

**작성일**: 2025-12-05
**버전**: v1.0
**상태**: 완료


---

## Phase 0 (PH00): Project Context Setup (Brownfield 전용, 2025-12-05 추가)

### 목표
사용자/조직의 현재 상태/자산/제약/선호를 구조화하여 Project Context로 생성

### v9 실행 흐름

#### 0.1 Role Plane: Structure Analyst + 사용자 인터뷰

**입력 (구조화된 폼 또는 인터뷰)**:
```yaml
focal_actor_input:
  organization_name: "XYZ어학원"
  current_business:
    revenue: "연 800억"
    customers: 45000
    channels: "오프라인 120개 지점, 온라인 미미"
  
  capabilities:
    - "전국 지점 네트워크 120개"
    - "강사 800명"
    - "브랜드 Top 3"
    - "디지털 인프라 약함"
  
  constraints:
    - "디지털 투자 연 30억 이내"
    - "오프라인 매출 90% 이상 유지"
    - "3년 내 손익 방어"
  
  preferences:
    - "현금흐름 안정 우선"
    - "점진적 전환"
  
  goal:
    - "디지털 확장하며 기존 사업 방어"
```

#### 0.2 Cognition Plane: Evidence Engine - 내부 데이터 수집

**Structure Analyst → Reality Monitor 협업**:
```yaml
collaboration_protocol: "data_collection_request"
request_type: "internal_data"
target_data:
  - "재무제표 (최근 3년)"
  - "CRM 고객 데이터"
  - "지점별 성과 데이터"
```

**Evidence Engine 동작**:
```python
evidence_bundle = evidence_engine.fetch_internal_data(
    sources=[
        {"type": "financial_statement", "path": "internal/fs_2024.xlsx"},
        {"type": "crm_export", "path": "internal/crm_2024.csv"},
        {"type": "branch_report", "path": "internal/branches_2024.json"}
    ]
)
```

**Evidence Store 저장**:
```yaml
- evidence_id: "EVD-internal-financial-statement-2024"
  source_tier: "curated_internal"
  content_ref: "재무제표 2024"
  metadata:
    revenue: 80000000000
    gross_margin: 0.45
  reliability: 95

- evidence_id: "EVD-internal-crm-export-2024"
  source_tier: "curated_internal"
  content_ref: "CRM 데이터"
  metadata:
    total_customers: 45000
  reliability: 90
```

#### 0.3 Cognition Plane: World Engine - focal_actor R-Graph 구성

**World Engine.ingest_evidence() 호출**:
```python
world_engine.ingest_evidence(
    evidence_ids=["EVD-internal-financial-statement-2024", ...]
)
```

**R-Graph에 Actor 노드 생성**:
```yaml
actor_id: "ACT-CLIENT-OfflineAcademy-Chain-001"
kind: "company"
name: "XYZ어학원"
traits:
  domain_id: "Adult_Language_Education_KR"
  institution_type: "offline_academy"
  delivery_channel: "offline"
  org_stage: "established"
metadata:
  revenue_2024: 80000000000
  branch_count: 120
  evidence_id: "EVD-internal-financial-statement-2024"
```

#### 0.4 Cognition Plane: Capability → Trait 매핑

**Structure Analyst가 capability_traits로 변환**:

입력:
```
"전국 지점 네트워크 120개"
```

변환:
```yaml
capability_id: "CAP-101"
name: "전국 오프라인 네트워크"
trait_set:
  domain_expertise: "education"
  maturity_level: "mature"
  geographic_coverage: "national"
  delivery_channel: "offline"
  scale_tier: "enterprise"
```

#### 0.5 Substrate Plane: Project Context 객체 생성

**project_context_store에 저장**:
```yaml
project_context_id: "PRJ-20251205-OfflineAcademy-Chain-001"
version: 1
focal_actor_id: "ACT-CLIENT-OfflineAcademy-Chain-001"
mode: "brownfield"

baseline_state:
  current_revenue: 80000000000
  current_customers: 45000
  evidence_ids: ["EVD-internal-financial-statement-2024"]

assets_profile:
  capability_traits: [...]  # 상세는 examples/project_context_examples.yaml 참조

constraints_profile:
  hard_constraints: [...]

preference_profile:
  soft_preferences: [...]

lineage:
  from_evidence_ids: ["EVD-internal-financial-statement-2024", ...]
  engine_ids: ["world_engine", "evidence_engine"]
```

#### 0.6 Validation

**Policy Engine - completeness_check**:
- ✅ focal_actor_id가 R-Graph에 존재
- ✅ baseline_state 핵심 Metric 계산 가능
- ✅ hard_constraints에 Evidence 연결
- ✅ capability_traits가 Trait 스키마 준수

**결과**: Phase 1으로 진행

---

## Phase 1-14: 기존 Phase 재사용 (project_context_id 전달)

**Brownfield 모드 (structure_analysis_for_project)**:
- PH01-PH14는 기존과 동일
- **차이점**: 모든 Engine 호출 시 `project_context_id` 전달

**예시 - Phase 7 시장규모 추정**:

기존 (Greenfield):
```python
value_engine.evaluate_metrics(
    graph=snapshot.graph,
    metric_requests=[MetricRequest("MET-SAM", ...)],
    policy_ref="decision_balanced"
)
```

확장 (Brownfield):
```python
value_engine.evaluate_metrics(
    graph=snapshot.graph,
    metric_requests=[
        MetricRequest("MET-SAM", ...),  # 시장 전체
        MetricRequest("MET-SOM_for_project", ...)  # 이 조직 관점
    ],
    policy_ref="decision_balanced",
    project_context_id="PRJ-20251205-OfflineAcademy-Chain-001"  # 추가
)
```

**PatternEngine 이중 평가**:
```python
pattern_matches = pattern_engine.match_patterns(
    graph_slice_ref=snapshot.graph,
    project_context_id="PRJ-20251205-OfflineAcademy-Chain-001"
)

# 결과:
[
    PatternMatch(
        pattern_id="PAT-online_subscription",
        structure_fit_score=0.90,  # 시장 구조 적합
        execution_fit_score=0.30,  # 조직 실행 어려움
        combined_score=0.27
    ),
    PatternMatch(
        pattern_id="PAT-offline_subscription_premium",
        structure_fit_score=0.60,
        execution_fit_score=0.95,  # 기존 자산 활용 가능
        combined_score=0.57  # 최종 우선순위 더 높음
    )
]
```

**최종 리포트 차이**:
- Greenfield: "시장 전체 TAM 1조원"
- Brownfield: "시장 TAM 1조원, **우리 SOM 500억** (오프라인 자산 활용 시)"

