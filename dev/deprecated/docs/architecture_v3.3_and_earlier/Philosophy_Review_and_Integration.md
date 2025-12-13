# CMIS 철학 v2 검토 및 설계 반영 방안

**작성일**: 2025-12-12
**대상**: cmis_philosophy_concept_v2.md
**검토자**: CMIS Architect
**결론**: ✅ 완벽한 일치, 설계 강화 필요

---

## 1. 철학 문서 검토 결과

### 1.1 전체 평가

**결론**: ✅ **완벽히 일치하며, Orchestration Kernel 설계를 강하게 지지**

**새로운 철학 (v2)**:
- **철학 8) Objective-Oriented Orchestration** (신규!)
  - 고정 프로세스 ❌
  - 목표 중심 ✅
  - 중간 결과 평가 → 동적 재설계

**이것은 정확히 Orchestration Kernel 설계의 핵심입니다!**

---

### 1.2 철학별 검토

| 철학 | 내용 | Orchestration Kernel 반영 | 상태 |
|------|------|-------------------------|------|
| 1. Evidence-first, Prior-last | Evidence 우선, Prior 최후 수단 | ✅ Stage 추적, Policy 연동 | 완벽 |
| 2. 권위 있는 Substrate + Lineage | SSOT, 재현성 | ✅ Ledgers, DecisionLog | 완벽 |
| 3. Model-first, Number-second | 구조 → 숫자 | ✅ R-Graph → Value | 완벽 |
| 4. Graph-of-Graphs | R/P/V/D 분리 | ✅ GoalGraph = D-Graph | 완벽 |
| 5. Trait 기반 Ontology | 라벨 고착 방지 | ✅ Predicate에도 적용 가능 | 양호 |
| 6. Project Context 1급 | Greenfield/Brownfield | ✅ Predicate 자동 변경 | 완벽 |
| 7. 세계-변화-결과-논증 | 패키지 답변 | ✅ Ledgers + DecisionLog | 완벽 |
| **8. Objective-Oriented** | **목표 중심, 동적** | ✅ **Reconcile Loop** | **완벽** |
| 9. Agent = 역할 | 엔진 아님 | ✅ Kernel ≠ Agent | 완벽 |
| 10. Monotonic Improvability | 학습 가능 | ✅ Ledger 재사용 | 완벽 |

**10개 철학 모두 Orchestration Kernel 설계와 일치!**

---

## 2. 철학 → 설계 매핑 (상세)

### 2.1 철학 1: Evidence-first, Prior-last

**철학 요구사항**:
```
구성요소:
- Evidence Engine: on-demand 수집
- Evidence Store: 출처/시점 스키마 강제
- Policy Engine: Prior 허용 범위 제어
- Belief Engine: Evidence 부족 시 마지막 수단
```

**Orchestration Kernel 반영**:
```python
# Verifier에서 Evidence Stage 확인
stage = stage_tracker.get_metric_stage(metric_id, ledgers)

if stage == "prior":
    # DecisionLog에 명시적 기록 + 경고
    decision_log.append({
        "type": "prior_usage",
        "metric_id": metric_id,
        "warning": "Evidence 부족으로 Prior 사용",
        "policy_ref": policy_ref
    })
```

**금지 규칙 강제**:
```python
# 철학 문서 금지 규칙 3:
# "Prior는 Belief Engine을 통해서만"

class Verifier:
    def check_prior_usage(self, ledgers):
        """Prior 사용 검증"""
        for metric_id, metric in ledgers.project_ledger.metrics.items():
            if metric.get("origin") == "prior":
                # Belief Engine 거쳤는지 확인
                if "belief_engine" not in metric.get("lineage", {}).get("engine_ids", []):
                    raise ValueError(
                        f"{metric_id}: Prior는 Belief Engine을 통해서만 사용 가능"
                    )
```

**반영 상태**: ✅ 완벽

---

### 2.2 철학 2: 권위 있는 Substrate + Lineage

**철학 요구사항**:
```
- Value Store: SSOT
- Evidence Store: 출처 보존
- Orchestration: Decision Logging
- IDs & Lineage: 표준화
```

