# dev/ 폴더 구조 가이드

**작성일**: 2025-12-09  
**최종 업데이트**: 2025-12-09 (CMIS 전환 완료)

---

## 개요

dev/ 폴더는 CMIS 개발과 관련된 모든 자료를 담습니다.  
프로덕션 루트는 **실행에 필요한 최소 파일만** 유지합니다.

**프로덕션 루트** (8개):
- cmis.yaml, cmis_core/, cmis_cli/, config/, seeds/
- requirements.txt, README.md, env.example

**개발 (dev/)**: 테스트, 문서, 예시, 참조, 이력 등

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

## 현재 구조 (2025-12-09 최종)

```
dev/
├── tests/                    # 기능 테스트 (pytest) - 44개 ✅
│   ├── unit/                 # 단위 테스트 (6개)
│   │   ├── test_graph.py
│   │   ├── test_world_engine.py
│   │   ├── test_value_engine.py
│   │   ├── test_pattern_engine.py
│   │   ├── test_config.py
│   │   └── test_dart_connector.py
│   ├── integration/          # 통합 테스트 (2개)
│   │   ├── test_workflow.py
│   │   └── test_report_generator.py
│   ├── e2e/                  # E2E 테스트 (1개)
│   │   └── test_e2e_structure_analysis.py
│   └── conftest.py           # pytest fixtures
│
├── scripts/
│   └── validation/           # 시스템 검증 (3개)
│       ├── validate_yaml_integrity.py
│       ├── validate_codebase.py
│       └── fix_yaml.py
│
├── examples/                 # 사용 예시
│   └── project_context_examples.yaml (3 시나리오)
│
├── v7_reference/             # v7 (UMIS) 참조 자료
│   ├── code/                 # v7 실제 코드
│   │   └── v7_reference_code/ (GitHub alpha)
│   ├── docs/                 # v7 문서/스키마
│   │   ├── Observer_v7.x/
│   │   └── reference_deprecated/
│   ├── outputs/              # v7 결과물 예시
│   │   └── market_reality_report_v7.x/ (548줄)
│   └── README.md             # v7 vs CMIS 비교
│
├── docs/
│   ├── architecture/         # 아키텍처 (4개)
│   │   ├── CMIS_Architecture_Blueprint.md
│   │   ├── cmis_philosophy_concept.md
│   │   ├── cmis_roadmap.md
│   │   └── cmis_project_context_layer_design.md
│   ├── analysis/             # 분석 (4개)
│   │   ├── CMIS_Architecture_Gap_Analysis.md
│   │   ├── CMIS_Project_Context_Philosophy_Alignment.md
│   │   ├── V7_Code_Reuse_Analysis.md
│   │   └── System_Naming_Analysis.md
│   └── implementation/       # 구현 (5개)
│       ├── CMIS_Implementation_Roadmap_Structure_Analysis.md
│       ├── CMIS_Implementation_Strategy_Final.md
│       ├── CMIS_Structure_Analysis_Detailed_Workflow.md
│       ├── CMIS_Structure_Analysis_Diagrams.md (13개 다이어그램)
│       └── cmis_structure_analysis_tasks.md
│
├── session_summary/          # 개발 세션 이력 (3개)
│   ├── session_summary_202512051421.yaml
│   ├── session_summary_202512051708.yaml
│   └── session_summary_20251209.yaml
│
├── backup/                   # 백업 파일
├── temp/                     # 임시 파일
└── STRUCTURE.md              # 이 문서
```

---

## 프로덕션 루트 (8개)

```
cmis/
├── cmis.yaml              # 1. 메인 스키마 (1,767줄)
├── cmis_core/             # 2. Core 엔진 (8개)
├── cmis_cli/              # 3. CLI
├── config/                # 4. 설정 YAML (8개 + domain_registry)
├── seeds/                 # 5. Reality seed
├── requirements.txt       # 6. 의존성
├── README.md              # 7. 메인 문서
└── env.example            # 8. 환경변수 템플릿

(+ pytest.ini)             # 테스트 설정
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

## 파일 분류 기준

### 프로덕션 루트에 두는 것
- ✅ 실행 필수 파일 (cmis.yaml, cmis_core/, seeds/)
- ✅ 사용자 직접 접근 파일 (README.md, env.example)
- ✅ 의존성/설정 (requirements.txt, pytest.ini)

### dev/에 두는 것
- ✅ 테스트 코드 (tests/)
- ✅ 검증 스크립트 (scripts/validation/)
- ✅ 문서 (docs/)
- ✅ 예시 (examples/)
- ✅ 참조 자료 (v7_reference/)
- ✅ 개발 이력 (session_summary/)
- ✅ 백업/임시 (backup/, temp/)

---

## 체크리스트

**개발 중**:
- [ ] pytest 실행 (매 커밋)
- [ ] 새 기능 추가 시 test 작성
- [ ] Legacy 코멘트 지양 (v1/v2 표시 등)

**배포 전**:
- [ ] pytest 전체 통과 (44개)
- [ ] validate_yaml_integrity.py 통과
- [ ] 프로덕션 루트 깔끔 확인 (8개만)
- [ ] README 업데이트

**브랜드**:
- ✅ CMIS (Contextual Market Intelligence System)
- ✅ UMIS 표시 완전 제거
- ✅ v1/v7 legacy 코멘트 제거

