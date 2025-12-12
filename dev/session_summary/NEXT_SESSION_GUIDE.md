# 다음 세션 가이드

**작성일**: 2025-12-11
**현재 버전**: CMIS v3.3
**완성도**: 89%
**다음 목표**: Production 배포 (v4.0)

---

## 현재 상태 요약

### 완성 엔진 (8/9) - 89%

| 엔진 | 상태 | 완성도 | 테스트 |
|------|------|--------|--------|
| Evidence Engine | ✅ | 100% | ✅ |
| Pattern Engine | ✅ | 100% | 53/53 |
| Value Engine | ✅ | 100% | ✅ |
| World Engine | ✅ | 100% | 56/56 |
| Search Strategy | ✅ | 100% | ✅ |
| Workflow CLI | ✅ | 100% | 19/19 |
| Strategy Engine | ✅ | 100% | 29/29 |
| Learning Engine | ✅ | 100% | 23/23 |

**테스트**: 377/378 (99.7%)

### 핵심 기능

- ✅ Understand → Discover → Decide → Learn 루프
- ✅ Greenfield/Brownfield 완전 지원
- ✅ Graph-of-Graphs (R/P/V/D)
- ✅ Evidence-first (실시간 데이터)
- ✅ Pattern 기반 전략 생성
- ✅ 자동 학습 및 개선

---

## 다음 개발 과제

### Priority 1: Production 배포 준비 (v4.0)

**예상 시간**: 1-2주

#### 1.1 성능 최적화

**작업**:
- [ ] 성능 프로파일링
  - 병목 지점 파악
  - 메모리 사용량 최적화
  - 캐시 효율성 개선

- [ ] 인덱싱 강화
  - RealityGraphStore 인덱스 최적화
  - Pattern 검색 인덱스
  - Metric 계산 캐싱

- [ ] 병렬 처리 개선
  - Evidence 수집 병렬화
  - Batch 분석 최적화

**예상 시간**: 3-4일

#### 1.2 배포 인프라

**작업**:
- [ ] Docker 설정
  - Dockerfile 작성
  - docker-compose.yaml
  - 환경 변수 관리

- [ ] 배포 스크립트
  - 설치 스크립트
  - 업데이트 스크립트
  - 백업/복구 스크립트

- [ ] CI/CD
  - GitHub Actions 설정
  - 자동 테스트
  - 자동 배포

**예상 시간**: 3-4일

#### 1.3 문서화 완성

**작업**:
- [ ] 사용자 가이드
  - 설치 가이드
  - 빠른 시작
  - CLI 명령어 레퍼런스
  - Python API 레퍼런스

- [ ] 개발자 가이드
  - 아키텍처 개요
  - 엔진별 가이드
  - 기여 가이드

- [ ] 운영 가이드
  - 설치 및 설정
  - 트러블슈팅
  - 성능 튜닝

**예상 시간**: 2-3일

---

### Priority 2: 고급 기능 (v4.1)

**예상 시간**: 2-3주

#### 2.1 ValueEngine 고급 기능

**작업**:
- [ ] ValueEngine.simulate_scenario()
  - What-if 시뮬레이션
  - Strategy → Metric 변화 예측

- [ ] Metric Formula 자동 학습
  - LearningEngine 연동
  - 공식 보정

- [ ] 불확실성 정량화
  - Distribution 기반 예측
  - Monte Carlo 시뮬레이션

**예상 시간**: 1주

#### 2.2 StrategyEngine 고급 최적화

**작업**:
- [ ] Dynamic Programming 최적화
  - Knapsack 기반 Portfolio
  - 최적해 보장

- [ ] 유전 알고리즘
  - 복잡한 제약 조건
  - 다목표 최적화

- [ ] Scenario Planning
  - 여러 시나리오 생성
  - 민감도 분석

**예상 시간**: 1주

#### 2.3 LearningEngine 고급 기능

**작업**:
- [ ] ValueEngine 완전 연동
  - Belief Update Request
  - value_graph 직접 수정

- [ ] memory_store 완전 통합
  - MEM-* 저장
  - drift_alert 자동 생성
  - pattern_note 관리

- [ ] Human-in-the-loop
  - 학습 승인 모드
  - Rollback 기능

**예상 시간**: 1주

---

### Priority 3: Web UI (v5.0, 선택)

**예상 시간**: 1-2개월

#### 3.1 대시보드

**작업**:
- [ ] 메인 대시보드
  - 시장 개요
  - 주요 Metric
  - 최근 분석

- [ ] 인터랙티브 분석
  - 파라미터 조정
  - 실시간 업데이트

- [ ] 시각화
  - R-Graph 시각화
  - Pattern 분포
  - 시계열 차트

#### 3.2 보고서 생성기

**작업**:
- [ ] 템플릿 시스템
- [ ] PDF 생성
- [ ] 차트 포함

---

## 세션 준비 사항

### 필수 확인

**현재 상태**:
- [ ] git status 확인
- [ ] 최신 코드 pull
- [ ] 테스트 실행 (377/378 통과 확인)
- [ ] 환경 변수 설정 (.env)

