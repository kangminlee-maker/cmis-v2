# CMIS × RLM Bridge 설계 작업문서

> **버전**: v0.2.0
> **작성일**: 2026-03-17
> **상태**: 실사 완료, 구현 대기
> **대상 레포**: `https://github.com/kangminlee-maker/cmis-v2`
> **원본 레포**: `https://github.com/kangminlee-maker/cmis` (CMIS v3.6.0)
> **참고 레포**: `https://github.com/alexzhang13/rlm` (RLM — Recursive Language Models)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|---------|
| v0.1.0 | 2026-03-17 | 초안 작성 |
| v0.2.0 | 2026-03-17 | CMIS 실사 결과 반영. State Machine/Gates/Scope/Events의 실제 구현 수준 확인 후 Bridge 역할 대폭 축소. Kernel.execute()를 주 도구로 격상 |

---

## 1. 배경과 목적

### 1.1 현재 CMIS의 실행 방식

CMIS v3.6.0은 9개 엔진이 모두 완성된 상태이다. 현재 실행 경로는 두 가지이다:

1. **CLI** — `cmis structure-analysis --domain ... --region ...`
2. **Cursor IDE** — `cmis.yaml`을 첨부하고 자연어로 요청

두 경로 모두 `OrchestrationKernel.execute(RunRequest)`를 호출하며, Kernel은 `config/workflows.yaml`에 정의된 4개 Canonical Workflow 중 하나를 선택하여 순차 실행한다.

### 1.2 현재 구조의 한계

| 한계 | 설명 |
|------|------|
| **Workflow 고정** | 4개 Canonical Workflow(`structure_analysis`, `opportunity_discovery`, `strategy_design`, `reality_monitoring`)가 YAML로 고정되어 있다. 중간 결과에 따라 전략을 바꾸는 것이 불가능하다. |
| **단일 Workflow 실행** | `RunRequest` 1건 = Workflow 1개. "시장 구조 분석 후 기회 발굴"처럼 여러 Workflow를 연결하려면 사용자가 수동으로 여러 번 호출해야 한다. |
| **적응적 분기 부재** | Evidence가 부족할 때 다른 소스를 시도하거나, 예상치 못한 패턴이 나왔을 때 추가 분석을 하는 등의 동적 판단이 없다. Replanner가 존재하지만 Diff 기반 Task 재생성에 한정되어 있다. (GoalBuilder는 키워드 기반 규칙만 사용, LLM 기반 목표 해석은 Phase 2+ 예정) |
| **Cursor 의존** | 비개발자가 사용하려면 Cursor IDE가 필요하다. Python 스크립트 단독 실행이 어렵다. |

### 1.3 RLM이 해결하는 것

RLM(Recursive Language Models)은 LM이 Python 코드를 작성하고 실행하는 REPL 환경을 제공한다. LM은:

- `llm_query(prompt)` — LM을 한 번 호출하여 답변을 받는다
- `rlm_query(prompt)` — 자식 RLM을 생성하여 복잡한 하위 작업을 위임한다
- `custom_tools` — 외부 함수를 REPL 안에서 호출할 수 있다

**CMIS의 OrchestrationKernel과 9개 엔진을 RLM의 `custom_tools`로 등록하면**, LM이 중간 결과를 보고 다음 Workflow를 스스로 결정할 수 있다. 여러 Workflow를 연결하고, 적응적으로 분기하는 것이 가능해진다.

### 1.4 목표

```
CMIS의 9개 엔진 + Orchestration 인프라  (기존, 그대로 보존)
          +
RLM의 재귀적 코드 실행 환경              (새로 연결)
          =
LM이 여러 CMIS Workflow를 연결하고 적응적으로 시장 분석을 수행하는 시스템
```

---

## 2. CMIS 실사 결과

### 2.1 이미 충분히 구현된 것

Bridge를 설계하기 전에 CMIS의 실제 구현 수준을 확인했다. **예상보다 많은 인프라가 이미 프로덕션 수준으로 구현되어 있었다.**

#### State Machine (상태 머신)

**Task 수준 — 완전 구현:**
- `PENDING → RUNNING → COMPLETED/FAILED` (cmis_core/orchestration/task.py)
- `ProgressLedger.overall_status`: `running → completed | stalled | failed | incomplete`

**Reconcile Loop — 완전 구현:**
- `Verify → Diff → Replan → Execute → 다시 Verify` (cmis_core/orchestration/kernel.py:273-433)
- 목표 미충족 시 자동 재계획 (Replanner)
- 예산/시간/Stall 제어 (Governor)

#### Gates (검증 게이트)

**정책 게이트 8종 — 완전 구현:**
- `evidence_min_sources`, `evidence_require_official`, `evidence_max_age_days` 등
- 위반 시 `GateViolation` 객체 + `suggested_actions` 생성
- (cmis_core/policy_engine.py:915-925, `_register_default_gates()`)

**시스템 게이트 — 완전 구현:**
- Task 의존성 게이트 (task.py `next_runnable()`)
- Stall 감지 (governor.py `check_stall()`, 정책별 threshold)
- 예산 제어 (governor.py `should_stop()`, 기본 20회/300초)
- 실행 모드 게이트 (`approval_required`, `manual`, `autopilot`)

**Verifier — 완전 구현:**
- Predicate 만족 + Evidence lineage + 일관성 검사 (verifier.py)
- 미충족 시 diff_report 생성 → Replanner가 작업 생성

#### Events (이벤트 로그)

**3계층 이벤트 시스템 — 프로덕션 수준:**

| 계층 | 저장소 | 형식 |
|------|--------|------|
| Kernel 이벤트 (12종) | RunStore → SQLite `run_events` | JSON |
| Kernel 의사결정 (9종) | RunStore → SQLite `run_decisions` | JSON |
| Search v3 이벤트 | ArtifactStore → NDJSON | NDJSON |

**RunExporter — 완전 구현:**
```
.cmis/runs/<run_id>/
├── request.yaml
├── project_ledger.yaml
├── progress_ledger.yaml
├── events.jsonl          ← NDJSON
├── decision_log.jsonl    ← NDJSON
└── results.md
```

#### Stores (데이터 저장)

**5개 Store 모두 SQLite 기반 프로덕션 구현:**

