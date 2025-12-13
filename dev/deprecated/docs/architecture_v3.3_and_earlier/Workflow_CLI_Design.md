# Workflow CLI 설계 문서

**작성일**: 2025-12-11
**버전**: v1.0
**상태**: 설계 완료

---

## 1. 설계 철학

### 1.1 핵심 원칙

**사용자 중심 설계**:
- 최소 타이핑으로 최대 효과
- 직관적인 명령어 구조
- 풍부한 출력 및 피드백
- 에러 메시지 명확성

**CMIS 철학 준수**:
- Model-first, Number-second
- Evidence-first, Prior-last
- 모든 답 = (세계, 변화, 결과, 논증 구조)
- Monotonic Improvability

**워크플로우 우선**:
- CLI는 단순 도구가 아닌 워크플로우 실행기
- 각 명령어는 완결된 분석 프로세스
- 중간 결과 재사용 가능
- 배치 처리 지원

---

## 2. 현재 상태 분석

### 2.1 구현 완료 항목

**WorkflowOrchestrator**:
- `run_structure_analysis()` - 구조 분석 워크플로우
- 3-Step: World Engine → Pattern Engine → Value Engine

**CLI**:
- `cmis structure-analysis` 명령
- 기본 출력 포맷팅
- JSON 저장 옵션

### 2.2 미구현 워크플로우

**cmis.yaml 정의 (4개)**:
1. ✅ `structure_analysis` - 구현 완료
2. ❌ `opportunity_discovery` - 미구현
3. ❌ `strategy_design` - 미구현 (StrategyEngine 필요)
4. ❌ `reality_monitoring` - 미구현 (LearningEngine 필요)

---

## 3. Workflow CLI 아키텍처

### 3.1 전체 구조

```
┌─────────────────────────────────────────────────────────┐
│                     CMIS CLI                             │
│  (cmis <workflow> --<options>)                          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Command Parser & Validator                  │
│  - Argument parsing                                      │
│  - Input validation                                      │
│  - Config loading                                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│            WorkflowOrchestrator                          │
│  - run_structure_analysis()                              │
│  - run_opportunity_discovery()                           │
│  - run_strategy_design()                                 │
│  - run_reality_monitoring()                              │
│  - run_custom_workflow()                                 │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │ World   │      │ Pattern │      │ Value   │
   │ Engine  │      │ Engine  │      │ Engine  │
   └─────────┘      └─────────┘      └─────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│               Output Formatter                           │
│  - Console (rich text)                                   │
│  - JSON                                                  │
│  - Markdown report                                       │
│  - CSV (metrics only)                                    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 계층 구조

**Layer 1: CLI Interface** (`cmis_cli/`)
- 명령어 파싱
- 사용자 입력 검증
- 출력 포맷팅

**Layer 2: Workflow Orchestration** (`cmis_core/workflow.py`)
- 워크플로우 실행 로직
- 엔진 간 데이터 전달
- 에러 핸들링

**Layer 3: Engine Layer** (`cmis_core/`)
- World Engine
- Pattern Engine
- Value Engine
- Strategy Engine (미래)
- Learning Engine (미래)

**Layer 4: Data Layer** (`cmis_core/types.py`, stores)
- 데이터 모델
- 캐시
- 영속성

---

## 4. 워크플로우 명령어 설계

### 4.1 structure-analysis (이미 구현)

**목적**: 시장/비즈니스 구조 분석

**명령어**:
```bash
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  [--segment office_worker] \
  [--as-of 2025-12-05] \
  [--project-context PRJ-001] \
  [--output report.json] \
  [--format json|markdown|console]
```

**출력**:
- R-Graph 구조 요약
- 감지된 패턴 (structure_fit_score)
- 핵심 Metrics (N_customers, Revenue 등)

**프로세스**:
1. World Engine: snapshot()
2. Pattern Engine: match_patterns()
3. Value Engine: evaluate_metrics()

---

### 4.2 opportunity-discovery (신규)

**목적**: 기회 발굴 및 Gap 분석

**명령어**:
```bash
cmis opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  [--project-context PRJ-001] \
  [--output opportunities.json] \
  [--format json|markdown|console] \
  [--top-n 5]
