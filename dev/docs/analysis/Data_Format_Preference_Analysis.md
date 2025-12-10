# 데이터 제공 방식 및 포맷 선호도 분석

**작성일**: 2025-12-10  
**목적**: CMIS에 최적화된 데이터 소스 선택 기준

---

## 🎯 데이터 제공 방식 (8가지)

### ⭐⭐⭐⭐⭐ REST (최우선)

**장점**:
- ✅ 프로그래밍 친화적 (Python requests)
- ✅ 실시간 조회 (최신 데이터)
- ✅ 파라미터 기반 필터링 (year, region 등)
- ✅ JSON/XML 응답 (구조화)
- ✅ 에러 처리 명확 (HTTP status)

**단점**:
- API 키 관리 필요
- Rate limiting

**활용도**: **100%** (KOSIS, DART, ECOS 모두 REST)

**예시**:
```python
# ECOS REST API
url = f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/100"
response = requests.get(url)
data = response.json()
```

---

### ⭐⭐⭐⭐ 다운로드 (파일)

**장점**:
- ✅ 대용량 데이터 효율적
- ✅ 오프라인 처리 가능
- ✅ 버전 관리 (파일 저장)

**단점**:
- 수동 업데이트 필요
- 최신성 떨어짐
- 스토리지 필요

**활용도**: **70%** (대용량 통계, 과거 데이터)

**예시**:
```python
# CSV 다운로드 후 파싱
import pandas as pd
df = pd.read_csv("data.csv")
```

---

### ⭐⭐⭐ LOD연계URL

**장점**:
- ✅ 구조화된 데이터 (RDF, JSON-LD)
- ✅ 의미론적 연결 (Linked Data)
- ✅ 표준화 (W3C)

**단점**:
- 복잡한 파싱 (SPARQL 등)
- 제한적 지원

**활용도**: **40%** (특수 목적)

---

### ⭐⭐ RSS/ATOM

**장점**:
- ✅ 업데이트 추적
- ✅ 표준화된 형식

**단점**:
- 피드 형식 (시계열 데이터 부적합)
- 제한적 정보

**활용도**: **20%** (뉴스, 업데이트 알림)

---

### ⭐ SOAP, LINK, 샘플, LOD연계파일

**SOAP**:
- 복잡한 XML 스키마
- 활용도: **10%** (레거시 시스템)

**LINK**:
- 수동 다운로드
- 활용도: **5%**

**샘플**: 테스트 용도만  
**LOD연계파일**: 특수 목적

---

## 📊 파일 포맷 (40가지)

### Tier 1: 구조화 데이터 (최우선)

#### ⭐⭐⭐⭐⭐ JSON

**장점**:
- ✅ Python native (json.loads)
- ✅ 계층 구조 표현
- ✅ 타입 안전성
- ✅ 읽기 쉬움
- ✅ API 응답 표준

**활용도**: **100%**

**현재 사용**:
- ECOS API: JSON ✅
- KOSIS API: JavaScript JSON → JSON 변환 ✅
- Google/DuckDuckGo: JSON ✅

```python
data = response.json()
value = data["result"]["value"]
```

---

#### ⭐⭐⭐⭐⭐ CSV

**장점**:
- ✅ 단순, 범용적
- ✅ Pandas 지원 완벽
- ✅ 대용량 효율적
- ✅ Excel 호환

**단점**:
- 계층 구조 어려움
- 타입 추론 필요

**활용도**: **90%**

```python
df = pd.read_csv("data.csv")
value = df.loc[df['year'] == 2024, 'gdp'].values[0]
```

---

#### ⭐⭐⭐⭐ XML

**장점**:
- ✅ 구조화
- ✅ 표준화
- ✅ 메타데이터 풍부

**단점**:
- 파싱 복잡
- JSON보다 무거움

**활용도**: **70%** (SOAP, 일부 OpenAPI)

```python
import xml.etree.ElementTree as ET
tree = ET.parse("data.xml")
value = tree.find(".//value").text
```

---

#### ⭐⭐⭐⭐ XLSX, XLS

**장점**:
- ✅ 표 형식
- ✅ 다중 시트
- ✅ Pandas 지원

**단점**:
- 바이너리 형식
- 메모리 소비

**활용도**: **70%**

```python
df = pd.read_excel("data.xlsx", sheet_name="Sheet1")
```

---

### Tier 2: 텍스트/문서 (보조)

#### ⭐⭐⭐ TXT

**장점**:
- ✅ 단순
- ✅ 범용

**단점**:
- 구조 없음
- 파싱 필요

**활용도**: **50%** (로그, 간단한 데이터)

---

#### ⭐⭐ PDF

**장점**:
- 문서 형식 (보고서)

**단점**:
- 파싱 복잡 (PyPDF2, pdfplumber)
- 구조 추출 어려움

**활용도**: **30%** (리포트 파싱, LLM 활용)

