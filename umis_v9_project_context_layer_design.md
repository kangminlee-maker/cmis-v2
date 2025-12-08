# UMIS v9: Project Context Layer  
사용자 상황을 반영하는 Brownfield-Aware Market OS 설계안

---

## 0. 문서 목적

이 문서는 UMIS v9 기존 아키텍처(Reality / Pattern / Value / Decision Graph, 4 Planes, 14-Phase 구조 분석 워크플로우)를 유지하면서,

> “사용자(조직)가 **지금 어떤 위치에 서 있는지**를 일급 개념으로 표현하고,  
> 그 위에서 기회 발굴과 전략 설계를 수행할 수 있도록 하는  
> `Project Context` 레이어”

를 설계하는 데 목적이 있습니다.

기존 v9는 특정 시장/도메인에 대해 “세계가 어떻게 생겼는가?”를 매우 잘 표현합니다.  
여기에 **“그 세계 안에서 나는 어디에 있고, 무엇을 가지고 있으며, 무엇을 원하고, 어떤 제약을 갖는가?”**를 정식 모델로 올려서 Brownfield/Greenfield 모두를 다루는 OS로 완성하는 것이 이 문서의 방향입니다.

---

## 1. 문제 정의 – “시장만 아는 OS” vs “나를 아는 OS”

### 1.1 현재 v9의 강점

- `umis_v9.yaml`에서  
  - Reality Graph(R-Graph): Actor / Event / MoneyFlow / State …  
  - Pattern Graph(P-Graph): Pattern / Pattern Family / Context Archetype  
  - Value Graph(V-Graph): Metric / ValueRecord / Parameter  
  - Decision Graph(D-Graph): Goal / Hypothesis / Strategy / Scenario / Action  
  이 명확하게 정의되어 있습니다.
- `UMIS_v9_Architecture_Blueprint_v9.md`에서  
  - Interaction / Role / Substrate / Cognition 4 Plane과  
  - Evidence/World/Pattern/Value/Strategy/Learning/Policy Engine 구조가 정리되어 있습니다.
- `UMIS_v9_Structure_Analysis_Detailed_Workflow.md`에서는  
  - “한국 성인 어학교육 시장 구조 분석”을 예시로,  
  - Needs → BM → Domain → Player → 가치사슬 → Market Size → 경쟁/집중도 → 검증 → 리포트에 이르는 14 Phase가 잘 정의돼 있습니다.

즉, v9는 **“시장 현실을 OS 수준에서 모델링하는 능력”**을 이미 확보하고 있습니다.

### 1.2 현재의 공백: 사용자/조직의 상황

기회 발굴과 전략 설계는 **항상 특정 행위자(회사/조직)**의 입장에서 수행됩니다.

- 같은 시장에서도:
  - 오프라인 학원 체인,
  - 글로벌 디지털 스타트업,
  - 이미 인접 시장을 지배하고 있는 대기업  
  은 **전혀 다른 기회/전략 세트**를 가져야 합니다.
- Brownfield:
  - 기존 사업/자산/채널/조직 구조/브랜드가 이미 깔려 있음.
  - “시장 전체에서 가장 좋은 전략”과  
    “우리가 당장 현실적으로 취할 수 있는 전략”이 다를 수밖에 없습니다.
- Greenfield:
  - “지금은 아무 것도 없지만, 자본/인력/기술/브랜드는 이런 수준”이라는 의미에서 역시 컨텍스트가 필요합니다.

현재 v9의 canonical_workflow(`structure_analysis`, `opportunity_discovery`, `strategy_design`)는 입력으로 `domain_id / region / segment` 정도만 받고 있으며,  
**특정 사용자/조직의 현재 위치와 제약을 구조적으로 표현하는 레이어는 비어 있습니다.**

그 결과:

- 같은 Adult Language 시장에 대해
  - 오프라인 학원 체인,
  - 디지털 플랫폼 스타트업  
  두 입장에서 분석을 한다 해도,  
  시스템 입장에서는 “같은 시장”만 보게 됩니다.
- Brownfield/Greenfield 차이는 분석자 머릿속에만 존재하고,  
  엔진/그래프에는 반영되지 않습니다.

이 공백을 메우는 것이 `Project Context` 설계의 목표입니다.

---

## 2. 설계 목표

`Project Context` 레이어는 다음 요구사항을 만족해야 합니다.

