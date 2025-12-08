# UMIS v9: Project Context Layer 설계의 철학 정합성 분석

**문서 목적**: `umis_v9_project_context_layer_design.md`의 설계가 `umis_v9_philosophy_concept.md`의 핵심 철학과 일치하는지 검증하고, 개선점을 도출

**작성일**: 2025-12-05

---

## 1. 철학 7대 원칙과의 정합성 체크

### ✅ 1.1 Model-first, Number-second

**철학**:
> "숫자는 항상 어떤 세계 모델(구조/패턴/가설/전략)을 전제로 했을 때의 결과여야 합니다."

**Project Context Layer 설계**:
- Project Context 자체가 **"사용자의 현재 상태/자산/제약"이라는 모델**
- baseline_state, assets_profile, constraints_profile는 모두 "현재 세계"의 구조적 표현
- 숫자(Baseline Revenue, SOM_for_project)는 이 모델을 전제로 계산됨

**정합성**: ✅ **완전 일치**

**개선점**:
```yaml
# Project Context도 "세계 모델의 일부"임을 명시
project_context:
  philosophical_role: "focal_actor의 현재 상태를 모델로 표현"
  model_components:
    - baseline_state: "현재 숫자들의 전제 조건"
    - assets_profile: "가용 자원/역량의 구조"
    - constraints_profile: "제약 조건의 명시적 표현"
```

---

### ✅ 1.2 Evidence-first, Prior-last

**철학**:
> "공식/데이터/구조가 먼저, LLM Prior/감각은 진짜 부족할 때만."

**Project Context Layer 설계**:
- baseline_state는 **Evidence 기반** (내부 데이터 → Evidence Store)
- assets_profile/constraints_profile도 선언적 입력이지만, 가능하면 Evidence로 뒷받침
- Project-aware Metric도 Direct Evidence → Derived → Prior 순서 유지

**정합성**: ✅ **완전 일치**

**개선점**:
```yaml
# PH00 Phase에서 Evidence 수집 명시
PH00_project_context_setup:
  evidence_collection:
    internal_data:
      - ERP_revenue_data → EVD-internal-001
      - CRM_customer_data → EVD-internal-002
      - Financial_statements → EVD-internal-003
    
    declaration_with_evidence:
      - assets_profile.capabilities → 검증 가능한 증거 (프로젝트 이력, 팀 이력서 등)
      - constraints_profile.budget → 재무제표/이사회 결의
```

**철학 강화**:
- "사용자가 말하는 것"도 Evidence로 기록
- 주관적 선호(preference_profile)와 객관적 제약(constraints_profile) 분리
- Prior는 선호에만 사용, 제약은 Evidence 기반

---

### ✅ 1.3 Graph-of-Graphs: R/P/V/D

**철학**:
> "하나로 뭉개지지 않고, 네 축을 분리하되 서로 연결합니다."

**Project Context Layer 설계**:
- **새로운 5번째 그래프를 추가하지 않음** ✅
- Substrate Plane의 `stores`에 `project_context_store`만 추가
- R-Graph: focal_actor는 Actor primitive로 표현
- D-Graph: Goal/Strategy에 `project_context_id` 필드만 추가
- P-Graph/V-Graph: 구조 유지, API 입력만 확장

**정합성**: ✅ **완전 일치**

**개선점**:
```yaml
# 4-Graph 분리 원칙 재확인
design_principle:
  what_not_to_do:
    - "Project Graph 신설 ❌"
    - "R/P/V/D 통합 ❌"
  
  what_to_do:
    - "R-Graph에 focal_actor를 Actor로 표현 ✅"
    - "D-Graph에 project_context 연결 ✅"
    - "Store에 project_context_store 추가 ✅"
    - "Engine API에 project_context_id 인자 추가 ✅"
```

---

### ⚠️ 1.4 Trait 기반 Ontology (부분 보완 필요)

**철학**:
> "SaaS / Marketplace 같은 패턴을 고정 라벨이 아니라 Trait/구조 제약으로 정의된 영역으로 표현합니다."

