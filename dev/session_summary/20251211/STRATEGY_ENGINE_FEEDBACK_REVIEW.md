# StrategyEngine 피드백 검토 및 반영 보고

**작성일**: 2025-12-11
**기반**: Strategy_Engine_Design.md 피드백
**상태**: ✅ 검토 및 반영 완료

---

## Executive Summary

StrategyEngine 설계에 대한 7개 주요 피드백을 검토하고 모두 반영했습니다.

**결론**:
- 기존 구조는 CMIS 철학과 잘 맞음
- 완전 재설계 불필요
- **API/스키마 레벨 정렬**로 충분

---

## 피드백 검토 및 반영

### 1. API 레벨 분리 (최상) ✅

**피드백**:
- cmis.yaml API vs 설계 문서 함수의 시그니처 불일치
- 공식 API는 goal_id만 받음
- 설계 함수는 Pattern/Gap 직접 받음

**문제**:
- canonical_workflows 호환성
- 레이어 역할 혼재

**반영 내용**:

**API 3단계 분리**:
```python
# Level 1: Public API (cmis.yaml 1:1 대응)
def search_strategies_api(
    goal_id: str,
    constraints: Dict,
    project_context_id: Optional[str]
) -> str:  # strategy_set_ref
    """
    canonical_workflows가 호출
    - goal_id → Goal 로딩 (D-Graph)
    - World/Pattern Engine 내부 호출
    - Core 함수 호출
    - D-Graph 저장
    """

# Level 2: Orchestration (엔진 조율)
def _orchestrate_strategy_search(...):
    """
    World/Pattern Engine 호출
    Core 함수 연결
    """

# Level 3: Core (순수 로직)
def search_strategies_core(
    goal: Goal,
    reality_snapshot: RealityGraphSnapshot,
    pattern_matches: List[PatternMatch],
    ...
) -> List[Strategy]:
    """
    테스트/실험용
    순수 로직
    """
```

**효과**:
- canonical_workflows 완전 호환
- 테스트 용이성
- 역할 명확화

**문서**: Enhanced Design § 2

---

### 2. D-Graph 스키마 정렬 (상) ✅

**피드백**:
- 설계 문서의 D-Graph 스키마가 구버전
- cmis.yaml이 최신 스펙
- Strategy → D-Graph 매핑 불명확

**반영 내용**:

**1) cmis.yaml 최신 스키마 사용**:
```yaml
decision_graph:
  node_types:
    strategy:
      - strategy_id
      - name
      - description
    # pattern_composition은 edge로 표현
  
  edge_types:
    strategy_uses_pattern  # Strategy → Pattern
    strategy_targets_goal  # Strategy → Goal
```

**2) 매핑 테이블 작성**:
| Strategy 필드 | D-Graph 저장 |
|--------------|-------------|
| strategy_id, name, description | strategy 노드 |
| pattern_composition | strategy_uses_pattern edge |
| expected_outcomes | ValueRecord (value_store) |
| execution_fit_score | strategy 노드 traits |
| action_set | strategy 노드 metadata |

**3) 저장/로딩 함수**:
```python
def _save_strategies_to_d_graph(strategies, goal_id, ...):
    """Strategy → D-Graph 노드 + edge"""

def _load_strategy_from_d_graph(strategy_id):
    """D-Graph → Strategy 데이터 클래스"""
```

**문서**: Enhanced Design § 4

---

### 3. ValueEngine ROI 연동 (상) ✅

**피드백**:
- ROI 계산은 원칙적으로 ValueEngine 영역
- StrategyEngine은 시나리오 정의만
- ValueEngine 호출 구조로 개선

**반영 내용**:

**설계 원칙 명확화**:
```
StrategyEngine 역할:
- Strategy 정의 (Pattern 조합)
- Execution Fit 평가
- Risk 평가

ValueEngine 역할:
- ROI/Outcomes Metric 계산
- Pattern Benchmark → Prior
- Simulation
```

**ValueEngine 연동**:
```python
class StrategyEvaluator:
    def __init__(self, value_engine: ValueEngine):
        self.value_engine = value_engine
    
    def predict_outcomes(self, strategy, baseline_state, value_engine):
        # 1. Pattern Benchmark → ValueEngine Prior
        pattern_priors = extract_pattern_priors(strategy.pattern_composition)
        
        # 2. ValueEngine 호출 (Phase 2)
        # value_records = value_engine.evaluate_metrics(
        #     metric_requests=[...],
        #     priors=pattern_priors
        # )
        
        # Phase 1: 간단한 계산 (ValueEngine-lite)
        outcomes = simple_calculation(...)
        
        # Lineage: ValueEngine 형식
        outcomes["lineage"] = {
            "method": "pattern_benchmark_projection",
            "confidence": 0.6,
            "engine": "strategy_engine_phase1"
        }
        
        return outcomes
```

**문서**: Enhanced Design § 5

---

### 4. Constraints 스키마 정렬 (상) ✅

**피드백**:
- project_context_store 스키마와 불일치
- type: "budget" vs type: "financial" + dimension: "budget"

**반영 내용**:

**project_context_store 스키마 준수**:
```python
hard_constraints: [
    {
        "type": "financial",      # cmis.yaml 스키마
        "dimension": "budget",    # 세부 구분
        "threshold": 1000000000,
        "description": "총 예산"
    }
]
```

**StrategyEngine 해석**:
```python
if ctype == "financial" and "budget" in dimension:
    # 예산 제약 처리
```

