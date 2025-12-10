# OFFICIAL Tier 확장 가능성 분석

**작성일**: 2025-12-10  
**목적**: OFFICIAL tier 소스 확장 전략 수립

---

## 🔍 현황 분석

### 현재 OFFICIAL Tier (2개만)

| Source | 제공 데이터 | API | 상태 |
|--------|------------|-----|------|
| **KOSIS** | 인구, 가구, 거시 통계 | ✅ | 작동 중 |
| **DART** | 재무제표, 공시 | ✅ | 작동 중 |

**문제**: 
- 범위 협소 (인구 + 재무만)
- 산업/시장 데이터 부족
- 글로벌 데이터 없음

---

## 🎯 확장 가능 OFFICIAL 소스

### Tier 1: 한국 정부 공식 통계 (즉시 확장 가능)

#### 1. 한국은행 경제통계 (ECOS)

**제공 데이터**:
- GDP, 물가지수, 금리
- 산업별 생산지수
- 국제수지, 환율
- 통화/신용 통계

**API**: ✅ OpenAPI 제공  
**접근성**: ✅ 무료, API 키 발급 간단  
**난이도**: 🟢 낮음 (KOSIS 유사)

**예시 Metric**:
- MET-GDP
- MET-CPI (소비자물가지수)
- MET-Interest_rate

**우선순위**: ⭐⭐⭐⭐⭐ (최우선)

---

#### 2. 공공데이터포털 (data.go.kr)

**제공 데이터**:
- 정부 부처별 통계 (100+ 기관)
- 산업 통계 (제조, 서비스, IT 등)
- 지역 통계
- 기업 통계

**API**: ✅ OpenAPI 제공  
**접근성**: ✅ 무료, 통합 API 키  
**난이도**: 🟡 중간 (API 통합 필요)

**예시 Metric**:
- MET-Industry_production
- MET-Regional_employment
- MET-SME_statistics

**우선순위**: ⭐⭐⭐⭐ (높음)

---

#### 3. 금융감독원 금융통계정보시스템

**제공 데이터**:
- 금융회사 통계
- 보험/증권/은행 통계
- 금융 소비자 통계

**API**: ⚠️ 제한적  
**접근성**: 🟡 웹 스크래핑 필요할 수 있음  
**난이도**: 🟡 중간

**예시 Metric**:
- MET-Financial_sector_stats
- MET-Insurance_market

**우선순위**: ⭐⭐⭐ (중간)

---

#### 4. 중소벤처기업부 통계

**제공 데이터**:
- 중소기업 현황
- 창업 통계
- 벤처투자 통계

**API**: ⚠️ 제한적  
**접근성**: 🟡 공공데이터포털 통합  
**난이도**: 🟡 중간

**예시 Metric**:
- MET-Startup_count
- MET-VC_investment

**우선순위**: ⭐⭐⭐ (중간)

---

### Tier 2: 글로벌 공식 통계 (중기 확장)

#### 5. OECD (경제협력개발기구)

**제공 데이터**:
- 회원국 경제 지표
- 교육, 보건, 노동 통계
- 산업별 벤치마크

**API**: ✅ OECD.Stat API  
**접근성**: ✅ 무료  
**난이도**: 🟡 중간 (SDMX 형식)

**예시 Metric**:
- MET-OECD_GDP_per_capita
- MET-Education_expenditure_ratio
- MET-R&D_intensity

**우선순위**: ⭐⭐⭐⭐ (높음, 국제 비교)

---

#### 6. World Bank (세계은행)

**제공 데이터**:
- 국가별 개발 지표
- 거시경제 통계
- 산업/인프라 데이터

**API**: ✅ World Bank API  
**접근성**: ✅ 무료  
**난이도**: 🟢 낮음 (JSON)

**예시 Metric**:
- MET-GDP_growth
- MET-Population_growth
- MET-Internet_penetration

**우선순위**: ⭐⭐⭐⭐ (높음)

---

#### 7. IMF (국제통화기금)

**제공 데이터**:
- 국가별 경제 전망
- 금융 통계
- 환율, 준비금

**API**: ✅ IMF Data API  
**접근성**: ✅ 무료  
**난이도**: 🟡 중간

**예시 Metric**:
- MET-IMF_GDP_forecast
- MET-Exchange_rate

**우선순위**: ⭐⭐⭐ (중간)

---

#### 8. UN Data

**제공 데이터**:
- 국제 통계
- 인구, 보건, 교육
- 지속가능발전목표 (SDGs)

**API**: ✅ UN Data API  
**접근성**: ✅ 무료  
**난이도**: 🟡 중간

**우선순위**: ⭐⭐⭐ (중간)

