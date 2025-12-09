# KOSIS OpenAPI 가이드

**작성일**: 2025-12-10
**출처**: KOSIS 공식 개발 가이드
**URL**: https://kosis.kr/openapi/file/openApi_manual_v1.0.pdf

---

## 1. 통계목록

### 요청URL
```
https://kosis.kr/openapi/statisticsList.do?method=getList
```

### 요청변수

| 변수 | 타입 | 설명 | 비고 |
|------|------|------|------|
| apiKey | String | 발급된 인증 key | 필수 |
| vwCd | String | 서비스뷰 코드 | 필수 |
| parentId | String | 시작목록 ID | 필수 |
| format | String | 결과 유형(json) | 필수 |
| content | String | 헤더 유형(html, json) | 선택 |

**서비스뷰 코드**:
- MT_ZTITLE: 국내통계 주제별
- MT_OTITLE: 국내통계 기관별
- MT_GTITLE01: e-지방지표(주제별)
- MT_RTITLE: 국제통계
- 기타

### 출력결과

| 변수 | 설명 | 형식 |
|------|------|------|
| VW_CD | 서비스뷰ID | VARCHAR2(40) |
| LIST_ID | 목록ID | VARCHAR2(40) |
| ORG_ID | 기관코드 | VARCHAR2(40) |
| TBL_ID | 통계표ID | VARCHAR2(40) |
| TBL_NM | 통계표명 | VARCHAR2(300) |

---

## 2. 통계자료

### 2.1 자료등록 방법

**요청URL**:
```
https://kosis.kr/openapi/statisticsData.do?method=getList
```

**요청변수**:

| 변수 | 타입 | 설명 | 비고 |
|------|------|------|------|
| apiKey | String | 인증 key | 필수 |
| userStatsId | String | 사용자 등록 통계표 | 필수 |
| prdSe | String | 수록주기 | 필수 |
| startPrdDe | String | 시작수록시점 | 선택 |
| endPrdDe | String | 종료수록시점 | 선택 |
| newEstPrdCnt | String | 최근수록시점 개수 | 선택 |
| format | String | 결과 유형(json) | 필수 |

---

### 2.2 통계표선택 방법

**요청URL**:
```
https://kosis.kr/openapi/Param/statisticsParameterData.do?method=getList
```

**요청변수**:

| 변수 | 타입 | 설명 | 비고 |
|------|------|------|------|
| apiKey | String | 인증 key | 필수 |
| orgId | String | 기관 ID | 필수 |
| tblId | String | 통계표 ID | 필수 |
| objL1 | String | 분류1 (첫번째 분류코드) | 필수 |
| objL2~objL8 | String | 분류2~8 | 선택 |
| itmId | String | 항목 | 필수 |
| prdSe | String | 수록주기 | 필수 |
| startPrdDe | String | 시작수록시점 | 선택 |
| endPrdDe | String | 종료수록시점 | 선택 |
| loadGubun | String | 조회구분 | **필수** (2) |
| format | String | 결과 유형(json) | 필수 |

**중요**: `loadGubun=2` 필수!

### 출력결과

| 변수 | 설명 | 형식 |
|------|------|------|
| ORG_ID | 기관코드 | VARCHAR2(40) |
| TBL_ID | 통계표ID | VARCHAR2(40) |
| TBL_NM | 통계표명 | VARCHAR2(300) |
| C1~C8 | 분류값 ID1~8 | VARCHAR2(40) |
| C1_NM~C8_NM | 분류값 명1~8 | VARCHAR2(3000) |
| ITM_ID | 항목 ID | VARCHAR2(40) |
| ITM_NM | 항목명 | VARCHAR2(3000) |
| UNIT_NM | 단위명 | VARCHAR2(1000) |
| PRD_DE | 수록시점 | VARCHAR2(8) |
| **DT** | **수치값** | VARCHAR2(100) |

---

## 3. 주기코드 및 시점

### 주기별 시점 형식

| 주기 | prdSe | 시점 형식 | 예시 |
|------|-------|----------|------|
| 일 | D | YYYYMMDD | 20140101 |
| 월 | M | YYYYMM | 201401 |
| 분기 | Q | YYYYQQ | 201401 |
| 반기 | S | YYYYHH | 201401 |
| **년** | **Y** | **YYYY** | **2014** |
| 부정기 | IR | YYYY, YYYYMM, YYYYMMDD | 2014 |