```

**출력**:
- 현재 매칭된 패턴
- 누락된 패턴 (Gap)
- Feasibility 평가
- 기회 우선순위 (expected_level × feasibility)
- Rough sizing (ValueEngine Prior 활용)

**프로세스**:
1. World Engine: snapshot()
2. Pattern Engine: match_patterns()
3. Pattern Engine: discover_gaps()
4. Value Engine: evaluate_metrics() (Gap별 Benchmark)
5. 정렬 및 우선순위화

**옵션**:
- `--top-n N`: 상위 N개 기회만 출력
- `--min-feasibility high|medium`: 최소 feasibility 필터
- `--include-matched`: 매칭된 패턴도 포함

---

### 4.3 compare-scenarios (신규)

**목적**: 여러 시나리오 비교 (Greenfield vs Brownfield, 시점 비교 등)

**명령어**:
```bash
cmis compare-scenarios \
  --scenario1 "domain:Adult_Language_Education_KR,region:KR" \
  --scenario2 "domain:Adult_Language_Education_KR,region:KR,project_context:PRJ-001" \
  [--output comparison.json] \
  [--format table|json|markdown]
```

**출력**:
- 시나리오별 패턴 매칭 비교
- Metrics 비교 (side-by-side)
- Gap 차이
- 의사결정 지원 요약

**프로세스**:
1. 각 시나리오에 대해 structure_analysis 실행
2. 결과 비교 테이블 생성
3. 차이점 하이라이트

---

### 4.4 batch-analysis (신규)

**목적**: 여러 도메인/지역 일괄 분석

**명령어**:
```bash
cmis batch-analysis \
  --config batch_config.yaml \
  [--output-dir ./results] \
  [--parallel] \
  [--workers 4]
```

**batch_config.yaml**:
```yaml
jobs:
  - workflow: structure_analysis
    params:
      domain: Adult_Language_Education_KR
      region: KR
    output: adult_lang_kr.json
  
  - workflow: opportunity_discovery
    params:
      domain: Online_Tutoring_KR
      region: KR
    output: online_tutoring_kr.json
```

**출력**:
- 각 작업별 결과 파일
- 배치 실행 요약
- 에러 로그

**프로세스**:
1. Config 파일 파싱
2. 작업 큐 생성
3. 병렬 실행 (선택적)
4. 결과 집계

---

### 4.5 report-generate (신규)

**목적**: 분석 결과를 보고서로 변환

**명령어**:
```bash
cmis report-generate \
  --input analysis_result.json \
  --template structure_analysis \
  [--output report.md] \
  [--format markdown|html|pdf]
```

**템플릿**:
- `structure_analysis`: 구조 분석 보고서
- `opportunity_discovery`: 기회 발굴 보고서
- `executive_summary`: 임원 요약 보고서

**출력**:
- Markdown/HTML/PDF 보고서
- 차트 포함 (선택적)
- Executive Summary

**프로세스**:
1. JSON 결과 로딩
2. 템플릿 적용
3. 보고서 생성

---

### 4.6 cache-manage (신규)

**목적**: Evidence/결과 캐시 관리

**명령어**:
```bash
# 캐시 상태 확인
cmis cache-manage --status

# 캐시 클리어
cmis cache-manage --clear [--type evidence|results|all]

# 캐시 통계
cmis cache-manage --stats
```

**출력**:
- 캐시 크기, 항목 수
- Hit rate
- 오래된 항목 정보

---

### 4.7 config-validate (신규)

**목적**: YAML 설정 검증

**명령어**:
```bash
cmis config-validate \
  [--file cmis.yaml] \
  [--check-seeds] \
  [--check-patterns] \
  [--check-metrics]
