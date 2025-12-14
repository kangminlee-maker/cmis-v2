# CMIS 설계 철학 · 컨셉 (v2, 20251213)

## 1. CMIS의 정체성

CMIS는 시장/비즈니스 세계를 **현실(Reality) · 패턴(Pattern) · 값(Value) · 결정(Decision)**의 **그래프-오브-그래프(Graph-of-Graphs)**로 표현하고, 그 위에서 **이해(Understand) → 기회 발굴(Discover) → 전략 설계(Decide) → 학습(Learn)**을 반복하는 **Contextual Market Intelligence OS**입니다.

CMIS는 “그럴듯한 답변 생성기”가 아니라, **증거와 모델을 바닥에 깔고**(Substrate) 그 위에서 **계산/추론/검증/학습**이 돌아가는 구조를 지향합니다.

## 2. CMIS를 이루는 서비스 구성요소(큰 덩어리)

CMIS는 “무엇이 어디에 속하는가”를 강하게 분리합니다. 이 분리가 철학을 실제로 지키게 합니다.

### 2.1 Interaction Plane

사용자/외부 시스템이 들어오는 입구입니다(CLI/Notebook/Web/App/API). 인터페이스별 기본 Role 바인딩까지 포함합니다.

### 2.2 Role Plane

**사람 역할/앱 관점**입니다. 핵심 정의는: **Agent = Persona + Workflow + View** 입니다.
Role은 엔진이 아니라 “질문을 어떤 워크플로로 풀어 보여줄지”의 UX 레이어입니다.

### 2.3 Cognition Plane

R/P/V/D 그래프 위에서 실제로 **수집·정규화·추론·계산·학습·정책**을 수행하는 엔진 계층입니다. Evidence Engine / World Engine / Value Engine / Strategy Engine / Learning Engine / Belief Engine / Policy Engine 등이 여기에 속합니다.

### 2.4 Substrate Plane

**권위 있는 상태(Authoritative State)**가 저장되는 바닥층입니다.
그래프(R/P/V/D)와 스토어(Evidence/Value/Outcome/Project Context/Memory 등)가 존재하며, 이 층이 **재현성/감사 가능성/리런 가능성**을 보장합니다.

## 3. CMIS 핵심 철학(Principles)

아래는 “슬로건”이 아니라, **시스템 설계 제약 조건**입니다. 각 철학은 “왜 필요한가”와 “어떤 구성요소가 그 철학을 강제하는가”로 함께 정의합니다.

---

### 철학 1) Evidence-first, Prior-last

**의미**
가능한 한 모든 결론은 **외부/내부 Evidence**와 **구조적 계산**에 기반합니다. Prior(LLM 감각, 휴리스틱)는 “정말로 Evidence가 부족할 때”만 마지막 수단으로 씁니다.

**왜 필요한가**
시장/전략 의사결정은 “말이 되는 이야기”보다 “다시 검증 가능한 근거”가 중요합니다. Prior 중심으로 가면, 동일 질문을 다시 실행했을 때 결과가 흔들리고(재현성 붕괴), 팀 내 합의가 감(느낌) 싸움이 됩니다.

**구성요소로 어떻게 구현되는가**

* Evidence Engine: 필요한 Evidence를 on-demand로 수집/정규화/번들링합니다.
* Evidence Store: 출처·확보 시점·소스 ID를 스키마로 강제합니다(`url_or_path`, `retrieved_at`, `source_id`).
* Policy Engine: 모드별로 Prior 허용 범위를 제어합니다(엄격 보고/균형 의사결정/탐색).
* Belief Engine: “Evidence 부족 시 마지막 수단”으로 Prior를 공급하는 별도 엔진으로 격리합니다.

---

### 철학 2) 권위 있는 Substrate(SSOT 개념) + Lineage(출처/계보) = 재현 가능성

**의미**
CMIS에서 “진실”은 **엔진/에이전트의 말**이 아니라 **Substrate에 저장된 객체**입니다.
모든 결과는 “어떤 Evidence/그래프/정책/프로그램”에서 나왔는지 역추적 가능해야 합니다.

**왜 필요한가**
Evidence-first를 표방하면서 SSOT/lineage가 없으면, 시스템은 곧 “그때그때 말이 바뀌는 보고서 생성기”가 됩니다. 디버깅도 불가능해집니다(왜 그렇게 결론이 났는지 못 찾음).

**구성요소로 어떻게 구현되는가**

