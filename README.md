# CMIS - Contextual Market Intelligence System

**버전**: v3.6.0
**상태**: Blueprint (Orchestration Kernel 설계)
**완성도**: 100% (9/9 엔진) + Orchestration 설계
**업데이트**: 2025-12-13

---

## 🎯 개요

CMIS는 시장/비즈니스 세계를 **Graph-of-Graphs**로 표현하고, **Understand → Discover → Decide → Learn** 루프를 통해 자동으로 시장을 분석하고 전략을 설계하는 Market Intelligence OS입니다.

**핵심 특징**:
- 🔄 완전한 학습 루프 (4단계)
- 🌍 Greenfield/Brownfield 완전 지원
- 📊 Graph-of-Graphs (R/P/V/D)
- 🤖 자동 전략 생성
- 📈 실제 결과로부터 학습

---

## 🚀 빠른 시작

### 설치

```bash
# 저장소 클론
git clone <repository-url>
cd v9_dev

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp env.example .env
# .env 파일 편집 (API 키 설정)
```

### 첫 분석

```bash
# 시장 구조 분석
python3 -m cmis_cli structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR

# 기회 발굴
python3 -m cmis_cli opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  --top-n 5
```

---

## 🏗️ 아키텍처

### CMIS 4단계 루프

```
1. Understand (이해)
   → World, Pattern, Value Engine
   → 시장 구조, 패턴, 지표 파악

2. Discover (발굴)
   → Pattern Engine (Gap Discovery)
   → 기회 자동 발굴

3. Decide (결정)
   → Strategy Engine
   → 전략 생성 및 평가

4. Learn (학습)
   → Learning Engine
   → 실제 결과로부터 학습
   ↓
1번으로 돌아감 (지속 개선)
```

### Graph-of-Graphs

- **R-Graph** (Reality): 시장 구조 (Actor, MoneyFlow, State)
- **P-Graph** (Pattern): 비즈니스 패턴 (23개 Pattern)
- **V-Graph** (Value): 지표/값 (Metric, ValueRecord)
- **D-Graph** (Decision): 전략/목표 (Goal, Strategy)

---

## ✅ 완성 엔진 (9/9) - 100%

### 1. Evidence Engine v2.2

**역할**: Evidence 수집 및 관리

**기능**:
- 6개 Source: DART, KOSIS, ECOS, WorldBank, Google, DuckDuckGo
- 3-Tier 시스템 (Official, Curated, Commercial)
- 캐싱 (24시간 TTL)

### 2. Pattern Engine v2.0

**역할**: 비즈니스 패턴 인식 및 Gap 발굴

**기능**:
- 23개 Pattern (5개 Family)
- Trait 기반 매칭 (Ontology lock-in 최소화)
- Structure Fit + Execution Fit
- Gap Discovery
- Context Archetype (6개)

### 3. Value Engine v2.0

**역할**: Metric 계산 및 평가

**기능**:
- 4-Stage Resolution (Evidence → Derived → Prior → Fusion)
- Pattern Benchmark 연동
- Lineage 완전 추적

### 4. World Engine v2.0

**역할**: Reality Graph 구축 및 관리

**기능**:
- Evidence → R-Graph 자동 변환
- Greenfield/Brownfield 지원
- as_of/segment 필터링
- 서브그래프 추출 (focal_actor 중심)
- 파일 백엔드, 캐싱
- 시계열 비교

### 5. Search Strategy v2.0

**역할**: 검색 전략 최적화

### 6. BeliefEngine v1.0 🆕

**역할**: Prior/Belief 관리 및 불확실성 정량화

**기능**:
- Prior Distribution 관리 (Pattern Benchmark, Uninformative)
- Bayesian Update (Normal, Lognormal, Beta, Empirical)
- Monte Carlo 불확실성 전파 (Sobol Sequence)
- AST evaluator (안전한 공식 평가)
- value_store 영속성
- Policy 통합 (reporting_strict/decision_balanced/exploration_friendly)

### 7. Workflow CLI

**역할**: 명령줄 인터페이스

**명령어** (8개):
```bash
cmis structure-analysis      # 시장 구조 분석
cmis opportunity-discovery   # 기회 발굴
cmis compare-contexts        # 컨텍스트 비교
cmis workflow run            # Generic workflow 실행
cmis batch-analysis          # 일괄 분석 (병렬)
cmis report-generate         # 보고서 생성
cmis cache-manage            # 캐시 관리
cmis config-validate         # 설정 검증
```

### 7. Strategy Engine v1.0

**역할**: 전략 생성 및 평가