| Store | DB 경로 | 용도 |
|-------|---------|------|
| RunStore | `.cmis/db/runs.db` | Run 메타 + 이벤트 + 의사결정 |
| LedgerStore | `.cmis/db/ledgers.db` | ProjectLedger/ProgressLedger 스냅샷 |
| ArtifactStore | `.cmis/db/artifacts.db` + 파일 | 산출물 (SHA256 중복제거) |
| OutcomeStore | `.cmis/db/outcomes.db` | 학습 엔진 결과 |
| FocalActorContextStore | `.cmis/db/contexts.db` | Brownfield 컨텍스트 (버전 관리) |

### 2.2 CMIS에 없는 것 (Bridge가 추가해야 하는 것)

| 영역 | 없는 것 | 설명 |
|------|---------|------|
| **프로젝트 수준 상태 머신** | 다중 Workflow를 연결하는 상위 흐름 | "structure_analysis → opportunity_discovery → strategy_design"을 하나의 프로젝트로 관리하는 상태 머신이 없음 |
| **프로젝트 Scope** | 여러 Run을 묶는 컨테이너 | RunRequest 1건 = Run 1건으로 끝남. 이전 Run의 결과를 다음 Run에 전달하는 메커니즘이 없음 |
| **프로젝트 수준 이벤트** | Run을 가로지르는 이벤트 스트림 | "Run A에서 structure_analysis를 했고, Run B에서 opportunity_discovery를 했다"를 연결하는 로그가 없음 |
| **Workflow 단계 간 게이트** | 단계 전환 시 사전 검증 | workflow.py에서 단계 간 정책 검증 없이 순차 실행. 단, Kernel의 Reconcile Loop가 사후 검증으로 보완 |
| **LLM 기반 Goal 해석** | 키워드 기반 규칙만 존재 | GoalBuilder가 query에서 workflow_hint를 키워드로 추론. LLM 기반은 Phase 2+ 예정 |
| **LLM 기반 Replanning** | 규칙 기반 Task 생성만 존재 | Replanner가 diff_report에서 고정 규칙으로 Task 생성. LLM 기반은 Phase 2+ 예정 |

### 2.3 결론: Bridge의 역할 재정의

**v0.1.0 설계**: Bridge가 State Machine, Gates, Scope, Events를 모두 새로 구현
**v0.2.0 수정**: Bridge는 **프로젝트 수준 래퍼만 추가**. Run 내부는 기존 CMIS 인프라를 그대로 사용

```
v0.1.0 (이전):
  Bridge가 만드는 것: state_machine.py + gates.py + scope.py + events.py + tools.py
  → 약 700줄 신규 코드

v0.2.0 (수정):
  Bridge가 만드는 것: project.py (Scope 래퍼) + tools.py + runner.py
  → 약 400줄 신규 코드
  CMIS에서 재사용하는 것: RunStore, LedgerStore, Verifier, Governor, PolicyEngine 전부
```

---

## 3. RLM 참조 정보

### 3.1 레포 위치

- **GitHub**: https://github.com/alexzhang13/rlm
- **로컬 클론**: `/Users/kangmin/cowork/rlm`
- **논문**: arXiv:2512.24601

### 3.2 RLM 핵심 구조 (CMIS 연결에 필요한 부분만)

```
rlm/
├── rlm/
│   ├── core/
│   │   ├── rlm.py           ← RLM 클래스. completion() 메서드가 진입점
│   │   ├── lm_handler.py    ← TCP 소켓 서버. 격리 환경에서 LM API 접근용
│   │   └── types.py         ← RLMChatCompletion, RLMIteration, CodeBlock 등
│   ├── clients/
│   │   ├── base_lm.py       ← BaseLM 인터페이스 (completion, acompletion)
│   │   ├── openai.py        ← OpenAI 클라이언트
│   │   └── anthropic.py     ← Anthropic 클라이언트
│   ├── environments/
│   │   └── local_repl.py    ← LocalREPL. exec()로 코드 실행. custom_tools 주입 지점
│   └── utils/
│       └── prompts.py       ← 시스템 프롬프트 (REPL 사용법 안내)
```

### 3.3 RLM custom_tools 인터페이스

```python
from rlm import RLM

rlm = RLM(
    backend="openai",
    backend_kwargs={"model_name": "gpt-4o"},
    custom_tools={
        "tool_name": {
            "tool": callable_or_value,        # 함수 또는 값
            "description": "도구 설명 문자열"   # LM에게 노출되는 설명
        },
    },
)
```

**참고 파일**: `rlm/environments/local_repl.py` — `_inject_tools()` 메서드

### 3.4 RLM 주요 파라미터

```python
RLM(
    backend="openai",                # LM 백엔드 (openai, anthropic, gemini 등)
    backend_kwargs={...},            # 백엔드 설정
    custom_tools={...},              # 외부 도구 (이 설계의 핵심)
    max_depth=2,                     # 재귀 깊이 제한
    max_iterations=30,               # 반복 횟수 제한
    max_budget=10.0,                 # USD 비용 상한
    max_timeout=300.0,               # 시간 제한 (초)
    persistent=False,                # True면 환경 유지 (다중 completion 호출)
    compaction=False,                # 컨텍스트 압축 자동화
    verbose=True,                    # Rich 콘솔 출력
    logger=None,                     # RLMLogger 인스턴스 (궤적 기록)
)
```

---

## 4. 설계: Bridge 모듈

### 4.1 디렉토리 구조

CMIS 레포 내에 `bridge/` 디렉토리를 추가한다. 기존 코드는 수정하지 않는다.

```
cmis-v2/
├── cmis_core/                ← 기존. 변경 없음
├── cmis_cli/                 ← 기존. 변경 없음
├── config/                   ← 기존. 변경 없음
├── libraries/                ← 기존. 변경 없음
│
├── bridge/                   ← 신규. RLM 연결 계층
│   ├── __init__.py
│   ├── tools.py              ← CMIS Kernel + 엔진 → RLM custom_tools 변환
│   ├── project.py            ← 프로젝트 Scope (다중 Run을 묶는 래퍼)
│   ├── system_prompt.py      ← RLM에 전달할 시스템 프롬프트 생성
│   └── runner.py             ← 사용자 진입점
│
├── projects/                 ← 신규. 프로젝트별 작업 공간
│   └── .gitkeep
│
└── dev/docs/design/
    └── CMIS_RLM_BRIDGE_DESIGN.md   ← 이 문서
```

