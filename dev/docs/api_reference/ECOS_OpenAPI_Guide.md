# ECOS (한국은행 경제통계시스템) OpenAPI 가이드

**작성일**: 2025-12-10  
**출처**: 한국은행 ECOS OpenAPI 개발명세서  
**API 문서**: https://ecos.bok.or.kr/api/  
**버전**: v1.0

---

## 📋 목차

1. [100대 통계지표 API](#1-100대-통계지표-api)
2. [서비스 통계 목록 API](#2-서비스-통계-목록-api)
3. [통계 조회 조건 설정 API](#3-통계-조회-조건-설정-api)
4. [통계 세부항목 목록 API](#4-통계-세부항목-목록-api)
5. [통계 메타 DB API](#5-통계-메타-db-api)
6. [통계 용어 사전 API](#6-통계-용어-사전-api)
7. [에러 코드](#7-에러-코드)
8. [주요 통계표 코드](#8-주요-통계표-코드)
9. [사용 예시](#9-사용-예시)

---

## 1. 100대 통계지표 API

### 서비스명
**KeyStatisticList** - 주요 경제 지표 조회 (가장 간단)

### 요청 URL

```
https://ecos.bok.or.kr/api/KeyStatisticList/{인증키}/{요청유형}/{언어}/{시작건수}/{종료건수}
```

### 요청 변수

| 항목명 | 필수 | 샘플 | 설명 |
|--------|------|------|------|
| 서비스명 | Y | KeyStatisticList | API 서비스명 |
| 인증키 | Y | sample | 한국은행 발급 인증키 |
| 요청유형 | Y | json | xml, json |
| 언어구분 | Y | kr | kr(국문), en(영문) |
| 요청시작건수 | Y | 1 | 시작 번호 |
| 요청종료건수 | Y | 10 | 끝 번호 |

### 출력값

| 항목명(국문) | 항목명(영문) | 샘플 | 설명 |
|-------------|-------------|------|------|
| 통계그룹명 | CLASS_NAME | 국민소득·경기·기업경영 | 통계그룹 |
| 통계명 | KEYSTAT_NAME | 경제성장률(전기대비) | 통계명 |
| 값 | DATA_VALUE | 1.9 | 값 |
| 시점 | CYCLE | 202003 | 최근 수록 시점 |
| 단위 | UNIT_NAME | %, 달러, 십억원 | 단위 |

### 테스트 URL

```
https://ecos.bok.or.kr/api/KeyStatisticList/sample/json/kr/1/100
```

### 주요 100대 지표 예시

| 통계명 | 값 (예시) | 단위 | 시점 |
|--------|-----------|------|------|
| GDP(명목, 계절조정) | 664424.9 | 십억원 | 2025Q3 |
| 경제성장률(실질, 전기대비) | 1.3 | % | 2025Q3 |
| 소비자물가지수 | 117.2 | 2020=100 | 202511 |
| 한국은행 기준금리 | 2.5 | % | 20251208 |
| 콜금리(익일물) | 2.513 | % | 20251209 |

---

## 2. 서비스 통계 목록 API

### 서비스명
**StatisticTableList** - 통계표 목록 조회

### 요청 URL

```
https://ecos.bok.or.kr/api/StatisticTableList/{인증키}/{요청유형}/{언어}/{시작}/{종료}/{통계표코드}
```

### 요청 변수

| 항목명 | 필수 | 샘플 | 설명 |
|--------|------|------|------|
| 서비스명 | Y | StatisticTableList | API 서비스명 |
| 인증키 | Y | sample | 한국은행 인증키 |
| 요청유형 | Y | json | xml, json |
| 언어구분 | Y | kr | kr, en |
| 요청시작건수 | Y | 1 | 시작 번호 |
| 요청종료건수 | Y | 10 | 끝 번호 |
| 통계표코드 | N | 102Y004 | 통계표코드 (선택) |

### 출력값

| 항목명(국문) | 항목명(영문) | 샘플 |
|-------------|-------------|------|
| 상위통계표코드 | P_STAT_CODE | 0000000004 |
| 통계표코드 | STAT_CODE | 102Y004 |
| 통계명 | STAT_NAME | 본원통화 구성내역 |
| 주기 | CYCLE | M (년, 분기, 월) |
| 검색가능여부 | SRCH_YN | Y |
| 출처 | ORG_NAME | 한국은행 |

### 테스트 URL

```
https://ecos.bok.or.kr/api/StatisticTableList/sample/json/kr/1/10/102Y004
```

---

## 3. 통계 조회 조건 설정 API ⭐

### 서비스명
**StatisticSearch** - 실제 통계 데이터 조회 (핵심!)

### 요청 URL

```
https://ecos.bok.or.kr/api/StatisticSearch/{인증키}/{요청유형}/{언어}/{시작}/{종료}/{통계표코드}/{주기}/{시작일자}/{종료일자}/{항목1}/{항목2}/{항목3}
```

### 요청 변수

| 항목명 | 필수 | 샘플 | 설명 |
|--------|------|------|------|
| 서비스명 | Y | StatisticSearch | API 서비스명 |
| 인증키 | Y | sample | 한국은행 인증키 |
| 요청유형 | Y | json | xml, json |
| 언어구분 | Y | kr | kr, en |
| 요청시작건수 | Y | 1 | 시작 번호 |
| 요청종료건수 | Y | 10 | 끝 번호 |
| 통계표코드 | Y | 200Y001 | 통계표코드 |
| 주기 | Y | A | A(년), Q(분기), M(월), D(일) |
| 검색시작일자 | Y | 2015 | 주기 형식 따름 |
| 검색종료일자 | Y | 2021 | 주기 형식 따름 |
| 통계항목코드1 | N | 10101 | 통계항목1 |
| 통계항목코드2 | N | ? | 통계항목2 |
| 통계항목코드3 | N | ? | 통계항목3 |

### 주기별 날짜 형식

| 주기 | 코드 | 날짜 형식 | 예시 |
|------|------|----------|------|
| 년 | A | YYYY | 2015 |
| 반년 | S | YYYYS1/S2 | 2015S1 |
| 분기 | Q | YYYYQ1-Q4 | 2015Q1 |
| 월 | M | YYYYMM | 201501 |
| 반월 | SM | YYYYMMSM | 201501SM |
| 일 | D | YYYYMMDD | 20150101 |

### 출력값

| 항목명(국문) | 항목명(영문) | 샘플 |
|-------------|-------------|------|
| 통계표코드 | STAT_CODE | 200Y001 |
| 통계명 | STAT_NAME | 주요지표(연간지표) |
| 통계항목코드1 | ITEM_CODE1 | 10101 |
| 통계항목명1 | ITEM_NAME1 | 국내총생산(명목, 원화표시) |
| 단위 | UNIT_NAME | 십억원 |
| 시점 | TIME | 2015 |
| 값 | DATA_VALUE | 1658020.4 |

### 테스트 URL

```
https://ecos.bok.or.kr/api/StatisticSearch/sample/json/kr/1/10/200Y001/A/2015/2021/10101/?/?
```

---

## 4. 통계 세부항목 목록 API

### 서비스명
**StatisticItemList** - 통계표의 항목 코드 조회

### 요청 URL

```
https://ecos.bok.or.kr/api/StatisticItemList/{인증키}/{요청유형}/{언어}/{시작}/{종료}/{통계표코드}
```

### 요청 변수

| 항목명 | 필수 | 샘플 | 설명 |
|--------|------|------|------|
| 서비스명 | Y | StatisticItemList | API 서비스명 |
| 인증키 | Y | sample | 한국은행 인증키 |
| 요청유형 | Y | json | xml, json |
| 언어구분 | Y | kr | kr, en |
| 요청시작건수 | Y | 1 | 시작 번호 |
| 요청종료건수 | Y | 10 | 끝 번호 |
| 통계표코드 | Y | 601Y002 | 통계표코드 |

### 출력값

| 항목명(국문) | 항목명(영문) | 샘플 |
|-------------|-------------|------|
| 통계표코드 | STAT_CODE | 601Y002 |
| 통계명 | STAT_NAME | 지역별 소비유형별 개인 신용카드 |
| 항목그룹코드 | GRP_CODE | Group1 |
| 항목그룹명 | GRP_NAME | 지역코드 |
| 통계항목코드 | ITEM_CODE | A |
| 통계항목명 | ITEM_NAME | 서울 |
| 주기 | CYCLE | M |
| 수록시작일자 | START_TIME | 200912 |
| 수록종료일자 | END_TIME | 202112 |
| 단위 | UNIT_NAME | 십억원 |

### 테스트 URL

```
https://ecos.bok.or.kr/api/StatisticItemList/sample/json/kr/1/10/043Y070/
```

---

## 5. 통계 메타 DB API

통계표의 메타데이터 조회 (통계 설명, 출처 등)

*상세 내용은 ECOS API 문서 참조*

---

## 6. 통계 용어 사전 API

통계 관련 용어 정의 조회

*상세 내용은 ECOS API 문서 참조*

---

## 7. 에러 코드

### 정보 메시지

| 코드 | 설명 |
|------|------|
| 100 | 인증키가 유효하지 않습니다. 인증키를 확인하십시오! |
| 200 | 해당하는 데이터가 없습니다. |

### 에러 메시지

| 코드 | 설명 |
|------|------|
| 100 | 필수 값이 누락되어 있습니다. |
| 101 | 주기와 다른 형식의 날짜 형식입니다. |
| 200 | 파일타입 값이 누락 혹은 유효하지 않습니다. |
| 300 | 조회건수 값이 누락되어 있습니다. |
| 301 | 조회건수 값의 타입이 유효하지 않습니다. |
| 400 | 검색범위 초과로 60초 TIMEOUT 발생 |
| 500 | 서버 오류 (서비스를 찾을 수 없음) |
| 600 | DB Connection 오류 |
| 601 | SQL 오류 |
| 602 | 과도한 OpenAPI 호출로 이용 제한 |

---

## 8. 주요 통계표 코드

### GDP 관련

| 통계표코드 | 항목코드 | 통계명 | 주기 |
|-----------|---------|--------|------|
| 200Y001 | 10101 | GDP(명목, 원화표시) | A (년) |
| 200Y001 | 10102 | GDP(실질) | A |
| 200Y001 | 10103 | 경제성장률(전년대비) | A |

### 물가 관련

| 통계표코드 | 항목코드 | 통계명 | 주기 |
|-----------|---------|--------|------|
| 901Y009 | 0 | 소비자물가지수 | M (월) |

### 금리 관련

| 통계표코드 | 항목코드 | 통계명 | 주기 |
|-----------|---------|--------|------|
| 722Y001 | 0101000 | 한국은행 기준금리 | D (일) |

*참고: 100대 통계지표 API는 통계표코드 불필요 (자동 조회)*

---

## 9. 사용 예시

### Example 1: 100대 통계지표 조회 (권장)

```python
import requests

url = "https://ecos.bok.or.kr/api/KeyStatisticList/YOUR_KEY/json/kr/1/100"

response = requests.get(url)
data = response.json()

# 100대 지표 전체
rows = data["KeyStatisticList"]["row"]

# GDP 찾기
for row in rows:
    if "GDP" in row["KEYSTAT_NAME"]:
        print(f"{row['KEYSTAT_NAME']}: {row['DATA_VALUE']} {row['UNIT_NAME']}")

# 출력:
# GDP(명목, 계절조정): 664424.9 십억원
# 경제성장률(실질, 전기대비): 1.3 %
```

---

### Example 2: 통계 조회 조건 설정 (상세 조회)

```python
# GDP 2015-2021 조회
url = (
    "https://ecos.bok.or.kr/api/StatisticSearch/"
    "YOUR_KEY/json/kr/1/10/"
    "200Y001/A/2015/2021/10101/?/?"
)

response = requests.get(url)
data = response.json()

# 시계열 데이터
rows = data["StatisticSearch"]["row"]
for row in rows:
    print(f"{row['TIME']}: {row['DATA_VALUE']} {row['UNIT_NAME']}")
```

---

### Example 3: 통계 세부항목 목록 조회

```python
# 통계표 601Y002의 항목 목록
url = (
    "https://ecos.bok.or.kr/api/StatisticItemList/"
    "YOUR_KEY/json/kr/1/100/601Y002"
)

response = requests.get(url)
data = response.json()

# 항목 목록
items = data["StatisticItemList"]["row"]
for item in items:
    print(f"{item['ITEM_CODE']}: {item['ITEM_NAME']}")
```

---

## 10. CMIS 구현 (ECOSSource)

### 현재 구현 방식

**사용 API**: KeyStatisticList (100대 통계지표)

**이유**:
- ✅ 가장 간단 (통계표코드, 항목코드 불필요)
- ✅ 주요 지표 모두 포함
- ✅ 최신 데이터 자동 제공

```python
class ECOSSource(BaseDataSource):
    KEY_STATISTICS = {
        "gdp": {
            "keyword": "GDP(명목, 계절조정)",
            "name": "GDP (명목)",
            "unit": "십억원"
        },
        "cpi": {
            "keyword": "소비자물가지수",
            "name": "CPI",
            "unit": "지수"
        }
    }
    
    def _fetch_key_statistic(self, keyword, context):
        # KeyStatisticList API 호출
        url = f"{base_url}/KeyStatisticList/{key}/json/kr/1/100"
        data = requests.get(url).json()
        
        # Keyword로 필터링
        rows = data["KeyStatisticList"]["row"]
        matched = [r for r in rows if keyword in r["KEYSTAT_NAME"]]
        
        return matched
```

---

## 11. API 선택 가이드

### KeyStatisticList (100대 지표)

**사용 시기**:
- ✅ GDP, CPI, 금리 등 주요 지표
- ✅ 최신 데이터만 필요
- ✅ 간단한 조회

**장점**:
- 통계표코드 불필요
- 항목코드 불필요
- 한 번 호출로 100개 지표

**단점**:
- 시계열 조회 불가 (최신 시점만)
- 100대 지표에만 한정

---

### StatisticSearch (상세 조회)

**사용 시기**:
- 시계열 데이터 필요 (2015-2021)
- 특정 항목 지정
- 세밀한 조건 설정

**장점**:
- 시계열 조회 가능
- 모든 통계표 지원
- 항목별 선택 가능

**단점**:
- 통계표코드, 항목코드 필요
- 파라미터 복잡

---

### StatisticItemList (메타 조회)

**사용 시기**:
- 통계표의 항목 코드 확인
- 항목 목록 탐색

**장점**:
- 항목 구조 파악

**단점**:
- 실제 데이터 조회 불가

---

## 12. 우리 구현 (ECOSSource)

### 현재 (Phase 1)

```python
# KeyStatisticList 사용
# - GDP, CPI, 금리 등 5개 지표
# - 최신 데이터만
```

### 향후 확장 (Phase 2)

```python
# StatisticSearch 추가
# - 시계열 데이터 (2015-2024)
# - 더 많은 통계표
# - 세부 항목 조회
```

---

## 13. 참고 링크

- **API 신청**: https://ecos.bok.or.kr/api/
- **통계 검색**: https://ecos.bok.or.kr/
- **통계코드 검색**: https://ecos.bok.or.kr/api/#/DevGuide/StatisticalCodeSearch
- **개발 가이드**: https://ecos.bok.or.kr/api/#/DevGuide

---

## 14. 빠른 시작

### 1단계: API 키 발급

1. https://ecos.bok.or.kr/api/ 접속
2. 회원가입 (무료)
3. 인증키 신청 (즉시 발급)

### 2단계: 100대 지표 테스트

```bash
curl "https://ecos.bok.or.kr/api/KeyStatisticList/YOUR_KEY/json/kr/1/10"
```

### 3단계: Python 구현

```python
from cmis_core.evidence.ecos_source import ECOSSource
from cmis_core.types import EvidenceRequest

source = ECOSSource()

request = EvidenceRequest(
    request_id="test-gdp",
    request_type="metric",
    metric_id="MET-GDP",
    context={"region": "KR", "year": 2024}
)

record = source.fetch(request)
print(f"GDP: {record.value:,.1f} {record.metadata['unit']}")
# 출력: GDP: 664,424.9 십억원
```

---

**작성**: 2025-12-10  
**검증**: GDP, CPI, 금리 (14개 테스트 통과)  
**형식**: JSON (권장)