---

### Tier 3: 산업별 공식 데이터 (장기)

#### 9. 특허청 (KIPRIS)

**제공 데이터**:
- 특허, 상표, 디자인 통계
- 기술 분야별 출원 현황
- 기업별 IP 포트폴리오

**API**: ✅ OpenAPI  
**접근성**: ✅ 무료  
**난이도**: 🟡 중간

**예시 Metric**:
- MET-Patent_count
- MET-Technology_activity

**우선순위**: ⭐⭐ (낮음, 특수 목적)

---

#### 10. 교육부 교육통계서비스 (KESS)

**제공 데이터**:
- 학교 현황
- 학생/교원 통계
- 교육 예산

**API**: ⚠️ 제한적  
**접근성**: 🟡 공공데이터포털  
**난이도**: 🟡 중간

**예시 Metric**:
- MET-Student_count
- MET-Education_budget

**우선순위**: ⭐⭐ (낮음)

---

## 📊 확장 우선순위 매트릭스

### 즉시 확장 (Phase 4, 1-2주)

| Source | 데이터 가치 | API 품질 | 난이도 | 우선순위 |
|--------|------------|----------|--------|----------|
| **한국은행 ECOS** | ⭐⭐⭐⭐⭐ | ✅ 우수 | 🟢 낮음 | **1순위** |
| **공공데이터포털** | ⭐⭐⭐⭐ | ✅ 좋음 | 🟡 중간 | **2순위** |
| **World Bank** | ⭐⭐⭐⭐ | ✅ 우수 | 🟢 낮음 | **3순위** |
| **OECD** | ⭐⭐⭐⭐ | ✅ 좋음 | 🟡 중간 | **4순위** |

**예상 효과**:
- OFFICIAL tier 소스: 2개 → 6개 (3배)
- 커버리지: 인구+재무 → 경제+산업+국제

---

### 중기 확장 (Phase 5-6, 1-2개월)

| Source | 데이터 가치 | API 품질 | 난이도 |
|--------|------------|----------|--------|
| 금융감독원 | ⭐⭐⭐ | ⚠️ 제한 | 🟡 중간 |
| IMF | ⭐⭐⭐ | ✅ 좋음 | 🟡 중간 |
| UN Data | ⭐⭐⭐ | ✅ 좋음 | 🟡 중간 |
| 중소벤처기업부 | ⭐⭐⭐ | ⚠️ 제한 | 🟡 중간 |

---

## 🚀 구현 계획

### Phase 4A: 한국은행 ECOS (1주)

**작업**:
1. ECOS API 연동
   - API 문서 분석
   - Connector 구현 (KOSIS 패턴 재사용)
   
2. 주요 지표 매핑
   - GDP, CPI, 금리
   - 산업생산지수
   - 통화량

3. 테스트
   - API 호출 테스트
   - Metric 계산 통합

**예상 코드**: 300-400 라인

---

### Phase 4B: 공공데이터포털 (1주)

**작업**:
1. data.go.kr API 연동
   - 통합 API 키
   - 부처별 API 매핑

2. 산업 통계 우선
   - 제조업 통계
   - 서비스업 통계
   - IT 산업 통계

3. 테스트

**예상 코드**: 400-500 라인

---

### Phase 4C: World Bank (3일)

**작업**:
1. World Bank API 연동
   - JSON API (간단)
   - 국가별 지표 조회

2. 주요 지표
   - GDP, 인구 성장률
   - 인터넷 보급률
   - 교육 지표

3. 테스트

**예상 코드**: 200-300 라인

---

### Phase 4D: OECD (5일)

**작업**:
1. OECD.Stat API 연동
   - SDMX 파싱 (복잡)
   - 지표 코드 매핑

2. 주요 지표
   - 교육 지출
   - R&D 투자
   - 노동 통계

3. 테스트

**예상 코드**: 400-500 라인

---

## 📊 예상 효과

### Before (현재)

```
OFFICIAL Tier: 2개
- KOSIS (인구, 가구)
- DART (재무제표)

커버리지: 제한적
```

### After (Phase 4 완료)

```
OFFICIAL Tier: 6개
- KOSIS (인구, 가구)
- DART (재무제표)
- ECOS (경제 지표)
- 공공데이터 (산업 통계)
- World Bank (글로벌)
- OECD (국제 비교)

커버리지: 포괄적
```

---

## 💡 각 소스별 상세 분석

### 1. 한국은행 ECOS (최우선)

**API 정보**:
- URL: `https://ecos.bok.or.kr/api/`
- 인증: API 키 (무료 발급)
- 형식: JSON, XML
- 문서: 상세한 개발 가이드

