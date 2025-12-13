# KOSIS OpenAPI 가이드

**작성일**: 2025-12-10
**출처**: https://kosis.kr/openapi/file/openApi_manual_v1.0.pdf
**버전**: v1.0

---

## 1. 통계목록 API

### 요청 URL
```
https://kosis.kr/openapi/statisticsList.do?method=getList
```

### 요청 변수

| 변수 | 타입 | 설명 | 필수 |
|------|------|------|------|
| apiKey | String | 발급된 인증 key | 필수 |
| vwCd | String | 서비스뷰 코드 | 필수 |
| parentId | String | 시작목록 ID | 필수 |
| format | String | 결과 유형(json) | 필수 |
| content | String | 헤더 유형(html, json) | 선택 |

### 서비스뷰 코드 (vwCd)

```
MT_ZTITLE        : 국내통계 주제별
MT_OTITLE        : 국내통계 기관별
MT_GTITLE01      : e-지방지표(주제별)
MT_GTITLE02      : e-지방지표(지역별)
MT_CHOSUN_TITLE  : 광복이전통계(1908~1943)
MT_HANKUK_TITLE  : 대한민국통계연감
MT_STOP_TITLE    : 작성중지통계
MT_RTITLE        : 국제통계
MT_BUKHAN        : 북한통계
MT_TM1_TITLE     : 대상별통계
MT_TM2_TITLE     : 이슈별통계
MT_ETITLE        : 영문 KOSIS
```

### 출력 결과

| 필드 | 설명 | 형식 |
|------|------|------|
| VW_CD | 서비스뷰ID | VARCHAR2(40) |
| VW_NM | 서비스뷰명 | VARCHAR2(300) |
| LIST_ID | 목록ID | VARCHAR2(40) |
| LIST_NM | 목록명 | VARCHAR2(300) |
| ORG_ID | 기관코드 | VARCHAR2(40) |
| TBL_ID | 통계표ID | VARCHAR2(40) |
| TBL_NM | 통계표명 | VARCHAR2(300) |

---

## 2. 통계자료 API

### 방법 1: 자료등록 방법

**요청 URL**:
```
https://kosis.kr/openapi/statisticsData.do?method=getList
```

**요청 변수**:

| 변수 | 타입 | 설명 | 필수 |
|------|------|------|------|
| apiKey | String | 인증 key | 필수 |
| userStatsId | String | 사용자 등록 통계표 | 필수 |
| prdSe | String | 수록주기 | 필수 |
| startPrdDe | String | 시작 수록시점 | 선택 |
| endPrdDe | String | 종료 수록시점 | 선택 |
| newEstPrdCnt | String | 최근 수록시점 개수 | 선택 |
| format | String | 결과 유형(json) | 필수 |

---

### 방법 2: 통계표선택 방법 ⭐

**요청 URL**:
```
https://kosis.kr/openapi/Param/statisticsParameterData.do?method=getList
```

**요청 변수**:

| 변수 | 타입 | 설명 | 필수 |
|------|------|------|------|
| apiKey | String | 인증 key | 필수 |
| orgId | String | 기관 ID | 필수 |
| tblId | String | 통계표 ID | 필수 |
| **objL1** | String | **분류1 (첫번째 분류코드)** | **필수** |
| objL2~objL8 | String | 분류2~8 | 선택 |
| **itmId** | String | **항목** | **필수** |
| prdSe | String | 수록주기 | 필수 |
| startPrdDe | String | 시작 수록시점 | 선택 |
| endPrdDe | String | 종료 수록시점 | 선택 |
| newEstPrdCnt | String | 최근 수록시점 개수 | 선택 |
| **loadGubun** | String | **조회구분** | **필수!** |
| format | String | 결과 유형(json) | 필수 |

**핵심 파라미터** (발견):
```python
# 필수 (누락 시 Error 20)
loadGubun = '2'      # ← 매우 중요!
itmId = 'T2+'        # + 필수!
objL1 = '00+'        # + 필수!
objL2 = 'ALL'        # 필수!
```

---

### 출력 변수

