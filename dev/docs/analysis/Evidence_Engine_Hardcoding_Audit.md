# Evidence Engine 하드코딩 전수 검토

**작성일**: 2025-12-10
**목적**: 하드코딩된 부분 식별 및 개선 방안
**범위**: Evidence Engine 전체 (10개 파일)

---

## 📋 검토 대상 파일

### Core (3개)
- evidence_engine.py (778 라인)
- evidence_store.py (616 라인)
- rate_limiter.py (189 라인)

### Quality/Validation (6개)
- evidence_quality.py (140 라인)
- evidence_validation.py (182 라인)
- evidence_batch.py (150 라인)
- evidence_parallel.py (130 라인)
- evidence_retry.py (180 라인)

### Sources (10개)
- kosis_source.py (509 라인)
- ecos_source.py (364 라인)
- dart_connector.py (497 라인)
- google_search_source.py (142 라인)
- duckduckgo_source.py (150 라인)
- base_search_source.py (304 라인)
- sga_extractor.py (315 라인)
- account_matcher.py (191 라인)
- sources.py (220 라인)

**총 19개 파일, 4,500+ 라인**

---

## 🔍 발견된 하드코딩 (우선순위순)

### 🔴 Critical: 동적 개선 필수

#### 1. kosis_source.py - STAT_TABLES

**위치**: Line 69-87

**현재**:
```python
STAT_TABLES = {
    "population": {
        "orgId": "101",
        "tblId": "DT_1B04006",
        "itmId": "T2",
        "prdSe": "Y"
    },
    "household": {...}
}
```

**문제**:
- 통계표가 2개로 고정
- 새 통계표 추가 시 코드 수정 필요
- 확장성 제한

**개선 방안**:
```python
# Option 1: YAML 외부화
# config/kosis_tables.yaml
tables:
  - stat_type: population
    orgId: "101"
    tblId: "DT_1B04006"
    itmId: "T2"

# Option 2: KOSIS API로 동적 조회
def discover_tables(domain):
    # StatisticTableList API 호출
    # 사용 가능한 통계표 자동 발견
```

**우선순위**: ⭐⭐⭐⭐⭐ (매우 높음)
**난이도**: 🟡 중간
**예상**: 2일

---

#### 2. kosis_source.py - REGION_CODES

**위치**: Line 89-109

**현재**:
```python
REGION_CODES = {
    "KR": "00",
    "서울": "11",
    "부산": "26",
    # ... 17개
}
```

**문제**:
- 17개 시도로 고정
- 세종시 추가 같은 변경 시 코드 수정

**개선 방안**:
```python
# Option 1: YAML 외부화
# config/region_codes.yaml

# Option 2: KOSIS StatisticItemList API로 조회
def discover_regions(stat_code):
    # objL1 항목 목록 자동 조회
```

**우선순위**: ⭐⭐⭐ (중간)
**난이도**: 🟢 낮음
**예상**: 1일

---

#### 3. ecos_source.py - KEY_STATISTICS

**위치**: Line 56-76

**현재**:
```python
KEY_STATISTICS = {
    "gdp": {
        "keyword": "GDP(명목, 계절조정)",
        "name": "GDP (명목)",
        "unit": "십억원"
    },
    # ... 5개만
}
```

**문제**:
- 5개 지표로 제한
- 100대 지표 중 5개만 활용

**개선 방안**:
```python
# Option 1: 전체 100대 지표 동적 조회
def fetch_all_key_statistics():
    # KeyStatisticList 전체 조회
    # 런타임에 keyword로 검색

# Option 2: YAML 외부화 (확장 용이)
# config/ecos_keywords.yaml
```

**우선순위**: ⭐⭐⭐⭐ (높음)
**난이도**: 🟢 낮음
**예상**: 1일

---

#### 4. evidence_engine.py - _capability_to_metric()

**위치**: Line 729-755

**현재**:
```python
mapping = {
    "population_by_age": "MET-N_customers",
    "gdp_stats": "MET-GDP",
    "market_data": "MET-TAM",
    # ... 15개
}
```