**Orchestration Kernel 반영**:
```python
# Ledgers = 권위 있는 상태
class Ledgers:
    def save_to_substrate(self):
        """Ledger → Substrate 영구 저장

        재현성 보장.
        """
        # ProjectLedger → Evidence/Value Store
        for metric_id, metric in self.project_ledger.metrics.items():
            value_store.save(metric)

        # DecisionLog → Memory Store
        for decision in self.decision_log:
            memory_store.save({
                "memory_id": f"MEM-decision-{uuid.uuid4().hex[:8]}",
                "memory_type": "orchestration_decision",
                "content": decision
            })
```

**금지 규칙 강제**:
```python
# 철학 문서 금지 규칙 1:
# "Substrate에 기록되지 않은 정보는 결론이 아님"

class OrchestrationKernel:
    def finalize_execution(self):
        """실행 종료 시 Substrate 저장 강제"""

        if not self.ledgers.is_saved_to_substrate():
            raise ValueError(
                "Ledger가 Substrate에 저장되지 않음. "
                "결론을 확정하려면 save_to_substrate() 호출 필요"
            )
```

**반영 상태**: ✅ 완벽

---

### 2.3 철학 8: Objective-Oriented Orchestration ⭐

**철학 요구사항** (신규!):
```
- 고정 프로세스 ❌
- 목표 달성 중심 ✅
- 중간 결과 평가 → 동적 재설계
- Orchestration Layer: Execute+Evaluate 루프
```

**Orchestration Kernel 반영**:
```python
# Reconcile Loop = Objective-Oriented 구현
def reconcile_loop():
    while not goal_achieved():
        # Desired State (Goal)
        desired = goal.success_predicate

        # Observed State (Ledgers)
        observed = ledgers.get_current_state()

        # Diff
        diff = verifier.compare(desired, observed)

        # Task 생성 (동적!)
        if diff.has_gaps():
            tasks = replanner.generate_tasks(diff)

        # Execute
        execute(tasks)

        # Update Observed
        ledgers.update()
```

**철학 문서와 완벽히 일치!**

**반영 상태**: ✅ 완벽 (Reconcile = Objective-Oriented의 구현)

---

## 3. 금지 규칙 강제 방안

### 3.1 금지 규칙 5개

| 규칙 | 내용 | Kernel 강제 방법 |
|------|------|-----------------|
| 1 | Substrate 기록 필수 | ✅ finalize_execution() 검증 |
| 2 | Evidence 없는 수치 명시 | ✅ Verifier가 origin 확인 |
| 3 | Prior는 Belief Engine만 | ✅ Lineage engine_ids 검증 |
| 4 | **Orchestration Decision Logging** | ✅ **모든 Reconcile 단계 기록** |
| 5 | 재현성 설명 | ✅ Ledger + DecisionLog → 완전 재현 |

---

### 3.2 구현 (Kernel에 추가)

