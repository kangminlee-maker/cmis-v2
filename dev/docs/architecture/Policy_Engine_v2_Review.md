# Policy Engine v2 검토 결과

**날짜**: 2025-12-13
**검토자**: AI Assistant
**버전**: v2.0

---

## 📋 검토 요약

### ✅ 우수한 점 (Strengths)

#### 1. 선언적 YAML 구조

```yaml
# 명확한 routing
routing:
  by_usage: {reporting: reporting_strict, ...}
  by_role: {structure_analyst: reporting_strict, ...}
  fallback: decision_balanced

# Profile 기반 재사용성
profiles:
  evidence_profiles: {...}
  value_profiles: {...}
  prior_profiles: {...}
  convergence_profiles: {...}
  orchestration_profiles: {...}

# Mode = Profile 조합 + Gates
modes:
  reporting_strict:
    profiles: {evidence: evidence_strict, value: value_strict, ...}
    gates: [evidence_min_sources, value_literal_ratio, ...]
```

**장점**:
- 정책 변경 시 코드 수정 불필요
- Profile 재사용으로 일관성 확보
- Gates 리스트로 검증 로직 명확화

---

#### 2. 구조화된 타입 시스템

```python
# 입력 (ValueEngine/EvidenceEngine → PolicyEngine)
EvidenceBundleSummary(num_sources, source_tiers_used, max_age_days)
MetricEval(metric_id, literal_ratio, spread_ratio, confidence, ...)

# 정책 (CompiledPolicy)
EvidencePolicy, ValuePolicy, PriorPolicy
ConvergencePolicy, OrchestrationPolicy

# 출력 (PolicyEngine → Orchestration)
GateViolation(gate_id, message, details, suggested_actions)
PolicyCheckResult(policy_id, passed, violations)
PolicyBatchResult(policy_id, passed, by_metric)
```

**장점**:
- 타입 안전성 (dataclass + frozen)
- 명확한 입력/출력 계약
- 타 모듈과 연결 인터페이스 명확

---

#### 3. GateRegistry 패턴

```python
class GateRegistry:
    def register(self, gate_id: str, fn: GateFn)
    def run(self, gate_id: str, ...) -> List[GateViolation]

# 게이트 함수 시그니처
GateFn = Callable[[CompiledPolicy, EvidenceBundleSummary, MetricEval], List[GateViolation]]
```

**장점**:
- 확장 가능 (새 게이트 추가 용이)
- 게이트별 독립적 검증
- 테스트 용이

---

#### 4. suggested_actions 기반 자동 재계획

```python
GateViolation(
    gate_id="value_literal_ratio",
    message="Literal ratio too low: 0.4 < 0.7",
    suggested_actions=[
        {"type": "fetch_more_direct_evidence"}
    ]
)
```

**장점**:
- Replanner가 suggested_actions → Task 변환 가능
- 자동 재계획 기반 마련
- Evidence-first 원칙 강제

---

#### 5. 5-Profile 분리

```python
# Evidence-first 철학 강제
evidence_profiles:  # Evidence 수집 정책
  evidence_strict: {min_sources: 2, require_official_sources: true}

value_profiles:     # Value 품질 정책
  value_strict: {min_literal_ratio: 0.7, max_spread_ratio: 0.3}

prior_profiles:     # Prior 사용 정책
  prior_none: {allow_prior: false, max_prior_ratio: 0.0}

convergence_profiles:  # 방법 간 수렴 정책
  conv_default: {default_threshold: 0.3, methods_required: 1}

orchestration_profiles:  # Orchestration 제어
  orch_strict: {stall_threshold: 1, allow_partial_replan: true}
```

**장점**:
- 관심사 분리 (Separation of Concerns)
- 각 엔진별 정책 독립 관리
- Orchestration 정책 포함 (통합)

---

### ⚠️ 보완 필요 사항

#### 1. 타 모듈 연결 (Integration)

**상태**: 통합 가이드 작성 완료 ✅

**필요한 작업**:
- [ ] EvidenceEngine: `EvidenceBundleSummary` 생성
- [ ] ValueEngine: `MetricEval` 생성
- [ ] WorkflowOrchestrator: `resolve_policy_id()` 호출 (완료 ✅)
- [ ] OrchestrationKernel: Verifier/Replanner 통합

**문서**: `Policy_Engine_v2_Integration_Guide.md` 참고

