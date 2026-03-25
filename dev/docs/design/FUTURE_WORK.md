# CMIS v2 향후과제

## 완료된 과제

### ~~Belief 엔진 로직 재검토~~ → Estimation Engine으로 대체 (2026-03-25)
- Belief Engine 폐기, 순수 Interval(P10/P90) 기반 Estimation Engine 구현
- 3차례 8-Agent Panel Review (8/8 완전 합의)
- Fermi 분해 트리, Constraint Propagation, batch fusion 포함
- confidence→sigma 변환 접근법(접근법 A) 폐기

### ~~Estimation Engine Phase 4: 하이브리드 확장~~ → 완료 (2026-03-26)
- Distribution 모듈: Beta/Lognormal/Uniform fitting (scipy 없음)
- Monte Carlo supplementary (evaluate_fermi_tree mc_summary)
- distribution_type 24개 메트릭 선언
- 2차례 8-Agent Panel Review (8/8 합의)

### ~~value_min_confidence 게이트 마이그레이션~~ → 완료 (2026-03-25)
- value_spread_ratio로 전면 대체, 3개 정책 모드 모두 이행

### ~~Reference Class Forecasting~~ → 완료 (2026-03-26)
- 과거 outcome에서 empirical P10/P90 구간 제안
- suggest_estimate_from_reference 도구 등록

### ~~Calibration~~ → 빈도 기반 완료 (2026-03-26)
- 빈도 기반 source_reliability 보정 (accurate×0.9 + acceptable×0.5)
- Platt Scaling은 outcome ≥30건 축적 시 후속

## 중간 우선순위

### Persistent RLM
- 대화형 분석 (세션 유지) 지원

### Docker 격리
- 프로덕션 배포 시 RLM DockerREPL로 전환

### 도메인별 trait scoping
- 다중 도메인 지원 시 ontology.yaml에 도메인 프로필 추가

### Platt Scaling (Calibration Phase 2)
- outcome ≥30건 축적 시 로지스틱 회귀 기반 보정으로 전환
- metric별, source_tier별 calibration curve

## 낮은 우선순위

### 외부 온톨로지 매핑 (FIBO, SNOMED 등)
### 스케줄링/배치 (reality_monitoring 주기 실행)
### 시각화 (RLM visualizer 연동)
