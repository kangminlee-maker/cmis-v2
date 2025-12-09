# UMIS v9 - v1 Release

**버전**: 9.0.0-alpha-v1  
**릴리스**: 2025-12-05  
**상태**: Production Ready (seed 기반)

---

## 🎯 v1이란?

UMIS v9의 **첫 번째 작동 버전**으로, `structure_analysis` 워크플로우를 **최소 vertical slice**로 구현했습니다.

**핵심 기능**:
- ✅ Reality seed → R-Graph 구축
- ✅ Pattern 매칭 (2개: subscription, platform)
- ✅ Metric 계산 (3개: N_customers, Revenue, Avg_price)
- ✅ CLI 실행 가능
- ✅ Markdown 리포트 생성

---

## 🚀 빠른 시작

### 1. 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# (선택) DART API 설정
cp env.example .env
# .env에서 DART_API_KEY 설정
```

### 2. 실행

```bash
# CLI로 구조 분석
python3 -m umis_v9_cli structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR

# JSON 출력
python3 -m umis_v9_cli structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --output output/result.json
```

### 3. 결과 예시

```
[핵심 Metric]
  MET-N_customers: 302만
  MET-Revenue: 2900억
  MET-Avg_price_per_unit: 10만

실행 시간: 0.01초
```

---

## 📦 구현 현황

### ✅ 완료 (v1)

**Core Engines**:
- ✅ World Engine (Reality seed → R-Graph)
- ✅ Pattern Engine (2개 패턴 매칭)
- ✅ Value Engine (3개 Metric 계산 + Fusion 로직)
- ✅ Config Loader (umis_v9.yaml 파싱)

**Workflow**:
- ✅ Workflow Orchestrator (World→Pattern→Value)
- ✅ CLI (structure-analysis 명령)
- ✅ Report Generator (Markdown 3개 섹션)

**Testing**:
- ✅ 42개 테스트 모두 통과
- ✅ E2E 통합 테스트

**v7 통합**:
- ✅ DART API (검증된 로직)
- ✅ Fusion 알고리즘 (가중 평균/범위 교집합)

### 🔲 v2 예정

- Evidence Engine (외부 데이터 자동 수집)
- 36개 Metric 전체
- 23개 Pattern 전체
- Project Context (Brownfield 지원)
- PH00-PH14 전체 Phase

---

## 📁 파일 구조

```
umis_v9_core/
  ├── types.py          # 공통 타입
  ├── graph.py          # InMemoryGraph
  ├── config.py         # Config Loader
  ├── world_engine.py   # World Engine
  ├── value_engine.py   # Value Engine (+ Fusion)
  ├── pattern_engine.py # Pattern Engine
  ├── workflow.py       # Orchestrator
  ├── report_generator.py
  └── evidence/
      ├── __init__.py
      └── dart_connector.py  # DART API

umis_v9_cli/
  ├── __init__.py
  └── __main__.py       # CLI

tests/
  ├── test_graph.py (7개)
  ├── test_config.py (5개)
  ├── test_world_engine.py (5개)
  ├── test_value_engine.py (7개)
  ├── test_pattern_engine.py (5개)
  ├── test_workflow.py (4개)
  ├── test_report_generator.py (2개)
  ├── test_e2e_structure_analysis.py (4개)
  └── test_dart_connector.py (3개)
```

---

## 🧪 테스트

```bash
# 전체 테스트
pytest tests/ -v

# 특정 모듈
pytest tests/test_world_engine.py -v

# E2E만
pytest tests/test_e2e_structure_analysis.py -v
```

**현황**: 42개 테스트, 모두 통과 ✅

---

## 📖 사용법

### Python API

```python
from umis_v9_core.workflow import run_structure_analysis

result = run_structure_analysis(
    domain_id="Adult_Language_Education_KR",
    region="KR"
)

print(f"Actors: {result.graph_overview['num_actors']}")
print(f"Patterns: {len(result.pattern_matches)}")
print(f"Metrics: {len(result.metrics)}")
```

### CLI

```bash
# 기본 실행
python3 -m umis_v9_cli structure-analysis --domain Adult_Language_Education_KR --region KR

# JSON 출력
python3 -m umis_v9_cli structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --output output/result.json

# 세그먼트 지정
python3 -m umis_v9_cli structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR \
  --segment office_worker
```

---

## 🎓 새 도메인 추가

1. Reality seed 생성:
   ```yaml
   # seeds/Your_Domain_ID_reality_seed.yaml
   ---
   umis_v9_reality_seed:
     meta:
       domain_id: "Your_Domain_ID"
       as_of: "2025-12-05"
     
     actors:
       - actor_id: "ACT-001"
         kind: "company"
         name: "Example Co"
     
     money_flows:
       - money_flow_id: "MFL-001"
         payer_id: "ACT-001"
         payee_id: "ACT-002"
         quantity: {amount: 1000000000, currency: "KRW", per: "year"}
   ```

2. domain_registry.yaml에 등록:
   ```yaml
   domains:
     - domain_id: "Your_Domain_ID"
       config_file: "umis_v9_domain_Your_Domain.yaml"
       status: "active"
   ```

3. 실행:
   ```bash
   python3 -m umis_v9_cli structure-analysis --domain Your_Domain_ID --region KR
   ```

---

## 📊 성능

**v1 (seed 기반)**:
- 실행 시간: < 0.1초
- 메모리: < 50MB
- 의존성: 최소 (pyyaml, pytest, pydantic)

**v2 예상 (외부 데이터)**:
- 실행 시간: 30초 ~ 2분
- DART API: 3-5초/회사
- 웹 검색: 5-10초/쿼리

---

## 🔗 참조 문서

- `umis_v9.yaml`: 전체 스키마 (1,767줄)
- `umis_v9_philosophy_concept.md`: v9 철학
- `UMIS_v9_Architecture_Blueprint_v9.md`: 아키텍처
- `UMIS_v9_Implementation_Strategy_Final.md`: 구현 전략
- `V7_Code_Reuse_Analysis.md`: v7 재사용 분석

---

**UMIS v9 Team • 2025-12-05 • v1 Release**