---

#### 2. ValueEngine 4-Stage Resolver 연동

**현재**: ValueEngine이 `MetricEval` 반환하지 않음

**필요**:
```python
# ValueEngine.evaluate_metrics() 반환값 확장
{
    "value_records": [...],
    "value_program": {...},
    "metric_evals": [  # 신규
        MetricEval(
            metric_id="MET-TAM",
            literal_ratio=0.75,
            spread_ratio=0.25,
            confidence=0.85,
            methods_used=["evidence_direct", "derived_formula"],
            prior_ratio=0.1,
            prior_types_used=["pattern_benchmark"],
            convergence_ratio=0.15
        ),
        ...
    ]
}
```

---

#### 3. Orchestration 통합 세부 사항

**Verifier**:
```python
class Verifier:
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine

    def verify_goal(self, goal, ledgers):
        # PolicyEngine 사용
        policy_id = ledgers.progress_ledger.policy_ref

        # Evidence Summary 추출
        evidence_summary = self._extract_evidence_summary(ledgers)

        # Metric Eval 추출
        metric_evals = []
        for metric_id in goal.target_metrics:
            metric_eval = self._extract_metric_eval(ledgers, metric_id)
            metric_evals.append(metric_eval)

        # Policy 검증
        batch_result = self.policy_engine.evaluate_metrics(
            policy_id=policy_id,
            evidence=evidence_summary,
            metrics=metric_evals
        )

        # Diff Report 생성
        diff_report = self._convert_to_diff_report(batch_result)

        return {
            "satisfied": batch_result.passed,
            "diff_report": diff_report,
            "policy_check_result": batch_result
        }
```

**Replanner**:
```python
class Replanner:
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine

    def generate_tasks_from_diff(self, diff_report, goal, ledgers):
        tasks = []

        # suggested_actions 추출
        policy_result = diff_report.get("policy_check_result")
        if policy_result:
            actions = self.policy_engine.extract_all_suggested_actions(policy_result)

            # Action → Task 변환
            for action in actions:
                task = self._action_to_task(action)
                if task:
                    tasks.append(task)

        return tasks

    def _action_to_task(self, action: Dict[str, Any]) -> Optional[Task]:
        action_type = action.get("type")

        if action_type == "fetch_more_evidence":
            return Task(
                task_type=TaskType.COLLECT_EVIDENCE,
                inputs={"min_sources": action.get("min_sources", 2)}
            )

        elif action_type == "run_additional_method":
            return Task(
                task_type=TaskType.COMPUTE_METRIC,
                inputs={"methods_required": action.get("required", 2)}
            )

        # ... 기타 action types

        return None
```

---

#### 4. 추가 유틸리티 메서드 (완료 ✅)

**추가됨**:
- `extract_all_suggested_actions()`: suggested_actions 추출
- `summarize_violations()`: gate별 위반 개수 집계
- `get_failed_metrics()`: 실패한 metric_id 리스트

---

### 🎯 추가 개선 제안

#### 1. Gate 확장 예시

**custom gate 등록**:
```python
def _gate_custom_domain_specific(
    policy: CompiledPolicy,
    evidence: EvidenceBundleSummary,
    metric: MetricEval
) -> List[GateViolation]:
    """도메인 특화 검증 (예: 금융 규제 준수)"""
    violations = []

    # 커스텀 로직
    if metric.metric_id.startswith("MET-Revenue"):
        if "official" not in evidence.source_tiers_used:
            violations.append(GateViolation(
                gate_id="custom_domain_specific",
                message="Revenue metrics require official sources (regulatory)",
                suggested_actions=[{"type": "fetch_official_sources"}]
            ))

    return violations

# 등록
policy_engine.gates.register("custom_domain_specific", _gate_custom_domain_specific)
```

---

#### 2. Metric-specific Policy Override

**현재**: convergence_policy에만 metric_specific 있음

**제안**: value_policy, prior_policy에도 추가

```yaml
# policies.yaml 확장 제안
value_profiles:
  value_strict_with_overrides:
    min_literal_ratio: 0.7
    max_spread_ratio: 0.3
    min_confidence: 0.8

    # Metric-specific overrides (제안)
    metric_specific:
      MET-Revenue:
        min_literal_ratio: 0.9  # Revenue는 더 엄격
      MET-Customer_Count:
        min_literal_ratio: 0.6  # Customer Count는 약간 완화
```

