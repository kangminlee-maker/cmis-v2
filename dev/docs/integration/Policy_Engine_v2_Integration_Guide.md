# Policy Engine v2 통합 가이드

**날짜**: 2025-12-13
**버전**: v2.0

---

## 개요

PolicyEngine v2는 구조화된 입력/출력과 Gate 기반 검증을 사용합니다.

**핵심 변경사항**:
- `resolve_policy()` → `resolve_policy_id()` (메서드명 변경)
- 구조화된 입력: `EvidenceBundleSummary`, `MetricEval`
- 구조화된 출력: `PolicyCheckResult`, `GateViolation`
- `suggested_actions` 포함 (자동 재계획 가능)

---

## 1. EvidenceEngine 연결

### 1.1 출력 형식

EvidenceEngine은 Evidence 수집 후 `EvidenceBundleSummary` 생성:

```python
from cmis_core.policy_engine import EvidenceBundleSummary

# EvidenceEngine에서 반환해야 할 형식
evidence_summary = EvidenceBundleSummary(
    num_sources=3,
    source_tiers_used=["official", "curated"],
    max_age_days=180
)

# 또는 Dict로 반환 (PolicyEngine이 자동 변환)
evidence_dict = {
    "num_sources": 3,
    "source_tiers_used": ["official", "curated"],
    "max_age_days": 180
}
```

### 1.2 PolicyEngine 연동

```python
from cmis_core.policy_engine import PolicyEngine

policy_engine = PolicyEngine()

# Policy 조회 (Evidence 수집 전)
policy_id = policy_engine.resolve_policy_id(
    role_id="structure_analyst",
    usage="reporting"
)
# → "reporting_strict"

evidence_policy = policy_engine.get_evidence_policy(policy_id)

# Evidence 수집 시 Policy 힌트 사용
evidence_bundle = evidence_engine.fetch_for_metrics(
    metric_requests=...,
    min_sources=evidence_policy.min_sources,
    allowed_source_tiers=evidence_policy.allowed_source_tiers,
    require_official_sources=evidence_policy.require_official_sources,
    max_age_days=evidence_policy.max_age_days,
    allow_web=evidence_policy.allow_web
)
```

---

## 2. ValueEngine 연결

### 2.1 출력 형식

ValueEngine은 Metric 계산 후 `MetricEval` 생성:

```python
from cmis_core.policy_engine import MetricEval

# ValueEngine에서 반환해야 할 형식
metric_eval = MetricEval(
    metric_id="MET-TAM",
    literal_ratio=0.75,      # Evidence 직접 사용 비율
    spread_ratio=0.25,       # 불확실성 비율 (CI width / mean)
    confidence=0.85,         # 모델 신뢰도
    methods_used=["evidence_direct", "derived_formula"],
    prior_ratio=0.1,         # Prior 기여 비율
    prior_types_used=["pattern_benchmark"],
    convergence_ratio=0.15   # 방법 간 불일치 비율
)

# 또는 Dict로 반환 (PolicyEngine이 자동 변환)
metric_dict = {
    "metric_id": "MET-TAM",
    "literal_ratio": 0.75,
    "spread_ratio": 0.25,
    "confidence": 0.85,
    "methods_used": ["evidence_direct", "derived_formula"],
    "prior_ratio": 0.1,
    "prior_types_used": ["pattern_benchmark"],
    "convergence_ratio": 0.15
}
```

### 2.2 4-Stage Resolver 통합

```python
# ValueEngine 내부 (pseudo-code)
def evaluate_metrics(self, metric_requests, policy_ref, ...):
    # Policy 조회
    value_policy = self.policy_engine.get_value_policy(policy_ref)
    prior_policy = self.policy_engine.get_prior_policy(policy_ref)
    convergence_policy = self.policy_engine.get_convergence_policy(policy_ref)
    
    results = []
    
    for metric_req in metric_requests:
        # Stage 1: Evidence
        evidence_value, literal_ratio = self._stage_evidence(metric_req)
        
        # Stage 2: Derived
        derived_value = self._stage_derived(metric_req)
        
        # Stage 3: Prior (Policy 확인)
        prior_value = None
        if prior_policy.allow_prior:
            prior_value = self._stage_prior(metric_req)
        
        # Stage 4: Fusion
        final_value, metrics = self._stage_fusion(
            evidence_value, 
            derived_value, 
            prior_value
        )
        
        # MetricEval 생성
        metric_eval = MetricEval(
            metric_id=metric_req.metric_id,
            literal_ratio=metrics["literal_ratio"],
            spread_ratio=metrics["spread_ratio"],
            confidence=metrics["confidence"],
            methods_used=metrics["methods_used"],
            prior_ratio=metrics["prior_ratio"],
            prior_types_used=metrics["prior_types_used"],
            convergence_ratio=metrics.get("convergence_ratio")
        )
        
        results.append(metric_eval)
    
    return results
```

### 2.3 PolicyEngine 검증

```python
# ValueEngine 결과 검증
from cmis_core.policy_engine import PolicyEngine

policy_engine = PolicyEngine()

# 단일 Metric 검증
result = policy_engine.evaluate_metric(
    policy_id="reporting_strict",
    evidence=evidence_summary,
    metric=metric_eval
)

if not result.passed:
    for violation in result.violations:
        print(f"Gate: {violation.gate_id}")
        print(f"Message: {violation.message}")
        print(f"Suggested: {violation.suggested_actions}")

# 배치 검증
batch_result = policy_engine.evaluate_metrics(
    policy_id="reporting_strict",
    evidence=evidence_summary,
    metrics=[metric_eval1, metric_eval2, ...]
)

for metric_id, check_result in batch_result.by_metric.items():
    if not check_result.passed:
        print(f"{metric_id}: FAILED")
        for v in check_result.violations:
            print(f"  - {v.message}")
```

