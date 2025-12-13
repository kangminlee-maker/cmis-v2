# NEXT_SESSION_GUIDE (최신)

**최신 가이드**: `dev/session_summary/20251213_NEXT_SESSION_GUIDE.md`

이 파일은 항상 "다음 세션에 바로 시작할 수 있는" 최소 정보만 유지합니다.

---

## 다음 세션 핵심 목표(우선순위)

### 1) Orchestration Kernel을 시스템 중심으로 심화
- GoalGraph/Predicates 정교화(D-Graph 연동 포함)
- Evidence plan / Open questions 생성 규칙 강화
- Tool/Resource registry의 실제 실행 연결(안전 호출/제약)

### 2) 품질/회귀 방지(Eval Harness) 구축
- `eval/regression_suite.yaml`, `eval/canary_domains.yaml` 기반 러너
- 지표 기반 조기 경보(prior 사용률/검증 실패율/evidence hit rate)
- run_store 기록 및 임계치 위반 시 FAIL 차단

### 3) Belief Engine의 안전한 Prior 구조화
- prior 분포 참조(`distribution_ref`) 체계
- prior 채택/기각의 정책 근거 로그 강제
- prior 기반 산출물에 "추정" 표기 강제

---

## 시작 체크리스트

### 정합성
```bash
python3 -m cmis_cli config-validate --check-registry --check-patterns --check-workflows
```

### 핵심 테스트
```bash
pytest -q dev/tests/unit/test_cursor_agent_interface_v2.py dev/tests/unit/test_spec_registry_consistency.py
```

---

## 컨텍스트 앵커(주요 파일)

- Contracts/Registry: `cmis.yaml`
- Ledger schema: `schemas/ledgers.yaml`
- Kernel: `cmis_core/orchestration/kernel.py`, `ledgers.py`, `verifier.py`, `replanner.py`
- Stores/View: `cmis_core/stores/`, `cmis_core/run_exporter.py`
- Focal context: `cmis_core/types.py`, `cmis_core/context_binding.py`
- Cursor interface: `cmis_cli/commands/cursor.py`
