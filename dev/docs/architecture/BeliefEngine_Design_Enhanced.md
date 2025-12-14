# BeliefEngine 설계 (v1.0, Production Ready)

**작성일**: 2025-12-12
**최종 업데이트**: 2025-12-14
**상태**: Production Ready
**역할**: Evidence 부족 시 Prior/Belief 제공 + Outcome 기반 업데이트 + 불확실성 전파

---

## 1. CMIS 내 위치와 철학 정렬

BeliefEngine은 CMIS의 Prior/Belief를 전담합니다. Evidence-first, Prior-last 철학에 따라:

- Prior는 ValueEngine의 4-stage resolver에서 **Stage 3(Prior)** 에서만 사용합니다.
- Prior는 항상 `origin="prior"`로 표기되고 lineage로 역추적 가능해야 합니다.
- `reporting_strict`에서는 Prior를 “마지막 수단”으로 제한하고 더 보수적으로 취급합니다.

관련 구성요소:

- **Substrate**: `value_store`(VAL-*)에 Prior/Belief 영속화
- **PolicyEngine**: policy_mode에 따라 confidence/spread 조정
- **LearningEngine**: Outcome → Belief update 트리거

---

## 2. 단일 진실원천(SSoT) 모델: Belief = 특수 ValueRecord

Belief/Prior는 별도 store를 만들지 않고 `value_store`에 ValueRecord 형태로 저장합니다.

- **origin**: `prior` | `learned`
- **literal_ratio**: Prior는 0.0
- **value_id 예시**: `VAL-BELIEF-...` 또는 `VAL-PRIOR-...` (구현체에서 prefix 규칙을 따름)

장점:

- ValueGraph/ValueStore/Lineage 규약을 그대로 사용
- Orchestration/Verifier에서 “근거 없는 수치”를 자동 검증하기 쉬움

---

## 3. 데이터 모델

핵심 레코드: `BeliefRecord` (`cmis_core/types.py`)

- **식별**: belief_id, metric_id, context
- **분포**: distribution(type, params, percentiles 또는 samples_ref)
- **신뢰**: confidence(0~1), source(`pattern_benchmark` | `uninformative` | `learned` | `domain_expert`)
- **관측**: observations, n_observations
- **시간**: created_at, updated_at
- **계보**: lineage(from_evidence_ids, from_outcome_ids, from_prior_id, engine_ids 등)

---

## 4. Public API

현재 코드 기준(`cmis_core/belief_engine.py`):

- `query_prior_api(metric_id, context, policy_ref=None) -> {distribution_ref, distribution, confidence, source, lineage, ...}`
- `update_belief_api(metric_id, context, observations, update_mode="bayesian") -> {belief_id, prior, posterior, delta, lineage}`
- `propagate_uncertainty_api(formula, input_distributions, n_samples=10000) -> {percentiles, statistics, samples_ref, ...}`

Contract 정렬 메모:

- `cmis.yaml`은 contracts/registry 성격상 API를 “최소 계약”으로만 적어두는 경우가 있어, 실제 코드 API 명과 1:1 정렬이 남아 있을 수 있습니다.
  - `get_prior` ≈ `query_prior_api`
  - `update_from_learning` ≈ `update_belief_api`

---

## 5. Prior 생성 전략

권장 우선순위:

1. **Direct/Derived Evidence**: BeliefEngine 호출 이전에 ValueEngine에서 해결
2. **Pattern Benchmark Prior**: 유사 pattern + context 유사도 기반 가중 결합
3. **Learned Prior**: 누적 Outcome 업데이트 결과
4. **Uninformative Prior**: 마지막 fallback(매우 넓은 분포)

Context 유사도 가중치(예시):

- domain_id 0.4
- region 0.3
- segment 0.2
- scale_tier 0.1

---

## 6. 업데이트(학습) 전략

- **트리거**: Outcome vs 예측 오차가 metric_spec의 `target_convergence` 기준을 초과할 때
- **방식**:
  - Normal/Lognormal/Beta-Binomial conjugate update
  - Empirical update(비모수) fallback
- **드리프트 알림**: mean shift 등 큰 변화는 별도 alert 객체로 기록(모니터링/회귀 감지)

---

## 7. 불확실성 전파(Uncertainty Propagation)

- Monte Carlo로 formula 기반 분포 전파
- 안전성 원칙:
  - `eval()` 금지
  - AST 기반 evaluator 사용
  - raw samples는 `artifact_store`에 저장하고 ref만 반환

---

## 8. Policy 통합

policy_mode별 조정 예:

- `reporting_strict`: confidence 낮추고 spread 크게(보수)
- `decision_balanced`: 기본
- `exploration_friendly`: prior 활용 허용(과도한 spread는 제한)

---

## 9. 통합 지점

- **ValueEngine**: 4-stage resolver Stage 3(prior)에서 BeliefEngine 호출
- **LearningEngine**: Outcome 비교 후 `update_belief_api()` 호출
- **Orchestration/Verifier**: prior 사용률/quality gate, lineage check

---

## 10. Roadmap

- **v1.1**: Human-in-the-loop(propose/approve/reject)
- **v1.2**: Joint Belief(다변량, copula)
- **v1.2**: Active Learning(VOI 기반 evidence 우선순위)
- **v2.0**: Causal inference(DAG/Do-calculus)

---

## 11. 문서 이력

(v3.6 문서 정리) 기존 분절 문서는 `dev/deprecated/docs/architecture_v3.6/`로 이동했습니다.
