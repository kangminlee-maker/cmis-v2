# CMIS 용어 결정: Orchestration & Ledger

**작성일**: 2025-12-13
**결정자**: CMIS Architect + 사용자
**상태**: 최종 결정

---

## 1. orchestration_kernel vs orchestration_plane

### 1.1 사용자 제안

**"Orchestration Plane 안에 Orchestration Kernel"**

```
문서/아키텍처: orchestration_plane (일관성)
구현/런타임: OrchestrationKernel (실행 핵)
```

**근거**:
- **Plane**: 구조적 분리 (정적 경계)
  - "어느 계층에 속하는가"
  - Interaction/Role/Cognition/Substrate와 일관

- **Kernel**: 실행 제어의 핵 (core runtime)
  - "무엇이 실제로 실행을 통제하는가"
  - 스케줄링, 거버넌스, 상태 관리
  - OS Kernel과 유사한 역할

---

### 1.2 비판적 검토

**찬성 의견** ✅:

1. **의미적 정확성**
   - Plane: 아키텍처 레벨 (Where)
   - Kernel: 구현 레벨 (What/How)
   - 각각 다른 목적, 충돌 없음

2. **실용적 가치**
   - 문서: "Orchestration Plane" (독자 친화적)
   - 코드: `OrchestrationKernel` 클래스 (개발자 명확)
   - 컨텍스트별 최적 용어

3. **강조 효과**
   - "Kernel" → 시스템의 핵심 제어 강조
   - "그냥 하나의 층" 아님을 명확히

**반대 의견** ⚠️:

1. **용어 복잡도 증가**
   - 2개 용어 (Plane + Kernel)
   - 초보자: "뭐가 달라?"

   **대응**: 명확한 정의 문서화 (Section 1.1)

2. **일관성 약간 약화**
   - 다른 Plane은 단일 용어
   - Orchestration만 이중

   **대응**: "특수성" 강조 (실행 핵심이므로)

**결론**: ✅ **사용자 제안 채택**

**이유**:
- 반대 의견의 비용 < 찬성 의견의 가치
- 명확성 > 단순한 일관성
- CMIS의 핵심이므로 특별 취급 정당

---

### 1.3 최종 결정

```yaml
# cmis.yaml (아키텍처 레벨)
planes:
  orchestration_plane:
    description: "실행 제어 및 동적 재설계"
    core_component: "orchestration_kernel"
```

```python
# cmis_core/ (구현 레벨)
class OrchestrationKernel:
    """Orchestration Kernel

    Orchestration Plane의 핵심 런타임.
    Goal → Plan → Execute → Verify → Replan
    """
```

**용어 사용 규칙**:
- **Plane**: 문서, YAML, 다이어그램
- **Kernel**: 코드, 클래스명, 구현 설명

---

## 2. Project Ledger vs Task Ledger

### 2.1 사용자 제안

**"Project Ledger" 권장**

**근거**:

1. **"Task" 혼동 (2가지 의미)**:
   - 실행 단위 task (workflow step, task graph)
   - 문제 공간 task (Magentic-One)
   - CMIS는 "실행 task" 개념 강함

2. **오해 가능성**:
   - "Task Ledger" → "to-do 리스트" 느낌
   - 실제 의미: "프로젝트 상태 참조"

3. **정확한 의미**:
   - Substrate(Evidence/Value/Graph) 참조 집합
   - 프로젝트/시장 분석의 상태 뷰

---

### 2.2 비판적 검토

**찬성 의견** ✅:

1. **명확성** (가장 중요)
   ```
   "Project Ledger"
   → "프로젝트 상태" (명확)

   "Task Ledger"
   → "Task 목록?" vs "문제 공간?" (혼란)
   ```

2. **CMIS 맥락 적합**
   - CMIS는 "시장/프로젝트 분석"
   - "Project" = 자연스러운 단위
   - "Task" = 너무 작은 단위 느낌

3. **충돌 방지**
   - TaskQueue, TaskGraph (실행)
   - Project Ledger (상태)
   - 명확히 분리됨

**반대 의견** ⚠️:

1. **Magentic-One과 차이**
   - Magentic-One: Task Ledger
   - CMIS: Project Ledger
   - 레퍼런스 용어와 다름

   **대응**: CMIS 맥락에 맞는 것이 우선

2. **"Progress Ledger"와 대칭성**
   - Task vs Progress (대칭적?)
   - Project vs Progress (덜 대칭?)

   **대응**:
   - 의미가 대칭보다 중요
   - Problem Space vs Process Control (실제 대비)

**결론**: ✅ **사용자 제안 채택**

**이유**:
- 명확성이 가장 중요
- CMIS 맥락에 적합
- 장기적 안전성

---

### 2.3 최종 결정