**Greenfield 정규화**:
```python
def _normalize_greenfield_constraints(constraints):
    """
    Greenfield constraints → constraints_profile 형식
    
    내부 통일: 모두 동일 형식으로 처리
    """
    return {
        "hard_constraints": [
            {"type": "financial", "dimension": "budget", "threshold": ...}
        ]
    }
```

**문서**: Enhanced Design § 6

---

### 5. PolicyEngine 통합 (중) ✅

**피드백**:
- evaluate_portfolio에 policy_ref 인자 없음
- canonical_workflows는 policy_ref 사용
- policy_mode에 따라 평가 다르게

**반영 내용**:

**evaluate_portfolio_api 시그니처**:
```python
def evaluate_portfolio_api(
    strategy_ids: List[str],
    policy_ref: str = "decision_balanced",  # 추가
    project_context_id: Optional[str] = None
) -> str:
    """
    policy_ref 추가
    """
```

**Policy 해석**:
```python
policy_params = _resolve_policy(policy_ref)
# {
#   "risk_tolerance": 0.5,
#   "prior_usage": "balanced",
#   "min_evidence_ratio": 0.5
# }
```

**평가 반영**:
```python
# Risk tolerance 반영
if risk_score > policy_params["risk_tolerance"]:
    # 페널티 또는 제외
```

**문서**: Enhanced Design § 7

---

### 6. Preference Profile 정렬 (중) ✅

**피드백**:
- preference_profile 구조 불일치
- project_context_store는 soft_preferences 형식

**반영 내용**:

**cmis.yaml 스키마 사용**:
```python
soft_preferences: [
    {
        "dimension": "prefer_patterns",
        "value": ["PAT-subscription_model"],
        "weight": 0.8
    }
]
```

**해석 함수**:
```python
def _adjust_by_preferences(strategy, preference_profile):
    for pref in soft_preferences:
        dimension = pref["dimension"]
        value = pref["value"]
        weight = pref["weight"]
        
        if dimension == "prefer_patterns":
            # 보너스 × weight
        elif dimension == "risk_appetite":
            # Risk 기반 조정 × weight
```

**문서**: Enhanced Design § 8

---

### 7. Explore/Decide 모드 (중) ✅

**피드백**:
- OpportunityDesigner (탐색) vs StrategyArchitect (결정)
- policy_mode를 더 명확하게

**반영 내용**:

**모드 추가**:
```python
def search_strategies_api(
    ...,
    mode: str = "decide"  # "explore" | "decide"
):
    if mode == "explore":
        max_strategies = 50
        policy_ref = "exploration_friendly"
    else:
        max_strategies = 10
        policy_ref = "decision_balanced"
```

**Role 연계**:
| Role | Mode | Policy | 전략 수 |
|------|------|--------|--------|
| opportunity_designer | explore | exploration_friendly | 50 |
| strategy_architect | decide | decision_balanced | 10 |

**문서**: Enhanced Design § 9

---

## 추가 고려사항 반영

### 8. 시간축 & Horizon

**고려사항**: Goal.target_horizon과 as_of 관계

**반영**:
- Goal에서 horizon 추출
- baseline as_of → horizon 시뮬레이션
- ValueEngine 연동 시 반영

---

### 9. 불확실성 표현

**고려사항**: confidence float → ValueEngine quality

**반영**:
- ValueRecord 형식 사용
- method, confidence, lineage 포함

---

### 10. LearningEngine 준비

**고려사항**: StrategyLibrary + 학습

**반영**:
- StrategyLibrary 설계 유지
- outcome_store 연동 준비

---

### 11. Explainability

**고려사항**: 전략 추천 근거

**반영**:
- Strategy.lineage 상세화
- 보고서까지 전달

---

## 변경 요약

### Before (v1.0)

**구조**:
- StrategyGenerator/Evaluator/Optimizer
- search_strategies(), evaluate_portfolio()

**문제**:
- cmis.yaml API 불일치
- D-Graph 스키마 구버전
- ValueEngine 연동 약함
- Constraints 스키마 불일치

---

### After (v1.1 Enhanced)

**개선**:
1. **API 3단계** - Public / Orchestration / Core
2. **D-Graph 중심** - cmis.yaml 최신 스키마
3. **ValueEngine 연동** - ROI 계산 위임
4. **스키마 정렬** - project_context_store 준수
5. **PolicyEngine** - policy_ref 통합
6. **Preference** - soft_preferences 형식
7. **Explore/Decide** - 모드 구분

**추가**:
- ADR 4개
- 매핑 테이블
- 정규화 함수

---

## 생성된 문서

1. **StrategyEngine_Design_Enhanced.md** (약 1,500 라인)
   - 피드백 7개 완전 반영
   - API 레벨 분리
   - D-Graph 통합
   - ADR 포함

2. **STRATEGY_ENGINE_FEEDBACK_REVIEW.md** (현재 문서)
   - 피드백 상세 검토
   - 반영 내역
   - 변경 요약

---

## 다음 단계

### StrategyEngine Phase 1 구현

**작업**:
- Strategy, Goal 데이터 모델
- D-Graph 매핑 함수
- StrategyGenerator, Evaluator
- Public API (search_strategies_api)
- 10개 테스트

**예상 시간**: 1주

---

**작성**: 2025-12-11
**상태**: 피드백 검토 및 반영 완료 ✅
**결과**: Enhanced Design v1.1
**다음**: Phase 1 구현
