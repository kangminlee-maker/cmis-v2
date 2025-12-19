# CMIS v3 다음 작업 로드맵

**작성일**: 2025-12-10
**현재 버전**: v2.1
**다음 버전**: v3.0

---

## 현재 상태 (v2.1)

### ✅ 완성된 기능

**Evidence Engine**:
- 4-Layer 아키텍처
- 4개 API 작동 (KOSIS, DART, Google, DuckDuckGo)
- EvidenceStore (캐시 1000배)
- ValueEngine 통합

**LLM Infrastructure**:
- TaskRoute 기반
- OpenAI 통합
- Optimization hooks
- 비용 추적

**DART Advanced**:
- AccountMatcher (Rule + Fallback)
- SG&A 세부 항목 추출 (LLM)
- 6개 기업 검증

**품질**:
- 128개 테스트 (100%)
- 리팩토링 완료 (-650 라인)
- CMIS 철학 부합

---

## v3 우선순위 작업

### 1. PatternEngine 확장 (최우선)

**목표**: 23개 Pattern 구현

**현재 상태**:
- pattern_engine.py (POC, 2개 Pattern)
- cmis.yaml에 Pattern 스펙 정의됨

**작업** (2-3주):
- [ ] Pattern Graph 구조 확장
- [ ] 23개 Pattern 정의 (subscription, platform, franchise 등)
- [ ] Pattern matching 알고리즘
- [ ] Trait 기반 인식
- [ ] Gap analysis
- [ ] 테스트 (10+ 도메인)

**참고**:
- `cmis.yaml` pattern_graph
- `dev/v7_reference` Pattern 정의

---

### 2. LLM 실전 활용 (높음)

**목표**: LLM을 실제 Engine에 통합

**작업** (1-2주):
- [ ] DART AccountMatcher LLM 활성화
- [ ] Pattern 추론 (LLM)
- [ ] Anthropic Claude 통합
- [ ] PromptTemplate Registry
- [ ] 비용 최적화 (Task별 모델 튜닝)

**현재 준비 완료**:
- LLMService (TaskRoute 기반)
- OpenAI 작동 검증
- cost tracking

---

### 3. StrategyEngine 초기 구현 (높음)

**목표**: Goal/Strategy 기본 기능

**작업** (2-3주):
- [ ] Decision Graph 기본 구조
- [ ] Goal 정의
- [ ] Strategy 생성 (Pattern 기반)
- [ ] Scenario 평가
- [ ] search_strategies() API

**참고**:
- `cmis.yaml` decision_graph
- `strategic_frameworks.yaml`

---

### 4. Project Context Layer (중간)

**목표**: Brownfield 분석 지원

**작업** (2-3주):
- [ ] Project Context Store
- [ ] Focal actor 관리
- [ ] Baseline state
- [ ] Capability traits
- [ ] Constraints/Preferences

**참고**:
- `cmis_project_context_layer_design.md`
- cmis.yaml focal_actor_context_store

---

## 즉시 개선 사항

### 단기 (1주)

**LLM**:
- [ ] MockLLM 테스트 안정화
- [ ] OpenAI 기본 Provider 설정
- [ ] LLM 비용 실제 검증

**DART**:
- [ ] SG&A 단위 변환 검증
- [ ] 10+ 기업 테스트
- [ ] 회사명 매칭 개선 (하이브 케이스)

**KOSIS**:
- [ ] 다양한 통계표 검증 (인구, 가구, 소득 등)
- [ ] objL1, objL2 파라미터 옵션 테스트
- [ ] itmId 항목 코드 매핑 구축
- [ ] 지역별 데이터 조회 (전국, 시도별)
- [ ] 시계열 데이터 (startPrdDe, endPrdDe)
- [ ] JavaScript JSON 파싱 안정성 검증

**문서**:
- [ ] API 사용 가이드
- [ ] LLM 설정 가이드
- [ ] 배포 가이드

---

### 중기 (2-3주)

**Evidence**:
- [ ] KOSIS 고도화 (통계표 매핑 확장)
- [ ] 추가 Official Source (한국은행, 금융위)
- [ ] Commercial Source (시장조사 리포트)
- [ ] Rate limiting 실제 구현

**LLM**:
- [ ] Streaming 구현
- [ ] JSON mode (OpenAI)
- [ ] 프롬프트 버전 관리

---

## 기술 부채 관리

### 해결된 부채

- ✅ Evidence Engine 설계 (피드백 반영)
- ✅ LLM 중앙 관리
- ✅ 중복 코드 (-650 라인)
- ✅ DART 하드코딩 제거

### 남은 부채 (낮은 우선순위)

- [ ] evidence_engine.py 분리 (673 라인, v4)
- [ ] datetime.utcnow() deprecation (value_engine.py)
- [ ] DuckDuckGo 패키지 업데이트 (ddgs)
- [ ] **KOSIS 파라미터 매핑 확장** (objL, itmId 체계화)

---

## 필요한 리소스

### API Keys (확보됨)

- ✅ OPENAI_API_KEY
- ✅ ANTHROPIC_API_KEY
- ✅ KOSIS_API_KEY
- ✅ DART_API_KEY
- ✅ GOOGLE_API_KEY
- ✅ GOOGLE_SEARCH_ENGINE_ID

### Python Packages

**현재**:
- openai
- requests
- beautifulsoup4
- pydantic
- pytest

**필요 (선택)**:
- anthropic (Claude)
- ddgs (DuckDuckGo 최신)

---

## 예상 타임라인

### v3.0 (1-2개월)

**Month 1**:
- Week 1-2: PatternEngine (23 Pattern)
- Week 3-4: LLM 실전 활용

**Month 2**:
- Week 1-2: StrategyEngine
- Week 3-4: Project Context Layer

### v4.0 (2-3개월)

- BeliefEngine
- LearningEngine
- Web UI
- 대규모 리팩토링 (engine 분리)

---

## 성공 기준

### v3 완료 조건

- [ ] 23개 Pattern 작동
- [ ] Strategy 생성 가능
- [ ] LLM 실전 사용 (10+ 케이스)
- [ ] Project Context 1개 완성
- [ ] 200+ 테스트
- [ ] 문서 완전

---

## 참고 문서

**설계**:
- `cmis.yaml` (전체 스펙)
- `dev/docs/architecture/README.md`
- `dev/docs/architecture/CMIS_Architecture_Blueprint_v3.6.0_km.md`

**구현**:
- `Evidence_Engine_Design_Revision.md`
- `CMIS_LLM_Infrastructure_Revision.md`
- `DART_Proper_Design.md`

**세션 서머리**:
- `session_summary_20251210.yaml` (오늘)
- `session_summary_20251209.yaml` (어제)

---

**작성**: 2025-12-10
**상태**: v2.1 완성, v3 준비 완료
**다음**: PatternEngine 또는 LLM 실전 활용
