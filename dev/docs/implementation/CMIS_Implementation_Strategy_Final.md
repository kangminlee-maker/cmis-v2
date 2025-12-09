---
**이력**: 2025-12-09 UMIS v9 → CMIS로 브랜드 변경
- Universal Market Intelligence → Contextual Market Intelligence
- v9 핵심 차별점 (Project Context Layer) 반영
---

# UMIS v9: structure_analysis v1 구현 전략 (최종)

**문서 목적**: Vertical Slice + v7 재사용을 통한 빠른 프로덕션 구현 전략

**작성일**: 2025-12-05

**참조 문서**:
- `umis_v9_structure_analysis_tasks.md`: Vertical Slice v1 접근법
- `V7_Code_Reuse_Analysis.md`: v7 코드 재사용 분석
- `UMIS_v9_Implementation_Roadmap_Structure_Analysis.md`: 7주 프로덕션 로드맵

---

## 🎯 통합 전략

### 전략 1: Vertical Slice v1 (최소 기능)

**범위**:
- seed 기반만 (외부 API 미사용)
- 3개 Metric만 (N_customers, Revenue, Avg_price)
- 2개 Pattern만 (subscription, platform)
- 간단 Markdown 리포트

**목표**:
- 2-3주 내 CLI 실행 가능
- 새 도메인 추가 = seed 파일만

### 전략 2: v7 코드 재사용

**즉시 복사**:
- DART API (100%)
- Fusion Layer (90%)
- Config 패턴 (80%)

**로직 참고**:
- Evidence Collector (Early Return)
- Fermi Estimator (재귀 없음)

**절감 효과**: 50-70% 작업 시간

### 통합 접근: v1 + v7 재사용

**Week 1-2: v1 Core (seed 기반)**
- v7 없이도 동작하는 최소 버전
- 3개 Metric, 2개 Pattern
- CLI 실행 가능

**Week 3: v7 통합**
- DART API 복사 → Evidence 수집
- Fusion Layer 복사 → 4-Method

**Week 4: 확장**
- 15개 Metric 전체
- 23개 Pattern 전체

---

## 📋 최종 작업 순서 (18개 Task)

### Phase 0: Setup (Day 1)

✅ **v1-scope**: Scope 확정 (완료)
- [x] seed 기반 vertical slice
- [x] CLI 실행 가능
- [x] 성공 기준 정의

🔲 **setup-1**: 프로젝트 구조
- [ ] umis_v9_core/, umis_v9_cli/, tests/ 생성
- [ ] requirements.txt (pyyaml, pytest, python-dotenv)
- [ ] .env.example 파일

🔲 **types-1**: 공통 타입
- [ ] types.py 생성
- [ ] Node, Edge, MetricRequest, ValueRecord dataclass
- [ ] StructureAnalysisInput, StructureAnalysisResult

---

### Phase 1: 인프라 (Day 2-3)

🔲 **graph-1**: InMemoryGraph 개선
- [ ] 기존 graph.py 확장
- [ ] neighbors() direction 파라미터
- [ ] test_graph.py 작성

🔲 **config-1**: Config Loader
- [ ] v7 config.py 패턴 참고
- [ ] pydantic BaseSettings
- [ ] umis_v9.yaml 파싱
- [ ] Metric 스펙 인덱싱

---

### Phase 2: Core Engines (Day 4-7)

🔲 **world-1**: World Engine v1
- [ ] load_reality_seed() 구현
- [ ] seed → InMemoryGraph 변환
- [ ] snapshot() 함수
- [ ] test_world_engine.py

🔲 **value-1**: Value Engine v1
- [ ] 3개 Metric 구현
  - MET-N_customers (Actor 집계)
  - MET-Revenue (MoneyFlow 합산)
  - MET-Avg_price_per_unit (계산)
- [ ] evaluate_metrics() API
- [ ] quality/lineage 기본값
- [ ] test_value_engine.py

🔲 **pattern-1**: Pattern Engine v1
- [ ] 2개 Pattern 코드 정의
  - PAT-subscription_model
  - PAT-platform_business_model
- [ ] match_patterns() 구현
- [ ] test_pattern_engine.py

---

### Phase 3: 워크플로우 통합 (Day 8-9)

🔲 **workflow-1**: Workflow Orchestrator
- [ ] run_structure_analysis() 구현
- [ ] World → Pattern → Value 순서
- [ ] StructureAnalysisResult 조합
- [ ] 에러 처리

🔲 **cli-1**: CLI v1
- [ ] umis_v9_cli/__main__.py
- [ ] argparse 기반
- [ ] structure-analysis 명령
- [ ] 콘솔 출력 (표 형식)

