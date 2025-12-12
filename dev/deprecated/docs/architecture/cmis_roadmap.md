---
**이력**: 2025-12-09 UMIS v9 → CMIS로 브랜드 변경
- Universal Market Intelligence → Contextual Market Intelligence
- v9 핵심 차별점 (Project Context Layer) 반영
---

# UMIS v9 구현 로드맵 (스프린트 단위 상위 설계)

UMIS v9를 실제로 구현하려면 **한 번에 전체를 만드는 방식이 아니라**,  
특정 도메인에 대한 **세로 슬라이스(vertical slice)** 를 반복해서 깊게 파는 방식이 적합합니다.

아래는 **2주 스프린트**를 가정한 상위 로드맵입니다.  
(기간은 조정 가능하며, 핵심은 “각 스프린트마다 실사용 + 피드백”이 반드시 들어가도록 설계하는 것 입니다.)

---

## 전체 Phase 개요

1. **Phase 0–1: 기반 잡기**  
   - 도메인 선택, v9 YAML/온톨로지 확정, 최소 인프라
2. **Phase 2: Reality + Value 최소 루프**  
   - 한 도메인에 대해 R-Graph + Metric Resolver v0
3. **Phase 3: Pattern + Opportunity 루프**  
   - P-Graph / PatternEngine, 기회 발굴까지
4. **Phase 4: Strategy + Outcome 루프**  
   - D-Graph / StrategyEngine / LearningEngine v0
5. **Phase 5: 멀티도메인 / 플랫폼화**  
   - 도메인 확장, UI/API, Ops/품질 체계

> 전제: **POC 도메인을 1개 선택** (예: B2B SaaS, 한국 피아노 레슨 시장 등)  
> 이 도메인에서 질문 → 구조 → 값 → 기회 → 전략 → 학습 루프를 먼저 완성한 뒤 확장합니다.

---

## Phase 0 – 문제 정의 & 도메인 고르기 (Sprint 0)

### Sprint 0: 도메인 · 질문 · 성공 기준 정리

**목표**

- v9 POC에서 집중할 **1개 도메인**과  
  이 도메인에 대한 **대표 질문 세트**,  
  그리고 **성공 기준**을 명시합니다.

**작업**

- 도메인 선택
  - 예: B2B SaaS, 한국 사교육(피아노 레슨), 특정 산업(물류/헬스케어 등)
  - 기준: 데이터 접근성, 내부 도메인 지식 보유 여부
- 대표 질문 10–20개 선정
  - 구조 질문  
    - 예: “이 시장의 주요 행위자/가치사슬/마진 구조는?”
  - 기회 질문  
    - 예: “어떤 새로운 수익 모델/패턴 기회가 있는가?”
  - 숫자 질문  
    - 예: “대략적인 TAM/ARPU/LTV/Churn은?”
  - 전략 질문  
    - 예: “전략 A/B/C의 3년 뒤 결과 차이는?”
- v9 POC 성공 기준(초기 버전) 정의
  - v7 + 엑셀(수동 분석) 대비:
    - 설명력(why) / 재사용성(모델 재활용) / 속도(총 작업 시간) 중 최소 1~2개에서 개선

**실사용 / 피드백**

- 현재 v7/수동 방식으로 대표 질문 2–3개를 실제로 풀어본 후:
  - 어떤 단계(데이터 수집, 구조화, 계산, 설명 등)에서 사람이 가장 고통받는지 기록
  - 이 고통 포인트를 이후 스프린트 우선순위에 반영

---

## Phase 1 – v9 뼈대 & 온톨로지 고정 (Sprint 1–2)

### Sprint 1: `umis_v9.yaml` 뼈대 + Ontology v1

**목표**

- 이미 설계한 `umis_v9.yaml` 스켈레톤을  
  **실제 리포지토리 상의 “단일 상위 설계 파일”**로 고정합니다.

**작업**

- `umis_v9.yaml` 코드 repo에 추가
- YAML 파서/검증 스크립트 작성
  - 필수 필드/타입 검증
- `ontology.primitives` / `traits.core_traits`를 POC 도메인 기준으로 1차 조정
  - Actor/Event/MoneyFlow/State/Quantity 필드에서 과도한/부족한 것 정리