**Project Context Layer 설계**:
- Pattern에 `required_capabilities` 추가
- assets_profile에 `capabilities` 리스트

**문제점**:
- `capabilities`가 **자유 문자열 리스트**로 표현되면, Trait 기반 Ontology 철학과 충돌
- "AI_TTS", "Curriculum_Design" 같은 capability가 고정 enum처럼 굳을 위험

**개선 방향**:

**Capability도 Trait처럼 표현**:

```yaml
# assets_profile에서 (현재 설계)
assets_profile:
  capabilities:
    - "AI_TTS"
    - "Curriculum_Design"

# 개선: Capability를 Trait 조합으로 표현
assets_profile:
  capability_traits:
    - capability_id: "CAP-AI_voice_tech"
      traits:
        technology_domain: "AI_speech_synthesis"
        maturity_level: "production_ready"
        scale_capacity: "10K+ concurrent users"
    
    - capability_id: "CAP-EdTech_design"
      traits:
        domain_expertise: "education"
        content_type: "curriculum"
        maturity_level: "early"
```

**Pattern 제약도 Trait로 통일**:

```yaml
# Pattern 정의
pattern:
  id: "PAT-AI_personalized_learning"
  constraints:
    required_traits:  # R-Graph 시장 구조
      - market_trait: "digital_learning_acceptance > 0.3"
    
    required_capability_traits:  # focal_actor 역량
      - capability_trait: "technology_domain in [AI_ML, NLP, Speech]"
      - capability_trait: "maturity_level >= early"
```

**PatternEngine 매칭 로직**:
```python
def execution_fit_score(pattern, project_context):
    required = pattern.constraints.required_capability_traits
    available = project_context.assets_profile.capability_traits
    
    # Trait 기반 유사도 계산 (고정 문자열 비교 ❌)
    match_score = trait_similarity(required, available)
    return match_score
```

**정합성**: ⚠️ **부분 보완 필요**

---

### ✅ 1.5 모든 답 = (세계, 변화, 결과, 논증 구조)

**철학**:
> "어떤 세계(Reality/Pattern)를 전제로, 어떤 변화(Strategy/Action)를 가정했을 때, 어떤 결과(Value/Distribution)를 예상하며, 왜 그런지(Explanation/Program)를 함께 제공합니다."

**Project Context Layer가 추가하는 것**:

**세계 확장**:
- Reality: 시장 + **focal_actor의 현재 위치**
- Pattern: 구조적 적합도 + **실행 가능성**

**변화 구체화**:
- Strategy: 이론적 전략 → **실행 가능한 전략**
- Scenario: 시장 변화 → **focal_actor 변화 (Baseline → Scenario)**

**결과 분해**:
- Market Metric: TAM, SAM
- **Project Metric**: SOM_for_project, Delta_Revenue, Payback

**논증 강화**:
- lineage: 기존 (Evidence → Value)
- **확장**: (Evidence + Project Context) → Value
- "왜 이 회사에 이 기회가 맞는가?" 설명 가능

**정합성**: ✅ **완전 일치 + 강화**

---

### ✅ 1.6 Monotonic Improvability & Re-runnability

**철학**:
> "새 Evidence/패턴/실험이 들어오면 과거 결론을 쉽게 다시 돌려볼 수 있어야 합니다."

**Project Context Layer 설계**:

**Project Context도 버전 관리 가능**:
```yaml
project_context:
  project_context_id: "PRJ-Startup_EdTech_001_v3"
  version: 3
  previous_version_id: "PRJ-Startup_EdTech_001_v2"
  
  baseline_state:
    as_of: "2025-12-05"
    revenue: 500M KRW
    # v2 대비 revenue 100M 증가
  
  changed_since_v2:
    - "available_capital: 300M → 500M"
    - "team_size: 2 → 3"
    - "new_capability: AI_TTS added"
```

