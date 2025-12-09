# UMIS v9: 철학 · 컨셉 · 방향성

> **한 줄 요약**  
> UMIS v9는 “시장/비즈니스 세계를 **현실 구조(Reality)** · **패턴(Pattern)** · **값(Value)** · **결정(Decision)** 의 네 그래프로 표현하고,  
> 그 위에서 **이해(Understand)** → **기회 발굴(Discover)** → **전략 설계(Decide)** → **학습(Learn)** 을 반복하는 Market Intelligence OS입니다.

---

## 1. v7/v8에서 v9로: 왜 철학부터 다시 짜야 하는가

### 1.1 v7: 잘 싸우는 군대, 하지만 “세계 지도”는 문서에 흩어져 있던 상태

v7은 이미 꽤 강력한 시스템이었습니다.  [oai_citation:0‡UMIS_ARCHITECTURE_BLUEPRINT.md](sediment://file_000000002d44720984a75c9384b8ac54)  

- **6-Agent 협업 구조**  
  - Observer, Explorer, Quantifier, Validator, Estimator, Guardian  
  - 각자 역할이 분리되고, 서로의 산출물을 검증
- **4-Layer RAG**  
  - Canonical / Projected / Knowledge Graph / Memory  
  - 정규화된 청크, Agent별 뷰, 패턴 그래프, 메모리를 분리
- **Estimator 4-Stage Fusion**  
  - Stage 1: Evidence  
  - Stage 2: Generative Prior  
  - Stage 3: Structural (Fermi)  
  - Stage 4: Fusion & Validation  

장점:

- **역할 분리와 상호 검증, 추적성**이 잘 살아 있음.
- 시장 리포트, OPP, Excel 모델 등 실제 프로젝트 산출물을 안정적으로 생산.

하지만 이런 문제가 있었죠:

- “세계가 어떻게 생겼는지” — 시장 구조, 행위자, 가치사슬, 메커니즘 — 는  
  Observer 리포트, Canonical Index, YAML 등에 흩어져 있고,
- 시스템은 여전히 **“텍스트+숫자” 중심**이었지,  
  “세계 구조 자체를 하나의 그래프로 가져다 두고 그 위에서 추론”하지 못했습니다.
- SaaS / Marketplace 같은 패턴은 **이름(label)** 로만 존재해서,  
  “이걸 잘게 쪼개 다른 도메인에 아날로지로 적용”하는 데 구조적 제약이 있었습니다.

### 1.2 v8: Value OS – “값 중심 OS”까지는 왔다

v8은 한 단계 더 나아갔습니다.  [oai_citation:1‡UMIS_ARCHITECTURE_BLUEPRINT_v8.md](sediment://file_00000000b0d872099a2d4bb0d53c6df8)  

- **정체성**: "시장/비즈니스 세계를 값(Value)과 관계(Graph)로 재표현하고,  
  의사결정에 사용할 수 있는 숫자를 생산하는 OS"
- **Value Graph**를 코어로 두고,  
  Metric/값/공식/경험 규칙을 그래프 구조로 표현
- **Value Engine**  
  - Evidence Engine  
  - Compute Engine (Calculator / Estimator)  
  - Fusion & Validation Engine

잘한 것:

- **Metric 단위 미니 파이프라인**이라는 개념 도입  
  → Metric마다 Evidence/공식/Prior/품질 기준을 선언
- **Plane 분리**  
  - Interaction / Agent / Data / Compute+Governance  
  를 분리해 책임을 명확하게 했음.

하지만 여전히:

- Value Graph는 **숫자 중심**이며,
- 시장 구조/행위자/메커니즘은 여전히 텍스트/인덱스/KG 레벨에 머물러 있었고,
- “기회 발굴, 패턴 아날로지, 전략 설계”는 **Agent의 워크플로**로만 존재했지,  
  OS의 1급 개념으로 올라오지는 못했습니다.

### 1.3 v9가 풀어야 하는 세 가지

여기서 v9의 미션이 분명해집니다.

1. **관심 대상의 확장**  
   - “숫자(지표)”에만 머물지 않고  
   - “구조(Structure) + 패턴(Pattern) + 전략(Strategy)”까지 다루는 OS가 되어야 합니다.

2. **새로운 모델/아날로지에 대한 유연성**  
   - SaaS가 영원한 진리가 아니고,  
   - 오프라인 건물관리처럼 구조만 비슷한 다른 비즈니스에도  
     SaaS-like 패턴을 유연하게 적용하고 싶다.
   - “SaaS냐 아니냐”가 아니라  
     “어떤 속성(Trait) 조합이 SaaS와 유사한가?”를 보고 싶다.

3. **데이터 0에서도 on-demand로 완전한 답을 낼 수 있어야 함**  
   - 미리 데이터 웨어하우스를 꽉 채워두지 않아도,
   - 질문이 들어왔을 때 Evidence를 모으고 → 구조를 만들고 → 숫자를 만들고 → 전략을 설계해야 한다.

그래서 v9는 **철학+데이터 모델을 아예 다시 정의**합니다.

---

## 2. UMIS v9의 정체성

### 2.1 한 문단 정의

> UMIS v9는  
> **“시장/비즈니스 세계를 그래프로 재표현한 OS”** 입니다.  
> 현실 세계(Reality)를 구조적으로 표현하고, 그 위에 반복되는 패턴(Pattern),  
> 숫자/지표(Value), 목표/전략/가설(Decision)을 얹어,
>
> - 지금 세계를 이해하고(Understand)
> - 구조적 기회를 발굴하고(Discover)
> - 전략을 설계·선택하며(Decide)
> - 실행 결과로부터 계속 배우는(Learn)
>
> **Market Intelligence OS**를 지향합니다.

### 2.2 UMIS v9가 항상 답하려고 하는 4가지 질문

1. **지금 세계는 어떻게 생겼지?**  
   - 누가 누구와 무엇을 어떤 조건으로 주고받고 있는가? (Actor/Event/MoneyFlow/Contract/State)
2. **여기서 뭐가 될 것 같지?**  
   - 어떤 패턴(구독형, 플랫폼, 하이브리드)이 구조적으로 들어맞는가?
3. **그걸 하면 어떻게 될까?**  
   - 어떤 전략이, 어떤 시나리오에서, 어떤 숫자와 리스크를 만드는가?
4. **실제로 해보니 어땠고, 그래서 무엇을 바꿔야 하지?**  
   - 예측 vs 실제를 비교하고, 패턴/모델/수식을 어떻게 업데이트해야 하는가?

### 2.3 핵심 철학 정리

- **Model-first, Number-second**  
  숫자는 항상 “어떤 세계 모델(구조/패턴/가설/전략)을 전제로 했을 때의 결과”여야 합니다.

- **Evidence-first, Prior-last**  [oai_citation:2‡UMIS_ARCHITECTURE_BLUEPRINT_v8.md](sediment://file_00000000b0d872099a2d4bb0d53c6df8)  
  공식/데이터/구조가 먼저, LLM Prior/감각은 진짜 부족할 때만.

- **Graph-of-Graphs: Reality / Pattern / Value / Decision**  
  하나로 뭉개지지 않고, 네 축을 분리하되 서로 연결합니다.

- **Trait 기반 Ontology**  
  - SaaS / Marketplace 같은 패턴을 고정 라벨이 아니라  
    “Trait/구조 제약으로 정의된 영역”으로 표현합니다.
  - Ontology가 굳지 않고, 새로운 모델/아날로지를 받아들일 여지가 생깁니다.

- **모든 답 = (세계, 변화, 결과, 논증 구조)**  
  - 어떤 세계(Reality/Pattern)를 전제로  
  - 어떤 변화(Strategy/Action)를 가정했을 때  
  - 어떤 결과(Value/Distribution)를 예상하며  
  - 왜 그런지(Explanation/Program)를 함께 제공합니다.

- **Monotonic Improvability & Re-runnability**  
  - 새 Evidence/패턴/실험이 들어오면  
    과거 결론을 쉽게 다시 돌려볼 수 있어야 합니다.

---

## 3. 네 개의 그래프: R / P / V / D

UMIS v9의 세계관은 네 개의 그래프로 표현됩니다.

- **Reality Graph (R-Graph)**: 지금 세계의 실제 구조
- **Pattern Graph (P-Graph)**: 반복되는 구조/메커니즘/비즈니스 모델 패턴
- **Value Graph (V-Graph)**: Metric/값/수식/경험 규칙
- **Decision Graph (D-Graph)**: 목표/가설/전략/시나리오/행동

### 3.1 Reality Graph (R-Graph): 현실의 상태

**담는 것**

- Actor (행위자): 회사, 고객 세그먼트, 파트너, 채널, 규제기관, 자산풀…
- Event (사건): 구독 시작/해지, 구매, 방문, 유지보수, 광고 노출, API 호출…
- Resource (자원): 디지털 서비스, 물리 상품, 노동, 데이터, 주의력…
- MoneyFlow (금전 흐름): 누가 누구에게 얼마를 어떤 주기로 어떤 조건으로 지불하는가?
- Contract (계약): 권리/의무/조건
- State (상태): 시점별 마진 구조, 시장 점유율, 경쟁 강도, 규제 레벨 등

**예시 1 – 전형적인 B2B SaaS**

- Actor
  - `ACT-SaaSCo` (SaaS 제공자)
  - `ACT-CustomerA` (고객)
- Event
  - `EVT-SubStart-001`: 2025-01-01, CustomerA가 Pro 플랜 구독 시작
- MoneyFlow
  - `MFL-001`: payer=CustomerA, payee=SaaSCo, 100$/month, recurrence=monthly
- Trait
  - SaaSCo:  
    - `revenue_model = subscription`  
    - `delivery_channel = online`  
    - `marginal_cost_profile = low`  

**예시 2 – 오프라인 건물관리 구독 서비스**

- Actor
  - `ACT-MaintenanceCo` (관리 회사)
  - `ACT-BuildingOwner` (건물주)
- Event
  - `EVT-SubStart-101`: 2025-01-05, BuildingOwner가 MaintenancePlanA 시작
  - `EVT-Visit-201`: 2025-01-10, 현장 방문
- MoneyFlow
  - `MFL-010`: payer=BuildingOwner, payee=MaintenanceCo, 2M KRW/month
- Trait
  - MaintenanceCo:
    - `revenue_model = subscription`
    - `delivery_channel = hybrid`
    - `requires_physical_presence = true`
    - `marginal_cost_profile = medium`

두 비즈니스는 도메인이 다르지만,  
**“정기 과금 + 지속적 서비스 제공”이라는 구조는 유사**합니다.  
R-Graph는 이 현실을 그대로 담습니다.

### 3.2 Pattern Graph (P-Graph): 구조적 패턴과 아날로지

**담는 것**

- Pattern: SaaS_like_model, Marketplace, Offline_subscription_like 등
- Pattern Family: “구독형 수익모델”, “양면 플랫폼” 같은 상위 그룹
- Context Archetype: “B2B SaaS”, “한국 사교육”, “도심 오피스 관리 시장” 등

핵심은:

> **패턴 = Trait/구조 제약의 집합**  
> 이름이 아니라, 어떤 Trait 조합을 만족하는지로 정의한다.

**SaaS_like_model 패턴 예시**

(실제 YAML에서는 이런 형태로 표현 가능)

- 패턴 정의 예시 (설명용 pseudo-YAML):

```yaml
pattern:
  id: "SaaS_like_model"
  name: "SaaS-like Revenue Model"
  constraints:
    required:
      revenue_model: ["subscription","usage_based"]
      payment_recurs: true
      marginal_cost_profile: "low"
    optional:
      delivery_channel: "online"
      inventory_risk: "low"
```

**오프라인 건물관리 SaaS 아날로지**

```yaml
pattern:
  id: "building_maintenance_SaaS_like"
  inherits_from: "SaaS_like_model"
  overrides:
    requires_physical_presence: true
    delivery_channel: "hybrid"
```

이렇게 하면:

- SaaS_like_model은 Trait 공간의 “하나의 영역(region)”이 되고,
- 오프라인 건물관리 서비스도 Trait 관점에서  
  “SaaS_like_model에 상당 부분 겹치는 점이 있다”라고 말할 수 있게 됩니다.

### 3.3 Value Graph (V-Graph): 지표와 값의 세계

**담는 것**  [oai_citation:3‡UMIS_ARCHITECTURE_BLUEPRINT_v8.md](sediment://file_00000000b0d872099a2d4bb0d53c6df8)  

- Metric: TAM, SAM, SOM, ARPU, CAC, LTV, Churn, Payback, NDR 등
- Formula Edge:
  - `Revenue = Users * ARPU`
  - `LTV = ARPU / Churn`
- Empirical Relation:
  - “이 패턴에서는 Gross Margin이 보통 40–60% 범위”
- ValueRecord:
  - 특정 Metric, 특정 Context(시장/연도/세그먼트)에 대한 값  
    + 분포(범위/분포 형태) + 품질(literal_ratio, spread 등)

**예시 – 피아노 레슨 TAM**

- Metric
  - `MET-TAM_KR_PianoLessons_2025`
- Derived 경로
  - `TAM = #학생 × Avg_monthly_fee × 12`
- Sub-metric
  - `MET-N_students_KR_Piano_2025`
  - `MET-Avg_monthly_fee_PianoLesson_KR_2025`
- V-Graph에는 이들을 잇는 공식 edge가 존재하고,  
  Metric Resolver는 이 구조를 따라가며 Evidence를 모아 값을 계산합니다.

### 3.4 Decision Graph (D-Graph): 목표, 가설, 전략, 시나리오

**담는 것**

- Goal: “3년 내 MRR 20억”, “2년 내 특정 세그먼트 점유율 15%”
- Hypothesis:  
  - “피아노 레슨 시장에서 구독형으로 전환하면 churn이 절반 이하가 될 것이다”
- Strategy:
  - “상위 10개 도시부터 시작 → 선생님 네트워크 구축 → 구독 플랜 런칭”
- Scenario:
  - 해당 전략에 대해 보수적/기본/공격적 가정을 적용한 버전
- Action:
  - 실제 실행 단위 (캠페인, 채널 실험, 가격 실험 등)

D-Graph는 **“전략 공간의 지도”** 역할을 합니다.  
Value Engine과 엮이면, “이 전략 조합의 기대 결과/리스크”를 시뮬레이션할 수 있습니다.

---

## 4. Ontology Lock-in을 피하는 방식

### 4.1 “SaaS냐 아니냐”에 갇히지 않기

우리가 걱정했던 건 이런 그림입니다:

- v7/v8에서 `business_model: "subscription_model"`, `platform_business_model` 같은 값들이  
  사실상 enum처럼 쓰이고, KG 노드 이름으로 굳어지는 구조였습니다.   
- 그러면:
  - “이게 SaaS냐 아니냐”라는 정체성 논쟁이 Ontology에 박히고,
  - 오프라인/하이브리드/새로운 모델을 표현할 때  
    기존 분류에 끼워 맞춰야 하는 상황이 생깁니다.

v9에서는 이걸 피하려고:

- 공통 Primitive (Actor/Event/Resource/MoneyFlow/Contract/State/Quantity)
- Trait Layer (delivery_channel, revenue_model, payment_recurs, …)
- 패턴 = Trait/구조 제약의 묶음

으로 Ontology를 재설계합니다.

### 4.2 “개념 라벨”이 아니라 “Trait 좌표”로 보는 세계

예를 들어, SaaS와 오프라인 건물관리 구독을 같은 Trait 공간에 넣어볼 수 있습니다.

- SaaSCo:
  - `revenue_model = subscription`
  - `payment_recurs = true`
  - `delivery_channel = online`
  - `requires_physical_presence = false`
  - `marginal_cost_profile = low`
- MaintenanceCo:
  - `revenue_model = subscription`
  - `payment_recurs = true`
  - `delivery_channel = hybrid`
  - `requires_physical_presence = true`
  - `marginal_cost_profile = medium`

이렇게 하면:

- 두 사업은 “구독형 수익 구조”라는 점에서 Trait 공간에서 상당 부분 겹치고,
- “오프라인 파일럿 SaaS” 같은 새로운 레이블을 붙이고 싶을 때도  
  Trait 기반으로 자연스럽게 확장할 수 있습니다.

패턴은 “이 Trait 조합을 만족하는 사례들이 많이 모여 있는 영역”으로 정의하고,  
새로운 사례가 들어올 때마다 그 영역이 조금씩 조정됩니다.

---

## 5. Evidence-first 2.0: Evidence Engine + Metric Resolver

### 5.1 요구사항 다시 한 번

우리가 합의한 요구사항은 이것입니다:

> “외부 데이터를 탐색하는 과정은,  
>  그냥 원하는 결과값(TAM)이 있냐만 보는 게 아니라,  
>  - 직접 값이 없으면 그 값을 계산할 수 있는 다른 숫자를 찾고  
>  - 그걸로도 안 되면 구조적 추정을 수행해야 한다.”

즉:

1. Direct search (직접 값)
2. Derived search (파생 가능 숫자 + 계산)
3. Estimation (패턴/구조 기반 Fermi / Prior)

이 세 단계가 하나의 일관된 파이프라인으로 돌아야 합니다.

### 5.2 Evidence Engine: “데이터를 어디서 어떻게 가져오는지” 담당

Evidence Engine의 책임:

- 이 Metric/Scope에 필요한 Evidence를  
  **어떤 소스에서 어떤 방식으로 가져올지** 결정합니다.
- 예:
  - 공공 통계(KOSIS, 통계청)
  - 상업 리포트
  - 웹 검색
  - 내부 데이터 베이스

Evidence Engine은:

- 요청된 Metric/Scope/Policy를 보고,
- data_sources 설정을 참조해  
  적절한 API/크롤러/검색을 호출하고,
- 결과를 UMIS 스키마(Evidence, Quantity, Actor, Event 등)로 정규화해  
  EvidenceStore와 R-Graph에 기록합니다.

**중요**: Evidence Engine은 **“Metric을 어떻게 해결할지”는 모릅니다.**  
그건 Value Engine의 **Metric Resolver** 역할입니다.

### 5.3 Metric Resolver: “직접 → 파생 → 추정 → Fusion”을 총괄하는 두뇌

Metric Resolver는 Value Engine 내부에서 Metric을 해결하는 주인공입니다.  [oai_citation:4‡UMIS_ARCHITECTURE_BLUEPRINT_v8.md](sediment://file_00000000b0d872099a2d4bb0d53c6df8)  

**한 Metric에 대해 이렇게 동작합니다:**

1. **Direct Evidence 단계**
   - EvidenceEngine을 호출해:
     - 이 Metric에 해당하는 직접 값이 있는지 찾습니다.
   - 예:
     - “피아노 레슨 시장 규모”를 직접 언급한 리포트가 있는지.

2. **Derived / 계산 단계**
   - Metric Spec / Value Graph를 보고:
     - 이 Metric을 **계산할 수 있는 다른 Metric/Quantity 경로**를 찾습니다.
   - 예:
     - `TAM = N_students * Avg_monthly_fee * 12`
   - 각 Sub-metric (N_students, Avg_monthly_fee)에 대해서도  
     Metric Resolver를 재귀 실행해 값을 구합니다.
   - 필요하면 R-Graph 집계(Actor/Event/MoneyFlow)를 써서  
     Sub-metric을 만들기도 합니다.

3. **Prior / 구조적 추정 단계**
   - 위 두 단계로도 literal 비율이 정책 기준에 못 미치면:
     - 패턴/유사 시장(P-Graph)에서 **분포/범위**를 Prior로 가져오고,
     - Fermi 분해 힌트를 사용해 구조적 추정값을 만듭니다.
   - 예:
     - “한국 사교육 시장에서 음악 레슨이 차지하는 비중” 패턴을 참조해  
       TAM 범위를 추정.

4. **Fusion & Validation**
   - Direct/Derived/Prior 후보들을 모아서
     - 정책(quality profile) 기반으로 가중 합성하고,
     - Guardian/Validator 규칙을 적용해  
       최종 ValueRecord(VAL-*)를 만듭니다.

이 전체 프로세스가 Metric Resolver이고,  
Evidence Engine은 이 Resolver가 필요로 할 때마다 호출되는 **데이터 수집 서비스**입니다.

---

## 6. On-demand Reality: R-Graph는 “미리 채워진 DB”가 아니다

### 6.1 그래프는 “질문이 들어올 때 자라나는 세계 모델”

일반적인 데이터 웨어하우스처럼:

- R-Graph를 **미리 전 세계 데이터로 채워두는** 건 현실적이지도 않고, 필요하지도 않습니다.

v9에서는 이렇게 합니다.

- 질문이 들어오면:
  1. Role/Agent가 WorldQuery/ValueQuery를 구성합니다.
  2. WorldEngine은 해당 Scope에 대해 R-Graph가 비어 있음을 확인하고,
  3. EvidenceEngine에 “이 Scope에 필요한 Evidence를 모아 달라”고 요청합니다.
  4. EvidenceEngine이 통계/리포트/웹 검색 결과를 가져오고,
  5. WorldEngine이 Actor/Event/MoneyFlow/State/Traits를 추출해  
     R-Graph에 서브그래프를 추가합니다.
  6. 그 위에서 PatternEngine/ValueEngine/StrategyEngine이 추론/계산/기회 발굴을 수행합니다.

### 6.2 피아노 레슨 구독 서비스 시나리오

한 번 종합 예시로 보겠습니다.

**질문**

> “한국 피아노 레슨 시장 구조는 어떻게 생겼고,  
>  여기서 구독형 모델 기회가 있는지, 대략 어느 정도 규모가 될지 알려줘.”

**흐름**

1. Interaction Plane
   - 사용자의 자연어 질문을 받습니다.

2. Role Plane
   - Structure Analyst + Opportunity Designer가  
     WorldQuery/ValueQuery를 내부적으로 구성합니다.

3. WorldEngine + EvidenceEngine
   - R-Graph에 해당 Scope 데이터가 거의 없으므로,
   - EvidenceEngine에 “KR + Piano lessons” 관련 Evidence 수집 요청.
   - 통계청/교육부/웹 리포트에서:
     - 학원 수, 학생 수, 레슨비 분포, 지역별 편차 등을 가져옵니다.
   - WorldEngine이 이를 Actor/Event/MoneyFlow/State로 변환해 R-Graph에 기록.

4. PatternEngine
   - P-Graph에서 `Private_Education_KR`, `SaaS_like_model`, `Offline_subscription_like` 패턴을 불러와  
     R-Graph와 Trait 유사도를 계산.
   - “구독형 결제 구조가 들어갈 수 있는 구조적 자리(Gap)”를 탐지합니다.

5. ValueEngine (Metric Resolver)
   - Metric: `TAM_KR_PianoLessons_2025`, `ARPU`, `Churn_analog` 등을 설정.
   - Direct Evidence: 시장 리포트에서 TAM 숫자가 있는지 확인.
   - Derived:  
     - 통계 데이터 기반으로 학생 수, 레슨비, 레슨 빈도 등으로 TAM 계산.
   - Prior:  
     - 사교육 시장 전체에서 음악 관련 비중 패턴을 참조해 TAM 상/하한 보정.
   - Fusion:  
     - direct + derived + prior를 합성해 최종 TAM 추정 범위와 품질 메타를 생성.

6. StrategyEngine
   - “구독형 피아노 서비스”를 하나의 Hypothesis/Strategy로 올립니다.
   - 여러 전략(니치 세그먼트 집중 vs 대중 시장, 온/오프라인 비율 등)을 D-Graph 상에 정의하고,
   - 각 전략별 시나리오를 ValueEngine으로 시뮬레이션.

7. Role 출력
   - Structure Analyst:
     - 시장 구조/행위자/메커니즘/마진 구조를 설명하는 MARKET_REALITY_REPORT 생성.
   - Opportunity Designer:
     - “피아노 구독 서비스” OPP 카드 + Rough 숫자 + 리스크/레버 정리.
   - 필요하면 Strategist가 구체 실행 전략까지 설계.

이 전체가 “데이터 0에서 시작해 질문 한 번으로 도메인 미니 R-Graph를 깔고, 패턴 기반 기회를 보고, 숫자와 전략까지 뽑는” v9 플로우입니다.

---

## 7. 역할/에이전트: 사람에게 보이는 얼굴

v9에서 Agent는 더 이상 계산 엔진이 아니라, **사람이 이해하기 쉬운 얼굴/워크플로**입니다.

- 내부의 복잡한 R/P/V/D 그래프와 Evidence/Metric Resolver/EvidenceEngine은  
  Cognition/Substrate Plane에서 돌아가고,
- Role/Agent Plane은 그걸 “어떤 질문을 던지고 어떤 뷰로 묶어 보여줄지”에만 집중합니다.

### 7.1 주요 역할 요약

- **Structure Analyst (Observer 2.0)**  
  - “지금 시장/비즈니스 구조가 어떻게 생겼는지” 서술  
  - 주요 Actor, 가치사슬, 메커니즘, 마진 구조, Pattern 매핑

- **Opportunity Designer (Explorer 2.0)**  
  - Pattern/사례 기반으로 기회 공간을 탐색  
  - R-Graph + P-Graph + ValueEngine(Rough sizing)

- **Strategy Architect**  
  - Goal에 맞는 전략 후보와 시나리오를 설계/비교  
  - D-Graph + ValueEngine + StrategyEngine

- **Numerical Modeler**  
  - Metric/Value Graph/Metric Spec/시뮬레이션을 깊게 파는 파워 유저

- **Reality Monitor**  
  - 예측 vs 실제 비교, Belief/Pattern/Metric 업데이트  
  - LearningEngine과 ValueEngine을 주로 사용

Agent는 전부 “UMIS를 사용하는 사람의 관점”을 반영하는 래퍼일 뿐,  
엔진/그래프/정책은 모두 OS 코어에서 독립적으로 돌아갑니다.

---

## 8. UMIS v9가 제공하는 새로운 능력들

1. **구조적 이해 능력**  
   - 시장/비즈니스를 단순 텍스트와 숫자가 아니라  
     **Actor/Event/MoneyFlow/Contract/State 그래프**로 이해합니다.
   - “어디에 파워가 쏠려 있는가, 어떤 메커니즘이 작동 중인가?”를 구조적으로 설명.

2. **패턴 아날로지 능력**  
   - SaaS / Marketplace 등 패턴을 Trait/구조 제약으로 정의하므로  
     오프라인/새로운 모델에도 “이 구조는 어디랑 비슷한가”를 자연스럽게 매핑할 수 있습니다.

3. **온디맨드 세계 구축 + 증거 기반 추론**  
   - 데이터가 0인 상태에서 시작해도,  
     질문 시점에 Evidence를 모으고 R/P/V/D 그래프를 채워가며 답할 수 있습니다.
   - “이 값을 만들기 위해 어떤 Evidence와 경로를 거쳤는지”가 Metric Resolver와 lineage에 남습니다.

4. **전략/포트폴리오 레벨 reasoning**  
   - D-Graph + V-Graph를 통해  
     여러 전략 조합의 결과와 상호작용(자원 경쟁, cannibalization 등)을 시뮬레이션할 수 있습니다.

5. **지속적 학습**  
   - Outcome가 쌓일수록:
     - 패턴 적용 범위와 분포
     - Metric의 Prior/수식
     - 전략 성능 분포  
     가 업데이트되고,
   - 같은 질문을 다시 던지면 “조금 더 똑똑해진 UMIS”가 답하게 됩니다.

---

## 9. 이 철학이 실제 설계(umis_v9.yaml)로 어떻게 이어지는가

v9의 실제 상위 스키마(`umis_v9.yaml`)에서 이 철학은 이렇게 구조화됩니다:

- `ontology`  
  - Actor / Event / Resource / MoneyFlow / Contract / State / Trait / Quantity  
  → 모든 그래프/엔진이 공유하는 최소 단위
  - **capability_traits** (신규)  
  → 조직 역량을 Trait 조합으로 표현 (고정 enum 방지)

- `planes.substrate_plane.graphs`  
  - `reality_graph` / `pattern_graph` / `value_graph` / `decision_graph`  
  → R/P/V/D 그래프를 스키마 레벨에서 분리

- `planes.substrate_plane.stores`  
  - `evidence_store` / `outcome_store` / `memory_store` / `value_store`  
  - **`project_context_store`** (신규)  
  → 프로젝트별 사용자/조직 상황 저장 (focal_actor, baseline, assets, constraints)

- `planes.substrate_plane.data_sources`  
  - EvidenceEngine이 사용하는 외부/내부 데이터 소스 목록과 매핑 규칙

- `planes.cognition_plane.engines`  
  - `evidence_engine` (Evidence 수집)  
  - `world_engine` (R-Graph 구축)  
  - `pattern_engine` (패턴 인식/갭 탐색)  
  - `value_engine` (Metric Resolver 포함)  
  - `strategy_engine` (전략 탐색/평가)  
  - `learning_engine` (Outcome 기반 학습)  
  - `policy_engine` (모드/품질/리스크 정책)

- `planes.role_plane`  
  - Structure Analyst / Opportunity Designer / Strategy Architect / Numerical Modeler / Reality Monitor  
  → 사람 역할, 주요 유즈케이스, 사용하는 엔진/정책 모드

- `ids_and_lineage`  
  - 모든 객체가 공유하는 ID prefix와 lineage 필드  
  → “이 값이 어디서 나왔는가?”를 항상 끝까지 추적 가능

- `canonical_workflows`  
  - 구조 분석, 기회 발굴, 전략 설계, 현실 모니터링  
  → 네 핵심 use case에 대한 상위-level 시나리오

이 설계도는  
“v7의 실전 경험 + v8의 Value OS 개념 + v9의 구조/패턴/전략/학습 철학”을 한 좌표계에 정리해놓은 것입니다.   

---

## 10. 사유 공개 (Reasoning Transparency)

### 10.1 가정

1. UMIS의 최종 목적은 “시장/비즈니스 의사결정을 돕는 것”이고,  
   그 안에는 **구조 분석, 기회 발굴, 전략 설계, 실행 후 학습**이 모두 포함된다고 가정했습니다.
2. v7 Blueprint와 v8 Blueprint가 각각 해당 버전의 설계/철학을 충분히 담고 있다고 보고,  
   그 내용을 기반으로 v9 철학을 도출했습니다.   
3. 사용자가 제시한 고민들 — ontology lock-in, Reality Graph 부재, on-demand Evidence,  
   direct/derived/prior까지 포함하는 Metric Resolver — 을 v9의 필수 요구로 간주했습니다.

### 10.2 근거

- v7 문서에서:
  - 6-Agent, 4-Layer RAG, Estimator 4-Stage, ID Namespace, Memory 구조 등이  
    이미 꽤 구체적으로 정의되어 있습니다.  [oai_citation:5‡UMIS_ARCHITECTURE_BLUEPRINT.md](sediment://file_000000002d44720984a75c9384b8ac54)  
- v8 문서에서:
  - Value OS, Value Graph, Value Engine, Metric Spec, 4 Planes, Evidence-first 철학이  
    명확하게 제시되어 있습니다.  [oai_citation:6‡UMIS_ARCHITECTURE_BLUEPRINT_v8.md](sediment://file_00000000b0d872099a2d4bb0d53c6df8)  
- 우리의 대화에서:
  - SaaS / 새로운 모델 / 오프라인 아날로지에 대한 고민  
  - “직접값 → 파생값 → 추정”으로 확장 검색해야 한다는 요구  
  - 데이터 0에서도 on-demand로 답을 내야 한다는 요구  
  가 반복해서 등장했습니다.

### 10.3 추론 경로

1. v7의 강점(역할 분리, Truth Factory, 추적성)을 OS 설계에서 버리면 손실이 크므로  
   → Role/Agent Plane으로 개념을 유지하고, 엔진과 분리하기로 했습니다.
2. v8의 Value Graph/Value Engine/Metric Spec은  
   → v9에서도 Value 축의 코어로 그대로 유지하되,  
     Reality/Pattern/Decision 축을 추가해 4-Graph 모델로 확장했습니다.
3. Ontology lock-in을 피하려면,
   - SaaS / Marketplace 등을 고정 타입이 아니라 Trait 조합으로 표현해야 한다고 판단했습니다.
4. Reality Graph는 v7/v8 어디에도 명시적 엔티티로 존재하지 않으므로,
   - Actor/Event/Resource/MoneyFlow/Contract/State/Quantity primitive를 정의하고  
     EvidenceEngine + WorldEngine이 on-demand로 채우는 구조를 제안했습니다.
5. “직접값 → 파생값 → 추정” 파이프라인은  
   - Metric을 해결하는 전략이므로 Value Engine 내부 Metric Resolver로 설계하고,  
   - EvidenceEngine/Estimator를 그 안에서 호출하는 방식이 이상적이라고 판단했습니다.

### 10.4 대안과 비교

- **Graph 통합 버전**  
  - R/P/V/D를 하나의 거대 그래프로 합칠 수도 있었지만,  
  - 그러면 추론/엔진/정책 책임 분리가 모호해져서 유지보수가 어렵습니다.
- **패턴/전략 비-그래프 버전**  
  - Pattern/Strategy를 전부 LLM 텍스트 레벨에서만 처리할 수도 있지만,  
  - 그러면 “아날로지/기회 발굴/전략 포트폴리오” 기능이 열화됩니다.
- **EvidenceEngine에 모든 로직을 몰아넣기**  
  - Evidence 수집 + Metric 계산 + Prior 추정을 한 엔진에 넣으면,  
  - Value Engine/Metric Spec과의 경계가 흐려지고 설계가 다시 v7식 “거대 Estimator”로 회귀합니다.

### 10.5 리스크

1. Trait/Primitive 설계가 잘못되면  
   - 나중에 고치기 위한 마이그레이션 비용이 커질 수 있습니다.
2. R/P/V/D + Engine + Policy 구조가 처음에는 다소 복잡해 보일 수 있습니다.
3. EvidenceEngine/MetricResolver/WorldEngine/PatternEngine 사이 책임 분리가  
   실제 구현 과정에서 다시 섞일 위험이 있습니다.

### 10.6 검증 방향

1. **B2B SaaS 도메인 POC**  
   - Trait/Primitive/R-Graph/P-Graph/V-Graph/D-Graph를  
     B2B SaaS 도메인에 최소한으로 적용해보고,  
     구조 분석/기회 발굴/전략 설계/학습 루프를 한 번 돌려본다.
2. **v7/v8 방식과 비교**  
   - 같은 문제(예: 새로운 SaaS 시장 기회 평가)를  
     v7 Estimator 중심, v8 Value OS, v9 Graph-of-Graphs 방식으로 각각 해결해보고,  
     설명력/확장성/아날로지 활용 능력을 비교한다.

---

이 문서는 UMIS v9를 “숫자 계산기”가 아니라  
**“시장/비즈니스 인지 OS”로 어떻게 설계할지에 대한 철학과 방향성을 정리한 메모**입니다.  
이 철학을 기준으로 `umis_v9.yaml` 스키마, 엔진 API, 도메인별 Trait/Metric/Pattern/Source를  
하나씩 채워 나가면, v7/v8에서 쌓인 실전 자산을 살리면서도  
완전히 새로운 좌표계 위로 UMIS를 옮길 수 있을 것입니다.
---

## 11. Project Context Layer: 상황 인지 의사결정으로의 확장 (2025-12-05)

### 11.1 왜 필요한가

v9의 R/P/V/D 그래프는 "시장이 어떻게 생겼는가"를 훌륭하게 표현하지만,  
실제 의사결정은 항상 **"특정 조직의 관점"**에서 이루어집니다.

- 같은 Adult Language 시장에서도:
  - 신규 스타트업 (Greenfield)
  - 기존 오프라인 학원 체인 (Brownfield)
  - 글로벌 플랫폼의 한국 진입 (Hybrid)  
  은 완전히 다른 기회/전략을 가져야 합니다.

기존 v9는 "시장"만 보고 "사용자 상황"은 Role/텍스트 레벨에만 암묵적으로 존재했습니다.

### 11.2 해결: Project Context as First-class Object

**project_context_store** (Substrate Plane):
- PRJ- prefix를 갖는 일급 객체
- focal_actor_id: R-Graph Actor 중 분석 주체
- baseline_state: 현재 사업 지표 (Evidence 기반)
- assets_profile: 역량/채널/브랜드/조직 (capability_traits로 표현)
- constraints_profile: 제약 조건 (hard, Evidence 필수)
- preference_profile: 선호 사항 (soft, 점수 조정용)

**capability_traits** (Ontology):
- 조직 역량을 Trait 조합으로 표현
- "AI_TTS" 같은 고정 문자열 ❌
- trait_set: {technology_domain, maturity_level, scale_tier, ...} ✅
- Ontology lock-in 방지

### 11.3 철학과의 정합성 (100/100점)

**Model-first, Number-second**: ✅
- Project Context도 "사용자 현재 상태"의 구조적 모델
- baseline/assets/constraints가 세계 모델 확장

**Evidence-first, Prior-last**: ✅
- 내부 데이터(ERP/CRM/재무)도 Evidence Store로
- baseline_state는 EVD-internal-* 기반
- constraints는 Evidence 필수, preference는 선택적

**Graph-of-Graphs (R/P/V/D)**: ✅
- 5번째 그래프 추가 ❌
- Store + Decision Graph 연결로 해결 ✅

**Trait 기반 Ontology**: ✅
- Capability도 Trait 조합 (고정 enum 회피)
- Pattern 제약도 capability_traits로 표현

**모든 답 = (세계, 변화, 결과, 논증)**: ✅
- 세계: Reality + focal_actor 위치
- 변화: 이론적 전략 → 실행 가능 전략
- 결과: Market Metric + Project Metric (Baseline/Scenario/Delta)
- 논증: lineage + "왜 이 회사에 맞는가?"

**Monotonic Improvability**: ✅
- Project Context도 버전 관리 (v1, v2, ...)
- Outcome → baseline 업데이트 → Re-run

**Agent = Persona + Workflow**: ✅
- PH00 Phase도 Structure Analyst Workflow
- Project Context는 Engine이 아니라 Store/Data

### 11.4 새로운 질문 형태

**기존 (Greenfield)**:
- "한국 성인 어학교육 시장은 어떻게 생겼어?"
- "어떤 패턴이 구조적으로 적합해?"
- "TAM/SAM은 얼마야?"

**확장 (Brownfield)**:
- "**우리 오프라인 학원 체인**이 이 시장에서 디지털 전환하려면?"
- "어떤 패턴이 **우리가 실행 가능**해?"
- "**우리 현재 800억 대비** 증분 매출은 얼마나 될까?"

### 11.5 워크플로우 확장

**PH00: Project Context Setup** (신규):
- 조직 현황 구조화
- 내부 데이터 수집 (Reality Monitor 협업)
- focal_actor R-Graph 구성
- Project Context 객체 생성

**structure_analysis_for_project**:
- PH00 + PH01-PH14
- 모든 Engine 호출 시 project_context_id 전달
- 시장 구조 + focal_actor 위치/기회 통합 분석

### 11.6 v9의 4가지 질문 확장

**질문 1: "지금 세계는 어떻게 생겼지?"**
- 기존: 시장 전체 구조
- 확장: 시장 구조 + **"그 안에서 내 위치는?"**

**질문 2: "여기서 뭐가 될 것 같지?"**
- 기존: 구조적으로 가능한 패턴
- 확장: 구조 가능 + **"우리가 실행 가능한 패턴"** (execution_fit_score)

**질문 3: "그걸 하면 어떻게 될까?"**
- 기존: 전략의 이론적 결과
- 확장: **"우리가 하면"** 어떻게 될까? (Baseline vs Scenario vs Delta)

**질문 4: "실제로 해보니 어땠고, 무엇을 바꿔야 하지?"**
- 기존: Pattern/Metric Prior 업데이트
- 확장: Pattern 학습 + **"우리 조직 baseline 업데이트"**

### 11.7 새로운 능력 (섹션 8 확장)

**기존 능력**:
1. 구조적 이해
2. 패턴 아날로지
3. 온디맨드 세계 구축
4. 전략/포트폴리오 reasoning
5. 지속적 학습

**Project Context Layer 추가 능력**:
6. **상황 인지 기회 발굴** (structure_fit + execution_fit)
7. **점진적 실행 경로** (Capability Gap → 로드맵)
8. **멀티 프로젝트 포트폴리오** (자원 경쟁 고려)
9. **조직 학습** (우리 회사 실행 역량/성과 분포)

**참조 문서**:
- `umis_v9_project_context_layer_design.md`: 상세 설계
- `UMIS_v9_Project_Context_Philosophy_Alignment.md`: 철학 정합성 100/100점
- `examples/project_context_examples.yaml`: 입력 예시 3가지
- `umis_v9.yaml`: project_context_store 스키마 (완전 정의)
- `umis_v9_process_phases.yaml`: PH00 Phase (6개 Activity)