- Reality/Pattern/Value/Decision Graph의 node/edge 타입 최소 집합 확정
- `ids_and_lineage`를 공통 베이스 클래스로 구현
  - ID 생성 규칙 + lineage 필드 자동 채우기 헬퍼

**실사용 / 피드백**

- 도메인 담당자(사람)에게:
  - 실제 케이스(회사/서비스 2–3개)를 Actor/Event/MoneyFlow/State 스키마로  
    수동 YAML/JSON 작성하게 해봄
- 피드백 수집:
  - “이 필드는 불필요하다”
  - “이 속성 없으면 도메인 설명이 안 된다”
  - → Sprint 2에서 Ontology v1.1에 반영

---

### Sprint 2: 최소 인프라 – Graph/Store 스켈레톤 + CLI/Notebook

**목표**

- 실제로 R/P/V/D 그래프를  
  **메모리나 간단한 DB(예: Neo4j/SQLite/Arango 등)** 에 표현할 수 있는 최소 코드와,
- 개발자가 직접 만져볼 수 있는 **CLI/Notebook 인터페이스**를 마련합니다.

**작업**

- Graph/Store 추상화 구현
  - `Graph` 인터페이스  
    - node upsert, edge upsert, query
  - `Store` 인터페이스  
    - evidence_store, value_store, memory_store 등
- `umis_v9.yaml` 로딩 및 인스턴스 구성 코드
  - YAML을 읽어 실제 Graph/Store 객체 생성
- 간단 Notebook/CLI 예제:
  - “Actor 1개 만들고, Event/ MoneyFlow 연결하기”
  - “현재 R-Graph에서 Actor 목록과 MoneyFlow 간선 출력”

**실사용 / 피드백**

- 팀 내에서:
  - POC 도메인(예: 피아노 레슨)으로 Actor/Event/MoneyFlow 3–5개를  
    Notebook에서 직접 입력해 보고,  
    간단히 시각화/조회까지 해봄
- 피드백:
  - 그래프 사용 시 번거로운 부분
  - ID/lineage 자동화 부족 지점
  - → EvidenceEngine/WorldEngine 설계 시 “어디를 자동화해야 하는지”에 대한 인사이트 확보

---

## Phase 1.5 – Project Context Layer 기반 (Sprint 2.5, 2025-12-05 추가)

### Sprint 2.5: Project Context Layer 스키마 및 PH00 Phase

**목표**

- Brownfield/Greenfield 모두 지원하기 위한 Project Context Layer 설계 및 최소 구현

**작업**

- `umis_v9.yaml` 확장
  - project_context_store 스키마 추가
  - capability_traits 정의 (9개 핵심 Trait)
  - Engine API에 project_context_id 인자 추가
  - Decision Graph goal 노드에 project_context_id 필드 추가
- `umis_v9_process_phases.yaml` 확장
  - PH00_project_context_setup Phase 정의
  - structure_analysis_for_project 워크플로우 추가
- Project Context 입력 예시 3가지 작성
  - Greenfield 스타트업
  - Brownfield 오프라인 학원
  - Hybrid 글로벌 플랫폼
- PH00 실행 템플릿/가이드 작성

**실사용 / 피드백**

- 실제 회사 2–3개에 대해 Project Context 수동 작성
- PH00 Phase 시뮬레이션 (실제 데이터 없이 가상)
- capability_traits 매핑 난이도 확인

---

## Phase 2 – Reality + Value 최소 루프 (Sprint 3–5)

### Sprint 3: EvidenceEngine v0 + WorldEngine v0 + R-Graph v0

**목표**

- POC 도메인에 대해 **외부 데이터 1–2개**를 Evidence로 가져와  
  **R-Graph에 자동 반영하는 최소 파이프라인**을 구현합니다.
- **내부 데이터 수집 지원 추가** (Project Context용)

**작업**

- `data_sources` 설정
  - 예: 공공 API(통계청/KOSIS) 1개 + 웹 검색(검색엔진+LLM) 1개
