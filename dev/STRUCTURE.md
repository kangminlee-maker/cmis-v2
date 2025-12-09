# dev/ 폴더 구조 가이드

**작성일**: 2025-12-09

---

## Test vs Validation

### Test (기능 테스트)
**목적**: 개발 중 지속적 기능 검증
- 단위 테스트 (Unit Test)
- 통합 테스트 (Integration Test)
- E2E 테스트 (End-to-End Test)

**도구**: pytest
**실행**: 개발 중 자주 (코드 변경 시마다)
**예시**:
- test_world_engine.py: World Engine 기능 테스트
- test_value_engine.py: Metric 계산 로직 테스트
- test_e2e_structure_analysis.py: 전체 워크플로우 테스트

**위치**: `dev/tests/`

---

### Validation (시스템 검증)
**목적**: 배포 전 시스템 전체 무결성 확인
- 구조적 검증 (YAML 문법, Python 문법)
- 논리적 검증 (순환 참조, 타입 일관성)
- 규약 검증 (네이밍, 스키마 준수)
- 품질 검증 (코드 스타일, 문서 일치성)

**도구**: 커스텀 스크립트
**실행**: 배포 전, PR 전
**예시**:
- validate_yaml_integrity.py: YAML 무결성 (36 Metrics, 4 Graphs 등)
- validate_codebase.py: 전체 코드베이스 검증
- fix_yaml.py: YAML 자동 수정

**위치**: `dev/scripts/validation/`

---

## 권장 구조

```
dev/
├── tests/                    # 기능 테스트 (pytest)
│   ├── unit/                 # 단위 테스트
│   │   ├── test_graph.py
│   │   ├── test_world_engine.py
│   │   ├── test_value_engine.py
│   │   └── test_pattern_engine.py
│   ├── integration/          # 통합 테스트
│   │   ├── test_workflow.py
│   │   └── test_report_generator.py
│   ├── e2e/                  # E2E 테스트
│   │   └── test_e2e_structure_analysis.py
│   └── conftest.py
│
├── scripts/
│   ├── validation/           # 시스템 검증
│   │   ├── validate_yaml_integrity.py
│   │   ├── validate_codebase.py
│   │   └── fix_yaml.py
│   └── tools/                # 기타 유틸리티
│       └── add_rename_notice.py
│
├── examples/                 # 사용 예시
│   └── project_context_examples.yaml
│
├── reference/                # 참조 자료
│   ├── v7/
│   └── deprecated/
│
├── docs/
│   ├── architecture/         # 아키텍처
│   ├── analysis/             # 분석
│   └── implementation/       # 구현
│
├── backup/                   # 백업
└── temp/                     # 임시
```

---

## 실행 방법

### 개발 중 테스트
```bash
# 전체 테스트
pytest

# 특정 카테고리
pytest dev/tests/unit/
pytest dev/tests/integration/
pytest dev/tests/e2e/

# 빠른 확인
pytest -q
```

### 배포 전 검증
```bash
# YAML 무결성
python3 dev/scripts/validation/validate_yaml_integrity.py

# 전체 코드베이스
pytest && python3 dev/scripts/validation/validate_codebase.py
```

---

## 체크리스트

**개발 중**:
- [ ] pytest 실행 (매 커밋)
- [ ] 새 기능 추가 시 test 작성

**배포 전**:
- [ ] pytest 전체 통과
- [ ] validate_yaml_integrity.py 통과
- [ ] validate_codebase.py 통과
- [ ] README 업데이트