```python
import pdfplumber
with pdfplumber.open("report.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

---

#### ⭐⭐ HWP, HWPX, DOC, DOCX

**장점**:
- 한국 문서 (HWP)
- 구조화된 문서

**단점**:
- 파싱 복잡
- 라이브러리 제한적

**활용도**: **20%** (문서 파싱 시)

---

### Tier 3: 특수 포맷

#### ⭐⭐⭐ GEOJSON

**장점**:
- ✅ 지리 데이터
- ✅ JSON 기반

**활용도**: **50%** (지역별 통계)

---

#### ⭐⭐ RDF, LOD, TTL

**장점**:
- Linked Open Data
- 의미론적 연결

**단점**:
- 복잡한 파싱 (rdflib)

**활용도**: **30%** (특수 목적)

---

#### ⭐ SHP (Shapefile)

**활용도**: **20%** (GIS 데이터)

---

### Tier 4: 미디어/기타 (제외)

**이미지**: JPG, PNG, GIF, TIFF - 활용도 **5%** (OCR 필요)  
**동영상**: MP4 - 활용도 **1%**  
**음성**: MP3, WAV - 활용도 **1%**  
**프레젠테이션**: PPT, PPTX - 활용도 **10%**  
**압축**: ZIP - 활용도 **60%** (압축 해제 후 사용)  
**코드**: PY - 활용도 **0%**  
**기타**: STL, FASTA, DTD, SGML, GPX - 활용도 **0%**

---

## 🎯 CMIS 최적 선택

### 데이터 제공 방식 (우선순위)

| 순위 | 방식 | 활용도 | 이유 |
|------|------|--------|------|
| **1** | **REST** | 100% | 실시간, 파라미터, 자동화 |
| **2** | **다운로드** | 70% | 대용량, 오프라인 |
| **3** | **LOD연계URL** | 40% | 구조화, 표준 |
| 4 | RSS/ATOM | 20% | 업데이트 추적 |
| 5 | SOAP | 10% | 레거시 |

---

### 파일 포맷 (우선순위)

| 순위 | 포맷 | 활용도 | 이유 |
|------|------|--------|------|
| **1** | **JSON** | 100% | Python native, API 표준 |
| **2** | **CSV** | 90% | Pandas, 대용량 |
| **3** | **XML** | 70% | 구조화, 표준 |
| **4** | **XLSX** | 70% | 표 형식, 다중 시트 |
| 5 | TXT | 50% | 단순 데이터 |
| 6 | GEOJSON | 50% | 지리 데이터 |
| 7 | PDF | 30% | 보고서 (LLM 활용) |
| 8 | RDF/TTL | 30% | Linked Data |
| 9 | ZIP | 60% | 압축 (내부 포맷 확인) |
| 10 | 기타 | <20% | 특수 목적 |

---

## 💡 CMIS 구현 전략

### 현재 활용 중 (✅)

**REST API**:
- KOSIS: JSON (JavaScript JSON 변환)
- DART: JSON
- ECOS: JSON
- Google/DuckDuckGo: JSON

**파일 포맷**:
- JSON: 100% 지원
- CSV: Pandas 활용 가능

---

### 향후 지원 (⏳)

**추가 방식**:
- 다운로드 (CSV, XLSX)
- RSS/ATOM (업데이트 추적)

**추가 포맷**:
- XLSX (Excel 파일)
- PDF (보고서, LLM 파싱)
- GEOJSON (지역 데이터)

---

## 🎯 권장 사항

### 우선 구현 (Phase 4-5)

**1. REST API** (최우선)
- World Bank: JSON ✅
- OECD: JSON/XML
- 공공데이터: JSON/XML

**2. CSV 다운로드**
- 대용량 통계 파일
- Pandas로 파싱

**3. XLSX 지원**
- Excel 파일 (정부 통계)
- openpyxl 라이브러리

---

### 선택적 지원 (Phase 6+)

**4. PDF 파싱**
- 시장조사 보고서
- LLM 활용 (GPT-4o)

**5. GEOJSON**
- 지역별 통계
- 시각화

---

## 📊 기술 스택

### 현재 지원

```python
# REST API
import requests
response = requests.get(url)
data = response.json()  # JSON

# CSV (준비됨)
import pandas as pd
df = pd.read_csv(url)  # Pandas

# XML (준비됨)
import xml.etree.ElementTree as ET
tree = ET.parse(url)
```

---

### 추가 필요

```python
# XLSX
import openpyxl
wb = openpyxl.load_workbook("data.xlsx")

# PDF (LLM)
import pdfplumber
with pdfplumber.open("report.pdf") as pdf:
    text = pdf.pages[0].extract_text()
    # → LLM으로 구조 추출

# GEOJSON
import geopandas as gpd
gdf = gpd.read_file("regions.geojson")
```

---

## 🎯 결론

### 최우선 (즉시 활용)

| 방식 | 포맷 | 활용도 | 상태 |
|------|------|--------|------|
| **REST** | **JSON** | 100% | ✅ 현재 사용 |
| **REST** | **XML** | 70% | ⏳ 준비됨 |
| **다운로드** | **CSV** | 90% | ⏳ 준비됨 |

---

### 차순위 (Phase 4-5)

| 방식 | 포맷 | 활용도 | 구현 필요 |
|------|------|--------|-----------|
| 다운로드 | XLSX | 70% | openpyxl |
| REST | XML | 70% | ElementTree |
| LOD연계URL | RDF/JSON-LD | 40% | rdflib |

---

### 특수 목적 (Phase 6+)

| 포맷 | 용도 | 활용도 | 구현 |
|------|------|--------|------|
| PDF | 보고서 | 30% | LLM 파싱 |
| GEOJSON | 지역 | 50% | geopandas |
| HWP | 한국 문서 | 20% | 변환 필요 |

---

## 📝 CMIS 권장 순서

### Phase 4: REST + JSON (현재)

✅ **KOSIS, DART, ECOS, Google** (모두 JSON)

### Phase 5: CSV + XLSX

⏳ **공공데이터포털, 정부 통계 파일**

### Phase 6: PDF + LLM

⏳ **시장조사 보고서, 컨설팅 리포트**

---

**작성**: 2025-12-10  
**결론**: REST + JSON이 최적, CSV/XLSX가 차선책