**기능**:
- Pattern → Strategy 자동 생성
- Greenfield/Brownfield 지원
- ROI/Risk 예측
- Portfolio 최적화
- Synergy/Conflict 분석

### 8. Learning Engine v1.0

**역할**: 학습 및 시스템 개선

**기능**:
- Outcome vs 예측 비교
- Pattern Benchmark 학습 (Context별)
- ProjectContext 자동 업데이트
- Metric Belief 조정
- Outlier 감지

---

## 💡 사용 예시

### 1. Greenfield 분석 (시장 전체)

```bash
# 10억 자본으로 교육 시장 진입 전략
cmis opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  --budget 1000000000 \
  --top-n 5
```

**출력**:
- 매칭된 패턴 (구독, 플랫폼 등)
- 발견된 기회 (Gap)
- Feasibility 평가
- 예상 ROI

### 2. Brownfield 분석 (우리 회사 관점)

```bash
# 우리 회사 성장 전략
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --project-context PRJ-my-company
```

**출력**:
- focal_actor 중심 시장 구조
- 실행 가능한 전략 (Execution Fit 높음)
- 우리 baseline 기준 ROI
- 리스크 평가

### 3. 컨텍스트 비교

```bash
# Greenfield vs Brownfield 비교
cmis compare-contexts \
  --context1 "domain:Adult_Language_KR,region:KR" \
  --context2 "domain:Adult_Language_KR,region:KR,project_context:PRJ-001"
```

**출력**:
- Graph 구조 차이
- 패턴 차이
- Metrics 변화

### 4. 일괄 분석

```bash
# 여러 시장 동시 분석
cmis batch-analysis \
  --config markets_2025.yaml \
  --parallel \
  --workers 4
```

### 5. 보고서 생성

```bash
# Lineage 포함 Markdown 보고서
cmis report-generate \
  --input analysis.json \
  --template structure_analysis \
  --include-lineage \
  --output report.md
```

---

## 🔧 개발

### 테스트

```bash
# 전체 테스트
pytest

# 특정 엔진
pytest dev/tests/unit/test_world_engine*.py
pytest dev/tests/unit/test_strategy_engine*.py
pytest dev/tests/unit/test_learning_engine*.py

# 빠른 확인
pytest -q
```

**현황**: 377/378 passed (99.7%)

### 검증

```bash
# YAML 무결성
python3 dev/validation/validate_yaml_integrity.py

# 코드베이스 검증
python3 dev/validation/validate_codebase.py

# 설정 검증
python3 -m cmis_cli config-validate --check-all
```

---

## 📊 완성도

### 엔진 (8/9) - 89%

| 엔진 | 상태 | 테스트 |
|------|------|--------|
| Evidence Engine v2.2 | ✅ 100% | ✅ |
| Pattern Engine v2.0 | ✅ 100% | 53/53 |
| Value Engine v2.0 | ✅ 100% | ✅ |
| World Engine v2.0 | ✅ 100% | 56/56 |
| Search Strategy v2.0 | ✅ 100% | ✅ |
| Workflow CLI | ✅ 100% | 19/19 |
| Strategy Engine v1.0 | ✅ 100% | 29/29 |
| Learning Engine v1.0 | ✅ 100% | 23/23 |

**완성률**: 89%

---

## 📚 문서

### 아키텍처
- [Architecture Blueprint v3.3](dev/docs/architecture/CMIS_Architecture_Blueprint_v3.3.md) - 전체 시스템 개요
- [Implementation Status v3.3](dev/docs/architecture/CMIS_Implementation_Status_v3.3.md) - 구현 현황
- [Roadmap v3.3](dev/docs/architecture/CMIS_Roadmap_v3.3.md) - 로드맵
- [Philosophy](dev/docs/architecture/cmis_philosophy_concept.md) - 설계 철학

### 엔진별 설계
- [Pattern Engine](dev/docs/architecture/PatternEngine_Design_Final.md)
- [World Engine](dev/docs/architecture/World_Engine_Enhanced_Design.md)
- [Strategy Engine](dev/docs/architecture/StrategyEngine_Design_Enhanced.md)
- [Learning Engine](dev/docs/architecture/LearningEngine_Design_Enhanced.md)
- [Workflow CLI](dev/docs/architecture/Workflow_CLI_Design_Enhanced.md)

### 기타
- [CHANGELOG](CHANGELOG.md) - 변경 이력
- [STRUCTURE](dev/STRUCTURE.md) - 폴더 구조

---

## 🌟 핵심 개념

### Greenfield vs Brownfield

**Greenfield** (시장 전체 관점):
- '나' 없이 neutral한 분석
- 최소 제약 (자본, 시간)
- "이 시장에서 일반적으로 통하는 전략은?"