---

## 4. KOSIS 통합검색

### 요청URL
```
https://kosis.kr/openapi/statisticsSearch.do?method=getList
```

### 요청변수

| 변수 | 타입 | 설명 |
|------|------|------|
| apiKey | String | 인증 key |
| searchNm | String | 검색명 |
| orgId | String | 기관코드 (선택) |
| sort | String | 정렬 (RANK/DATE) |
| format | String | json |

---

## 5. 실제 작동 예제

### 예제 1: 인구 통계 조회

```python
import requests
import json
import re

api_key = "your-api-key"
url = 'https://kosis.kr/openapi/Param/statisticsParameterData.do'

params = {
    'method': 'getList',
    'apiKey': api_key,
    'orgId': '101',           # 통계청
    'tblId': 'DT_1B04005N',   # 인구 통계표
    'itmId': 'T2+',           # 인구수 (+ 필수!)
    'objL1': '00+',           # 전국 (+ 필수!)
    'objL2': 'ALL',           # 전체
    'objL3': '',
    'objL4': '',
    'objL5': '',
    'objL6': '',
    'objL7': '',
    'objL8': '',
    'format': 'json',
    'jsonVD': 'Y',            # Value Description
    'prdSe': 'Y',             # 연도
    'startPrdDe': '2024',
    'endPrdDe': '2024',
    'loadGubun': '2'          # 필수!
}

response = requests.get(url, params=params)

# JavaScript JSON 파싱
text = response.text
text_fixed = re.sub(r'([{,])(\w+):', r'\1"\2":', text)
data = json.loads(text_fixed)

# 결과
for item in data:
    print(f"시점: {item['PRD_DE']}")
    print(f"지역: {item['C1_NM']}")
    print(f"값: {item['DT']}")
    print(f"단위: {item['UNIT_NM']}")
```

**결과**: 51,217,221명 (2024 전국 인구)

---

### 예제 2: 가구 통계 조회

```python
params = {
    'method': 'getList',
    'apiKey': api_key,
    'orgId': '101',
    'tblId': 'DT_1B04005N',   # 가구 통계표
    'itmId': 'T2+T3+T4+',     # 여러 항목 (+ 구분)
    'objL1': '31+',           # 경북
    'objL2': 'ALL',
    'format': 'json',
    'jsonVD': 'Y',
    'prdSe': 'M',             # 월간
    'startPrdDe': '202104',
    'endPrdDe': '202104',
    'loadGubun': '2'
}
```

---

## 6. 주요 통계표 ID

### 인구/가구

| 통계표명 | tblId | 설명 |
|---------|-------|------|
| 주민등록인구 | DT_1B04006 | 시군구/성/연령별 |
| 주민등록연앙인구 | DT_1B040M1 | 연앙인구 |
| 가구 통계 | DT_1B04005N | 가구 수 |

### 경제/산업

| 통계표명 | tblId | 설명 |
|---------|-------|------|
| GDP | - | 확인 필요 |
| 산업별 생산 | - | 확인 필요 |

---

## 7. JavaScript JSON 파싱

### 문제

KOSIS는 `jsonVD=Y` 사용 시 JavaScript 형식 반환:
```javascript
{ORG_ID:"101",TBL_NM:"인구통계"}  // 키에 따옴표 없음
```

### 해결

정규식으로 변환:
```python
import re
import json

# JavaScript → JSON
text_fixed = re.sub(r'([{,])(\w+):', r'\1"\2":', text)
data = json.loads(text_fixed)
```

---

## 8. 주의사항

### 필수 파라미터

```python
# ✅ 필수
loadGubun = '2'      # 조회구분 (필수!)
itmId = 'T2+'        # + 필수!
objL1 = '00+'        # + 필수!
objL2 = 'ALL'        # 필수!

# ❌ 누락 시
Error 20: 필수요청변수값이 누락되었습니다.
```

### 데이터 제한

- 최대 40,000건/호출
- 초과 시: Error 31

---

## 9. 참고 링크

- 공식 사이트: https://kosis.kr/openapi/
- 개발 가이드: https://kosis.kr/openapi/file/openApi_manual_v1.0.pdf
- 활용 신청: https://kosis.kr/openapi/index/index.jsp

---

**작성**: 2025-12-10
**검증**: 2024년 인구 51,217,221명 (성공)
**상태**: JSON 형식 사용, 기본 조회 작동
