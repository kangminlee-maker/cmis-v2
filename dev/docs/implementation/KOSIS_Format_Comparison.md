# KOSIS API 데이터 형식 비교 (SDMX vs JSON)

**작성일**: 2025-12-09
**목적**: KOSIS API의 SDMX와 JSON 형식 비교 및 선택 가이드

---

## 1. 형식 개요

### SDMX (Statistical Data and Metadata eXchange)

**특징**:
- 통계 데이터 교환 국제 표준
- XML 기반
- 메타데이터 풍부 (Concepts, CodeLists, DataStructure)
- OECD, IMF, World Bank 등 국제기구 표준

**구조**:
```xml
<Structure>
  <CodeLists>
    <CodeList id="CL_AREA">
      <Code value="KR">
        <Description>대한민국</Description>
      </Code>
    </CodeList>
  </CodeLists>
</Structure>
<DataSet>
  <Series AREA="KR" TIME_PERIOD="2024">
    <Obs TIME_PERIOD="2024" OBS_VALUE="51000000"/>
  </Series>
</DataSet>
```

### JSON

**특징**:
- 경량 데이터 형식
- JavaScript 기반, Python 기본 지원
- 파싱 간단
- 웹 API 표준

**구조**:
```json
{
  "data": [
    {
      "C1": "2024",
      "C1_NM": "2024년",
      "DT": "51000000",
      "UNIT_NM": "명"
    }
  ]
}
```

---

## 2. Evidence Engine 관점 비교

### 우리의 요구사항

| 요구사항 | 중요도 | SDMX | JSON |
|---------|--------|------|------|
| **빠른 파싱** | 상 | ⚠️ 복잡 | ✅ 간단 |
| **값 추출** | 상 | ✅ | ✅ |
| **메타데이터** | 중 | ✅ 풍부 | ⚠️ 제한적 |
| **Python 호환** | 상 | ⚠️ 라이브러리 | ✅ 기본 |
| **유지보수** | 상 | ⚠️ 어려움 | ✅ 쉬움 |
| **표준 준수** | 중 | ✅ 국제 표준 | △ 웹 표준 |

---

## 3. 상세 비교

### 3.1 파싱 복잡도

**SDMX**:
```python
# 추가 라이브러리 필요
import sdmx

# 파싱
msg = sdmx.read_sdmx('response.xml')
data = msg.data[0]

# 값 추출
for series in data.series:
    for obs in series.observations:
        value = obs.value
        time = obs.dimension['TIME_PERIOD']
```

**JSON**:
```python
# Python 기본 라이브러리
import json

# 파싱
data = response.json()

# 값 추출
for row in data.get('data', []):
    value = row.get('DT')
    time = row.get('C1')
```

**결과**: JSON 승리 (단순성)

### 3.2 메타데이터

**SDMX**:
```xml
<!-- 풍부한 메타데이터 -->
<CodeList id="CL_SEX">
  <Code value="M"><Description>남성</Description></Code>
  <Code value="F"><Description>여성</Description></Code>
</CodeList>

<Concept id="OBS_VALUE">
  <Name>관측값</Name>
  <Description>인구수</Description>
</Concept>
```

**JSON**:
```json
{
  "C1_NM": "2024년",
  "C1_OBJ_NM": "시점",
  "DT": "51000000",
  "UNIT_NM": "명"
}
```

**결과**: SDMX 승리 (메타데이터 풍부)

### 3.3 Evidence Engine 통합

**SDMX**:
```python
# 장점
- 표준 스키마 (재사용성)
- 코드리스트로 validation 가능

# 단점
- 파싱 라이브러리 필요 (sdmx, pandasdmx)
- 복잡도 증가
- 디버깅 어려움
```

**JSON**:
```python
# 장점
- Python dict로 즉시 사용
- 디버깅 간단 (print로 확인)
- 추가 의존성 없음

# 단점
- 메타데이터 제한적
- 스키마 변경 시 코드 수정 필요
```

---

## 4. 권장 사항

### 4.1 Evidence Engine v1: **JSON 사용 권장** ✅

**이유**:

1. **단순성** (가장 중요)
   - Python 기본 지원
   - 파싱 코드 5줄
   - 디버깅 쉬움