### 4.2 의존성 추가

`requirements.txt`에 추가:

```
# RLM Bridge
rlms>=0.1.1
```

---

## 5. 모듈 상세 설계

### 5.1 `bridge/tools.py` — CMIS를 RLM 도구로 변환

#### 5.1.1 설계 원칙

1. **Kernel.execute()를 주 도구로 사용** — 개별 엔진 직접 호출 대신, Kernel의 Reconcile Loop를 활용한다. Kernel이 이미 정책 검증, 재시도, 이벤트 기록을 수행하므로, 이를 우회할 이유가 없다.
2. **개별 엔진은 보조 도구로 제공** — Kernel을 거치지 않고 특정 엔진만 호출할 필요가 있는 경우를 위해 보조 도구로 노출한다.
3. **CMIS 코드 변경 금지** — 기존 엔진을 import하여 래핑만 한다.
4. **오류는 문자열로 반환** — exception 대신 `{"error": "..."}` 반환.

#### 5.1.2 도구 분류

**Tier 1: Kernel 도구 (주 도구)**

Kernel.execute()를 래핑한다. LM은 대부분의 작업에 이 도구를 사용한다.

```python
# bridge/tools.py

from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import asdict

from cmis_core.orchestration.kernel import OrchestrationKernel, RunRequest, RunResult
from cmis_core.stores.factory import StoreFactory


PROJECT_ROOT = Path(__file__).parent.parent


def _safe_call(fn, **kwargs) -> Dict[str, Any]:
    """엔진 호출을 래핑하여 오류를 dict로 반환"""
    try:
        result = fn(**kwargs)
        if hasattr(result, "__dataclass_fields__"):
            return asdict(result)
        if hasattr(result, "to_dict"):
            return result.to_dict()
        if isinstance(result, dict):
            return result
        return {"result": result}
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


class CMISTools:
    """CMIS를 RLM custom_tools로 노출하는 클래스"""

    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.store_factory = StoreFactory(project_root=project_root)
        self.kernel = OrchestrationKernel(
            project_root=project_root,
            run_store=self.store_factory.run_store(),
            ledger_store=self.store_factory.ledger_store(),
        )

    # ─── Tier 1: Kernel 도구 (주 도구) ───

    def run_analysis(self, query: str, role_id: str = "",
                     policy_id: str = "", run_mode: str = "autopilot",
                     context: dict = None, budgets: dict = None) -> Dict[str, Any]:
        """CMIS 분석을 실행한다. Kernel의 Reconcile Loop가 자동으로:
        - 적절한 Workflow를 선택하고 실행
        - 정책 게이트로 결과 품질을 검증
        - 미충족 시 Evidence 추가 수집 + Metric 재계산
        - 모든 이벤트와 의사결정을 기록

        Args:
            query: 자연어 요청. 예:
                - "성인 영어 교육 시장 구조 분석" → structure_analysis Workflow
                - "전기차 충전 시장 기회 발굴" → opportunity_discovery Workflow
                - "B2B SaaS 시장 진입 전략 설계" → strategy_design Workflow
            role_id: 역할 (선택). 비워두면 query에서 자동 추론.
                - "structure_analyst" → reporting_strict 정책
                - "opportunity_designer" → exploration_friendly 정책
                - "strategy_architect" → decision_balanced 정책
            policy_id: 정책 (선택). 비워두면 role에서 자동 추론.
                - "reporting_strict": 공식 데이터 2개 이상, 검증 70%+
                - "decision_balanced": 데이터 1개 이상, 검증 50%+
                - "exploration_friendly": 제약 최소, Prior 허용
            run_mode: 실행 모드.
                - "autopilot": 모든 작업을 자동 실행 (기본값)
                - "approval_required": 작업 계획 생성 후 일시정지
                - "manual": 작업 1건 실행 후 일시정지
            context: 분석 컨텍스트. 예:
                {"domain_id": "EV_Charging_KR", "region": "KR", "year": 2025}
            budgets: 예산 제한. 예:
                {"max_iterations": 20, "max_time_sec": 300}

        Returns:
            {
                "run_id": "RUN-20260317-...",
                "status": "success|incomplete|failed|stalled",
                "goal_satisfied": true/false,
                "iterations": 5,
                "ledgers": {
                    "project_ledger": { "facts": {...}, "metrics": {...}, ... },
                    "progress_ledger": { "steps": [...], "overall_status": "...", ... }
                },
                "events": [...],
                "decision_log": [...]
            }
        """
        request = RunRequest(
            query=query,
            role_id=role_id or None,
            policy_id=policy_id or None,
            run_mode=run_mode,
            context=context or {},
            budgets=budgets or {},
        )
        return _safe_call(self.kernel.execute, request=request)

    def get_run_events(self, run_id: str) -> Dict[str, Any]:
        """특정 Run의 전체 이벤트 로그를 조회한다.

        Args:
            run_id: Run ID (예: "RUN-20260317-103000-abc123")

        Returns:
            {"events": [...], "decisions": [...]}
        """
        run_store = self.store_factory.run_store()
        return {
            "events": run_store.list_events(run_id),
            "decisions": run_store.list_decisions(run_id),
        }

    def get_run_ledger(self, run_id: str) -> Dict[str, Any]:
        """특정 Run의 최신 Ledger 스냅샷을 조회한다.

        Args:
            run_id: Run ID

        Returns:
            {"project_ledger": {...}, "progress_ledger": {...}}
            또는 {"error": "..."}
        """
        ledger_store = self.store_factory.ledger_store()
        snapshot = ledger_store.get_latest_snapshot(run_id)
        if snapshot is None:
            return {"error": f"Run '{run_id}'의 Ledger를 찾을 수 없습니다."}
        return snapshot

    # ─── Tier 2: 개별 엔진 도구 (보조 도구) ───
    # Kernel을 거치지 않고 특정 엔진만 직접 호출할 때 사용.
    # 정책 검증, 재시도, 이벤트 기록이 자동으로 수행되지 않으므로 주의.

    def collect_evidence(self, query: str, domain_id: str = "",
                         region: str = "KR") -> Dict[str, Any]:
        """[보조] Evidence를 직접 수집한다. Kernel의 정책 검증을 거치지 않는다.

        Args:
            query: 검색할 내용 (예: "한국 전기차 충전 시장 규모")
            domain_id: 도메인 ID (선택)
            region: 지역 코드

        Returns:
            {"evidence_records": [...], "lineage": {...}}
        """
        from cmis_core.evidence_engine import EvidenceEngine
        engine = EvidenceEngine(project_root=self.project_root)
        return _safe_call(
            engine.collect,
            query=query,
            domain_id=domain_id,
            region=region,
        )

    def build_snapshot(self, domain_id: str, region: str = "KR",
                       focal_actor_context_id: str = "") -> Dict[str, Any]:
        """[보조] Reality Snapshot(R-Graph)을 직접 생성한다.

        Args:
            domain_id: 도메인 ID (예: "Adult_Language_Education_KR")
            region: 지역 코드
            focal_actor_context_id: Brownfield 컨텍스트 ID (선택)

        Returns:
            {"reality_snapshot_ref": "...", "nodes": [...], "edges": [...]}
        """
        from cmis_core.world_engine import WorldEngine
        engine = WorldEngine(project_root=self.project_root)
        return _safe_call(
            engine.snapshot,
            domain_id=domain_id,
            region=region,
            focal_actor_context_id=focal_actor_context_id,
        )

    def match_patterns(self, reality_snapshot_ref: str,
                       focal_actor_context_id: str = "") -> Dict[str, Any]:
        """[보조] R-Graph에서 비즈니스 패턴(23개)을 직접 매칭한다.

        Args:
            reality_snapshot_ref: build_snapshot()이 반환한 참조 ID
            focal_actor_context_id: Brownfield 컨텍스트 ID (선택)

        Returns:
            {"pattern_matches": [{"pattern_id": "...", "fit_score": ...}]}
        """
        from cmis_core.pattern_engine_v2 import PatternEngineV2
        engine = PatternEngineV2(project_root=self.project_root)
        return _safe_call(
            engine.match_patterns,
            reality_snapshot_ref=reality_snapshot_ref,
            focal_actor_context_id=focal_actor_context_id,
        )

    def evaluate_metrics(self, metric_ids: list, context: dict = None,
                         policy_ref: str = "decision_balanced") -> Dict[str, Any]:
        """[보조] Metric을 직접 계산한다. 4-Method Fusion 사용.

        Args:
            metric_ids: Metric ID 목록 (예: ["MET-TAM", "MET-Revenue"])
            context: 컨텍스트 (예: {"domain_id": "...", "year": 2025})
            policy_ref: 정책 모드

        Returns:
            {"value_records": [{"metric_id": "...", "point_estimate": ..., "quality": {...}}]}
        """
        from cmis_core.value_engine import ValueEngine
        engine = ValueEngine(project_root=self.project_root)
        requests = [{"metric_id": mid, "context": context or {}} for mid in metric_ids]
        return _safe_call(
            engine.evaluate_metrics,
            metric_requests=requests,
            policy_ref=policy_ref,
        )

    def get_policy(self, role_id: str = "structure_analyst",
                   usage: str = "reporting") -> Dict[str, Any]:
        """현재 적용되는 정책을 조회한다.

        Args:
            role_id: 역할
            usage: 용도 (reporting / decision / exploration)

        Returns:
            {"policy_id": "...", "profiles": {...}}
        """
        from cmis_core.policy_engine import PolicyEngine
        engine = PolicyEngine(project_root=self.project_root)
        return _safe_call(
            engine.resolve_policy,
            role_id=role_id,
            usage=usage,
        )

    # ─── 도구 딕셔너리 생성 ───

    def as_rlm_tools(self) -> Dict[str, Dict[str, Any]]:
        """RLM custom_tools 형식으로 변환"""
        return {
            # Tier 1: Kernel 도구 (주 도구)
            "run_analysis": {
                "tool": self.run_analysis,
                "description": (
                    "CMIS 분석을 실행한다. 정책 검증, 재시도, 이벤트 기록이 자동 수행된다. "
                    "query(자연어), context(dict), role_id, policy_id, run_mode, budgets 인자."
                ),
            },
            "get_run_events": {
                "tool": self.get_run_events,
                "description": "Run의 이벤트/의사결정 로그 조회. run_id 인자.",
            },
            "get_run_ledger": {
                "tool": self.get_run_ledger,
                "description": "Run의 Ledger(프로젝트 상태) 조회. run_id 인자.",
            },

            # Tier 2: 개별 엔진 도구 (보조)
            "collect_evidence": {
                "tool": self.collect_evidence,
                "description": "[보조] Evidence 직접 수집. Kernel 정책 검증 없음. query, domain_id, region 인자.",
            },
            "build_snapshot": {
                "tool": self.build_snapshot,
                "description": "[보조] R-Graph 직접 생성. domain_id, region 인자.",
            },
            "match_patterns": {
                "tool": self.match_patterns,
                "description": "[보조] 패턴 매칭 직접 실행. reality_snapshot_ref 인자.",
            },
            "evaluate_metrics": {
                "tool": self.evaluate_metrics,
                "description": "[보조] Metric 직접 계산. metric_ids(리스트), context, policy_ref 인자.",
            },
            "get_policy": {
                "tool": self.get_policy,
                "description": "정책 조회. role_id, usage(reporting/decision/exploration) 인자.",
            },
        }
```

