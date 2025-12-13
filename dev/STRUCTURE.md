# CMIS 프로젝트 구조

**업데이트**: 2025-12-13
**버전**: v3.6.0

---

## 📁 루트 구조

```
cmis/
├─ cmis.yaml                    # Contracts + Registry (v3.6.0)
│
├─ schemas/                     # 타입 시스템 (데이터 구조)
│  ├─ ledgers.yaml
│  ├─ ontology.yaml (생성 예정)
│  └─ *_graph.yaml (4개, 생성 예정)
│
├─ libraries/                   # 도메인 지식/데이터
│  ├─ patterns/ (23개)
│  ├─ domains/
│  ├─ domain_registry.yaml
│  ├─ pattern_library.yaml (생성 예정)
│  └─ metrics_spec.yaml (생성 예정)
│
├─ config/                      # 런타임 설정
│  ├─ policies.yaml
│  ├─ workflows.yaml
│  ├─ archetypes/ (6개)
│  └─ sources/
│
├─ cmis_core/                   # Core 엔진
├─ cmis_cli/                    # CLI 인터페이스
├─ requirements.txt             # Python 의존성
├─ README.md                    # 프로젝트 README
├─ CHANGELOG.md                 # 변경 이력
├─ env.example                  # 환경 변수 예시
└─ dev/                         # 개발 전용
```

---

## 🔧 cmis_core/ (엔진)

```
cmis_core/
├─ belief_engine.py             # BeliefEngine (v1.0)
├─ prior_manager.py
├─ belief_updater.py
├─ uncertainty_propagator.py
├─ world_engine.py              # World Engine (v2.0)
├─ pattern_engine_v2.py         # Pattern Engine (v2.0)
├─ value_engine.py              # Value Engine
├─ strategy_engine.py           # Strategy Engine (v1.0)
├─ learning_engine.py           # Learning Engine (v1.0)
├─ evidence_engine.py           # Evidence Engine
├─ policy_engine.py             # Policy Engine
├─ workflow.py                  # WorkflowOrchestrator
├─ config.py                    # Config 로더
├─ graph.py                     # Graph 구조
└─ types.py                     # 공통 타입
```

**총 9개 엔진 (100% 완성)**

---

## 💻 cmis_cli/ (CLI)

```
cmis_cli/
├─ __main__.py                  # CLI 진입점
├─ commands/                    # 명령어 (8개)
│  ├─ structure_analysis.py
│  ├─ opportunity_discovery.py
│  ├─ compare_contexts.py
│  ├─ workflow_run.py
│  ├─ batch_analysis.py
│  ├─ report_generate.py
│  ├─ cache_manage.py
│  └─ config_validate.py
└─ formatters/                  # 출력 포맷
   ├─ json_formatter.py
   └─ markdown_formatter.py
```

---

## ⚙️ config/ (설정)

```
config/
├─ archetypes/                  # Context Archetype (6개)
│  ├─ ARCH-digital_service_KR.yaml
│  ├─ ARCH-education_platform_KR.yaml
│  └─ ...
└─ (미래) 외부 모듈
   ├─ policies.yaml
   ├─ workflows.yaml
   ├─ metrics_spec.yaml
   └─ pattern_library.yaml
```

---

## 📚 dev/ (개발 전용)

```
dev/
├─ docs/                        # 문서
│  ├─ architecture/             # 아키텍처 설계 (18개)
│  ├─ user_guide/               # 사용자 가이드
│  ├─ analysis/                 # 분석 문서
│  └─ implementation/           # 구현 문서
│
├─ tests/                       # 테스트
│  ├─ unit/                     # 단위 테스트 (420+개)
│  ├─ integration/              # 통합 테스트
│  └─ conftest.py
│
├─ session_summary/             # 세션 요약
│  ├─ 20251211/
│  ├─ 20251212/
│  └─ *.md
│
├─ deprecated/                  # 구버전 보관
│  └─ docs/
│     └─ architecture_v3.3_and_earlier/  (25개)
│
├─ examples/                    # 예시
│  └─ seeds/                    # 샘플 데이터
│
├─ validation/                  # 검증 스크립트
│
└─ STRUCTURE.md (본 문서)
```

---

## 📖 문서 구조 (dev/docs/)

### architecture/ (18개 - Active)

**핵심 (4개)**:
- cmis_philosophy_concept.md (철학)
- CMIS_Architecture_Blueprint_v3.4_km.md (전체 아키텍처)
- CMIS_Orchestration_Kernel_Design.md (Reconcile Loop)
- Blueprint_v3.4_Review.md (검토 문서)

**엔진별 (7개)**:
- BeliefEngine_Design_Enhanced.md
- World_Engine_Enhanced_Design.md
- PatternEngine_Design_Final.md
- StrategyEngine_Design_Enhanced.md
- LearningEngine_Design_Enhanced.md
- Workflow_CLI_Design_Enhanced.md
- Search_Strategy_Design_v2.md

**보조 (7개)**:
- BeliefEngine 관련 3개
- StrategyEngine 관련 2개
- cmis_project_context_layer_design.md
- README.md

---

### deprecated/docs/architecture_v3.3_and_earlier/ (25개)

**v3.3 문서**: Blueprint, Implementation Status, Roadmap

**구버전 엔진 설계**: World v1-v2, Pattern v1.1, Strategy v1, Learning v1, Workflow v1

**Orchestration 설계 진화**:
- CMIS_Cursor_Agent_Interface_Design.md (v1.1)
- CMIS_Adaptive_Execution_Design.md (v2.0)
→ CMIS_Orchestration_Kernel_Design.md (v3.0, 최신)

**검토/분석**: Philosophy Review, Blueprint Review 등

---

## 🗂️ 데이터 구조

```
data/                           # 런타임 데이터 (.gitignore)
├─ value_store/                 # ValueRecord 영속화
├─ artifacts/                   # Monte Carlo samples 등
├─ cache/                       # 캐시 (선택적)
└─ graphs/                      # Graph 백엔드 (선택적)
```

---

## 🔄 버전 관리 규칙

### Architecture 문서

**버전 업그레이드 시** (예: v3.4 → v3.5):

```bash
# 1. 신규 문서 작성
vi dev/docs/architecture/CMIS_Architecture_Blueprint_v3.5.md

# 2. 구버전 이동
mkdir dev/deprecated/docs/architecture_v3.4
mv dev/docs/architecture/*_v3.4*.md dev/deprecated/docs/architecture_v3.4/

# 3. README 업데이트
vi dev/docs/architecture/README.md
```

**폴더명 = Deprecated 문서 버전**

**현재**:
- Active: v3.4 및 최신
- Deprecated: architecture_v3.3_and_earlier/

---

## 📊 코드 통계 (v3.6.0)

```
Core 엔진:        ~15,000줄
CLI:              ~2,500줄
Tests:            ~8,000줄 (420+개)
Documentation:    ~35,000줄
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:           ~60,000줄
```

---

## 🎯 핵심 원칙

1. **프로덕션 루트는 최소화** (8개 항목만)
2. **dev/ 아래에 모든 개발 자료**
3. **문서는 버전별 폴더로 정리**
4. **테스트는 Phase별/엔진별 분리**
5. **Deprecated는 명확한 버전 폴더**

---

**작성**: 2025-12-13
**버전**: v3.6.0
**상태**: 정리 완료 ✅