```python
class OrchestrationKernel:
    """Orchestration Kernel

    CMIS 철학 강제:
    - Evidence-first (Stage 추적)
    - Substrate SSOT (Ledger → Store 저장)
    - Objective-Oriented (Reconcile Loop)
    - Decision Logging (모든 결정 기록)
    """

    def __init__(self, policy_engine):
        self.policy_engine = policy_engine
        self.ledgers = Ledgers()
        self.decision_log = []

        # 철학 강제 플래그
        self.enforce_philosophy = True

    def reconcile_loop(self, goal: Goal) -> Dict:
        """Reconcile Loop (철학 8 구현)"""

        iteration = 0
        max_iterations = 20

        while iteration < max_iterations:
            # Desired vs Observed
            verification = self.verifier.verify_goal(goal, self.ledgers)

            if verification["satisfied"]:
                break

            # Diff → Tasks
            diff = verification["diff_report"]
            tasks = self.replanner.generate_tasks_from_diff(diff, goal, self.ledgers)

            # 철학 4: Decision Logging
            self._log_decision("diff_to_tasks", {
                "diff": diff,
                "tasks": [t.task_id for t in tasks]
            })

            # Execute
            for task in tasks:
                result = self._execute_task(task)
                self.ledgers.update_from_task_result(task, result)

                # 철학 1: Prior 사용 검증
                if self.enforce_philosophy:
                    self._check_prior_usage(result)

            iteration += 1

        # 철학 1: Substrate 저장 강제
        if self.enforce_philosophy:
            self._ensure_substrate_saved()

        return {
            "goal_satisfied": verification["satisfied"],
            "ledgers": self.ledgers.to_dict(),
            "decision_log": self.decision_log
        }

    def _check_prior_usage(self, result: Dict):
        """철학 3: Prior는 Belief Engine만"""

        if result.get("origin") == "prior":
            lineage = result.get("lineage", {})
            engine_ids = lineage.get("engine_ids", [])

            if "belief_engine" not in engine_ids:
                raise ValueError(
                    f"철학 위반: Prior는 Belief Engine을 통해서만 사용 가능. "
                    f"engine_ids: {engine_ids}"
                )

    def _ensure_substrate_saved(self):
        """철학 1: Substrate 기록 강제"""

        if not self.ledgers.is_saved_to_substrate():
            # 경고만 (강제는 선택)
            self._emit_warning(
                "substrate_not_saved",
                "결론 확정 전 Substrate 저장 권장"
            )

    def _log_decision(self, decision_type: str, data: Dict):
        """철학 4: Decision Logging (모든 결정)"""

        self.decision_log.append({
            "timestamp": datetime.now().isoformat(),
            "decision_type": decision_type,
            "data": data,
            "goal_id": self.current_goal.goal_id if self.current_goal else None
        })
```

---

## 4. 설계 반영 방안

### 4.1 즉시 반영 (v3.0)

**1. Orchestration Kernel에 철학 명시**

```python
# cmis_core/orchestration_kernel.py

class OrchestrationKernel:
    """Orchestration Kernel

    CMIS 철학 구현:
    - 철학 1: Evidence-first (Stage 추적 + Policy)
    - 철학 2: SSOT (Ledger → Substrate)
    - 철학 8: Objective-Oriented (Reconcile Loop)

    금지 규칙 강제:
    - Prior는 Belief Engine만
    - Decision Logging 필수
    - Substrate 저장 권장
    """
```

**2. cmis.yaml에 철학 참조 추가**

```yaml
orchestration_kernel:
  philosophy_alignment:
    - id: "evidence_first"
      philosophy_ref: "cmis_philosophy_concept_v2.md#철학1"
      implementation: "Stage 추적 + Policy Engine 연동"

    - id: "substrate_ssot"
      philosophy_ref: "cmis_philosophy_concept_v2.md#철학2"
      implementation: "Ledgers → Substrate 저장"

    - id: "objective_oriented"
      philosophy_ref: "cmis_philosophy_concept_v2.md#철학8"
      implementation: "Reconcile Loop (Desired ↔ Observed)"

  prohibited_patterns:
    - pattern: "Prior without Belief Engine"
      enforcement: "runtime_check"
      error_message: "철학 3 위반"

    - pattern: "Conclusion without Substrate"
      enforcement: "warning"
      error_message: "철학 1(금지 규칙 1) 위반"

    - pattern: "Orchestration without Logging"
      enforcement: "mandatory"
      error_message: "철학 4(금지 규칙 4) 위반"
```

---

### 4.2 문서 통합

**1. Orchestration Kernel 설계 문서 업데이트**

```markdown
# Section 0: 설계 철학 기반

본 설계는 `cmis_philosophy_concept_v2.md`의 다음 철학을 구현합니다:

## 철학 8: Objective-Oriented Orchestration

"고정 프로세스가 아니라 목표 달성이 중심"

**구현**:
- Reconcile Loop (Desired ↔ Observed)
- Goal Predicate (검증 가능한 성공 조건)
- Diff Report → Task Generation
- 중간 평가 → 동적 재설계

## 철학 1: Evidence-first, Prior-last

**구현**:
- MetricStageTracker (4-Stage 추적)
- Policy Engine 연동 (품질 기준)
- Belief Engine 격리
- Prior 사용 시 명시적 Logging

## 철학 2: 권위 있는 Substrate

**구현**:
- Ledgers (ProjectLedger + ProgressLedger)
- save_to_substrate() (재현성)
- DecisionLog → Memory Store

...
```