---

## 3. OrchestrationKernel 연결

### 3.1 suggested_actions → Task 변환

```python
# Verifier에서 PolicyEngine 사용
class Verifier:
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
    
    def verify_goal(self, goal, ledgers):
        # Goal의 target_metrics 검증
        policy_id = ledgers.progress_ledger.policy_ref
        evidence_summary = self._extract_evidence_summary(ledgers)
        
        violations_by_metric = {}
        
        for metric_id in goal.target_metrics:
            metric_eval = self._extract_metric_eval(ledgers, metric_id)
            
            result = self.policy_engine.evaluate_metric(
                policy_id=policy_id,
                evidence=evidence_summary,
                metric=metric_eval
            )
            
            if not result.passed:
                violations_by_metric[metric_id] = result.violations
        
        # Diff Report 생성
        return self._generate_diff_report(violations_by_metric)
    
    def _generate_diff_report(self, violations_by_metric):
        """PolicyCheckResult → Diff Report 변환"""
        diff_report = {
            "missing_metrics": [],
            "low_quality_metrics": [],
            "suggested_actions": []
        }
        
        for metric_id, violations in violations_by_metric.items():
            for violation in violations:
                # Gate별 처리
                if violation.gate_id == "value_literal_ratio":
                    diff_report["low_quality_metrics"].append(metric_id)
                
                # suggested_actions 수집
                diff_report["suggested_actions"].extend(
                    violation.suggested_actions
                )
        
        return diff_report
```

### 3.2 Replanner에서 suggested_actions 활용

```python
class Replanner:
    def generate_tasks_from_diff(self, diff_report, goal, ledgers):
        tasks = []
        
        for action in diff_report.get("suggested_actions", []):
            action_type = action.get("type")
            
            if action_type == "fetch_more_evidence":
                tasks.append(Task(
                    task_id=f"TASK-fetch-evidence-{uuid4().hex[:8]}",
                    task_type=TaskType.COLLECT_EVIDENCE,
                    inputs={
                        "min_sources": action.get("min_sources", 2)
                    }
                ))
            
            elif action_type == "run_additional_method":
                tasks.append(Task(
                    task_id=f"TASK-compute-{uuid4().hex[:8]}",
                    task_type=TaskType.COMPUTE_METRIC,
                    inputs={
                        "methods_required": action.get("required", 2)
                    }
                ))
            
            # ... 기타 action types
        
        return tasks
```

---

## 4. 마이그레이션 체크리스트

### EvidenceEngine

- [ ] `fetch_for_metrics()` 반환값에 summary 메타데이터 추가
- [ ] `EvidenceBundleSummary` 생성 로직 구현
- [ ] PolicyEngine에서 evidence_policy 힌트 받아서 사용

### ValueEngine

- [ ] `evaluate_metrics()` 반환값에 `MetricEval` 포함
- [ ] 4-Stage Resolver에서 literal_ratio, prior_ratio 계산
- [ ] convergence_ratio 계산 (methods_required > 1일 때)
- [ ] PolicyEngine 검증 호출

### WorkflowOrchestrator

- [x] `resolve_policy()` → `resolve_policy_id()` 변경
- [ ] Workflow 결과에 PolicyCheckResult 포함

### OrchestrationKernel

- [ ] Verifier가 PolicyEngine 사용
- [ ] Replanner가 suggested_actions → Task 변환
- [ ] Governor가 orchestration_policy 사용

---

## 5. 사용 예시

### 5.1 전체 플로우

```python
from cmis_core.policy_engine import PolicyEngine
from cmis_core.workflow import WorkflowOrchestrator

# 1. Policy 결정
policy_engine = PolicyEngine()
policy_id = policy_engine.resolve_policy_id(
    role_id="structure_analyst",
    usage="reporting"
)
# → "reporting_strict"

# 2. Workflow 실행 (Policy 힌트 사용)
workflow_orch = WorkflowOrchestrator()
result = workflow_orch.run_workflow(
    workflow_id="structure_analysis",
    inputs={"domain_id": "...", "region": "KR"},
    role_id="structure_analyst"
)

# 3. Policy 검증
evidence_summary = result["evidence_summary"]
metrics = result["metrics"]

check_result = policy_engine.evaluate_metrics(
    policy_id=policy_id,
    evidence=evidence_summary,
    metrics=metrics
)

# 4. 위반 처리
if not check_result.passed:
    for metric_id, result in check_result.by_metric.items():
        if not result.passed:
            print(f"{metric_id} violations:")
            for v in result.violations:
                print(f"  - {v.message}")
                print(f"  Suggested: {v.suggested_actions}")
```

---

## 6. 추가 유틸리티 (제안)

### 6.1 PolicyEngine 유틸리티 메서드

```python
# policy_engine.py에 추가

def extract_all_suggested_actions(
    self, 
    check_result: PolicyCheckResult
) -> List[Dict[str, Any]]:
    """모든 suggested_actions 추출"""
    actions = []
    for violation in check_result.violations:
        actions.extend(violation.suggested_actions)
    return actions

def summarize_violations(
    self, 
    check_result: PolicyCheckResult
) -> Dict[str, int]:
    """위반 gate별 개수 집계"""
    summary = {}
    for violation in check_result.violations:
        gate_id = violation.gate_id
        summary[gate_id] = summary.get(gate_id, 0) + 1
    return summary
```

---

**작성**: 2025-12-13
**버전**: v2.0
**상태**: 통합 가이드