* Value Store: ValueRecord의 영구 저장소이며 “단일 진실의 원천 역할”로 정의됩니다.
* Evidence Store: 출처 메타데이터를 스키마로 보존합니다.
* Orchestration Layer: 목표 설정, 플랜 수립, 평가, 동적 재설계 과정 전체를 **Decision Logging**합니다.
* (권장) IDs & Lineage: 모든 오브젝트가 같은 방식으로 참조되도록 ID 프리픽스/스키마를 표준화합니다.

---

### 철학 3) Model-first, Number-second

**의미**
숫자는 “세계 모델”의 결과입니다.
즉, **Reality(구조) → Pattern(가능한 메커니즘) → Value(지표/계산) → Decision(전략/가설)**의 순서가 기본입니다.

**왜 필요한가**
시장은 숫자만으로 설명되지 않습니다. 같은 TAM도 “누가 누구에게 무엇을 어떤 계약으로 파는지”가 바뀌면 의미가 달라집니다. 모델이 없으면 숫자는 떠다니는 라벨이 됩니다.

**구성요소로 어떻게 구현되는가**

* World Engine: Evidence를 **Reality Graph 스냅샷**으로 정규화/업데이트합니다.
* Substrate의 Reality Graph: actor/event/resource/money_flow/contract/state primitive로 세계 구조를 담습니다.
* Value Engine: R/P/V 그래프와 Evidence를 입력으로 값을 계산·추론하고, 결과를 Value Store에 저장합니다.

---

### 철학 4) Graph-of-Graphs: R/P/V/D를 분리하고 연결한다

**의미**
Reality/Pattern/Value/Decision을 한 덩어리로 뭉개지 않고, **서로 다른 그래프로 분리**하되 **참조로 연결**합니다.

**왜 필요한가**

* Reality는 “사실”에 가까운 구조(변경 비용 큼)
* Pattern은 “일반화된 메커니즘”(업데이트 주기/근거/검증이 다름)
* Value는 “계산 가능한 지표 세계”(공식/추정/분포)
* Decision은 “목표/가설/전략”(사람·조직 컨텍스트 의존)
  이 네 가지는 생명주기와 검증 방식이 달라서, 한 그래프에 섞으면 추적성이 무너집니다.

**구성요소로 어떻게 구현되는가**

* Substrate Plane에 R/P/V/D 그래프 스키마가 별도로 정의됩니다.
* Decision Graph는 Goal/Hypothesis/Strategy/Scenario/Action을 일급 객체로 표현합니다.

---

### 철학 5) Trait 기반 Ontology: 라벨 고착(lock-in)을 피한다

**의미**
“SaaS/Marketplace” 같은 라벨을 고정 분류로 박지 않고, **Trait(속성) 공간에서 제약의 조합**으로 정의합니다. 이를 통해 새로운 모델/하이브리드 모델도 자연스럽게 흡수합니다. (CMIS 온톨로지에 trait set / capability traits가 포함됩니다.)

**왜 필요한가**
라벨 기반 분류는 시간이 지나면 “분류 싸움”이 됩니다. 반면 Trait 기반은 “어떤 성질이 얼마나 겹치는가”로 논쟁이 수렴합니다.

**구성요소로 어떻게 구현되는가**

* Pattern Graph에서 pattern은 traits/constraints로 정의됩니다.
* Pattern Engine은 구조 적합도(structure_fit)와 프로젝트 컨텍스트가 있을 때 실행 적합도(execution_fit)를 함께 계산하도록 설계되어 있습니다.

---

### 철학 6) Project Context는 “부가 정보”가 아니라 1급 객체다

**의미**
같은 시장이라도 “누가 하느냐”에 따라 가능한 전략이 달라집니다. CMIS는 이를 위해 Project Context(기준 상태/자산/제약/선호)를 1급으로 다루고, 엔진 호출에 `project_context_id`가 들어가면 해석이 달라지게 만듭니다.

**왜 필요한가**
Greenfield(시장 일반 분석)만 하면 “좋은 전략”이 나오고, Brownfield(특정 조직 관점)이 들어오면 “실행 가능한 전략”이 달라집니다. 이 차이를 Role 프롬프트로만 처리하면 결국 흔들립니다.

**구성요소로 어떻게 구현되는가**

* Decision Graph의 Goal에 `project_context_id`가 옵션으로 붙고, 유무에 따라 Greenfield/Brownfield를 구분합니다.
* Strategy Engine은 `project_context_id`가 있으면 hard constraints를 자동 반영하고, execution_fit_score를 고려합니다.
* Learning Engine은 Outcome으로부터 Project Context를 버전업(새 baseline 생성)하도록 정의되어 있습니다.