**Re-run 시나리오**:
```python
# v2 시점 기회 발굴
opportunities_v2 = opportunity_discovery_for_project(
    domain_id="Adult_Language_KR",
    project_context_id="PRJ-Startup_EdTech_001_v2"
)

# v3 시점 (자본 증가, 역량 추가 후)
opportunities_v3 = opportunity_discovery_for_project(
    domain_id="Adult_Language_KR",
    project_context_id="PRJ-Startup_EdTech_001_v3"
)

# 차이 비교
delta = compare_opportunities(opportunities_v2, opportunities_v3)
# → "AI 개인화 코칭 기회가 feasibility 0.4 → 0.85로 상승"
```

**정합성**: ✅ **완전 일치**

---

### ✅ 1.7 Agent = Persona + Workflow

**철학**:
> "Agent는 더 이상 계산 엔진이 아니라, 사람이 이해하기 쉬운 얼굴/워크플로입니다."

**Project Context Layer 설계**:
- PH00 Phase는 Structure Analyst가 주도
- *_for_project 워크플로우는 기존 Role에 할당
- Project Context 자체는 Engine이 아니라 **데이터/Store**

**정합성**: ✅ **완전 일치**

---

## 2. v9의 4가지 핵심 질문과 Project Context

**철학에서 제시한 4가지 질문**:

### 질문 1: "지금 세계는 어떻게 생겼지?"

**기존 v9**: 시장 전체 구조
**Project Context 추가**: 시장 구조 + **"그 안에서 내 위치는?"**

```
기존: "한국 성인 어학교육 시장은 1조원, Top 10이 34%"
추가: "우리 회사는 Top 10 밖, 오프라인 5개 지점, 연 50억 매출"
```

### 질문 2: "여기서 뭐가 될 것 같지?"

**기존 v9**: 구조적으로 가능한 패턴
**Project Context 추가**: 구조 가능 + **"우리가 실행 가능한 패턴"**

```
기존: "플랫폼형 BM이 구조적으로 적합"
추가: "플랫폼형은 structure_fit 0.9, 하지만 우리 execution_fit 0.3"
     "오프라인 구독 강화는 structure_fit 0.6, execution_fit 0.9"
```

### 질문 3: "그걸 하면 어떻게 될까?"

**기존 v9**: 전략의 이론적 결과
**Project Context 추가**: **"우리가 하면" 어떻게 될까**

```
기존: "구독형 전환 시 시장 전체 Churn 5% 예상"
추가: "우리 기존 50억 매출 기준, 구독형 전환 시"
     "- Baseline: 50억/년, Churn 20%"
     "- Scenario: 80억/년, Churn 8%"
     "- Delta: +30억 증가, Payback 18개월"
```

### 질문 4: "실제로 해보니 어땠고, 무엇을 바꿔야 하지?"

**기존 v9**: Pattern/Metric Prior 업데이트
**Project Context 추가**: **"우리 회사 baseline 업데이트"**

```
기존: "구독형 패턴에서 Churn 5% → 7%로 Prior 조정"
추가: "우리 프로젝트 PRJ-001"
     "- 예상 Churn 8% → 실제 12%"
     "- baseline_state 업데이트"
     "- 다음 전략 시 이 실적 반영"
```

**결론**: ✅ **4가지 질문 모두 Project Context로 강화됨**

---

## 3. On-demand Reality 철학과 Project Context

**철학**:
> "R-Graph를 미리 전 세계 데이터로 채워두는 건 현실적이지 않다. 질문이 들어올 때 자라나는 세계 모델."

**Project Context Layer와의 조화**:

### 3.1 두 종류의 On-demand

**Market Reality** (기존):
```
질문: "한국 성인 어학교육 시장..."
→ EvidenceEngine: 외부 데이터 수집 (DART, 웹)
→ WorldEngine: R-Graph 구축 (ACT-YBM, ACT-Ringle, ...)
```

