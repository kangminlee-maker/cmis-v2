# dev/ 폴더 구조 가이드

**작성일**: 2025-12-09  
**최종 업데이트**: 2025-12-11 (CMIS v3.3 완성)

---

## 개요

dev/ 폴더는 CMIS 개발과 관련된 모든 자료를 담습니다.  
프로덕션 루트는 **실행에 필요한 최소 파일만** 유지합니다.

**프로덕션 루트** (7개):
- cmis.yaml, cmis_core/, cmis_cli/, config/
- requirements.txt, README.md, env.example

**Note**: seeds/는 dev/examples/seeds/로 이동 (선택적)

**개발 (dev/)**: 테스트, 문서, 검증, 예시, 참조, 이력 등

---

## 현재 구조 (2025-12-11 최종)

```
dev/
├── tests/                    # 기능 테스트 (pytest) - 370개 ✅
│   ├── unit/                 # 단위 테스트 (200개)
│   │   ├── test_graph.py
│   │   ├── test_world_engine*.py (4개)
│   │   ├── test_value_engine.py
│   │   ├── test_pattern_engine*.py (3개)
│   │   ├── test_strategy_engine*.py (3개)
│   │   ├── test_learning_engine*.py (3개)
│   │   ├── test_workflow_cli*.py (2개)
│   │   ├── test_evidence_*.py (3개)
│   │   └── test_*.py (기타)
│   ├── integration/          # 통합 테스트 (150개)
│   │   ├── test_workflow.py
│   │   ├── test_pattern_engine_e2e.py
│   │   ├── test_real_api_sources.py
│   │   └── test_*.py (기타)
│   ├── e2e/                  # E2E 테스트 (20개)
│   │   └── test_e2e_structure_analysis.py
│   └── conftest.py           # pytest fixtures
│
├── validation/               # 시스템 검증 ✅ (이동 완료)
│   ├── validate_yaml_integrity.py
│   ├── validate_codebase.py
│   └── fix_yaml.py
│
├── examples/                 # 사용 예시
│   ├── project_context_examples.yaml (3 시나리오)
│   └── seeds/                # Reality seed (테스트/데모용)
│       └── Adult_Language_Education_KR_reality_seed.yaml
│
├── v7_reference/             # v7 (UMIS) 참조 자료
│   ├── code/
│   ├── docs/
│   ├── outputs/
│   └── README.md
│
├── deprecated/               # 구버전 보관 ✅ (신규)
│   └── docs/
│       └── architecture/     # 구버전 설계 문서 (13개)
│
├── docs/
│   ├── architecture/         # 아키텍처 (13개) ✅ 정리 완료
│   │   ├── README.md (인덱스)
│   │   ├── CMIS_Architecture_Blueprint_v3.3.md
│   │   ├── CMIS_Implementation_Status_v3.3.md
│   │   ├── CMIS_Roadmap_v3.3.md
│   │   ├── cmis_philosophy_concept.md
│   │   ├── cmis_project_context_layer_design.md
│   │   ├── PatternEngine_Design_Final.md
│   │   ├── StrategyEngine_Design_Enhanced.md
│   │   ├── LearningEngine_Design_Enhanced.md
│   │   ├── World_Engine_Enhanced_Design.md
│   │   ├── Workflow_CLI_Design_Enhanced.md
│   │   ├── Search_Strategy_Design_v2.md
│   │   └── CMIS_LLM_Infrastructure_*.md (2개)
│   ├── analysis/             # 분석
│   └── implementation/       # 구현
│
├── session_summary/          # 개발 세션 이력
│   ├── 20251210/             # 2025-12-10 세션 (20개)
│   ├── 20251211/             # 2025-12-11 세션 (25개) ✅
│   ├── INDEX.md
│   └── README.md
│
└── STRUCTURE.md              # 이 문서
```

---

## Test vs Validation (명확화)

### tests/ (기능 테스트)
**목적**: 개발 중 지속적 기능 검증
**도구**: pytest
**실행**: 코드 변경 시마다
**현황**: 370/375 passed (98.7%)

### validation/ (시스템 검증)
**목적**: 배포 전 시스템 전체 무결성 확인
**도구**: 커스텀 스크립트
**실행**: 배포 전, PR 전

**위치 변경**: ✅
- Before: `dev/scripts/validation/`
- After: `dev/validation/`

---

## 프로덕션 루트 (8개)

```
/Users/kangmin/v9_dev/
├── cmis.yaml              # 1. 메인 스키마
├── cmis_core/             # 2. Core 엔진 (25개 .py)
├── cmis_cli/              # 3. CLI (3개 폴더, 8개 명령어)
├── config/                # 4. 설정 YAML
│   ├── patterns/          # 23개 Pattern
│   ├── archetypes/        # 6개 Archetype
│   ├── sources/           # Data source 설정
│   └── *.yaml             # 기타 설정
├── requirements.txt       # 5. 의존성
├── README.md              # 6. 메인 문서
└── env.example            # 7. 환경변수 템플릿

Note: seeds/는 dev/examples/seeds/로 이동 (선택적)
```

---

## 실행 방법

### 개발 중 테스트
```bash
# 전체 테스트
pytest

# 특정 엔진
pytest dev/tests/unit/test_world_engine*.py
pytest dev/tests/unit/test_strategy_engine*.py

# 빠른 확인
pytest -q
```

### 배포 전 검증
```bash
# YAML 무결성
python3 dev/validation/validate_yaml_integrity.py

# 전체 코드베이스
python3 dev/validation/validate_codebase.py

# 테스트 + 검증
pytest && python3 dev/validation/validate_codebase.py
```

### CLI 사용
```bash
# 시장 분석
python3 -m cmis_cli structure-analysis --domain ... --region ...

# 기회 발굴
python3 -m cmis_cli opportunity-discovery --domain ... --top-n 5

# 일괄 분석
python3 -m cmis_cli batch-analysis --config batch.yaml --parallel

# 설정 검증
python3 -m cmis_cli config-validate --check-all
```

---

## 파일 분류 기준

### 프로덕션 루트
- ✅ 실행 필수 (cmis.yaml, cmis_core/, config/, seeds/)
- ✅ 사용자 직접 접근 (README.md, env.example)
- ✅ 의존성/설정 (requirements.txt, pytest.ini)

### dev/
- ✅ 테스트 (tests/)
- ✅ 검증 스크립트 (validation/)
- ✅ 문서 (docs/)
- ✅ 예시 (examples/)
- ✅ 참조 (v7_reference/)
- ✅ 세션 이력 (session_summary/)
- ✅ Deprecated (deprecated/)

---

## 체크리스트

### 개발 중
- [x] pytest 실행 (매 커밋)
- [x] 새 기능 추가 시 test 작성
- [x] Legacy 코멘트 제거
- [x] CMIS 브랜드 통일

### 배포 전
- [x] pytest 370/375 통과
- [ ] validate_yaml_integrity.py 통과
- [x] 프로덕션 루트 깔끔 (8개만)
- [x] README.md 업데이트
- [x] 문서 정리 (deprecated 이동)

### 완성 (2025-12-11)
- [x] World Engine v2.0
- [x] Workflow CLI (8개 명령어)
- [x] Strategy Engine v1.0
- [x] Learning Engine v1.0
- [x] 4단계 루프 완성
- [x] 문서 정리

---

**작성**: 2025-12-09  
**업데이트**: 2025-12-11  
**상태**: CMIS v3.3 완성 ✅
