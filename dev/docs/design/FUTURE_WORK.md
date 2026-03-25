# CMIS v2 향후과제

## 완료된 과제

### ~~Belief 엔진 로직 재검토~~ → Estimation Engine으로 대체 (2026-03-25)
- Belief Engine 폐기, 순수 Interval(P10/P90) 기반 Estimation Engine 구현
- 3차례 8-Agent Panel Review (8/8 완전 합의)
- Fermi 분해 트리, Constraint Propagation, batch fusion 포함
- confidence→sigma 변환 접근법(접근법 A) 폐기

## 높은 우선순위

### Estimation Engine Phase 4: 하이브리드 확장
- `Estimate`에 `distribution: Distribution | None` 필드 추가
- `Interval.to_uniform()` 변환 함수 — Monte Carlo 시뮬레이션 진입점
- 정밀 메트릭에만 Distribution 추가 (나머지는 Interval 유지)
- 3차 리뷰 evolution 에이전트 권장: Phase 1에서 필드만 선언, Phase 3에서 구현

### value_min_confidence 게이트 마이그레이션
- Estimation Engine이 confidence 대신 Interval 사용하므로, value_min_confidence 게이트를 value_spread_ratio로 대체
- 영향 범위: policy.py, policies.yaml (reporting_strict, decision_balanced 모드)

## 중간 우선순위

### Persistent RLM
- 대화형 분석 (세션 유지) 지원

### Docker 격리
- 프로덕션 배포 시 RLM DockerREPL로 전환

### 도메인별 trait scoping
- 다중 도메인 지원 시 ontology.yaml에 도메인 프로필 추가

### Reference Class Forecasting
- 유사 과거 사례 기반 추정 (FermiNode와 동등 수준의 ReferenceClassNode)
- Evidence Engine의 수집 데이터를 참조 집단 구축 재료로 활용

## 낮은 우선순위

### 외부 온톨로지 매핑 (FIBO, SNOMED 등)
### 스케줄링/배치 (reality_monitoring 주기 실행)
### 시각화 (RLM visualizer 연동)
### Calibration (Learning Engine 연동)
- outcome 데이터 축적 시 Platt Scaling으로 source_reliability 보정
- metric별, source_tier별 calibration curve