| 변수 | 설명 | 형식 |
|------|------|------|
| ORG_ID | 기관코드 | VARCHAR2(40) |
| TBL_ID | 통계표ID | VARCHAR2(40) |
| C1~C8 | 분류값 ID1~8 | VARCHAR2(40) |
| C1_NM~C8_NM | 분류값 명1~8 | VARCHAR2(3000) |
| ITM_ID | 항목 ID | VARCHAR2(40) |
| ITM_NM | 항목명 | VARCHAR2(3000) |
| UNIT_NM | 단위명 | VARCHAR2(1000) |
| PRD_SE | 수록주기 | VARCHAR2(20) |
| PRD_DE | 수록시점 | VARCHAR2(8) |
| **DT** | **수치값** | VARCHAR2(100) |

---

## 3. 주기 코드 및 시점

### 주기 코드 (prdSe)

| 주기 | 설명 | 입력값 | 출력값 |
|------|------|--------|--------|
| 일 | 1일 주기 | D | D |
| 월 | 1개월 주기 | M | M |
| 분기 | 3개월 주기 | Q | Q |
| 반기 | 6개월 주기 | H | H |
| **년** | **1년 주기** | **Y** | **Y** |
| 부정기 | 1회한, 수시 | IR | IR |

### 시점 입력 형식

| 주기 | 형식 | 예시 |
|------|------|------|
| 일 | YYYYMMDD | 20140101 |
| 월 | YYYYMM | 201401 |
| 분기 | YYYYQQ | 201401 |
| 반기 | YYYYHH | 201401 |
| **년** | **YYYY** | **2014** |
| 부정기 | YYYY, YYYYMM, YYYYMMDD | 2014 |

---

## 4. KOSIS 통합검색

### 요청 URL
```
https://kosis.kr/openapi/statisticsSearch.do?method=getList
```

### 요청 변수

| 변수 | 타입 | 설명 | 필수 |
|------|------|------|------|
| apiKey | String | 인증 key | 필수 |
| searchNm | String | 검색명 | 필수 |
| orgId | String | 기관코드 | 선택 |
| sort | String | 정렬 (RANK/DATE) | 선택 |
| startCount | String | 페이지 번호 | 선택 |
| resultCount | String | 출력 개수 | 선택 |
| format | String | 결과 유형(json) | 필수 |

---

## 5. 통계설명 API

### 요청 URL
```
https://kosis.kr/openapi/statisticsExplData.do?method=getList
```

### 요청 변수

| 변수 | 타입 | 설명 | 필수 |
|------|------|------|------|
| apiKey | String | 인증 Key | 필수 |
| statId | String | 통계조사 ID | 필수 |
| metaItm | String | 요청 항목 (All, statsNm 등) | 필수 |
| format | String | 결과 유형(json) | 필수 |

---

## 6. 실제 사용 예제

### 인구 통계 조회 (검증됨)

```python
import requests

url = 'https://kosis.kr/openapi/Param/statisticsParameterData.do'

params = {
    'method': 'getList',
    'apiKey': 'YOUR_API_KEY',
    'orgId': '101',           # 통계청
    'tblId': 'DT_1B04005N',  # 주민등록인구
    'itmId': 'T2+',          # 인구수 (+ 필수!)
    'objL1': '00+',          # 전국 (+ 필수!)
    'objL2': 'ALL',          # 전체 (필수!)
    'objL3': '',
    'objL4': '',
    'objL5': '',
    'objL6': '',
    'objL7': '',
    'objL8': '',
    'format': 'json',
    'jsonVD': 'Y',           # JavaScript JSON
    'prdSe': 'Y',            # 연도
    'startPrdDe': '2024',
    'endPrdDe': '2024',
    'loadGubun': '2'         # 필수!
}

response = requests.get(url, params=params)
data = response.json()  # JavaScript JSON → Python dict 변환 필요
```

### JavaScript JSON 파싱

```python
import re
import json

# KOSIS는 JavaScript 형식 반환
# {ORG_ID:"101",TBL_NM:"인구"}

# Python dict로 변환
text_fixed = re.sub(r'([{,])(\w+):', r'\1"\2":', response.text)
data = json.loads(text_fixed)

# 값 추출
for row in data:
    value = float(row['DT'].replace(',', ''))
    print(f'{row["C1_NM"]}: {value:,.0f}명')
```

---

## 7. 주요 통계표 ID

### 인구/가구

| 통계표 | ID | 설명 |
|--------|-----|------|
| 주민등록인구 | DT_1B04006 | 시군구/성/연령별 |
| 주민등록연앙인구 | DT_1B040M1 | 연앙인구 |
| 가구 통계 | DT_1B04005N | 가구 수 |

### 경제