- EvidenceEngine v0
  - `fetch_for_reality_slice(scope)` 구현
    - 입력: { country, sector, year 등 }
    - 출력: EvidenceBundle (아직은 간단한 구조)
- WorldEngine v0
  - EvidenceBundle → Actor/Event/MoneyFlow/State/Traits 추출 규칙(LLM + 규칙 기반)
  - R-Graph에 upsert
- 최소 R-Graph 쿼리 구현
  - “이 도메인의 주요 Actor 리스트”
  - “Actor 간 MoneyFlow 관계의 개략 구조”

**실사용 / 피드백**

- 실제 질문 예시:
  - “한국 피아노 레슨 시장에 어떤 유형의 플레이어와 돈 흐름이 있는지?”
- 스프린트 마지막에:
  - 위 질문에 대해 v9 R-Graph 기반 리포트를 만들어보고,
  - v7/수동 분석 결과와 구조적으로 비교
- 피드백:
  - Evidence 정규화 규칙/프롬프트 튜닝 필요
  - Trait 자동 태깅 품질 이슈
  - → Sprint 4에 반영

---

### Sprint 4: ValueEngine v0 + MetricSpec v0 + Metric Resolver (Direct + Derived)

**목표**

- POC 도메인 핵심 Metric 5–10개에 대해  
  **Direct Evidence + Derived 계산**까지 되는 Metric Resolver v0를 구현합니다.

**작업**

- MetricSpec v0 작성
  - 예: `TAM`, `N_customers`, `Avg_price`, `ARPU`, 간단한 `Churn_analog` 등
  - 각 Metric에 대해:
    - direct_evidence 설정(어떤 소스/조건을 우선 탐색할지)
    - derived_paths 설정(어떤 Sub-metric과 공식으로 계산 가능한지)
- ValueEngine v0
  - `evaluate_metrics(metric_requests, policy_ref)` 구현:
    - Direct Evidence:
      - EvidenceEngine.fetch_for_metrics 호출
    - Derived:
      - ValueGraph의 formula/MetricSpec의 derived_paths를 따르며  
        Sub-metric에 대해 Metric Resolver 재귀 호출
- ValueRecord 구조/quality(lineage 포함) 저장

**실사용 / 피드백**

- 실제 질문 예시:
  - “이 도메인의 Rough TAM / 평균 가격 / Rough 고객 수?”
- 스프린트 마지막에:
  - v7 + 엑셀 기반 계산 vs v9 ValueEngine 결과를 비교:
    - 값 차이
    - “어떤 Evidence/공식을 사용했는지” 설명력 비교
- 피드백:
  - MetricSpec 표현이 어려운 부분
  - Derived 경로 설계 방식 개선점
  - EvidenceEngine이 Metric 단위로 fetch할 때 발생하는 마찰

---

### Sprint 5: Metric Resolver Prior 단계 v1 + 품질/정책 프로파일

**목표**

- Evidence/Derived만으로는 부족한 Metric에 대해  
  **구조적 추정(Prior/Fermi) 단계**까지 포함하는 Metric Resolver를 구현하고,
- `reporting_strict / decision_balanced / exploration_friendly` 같은  
  **품질/정책 프로파일을 실제로 활용**해봅니다.

**작업**

- MetricSpec 확장:
  - `prior_estimation` 섹션 추가
    - Fermi decomposition hint
    - 참고할 패턴/유사 시장(P-Graph) 목록
- Metric Resolver Prior 단계 구현:
  - Evidence/Derived 후보들의 quality(문자비율/spread 등)가  
    policy 기준 미달일 때만 Prior 단계 호출
  - Belief/LLM 모듈을 이용해 Fermi/유사사례 기반 rough 값 생성
- 품질 프로파일 정의/적용
  - `reporting_strict`, `decision_balanced`, `exploration_friendly`
  - 각각 min_literal_ratio / max_spread_ratio / allow_prior 등을 설정

**실사용 / 피드백**

- 데이터가 희박한 상황의 질문:
  - “아직 초창기인 새 시장의 TAM rough 추정”
- 같은 질문을 서로 다른 policy 모드로 실행:
  - exploration 모드에서 얼마나 과감해지는지
  - reporting 모드에서 어디서 stop하는지