**Brownfield** (특정 주체 관점):
- '나'(focal_actor) 정의됨
- 전체 제약 (baseline, assets, constraints)
- "우리 회사가 할 수 있는 전략은?"

### Evidence-first

**실행 방식**:
1. Evidence 수집 (KOSIS, DART 등)
2. R-Graph 자동 생성 (seed 불필요)
3. 분석 실행

**장점**:
- 실시간 데이터
- 동적 업데이트
- seed 작성 불필요

---

## 🔑 환경 변수

`.env` 파일 설정:

```bash
# 한국 공공 데이터 API (권장)
DART_API_KEY=your-dart-api-key
KOSIS_API_KEY=your-kosis-api-key
ECOS_API_KEY=your-ecos-api-key

# Google Search (선택)
GOOGLE_API_KEY=your-google-api-key
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id

# LLM (선택)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

---

## 📈 성능

### 테스트 결과
```
377/378 passed (99.7%)
실행 시간: ~80초
```

### 캐싱
- Evidence: 24시간 TTL
- Snapshot: 1시간 TTL
- Result: 1시간 TTL

### 병렬 처리
- batch-analysis: 최대 N개 worker
- Evidence 수집: 병렬 지원

---

## 🛠️ 개발 가이드

### 프로젝트 구조

```
cmis/
├── cmis.yaml              # 메인 스키마
├── cmis_core/             # Core 엔진 (25개 .py)
├── cmis_cli/              # CLI (8개 명령어)
├── config/                # 설정 YAML
│   ├── patterns/          # 23개 Pattern
│   ├── archetypes/        # 6개 Archetype
│   └── sources/           # Data source 설정
├── requirements.txt       # 의존성
└── README.md              # 이 문서