---

### 철학 7) 모든 답은 “세계-변화-결과-논증”의 패키지다

**의미**
CMIS의 산출물은 “결론”이 아니라,

1. 어떤 세계 모델을 전제했고
2. 어떤 변화(전략/가설)를 가정했고
3. 어떤 결과(지표/분포/리스크)가 나왔고
4. 왜 그런지(근거/계산/lineage)
   를 함께 제공해야 합니다. 이 철학은 Strategy Engine 설계에도 그대로 녹아 있습니다.

**왜 필요한가**
시장/전략은 반박 가능한 주장이어야 합니다. 패키지가 아니면 팀이 재사용을 못 하고, 다음 프로젝트에서 “또 처음부터” 하게 됩니다.

**구성요소로 어떻게 구현되는가**

* Value Engine이 `value_program_ref`(계산/추론 실행 기록)와 `value_record_ref`를 함께 반환하도록 되어 있습니다.
* Strategy Engine은 Goal/Pattern/Reality/Value를 결합해 전략 후보를 만들고 평가하도록 정의됩니다.
* Blueprint의 구현 원칙이 lineage를 강제합니다.

---

### 철학 8) Objective-Oriented Orchestration: “고정 프로세스”가 아니라 “목표 달성”이 중심이다

**의미**
CMIS는 Process-Oriented(고정 단계)로 굳지 않고, **중간 결과 평가 → 동적 재설계**가 가능한 목표 중심 오케스트레이션을 채택합니다.

**왜 필요한가**
시장 리서치는 “처음에 설계한 플랜대로” 흘러가지 않습니다. 새 Evidence가 나오면 질문이 바뀌고, Scope가 좁혀지거나 넓어집니다. 고정 프로세스는 여기서 부러집니다.

**구성요소로 어떻게 구현되는가**

* Orchestration Layer의 책임에 Execute+Evaluate 루프와 동적 재설계가 포함됩니다.
* Orchestration은 canonical workflow를 단일/멀티/커스텀/점진적으로 조합할 수 있습니다.
* Orchestration Provider는 Cursor/외부 LLM/규칙 기반 등으로 추상화됩니다.

---

### 철학 9) Agent는 엔진이 아니라 “일관된 작업 방식”이다

**의미**
Agent는 계산/수집의 실체가 아니라, **사용자에게 일관된 관점과 워크플로를 제공하는 역할 레이어**입니다. 내부 엔진이 바뀌어도, Role은 “어떤 질문을 어떤 순서로 어떻게 검증하며 제시하는가”를 지킵니다.

**왜 필요한가**
LLM Agent를 엔진처럼 쓰면, 구현은 빨라 보이지만 시간이 갈수록 “재현 불가능한 지식”만 쌓입니다. CMIS는 반대로, **엔진/스토어가 진실**이고, Agent는 “그 진실을 꺼내오는 얼굴”로 제한합니다.

**구성요소로 어떻게 구현되는가**

* Role 정의는 어떤 엔진을 주로 쓰는지(primary_engines)와 기본 정책 모드(default_policy_mode)를 가진 “사용 시나리오 템플릿”입니다.

---

### 철학 10) Monotonic Improvability & Re-runnability: 시스템은 계속 좋아져야 하고, 다시 돌릴 수 있어야 한다

**의미**
새 Evidence/Outcome이 쌓이면 과거 결론을 쉽게 재실행(re-run)해서 더 나은 답을 내야 합니다. 시스템은 “한 번 답하면 끝”이 아니라 **학습 가능한 OS**입니다.

**왜 필요한가**
시장/전략은 시간이 지나며 변합니다. 과거 리포트가 그대로 누적되면 부채가 됩니다. 반대로 리런 구조가 있으면 자산이 됩니다.

**구성요소로 어떻게 구현되는가**

* Learning Engine은 Outcome 기반으로 Metric/Pattern/Belief 업데이트를 수행합니다.
* Project Context는 Outcome으로 baseline을 업데이트하며 새 버전을 생성합니다(version += 1).
* Belief Engine은 learned belief를 ValueRecord 형태로 반영할 수 있습니다.

---

## 4. 문서 수준에서 명시해야 하는 “금지 규칙”(운영 원칙)

아래는 철학을 지키기 위한 실전 규칙입니다.