**주요 통계표**:
```
- 200Y001: GDP (국내총생산)
- 901Y009: CPI (소비자물가지수)
- 722Y001: 산업생산지수
- 010Y002: 통화량
- 036Y001: 예금은행 금리
```

**Metric 매핑**:
```python
ECOS_TABLES = {
    "gdp": {
        "stat_code": "200Y001",
        "item_code": "10101",  # 명목 GDP
        "cycle": "A"  # Annual
    },
    "cpi": {
        "stat_code": "901Y009",
        "item_code": "0",  # 전체
        "cycle": "M"  # Monthly
    }
}
```

**구현 유사도**: KOSIS와 90% 유사 (재사용 가능)

---

### 2. 공공데이터포털 (data.go.kr)

**특징**:
- 100+ 정부 기관 데이터 통합
- 단일 API 키로 접근
- 산업별 세분화된 통계

**주요 카테고리**:
```
1. 산업/경제
   - 제조업 생산 통계
   - 서비스업 매출 통계
   - IT/SW 산업 통계
   
2. 기업/창업
   - 기업 현황
   - 창업 통계
   - 폐업 통계

3. 고용/노동
   - 취업자 수
   - 임금 통계
   - 직종별 통계
```

**구현 전략**:
```python
class DataGovSource(BaseDataSource):
    """공공데이터포털 통합 Source"""
    
    DATASETS = {
        "manufacturing_production": {
            "service_key": "공공데이터포털_API_KEY",
            "endpoint": "/manufacturing/production",
            "params": {...}
        }
    }
```

**난이도**: 중간 (각 API마다 형식 다름)

---

### 3. World Bank

**API 정보**:
- URL: `https://api.worldbank.org/v2/`
- 인증: 불필요 (Public)
- 형식: JSON, XML
- 문서: 매우 상세

**주요 지표**:
```
- NY.GDP.MKTP.CD: GDP (current US$)
- SP.POP.TOTL: Population, total
- IT.NET.USER.ZS: Internet users (% of population)
- SE.XPD.TOTL.GD.ZS: Education expenditure (% of GDP)
```

**쿼리 예시**:
```
GET /v2/country/KR/indicator/NY.GDP.MKTP.CD
→ Korea GDP time series
```

**구현 난이도**: 낮음 (JSON API, 간단)

---

### 4. OECD

**API 정보**:
- URL: `https://stats.oecd.org/restsdmx/`
- 인증: 불필요
- 형식: SDMX (복잡), JSON (간단)
- 문서: 상세

**주요 지표**:
```
- MEI: 주요 경제 지표
- EDU: 교육 통계
- SNA: 국민계정
- R&D: 연구개발 통계
```

**난이도**: 중간 (SDMX 파싱 복잡)

---

## 🎯 확장 전략

### 단계별 로드맵

#### Phase 4A: 한국은행 ECOS (즉시, 1주)

**목표**: 경제 지표 OFFICIAL tier 확보

**작업**:
1. ECOS Connector 구현
2. 5개 핵심 지표 (GDP, CPI, 금리, 산업생산, 통화량)
3. 10+ 테스트

**효과**: 거시경제 데이터 → OFFICIAL tier

---

#### Phase 4B: World Bank (1주 후, 3일)

**목표**: 글로벌 비교 데이터

**작업**:
1. World Bank Connector
2. 5개 지표 (GDP, 인구, 인터넷, 교육, R&D)
3. 5+ 테스트

**효과**: 국제 벤치마크 → OFFICIAL tier

---

#### Phase 4C: 공공데이터포털 (2주 후, 1주)

**목표**: 산업별 세분화 통계

**작업**:
1. data.go.kr 통합 Connector
2. 3개 산업 (제조, 서비스, IT)
3. 10+ 테스트

**효과**: 산업 통계 → OFFICIAL tier

---

#### Phase 4D: OECD (3주 후, 5일)

**목표**: 국제 비교 벤치마크

**작업**:
1. OECD.Stat Connector
2. 5개 지표 (교육, R&D, 노동, 산업)
3. 5+ 테스트

**효과**: OECD 벤치마크 → OFFICIAL tier

---

## 📊 예상 최종 구성

### OFFICIAL Tier (6개 → 10+)

**Core (즉시 확장)**:
1. KOSIS (현재) - 인구, 가구
2. DART (현재) - 재무제표
3. **ECOS (신규)** - 경제 지표
4. **World Bank (신규)** - 글로벌 비교

**Extended (중기)**:
5. **공공데이터 (신규)** - 산업 통계
6. **OECD (신규)** - 국제 벤치마크