**문제**:
- Capability-Metric 매핑 하드코딩
- 새 Capability 추가 시 코드 수정

**개선 방안**:
```python
# Option 1: YAML 외부화
# config/capability_metric_mapping.yaml
capability_mappings:
  - capability: population_by_age
    metric_id: MET-N_customers
  - capability: gdp_stats
    metric_id: MET-GDP

# Option 2: cmis.yaml metrics_spec 활용
# metrics_spec.metrics[].direct_evidence_sources를 역으로 활용
def capability_to_metric(capability):
    for metric_id, spec in metrics_spec.items():
        if capability in spec.direct_evidence_sources:
            return metric_id
```

**우선순위**: ⭐⭐⭐⭐⭐ (매우 높음)
**난이도**: 🟡 중간
**예상**: 2일

---

#### 5. rate_limiter.py - LIMITS

**위치**: Line 20-49

**현재**:
```python
LIMITS = {
    "ECOS": {"calls": 100, "period": 60},
    "KOSIS": {"calls": 1000, "period": 86400},
    # ... 5개
}
```

**문제**:
- Source별 제한 하드코딩
- 새 Source 추가 시 코드 수정

**개선 방안**:
```python
# Option 1: YAML 외부화
# config/rate_limits.yaml

# Option 2: Source에서 제공
class BaseDataSource:
    def get_rate_limit(self):
        return {"calls": 1000, "period": 86400}

# Option 3: 기본값 + override
LIMITS = load_from_yaml("rate_limits.yaml")
```

**우선순위**: ⭐⭐⭐ (중간)
**난이도**: 🟢 낮음
**예상**: 1일

---

### 🟡 Medium: 개선 권장

#### 6. kosis_source.py - _determine_stat_type()

**위치**: Line 468-501

**현재**:
```python
if "n_customers" in metric_lower or "population" in metric_lower:
    return "population"

if "household" in metric_lower or "family" in metric_lower:
    return "household"
```

**문제**:
- if-elif 체인 (확장 어려움)
- 키워드 하드코딩

**개선 방안**:
```python
# Option 1: 패턴 매칭 테이블
STAT_TYPE_PATTERNS = {
    "population": ["n_customers", "population", "인구"],
    "household": ["household", "family", "가구"]
}

def _determine_stat_type(request):
    for stat_type, keywords in STAT_TYPE_PATTERNS.items():
        if any(kw in metric_lower for kw in keywords):
            return stat_type

# Option 2: STAT_TABLES에 통합
STAT_TABLES = {
    "population": {
        "keywords": ["n_customers", "population", "인구"],
        "orgId": "101",
        ...
    }
}
```

**우선순위**: ⭐⭐⭐ (중간)
**난이도**: 🟢 낮음
**예상**: 0.5일

---

#### 7. ecos_source.py - _determine_stat_type()

**위치**: Line 327-365

**현재**:
```python
if "gdp" in metric_lower:
    if "growth" in metric_lower:
        return "gdp_growth"
    elif "real" in metric_lower:
        return "gdp_real"
    else:
        return "gdp"

if "cpi" in metric_lower or "inflation" in metric_lower:
    return "cpi"
```

**문제**:
- 중첩된 if-elif (복잡)
- 키워드 하드코딩

**개선 방안**:
```python
# KEY_STATISTICS에 통합
KEY_STATISTICS = {
    "gdp": {
        "keywords": ["gdp"],
        "exclude_keywords": ["growth", "real"],
        ...
    },
    "gdp_growth": {
        "keywords": ["gdp", "growth"],
        ...
    }
}

def _determine_stat_type(request):
    for stat_type, info in KEY_STATISTICS.items():
        if all(kw in metric_lower for kw in info["keywords"]):
            if not any(ex in metric_lower for ex in info.get("exclude_keywords", [])):
                return stat_type
```

**우선순위**: ⭐⭐⭐ (중간)
**난이도**: 🟢 낮음
**예상**: 0.5일

---

#### 8. base_search_source.py - build_search_query()

**위치**: Line 84-99