1. **Brownfield/Greenfield 모두 표현 가능**
   - 기존 사업/자산/관계망이 깔려 있는 Brownfield,
   - 거의 백지 상태인 Greenfield,
   - 일부 인접 도메인에서만 사업을 하고 있는 Hybrid까지.
2. **R/P/V/D와 자연스럽게 연결**
   - 사용자는 R-Graph의 Actor(회사/조직) 중 하나로 표현.
   - 사용자의 목표/전략/제약/선호는 D-Graph 및 별도 Context로 표현.
   - 패턴/기회/전략/값 계산이 항상 “시장 + 나”를 함께 고려하도록.
3. **기존 아키텍처를 깨지 않을 것**
   - R/P/V/D 그래프 자체를 갈아엎지 않는다.
   - 새로운 거대 그래프를 추가하지 않고,  
     Substrate/Decision/Engine 쪽에 “얇은 레이어”로 삽입.
4. **멀티 프로젝트/멀티 도메인 확장 가능**
   - 한 회사가 여러 시장/전략 프로젝트를 동시에 진행할 수 있고,
   - 하나의 시장 R-Graph가 여러 회사의 컨텍스트에 재사용되어야 한다.
5. **엔진 레벨에서 일관되게 사용**
   - PatternEngine: 구조적 적합도 vs 실행 가능성.
   - ValueEngine: 전체 파이 vs “내가 먹을 수 있는 파이”.
   - StrategyEngine: 이론적 전략 공간 vs 내 제약을 고려한 실행 가능한 전략 공간.

---

## 3. 핵심 개념: Project Context

### 3.1 정의

> **Project Context**  
> = 특정 조직/사용자가, 특정 시장/도메인에 대해,  
> 어떤 출발점과 자산/제약/선호/목표를 가지고 있는지를 표현하는  
> **일급 객체(First-class object)**

논리적으로,

- “이 프로젝트에서 **우리가 누구인지**”
- “어떤 시장을 대상으로 하는지”
- “현재 어떤 사업/지표/자산이 있고”
- “어떤 제약과 우선순위를 갖는지”

를 한 번에 담는 구조입니다.

### 3.2 최소 스키마 (개념 레벨)

Substrate Plane의 `stores` 아래에 `project_context_store`를 추가하는 형태로 설계합니다.

(개념 스케치 – 실제 YAML은 별도 파일로 정의)

- project_context_id
  - PRJ- 프리픽스를 갖는 ID
- focal_actor_id
  - R-Graph의 Actor ID (해당 조직/사용자)
- scope
  - domain_id, region, segment, time_horizon 등
- baseline_state
  - 현재 지표(매출/고객 수/채널별 구조 등)와 주요 State 요약
- assets_profile
  - 채널(온라인/오프라인), 브랜드 파워, 기술 스택, 인력/조직 역량, 데이터 자산 등
- constraints_profile
  - 예산, 리스크 허용도, 타임라인, 규제/지배구조 제약, 조직 문화상 금기 등
- preference_profile
  - 성장 vs 수익, 손익분기 시점 선호, 지역/채널/고객군 선호, 리스크 성향 등
- mode
  - "greenfield" / "brownfield" / "hybrid"
- related_goal_ids
  - 이 프로젝트 컨텍스트와 직접 연결된 Goal ID 목록
- metadata
  - 기타 자유 메타데이터

이렇게 보면 Project Context는

- “R-Graph에서 **우리 회사 Actor**를 가리키는 포인터” +  
- “이 프로젝트의 목표/상황에 특화된 속성”

의 조합이라고 볼 수 있습니다.

---

## 4. R/P/V/D와의 통합 구조

### 4.1 Reality Graph (R-Graph) – “시장 + 나의 자리”

R-Graph에는 이미 Actor/State/MoneyFlow 등의 구조가 있으므로,

- 사용자/조직은 **단순히 하나의 Actor**로 표현됩니다.
  - kind: "company"
  - traits:  
    - domain_id, industry_portfolio, org_stage, digital_maturity 등

Project Context는 이 Actor를 `focal_actor_id`로 참조하고,

- baseline_state: 이 Actor와 관련된 State/Metric/Outcome 요약
- assets_profile / constraints_profile:  
  R-Graph의 서브그래프 + 추가 메타데이터의 압축 버전

World Engine에는 다음과 같은 확장이 들어갑니다.