**문서 확인**:
- [ ] CHANGELOG.md 최신 버전 확인
- [ ] README.md 버전 확인 (v3.3)
- [ ] dev/docs/architecture/ 설계 문서 확인

---

## 개발 우선순위별 가이드

### Option 1: Production 배포 (추천)

**선택 이유**:
- 89% 완성, 실전 투입 가능
- 사용자 피드백 수집 시작
- 실무 검증

**시작 파일**:
- `Dockerfile` (신규 작성)
- `docker-compose.yaml` (신규)
- `docs/user_guide/` (신규)

**참고 문서**:
- CMIS_Architecture_Blueprint_v3.3.md
- CMIS_Implementation_Status_v3.3.md

---

### Option 2: 고급 기능 개발

**선택 이유**:
- 완성도 향상
- 차별화된 기능

**시작 파일**:
- `cmis_core/value_engine.py` (확장)
- `cmis_core/strategy_optimizer.py` (신규)
- `cmis_core/scenario_planner.py` (신규)

**참고 문서**:
- StrategyEngine_Design_Enhanced.md
- LearningEngine_Design_Enhanced.md

---

### Option 3: Web UI 개발

**선택 이유**:
- 사용자 경험 향상
- 접근성 개선

**시작 파일**:
- `cmis_web/` (신규 폴더)
- `cmis_web/app.py` (FastAPI)
- `cmis_web/templates/` (Jinja2)

**참고 문서**:
- Workflow_CLI_Design_Enhanced.md (UI 참고)

---

## 알려진 이슈

### 해결 필요

**1. Google API 403 (낮은 우선순위)**
- 문제: IP 주소 제한
- 해결: Google Cloud Console 설정
- 우회: DuckDuckGo 사용

**2. test_config.py 버전 체크 (해결됨)**
- ~~문제: 버전 9.0.0-alpha vs 3.3.0~~
- 해결: 테스트 업데이트 필요

---

## 세션 시작 체크리스트

### 환경 설정
- [ ] Python 3.13+ 설치
- [ ] 의존성 설치: `pip install -r requirements.txt`
- [ ] 환경 변수 설정: `.env` 파일
- [ ] API 키 확인 (KOSIS, DART, ECOS)

### 코드 확인
- [ ] `git pull` 실행
- [ ] `pytest` 실행 (377/378 통과 확인)
- [ ] `python3 -m cmis_cli config-validate --check-all`

### 문서 확인
- [ ] CHANGELOG.md 최신 버전 (v3.3)
- [ ] TODO 리스트 (현재 없음, 새로 작성 필요)

---

## 참고 자료

### 핵심 문서
1. `dev/docs/architecture/CMIS_Architecture_Blueprint_v3.3.md`
2. `dev/docs/architecture/CMIS_Implementation_Status_v3.3.md`
3. `dev/docs/architecture/CMIS_Roadmap_v3.3.md`

### 엔진별 설계
- World Engine: `World_Engine_Enhanced_Design.md`
- Strategy Engine: `StrategyEngine_Design_Enhanced.md`
- Learning Engine: `LearningEngine_Design_Enhanced.md`
- Workflow CLI: `Workflow_CLI_Design_Enhanced.md`

### 이전 세션
- `dev/session_summary/20251211/` (25개 파일)
- 주요: `SESSION_ABSOLUTE_COMPLETE.md`, `CMIS_FINAL_COMPLETE.md`

---

## 빠른 명령어

### 테스트
```bash
# 전체
pytest

# 특정 엔진
pytest dev/tests/unit/test_world_engine*.py
pytest dev/tests/unit/test_strategy_engine*.py

# 빠른 확인
pytest -q
```

### CLI
```bash
# 시장 분석
python3 -m cmis_cli structure-analysis --domain Adult_Language_Education_KR --region KR

# 기회 발굴
python3 -m cmis_cli opportunity-discovery --domain Adult_Language_Education_KR --region KR --top-n 5

# 설정 검증
python3 -m cmis_cli config-validate --check-all
```

### 검증
```bash
# YAML
python3 dev/validation/validate_yaml_integrity.py

# 코드베이스
python3 dev/validation/validate_codebase.py
```

---

## 예상 일정

### v4.0 (Production) - 2주
- Week 1: 성능 최적화, Docker
- Week 2: 문서화, 배포

### v4.1 (고급 기능) - 3주
- Week 1: ValueEngine 고급
- Week 2: StrategyEngine 최적화
- Week 3: LearningEngine 고급

### v5.0 (Web UI) - 2개월
- Month 1: 기본 UI
- Month 2: 고급 기능

---

## 연락처 및 리소스

### GitHub
- Repository: https://github.com/kangminlee-maker/cmis
- Issues: 문제 보고
- Discussions: 질문/논의

### 문서
- Architecture: `dev/docs/architecture/`
- Analysis: `dev/docs/analysis/`
- Implementation: `dev/docs/implementation/`

---

**작성**: 2025-12-11
**현재**: CMIS v3.3 (89%)
**다음**: v4.0 (Production)

**준비 완료!** ✅