**Primary 용어**:
- **Project Ledger** (문제 공간 상태)
- **Progress Ledger** (프로세스 제어)

**Alias 허용** (문서에서):
- "Task Ledger (Magentic-One 용어, CMIS에서는 Project Ledger)"

**코드**:
```python
class Ledgers:
    """2-Ledger 구조"""

    def __init__(self):
        self.project_ledger = ProjectLedger()  # 상태
        self.progress_ledger = ProgressLedger()  # 제어
```

---

## 3. 종합 결론

### 3.1 최종 용어 체계

| 개념 | 아키텍처 레벨 | 구현 레벨 | 이유 |
|------|--------------|----------|------|
| **Orchestration** | orchestration_plane | OrchestrationKernel | 구조 vs 실행 분리 |
| **상태 Ledger** | Project Ledger | ProjectLedger | 명확성, 충돌 방지 |
| **제어 Ledger** | Progress Ledger | ProgressLedger | 일관성 유지 |

---

### 3.2 비판적 평가

**사용자 제안의 강점**:
1. ✅ 용어 명확성 (장기 가치)
2. ✅ 실용적 타협 (Plane + Kernel)
3. ✅ 충돌 방지 (Task 혼동 제거)
4. ✅ CMIS 맥락 적합

**잠재적 우려**:
1. ⚠️ 용어 복잡도 약간 증가
2. ⚠️ 대칭성 약간 감소
3. ⚠️ 레퍼런스와 차이

**우려 대응**:
- 명확한 문서화 (본 문서)
- Glossary 제공
- 실용성 > 이론적 완벽함

**종합 평가**: ✅ **사용자 제안이 옳음**

---

### 3.3 채택 근거

**원칙 1**: **명확성 > 일관성 > 간결성**

```
일관성을 위해 "Task Ledger"
→ 혼동 비용 높음 ❌

명확성을 위해 "Project Ledger"
→ 즉시 이해 ✅
```

**원칙 2**: **장기 안전성**

```
초기 간결함 (단일 용어)
→ 후기 혼란 (의미 충돌) ❌

초기 약간 복잡 (이중 용어)
→ 후기 명확 (각자 역할) ✅
```

**원칙 3**: **CMIS 맥락 우선**

```
레퍼런스 용어 (Task Ledger)
→ CMIS 맥락과 안 맞음 ❌

CMIS 적합 용어 (Project Ledger)
→ 프로젝트 분석에 자연스러움 ✅
```

---

## 4. 구현 방침

### 4.1 문서 업데이트

**즉시**:
1. ✅ orchestration_plane + kernel 이중 구조 명시
2. ✅ Project Ledger로 통일
3. ✅ Glossary 추가

**위치**:
- CMIS_Orchestration_Kernel_Design.md
- cmis_contracts-and-registry_km.yaml
- CMIS_Architecture_Blueprint_v3.4_km.md

---

### 4.2 Glossary (필수)

```markdown
## CMIS 용어 사전

**Orchestration Plane**:
  - 아키텍처 레벨 용어
  - 4 Planes 중 하나 (실행 제어 계층)

**Orchestration Kernel**:
  - 구현/런타임 레벨 용어
  - Orchestration Plane의 핵심 컴포넌트
  - 실제 Reconcile Loop 실행

**Project Ledger**:
  - 프로젝트/시장 분석의 상태 참조
  - Substrate(Evidence/Value/Graph) 포인터 집합
  - 문제 공간 작업기억

**Progress Ledger**:
  - 실행 프로세스의 제어 상태
  - Step/Status/Stall/Budget
  - 프로세스 제어판

**Task** (실행 단위):
  - TaskQueue의 Task
  - Plan/Task Graph의 노드
  - "실행할 작업"

**Note**: "Task Ledger"는 사용 금지 (혼동 방지)
```

---

## 5. Summary

### 최종 결정

| 항목 | 결정 | 대안 거부 이유 |
|------|------|--------------|
| Orchestration 용어 | **Plane + Kernel 이중** | Plane만으로는 실행 핵심 강조 부족 |
| Ledger 명칭 | **Project + Progress** | Task는 실행 단위와 혼동 |

### 문서화 방침

1. **Glossary 필수** - 모든 핵심 문서에 포함
2. **컨텍스트별 용어** - 아키텍처/구현 구분
3. **Alias 명시** - "Task Ledger (Magentic-One, CMIS=Project)"

### 비판적 평가

**사용자 제안**: ✅ **채택**

**근거**:
- 명확성 최우선
- 장기 안전성
- 실용적 타협 (Plane + Kernel)

**우려 대응**:
- Glossary로 혼란 방지
- 명확한 문서화

---

**작성**: 2025-12-13
**결정**: orchestration_plane + kernel, Project Ledger
**상태**: ✅ 최종 확정