- `snapshot(as_of, scope, project_context_id=None)`
  - project_context_id가 없으면:  
    기존처럼 “시장 전체 Reality” 서브그래프 반환
  - project_context_id가 있으면:
    - scope에 해당하는 시장 서브그래프 +
    - focal_actor_id 및 그 주변 서브그래프(기존 사업/고객/채널/파트너 등)를 포함한 확장 스냅샷 반환

이렇게 하면 **동일한 R-Graph 위에 “시장 전체 Reality + 클라이언트 Reality”가 같이 얹히는 구조**가 됩니다.

### 4.2 Pattern Graph (P-Graph) – 구조적 적합도 vs 실행 가능성

기존 PatternGraph는 “시장 구조 입장에서 패턴이 맞는가?”만 평가했습니다.

Project Context를 넣으면 패턴에 두 가지 차원의 점수를 줄 수 있습니다.

1. structure_fit_score  
   - “이 패턴이 시장 구조에 맞는가?”
   - 기존 PatternEngine이 하는 일과 거의 동일.

2. execution_fit_score  
   - “이 패턴을 **이 회사가** 실행할 수 있는가?”
   - Project Context의 assets_profile / constraints_profile / mode를 사용.

패턴 스펙은 다음과 같은 필드를 추가로 갖게 됩니다.

- constraints.required_traits
  - R-Graph primitive(Actor/State/MoneyFlow)의 Trait 제약
- constraints.required_capabilities
  - 프로젝트를 수행하기 위한 조직/기술/채널 역량
- constraints.incompatible_traits
  - 이 패턴과 양립하기 어려운 Trait

PatternEngine는 호출 시 `project_context_id`를 선택적으로 인자로 받아,

- structure_fit_score: R-Graph vs Pattern 구조 매칭
- execution_fit_score: Project Context vs Pattern 제약 매칭

을 동시에 계산합니다.

결과적으로,

- 구조적으로 매력적이지만 실행이 어려운 패턴,
- 구조+실행 모두 적합한 패턴,
- 구조는 맞지만 이 회사에겐 전략적으로 의미가 적은 패턴

을 구분해 랭킹할 수 있습니다.

### 4.3 Value Graph (V-Graph) – 전체 파이 vs “내 파이”

기존 ValueEngine은 “시장 전체” 관점에서 Metric을 계산/추정합니다.

Project Context를 추가하면 Metric은 두 레벨로 나뉩니다.

1. 시장 레벨 Metric
   - `MET-TAM`, `MET-SAM`, `MET-Revenue`, `MET-HHI_revenue` 등
   - context: domain_id / region / year …

2. 프로젝트 레벨 Metric
   - `MET-SOM_for_project`, `MET-Reach_for_project`,  
     `MET-Base_Revenue_for_project`, `MET-Scenario_Revenue_for_project` 등
   - context: project_context_id + domain_id / region / year …

MetricSpec에 `context_requirements.level = market / project`와 같이 표현하면,

- ValueEngine은 `project_context_id`가 필요한 Metric과 그렇지 않은 Metric을 구분해 처리할 수 있습니다.
- 예:
  - `MET-SAM`: market level (project_context_id 없어도 계산)
  - `MET-SOM_for_project`: project level (project_context_id 없으면 fail)

또한 Project Context는 `baseline_state`를 통해

- 현재 매출 / 고객 수 / 마진 구조 / 채널 믹스 등  
  “현 상태”를 담고 있으므로,

ValueEngine은

- Baseline Metric: 현재 값
- Scenario Metric: 특정 Strategy/Scenario 하에서의 예상 값
- Delta Metric: Scenario – Baseline

을 프로젝트별로 계산할 수 있습니다.

### 4.4 Decision Graph (D-Graph) – Goal과 Project Context의 연결

Decision Graph에 Project Context를 연결하면, Goal/Strategy/Scenario가 “시장 전체”가 아니라 “이 프로젝트”에 귀속됩니다.

Goal 노드에 다음 필드를 추가합니다.

- project_context_id (optional)

이렇게 하면,

- “Adult Language KR 시장 전체에서의 전략 목표” (project_context_id 없음)와
- “특정 회사의 Adult Language KR 진입 목표” (project_context_id 있음)를  
  명확히 구분할 수 있습니다.

StrategyEngine은

- `search_strategies(goal_id, constraints, project_context_id=None)` 형태로 API를 확장해,
- project_context_id가 주어졌을 때:
  - Project Context의 constraints_profile을 즉시 반영하고,
  - PatternEngine의 execution_fit_score를 전략/패턴 조합의 스코어에 반영합니다.