**구현**:
```python
@dataclass(frozen=True)
class ValuePolicy:
    min_literal_ratio: float
    max_spread_ratio: float
    min_confidence: float
    metric_specific: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def for_metric(self, metric_id: str) -> "ValuePolicy":
        """Metric-specific override 적용"""
        if metric_id not in self.metric_specific:
            return self

        overrides = self.metric_specific[metric_id]
        return ValuePolicy(
            min_literal_ratio=overrides.get("min_literal_ratio", self.min_literal_ratio),
            max_spread_ratio=overrides.get("max_spread_ratio", self.max_spread_ratio),
            min_confidence=overrides.get("min_confidence", self.min_confidence),
            metric_specific=self.metric_specific
        )
```

---

#### 3. Policy 버전 관리

**제안**: policies.yaml에 버전 및 변경 이력 포함

```yaml
policy_pack:
  schema_version: 2
  pack_version: "2.1.0"
  last_updated: "2025-12-13"

  # 변경 이력
  changelog:
    - version: "2.1.0"
      date: "2025-12-13"
      changes:
        - "Add orchestration_profiles"
        - "Add convergence_methods_required gate"

    - version: "2.0.0"
      date: "2025-12-10"
      changes:
        - "Redesign to profile-based structure"
        - "Add suggested_actions to violations"
```

---

#### 4. Dry-run Mode

**제안**: Policy 검증을 실제 적용 전 테스트

```python
# policy_engine.py 추가
def dry_run_policy(
    self,
    policy_id: str,
    evidence: EvidenceBundleSummary,
    metrics: List[MetricEval]
) -> Dict[str, Any]:
    """
    Dry-run policy check (로그만 출력, 실제 적용 안 함)

    Returns:
        {
            "would_pass": True/False,
            "violations": [...],
            "summary": {...}
        }
    """
    result = self.evaluate_metrics(policy_id, evidence, metrics)

    return {
        "would_pass": result.passed,
        "violations": [v.to_dict() for v in self._collect_all_violations(result)],
        "summary": self.summarize_violations(result)
    }
```

---

## 📝 체크리스트

### PolicyEngine v2 (완료 ✅)
- [x] policies.yaml v2 구조
- [x] PolicyEngine 클래스 구현
- [x] GateRegistry 패턴
- [x] 8개 기본 게이트 구현
- [x] suggested_actions 생성
- [x] 유틸리티 메서드 (extract_all_suggested_actions, summarize_violations, get_failed_metrics)

### 통합 작업 (진행 중)
- [x] WorkflowOrchestrator 수정 (`resolve_policy_id()`)
- [x] 통합 가이드 작성
- [ ] EvidenceEngine 수정 (`EvidenceBundleSummary` 생성)
- [ ] ValueEngine 수정 (`MetricEval` 생성)
- [ ] OrchestrationKernel: Verifier 통합
- [ ] OrchestrationKernel: Replanner 통합
- [ ] OrchestrationKernel: Governor 통합 (orchestration_policy 사용)

### 테스트 (TODO)
- [ ] PolicyEngine 단위 테스트 (10개)
- [ ] 각 Gate 테스트 (8개)
- [ ] 통합 테스트 (5개)

---

## 🎉 결론

**PolicyEngine v2는 훌륭한 설계입니다!**

**핵심 강점**:
1. ✅ 선언적 YAML (코드 변경 없이 정책 수정)
2. ✅ Profile 기반 재사용성
3. ✅ Gate 기반 확장성
4. ✅ suggested_actions로 자동 재계획 가능
5. ✅ 구조화된 타입 (타 모듈 연결 명확)

**보완 필요**:
1. ⚠️ EvidenceEngine, ValueEngine 수정 (출력 형식 변경)
2. ⚠️ OrchestrationKernel 통합 (Verifier/Replanner/Governor)
3. ⚠️ 테스트 작성

**추가 제안**:
- Metric-specific overrides (value_policy, prior_policy)
- Policy 버전 관리
- Dry-run mode
- Custom gate 등록 (도메인 특화)

---

**검토일**: 2025-12-13
**상태**: ✅ 승인 (통합 작업 진행 가능)
**다음**: EvidenceEngine/ValueEngine 수정, OrchestrationKernel 통합