```

**출력**:
- 검증 결과 (PASS/FAIL)
- 에러 상세 정보
- 경고 사항

---

## 5. 공통 옵션 설계

### 5.1 모든 워크플로우 공통 옵션

```bash
--verbose, -v          # 상세 로그 출력
--quiet, -q            # 최소 출력만
--dry-run              # 실제 실행 없이 계획만 출력
--config FILE          # 커스텀 설정 파일
--log-level LEVEL      # 로그 레벨 (DEBUG|INFO|WARNING|ERROR)
--log-file FILE        # 로그 파일 저장
--no-cache             # 캐시 사용 안 함
--cache-ttl SECONDS    # 캐시 유효 시간
```

### 5.2 출력 포맷 옵션

```bash
--format FORMAT        # 출력 형식 (console|json|markdown|yaml)
--output FILE          # 출력 파일 경로
--pretty               # JSON/YAML 정렬 출력
--color / --no-color   # 컬러 출력 on/off
```

### 5.3 성능 옵션

```bash
--parallel             # 병렬 실행 활성화
--workers N            # 병렬 작업 수
--timeout SECONDS      # 타임아웃 설정
--memory-limit MB      # 메모리 제한
```

---

## 6. 출력 포맷 설계

### 6.1 Console 출력 (기본)

**특징**:
- Rich text formatting (색상, 굵기, 밑줄)
- 진행 바
- 표 형식
- 이모지 사용

**예시**:
```
╭─────────────────────────────────────────╮
│   CMIS - Structure Analysis             │
╰─────────────────────────────────────────╯

[1/3] Loading R-Graph snapshot... ✓
   → 12 actors, 8 money flows

[2/3] Matching patterns... ✓
   → 3 patterns matched

[3/3] Calculating metrics... ✓
   → 5 metrics calculated

╭─────────────────────────────────────────╮
│   결과                                   │
╰─────────────────────────────────────────╯

📊 R-Graph 구조
  • Actors:      12개
  • Money Flows: 8개
  • States:      0개

🔍 감지된 패턴
  ✓ PAT-subscription_model
    구독형 비즈니스 모델
    적합도: 0.85

  ✓ PAT-asset_light_model
    자산 경량화 모델
    적합도: 0.72

💰 핵심 Metric
  • MET-N_customers:       15만
  • MET-Revenue:           120억
  • MET-Avg_price_per_unit: 8,000원

⏱️  실행 시간: 1.23초
```

### 6.2 JSON 출력

**구조**:
```json
{
  "meta": {
    "workflow": "structure_analysis",
    "version": "1.0",
    "timestamp": "2025-12-11T12:00:00Z",
    "execution_time": 1.23,
    "domain_id": "Adult_Language_Education_KR",
    "region": "KR"
  },
  "graph_overview": {
    "num_actors": 12,
    "num_money_flows": 8,
    "actor_types": {
      "company": 3,
      "customer_segment": 9
    }
  },
  "pattern_matches": [
    {
      "pattern_id": "PAT-subscription_model",
      "description": "구독형 비즈니스 모델",
      "structure_fit_score": 0.85,
      "execution_fit_score": null,
      "combined_score": 0.85
    }
  ],
  "metrics": [
    {
      "metric_id": "MET-N_customers",
      "point_estimate": 150000,
      "quality": {"status": "ok"}
    }
  ]
}
```

### 6.3 Markdown 보고서

**구조**:
```markdown
# Structure Analysis Report

**도메인**: Adult_Language_Education_KR
**지역**: KR
**분석 일시**: 2025-12-11 12:00:00

## Executive Summary

이 시장은 **구독형 비즈니스 모델**과 **자산 경량화** 특징을 보입니다.

## R-Graph 구조

- **Actors**: 12개
- **Money Flows**: 8개

### Actor 분포

| 종류 | 개수 |
|------|------|
| 회사 | 3개 |
| 고객 세그먼트 | 9개 |

## 감지된 패턴

### 1. PAT-subscription_model (적합도: 0.85)

구독형 비즈니스 모델

...
```

### 6.4 CSV 출력 (Metrics만)

```csv
metric_id,value,unit,quality_status
MET-N_customers,150000,count,ok
MET-Revenue,12000000000,KRW,ok
MET-Avg_price_per_unit,8000,KRW,ok
```

---

## 7. 에러 처리 전략

### 7.1 에러 계층

**1. User Input Error** (4xx 스타일)
- 잘못된 인자
- 필수 인자 누락
- 존재하지 않는 도메인

**처리**:
```
❌ 에러: 존재하지 않는 도메인 'Invalid_Domain'

사용 가능한 도메인:
  • Adult_Language_Education_KR
  • Online_Tutoring_KR

도움말: cmis list-domains
```

**2. System Error** (5xx 스타일)
- Engine 실행 실패
- API 호출 실패
- 메모리 부족

**처리**:
```
❌ 시스템 에러: Pattern Engine 실행 실패

상세:
  File: pattern_engine.py:123
  Error: IndexError: list index out of range