---

## 5. 엔진별 Project Context 통합 설계

### 5.1 Evidence Engine

Evidence Engine 자체는 “시장/회사/프로젝트” 구분을 크게 신경 쓰지 않아도 됩니다.  
다만, Project Context 생성/업데이트 시 다음 역할이 추가될 수 있습니다.

- 내부 데이터(ERP/CRM/재무 DB 등)를 Evidence로 받아,
  - `source_tier: "curated_internal"`로 Evidence Store에 저장.
- WorldEngine이 이 Evidence를 통해 focal_actor의 Reality를 업데이트하도록 지원.

결과적으로 Project Context의 baseline_state는

- 외부공시/리포트
- 내부 데이터(Evidence)
- 분석자의 수동 입력/추정(ASM/EST)

로부터 구성됩니다.

### 5.2 World Engine

WorldEngine의 핵심 변화는 두 가지입니다.

1. `snapshot` API 확장

   - 기존:
     - snapshot(as_of, scope)
   - 확장:
     - snapshot(as_of, scope, project_context_id=None)

   project_context_id가 주어지면:

   - Project Context의 focal_actor_id에 해당하는 Actor 노드 및 인접 구조를 우선적으로 포함.
   - baseline_state에서 참조하는 Metric/State/Outcome 정보에 기반해 R-Graph를 보완.

2. `ingest_project_context` 유틸리티

   - Project Context 생성/업데이트 시,
   - 이 Context에 담긴 baseline 지표/상태를 R-Graph로 투영하는 작업을 수행.

이를 통해 “시장 Reality + 클라이언트 Reality”가 한 그래프 안에서 결합됩니다.

### 5.3 Pattern Engine

PatternEngine는 다음과 같이 확장됩니다.

- 입력: graph_slice_ref, project_context_id(optional)
- 출력: pattern_match_set
  - 각 PatternMatch에
    - structure_fit_score
    - execution_fit_score
    - reasoning (둘의 근거) 포함

execution_fit_score는 주로 다음을 참조합니다.

- project_context.assets_profile.capabilities / channels / tech_stack
- project_context.constraints_profile.budget / timeline / risk_appetite
- project_context.mode (brownfield / greenfield / hybrid)

이 점수는

- Opportunity Discovery에서 “어떤 패턴 기반 기회를 우선 추천할지”,
- Strategy Design에서 “어떤 전략이 이 회사에 현실적인지”를 정렬하는 핵심 입력입니다.

### 5.4 Value Engine

ValueEngine 확장은 크게 세 부분입니다.

1. Metric Request에 project_context_id 포함 가능
   - MetricSpec의 context_requirements에 따라,
   - market level / project level Metric을 구분하여 처리.

2. Project-aware Metric 정의
   - 예시:
     - `MET-reachable_share_for_project`
       - SAM 대비 이 회사가 현실적으로 도달 가능한 점유율
       - Pattern, assets_profile, constraints_profile를 반영
     - `MET-SOM_for_project`
       - `MET-SAM × MET-reachable_share_for_project`로 추정
     - `MET-Base_Revenue_for_project`
       - Project Context baseline_state로부터 읽어옴
     - `MET-Scenario_Revenue_for_project`
       - 특정 Strategy/Scenario 하에서 ValueEngine이 계산
     - `MET-Delta_Revenue_for_project`
       - 시나리오 Revenue – Baseline Revenue

3. Metric Resolver Prior 단계에서 Project Context 활용
   - 데이터가 부족한 경우,
   - 동일/유사 패턴의 다른 시장 사례(P-Graph)를 참고하는 것 외에,
   - “이 회사의 기존 실적/역량/채널”을 Prior로 활용하여  
     조금 더 현실적인 추정치를 생성.

이렇게 하면 “단순히 시장 전체가 얼마나 크냐”에서 끝나지 않고,

- “이 회사가 현실적으로 가져갈 수 있는 파이”,
- “기존 사업 대비 incremental value”

까지 정량화할 수 있습니다.

### 5.5 Strategy Engine

StrategyEngine은 Goal/Pattern/Value/R-Graph를 기반으로 전략 후보를 탐색합니다.

Project Context를 넣으면:

- 입력: goal_id, constraints, project_context_id(optional)
- 동작:
  1. Goal에 project_context_id가 연결되어 있지 않더라도,
     - 입력 인자로 받은 project_context_id를 통해  
       해당 프로젝트의 제약/자산/선호를 불러옴.
  2. PatternEngine의 structure_fit_score / execution_fit_score를 조합해,
     - “시장 구조에는 맞지만 이 회사에겐 무리인 전략”
     - “시장/회사 둘 다에 잘 맞는 전략”
     을 구분하고 랭킹.
  3. ValueEngine에 project-aware Metric Request를 발행해,
     - 각 전략/시나리오마다 `Base vs Scenario vs Delta` 지표를 비교.

최종적으로 StrategyEngine은

- 전략 후보 리스트(STR-*)
- 각 전략별 시나리오(보수적/기본/공격적 등)
- 각 전략/시나리오마다
  - SOM_for_project
  - 3년 뒤 MRR / FCF / Payback
  - 주요 리스크 및 조직 부담도

를 제공할 수 있게 됩니다.

---

## 6. 워크플로우 관점 통합: PH00 + *_for_project

### 6.1 PH00: Project Context Setup (새 Phase)

`UMIS_v9_Structure_Analysis_Detailed_Workflow.md`에는 PH01~PH14가 정의되어 있습니다.  
여기에 PH00을 추가하여, 구조 분석이 항상 “프로젝트 컨텍스트” 위에서 시작되도록 할 수 있습니다.

PH00의 목표:

- 사용자/조직의 현재 상태/자산/제약/선호를 구조화하여  
  `project_context_store`와 R-Graph에 반영.

입력:

- 사용자/조직 인터뷰 / 설명
- 내부 데이터(있다면)
- 기존 리포트/문서 (Evidence로 취급)

역할:

- Structure Analyst (주도)
- 필요시 Numerical Modeler / Reality Monitor 보조

주요 활동:

1. 사용자 인터뷰/폼 기반 입력
   - “현재 어떤 사업을 어디서 하고 있는지”
   - “어떤 채널/조직/기술 자산을 가지고 있는지”
   - “예산/리스크/타임라인은 어떠한지”
2. 내부 데이터 수집 요청
   - Reality Monitor에게 data_collection_request 발행
   - EvidenceEngine이 내부 시스템/파일을 Evidence로 저장
3. WorldEngine을 통해 R-Graph에 focal_actor 및 서브그래프 구성
4. Project Context 객체 생성
   - project_context_id 발급
   - focal_actor_id, scope, baseline_state, assets_profile, constraints_profile, preference_profile 채우기

산출물:

- PRJ-* Project Context 레코드
- ACT-CLIENT-* Actor 노드 및 관련 R-Graph 구조
- Baseline Metric 몇 개 (현재 매출/고객 수/주요 BM/도메인 등)
- PH01 이후 단계에서 사용할 reference (project_context_id)

### 6.2 structure_analysis_for_project

기존 `structure_analysis`는 “시장 구조” 관점이라면,  
`structure_analysis_for_project`는 “시장 구조 + 나의 현재 위치” 관점입니다.

입력:

- domain_id, region, segment
- project_context_id

단계:

1. PH00에서 생성한 project_context_id를 기반으로
   - WorldEngine.snapshot(as_of, scope, project_context_id) 호출
2. R-Graph에서 focal_actor와 주변 구조를 강조한 맵을 생성
3. PatternEngine.match_patterns(graph_slice_ref, project_context_id)
   - 현재 회사가 어떤 패턴 위에 서 있는지, 어떤 패턴에 가깝지만 아직 구현되지 않았는지
4. ValueEngine.evaluate_metrics
   - 시장 레벨 Metric + 프로젝트 레벨 Baseline Metric을 함께 계산
5. 구조 분석 리포트에
   - “시장 전체 구조”와 함께
   - “현재 회사의 포지션/강점/약점/기회 공간”을 표현

### 6.3 opportunity_discovery_for_project

기존 `opportunity_discovery`는 시장 구조/패턴 기반 기회를 찾습니다.  
`opportunity_discovery_for_project`는 Project Context를 추가로 사용합니다.

입력:

- domain_id, region, segment
- project_context_id

단계:

1. WorldEngine.snapshot(..., project_context_id)
2. PatternEngine.discover_gaps(graph_slice_ref, project_context_id)
   - structure_fit_score / execution_fit_score를 함께 계산
3. ValueEngine.evaluate_metrics
   - 시장 레벨 Metric (TAM/SAM 등)
   - 프로젝트 레벨 Metric (SOM_for_project, Delta 가능성 등)