| 통계표 | ID | 설명 |
|--------|-----|------|
| GDP | (확인 필요) | 국내총생산 |
| 소비자물가 | (확인 필요) | CPI |

---

## 8. 제한 사항

**데이터 호출 제한**:
- **40,000건/호출**
- 초과 시 Error 31

**해결**:
- objL1, objL2를 구체화하여 결과 제한
- 예: objL1='ALL' (모든 지역) → Error 31
- 수정: objL1='00' (전국만) → 성공

---

## 9. 오류 코드

| 코드 | 메시지 | 원인 | 해결 |
|------|--------|------|------|
| 0 | 정상 | - | - |
| 20 | 필수요청변수값 누락 | objL, loadGubun 등 | 파라미터 추가 |
| 21 | 요청변수값 잘못됨 | 잘못된 값 | 값 수정 |
| 31 | 40,000셀 초과 | 데이터 너무 많음 | objL 구체화 |

---

## 10. 참고 사항

### 형식 선택

**JSON** (권장):
- 파싱 간단
- Python 친화적
- JavaScript JSON 변환 필요

**SDMX**:
- 국제 표준
- 메타데이터 풍부
- 파싱 복잡

**선택**: JSON (단순성, 효율성)

---

## 11. 예제 코드 (Python)

### 기본 조회

```python
from pandas.io.json import json_normalize
import pandas as pd
import requests
import re
import json

# API 호출
url = 'https://kosis.kr/openapi/Param/statisticsParameterData.do'

params = {
    'method': 'getList',
    'apiKey': 'YOUR_KEY',
    'orgId': '101',
    'tblId': 'DT_1B04005N',
    'itmId': 'T2+',
    'objL1': '31+',     # 경북
    'objL2': 'ALL',
    'format': 'json',
    'jsonVD': 'Y',
    'prdSe': 'M',
    'startPrdDe': '202104',
    'endPrdDe': '202104',
    'loadGubun': '2'
}

response = requests.get(url, params=params)

# JavaScript JSON 파싱
text_fixed = re.sub(r'([{,])(\w+):', r'\1"\2":', response.text)
data = json.loads(text_fixed)

# DataFrame 변환
df = pd.json_normalize(data)

# CSV 저장
df.to_csv('kosis_data.csv', encoding='cp949')
```

---

## 12. 우리 구현 (KOSISSource)

### 현재 구현

```python
class KOSISSource(BaseDataSource):
    """KOSIS API Source"""

    STAT_TABLES = {
        "population": {
            "orgId": "101",
            "tblId": "DT_1B04006",
            "name": "주민등록인구"
        }
    }

    def _fetch_stat_data(self, org_id, tbl_id, context):
        params = {
            'method': 'getList',
            'apiKey': self.api_key,
            'orgId': org_id,
            'tblId': tbl_id,
            'itmId': 'T2+',        # 인구수
            'objL1': '00+',        # 전국
            'objL2': 'ALL',
            'format': 'json',
            'jsonVD': 'Y',
            'prdSe': 'Y',
            'loadGubun': '2',      # 필수!
        }

        if context.get('year'):
            params['startPrdDe'] = str(context['year'])
            params['endPrdDe'] = str(context['year'])

        # API 호출
        response = requests.get(self.base_url, params=params)

        # JavaScript JSON 파싱
        data = self._parse_javascript_json(response.text)

        return data
```

---

## 13. 필요한 확장

### v3 계획

**통계표 매핑**:
```python
STAT_TABLES = {
    "population": {...},
    "household": {
        "orgId": "101",
        "tblId": "DT_1B04005N",
        "itmId_map": {
            "count": "T2",
            "by_size": "T3",
        }
    },
    "income": {...},
}
```

**파라미터 동적 생성**:
```python
def _build_params(context, stat_table):
    # region → objL1
    if context.get('area') == '서울':
        objL1 = '11+'

    # gender → objL2
    if context.get('gender') == '남성':
        objL2 = '1'

    return params
```

---

## 14. 참고 링크

- **공식 문서**: https://kosis.kr/openapi/file/openApi_manual_v1.0.pdf
- **회원 가입**: https://kosis.kr/openapi/
- **개발 가이드**: https://edu.kosis.kr/openapi/introduce/introduce_01List.do
- **API 신청**: https://kosis.kr/openapi/community/community_0401List.do

---

**작성**: 2025-12-10
**검증**: 2024년 전국 인구 (51,217,221명)
**형식**: JSON (JavaScript JSON 파싱)