#### 5.1.3 도구 Tier 설계 의도

| Tier | 도구 | 정책 검증 | 이벤트 기록 | 재시도 | 사용 시점 |
|------|------|---------|-----------|-------|---------|
| **Tier 1** | `run_analysis` | 자동 (Verifier) | 자동 (RunStore) | 자동 (Replanner) | 기본. 대부분의 분석에 사용 |
| **Tier 1** | `get_run_events`, `get_run_ledger` | — | — | — | 이전 Run 결과 확인 |
| **Tier 2** | `collect_evidence`, `build_snapshot` 등 | 없음 | 없음 | 없음 | Kernel로 부족할 때 보조적으로 사용 |

**v0.1.0과의 차이**: v0.1.0에서는 모든 엔진을 동등한 도구로 노출했다. v0.2.0에서는 Kernel.execute()를 주 도구로 격상하고, 개별 엔진은 보조 도구로 내렸다. Kernel이 이미 정책 검증, 재시도, 이벤트 기록을 수행하므로, 이를 우회할 이유가 없기 때문이다.

---

### 5.2 `bridge/project.py` — 프로젝트 Scope

여러 `run_analysis()` 호출을 하나의 프로젝트로 묶는 래퍼이다. Run 내부의 이벤트/상태 저장은 CMIS의 RunStore/LedgerStore가 담당하고, project.py는 **Run 간 연결**만 관리한다.