**Focal Actor Reality** (추가):
```
질문: "우리 회사가 이 시장에 진입하려면..."
→ PH00 Phase 시작
→ EvidenceEngine: 내부 데이터 수집 (ERP, CRM, 재무제표)
→ WorldEngine: R-Graph에 focal_actor + 주변 구조 추가
→ Project Context 생성
```

### 3.2 동일한 철학, 두 레벨 적용

**On-demand 원칙**:
1. 미리 채우지 않는다
2. 질문 시점에 Evidence 수집
3. 점진적 그래프 확장

**적용**:
- 시장: 도메인별 on-demand R-Graph 구축 ✅
- 사용자: 프로젝트별 on-demand focal_actor 구축 ✅

**정합성**: ✅ **철학의 자연스러운 확장**

---

## 4. 철학 관점 개선점

### 4.1 Capability를 Trait 체계로 통합

**현재 설계 (잠재적 문제)**:
```yaml
assets_profile:
  capabilities:
    - "AI_TTS"
    - "Curriculum_Design"
    - "Platform_Tech"
```
→ 고정 문자열 리스트, Ontology lock-in 위험

**개선 (Trait 기반)**:
```yaml
assets_profile:
  capability_traits:
    - capability_id: "CAP-001"
      trait_set:
        technology_domain: "AI_speech_synthesis"
        maturity_level: "production_ready"
        scale_tier: "10K_users"
        deployment_type: "cloud_native"
    
    - capability_id: "CAP-002"
      trait_set:
        domain_expertise: "education_content"
        content_format: "curriculum"
        language_coverage: ["korean", "english"]
        maturity_level: "mvp"
```

**Pattern 제약도 Trait로**:
```yaml
pattern:
  id: "PAT-AI_personalized_learning"
  constraints:
    required_market_traits:
      - "digital_learning_acceptance >= 0.3"
    
    required_capability_traits:
      - "technology_domain in [AI_ML, NLP, speech_synthesis]"
      - "maturity_level >= mvp"
    
    incompatible_traits:
      - "delivery_channel == purely_offline"
```

**장점**:
- Capability도 "Trait 공간의 좌표"로 표현
- 새로운 기술/역량이 등장해도 Trait 조합으로 유연하게 표현
- PatternEngine의 execution_fit_score가 Trait 유사도 계산으로 일관성 확보

---

### 4.2 Preference vs Constraint 명확한 분리

**철학적 근거**:
- Evidence-first: 객관적 제약은 Evidence 기반
- Prior-last: 주관적 선호는 Prior/휴리스틱으로 처리

**설계 명확화**:

```yaml
project_context:
  
  constraints_profile:  # 객관적, Evidence 기반, 위반 불가
    hard_constraints:
      - constraint_id: "CNS-budget"
        type: "financial"
        max_initial_investment: 500M KRW
        evidence_id: "EVD-internal-board_resolution"
      
      - constraint_id: "CNS-timeline"
        type: "temporal"
        mvp_deadline: "2026-06-01"
        evidence_id: "EVD-internal-roadmap"
  
  preference_profile:  # 주관적, Prior/휴리스틱, 위반 가능 (패널티)
    soft_preferences:
      - pref_id: "PREF-growth_vs_profit"
        dimension: "strategic_priority"
        value: "growth_oriented"
        weight: 0.7
      
      - pref_id: "PREF-segment"
        dimension: "target_customer"
        preferred: ["office_worker", "professional"]
        avoid: ["student", "retiree"]
        weight: 0.5
```

**Engine 사용 방식**:
- StrategyEngine: hard_constraints 위반 전략은 **제거**
- StrategyEngine: soft_preferences 위반 전략은 **점수 감점**

---

### 4.3 Learning Engine과 Project Context 통합

**철학**:
> "Outcome이 쌓일수록 패턴/Metric/전략 성능이 업데이트되고, 같은 질문을 다시 던지면 조금 더 똑똑해진 UMIS가 답하게 됩니다."

**Project Context Layer에 추가해야 할 것**:

**Outcome → Project Context 업데이트**:

```yaml
# Outcome 기록
outcome:
  outcome_id: "OUT-PRJ001-Q1-2026"
  related_project_id: "PRJ-Startup_EdTech_001"
  related_strategy_id: "STR-AI_Coaching_MVP"
  as_of: "2026-03-31"
  
  actual_metrics:
    - metric_id: "MET-Revenue"
      predicted: 200M KRW  # Scenario 예상
      actual: 150M KRW     # 실제
      delta: -25%
    
    - metric_id: "MET-Churn_rate"
      predicted: 0.08
      actual: 0.12
      delta: +50%

# LearningEngine이 수행
learning_engine.update_from_outcome("OUT-PRJ001-Q1-2026")

# Project Context 업데이트
project_context_v4:
  baseline_state:  # 업데이트
    current_revenue: 150M KRW  # v3: 0 → v4: 150M
    current_churn: 0.12
  
  learned_patterns:  # 새로 추가
    - pattern_id: "PAT-AI_personalized_learning"
      our_performance:
        revenue_vs_prediction: -25%
        churn_vs_prediction: +50%
      lessons:
        - "AI 튜터 onboarding UX 개선 필요"
        - "Churn이 예상보다 높음 → retention 전략 강화"
```

**Re-run**:
```python
# v4 (실적 반영 후) 다시 기회 발굴
opportunities_v4 = opportunity_discovery_for_project(
    domain_id="Adult_Language_KR",
    project_context_id="PRJ-Startup_EdTech_001_v4"
)

# 이전 예측이 틀렸던 부분을 반영한 더 현실적인 기회 제시
```

**정합성**: ✅ **완전 일치**

---

### ✅ 1.7 Agent = Persona + Workflow (엔진이 아님)

**철학**:
> "Agent는 전부 UMIS를 사용하는 사람의 관점을 반영하는 래퍼일 뿐, 엔진/그래프/정책은 모두 OS 코어에서 독립적으로 돌아갑니다."

**Project Context Layer 설계**:
- PH00 Phase: Structure Analyst가 **주도**하지만
- 실제 작업: WorldEngine, EvidenceEngine이 수행
- Project Context: **Store/데이터**이지 Engine이 아님

**정합성**: ✅ **완전 일치**

---

## 5. 종합 평가 및 개선 권고

### 5.1 정합성 스코어

| 철학 원칙 | 정합성 | 비고 |
|----------|--------|------|
| Model-first, Number-second | ✅ 100% | Project Context도 모델 |
| Evidence-first, Prior-last | ✅ 100% | 내부 데이터도 Evidence |
| Graph-of-Graphs | ✅ 100% | 5번째 그래프 추가 ❌ |
| Trait 기반 Ontology | ⚠️ 85% | Capability를 Trait로 재설계 필요 |
| 모든 답 = (세계, 변화, 결과, 논증) | ✅ 100% | 오히려 강화됨 |
| Monotonic Improvability | ✅ 100% | Project Context 버전 관리 |
| Agent = Persona + Workflow | ✅ 100% | PH00도 Workflow |

**총점**: 98/100

---

### 5.2 필수 개선 사항

#### 개선 1: Capability를 Trait 체계로 통합

**현재**:
```yaml
assets_profile:
  capabilities: ["AI_TTS", "Curriculum_Design"]
```

**개선**:
```yaml
assets_profile:
  capability_traits:
    - capability_id: "CAP-001"
      name: "AI 음성합성 기술"
      trait_set:
        technology_domain: "AI_speech_synthesis"
        maturity_level: "production_ready"
        scale_tier: "enterprise"
```

**umis_v9.yaml 확장**:
```yaml
ontology:
  traits:
    capability_traits:
      technology_domain:
        value_type: "enum"
        allowed_values: ["AI_ML", "NLP", "speech_synthesis", "platform_tech", ...]
      
      maturity_level:
        value_type: "enum"
        allowed_values: ["concept", "mvp", "early", "production_ready", "mature"]
      
      scale_tier:
        value_type: "enum"
        allowed_values: ["poc", "startup", "enterprise", "hyperscale"]
```