- 피드백:
  - Prior를 너무 빨리/늦게 쓰는지
  - 사람이 볼 때 “이건 너무 비약이다” 싶은 패턴은 무엇인지

---

## Phase 3 – Pattern + Opportunity 루프 (Sprint 6–7)

### Sprint 6: PatternGraph v0 + PatternEngine v0 + Trait 기반 매칭

**목표**

- POC 도메인에 대해서 3–5개 패턴을 정의하고,  
  R-Graph + Trait 기반 패턴 매칭/유사도 평가까지 구현합니다.

**작업**

- 패턴 정의
  - `SaaS_like_model`
  - 도메인 특화 패턴 2–3개 (예: “사교육_학원형”, “사교육_과외형”, “플랫폼형” 등)
- PatternGraph 스키마 구현, 패턴 등록
- PatternEngine v0:
  - R-Graph Actor/State/Traits를 기반으로  
    “이 Actor/business가 어떤 패턴에 얼마나 가까운지” 유사도 산출
- Gap detection v0:
  - Trait 공간에서 “패턴이 구조적으로 들어갈 수 있는데 현재 없는 자리” rough 탐지

**실사용 / 피드백**

- 실제 질문 예시:
  - “이 도메인에서 SaaS-like/플랫폼-like 패턴이 꽂힐 수 있는 지점은 어디인가?”
- 스프린트 마지막:
  - 사람(도메인 전문가)이 생각한 “패턴 적용 가능 포인트”와  
    시스템이 찾은 위치를 비교
- 피드백:
  - Trait 정의의 부족/과잉
  - Pattern 제약 조건의 너무 빡셈/너무 느슨함

---

### Sprint 7: Opportunity Discovery v1 – Pattern + Value 결합

**목표**

- PatternEngine과 ValueEngine을 묶어  
  **기회 후보(OPP) 카드**를 생성하는 최소 기능 구현.

**작업**

- `opportunity_discovery` canonical workflow 구현:
  - WorldEngine.snapshot  
  → PatternEngine.discover_gaps  
  → ValueEngine.evaluate_metrics(rough size metrics)
- OPP 카드 스키마 정의:
  - 어떤 패턴/구조에 기반한 기회인지
  - Rough 목표 Metric (TAM, ARPU, LTV 등)
  - 주요 가정/리스크/레버
- 기회 랭킹 로직 v0:
  - 예상 규모 × 패턴 적합도 × (불확실성 패널티)

**실사용 / 피드백**

- 실제 질문 예시:
  - “이 도메인에서 새 비즈니스 기회 후보 3개만 보여줘”
- 스프린트 마지막:
  - 사람(Explorer/전략가)이 만든 OPP vs 시스템이 제안한 OPP 비교:
    - 새로운 통찰 제공 여부
    - “그냥 상식적인 이야기만 반복하는지” 여부
- 피드백:
  - OPP 카드에 반드시 있어야 하는 필드/불필요한 필드
  - 기회 랭킹 기준 조정 필요성

---

## Phase 3.5 – Project Context + Brownfield 지원 (Sprint 7.5, 2025-12-05 추가)

### Sprint 7.5: Project Context Layer v0 + PH00 Phase 구현

**목표**

- Brownfield/Greenfield 모두를 지원하기 위한 Project Context Layer 구현
- PH00 Phase (프로젝트 컨텍스트 설정) 최소 버전 구현
- structure_analysis_for_project 워크플로우 동작 검증

**작업**

- Project Context 스키마 구현
  - `project_context_store` (umis_v9.yaml에 이미 정의됨)
  - focal_actor_id, baseline_state, assets_profile, constraints_profile, preference_profile
- PH00 Phase 실행기 구현
  - 조직 현황 폼/템플릿
  - 내부 데이터 → Evidence Store 파이프라인
  - Capability → Trait 매핑 헬퍼
  - focal_actor R-Graph 구성
  - Project Context 객체 생성
- PatternEngine 확장
  - structure_fit_score (기존) + execution_fit_score (신규) 계산
  - capability_traits 매칭 로직