```python
# bridge/project.py

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List


PROJECTS_DIR = Path(__file__).parent.parent / "projects"


def create_project(name: str, description: str = "",
                   domain_id: str = "", region: str = "KR") -> Dict[str, Any]:
    """새 분석 프로젝트를 생성한다.

    Args:
        name: 프로젝트 이름 (예: "ev-charging-korea")
        description: 설명 (예: "한국 전기차 충전 인프라 시장 분석")
        domain_id: CMIS 도메인 ID (선택)
        region: 지역 코드

    Returns:
        {"project_id": "...", "project_dir": "...", "status": "active"}
    """
    date_str = datetime.now().strftime("%Y%m%d")
    project_id = f"{name}-{date_str}"
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "project_id": project_id,
        "name": name,
        "description": description,
        "domain_id": domain_id,
        "region": region,
        "status": "active",
        "runs": [],           # run_id 목록 (시간 순)
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    _write_manifest(project_id, manifest)
    _append_event(project_id, "project.created", "system", {"name": name})

    return manifest


def add_run(project_id: str, run_id: str, query: str,
            workflow_hint: str = "") -> Dict[str, Any]:
    """프로젝트에 Run을 등록한다. run_analysis() 호출 후 결과의 run_id를 등록하는 용도.

    Args:
        project_id: 프로젝트 ID
        run_id: CMIS Run ID (예: "RUN-20260317-103000-abc123")
        query: Run에서 사용한 query
        workflow_hint: 실행된 Workflow 이름 (선택)

    Returns:
        업데이트된 manifest
    """
    manifest = load_project(project_id)
    if "error" in manifest:
        return manifest

    manifest["runs"].append({
        "run_id": run_id,
        "query": query,
        "workflow_hint": workflow_hint,
        "added_at": datetime.now().isoformat(),
    })
    manifest["updated_at"] = datetime.now().isoformat()
    _write_manifest(project_id, manifest)
    _append_event(project_id, "run.added", "system",
                  {"run_id": run_id, "query": query})

    return manifest


def load_project(project_id: str) -> Dict[str, Any]:
    """프로젝트의 현재 상태를 조회한다.

    Returns:
        manifest dict 또는 {"error": "..."}
    """
    path = PROJECTS_DIR / project_id / "manifest.json"
    if not path.exists():
        return {"error": f"프로젝트 '{project_id}'가 존재하지 않습니다."}
    return json.loads(path.read_text())


def complete_project(project_id: str) -> Dict[str, Any]:
    """프로젝트를 완료 상태로 변경한다."""
    manifest = load_project(project_id)
    if "error" in manifest:
        return manifest
    manifest["status"] = "completed"
    manifest["updated_at"] = datetime.now().isoformat()
    _write_manifest(project_id, manifest)
    _append_event(project_id, "project.completed", "system")
    return manifest


def save_deliverable(project_id: str, filename: str,
                     content: str) -> str:
    """프로젝트 산출물을 저장한다.

    Args:
        project_id: 프로젝트 ID
        filename: 파일명 (예: "final_report.md")
        content: 파일 내용

    Returns:
        저장된 파일 경로
    """
    path = PROJECTS_DIR / project_id / filename
    path.write_text(content)
    _append_event(project_id, "deliverable.saved", "system",
                  {"filename": filename})
    return str(path)


def list_projects() -> List[Dict[str, Any]]:
    """모든 프로젝트 목록을 반환한다."""
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        manifest_path = d / "manifest.json"
        if d.is_dir() and manifest_path.exists():
            m = json.loads(manifest_path.read_text())
            projects.append({
                "project_id": m["project_id"],
                "description": m.get("description", ""),
                "status": m["status"],
                "run_count": len(m.get("runs", [])),
                "created_at": m.get("created_at", ""),
            })
    return projects


def read_project_events(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트의 이벤트 로그를 읽는다."""
    path = PROJECTS_DIR / project_id / "events.ndjson"
    if not path.exists():
        return []
    events = []
    for line in path.read_text().strip().split("\n"):
        if line:
            events.append(json.loads(line))
    return events


# ─── 내부 함수 ───

def _write_manifest(project_id: str, manifest: dict) -> None:
    path = PROJECTS_DIR / project_id / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))


def _append_event(project_id: str, event_type: str, actor: str,
                  payload: dict = None) -> None:
    path = PROJECTS_DIR / project_id / "events.ndjson"
    existing = path.read_text().strip().split("\n") if path.exists() and path.stat().st_size > 0 else []
    revision = len(existing) + 1
    event = {
        "event_id": f"evt_{revision:04d}",
        "type": event_type,
        "ts": datetime.now().isoformat(),
        "revision": revision,
        "actor": actor,
        "payload": payload or {},
    }
    with open(path, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
```

#### 5.2.1 프로젝트 디렉토리 구조

```
projects/
└── ev-charging-korea-20260317/
    ├── manifest.json         ← 프로젝트 메타 + Run 목록
    ├── events.ndjson         ← 프로젝트 수준 이벤트 (Run 추가, 완료 등)
    ├── final_report.md       ← 산출물 (선택)
    └── opportunity_report.md ← 산출물 (선택)
```

**Run 내부 이벤트는 CMIS RunStore에 저장된다** (`.cmis/db/runs.db`).
프로젝트 수준 `events.ndjson`은 Run 간 연결만 기록한다.

#### 5.2.2 Scope 이벤트와 Run 이벤트의 역할 분담

| 이벤트 | 저장 위치 | 예시 |
|--------|---------|------|
| **프로젝트 생성/완료** | `projects/{id}/events.ndjson` | `project.created`, `project.completed` |
| **Run 등록** | `projects/{id}/events.ndjson` | `run.added` (run_id, query) |
| **산출물 저장** | `projects/{id}/events.ndjson` | `deliverable.saved` |
| **Task 시작/완료** | `.cmis/db/runs.db` (RunStore) | `task_started`, `task_completed` |
| **정책 검증** | `.cmis/db/runs.db` (RunStore) | `diff_detected`, `replanned` |
| **목표 달성** | `.cmis/db/runs.db` (RunStore) | `goal_satisfied` |