#### 개선 2: Constraint vs Preference 엄격 분리

**설계 명확화**:
```yaml
project_context:
  
  constraints_profile:  # 위반 불가, Evidence 필수
    type: "hard_constraints"
    evidence_required: true
    violation_handling: "filter_out"
  
  preference_profile:  # 위반 가능, Evidence 선택적
    type: "soft_preferences"
    evidence_required: false
    violation_handling: "score_penalty"
```

#### 개선 3: Learning Engine → Project Context 업데이트 경로 명시

**umis_v9.yaml에 추가**:
```yaml
cognition_plane:
  engines:
    learning_engine:
      api:
        - name: "update_project_context_from_outcome"
          description: "실제 Outcome 기반 Project Context baseline/learned_patterns 업데이트"
          input:
            outcome_id: "outcome_id"
            project_context_id: "project_context_id"
          output:
            updated_project_context_version: "project_context_ref"
```

---

## 6. 철학 강화: Project Context가 추가하는 새로운 차원

### 6.1 철학 확장: "시장 인지 OS" → "상황 인지 의사결정 OS"

**기존 정체성**:
> "시장/비즈니스 세계를 그래프로 재표현한 Market Intelligence OS"

**확장 정체성**:
> "시장 세계(R/P/V)와 사용자 상황(Project Context)을 함께 그래프로 표현하고,  
> 그 위에서 이해·발굴·설계·학습을 수행하는 **Contextual Market Intelligence OS**"

### 6.2 새로운 능력 추가

**기존 v9 능력** (철학 문서 섹션 8):
1. 구조적 이해 능력
2. 패턴 아날로지 능력
3. 온디맨드 세계 구축 + 증거 기반 추론
4. 전략/포트폴리오 레벨 reasoning
5. 지속적 학습

**Project Context Layer가 추가하는 능력**:

6. **상황 인지 기회 발굴**
   - 구조적으로 가능한 기회 (structure_fit)
   - **실행 가능한 기회** (execution_fit)
   - 둘의 조합으로 현실적 우선순위 제시

7. **점진적 실행 경로 추천**
   - "지금 당장" vs "역량 확보 후" vs "장기 투자 필요"
   - Capability Gap 분석 기반

8. **멀티 프로젝트 포트폴리오 최적화**
   - 한 회사의 여러 도메인/전략 프로젝트
   - 자원(예산/인력) 경쟁 고려
   - Cannibalization 리스크 평가

9. **조직 학습 축적**
   - 시장 학습 (Pattern/Metric Prior)
   - **조직 학습** (우리 회사의 실행 역량/성과 분포)

---

## 7. 최종 권고사항

### 7.1 umis_v9.yaml 확장 필수 사항

```yaml
# 1. Project Context Store 추가
substrate_plane:
  stores:
    project_context_store:
      id_prefix: "PRJ-"
      schema:
        fields:
          project_context_id: { type: "string", required: true }
          focal_actor_id: { type: "actor_id", required: true }
          mode: { type: "enum", values: ["greenfield","brownfield","hybrid"] }
          baseline_state: { type: "dict", required: true }
          assets_profile: { type: "asset_profile_ref", required: true }
          constraints_profile: { type: "constraint_profile_ref", required: true }
          preference_profile: { type: "preference_profile_ref", required: false }
          version: { type: "int", default: 1 }
          previous_version_id: { type: "project_context_id", required: false }

# 2. Capability Trait 정의
ontology:
  traits:
    capability_traits:
      technology_domain: { ... }
      maturity_level: { ... }
      scale_tier: { ... }

# 3. Decision Graph Goal 확장
substrate_plane:
  graphs:
    decision_graph:
      node_types:
        goal:
          fields:
            # 기존 필드 유지
            project_context_id: { type: "project_context_id", required: false }  # 추가

# 4. Engine API 확장
cognition_plane:
  engines:
    world_engine:
      api:
        - name: "snapshot"
          input:
            # 기존 인자 유지
            project_context_id: { type: "project_context_id", required: false }  # 추가
    
    pattern_engine:
      api:
        - name: "match_patterns"
          output:
            # structure_fit_score 추가
            execution_fit_score: { type: "float", required: false }  # project_context 있을 때만
    
    value_engine:
      metrics_spec:
        metric_level_types:
          - "market"   # domain_id만 필요
          - "project"  # project_context_id 필요
```