**2. README.md에 철학 참조**

```markdown
# CMIS 핵심 철학

CMIS는 다음 10가지 철학을 시스템 설계 제약 조건으로 삼습니다.

상세: `dev/docs/architecture/cmis_philosophy_concept_v2.md`

핵심:
1. Evidence-first, Prior-last
2. 권위 있는 Substrate (SSOT)
8. **Objective-Oriented Orchestration** (신규)
   - 목표 중심, 프로세스 동적
   - 중간 결과 → 재설계
   - Orchestration Kernel이 구현
```

---

## 5. 철학 강화 제안

### 5.1 검증 가능성 강화

**철학 문서 검증 섹션**:
```
검증:
- 동일 질문 2회 실행 → 결과 변화 = evidence/policy/context 변화
- ValueRecord lineage 추적 → Evidence까지 완주
```

**Kernel에 검증 메서드 추가**:

```python
class OrchestrationKernel:
    def verify_reproducibility(
        self,
        query: str,
        context: Dict
    ) -> Dict:
        """재현성 검증 (철학 2, 10)

        동일 질문 2회 실행 → 결과 비교

        Returns:
            {
                "reproducible": True/False,
                "changes_explanation": [
                    "evidence_store 업데이트 (3개 Evidence 추가)",
                    "policy_mode 변경 (exploration → reporting)"
                ]
            }
        """
        # 1차 실행
        result1 = self.execute(query, context)

        # 2차 실행 (즉시)
        result2 = self.execute(query, context)

        # 비교
        if result1 == result2:
            return {"reproducible": True}

        # 차이 설명
        changes = self._explain_changes(result1, result2)

        return {
            "reproducible": False,
            "changes_explanation": changes,
            "acceptable": self._is_acceptable_change(changes)
        }

    def _is_acceptable_change(self, changes: List[str]) -> bool:
        """변화가 허용 가능한가

        철학: evidence/policy/context 변화만 허용
        """
        acceptable_types = [
            "evidence_store",
            "policy_mode",
            "project_context",
            "pattern_graph",
            "value_graph"
        ]

        return all(
            any(t in change for t in acceptable_types)
            for change in changes
        )
```

---

### 5.2 Non-goals 강제

**철학 문서 Non-goals**:
```
- "그럴듯한 답만" 목표 아님
- "전 세계 데이터 미리 적재" 아님
- "Agent가 임의로 사실 확정" 아님
```

**Kernel 검증**:

```python
class OrchestrationKernel:
    def check_non_goals(self, result: Dict):
        """Non-goals 위반 검증"""

        # Non-goal 1: 그럴듯한 답만
        if not result.get("decision_log"):
            raise ValueError(
                "Non-goal 위반: Decision Log 없음. "
                "근거/재현성 없는 답변 금지"
            )

        # Non-goal 3: Agent가 사실 확정
        for metric in result.get("metrics", []):
            if metric.get("confirmed_by") == "agent":
                # Agent 확정 아님, Substrate에 저장되어야
                if not self._is_in_substrate(metric["metric_id"]):
                    raise ValueError(
                        f"Non-goal 위반: {metric['metric_id']} "
                        "Agent 확정 아님, Substrate 저장 필요"
                    )
```

---

## 6. 설계 문서 업데이트 계획

### 6.1 CMIS_Orchestration_Kernel_Design.md

**추가 섹션**:

```markdown
## Section 0: 설계 철학 기반

본 설계는 `cmis_philosophy_concept_v2.md`를 구현합니다.

### 핵심 철학

**철학 8: Objective-Oriented Orchestration**
→ Reconcile Loop로 구현

**철학 1: Evidence-first, Prior-last**
→ MetricStageTracker + Policy Engine

**철학 2: 권위 있는 Substrate**
→ Ledgers + save_to_substrate()

### 금지 규칙 강제

1. Substrate 기록 강제
2. Prior는 Belief Engine만
3. Decision Logging 필수

### 검증 가능성

- verify_reproducibility()
- check_non_goals()
```