1. **Substrate에 기록되지 않은 정보는 ‘결론’이 아닙니다.** (초안/가설일 뿐)
2. **Evidence 없는 수치가 나오면**, Policy 모드에 맞춰 “추정(Structured Estimation)”로 명시하고, 가능하면 Evidence 확보를 먼저 수행합니다.
3. **Prior는 Belief Engine을 통해서만** 들어오게 하고, Value Engine/Policy Engine이 그 사용을 통제합니다.
4. **오케스트레이션은 항상 Decision Logging**을 남깁니다(재현/디버깅/감사).
5. 동일 질문 반복 실행 시 결과가 바뀌면, “왜 바뀌었는지”가 evidence/lineage/정책 변화로 설명되어야 합니다.

---

## 5. Non-goals (CMIS가 의도적으로 하지 않는 것)

* “그럴듯한 답만 빠르게 내는 챗봇”이 목표가 아닙니다. (근거·재현성 없는 답은 CMIS에선 부채입니다.)
* “전 세계 데이터를 미리 다 적재한 DW”가 목표가 아닙니다. (필요할 때 on-demand로 수집/모델링하는 OS를 지향합니다.)
* Agent가 임의로 사실을 확정하는 구조를 목표로 하지 않습니다. (Agent는 workflow/view입니다.)

---

# 사유 공개 블록 (가정/근거/추론/대안/리스크/검증)

### 가정

* “설계철학 문서”는 슬로건이 아니라, **철학 ↔ 아키텍처 구성요소가 1:1로 연결되는 문서**여야 한다고 가정했습니다.
* CMIS의 핵심 차별점은 “리서치/전략 설계에서의 증거 기반 재현성”이며, 이를 지키려면 Substrate/lineage/orchestration logging이 핵심이라고 가정했습니다.

### 근거

* Blueprint의 핵심 철학(모델 우선, 증거 우선, 그래프 분리, 재실행 가능성)이 명시돼 있습니다.
* CMIS YAML에 Role Plane(Agent=Persona+Workflow+View), Substrate Plane(그래프/스토어), Cognition Plane(엔진)이 구조적으로 분리돼 있습니다.
* Evidence Store/Value Store/Orchestration Logging이 “재현/감사”를 직접 지원하도록 정의돼 있습니다.

### 추론 경로

* Evidence-first를 “행동 강제”로 만들려면,
  (1) Evidence를 스키마로 강제하는 저장소,
  (2) Prior를 별도 엔진으로 격리하고 정책으로 통제,
  (3) 모든 결과를 Value Store에 고정,
  (4) 오케스트레이션 의사결정을 로깅
  이 동시에 필요하다고 판단했습니다.
* Agent를 엔진으로 두면 (1)~(4)가 무너질 가능성이 높아서, Agent의 역할을 “workflow/view”로 명시하는 편이 더 robust하다고 결론냈습니다.

### 대안

* “SSOT”라는 표현을 철학 문서에서 제거하고, **‘권위 있는 Substrate’** 같은 표현으로 완곡하게 대체할 수 있습니다. (단, 내용 자체는 유지되어야 합니다.)
* Objective-Oriented orchestration을 더 강하게 하려면, Orchestration Layer에 “진행 ledger/프로젝트 ledger”를 명시적으로 추가(예: Task/Progress ledger)하고, 모든 엔진 호출/결과를 그 ledger와 함께 저장하는 방식도 가능합니다. (현재 YAML에는 decision logging이 이미 들어가 있으므로 확장 방향으로 자연스럽습니다.)

### 불확실성/리스크

* “Agent는 workflow/view”라는 원칙을 너무 엄격하게 적용하면, 초기 개발 단계에서 생산성이 떨어질 수 있습니다(빠른 프로토타이핑이 어려움).
* 반대로 느슨하게 적용하면, Evidence-first가 껍데기가 될 수 있습니다(에이전트가 근거 없이 결론을 확정).

### 검증

* 동일한 질문을 **두 번 실행**했을 때, 결과가 바뀐다면 그 변화가
  ① evidence_store의 변화, ② policy 모드 변화, ③ project_context 버전 변화, ④ pattern/value 그래프 업데이트
  중 최소 하나로 설명되는지 확인하시면 됩니다.
* 임의의 ValueRecord를 골라 **“어떤 Evidence로부터 어떤 Program을 거쳐 나왔는지”**가 끝까지 추적되는지(라인리지 완주)로 품질을 판정하시면 됩니다.
