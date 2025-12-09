# CMIS - Contextual Market Intelligence System

**버전**: 9.0.0-alpha  
**상태**: Production Ready  
**릴리스**: 2025-12-09

> **"시장과 사용자 상황을 함께 이해하는 인텔리전스"**

---

## 🎯 CMIS란?

시장/비즈니스 세계를 **Reality/Pattern/Value/Decision 그래프**로 표현하고,  
**사용자 상황(Project Context)**을 함께 고려하여  
구조 이해 → 기회 발굴 → 전략 설계 → 학습을 수행하는  
**Contextual Market Intelligence OS**

### 핵심 철학

1. **Model-first, Number-second**: 숫자는 항상 모델의 결과
2. **Evidence-first, Prior-last**: 증거 우선, 추정은 최후
3. **Graph-of-Graphs**: R/P/V/D 4개 그래프로 세계 표현
4. **Trait 기반 Ontology**: 유연한 패턴 정의
5. **Contextual**: 시장 + 사용자 상황 통합 이해

---

## 🚀 빠른 시작

### 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# (선택) API 설정
cp env.example .env
# .env에서 DART_API_KEY, GOOGLE_API_KEY 등 설정
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

**프로덕션** (루트):
```
cmis/
├── cmis.yaml              # 메인 스키마
├── domain_registry.yaml   # 도메인 레지스트리
├── cmis_core/             # Core 엔진 (8개)
├── cmis_cli/              # CLI
├── config/                # 설정 YAML
├── seeds/                 # Reality seed
├── requirements.txt
└── README.md
```

**개발** (dev/):
```
dev/
├── scripts/
│   ├── validation/        # 검증 스크립트
│   └── tests/             # 테스트 (44개)
├── examples/              # 예시 (Project Context 등)
├── reference/             # v7 참조 자료
├── docs/
│   ├── architecture/      # 아키텍처 문서
│   ├── analysis/          # 분석 문서
│   └── implementation/    # 구현 문서
├── backup/
└── temp/
```

---

## 🧪 테스트

```bash
# 전체 테스트
pytest

# 빠른 확인
pytest -q

# 특정 모듈
pytest dev/scripts/tests/test_world_engine.py -v
```

**현황**: 44개 테스트, 모두 통과 ✅

---

## 📖 주요 문서

**사용법**:
- `README_v1.md`: 상세 사용 가이드

**아키텍처** (`dev/docs/architecture/`):
- `CMIS_Architecture_Blueprint.md`: 전체 아키텍처
- `cmis_philosophy_concept.md`: 핵심 철학
- `cmis_roadmap.md`: 개발 로드맵
- `cmis_project_context_layer_design.md`: Project Context 설계

**구현** (`dev/docs/implementation/`):
- `CMIS_Implementation_Strategy_Final.md`: 구현 전략
- `CMIS_Structure_Analysis_Detailed_Workflow.md`: 워크플로우 상세
- `CMIS_Structure_Analysis_Diagrams.md`: 13개 다이어그램

---

## 🎓 새 도메인 추가

1. **Reality seed 생성**:
   ```yaml
   # seeds/Your_Domain_reality_seed.yaml
   ---
   cmis_reality_seed:
     meta:
       domain_id: "Your_Domain"
     actors: [...]
     money_flows: [...]
   ```

2. **domain_registry.yaml 등록**:
   ```yaml
   cmis_domain_registry:
     domains:
       - domain_id: "Your_Domain"
         config_file: "cmis_domain_Your_Domain.yaml"
   ```

3. **실행**:
   ```bash
   python3 -m cmis_cli structure-analysis --domain Your_Domain --region KR
   ```

---

## 📊 성능

- 실행 시간: < 0.1초 (seed 기반)
- 메모리: < 50MB
- 테스트: 44개, 4초

---

## 🔧 개발

**검증**:
```bash
# YAML 무결성
python3 dev/scripts/validation/validate_yaml_integrity.py

# 전체 테스트
pytest
```

**예시**:
- `dev/examples/project_context_examples.yaml`: Project Context 3가지 시나리오

---

## 📜 브랜드 변경 이력

**2025-12-09**: UMIS v9 → CMIS
- Universal Market Intelligence → **Contextual** Market Intelligence
- v9 핵심 차별점 (Project Context Layer) 반영
- "사용자 상황을 이해하는" 시스템으로 진화

---

---

**CMIS Team • 2025 • Production Ready**

GitHub: [kangminlee-maker/cmis](https://github.com/kangminlee-maker/cmis)
