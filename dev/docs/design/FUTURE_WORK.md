# CMIS v2 향후과제

## 높은 우선순위

### Belief 엔진 로직 재검토
- 현재: 단순 가중 평균 (pseudo-Bayesian)
- 필요: 적절한 베이지안 추론 (conjugate prior, MCMC 등)
- 현재 update_belief()의 공식이 통계적으로 올바른지 검증 필요
- scipy.stats 활용 가능성 검토
- 다중 소스 융합(multi-source fusion) 로직 설계

## 중간 우선순위

### Persistent RLM
- 대화형 분석 (세션 유지) 지원

### Docker 격리
- 프로덕션 배포 시 RLM DockerREPL로 전환

### 도메인별 trait scoping
- 다중 도메인 지원 시 ontology.yaml에 도메인 프로필 추가

## 낮은 우선순위

### 외부 온톨로지 매핑 (FIBO, SNOMED 등)
### 스케줄링/배치 (reality_monitoring 주기 실행)
### 시각화 (RLM visualizer 연동)