4. Context-aware 랭킹
   - “구조적으로 매력 + 실행 용이” 기회 우선
   - “구조적으로 매우 매력 + 실행 난이도 높음” 기회는 별도 카테고리로

산출:

- OPP 카드: 각 기회에 대해
  - 관련 패턴/Structure Fit / Execution Fit
  - 예상 규모/TAM/SOM_for_project
  - 주요 가정/리스크
  - 요구 역량/투자/타임라인

### 6.4 strategy_design_for_project

`strategy_design`에 project_context_id를 추가하면,  
같은 Goal이라도 Project Context에 따라 전략 후보가 달라집니다.

입력:

- goal_id (project_context_id와 연결)
- 또는 goal_id + project_context_id

단계:

1. StrategyEngine.search_strategies(goal_id, constraints, project_context_id)
   - execution_fit_score / constraints_profile를 활용해 전략 후보 생성/필터링
2. ValueEngine.simulate_scenario(scenario_id, policy_ref, project_context_id)
   - 각 전략 시나리오별 프로젝트 레벨 Metric (Delta Revenue, Payback, Risk 등) 계산
3. 포트폴리오 평가
   - 여러 전략을 조합했을 때의 전체 프로젝트 성과/리스크 프로파일 평가

산출:

- 전략 포트폴리오
  - 각 전략의 Delta Value
  - Base 대비 Payoff
  - 조직/자산 측면에서의 요구사항

---

## 7. 예시: 같은 시장, 다른 Project Context 두 개

### 7.1 공통: Adult Language KR 시장 (기존 POC)

- R-Graph:
  - 성인 학습자, 오프라인 학원 Top-N, 온라인/원격 플랫폼, B2B 교육 제공자 등 Actor
  - MoneyFlow: 개인/기업 → 교육 제공자 → 콘텐츠 제작사 등
- P-Graph:
  - 오프라인 학원형 패턴
  - 온라인 VOD형 패턴
  - 플랫폼형 패턴
- V-Graph:
  - MET-SAM, MET-N_customers, MET-Revenue 등 구현
- D-Graph:
  - 아직 POC 단계에서 Goal/Strategy는 간단한 형태

이 시장에 두 개의 Project Context를 얹어보겠습니다.

### 7.2 Project A: 대형 오프라인 학원 체인 (Brownfield)

- focal_actor_id: ACT-OfflineAcademyGroup
- mode: "brownfield"
- scope:
  - domain_id: Adult_Language_Education_KR
  - region: KR
- baseline_state:
  - existing_revenue: 연 800억 (어학 부문)
  - channel_mix: 오프라인 95%, 온라인 5%
  - margin_structure: Gross Margin 45%, Operating Margin 10%
- assets_profile:
  - nationwide_centers: 120개
  - strong_brand_awareness: high
  - digital_infra_maturity: low-medium
  - sales_organization: large_offline_sales_team
- constraints_profile:
  - max_capex_for_digital: 제한적
  - risk_appetite: medium-low
  - time_horizon: 3년 내 손익 방어
- preference_profile:
  - cash_flow_stability 우선
  - 오프라인 자산 활용 극대화

결과:

- PatternEngine:
  - 플랫폼형/완전 온라인 구독형 패턴
    - structure_fit_score: 높음
    - execution_fit_score: 낮음 (digital_infra, 조직 문화 측면)
  - 오프라인 구독/멤버십 강화 패턴
    - structure_fit_score: 중간
    - execution_fit_score: 매우 높음
- OpportunityDiscovery_for_project:
  - “오프라인 멤버십/패키지 강화 및 하이브리드화” 기회가 상위 랭킹
- StrategyDesign_for_project:
  - 핵심 전략: 오프라인 cash cow 유지 + 점진적 디지털 보완
  - Delta Metric: 기존 오프라인 베이스 대비 LTV/Churn 개선 중심

### 7.3 Project B: 글로벌 디지털 원격 학습 스타트업 (Hybrid/Greenfield)

- focal_actor_id: ACT-RemoteLearningStartup
- mode: "hybrid"
- scope:
  - domain_id: Adult_Language_Education_KR
  - region: KR
- baseline_state:
  - existing_revenue: 해외 시장 구독 매출 300억
  - korea_revenue: 거의 없음