2. **우리의 사용 패턴**
   - 값 추출이 주 목적 (메타데이터는 부수적)
   - EvidenceRecord.metadata에 필요한 것만 저장
   - 복잡한 메타데이터 불필요

3. **유지보수**
   - 팀원이 쉽게 이해
   - 추가 라이브러리 없음
   - 오류 처리 간단

4. **성능**
   - JSON 파싱 빠름
   - 메모리 사용 적음

### 4.2 SDMX가 필요한 경우

**다음 상황에서만 SDMX 고려**:

1. **국제 데이터 통합**
   - OECD, World Bank 데이터와 통합
   - 표준 스키마 필요

2. **복잡한 메타데이터 필요**
   - 코드리스트 자동 validation
   - 다국어 지원
   - 개념 체계 정의

3. **데이터 교환**
   - 외부 시스템과 SDMX 형식으로 교환
   - 표준 준수 필수

**현재 Evidence Engine에는 해당 안 됨**

---

## 5. 구현 예시 비교

### JSON 구현 (권장)

```python
def _fetch_stat_data(self, org_id, tbl_id, context):
    """KOSIS 통계 조회 (JSON)"""
    params = {
        'method': 'getList',
        'apiKey': self.api_key,
        'orgId': org_id,
        'tblId': tbl_id,
        'objL1': 'ALL',  # 전국
        'format': 'json',
        'jsonVD': 'Y'
    }
    
    response = requests.get(self.base_url, params=params)
    data = response.json()
    
    # 간단한 파싱
    for row in data.get('data', []):
        value = float(row['DT'].replace(',', ''))
        return value

# 장점: 5줄 코드, 명확함
```

### SDMX 구현 (복잡)

```python
def _fetch_stat_data_sdmx(self, org_id, tbl_id, context):
    """KOSIS 통계 조회 (SDMX)"""
    import sdmx
    
    params = {
        'method': 'getList',
        'apiKey': self.api_key,
        'orgId': org_id,
        'tblId': tbl_id,
        'format': 'sdmx'
    }
    
    response = requests.get(self.base_url, params=params)
    
    # SDMX 파싱
    msg = sdmx.read_sdmx(response.content)
    
    # 구조 파악 필요
    for dataset in msg.data:
        for series in dataset.series:
            for obs in series.observations:
                value = obs.value
                return value

# 단점: 복잡, 추가 라이브러리, 디버깅 어려움
```

---

## 6. 결론 및 권장사항

### 최종 권장: **JSON 형식 사용** ✅

**근거**:
1. Evidence Engine의 주 목적은 "값 추출"
2. 메타데이터는 EvidenceRecord.metadata에 선별적으로 저장
3. 단순성 > 표준 준수 (현 단계에서)
4. Python 생태계 친화적
5. 팀 유지보수 용이

### 구현 전략

```python
class KOSISSource(BaseDataSource):
    """KOSIS API Source (JSON 형식)"""
    
    def _fetch_stat_data(self, org_id, tbl_id, context):
        params = {
            'format': 'json',  # ← JSON 사용
            'jsonVD': 'Y',     # Value + Description
            ...
        }
        
        response = requests.get(self.base_url, params=params)
        data = response.json()  # ← 간단 파싱
        
        return data
    
    def _parse_stat_data(self, data, request):
        """JSON 데이터 파싱 (간단)"""
        for row in data.get('data', []):
            value = float(row['DT'].replace(',', ''))
            
            # 메타데이터 선별 저장
            metadata = {
                'year': row.get('C1'),
                'unit': row.get('UNIT_NM'),
                'stat_name': row.get('C1_NM')
            }
            
            return value, metadata
```

### v2에서 SDMX 고려 가능

**조건**:
- 국제 데이터 통합 시 (OECD 등)
- 메타데이터 중요도 상승 시
- 표준 준수 요구 시

---

**결론**: ✅ **JSON 형식 사용 권장 (v1/v2)**

**이유**: 단순성, 유지보수성, Python 호환성

**SDMX**: v3 이후 국제 데이터 통합 시 고려

---

**작성**: 2025-12-09
**권장**: JSON (v1/v2), SDMX (v3+)

