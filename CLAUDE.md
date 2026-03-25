# CLAUDE.md — CMIS v2

domain: market-intelligence
secondary_domains: llm-native-development

## Project Overview

CMIS v2 = RLM(Recursive Language Model) + KBD(Knowledge-Based Design) 기반 Market Intelligence OS. 정확한 숫자가 없을 때 관계 추론 + 경계 제약 + Fermi 추정으로 합리적으로 추정하는 시장 분석 시스템.

## User Communication

사용자는 제품/도메인 전문가이며 개발 비전문가. 빠른 결정, 철저한 검증. 간결함 선호.

### 소통 규칙
- 기술 용어 유지 + 설명 첨부. 쉬운 말로 대체 금지.
- 학술적/현학적 용어 지양. 쉬운 말로 같은 정확성 달성.
- 비유/은유 금지. 직접 설명.
- 리스크는 선택 시점에 제시. 결정 후 추가 리스크 금지.
- 선택지가 하나뿐이어도 사용자에게 확인. 자동 적용 금지.
- 순수 기술 결정: Builder 소관이지만, 장단점 + 추천 안내.
- 시스템이 아는 모든 정보 제공. 정보와 결정을 구분.
- 이름은 역할 기준. 실제로 일어나는 일을 반영.
- 의미의 정확성 > 편의성. 기존 용어 의미 확장 금지, 정확한 새 개념 추가.
- 복잡도 = 통제 가능성. 크기가 아님.
- 문서를 위한 문서 금지. 기존 문서에 간결 포함.
- 전역 규칙은 model-independent 위치(README.md 등)에 배치.
- 행위 주체는 설계 원칙에서 도출. 원칙에서 논리적으로 추론.

### 작업 방식
- 주요 결정마다 병렬 에이전트 리뷰 (8인 onto-review).
- 2라운드 구조: Round 1 독립 리뷰 → Philosopher 종합 → (조건부) Round 2 토론.
- 리뷰 기준: 목적·철학·persona 정합성 우선. 단순 오류 검출보다 상위.
- 전문가 만장일치도 근거 약하면 재검토. 합의 자체가 아니라 합의의 논리를 평가.
- 결정은 빠르게, 검증은 철저하게.
- 커밋은 의미 있는 작업 단위로.
- 상위설계: 레거시 무관. 세부구현: 레거시 참고 (실패 반복 방지).
- 좋은 이름이 떠오르지 않으면 기존 이름 유지.

### Anti-Patterns (X → O)
| 하지 말 것 | 해야 할 것 |
|-----------|-----------|
| 기술 용어를 쉬운 말로 대체 | 용어 유지 + 설명 첨부 |
| 학술적 용어로 정확성 추구 | 쉬운 말로 같은 정확성 달성 |
| 별도 문서로 원칙을 장황하게 서술 | 기존 문서에 간결 포함 |
| 리스크를 결정 후 별도 섹션에 제시 | 선택 시점에 각 선택지 리스크 제시 |
| 전문가 만장일치를 무비판적 수용 | 합의 근거를 별도 검증 |
| "파급범위가 크다"로 차선책 선택 | "통제 가능한 복잡도인가" 기준 |
| 편의를 위해 기존 용어 의미 확장 | 의미가 정확한 새 개념 추가 |

## Tech Stack

<!-- auto:tech-stack -->
- Programming Language: Python 3.11+
- Framework: RLM (rlms), Pydantic v2
- Package Manager: pip
- Type Checking: mypy strict
<!-- /auto:tech-stack -->

## System Structure

<!-- auto:system-structure -->
- **Ontology Code Generator**: `scripts/generate_from_ontology.py` — schemas/ontology.yaml → generated/types.py, validators.py 자동 생성
- **Pattern Validator**: `scripts/validate_patterns.py` — libraries/patterns/*.yaml 검증
- **Ontology Map**: `docs/ontology-map.md` — 자동 생성 타입 맵
- **Policy Pack**: `config/policies.yaml` — 3단계 정책 모드 (strict/balanced/friendly) + 8개 게이트 선언
- **State Machine**: `cmis_v2/state_machine.py` — 14상태 21전이 5 user gate
- **Event System**: `cmis_v2/events.py` — SQLite WAL 모드 이벤트 영속화
- **8-Agent Panel Review**: `~/.claude/plugins/onto-review/` — 7인 검증 + Philosopher 종합
<!-- /auto:system-structure -->

## Verification Loop

<!-- auto:verify -->
After every change: `python3 -c "from cmis_v2.tools import CMISTools; t = CMISTools(); print('OK')"` (import 검증).
Before PR: `python3 -m pytest dev/tests/ -x -q` (테스트 실행).
<!-- /auto:verify -->

## Code Style

Follow `@.claude/rules/coding-conventions.md` for all code.

## Project Patterns

Follow `@.claude/rules/project-patterns.md` for file naming, conventions, and terminology.

## Plan Mode — Design Protocol

Every non-trivial task starts in plan mode. Complete all 4 steps before switching to auto-accept.

**Step 1 — Scope Lock**
- In scope: concrete outcomes this change delivers
- Out of scope: anything else (tag Phase 2 if worth revisiting)
- Affected surface: which existing files/modules are touched
- Never expand scope mid-design

**Step 2 — Contracts First**
Define before writing any implementation:
- Input/output types: exact signatures for every public function/endpoint
- State transitions: all states, triggers, and illegal transitions
- Error cases: every failure mode with its type
- Invariants: conditions that must always hold

**Step 3 — Pre-mortem**
Answer explicitly before finalizing:
1. "If this fails in production, what breaks first?"
2. "What system state does this design not handle?"
3. "What assumption about existing code might be wrong?"

**Step 4 — Simplicity Gate**
- Remove any abstraction layer that isn't required for correctness
- Every new file/type/function must trace to a Step 1 requirement

**Transition**: If Claude can't 1-shot the implementation from this plan, the plan isn't done.

## Parallel Work

Subagents for clean context windows. One agent per file. For parallel streams: `git worktree add .claude/worktrees/<n> origin/main`

## Commit Protocol

커밋 또는 푸시 전에 다음 문서가 현재 코드를 반영하는지 확인하고, 필요시 업데이트합니다:
<!-- auto:commit-protocol -->
- `CHANGELOG.md` — 새 버전/변경 사항 추가
- `README.md` — 현재 규모 (파일 수, 테스트 수) + 새 기능 반영
- `docs/ontology-map.md` — ontology.yaml 변경 시 재생성
<!-- /auto:commit-protocol -->

이 규칙은 의미적 판단이므로 모든 커밋에 적용하지 않습니다. 기능 추가/구조 변경 커밋에만 적용합니다.

## Prohibitions

- No skipped error handling
- No commits without tests
- No breaking API changes without discussion
- No scope expansion beyond Step 1 lock
- No implementation with unresolved pre-mortem gaps
- No abstractions without concrete in-scope justification

## Self-Improvement

After every correction → update this file with a prevention rule.