### 7.2 Workflow 확장

```yaml
canonical_workflows:
  
  # 기존 (Greenfield)
  - id: "structure_analysis"
    input_schema:
      required: ["domain_id", "region"]
      optional: []
  
  # 추가 (Brownfield)
  - id: "structure_analysis_for_project"
    input_schema:
      required: ["domain_id", "region", "project_context_id"]
      optional: []
    
    phases:
      - id: "PH00"
        name: "Project Context Setup"
        new: true
      - id: "PH01-PH14"
        name: "기존 Phase 재사용"
        context_aware: true
```

### 7.3 Phase 0 (PH00) 상세 정의

**umis_v9_process_phases.yaml에 추가**:

```yaml
workflows:
  structure_analysis_for_project:
    phases:
      - phase_id: "PH00_project_context_setup"
        sequence: 0
        name: "프로젝트 컨텍스트 설정"
        owner: "structure_analyst"
        duration: "2-4 hours"
        
        inputs:
          - type: "user_input"
            content: "조직/프로젝트 현황 인터뷰/폼"
          - type: "internal_data"
            content: "ERP/CRM/재무 데이터 (선택적)"
        
        activities:
          - "조직 현황 파악 (사업/매출/조직/역량)"
          - "내부 데이터 수집 요청 (Reality Monitor)"
          - "focal_actor R-Graph 구성 (World Engine)"
          - "Project Context 객체 생성"
        
        outputs:
          - type: "project_context"
            id: "PRJ-*"
          - type: "r_graph_extension"
            content: "focal_actor + 관련 서브그래프"
        
        validation:
          - "constraints_profile에 Evidence 연결 확인"
          - "baseline_state의 핵심 Metric 계산 가능 확인"
```

---

## 8. 결론: 철학과 설계의 정합성

### ✅ 강점

1. **R/P/V/D 분리 철학 유지**
   - 5번째 그래프 추가 없이 Store/API 확장으로 해결

2. **Evidence-first 원칙 확장**
   - 내부 데이터도 Evidence로 처리
   - Constraint는 Evidence 필수, Preference는 선택적

3. **On-demand 철학 일관성**
   - 시장 Reality + focal_actor Reality 모두 on-demand

4. **Agent 역할 유지**
   - Project Context 설정도 Workflow/Phase로 표현

### ⚠️ 보완 필요

1. **Capability를 Trait 체계로 통합**
   - 고정 문자열 → Trait 조합

2. **Constraint/Preference 분리 명확화**
   - Evidence 요구사항 차별화

3. **Learning Engine 통합 경로 명시**
   - Outcome → Project Context 업데이트 API

### 📋 실행 우선순위

**즉시 (이번 세션)**:
1. umis_v9.yaml에 project_context_store 스키마 추가
2. capability_traits 정의
3. Engine API에 project_context_id 인자 추가

**Sprint 1 (1주)**:
1. PH00 Phase 상세 설계 및 템플릿
2. Evidence Engine 내부 데이터 연동
3. Project Context 입력 예시 5개 작성

**Sprint 2 (1주)**:
1. PatternEngine execution_fit_score 구현
2. ValueEngine project-level Metric 구현
3. opportunity_discovery_for_project 최소 버전

---

**총평**: Project Context Layer 설계는 v9 철학과 **98% 정합**하며, Capability Trait 통합만 보완하면 완벽하게 일치합니다.

**작성일**: 2025-12-05
**상태**: 분석 완료