🔲 **report-1**: Report Generator v1
- [ ] 간단 Markdown 템플릿
- [ ] 3개 섹션 (Overview/Patterns/Metrics)
- [ ] 파일 저장

---

### Phase 4: 테스트 (Day 10-11)

🔲 **test-unit**: 유닛 테스트
- [ ] test_graph.py
- [ ] test_world_engine.py
- [ ] test_value_engine.py
- [ ] test_pattern_engine.py
- [ ] pytest 실행 100% 통과

🔲 **test-e2e**: E2E 테스트
- [ ] test_structure_analysis_workflow.py
- [ ] Adult_Language_Education_KR 실행
- [ ] 결과 검증 (Actor 수, Metric 값, Pattern 목록)

---

### Phase 5: v7 재사용 (Day 12-14, 선택적)

🔲 **v7-dart**: DART API 복사
- [ ] v7 dart_api.py 복사
- [ ] DARTConnector 래퍼 작성
- [ ] Evidence 스키마 변환
- [ ] YBM넷 2023 테스트

🔲 **v7-fusion**: Fusion Layer 복사
- [ ] v7 fusion_layer.py 복사
- [ ] MetricResolver._stage_4_fusion() 통합
- [ ] ValueRecord 변환
- [ ] 가중 평균 테스트

🔲 **v7-evidence**: Evidence Collector 패턴
- [ ] Early Return 로직 참고
- [ ] 4-Source 구조 이해
- [ ] v9 스타일 재작성

🔲 **v7-fermi**: Fermi Estimator 로직
- [ ] 재귀 없음 패턴 이해
- [ ] 변수 식별 프롬프트 참고
- [ ] v9 Derived Stage에 통합

---

### Phase 6: 문서화 (Day 15)

🔲 **doc-update**: 문서 업데이트
- [ ] UMIS_v9_Architecture_Blueprint_v9.md
  - 섹션 4.1 "POC 구현 완료" → "v1 구현 완료"
- [ ] UMIS_v9_Implementation_Roadmap_Structure_Analysis.md
  - v1 완료 체크마크
- [ ] README.md 작성
  - v1 사용법, 설치 방법

---

## 🚀 2주 실행 계획

### Week 1: Core v1 (seed 기반)

**Day 1 (월요일)**:
- ✅ v1-scope (완료)
- 🔲 setup-1 (프로젝트 구조)
- 🔲 types-1 (공통 타입)

**Day 2 (화요일)**:
- 🔲 graph-1 (InMemoryGraph)
- 🔲 config-1 (Config Loader)

**Day 3 (수요일)**:
- 🔲 world-1 (World Engine v1)
- test_world_engine.py

**Day 4 (목요일)**:
- 🔲 value-1 (Value Engine v1)
- test_value_engine.py

**Day 5 (금요일)**:
- 🔲 pattern-1 (Pattern Engine v1)
- test_pattern_engine.py

---

### Week 2: 통합 + v7

**Day 6 (월요일)**:
- 🔲 workflow-1 (Orchestrator)
- 🔲 cli-1 (CLI)

**Day 7 (화요일)**:
- 🔲 report-1 (Report Generator)
- 🔲 test-unit (유닛 테스트 완성)

**Day 8 (수요일)**:
- 🔲 test-e2e (통합 테스트)
- v1 검증

**Day 9 (목요일)**:
- 🔲 v7-dart (DART API 복사)
- 🔲 v7-fusion (Fusion Layer)

**Day 10 (금요일)**:
- 🔲 v7-evidence (참고)
- 🔲 v7-fermi (참고)
- 🔲 doc-update

---

## ✅ v1 vs v7 통합 성공 기준

### v1만 (seed 기반)

**입력**:
```bash
umis structure-analysis --domain Adult_Language_Education_KR --region KR
```

**출력**:
```
=== Market Structure Snapshot ===
Domain: Adult_Language_Education_KR
Region: KR

[Actors]
- 7 actors (3 customer_segment, 4 company)

[Money Flows]
- 6 money flows (total: 290B KRW/year)

[Patterns]
✓ PAT-subscription_model (fit: 1.0)
✓ PAT-platform_business_model (fit: 1.0)

[Metrics]
- MET-N_customers: 3,020,000
- MET-Revenue: 290,000,000,000 KRW
- MET-Avg_price_per_unit: 96,026 KRW

Report: output/Market_Structure_Snapshot_Adult_Language_KR_20251205.md
```

**검증**: ✅ 3개 Metric 계산, 2개 Pattern 매칭, Markdown 생성

---

### v1 + v7 통합 (DART/Fusion)