---

### 5.3 `bridge/system_prompt.py` — RLM 시스템 프롬프트

```python
# bridge/system_prompt.py

SYSTEM_PROMPT = """당신은 CMIS(Contextual Market Intelligence System)의 분석 에이전트입니다.

## 주 도구: run_analysis

대부분의 분석에 이 도구를 사용하세요. Kernel이 자동으로:
- Workflow 선택 및 실행
- 정책 게이트 검증
- 미충족 시 Evidence 추가 수집 및 재계산
- 이벤트/의사결정 기록

```python
result = run_analysis(
    query="성인 영어 교육 시장 구조 분석",
    context={"domain_id": "Adult_Language_Education_KR", "region": "KR"},
    run_mode="autopilot"
)
```

query 키워드에 따라 자동으로 Workflow가 선택됩니다:
- "구조", "분석", "규모" → structure_analysis (reporting_strict 정책)
- "기회", "발굴", "탐색" → opportunity_discovery (exploration_friendly 정책)
- "전략", "의사결정", "포트폴리오" → strategy_design (decision_balanced 정책)

## 보조 도구

Kernel을 거치지 않고 특정 엔진만 호출할 때:
- collect_evidence(query, domain_id, region) — Evidence 직접 수집
- build_snapshot(domain_id, region) — R-Graph 직접 생성
- match_patterns(reality_snapshot_ref) — 패턴 매칭
- evaluate_metrics(metric_ids, context, policy_ref) — Metric 계산
- get_policy(role_id, usage) — 정책 조회

## 프로젝트 관리 도구

- create_project(name, description, domain_id, region) — 프로젝트 생성
- add_run(project_id, run_id, query) — Run 등록
- load_project(project_id) — 프로젝트 상태 조회
- complete_project(project_id) — 프로젝트 완료
- save_deliverable(project_id, filename, content) — 산출물 저장
- list_projects() — 프로젝트 목록
- get_run_events(run_id) — Run 이벤트 조회
- get_run_ledger(run_id) — Run Ledger 조회

## 실행 규칙

1. **프로젝트를 먼저 생성한다** — create_project()
2. **run_analysis()를 주 도구로 사용한다** — 정책 검증과 재시도가 자동
3. **Run 결과를 프로젝트에 등록한다** — add_run(project_id, result["run_id"], query)
4. **이전 Run 결과를 확인하고 다음 분석을 결정한다** — get_run_ledger()
5. **여러 Workflow를 연결한다** — 한 run_analysis()가 끝나면 결과를 보고 다음 query를 결정
6. **최종 보고서는 save_deliverable()로 저장한다**

## 정책 모드

- reporting_strict: 공식 데이터 2개+, 검증 70%+
- decision_balanced: 데이터 1개+, 검증 50%+
- exploration_friendly: 제약 최소, Prior 허용

## Metric ID 예시

MET-TAM, MET-SAM, MET-SOM, MET-Revenue, MET-N_customers,
MET-ARPU, MET-Churn_rate, MET-CAC, MET-LTV, MET-Gross_margin
"""


def build_prompt(target_description: str,
                 policy_mode: str = "decision_balanced") -> str:
    """RLM에 전달할 전체 프롬프트를 생성한다."""
    return f"""{SYSTEM_PROMPT}

## 이번 작업

분석 대상: {target_description}
기본 정책: {policy_mode}

위 도구들을 사용하여 분석을 수행하세요.
최종 결과는 FINAL_VAR()로 반환하세요.
"""
```

---

### 5.4 `bridge/runner.py` — 사용자 진입점

```python
# bridge/runner.py

"""CMIS × RLM Runner

사용법:
    python -m bridge.runner "한국 전기차 충전 인프라 시장 분석"
    python -m bridge.runner "성인 영어 교육 시장 기회 발굴" --policy exploration_friendly
    python -m bridge.runner --resume ev-charging-korea-20260317
"""

import argparse
import sys
from pathlib import Path

from rlm import RLM
from rlm.logger import RLMLogger

from .tools import CMISTools
from .project import (
    create_project, add_run, load_project, complete_project,
    save_deliverable, list_projects, read_project_events,
)
from .system_prompt import build_prompt


def build_rlm(policy_mode: str = "decision_balanced",
              backend: str = "openai",
              model_name: str = "gpt-4o",
              verbose: bool = True) -> RLM:
    """CMIS 도구가 등록된 RLM 인스턴스를 생성한다."""

    cmis = CMISTools()
    tools = cmis.as_rlm_tools()

    # 프로젝트 관리 도구 추가
    tools.update({
        "create_project": {
            "tool": create_project,
            "description": "프로젝트 생성. name, description, domain_id, region 인자.",
        },
        "add_run": {
            "tool": add_run,
            "description": "프로젝트에 Run 등록. project_id, run_id, query 인자.",
        },
        "load_project": {
            "tool": load_project,
            "description": "프로젝트 상태 조회. project_id 인자.",
        },
        "complete_project": {
            "tool": complete_project,
            "description": "프로젝트 완료. project_id 인자.",
        },
        "save_deliverable": {
            "tool": save_deliverable,
            "description": "산출물 저장. project_id, filename, content 인자.",
        },
        "list_projects": {
            "tool": list_projects,
            "description": "모든 프로젝트 목록 조회. 인자 없음.",
        },
        "read_project_events": {
            "tool": read_project_events,
            "description": "프로젝트 이벤트 로그 읽기. project_id 인자.",
        },
    })

    logger = RLMLogger(log_dir="./logs")

    return RLM(
        backend=backend,
        backend_kwargs={"model_name": model_name},
        custom_tools=tools,
        max_depth=2,
        max_iterations=30,
        max_budget=15.0,
        max_timeout=600.0,
        verbose=verbose,
        logger=logger,
    )


def run(target: str, policy_mode: str = "decision_balanced", **kwargs) -> dict:
    """시장 분석을 실행한다."""
    rlm = build_rlm(policy_mode=policy_mode, **kwargs)
    prompt = build_prompt(target, policy_mode)
    result = rlm.completion(prompt)
    return {
        "response": result.response,
        "execution_time": result.execution_time,
    }


def resume(project_id: str, instruction: str = "", **kwargs) -> dict:
    """중단된 분석을 이어서 실행한다."""
    project = load_project(project_id)
    if "error" in project:
        print(f"오류: {project['error']}")
        sys.exit(1)

    runs = project.get("runs", [])
    resume_prompt = f"""이전에 시작한 분석을 이어서 수행합니다.

프로젝트 ID: {project_id}
설명: {project.get('description', '')}
완료된 Run 수: {len(runs)}
마지막 Run: {runs[-1] if runs else '없음'}

get_run_ledger()로 이전 Run의 결과를 확인하고, 남은 분석을 이어서 수행하세요.
{f'추가 지시: {instruction}' if instruction else ''}
"""

    rlm = build_rlm(**kwargs)
    prompt = build_prompt(resume_prompt)
    result = rlm.completion(prompt)
    return {"response": result.response, "execution_time": result.execution_time}


def main():
    parser = argparse.ArgumentParser(description="CMIS × RLM Market Intelligence Runner")
    parser.add_argument("target", nargs="?", help="분석 대상")
    parser.add_argument("--policy", default="decision_balanced",
                        choices=["reporting_strict", "decision_balanced", "exploration_friendly"])
    parser.add_argument("--resume", metavar="PROJECT_ID", help="프로젝트 이어서 실행")
    parser.add_argument("--backend", default="openai")
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.resume:
        result = resume(args.resume, backend=args.backend, model_name=args.model,
                        verbose=not args.quiet)
    elif args.target:
        result = run(args.target, policy_mode=args.policy, backend=args.backend,
                     model_name=args.model, verbose=not args.quiet)
    else:
        parser.print_help()
        sys.exit(1)

    print(f"\n=== 분석 완료 ({result.get('execution_time', '?')}초) ===")
    print(result["response"][:1000])


if __name__ == "__main__":
    main()
```