- assets_profile:
  - digital_platform_maturity: high
  - recurring_billing_infrastructure: complete
  - data_driven_growth_experience: strong
  - offline_network: 없음
- constraints_profile:
  - marketing_budget_for_KR: 충분하나 무한하지 않음
  - time_horizon: 5년 내 의미 있는 MRR 확보
  - brand_in_KR: 낮음
- preference_profile:
  - 고성장 전략 선호
  - 장기 LTV 극대화

결과:

- PatternEngine:
  - 온라인 구독형 패턴
    - structure_fit_score: 높음
    - execution_fit_score: 매우 높음
  - 오프라인 학원형 패턴
    - execution_fit_score: 낮음
- OpportunityDiscovery_for_project:
  - “온라인 구독형 Adult Language KR 진입” 기회가 최상위
  - 기존 해외 성공 사례를 패턴/레퍼런스로 사용해 Prior 강화
- StrategyDesign_for_project:
  - 주요 전략: 디지털 only 또는 디지털 first 전략
  - Delta Metric: “한국 시장 incremental MRR/FCF” 중심 평가

같은 R-Graph/V-Graph/P-Graph 위에서,  
`project_context_id`만 달라졌을 뿐인데,

- 기회 후보 목록,
- 전략 후보,
- 우선순위와 위험/보상 프로파일

이 완전히 달라지는 것이 Project Context 설계의 핵심 효과입니다.

---

## 8. 기존 아키텍처와의 정합성

### 8.1 Graph/Store 구조 변화 요약

- Reality/Pattern/Value/Decision Graph 구조는 그대로 유지.
- Substrate Plane에 `project_context_store`만 추가.
- R-Graph에는 “클라이언트 회사” Actor와 관련 노드가 추가되지만,  
  이는 원래 설계에서도 자연스러운 확장입니다.
- Decision Graph의 Goal/Strategy에 `project_context_id` 필드를 추가하는 수준의 변화.

### 8.2 Engine 책임 분리 유지

- WorldEngine: 여전히 Evidence → R-Graph 변환 담당.
- PatternEngine: 패턴 인식/갭 탐지 담당.  
  Project Context는 “추가 스코어링을 위한 입력”일 뿐,  
  구조적 패턴 정의 자체에는 영향을 주지 않음.
- ValueEngine: Metric Resolver 구조는 그대로.  
  MetricSpec에 project-aware Metric을 추가할 뿐.
- StrategyEngine: Goal/Pattern/Value를 이용해 전략을 구성하되,  
  Project Context를 제약/스코어링에 사용하는 역할.

새로운 거대 엔진을 만들지 않고,  
기존 엔진의 API 입력에 `project_context_id`라는 하나의 축을 추가하는 형태입니다.

### 8.3 멀티 프로젝트/멀티 도메인

- 동일한 R-Graph(AdultLanguage_KR)에
  - 여러 Project Context(다수의 회사/프로젝트)를 얹을 수 있음.
- 동일한 회사도
  - 여러 도메인(AdultLanguage_KR, TestPrep_KR, CorporateTraining_KR …)에 대해  
    각각 다른 Project Context를 가질 수 있음.

이 구조 덕분에,

- 시장 Reality 분석 결과를 다양한 프로젝트/조직에 재사용할 수 있고,
- 한 조직의 자산/제약/선호가 여러 도메인에서 어떻게 활용/제약되는지도 비교할 수 있습니다.

---

## 9. 사유 공개 (Reasoning Transparency)

### 9.1 가정

- UMIS v9는 “시장 OS”이자 “의사결정 OS”로 동작해야 하며,  
  실제 사용 시에는 항상 특정 조직/프로젝트의 관점이 존재한다고 가정했습니다.
- 기존 v9의 R/P/V/D 분해 구조와 4 Plane 설계는  
  이미 잘 정립되어 있다고 보고,  
  이를 변경하기보다는 “위에 얇은 컨텍스트 레이어를 얹는 방식”이 더 안전하다고 전제했습니다.

### 9.2 근거

- `umis_v9.yaml`의 `planes`/`substrate_plane`/`cognition_plane` 구조를 보면,  
  시장/패턴/값/결정에 대한 스키마와 엔진은 잘 정의되어 있지만,  
  사용자/조직의 현재 상황을 저장하는 Store는 존재하지 않습니다.
- `UMIS_v9_Architecture_Blueprint_v9.md`에서  
  v9의 대표 질문은 “한국 성인 어학교육 시장 구조/기회/진입전략”이지만,  
  이 역시 특정 조직 관점보다는 시장 관점을 기준으로 설명됩니다.