**Specialized (장기)**:
7. 금융감독원 - 금융 통계
8. 중소벤처기업부 - 창업/벤처
9. 특허청 - IP 통계
10. 교육부 - 교육 통계

---

## 🎯 Metric 커버리지 확장

### Before (현재)

| Metric 카테고리 | OFFICIAL 가능 | COMMERCIAL 의존 |
|-----------------|---------------|-----------------|
| 인구/가구 | ✅ KOSIS | - |
| 기업 재무 | ✅ DART | - |
| 시장 규모 | ❌ | ✅ Google |
| 경제 지표 | ❌ | ✅ Google |
| 산업 통계 | ❌ | ✅ Google |
| 국제 비교 | ❌ | ✅ Google |

**OFFICIAL 커버리지**: 30%

---

### After (Phase 4 완료)

| Metric 카테고리 | OFFICIAL 가능 | COMMERCIAL 의존 |
|-----------------|---------------|-----------------|
| 인구/가구 | ✅ KOSIS | - |
| 기업 재무 | ✅ DART | - |
| 시장 규모 | ⚠️ 부분 | ✅ Google (보조) |
| 경제 지표 | ✅ ECOS | - |
| 산업 통계 | ✅ 공공데이터 | ✅ Google (보조) |
| 국제 비교 | ✅ World Bank, OECD | - |

**OFFICIAL 커버리지**: 70%+

---

## 💎 구현 패턴 재사용

### KOSIS 패턴 활용

```python
class ECOSSource(BaseDataSource):
    """한국은행 ECOS (KOSIS 패턴 재사용)"""
    
    STAT_TABLES = {
        "gdp": {
            "stat_code": "200Y001",
            "item_code": "10101"
        }
    }
    
    def _fetch_stat_data(self, stat_code, item_code, context):
        # KOSIS와 90% 유사
        params = {
            'keycode': self.api_key,
            'type': 'json',
            'lang': 'kr',
            'stat_code': stat_code,
            'item_code': item_code,
            'start_date': context.get('year'),
            'end_date': context.get('year')
        }
        # ...
```

**재사용률**: 70-90%

---

## 📝 구현 예상 코드량

### Source별

| Source | 예상 라인 | 재사용 | 테스트 |
|--------|-----------|--------|--------|
| ECOS | 400 | 70% from KOSIS | 15 |
| 공공데이터 | 500 | 60% from KOSIS | 20 |
| World Bank | 300 | 50% | 10 |
| OECD | 500 | 40% (SDMX) | 10 |

**총계**: 1,700 라인 (프로덕션)  
**테스트**: 55개

---

## 🎯 권장 사항

### 즉시 착수 (Phase 4A)

**한국은행 ECOS** (1주 작업)

**이유**:
1. ⭐ 데이터 가치 최고 (경제 지표)
2. ✅ API 품질 우수
3. 🟢 구현 난이도 낮음 (KOSIS 유사)
4. 🚀 즉시 효과 (거시경제 → OFFICIAL)

**예상 효과**:
```
MET-GDP: OFFICIAL (0.95)
MET-CPI: OFFICIAL (0.95)
MET-Interest_rate: OFFICIAL (0.95)

COMMERCIAL 의존도 감소
Evidence-first 철학 강화
```

---

### 중기 (Phase 4B-D)

**World Bank → 공공데이터 → OECD** 순서

**이유**:
- World Bank: 간단, 빠른 효과
- 공공데이터: 산업 통계 (한국 특화)
- OECD: 복잡하지만 가치 높음

---

## 📊 ROI 분석

### ECOS 추가 시

**투자**:
- 개발: 1주 (1명)
- 코드: 400 라인
- 테스트: 15개

**효과**:
- OFFICIAL tier: +50% 확장
- 경제 Metric: COMMERCIAL → OFFICIAL
- API 호출 비용: -30% (Early Return)
- Confidence: 0.7 → 0.95 (+36%)

**ROI**: 매우 높음 ⭐⭐⭐⭐⭐

---

## 🚀 추천 실행 계획

### 즉시 (이번 주)

1. ✅ **한국은행 ECOS** 착수
   - API 키 발급
   - Connector POC
   - GDP, CPI 테스트

### 다음 주

2. ✅ **World Bank** 구현
   - 간단, 빠른 효과

### 2주 후

3. ✅ **공공데이터포털** 구현
   - 산업 통계 확보

### 1개월 후

4. ✅ **OECD** 구현
   - 국제 벤치마크 완성

**4주 후 목표**: OFFICIAL tier 6개, 커버리지 70%

---

**작성**: 2025-12-10  
**결론**: 한국은행 ECOS 즉시 착수 권장  
**예상 효과**: OFFICIAL 커버리지 3배 확장