- ValueEngine 확장
  - project-level Metric 정의 (MET-SOM_for_project, MET-Base_Revenue_for_project 등)
  - project_context_id 인자 처리

**실사용 / 피드백**

- 실제 시나리오 3가지로 테스트:
  - Greenfield: EdTech 스타트업 (examples/project_context_examples.yaml#example_1)
  - Brownfield: 오프라인 학원 체인 (examples/project_context_examples.yaml#example_2)
  - Hybrid: 글로벌 플랫폼 한국 진입 (examples/project_context_examples.yaml#example_3)
- 스프린트 마지막에:
  - 같은 시장(Adult Language KR)에 대해
    - Greenfield 분석 vs Brownfield 분석 결과를 비교
    - "실행 가능한 기회"가 어떻게 달라지는지 확인
- 피드백:
  - Project Context 입력이 너무 복잡한지
  - capability_traits 매핑이 직관적인지
  - execution_fit_score 계산이 합리적인지

**성공 기준**

- PH00 Phase를 실행하여 PRJ-* 생성 가능
- structure_analysis_for_project 워크플로우 end-to-end 실행
- PatternEngine이 structure_fit + execution_fit 이중 점수 반환
- 같은 시장에 대해 조직별로 다른 기회 우선순위 제시

---

## Phase 4 – Strategy + Outcome 루프 (Sprint 8–9)

### Sprint 8: DecisionGraph v0 + StrategyEngine v0

**목표**

- 최소한의 전략/시나리오 표현 구조(D-Graph)와  
  전략 평가 루프(StrategyEngine v0)를 만든다.

**작업**

- D-Graph 스키마 구현:
  - Goal / Hypothesis / Strategy / Scenario / Action 최소 정의
- StrategyEngine v0:
  - Goal + 제약(예산, 리스크 한도 등)을 입력받아  
    전략 템플릿 2–3개를 조합해 Strategy 후보 생성
  - Strategy별 Scenario(보수적/기본/공격적) 정의  
  → 각 Scenario에 대해 ValueEngine에 Metric 평가 요청
- 포트폴리오 평가 v0:
  - 전략별 결과를 합쳐 간단한 “효용/리스크 프로파일” 생성

**실사용 / 피드백**

- 실제 질문 예시:
  - “이 구독형 피아노 서비스 기회를 공략하는 전략 A/B의 3년 뒤 MRR, CAC 회수기간, 리스크 비교”
- 스프린트 마지막:
  - 사람이 전통 방식(엑셀/슬라이드)으로 만든 전략 A/B 비교 vs  
    UMIS v9가 생성한 전략 A/B 비교를 비교
- 피드백:
  - 어떤 가정은 시스템에 넣기 어렵고 사람 머리에만 있는지
  - D-Graph 구조/표현의 불편함

---

### Sprint 9: LearningEngine v0 + Reality Monitor 루프

**목표**

- 실제 Outcome 데이터를 넣고  
  “예측 vs 실제”를 비교하며 Belief/패턴/Metric을 업데이트하는 최소 루프를 만든다.

**작업**

- outcome_store 스키마 및 입력 파이프라인
  - 전략/Scenario별 Outcome(실제 매출/고객/Churn 등)을 기록하는 최소 구조
- LearningEngine v0:
  - 예측 ValueRecord vs Outcome 비교
  - Metric Prior 분포/패턴 성능 메타 업데이트
- Reality Monitor Role을 위한 기본 리포트:
  - “지난 N개월 동안의 전략/기회에 대한 예측 vs 실제 요약”
  - “어떤 Metric/패턴이 일관되게 bias가 있는지”

**실사용 / 피드백**

- 실제로 한두 개 전략/실험을 실행하고:
  - UMIS v9가 준 예측 vs 실제를 비교,
  - “다음 번 같은 질문에서 어떤 점이 달라졌는지” 확인
- 피드백:
  - 어떤 종류의 오차는 학습으로 줄어드는지
  - 어떤 종류는 구조/패턴 자체를 바꿔야 줄어드는지

---

## Phase 5 – 멀티도메인 / 플랫폼화 (Sprint 10+)

### Sprint 10–11: 두 번째 도메인 온보딩

**목표**

- 완전히 다른 도메인(예: Logistics, Marketplace, Healthcare 등)에  
  v9를 적용해 **온톨로지/엔진의 범용성**을 검증합니다.

**작업**

- 두 번째 도메인 선택
- 이 도메인에 맞는 Trait/Pattern/Metric 일부 추가 정의
- 기존 R/P/V/D 구조와 Engine을 그대로 두고,  
  얼마나 적은 수정으로도 이 도메인을 커버할 수 있는지 테스트

**실사용 / 피드백**

- 실제 질문 예시:
  - “한국 라스트마일 물류 시장 구조와 기회?”,  
    “새로운 fulfillment 패턴의 전략 효과?” 등
- 피드백:
  - Ontology/Trait가 얼마나 재사용 가능한지
  - 도메인 특화 패턴/Metric이 어디까지 공통화 가능한지

---

### Sprint 12+: UI/UX / API / Ops·품질 체계

**목표**

- 사람/팀이 UMIS v9를 편하게 쓰도록 **제품화 레이어**를 정리합니다.

**작업**

- UI/UX
  - Structure Analyst/Explorer/Strategist에게 필요한 대시보드/리포트 설계
  - R/P/V/D 그래프를 “사람 눈에 보기 좋은 뷰”로 변환하는 구성 요소들
- API
  - 외부 서비스/내부 툴에서 UMIS v9를 호출할 REST/GraphQL API 설계
- Ops/품질
  - 로그/모니터링/알람
  - 회귀 테스트(같은 질문에 대해 새로운 코드가 결과를 어떻게 바꾸는지 확인하는 테스트)
  - 도메인별/전략별 “예측 정확도/설명력”을 트래킹하는 품질 지표

---

## 사유 공개 (Reasoning Transparency)

### 가정

- 스프린트는 2주 단위로 진행하며,
  **각 스프린트 말에 최소 1회 “실제 질문을 풀어보고 피드백 받는 세션”**이 있다고 가정했습니다.
- 초기에는 1개 도메인(PoC 도메인)에 집중해 vertical slice를 만드는 것이  
  가장 리스크가 낮다고 보았습니다.
- v7/v8 자산(Estimator, RAG, KG, Metric/Pattern YAML 등)은  
  버리는 것이 아니라, v9에서 비교 기준/데이터 소스/파싱 규칙/프롬프트 등으로 재활용 가능합니다.

### 근거

- v7에서는 6-Agent, 4-Layer RAG, Estimator 4-Stage 등 복잡한 구조가 이미 존재했지만,  
  현실 문제를 end-to-end로 풀면서 구조를 느리게/조심스럽게 바꾸는 데 어려움이 있었습니다.  [oai_citation:0‡UMIS_ARCHITECTURE_BLUEPRINT.md](sediment://file_000000002d44720984a75c9384b8ac54)  
- v8은 ValueEngine/MetricSpec/Planes로 승격하면서 구조적 단순화에 성공했지만,  
  여전히 Reality/Pattern/Decision 축까지 OS 레벨로 끌어올리지는 못했습니다.  [oai_citation:1‡UMIS_ARCHITECTURE_BLUEPRINT_v8.md](sediment://file_00000000b0d872099a2d4bb0d53c6df8)  
- 지금까지의 논의에서:
  - Reality Graph 부재
  - Ontology lock-in 위험
  - on-demand Evidence + Metric Resolver 필요
  - Pattern/Strategy/Outcome 루프 중요성  
  이 반복해서 제기되었습니다.

### 추론 경로

1. **엔진 우선 구현**(EvidenceEngine → ValueEngine → PatternEngine…)처럼  
   기술 기능만 순서대로 만들면,  
   정작 “질문을 실제로 풀어보는 경험”이 뒤로 밀려 v9 철학이 흐려질 위험이 있습니다.
2. 반대로 **도메인만 끝까지 파는** 스타일(B2B SaaS를 완전 지원한 다음 Logistics…)은  
   도메인별 특수 설계가 쌓여 OS로서의 통일성이 깨질 위험이 있습니다.
3. 그래서:
   - Reality → Value → Pattern → Strategy+Outcome  
     네 개의 “학습 루프”를 순차적으로 여는 방향으로 스프린트를 설계했습니다.
   - 각 루프는:
     - 최소 기능
     - 실제 질문
     - v7/수동 방식과의 비교  
     를 포함해, 설계가 현실에 맞게 수렴하게 합니다.
4. 마지막 Phase에서 두 번째 도메인을 추가하는 이유는,  
   v9 구조가 **특정 도메인에만 맞는 특수 설계**가 아니라  
   진짜 “Universal Market OS”로 작동하는지 검증하기 위함입니다.

### 대안

- **기능 단위 스프린트**  
  - EvidenceEngine → ValueEngine → PatternEngine → StrategyEngine…  
  - 장점: 각 엔진이 빠르게 완성되는 느낌을 줄 수 있음.  
  - 단점: 실제 end-to-end 문제 해결과의 연결이 늦게 드러나,  
    설계가 현실과 어긋나기 쉬움.
- **도메인 단위 스프린트**  
  - 도메인 A를 완전히 끝까지 → 도메인 B…  
  - 장점: 특정 도메인 깊이는 보장.  
  - 단점: OS/플랫폼 관점에서 재사용성·통일성이 쉽게 깨짐.

여기 제안한 로드맵은  
**“엔진 축”과 “도메인 축”을 동시에 조금씩 전진시키는 절충안**입니다.

### 리스크

- 스프린트마다 “실사용/피드백”을 넣으면  
  **시간/일정 압박**이 생길 수 있습니다.  
  하지만 UMIS v9의 철학상, 이걸 줄이면 장기적으로 더 큰 리스크를 떠안게 됩니다.
- 초기 Ontology/Trait/MetricSpec를 자주 바꾸게 될 가능성이 높습니다.
  - 이건 어느 정도 감수해야 하는 비용이지만,  
    스프린트마다 변경 범위를 제한하는 룰을 두는 게 좋습니다.
- EvidenceEngine/MetricResolver/WorldEngine/PatternEngine 간 책임 분리가  
  구현 과정에서 다시 흐려질 위험이 있습니다.
  - 각 엔진의 “할 일/하지 말아야 할 일”을 문서/테스트로 명확히 하는 게 중요합니다.

### 검증

- 각 Phase 종료 시점(특히 Phase 2, 3, 4 끝)에  
  **실제 프로젝트 하나를 UMIS v9 vertical slice로만 끝까지 수행해 보는 것**을 목표로 잡는 것이 좋습니다.
  - 예: “한국 피아노 레슨 구독 모델 기회 분석 및 전략 제안”
- 이 프로젝트 결과를 v7 + 엑셀 + 슬라이드 조합과 비교해:
  - 구조 표현력
  - 반복 가능성
  - 설명력
  - 작업 시간/노동 강도  
  를 평가하면, v9 설계가 제대로 목적에 수렴하고 있는지 잘 보일 것입니다.
---

## Phase 1.5 보충: Project Context Layer 통합 (2025-12-05 추가)

### 목표

Brownfield/Greenfield 모두 지원하기 위한 Project Context Layer를 Phase 1-2와 Phase 3 사이에 끼워넣습니다.

### Sprint 2.5: Project Context Layer 기반 구축

**작업**:
- umis_v9.yaml 확장 완료 ✅
  - project_context_store 스키마
  - capability_traits (9개 Trait)
  - Engine API project_context_id 인자
- umis_v9_process_phases.yaml PH00 추가 ✅
- Project Context 입력 예시 3가지 ✅
- PH00 실행 템플릿 작성
- WorldEngine.ingest_project_context() 구현

**실사용**:
- 실제 회사 2-3개 Project Context 작성
- Greenfield/Brownfield 시나리오 각 1개씩 테스트

### Sprint 6-7 확장: execution_fit_score 구현

**Phase 3 Sprint 6-7에 추가**:
- PatternEngine:
  - structure_fit_score (기존)
  - execution_fit_score (신규, capability_traits 매칭)
- ValueEngine:
  - project-level Metric 구현
    - MET-SOM_for_project
    - MET-Base_Revenue_for_project
    - MET-Delta_Revenue_for_project