- `UMIS_v9_Structure_Analysis_Detailed_Workflow.md`의 14 Phase도  
  v7 Market Reality Report를 재현하는 데 초점을 두고 있으며,  
  특정 조직의 자산/제약/선호는 Role/텍스트 레벨에서만 암묵적으로 등장합니다.

### 9.3 추론 경로

1. “사용자/조직 상황을 어디에 넣을까?”라는 질문에 대해,
   - R-Graph에 회사 Actor만 넣는 방식은  
     목표/제약/선호/자산 정보를 표현하기에 부족.
   - 별도 “User Graph”를 만드는 방식은 R/P/V/D 분해 철학을 약화시키고 복잡도를 급격히 올릴 위험이 큼.
2. 따라서,
   - Actor(회사)는 R-Graph의 primitive로 유지하고,
   - 프로젝트별 Goal/자산/제약/선호는 별도 객체로 두되,
   - Substrate Plane의 Store + Decision Graph와 자연스럽게 연결하는 방식이 가장 안정적이라고 판단했습니다.
3. 이어서,
   - PatternEngine: 구조적 적합도 vs 실행 가능성 분리,
   - ValueEngine: 시장 값 vs 프로젝트 값(Baseline/Delta),
   - StrategyEngine: 이론적 전략 vs 실행 가능한 전략  
   이라는 분해가 Project Context 도입 후에도 자연스럽게 작동한다는 점이 검토되었습니다.
4. 마지막으로,
   - PH00 Project Context Setup Phase,
   - *_for_project 워크플로우 변형을 통해,  
     기존 14-Phase 구조 분석 워크플로우와도 모순 없이 결합된다고 보았습니다.

### 9.4 대안

1. User/Org Plane 신설
   - Interaction/Role/Substrate/Cognition 위에 5번째 Plane으로 User/Org Plane을 두는 설계.
   - 장점: 개념적 분리가 극도로 명확.
   - 단점: Plane 간 관계 정의, R/P/V/D와의 연결을 모두 새로 설계해야 하므로 복잡도 급증.

2. Client-Specific Reality Graph
   - 회사마다 별도 R-Graph를 두고,  
     시장 Reality와 클라이언트 Reality를 완전히 분리하는 방식.
   - 장점: 권한/데이터 분리 구현은 용이할 수 있음.
   - 단점: “시장 전체 vs 내 위치”를 한눈에 보기 어렵고,  
     Pattern/Value/Decision 측면에서의 아날로지/재사용성이 떨어짐.

이번 설계안은 이 대안들에 비해,

- 기존 R/P/V/D 구조를 유지하고,
- Substrate/Decision/Engine API에 최소 변경으로,
- “시장 + 사용자 상황”을 동시에 다루는 기능을 제공하는  
  **균형 잡힌 절충안**이라고 판단됩니다.

### 9.5 리스크

- Project Context 스키마가 과도하게 비대해질 수 있음.
  - 초기에는 최소 필드만 두고, 도메인/프로젝트 경험을 통해 점진적으로 확장해야 합니다.
- 엔진 간 책임 경계가 흐려질 수 있음.
  - PatternEngine/ValueEngine/StrategyEngine이 Project Context를 서로 다른 방식으로 해석하면  
    이해/디버깅이 어려워지므로,  
    “Project Context를 읽는 헬퍼/라이브러리”를 중앙에서 관리하는 것이 필요합니다.
- 도메인 특화 필드가 Project Context 스키마에 섞여 들어갈 위험.
  - 도메인별 필드는 별도 domain_traits나 전용 설정으로 분리하고,  
    Project Context는 가능한 범용 필드만 갖도록 유지하는 것이 좋습니다.

### 9.6 검증 아이디어

- Adult Language KR POC에 실제 회사/프로젝트 두 개를 얹어,
  - structure_analysis_for_project / opportunity_discovery_for_project / strategy_design_for_project를 end-to-end로 실행해 보는 것.
- v7에서 수행한 실제 Market Reality Report + 전략 프로젝트 1~2개를 v9+Project Context로 재구현해 보고,
  - 결과물 품질/설명력/재사용성/작업량 관점에서 비교.

이 과정을 통해 Project Context 설계가 현실의 Brownfield/Greenfield 프로젝트에 잘 맞는지 검증할 수 있습니다.