---

## 6. 실행 시나리오

### 6.1 전체 시장 분석 (구조 → 기회 → 전략)

```bash
python -m bridge.runner "한국 전기차 충전 인프라 시장 종합 분석"
```

LM이 REPL에서 작성하는 코드 (예상):

```python
# 1. 프로젝트 생성
project = create_project(
    name="ev-charging-korea",
    description="한국 전기차 충전 인프라 시장 종합 분석",
    domain_id="EV_Charging_KR",
    region="KR"
)
project_id = project["project_id"]

# 2. 시장 구조 분석 (Kernel이 정책 검증 + 재시도 자동 수행)
structure = run_analysis(
    query="한국 전기차 충전 인프라 시장 구조 분석",
    context={"domain_id": "EV_Charging_KR", "region": "KR"}
)
add_run(project_id, structure["run_id"], "시장 구조 분석")

# 3. 결과 확인 → 다음 분석 결정
ledger = get_run_ledger(structure["run_id"])
metrics = ledger["project_ledger"]["metrics"]

# 4. 기회 발굴 (구조 분석 결과를 보고 결정)
if structure["status"] == "success":
    opportunity = run_analysis(
        query="전기차 충전 인프라 시장 기회 발굴",
        context={"domain_id": "EV_Charging_KR", "region": "KR"}
    )
    add_run(project_id, opportunity["run_id"], "기회 발굴")

    # 5. 기회가 발견되었으면 전략 설계
    opp_ledger = get_run_ledger(opportunity["run_id"])
    if opportunity["status"] == "success":
        strategy = run_analysis(
            query="전기차 충전 시장 진입 전략 설계",
            context={"domain_id": "EV_Charging_KR", "region": "KR"}
        )
        add_run(project_id, strategy["run_id"], "전략 설계")

# 6. 종합 보고서 생성 (rlm_query로 LM에게 위임)
report = rlm_query(f"""
다음 분석 결과를 종합하여 보고서를 작성하세요:

시장 구조: {ledger}
기회 발굴: {opp_ledger}
전략 설계: {get_run_ledger(strategy['run_id'])}
""")

save_deliverable(project_id, "final_report.md", report)
complete_project(project_id)
FINAL_VAR(report)
```

### 6.2 중단 후 재개

```bash
python -m bridge.runner --resume ev-charging-korea-20260317
```

LM은 `load_project()`로 프로젝트 상태를 확인하고, `get_run_ledger()`로 이전 Run의 결과를 읽어서 남은 분석만 수행한다.

---

## 7. 기존 코드와의 관계

### 7.1 변경하지 않는 것

| 파일/디렉토리 | 이유 |
|-------------|------|
| `cmis_core/` 전체 | Bridge는 import만 한다 |
| `cmis_core/orchestration/` 전체 | Kernel, Verifier, Governor, Replanner 그대로 사용 |
| `cmis_core/stores/` 전체 | RunStore, LedgerStore, ArtifactStore 그대로 사용 |
| `cmis_cli/` | CLI는 그대로 동작 |
| `config/`, `libraries/` | 기존 설정/패턴 그대로 사용 |

### 7.2 새로 추가하는 것

| 파일 | 줄 수 | 용도 |
|------|------|------|
| `bridge/__init__.py` | ~5 | 패키지 초기화 |
| `bridge/tools.py` | ~200 | CMIS → RLM 도구 변환 |
| `bridge/project.py` | ~150 | 프로젝트 Scope (다중 Run 래퍼) |
| `bridge/system_prompt.py` | ~80 | 시스템 프롬프트 |
| `bridge/runner.py` | ~100 | 진입점 + CLI |
| `projects/.gitkeep` | 0 | 디렉토리 |
| **합계** | **~535** | |

### 7.3 v0.1.0 대비 제거된 것

| v0.1.0에서 계획했던 것 | v0.2.0에서 제거한 이유 |
|-----------------------|---------------------|
| `bridge/scope.py` (120줄) — Scope 전체 구현 | CMIS RunStore + LedgerStore가 Run 단위 관리를 이미 수행. project.py가 Run 간 연결만 추가 |
| `bridge/events.py` (60줄) — 이벤트 전체 구현 | CMIS RunStore가 12종 이벤트 + 9종 의사결정을 이미 SQLite에 기록. project.py가 프로젝트 수준 이벤트만 추가 |
| `state_machine.py` — 상태 머신 구현 | CMIS Kernel의 Reconcile Loop + Governor + Verifier가 이미 상태 관리 수행 |
| `gates.py` — 게이트 구현 | CMIS PolicyEngine의 8개 게이트 + Governor의 예산/Stall 게이트가 이미 존재 |