해결 방법:
  1. --verbose 옵션으로 상세 로그 확인
  2. GitHub 이슈 등록
  3. 로그 파일: /tmp/cmis_error_20251211.log
```

**3. Timeout Error**
```
⏱️  타임아웃: Evidence 수집이 30초를 초과했습니다

진행 상황:
  ✓ KOSIS API 완료
  ✓ ECOS API 완료
  ⏳ Google Search 진행 중 (응답 대기)

해결 방법:
  • --timeout 60 으로 시간 연장
  • --no-cache 옵션 시도
```

### 7.2 Graceful Degradation

**일부 실패 허용**:
- Evidence 일부 실패 → 나머지로 진행
- Pattern 일부 실패 → 나머지 패턴 계속
- Metric 일부 실패 → "N/A" 표시

**예시**:
```
⚠️  경고: 일부 Metric 계산 실패

성공: 3/5
실패:
  • MET-Market_size: Evidence 부족
  • MET-CAC: 공식 미구현

결과는 부분적입니다. 계속하시겠습니까? [Y/n]
```

---

## 8. 구현 계획

### 8.1 Phase 1: Core Infrastructure (1주)

**목표**: 기본 CLI 프레임워크 완성

**작업**:
1. CLI 구조 개선
   - `cmis_cli/commands/` 폴더 생성
   - 명령어별 모듈 분리
   - 공통 옵션 처리기

2. 출력 포맷터 구현
   - `cmis_cli/formatters/`
   - ConsoleFormatter (rich 라이브러리)
   - JSONFormatter
   - MarkdownFormatter

3. WorkflowOrchestrator 확장
   - 공통 로직 추상화
   - 에러 핸들링 개선
   - 진행 상황 콜백

**파일**:
```
cmis_cli/
├── __init__.py
├── __main__.py
├── commands/
│   ├── __init__.py
│   ├── structure_analysis.py
│   ├── opportunity_discovery.py
│   ├── batch_analysis.py
│   ├── report_generate.py
│   └── cache_manage.py
├── formatters/
│   ├── __init__.py
│   ├── console.py
│   ├── json.py
│   ├── markdown.py
│   └── csv.py
└── utils/
    ├── __init__.py
    ├── validators.py
    └── error_handlers.py
```

---

### 8.2 Phase 2: Workflow Implementation (1주)

**목표**: 주요 워크플로우 구현

**작업**:
1. `opportunity_discovery` 워크플로우
   - WorkflowOrchestrator.run_opportunity_discovery()
   - CLI 명령어 추가
   - 출력 포맷 정의

2. `compare_scenarios` 워크플로우
   - 시나리오 비교 로직
   - 테이블 출력

3. `batch_analysis` 워크플로우
   - YAML config 파서
   - 병렬 실행 (concurrent.futures)
   - 진행 바

**테스트**: 10개

---

### 8.3 Phase 3: Advanced Features (1주)

**목표**: 고급 기능 추가

**작업**:
1. 보고서 생성 시스템
   - Markdown 템플릿
   - HTML 변환 (markdown2)
   - 차트 생성 (matplotlib, optional)

2. 캐시 관리 기능
   - 캐시 상태 조회
   - 클리어 기능
   - 통계

3. Config 검증 도구
   - YAML 구조 검증
   - Pattern/Metric 존재 확인

**테스트**: 8개

---

### 8.4 Phase 4: Polish & Documentation (3일)

**목표**: 완성도 및 문서화

**작업**:
1. 에러 메시지 개선
2. Help 문구 작성
3. 사용 예시 문서
4. 통합 테스트

---

## 9. 기술 스택

### 9.1 필수 라이브러리

```python
# CLI 프레임워크
argparse          # 표준 라이브러리 (충분함)

# 출력 포맷팅
rich              # 터미널 rich text (테이블, 진행바, 색상)

# 보고서 생성
markdown2         # Markdown → HTML
jinja2           # 템플릿 엔진

# 병렬 처리
concurrent.futures  # 표준 라이브러리

# 유틸리티
pyyaml           # 이미 사용 중
```

### 9.2 선택적 라이브러리

```python
# 차트 생성 (선택)
matplotlib       # 시각화
plotly           # 인터랙티브 차트