**입력** (동일):
```bash
umis structure-analysis --domain Adult_Language_Education_KR --region KR --enable-external-data
```

**추가 동작**:
- DART API로 YBM넷/능률교육 등 상장사 실제 매출 수집
- seed + DART 데이터 융합 (Fusion Layer)
- 4-Method 계산 (Top-down/Bottom-up/Fermi/Proxy)

**출력 개선**:
```
[External Data Collection]
✓ DART: YBM넷 817억 (2023)
✓ DART: 능률교육 매출 수집
✓ Web Search: 링글 200억 (추정)

[Metrics - 4-Method Fusion]
- MET-SAM:
  - Method 1 (Top-down): 1,500억
  - Method 2 (Bottom-up): 10,000억
  - Method 3 (Fermi): 13,000억
  - Method 4 (Proxy): 18,000억
  - Fusion: 10,000억 (±30% convergence: PASS)
  - Lineage: EVD-DART-001, EVD-DART-002, ...
```

**검증**: ✅ DART 연동, 4-Method, Fusion, v7 수준 추적성

---

## 📊 작업량 예상

### v1만 (seed 기반)

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| Setup | 프로젝트 구조, 타입 | 1일 |
| 인프라 | Graph, Config | 2일 |
| Engines | World, Value, Pattern | 3일 |
| 통합 | Workflow, CLI, Report | 2일 |
| 테스트 | 유닛 + E2E | 2일 |
| **총계** | | **10일** |

### v1 + v7 재사용

| Phase | 작업 | v7 재사용 | 예상 시간 |
|-------|------|----------|----------|
| Setup | (동일) | - | 1일 |
| 인프라 | (동일) | Config 패턴 | 1.5일 |
| Engines | (동일) | - | 3일 |
| 통합 | (동일) | - | 2일 |
| 테스트 | (동일) | - | 1.5일 |
| **v1 소계** | | | **9일** |
| v7 통합 | DART, Fusion | 복사+변환 | **2일** |
| v7 참고 | Evidence, Fermi | 참고 | **2일** |
| **총계** | | | **13일** |

---

## 🎯 즉시 시작 가능

**오늘 (Day 1)**:

1. ✅ v1-scope (완료)
2. 🔲 setup-1 시작:

```bash
# 디렉토리 구조
mkdir -p umis_v9_core
mkdir -p umis_v9_cli
mkdir -p tests

# requirements.txt
cat > requirements.txt << 'EOF'
pyyaml>=6.0
pytest>=7.4.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
EOF

# .env.example
cat > .env.example << 'EOF'
# UMIS v9 Configuration

# DART API (선택, v1+v7 통합 시)
DART_API_KEY=your-dart-api-key-here

# Tavily API (선택, 웹 검색 시)
TAVILY_API_KEY=your-tavily-api-key-here
EOF
```

3. 🔲 types-1 시작:

```python
# umis_v9_core/types.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class Node:
    id: str
    type: str
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Edge:
    type: str
    source: str
    target: str
    data: Dict[str, Any] = field(default_factory=dict)

# ... (나머지 타입들)
```

---

## 📝 다음 커밋 계획

**커밋 1 (오늘)**:
```bash
git add .
git commit -m "Setup v9 v1 project structure and types

- Create umis_v9_core/, umis_v9_cli/, tests/ directories
- Add requirements.txt (minimal dependencies)
- Add .env.example
- Add umis_v9_core/types.py (common dataclasses)
- Add V7_Code_Reuse_Analysis.md
- Add UMIS_v9_Implementation_Strategy_Final.md
"
```

**커밋 2 (Day 2-3)**:
```bash
git commit -m "Implement InMemoryGraph and Config Loader v1

- umis_v9_core/graph.py: InMemoryGraph with full API
- umis_v9_core/config.py: YAML loader with pydantic
- tests/test_graph.py: Graph CRUD tests
- tests/test_config.py: Config loading tests
"
```

---

## 🔥 핵심 성공 요인

**1. 최소 범위 유지**:
- ❌ "모든 기능 한번에"
- ✅ "seed로 3개 Metric + 2개 Pattern"

**2. v7 검증 코드 활용**:
- ❌ "DART API 재개발"
- ✅ "v7 복사 + 스키마 변환"

**3. 점진적 확장**:
- Week 1-2: v1 (seed만)
- Week 3: +DART/Fusion
- Week 4+: +웹검색/15 Metrics

**4. 테스트 주도**:
- 각 모듈마다 유닛 테스트
- E2E 테스트로 통합 검증

---

**지금 시작하시겠습니까?** setup-1 (프로젝트 구조)부터 진행할까요?