---

## 8. 구현 작업 순서

| 순서 | 파일 | 작업 | 의존성 |
|------|------|------|-------|
| **1** | `bridge/__init__.py` | 패키지 초기화 | 없음 |
| **2** | `bridge/project.py` | 프로젝트 CRUD + 이벤트 | 없음 |
| **3** | `bridge/tools.py` | CMIS 엔진 래핑 | cmis_core |
| **4** | `bridge/system_prompt.py` | 시스템 프롬프트 | tools.py 도구 목록 확정 후 |
| **5** | `bridge/runner.py` | 진입점 + CLI | 2~4 전부 |
| **6** | `requirements.txt` 수정 | `rlms>=0.1.1` 추가 | 없음 |
| **7** | `projects/.gitkeep` | 디렉토리 | 없음 |

**작업 1~3은 병렬 가능.**

### 8.1 구현 시 확인할 CMIS 메서드 시그니처

tools.py 구현 시 다음 파일의 실제 메서드 시그니처를 확인할 것:

| 래퍼 함수 | CMIS 메서드 | 확인할 파일 |
|---------|-----------|-----------|
| `run_analysis()` | `OrchestrationKernel.execute(RunRequest)` | `cmis_core/orchestration/kernel.py:113` |
| `collect_evidence()` | `EvidenceEngine.collect(...)` | `cmis_core/evidence_engine.py` |
| `build_snapshot()` | `WorldEngine.snapshot(...)` | `cmis_core/world_engine.py` |
| `match_patterns()` | `PatternEngineV2.match_patterns(...)` | `cmis_core/pattern_engine_v2.py` |
| `evaluate_metrics()` | `ValueEngine.evaluate_metrics(...)` | `cmis_core/value_engine.py` |
| `get_policy()` | `PolicyEngine.resolve_policy(...)` | `cmis_core/policy_engine.py` |

---

## 9. 테스트 계획

### 9.1 단위 테스트

| 테스트 | 대상 | 검증 |
|--------|------|------|
| `test_project_crud` | project.py | create → add_run → load → complete 순환 |
| `test_project_events` | project.py | 이벤트 기록 → 읽기 → revision 순서 |
| `test_tools_safe_call` | tools.py | 오류 시 `{"error": ...}` 반환 |
| `test_tools_tier_separation` | tools.py | Tier 1/2 도구가 올바른 형식으로 반환 |

### 9.2 통합 테스트

| 테스트 | 검증 |
|--------|------|
| `test_rlm_tool_registration` | `as_rlm_tools()`가 RLM에 등록 가능한 형식인지 |
| `test_kernel_via_bridge` | `run_analysis()` → Kernel 실행 → RunStore에 이벤트 기록 |
| `test_project_multi_run` | 프로젝트에 여러 Run 등록 → 이전 Run의 Ledger 조회 |

---

## 10. 향후 확장

| 확장 | 설명 |
|------|------|
| **LLM 기반 GoalBuilder** | CMIS의 GoalBuilder를 LLM 기반으로 교체 (현재 키워드 규칙만). Bridge가 아닌 cmis_core 수정 |
| **LLM 기반 Replanner** | CMIS의 Replanner를 LLM 기반으로 교체 (현재 규칙 기반만). 마찬가지로 cmis_core 수정 |
| **Persistent RLM** | `RLM(persistent=True)` 사용하여 대화형 분석. 프로젝트 Scope와 결합 |
| **Docker 환경** | RLM의 `docker_repl` 사용하여 코드 실행 격리 |
| **Visualizer 연동** | RLM의 visualizer 웹 앱으로 분석 궤적 시각화 |

---

## 부록 A: 참조 파일 경로

### RLM 레포 (`https://github.com/alexzhang13/rlm`)

| 파일 | 용도 |
|------|------|
| `rlm/core/rlm.py` | RLM 클래스 — `completion()`, `custom_tools` 처리 |
| `rlm/environments/local_repl.py` | REPL — `_inject_tools()`에서 custom_tools 주입 |
| `rlm/core/types.py` | `RLMChatCompletion` 등 반환 타입 |
| `examples/custom_tools_example.py` | custom_tools 사용 예제 |

### CMIS 레포 (`https://github.com/kangminlee-maker/cmis`)

| 파일 | 용도 |
|------|------|
| `cmis_core/orchestration/kernel.py` | OrchestrationKernel — Reconcile Loop |
| `cmis_core/orchestration/verifier.py` | Verifier — Goal Predicate 검증 |
| `cmis_core/orchestration/ledgers.py` | ProjectLedger, ProgressLedger |
| `cmis_core/orchestration/governor.py` | Budget/Stall 제어 |
| `cmis_core/orchestration/replanner.py` | Diff → Task 재생성 |
| `cmis_core/orchestration/executor.py` | Task 실행 (Workflow/Evidence/Metric) |
| `cmis_core/orchestration/goal.py` | GoalBuilder (키워드 기반) |
| `cmis_core/orchestration/task.py` | Task 모델 + TaskQueue |
| `cmis_core/stores/run_store.py` | RunStore (SQLite) — 이벤트/의사결정 |
| `cmis_core/stores/ledger_store.py` | LedgerStore (SQLite) — Ledger 스냅샷 |
| `cmis_core/stores/artifact_store.py` | ArtifactStore (파일+SQLite) |
| `cmis_core/world_engine.py` | `snapshot()` — R-Graph |
| `cmis_core/pattern_engine_v2.py` | `match_patterns()`, `discover_gaps()` |
| `cmis_core/value_engine.py` | `evaluate_metrics()` — 4-Method Fusion |
| `cmis_core/evidence_engine.py` | `collect()` — Evidence 수집 |
| `cmis_core/strategy_engine.py` | `search_strategies()`, `evaluate_portfolio()` |
| `cmis_core/policy_engine.py` | `resolve_policy()` — 정책 라우팅 + 8개 게이트 |
| `config/workflows.yaml` | 4개 Canonical Workflow |
| `config/policies.yaml` | 정책 팩 (3모드 × 5프로필) |
