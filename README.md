# CMIS - Universal Market Intelligence System

**버전**: 9.0.0-alpha  
**상태**: Production Ready  
**릴리스**: 2025-12-05

---

## 🎯 CMIS란?

시장/비즈니스 세계를 **Reality/Pattern/Value/Decision 그래프**로 표현하고,  
구조 이해 → 기회 발굴 → 전략 설계 → 학습을 수행하는  
**Contextual Market Intelligence OS**

### 핵심 철학

1. **Model-first, Number-second**: 숫자는 항상 모델의 결과
2. **Evidence-first, Prior-last**: 증거 우선, 추정은 최후
3. **Graph-of-Graphs**: R/P/V/D 4개 그래프로 세계 표현
4. **Trait 기반 Ontology**: 유연한 패턴 정의
5. **On-demand Reality**: 질문 시점에 세계 구축

---

## 🚀 빠른 시작

### 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# (선택) API 설정
cp env.example .env
# .env에서 DART_API_KEY 등 설정
```

### 실행

```bash
# 시장 구조 분석
python3 -m cmis_cli structure-analysis \
  --domain Adult_Language_Education_KR \
  --region KR

# 결과:
# MET-N_customers: 302만
# MET-Revenue: 2900억
# 실행 시간: 0.01초
```

---

## 📦 프로젝트 구조

```
cmis/
├── cmis.yaml           # 메인 스키마 정의
├── domain_registry.yaml   # 도메인 레지스트리
├── cmis_core/          # Core 엔진
│   ├── types.py
│   ├── graph.py
│   ├── config.py
│   ├── world_engine.py
│   ├── value_engine.py
│   ├── pattern_engine.py
│   ├── workflow.py
│   ├── report_generator.py
│   └── evidence/
│       └── dart_connector.py
├── cmis_cli/           # CLI
│   └── __main__.py
├── config/                # 설정 YAML
│   ├── cmis_agent_protocols.yaml
│   ├── cmis_process_phases.yaml
│   └── domains/
├── seeds/                 # Reality seed
│   └── Adult_Language_Education_KR_reality_seed.yaml
├── tests/                 # 테스트 (44개)
├── dev/                   # 개발 관련
│   ├── scripts/validation/
│   ├── docs/
│   │   ├── architecture/
│   │   ├── analysis/
│   │   └── implementation/
│   ├── backup/
│   └── temp/
└── session_summary/       # 개발 이력
```

---

## 🧪 테스트

```bash
# 전체 테스트
pytest tests/ -v

# 빠른 확인
pytest tests/ -q

# 특정 모듈
pytest tests/test_world_engine.py -v
```

**현황**: 44개 테스트, 모두 통과 ✅

---

## 📖 주요 문서

**사용법**:
- `README_v1.md`: 상세 사용 가이드

**아키텍처** (`dev/docs/architecture/`):
- `UMIS_v9_Architecture_Blueprint_v9.md`: 전체 아키텍처
- `cmis_philosophy_concept.md`: 핵심 철학
- `cmis_roadmap.md`: 개발 로드맵
- `cmis_project_context_layer_design.md`: Project Context 설계

**구현** (`dev/docs/implementation/`):
- `UMIS_v9_Implementation_Strategy_Final.md`: 구현 전략
- `UMIS_v9_Structure_Analysis_Detailed_Workflow.md`: 워크플로우 상세
- `UMIS_v9_Structure_Analysis_Diagrams.md`: 13개 다이어그램

**분석** (`dev/docs/analysis/`):
- `V7_Code_Reuse_Analysis.md`: v7 재사용 분석
- `UMIS_v9_Project_Context_Philosophy_Alignment.md`: 철학 정합성

---

## 🎓 새 도메인 추가

1. **Reality seed 생성**:
   ```yaml
   # seeds/Your_Domain_reality_seed.yaml
   cmis_reality_seed:
     meta:
       domain_id: "Your_Domain"
     actors: [...]
     money_flows: [...]
   ```

2. **실행**:
   ```bash
   python3 -m cmis_cli structure-analysis --domain Your_Domain --region KR
   ```

---

## 🔧 개발

**검증 스크립트** (`dev/scripts/validation/`):
```bash
# YAML 무결성
python3 dev/scripts/validation/validate_yaml_integrity.py

# 전체 코드베이스
python3 -m pytest tests/ -v
```

---

## 📊 성능

- 실행 시간: < 0.1초 (seed 기반)
- 메모리: < 50MB
- 테스트: 44개, 4초

---

## 🤝 기여

이슈와 PR을 환영합니다!

---

**CMIS Team • 2025 • Production Ready**