**현재**:
```python
if "revenue" in metric_id or "tam" in metric_id:
    parts.append("market size")

if "revenue" in metric_id:
    parts.append("revenue")
elif "tam" in metric_id:
    parts.append("total addressable market")
```

**문제**:
- 검색 키워드 로직 하드코딩
- Metric별 최적 쿼리가 다를 수 있음

**개선 방안**:
```python
# Option 1: Metric별 쿼리 템플릿
QUERY_TEMPLATES = {
    "MET-TAM": "{domain} {region} total addressable market size {year}",
    "MET-Revenue": "{domain} {region} market revenue {year}",
    "MET-GDP": "{region} GDP {year}"
}

# Option 2: LLM 기반 쿼리 생성
def build_search_query_smart(request):
    # LLM에게 최적 쿼리 생성 요청
```

**우선순위**: ⭐⭐ (낮음, 현재도 작동)
**난이도**: 🟡 중간
**예상**: 1일

---

### 🟢 Low: 현재 상태 양호

#### 9. evidence_quality.py - tier_scores

**위치**: Line 91-95

**현재**:
```python
tier_scores = {
    "official": 1.0,
    "curated_internal": 0.8,
    "commercial": 0.6
}
```

**문제**: SourceTier enum과 연동됨 (문제 적음)

**개선**: YAML 외부화 (선택적)

**우선순위**: ⭐ (낮음)

---

#### 10. evidence_validation.py - conflict_threshold

**위치**: Line 113 (함수 파라미터)

**현재**:
```python
def detect_conflicts(evidence_list, conflict_threshold=0.5):
```

**문제**: 거의 없음 (파라미터로 조정 가능)

**우선순위**: ⭐ (낮음)

---

## 📊 하드코딩 요약

| 파일 | 항목 | 타입 | 우선순위 | 개선 방안 |
|------|------|------|----------|-----------|
| **kosis_source.py** | STAT_TABLES | Dict | 🔴 매우높음 | YAML 또는 API 조회 |
| **kosis_source.py** | REGION_CODES | Dict | 🟡 중간 | YAML 또는 API 조회 |
| **ecos_source.py** | KEY_STATISTICS | Dict | 🔴 높음 | YAML 또는 전체 조회 |
| **evidence_engine.py** | capability mapping | Dict | 🔴 매우높음 | cmis.yaml 연동 |
| **kosis_source.py** | _determine_stat_type | if-elif | 🟡 중간 | 패턴 테이블 |
| **ecos_source.py** | _determine_stat_type | if-elif | 🟡 중간 | 패턴 테이블 |
| **base_search_source.py** | build_search_query | if-elif | 🟢 낮음 | 템플릿 |
| **rate_limiter.py** | LIMITS | Dict | 🟡 중간 | YAML |

**총 8개 하드코딩 발견**

---

## 🎯 개선 우선순위

### Phase 1: 즉시 개선 (1주)

**1. evidence_engine.py - capability_to_metric (최우선)**

**현재 문제**:
- Capability-Metric 매핑 15개 하드코딩
- 확장 시마다 코드 수정

**개선안**:
```python
# cmis.yaml metrics_spec 활용
class EvidenceEngine:
    def _build_capability_mapping(self):
        """metrics_spec에서 동적 생성"""
        mapping = {}

        for metric_id, spec in self.config.metrics.items():
            sources = spec.direct_evidence_sources
            for source in sources:
                mapping[source] = metric_id

        return mapping
```

**효과**:
- ✅ cmis.yaml 단일 진실의 원천
- ✅ 코드 수정 불필요
- ✅ 자동 sync

---

**2. kosis/ecos_source.py - STAT_TABLES/KEY_STATISTICS**

**개선안**:
```python
# config/sources/kosis_tables.yaml
tables:
  - stat_type: population
    orgId: "101"
    tblId: "DT_1B04006"
    itmId: "T2"
    keywords: [n_customers, population, 인구]

# config/sources/ecos_keywords.yaml
statistics:
  - stat_type: gdp
    keyword: "GDP(명목, 계절조정)"
    keywords_match: [gdp]
    keywords_exclude: [growth, real]
```