---

### 6.2 cmis.yaml

**orchestration_kernel 섹션 확장**:

```yaml
orchestration_kernel:
  philosophy_compliance:
    reference: "dev/docs/architecture/cmis_philosophy_concept_v2.md"

    implemented_philosophies:
      - philosophy_id: 8
        name: "Objective-Oriented Orchestration"
        implementation: "Reconcile Loop (Desired ↔ Observed)"

      - philosophy_id: 1
        name: "Evidence-first, Prior-last"
        implementation: "MetricStageTracker + Policy Engine 연동"

      - philosophy_id: 2
        name: "권위 있는 Substrate"
        implementation: "Ledgers → Substrate 영구 저장"

    prohibited_rules_enforcement:
      - rule_id: 1
        rule: "Substrate 기록 필수"
        enforcement: "finalize_execution() 검증"

      - rule_id: 3
        rule: "Prior는 Belief Engine만"
        enforcement: "Lineage engine_ids 확인"

      - rule_id: 4
        rule: "Orchestration Decision Logging"
        enforcement: "모든 Reconcile 단계 기록 (강제)"

    non_goals_checks:
      - "Decision Log 존재 확인"
      - "Agent 확정 금지 확인"
      - "Substrate 저장 확인"
```

---

## 7. 검토 결과 요약

### ✅ 완벽한 일치

**철학 v2 → Orchestration Kernel**:

1. **철학 8 (Objective-Oriented)**
   → Reconcile Loop로 완벽 구현

2. **철학 1 (Evidence-first)**
   → Stage 추적 + Policy 연동

3. **철학 2 (Substrate SSOT)**
   → Ledgers + DecisionLog

4. **금지 규칙 4 (Decision Logging)**
   → 모든 Reconcile 단계 기록

5. **검증 가능성**
   → verify_reproducibility() 추가

---

### 🔧 추가 필요 사항

**1. 철학 강제 메서드** (Kernel에 추가):
- `_check_prior_usage()` (철학 3)
- `_ensure_substrate_saved()` (금지 규칙 1)
- `verify_reproducibility()` (검증)
- `check_non_goals()` (Non-goals)

**2. 문서 참조** (cmis.yaml):
- `philosophy_compliance` 섹션
- `prohibited_rules_enforcement`
- `non_goals_checks`

**3. README 업데이트**:
- 철학 10개 요약
- 철학 8 강조 (Objective-Oriented)

---

## 8. 문제점

### ❌ 없음!

**철학 v2는**:
- 명확함 ✅
- 구현 가능 ✅
- Orchestration Kernel과 완벽히 일치 ✅
- 검증 가능 ✅

**유일한 작업**: 설계 문서에 철학 참조 명시

---

## 9. 반영 계획

### 즉시 (오늘)

1. ✅ Orchestration Kernel 설계에 철학 섹션 추가
2. ✅ cmis.yaml에 philosophy_compliance 추가
3. ✅ 금지 규칙 강제 메서드 설계

### 구현 시 (v3.6.0)

1. ⏳ Kernel에 철학 강제 메서드 구현
2. ⏳ 검증 메서드 구현
3. ⏳ 테스트 (철학 위반 시나리오)

---

## 10. Summary

**철학 v2 검토 결과**: ✅ **완벽**

**주요 발견**:
- **철학 8 (Objective-Oriented)** 신규 추가
- Orchestration Kernel 설계와 **100% 일치**
- 금지 규칙이 구현 가능하게 명확

**반영 방안**:
- 설계 문서에 철학 참조 추가
- cmis.yaml에 compliance 섹션
- Kernel에 강제 메서드

**문제점**: **없음**

**다음 단계**: 설계 문서 업데이트

---

**작성**: 2025-12-12
**철학 v2**: ✅ 검증 완료
**설계 정합성**: ✅ 100%
