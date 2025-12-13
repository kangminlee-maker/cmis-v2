# CMIS Examples

**업데이트**: 2025-12-11

---

## 예시 파일

### 1. project_context_examples.yaml

**목적**: FocalActorContext 입력 예시

**시나리오** (3개):
1. Greenfield (신규 진입, 자본 제약)
2. Brownfield (기존 사업자)
3. Hybrid

---

### 2. seeds/

**목적**: Reality seed 예시 (테스트/데모용)

**파일**:
- `Adult_Language_Education_KR_reality_seed.yaml`

**사용**:
```python
from cmis_core.world_engine import WorldEngine

engine = WorldEngine()
snapshot = engine.snapshot('Adult_Language_Education_KR', 'KR')
```

**Note**:
- Production에서는 Evidence 기반 권장 (seed 불필요)
- Development에서는 빠른 테스트/데모에 유용

---

## 실행 방식

### Evidence 기반 (권장)

```python
# 1. Evidence 수집
evidence = evidence_engine.fetch_for_metrics([
    MetricRequest("MET-Market_size", {"domain": "New_Market"})
])

# 2. R-Graph 생성
world_engine.ingest_evidence("New_Market", evidence.records)

# 3. 분석
snapshot = world_engine.snapshot("New_Market", "KR")
patterns = pattern_engine.match_patterns(snapshot.graph)
```

**장점**:
- 실시간 데이터
- seed 작성 불필요
- 동적 업데이트

---

### Seed 기반 (테스트/데모)

```python
# 1. Seed 로딩
snapshot = world_engine.snapshot('Adult_Language_Education_KR', 'KR')

# 2. 분석
patterns = pattern_engine.match_patterns(snapshot.graph)
```

**장점**:
- 빠른 초기화
- 오프라인 가능
- 재현 가능

---

**작성**: 2025-12-11
**용도**: 테스트, 데모, 예시