**효과**:
- ✅ 비개발자도 통계표 추가 가능
- ✅ 버전 관리
- ✅ 테스트 용이

---

### Phase 2: 권장 개선 (3일)

**3. _determine_stat_type() 통합**

**개선안**:
```python
# STAT_TABLES/KEY_STATISTICS에 keywords 추가
# 패턴 매칭 엔진 사용

def _determine_stat_type(request, stat_tables):
    metric_text = f"{request.metric_id} {request.context}".lower()

    for stat_type, info in stat_tables.items():
        keywords = info.get("keywords", [])
        exclude = info.get("exclude_keywords", [])

        if any(kw in metric_text for kw in keywords):
            if not any(ex in metric_text for ex in exclude):
                return stat_type

    return None
```

---

**4. Rate Limiter LIMITS**

**개선안**:
```python
# config/rate_limits.yaml
limits:
  - source_id: ECOS
    calls: 100
    period: 60
  - source_id: KOSIS
    calls: 1000
    period: 86400

# 또는 BaseDataSource에 메서드 추가
class BaseDataSource:
    def get_rate_limit(self):
        """각 Source가 자신의 제한 반환"""
        return {"calls": 1000, "period": 86400}
```

---

### Phase 3: 선택적 개선 (1주)

**5. build_search_query 최적화**

**개선안**:
```python
# config/search_query_templates.yaml
templates:
  MET-TAM: "{domain} {region} total addressable market size {year}"
  MET-Revenue: "{domain} {region} revenue {year}"

# 또는 LLM 기반
def build_search_query_smart(request):
    prompt = f"Generate optimal search query for {request.metric_id}"
    return llm.generate(prompt)
```

---

## 🔧 구현 계획

### Week 1: Critical 하드코딩 제거

**Day 1-2**: capability_to_metric
- cmis.yaml metrics_spec 연동
- 동적 mapping 생성
- 테스트

**Day 3-4**: STAT_TABLES, KEY_STATISTICS
- YAML 외부화
- 로딩 로직
- 테스트

**Day 5**: REGION_CODES
- YAML 외부화 또는 API 조회

---

### Week 2: _determine_stat_type 통합

**Day 1-2**: 패턴 매칭 엔진
- keywords/exclude_keywords
- 통합 로직

**Day 3**: Rate Limiter
- YAML 외부화

---

## 📊 예상 효과

### Before (현재)

```
하드코딩: 8개 위치
확장성: 제한적
유지보수: 코드 수정 필요
```

### After (개선)

```
하드코딩: 0-2개 (최소화)
확장성: 무한대 (YAML/API)
유지보수: 설정 파일 수정만
```

---

## 🎯 가장 시급한 개선

### 1. capability_to_metric (evidence_engine.py)

**이유**:
- ✅ Evidence Engine 핵심 로직
- ✅ 모든 Source에 영향
- ✅ cmis.yaml과 sync 필요

**개선**:
```python
# 현재: 하드코딩 15개
mapping = {"population_by_age": "MET-N_customers", ...}

# 개선: cmis.yaml에서 동적 생성
def _build_capability_mapping(self):
    mapping = {}
    for metric_id, spec in self.config.metrics.items():
        for source_cap in spec.direct_evidence_sources:
            if source_cap not in mapping:
                mapping[source_cap] = metric_id
    return mapping
```

---

## 📝 권장 조치

### 즉시 (이번 주)

1. ✅ **capability_to_metric 동적화** (2일)
   - cmis.yaml metrics_spec 활용
   - 단일 진실의 원천

### 다음 주

2. ⏳ **STAT_TABLES/KEY_STATISTICS YAML화** (3일)
   - config/sources/ 디렉토리
   - 확장성 확보

### 선택적

3. ⏳ **_determine_stat_type 통합** (2일)
   - 패턴 매칭
   - keywords 기반

---

**작성**: 2025-12-10
**발견**: 8개 하드코딩
**추천**: capability_to_metric 즉시 개선