dev/
├── tests/                 # 테스트 (370개)
├── validation/            # 검증 스크립트
├── examples/              # 예시
│   └── seeds/             # Reality seed (테스트용)
├── docs/                  # 문서
└── deprecated/            # 구버전 보관
```

### 새 기능 추가

1. 테스트 작성: `dev/tests/unit/test_*.py`
2. 구현: `cmis_core/*.py`
3. 테스트 실행: `pytest`
4. 문서 업데이트

---

## 🔬 고급 기능

### Python API

```python
from cmis_core.world_engine import WorldEngine
from cmis_core.pattern_engine_v2 import PatternEngineV2
from cmis_core.strategy_engine import StrategyEngine
from cmis_core.learning_engine import LearningEngine

# 1. Evidence → R-Graph
world_engine = WorldEngine()
evidence = evidence_engine.fetch_for_metrics([...])
world_engine.ingest_evidence('Domain', evidence.records)

# 2. 시장 분석
snapshot = world_engine.snapshot('Domain', 'KR')
patterns = pattern_engine.match_patterns(snapshot.graph)
gaps = pattern_engine.discover_gaps(snapshot.graph)

# 3. 전략 생성
strategy_engine = StrategyEngine()
strategies = strategy_engine.search_strategies_core(
    goal, snapshot, patterns, gaps
)

# 4. 학습
learning_engine = LearningEngine()
learning_engine.update_from_outcomes_api(['OUT-001'])
```

### Brownfield 분석

```python
from cmis_core.types import ProjectContext

# 우리 회사 정의
project_context = ProjectContext(
    project_context_id="PRJ-my-company",
    baseline_state={
        "current_revenue": 5000000000,
        "current_customers": 50000
    },
    assets_profile={
        "capability_traits": [
            {"technology_domain": "platform_tech"}
        ]
    },
    constraints_profile={
        "hard_constraints": [
            {"type": "financial", "dimension": "budget", "threshold": 500000000}
        ]
    }
)

# focal_actor 생성
world_engine.ingest_project_context(project_context)

# 우리 회사 관점 분석
snapshot = world_engine.snapshot(
    'Domain', 'KR',
    project_context_id='PRJ-my-company'
)

patterns = pattern_engine.match_patterns(
    snapshot.graph,
    project_context_id='PRJ-my-company'
)
```

---

## 📋 CLI 명령어

### 기본 분석

```bash
# 시장 구조 분석
cmis structure-analysis --domain <DOMAIN> --region <REGION>

# 기회 발굴 (상위 N개)
cmis opportunity-discovery --domain <DOMAIN> --region <REGION> --top-n 5

# 컨텍스트 비교
cmis compare-contexts \
  --context1 "domain:X,region:KR" \
  --context2 "domain:X,region:KR,project_context:PRJ-001"

# Generic workflow
cmis workflow run <workflow_id> \
  --input key=value \
  [--role ROLE] \
  [--policy POLICY]
```

### 고급 기능

```bash
# 일괄 분석 (병렬)
cmis batch-analysis --config batch.yaml --parallel --workers 4

# 보고서 생성 (Lineage 포함)
cmis report-generate \
  --input result.json \
  --template structure_analysis \
  --include-lineage

# 캐시 관리
cmis cache-manage --status
cmis cache-manage --clear --type all

# 설정 검증
cmis config-validate --check-all
```

### 옵션

**모든 워크플로우 공통**:
- `--role ROLE_ID`: role override
- `--policy POLICY_MODE`: policy override (reporting_strict/decision_balanced/exploration_friendly)
- `--dry-run`: 실행 계획만 출력
- `--output FILE`: 결과 저장

---

## 🎓 실무 활용 시나리오

### 시나리오 1: 신규 시장 진입 검토

**상황**: 10억 자본으로 교육 시장 진입

```bash
cmis opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  --budget 1000000000 \
  --top-n 3
```

**결과**:
- 자본 10억 이내 전략
- 예상 ROI, 필요 팀 규모
- 실행 가능성 평가

### 시나리오 2: 우리 회사 전략 수립

**상황**: 기존 사업 확장

```bash
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --project-context PRJ-my-company
```

**결과**:
- focal_actor 중심 시장 구조
- 우리 회사 실행 가능 전략
- 우리 baseline 기준 ROI

### 시나리오 3: 여러 시장 비교

**batch.yaml**:
```yaml
jobs:
  - workflow_id: structure_analysis
    inputs:
      domain_id: Market_A
      region: KR
    output: market_a.json
  
  - workflow_id: structure_analysis
    inputs:
      domain_id: Market_B
      region: KR
    output: market_b.json
```

```bash
cmis batch-analysis --config batch.yaml --parallel
```

---

## 🔍 디버깅

### Dry-run 모드

```bash
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --dry-run
```

**출력**:
```
[DRY RUN MODE]
Workflow: structure_analysis
Domain: Adult_Language_Education_KR
Region: KR
Role: structure_analyst (default)
Policy: reporting_strict (default)

실행 계획:
  1. Load canonical_workflows YAML
  2. Resolve role → policy
  3. Execute workflow steps
  4. Format output
```

### 로그 레벨

```bash
# 상세 로그
cmis structure-analysis --domain ... --verbose

# 에러만
cmis structure-analysis --domain ... --quiet
```

---

## 🤝 Contributing

### 개발 워크플로우

1. Feature branch 생성
2. 코드 작성
3. 테스트 작성 및 실행
4. `pytest` 통과 확인
5. `python3 dev/validation/validate_codebase.py` 실행
6. PR 생성

### 코드 스타일

- Type hints 필수
- Docstring 필수
- Linter 오류 0개 유지

---

## 📖 참고 자료

### 설계 문서
- [Architecture](dev/docs/architecture/) - 13개 설계 문서
- [Analysis](dev/docs/analysis/) - 분석 문서
- [Implementation](dev/docs/implementation/) - 구현 가이드

### 세션 이력
- [Session Summary](dev/session_summary/) - 개발 세션 기록
- 2025-12-11: World, Strategy, Learning Engine 완성

---

## 🐛 알려진 이슈

### Google API 403
- **문제**: IP 주소 제한
- **해결**: Google Cloud Console에서 IP 제한 제거
- **우회**: DuckDuckGo 사용

---

## 🔮 다음 단계

### v4.0: Production 배포 (예정)
- 성능 최적화
- Docker 설정
- 배포 문서
- 사용자 가이드

### v4.1: 고급 기능
- ValueEngine 시뮬레이션
- 고급 최적화 알고리즘
- Rich console 출력

### v5.0: Web UI
- 대시보드
- 인터랙티브 분석
- 시각화

---

## 📜 라이선스

MIT License

---

## 👨‍💻 팀

**CMIS Development Team**

---

## 🎉 주요 성과

- ✅ **CMIS 4단계 루프 완성** (Understand → Discover → Decide → Learn)
- ✅ **89% 완성** (8/9 엔진)
- ✅ **377/378 테스트 통과** (99.7%)
- ✅ **Greenfield/Brownfield 완전 지원**
- ✅ **Production Ready**

---

**CMIS v3.3 - Contextual Market Intelligence System**

**Built with ❤️ for Market Intelligence**

🚀 Ready for Production!

---

**최종 업데이트**: 2025-12-11  
**버전**: v3.3  
**상태**: Production Ready ✅