# PDF 생성 (선택)
weasyprint       # HTML → PDF
```

---

## 10. 사용 예시

### 10.1 기본 분석

```bash
# 구조 분석
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR

# 기회 발굴
cmis opportunity-discovery \
  --domain Adult_Language_Education_KR \
  --region KR \
  --top-n 3
```

### 10.2 Brownfield 분석

```bash
# Project Context 포함
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --project-context PRJ-my-company
```

### 10.3 시나리오 비교

```bash
# Greenfield vs Brownfield
cmis compare-scenarios \
  --scenario1 "domain:Adult_Language_Education_KR,region:KR" \
  --scenario2 "domain:Adult_Language_Education_KR,region:KR,project_context:PRJ-001"
```

### 10.4 배치 분석

```bash
# 여러 시장 동시 분석
cmis batch-analysis \
  --config markets_2025.yaml \
  --parallel \
  --workers 4
```

### 10.5 보고서 생성

```bash
# 분석 → 보고서
cmis structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --output analysis.json

cmis report-generate \
  --input analysis.json \
  --template structure_analysis \
  --format markdown \
  --output report.md
```

---

## 11. 성능 고려사항

### 11.1 캐싱 전략

**Evidence 캐시**:
- TTL: 24시간 (설정 가능)
- 키: (source, metric, context) hash
- Backend: SQLite (기존)

**결과 캐시**:
- TTL: 1시간
- 키: (workflow, params) hash
- Backend: 파일 시스템

### 11.2 병렬 처리

**배치 분석**:
- concurrent.futures.ProcessPoolExecutor
- 각 작업은 독립적
- CPU 코어 수만큼 병렬 실행

**Evidence 수집**:
- 이미 구현됨 (evidence_parallel.py)

### 11.3 메모리 관리

**대용량 배치**:
- 스트리밍 처리
- 결과 즉시 디스크 저장
- 메모리 제한 옵션

---

## 12. 테스트 전략

### 12.1 단위 테스트

**대상**:
- 각 명령어 로직
- Formatter 클래스
- Validator 함수

**예시**:
```python
def test_structure_analysis_command():
    args = parse_args(['structure-analysis', '--domain', 'test', '--region', 'KR'])
    result = cmd_structure_analysis(args)
    assert result.meta['domain_id'] == 'test'
```

### 12.2 통합 테스트

**시나리오**:
- 전체 워크플로우 실행
- 출력 파일 생성 확인
- 에러 케이스 처리

### 12.3 E2E 테스트

**실제 명령어 실행**:
```bash
# CLI 실행 테스트
python -m cmis_cli structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --output /tmp/test_output.json

# 결과 검증
python -c "import json; result = json.load(open('/tmp/test_output.json')); assert len(result['pattern_matches']) > 0"
```

---

## 13. 문서화 계획

### 13.1 README.md 업데이트

**추가 섹션**:
- CLI 사용법
- 명령어 레퍼런스
- 예시 모음

### 13.2 CLI Help

**각 명령어마다**:
```bash
cmis structure-analysis --help
```

**출력**:
```
usage: cmis structure-analysis [options]

시장/비즈니스 구조를 분석합니다.

options:
  --domain DOMAIN       도메인 ID (필수)
  --region REGION       지역 코드 (필수)
  --segment SEGMENT     고객 세그먼트 (선택)
  --output FILE         결과 저장 경로 (선택)

예시:
  cmis structure-analysis --domain Adult_Language_Education_KR --region KR
```

### 13.3 사용 가이드

**dev/docs/user_guide/CLI_Guide.md**:
- 설치 및 설정
- 기본 사용법
- 고급 기능
- 트러블슈팅

---

## 14. 다음 단계

### 우선순위 1: Core Infrastructure (즉시)

**작업**:
- CLI 구조 개선
- 출력 포맷터 구현
- opportunity_discovery 워크플로우

**예상 시간**: 1주

### 우선순위 2: Advanced Workflows (중기)

**작업**:
- batch_analysis
- compare_scenarios
- report_generate

**예상 시간**: 1주

### 우선순위 3: Polish (장기)

**작업**:
- 문서화 완성
- 에러 메시지 개선
- 성능 최적화

**예상 시간**: 3일

---

**작성**: 2025-12-11
**상태**: 설계 완료
**다음**: Phase 1 구현 착수

