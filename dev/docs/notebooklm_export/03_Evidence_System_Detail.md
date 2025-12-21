# Evidence 시스템 구현 상세

**생성일**: 2025-12-21 10:20:00
**목적**: Evidence 수집, 검증, 저장 시스템

---

## 1. Evidence Engine

### 모듈 설명

```
CMIS Evidence Engine

Evidence 수집 및 관리 엔진 (v2 개정판)

설계 원칙:
- Evidence-first, Prior-last
- Early Return (상위 tier 성공 시 즉시 반환)
- Graceful Degradation (부분 실패 허용)
- Source-agnostic Interface
- Comprehensive Lineage

아키텍처:
- EvidenceEngine: Facade (public API)
- EvidencePlanner: Plan 생성
- EvidenceExecutor: Plan 실행
- SourceRegistry: Source 관리
- EvidenceStore: 캐싱/저장
```

### 주요 클래스

#### `EvidenceEngineError`

Base exception for Evidence Engine

#### `SourceNotAvailableError`

Source 접근 불가 (API down, 네트워크 등)

---

## 2. Evidence Sources

### account_matcher

Account Matcher

DART 계정과목 매칭 (Rule + LLM Hybrid)

**클래스**: `AccountMatcher`

계정과목 매칭 (Rule + LLM Hybrid)

전략:
1. Rule-based Filtering (넓게 수집, 명확히 제외)
2. Fallback: 가장 큰 금액
3. LLM (선택적): 여러 후보 중 최적 선택

### base_search_source

Base Search Source

웹 검색 공통 로직 (Google, DuckDuckGo 등)

**클래스**: `BaseSearchSource`

웹 검색 Base Class

공통 기능:
- 검색 쿼리 구성
- 숫자 추출 (정규식)
- Consensus 알고리즘
- 페이지 크롤링

하위 클래스:
- GoogleSearchSource
- DuckDuckGoSource

### curated_internal_source

CuratedEvidenceSource (BF-14).

Brownfield curated store(CUR/CUB/PRJ/BPK)를 EvidenceEngine의 curated_internal tier로 연결합니다.

의도:
- 외부 API/웹검색 전에 "내부 curated"에서 값을 찾을 수 있으면 우선 사용합니다.
- 단, 어떤 값을 어디에서 읽을지(semantic_key/field_path)는 계약으로 명시되어야 합니다.

현재 구현(저복잡도, 안전한 최소):
- request.context에 아래 키 중 하나가 있을 때만 동작
  - focal_actor_context_id: PRJ-...(-vN 권장)
  - brownfield_pack_id: BPK-...
- semantic_key 결정 규칙
  1) context.curated_semantic_key가 있으면 사용
  2) 없으면 metric_id(+ year/as_of)를 이용해 기본 규칙으로 생성
     - kv:metric:<metric_id>:<year>
     - kv:metric:<metric_id>:as_of=<YYYY-MM-DD>
- 값 추출 규칙
  - context.curated_json_pointer("/a/b") 또는 context.curated_field("revenue")가 있으면 그 경로에서 numeric을 추출
  - 없으면 payload_json["value"](numeric) 우선

주의:
- 본 소스는 "테이블 파싱/정규화"를 수행하지 않습니다.
  (그 책임은 Brownfield ingest/mapping 단계에 있으며, 여기서는 ref 기반 조회만 합니다.)

**클래스**: `CuratedEvidenceSource`

Brownfield curated store 기반 curated_internal Evidence source.

### dart_connector

CMIS DART Evidence Connector

한국 전자공시시스템(DART) API 연동

검증 이력:
- 11개 기업, 537개 항목으로 검증 완료
- 성공률: 91% (11/12)
- 검증 기업: 삼성전자, LG전자, GS리테일, YBM넷, 하이브 등

**클래스**: `Evidence`

Evidence 타입 (v9 스키마)

umis_v9.yaml#substrate_plane.stores.evidence_store 기준

### duckduckgo_source

DuckDuckGo Search Source

DuckDuckGo 검색 (v2 리팩토링: BaseSearchSource 활용)

**클래스**: `DuckDuckGoSource`

DuckDuckGo Search Source (간결화)

### ecos_source

ECOS (한국은행 경제통계) Source

한국은행 경제통계시스템 OpenAPI를 통한 Evidence 수집

2025-12-10: OFFICIAL Tier 확장
- GDP, CPI, 금리, 산업생산지수, 통화량
- Official tier, Confidence: 0.95
- KOSIS 패턴 70% 재사용

검증 예정:
- GDP (국내총생산)
- CPI (소비자물가지수)
- Interest Rate (기준금리)

API: https://ecos.bok.or.kr/api/
형식: JSON

**클래스**: `ECOSSource`

ECOS (한국은행 경제통계시스템) API Source

기능:
- GDP 조회 (국내총생산)
- CPI 조회 (소비자물가지수)
- 금리 조회 (기준금리, 예금은행 금리)
- 산업생산지수
- 통화량

API 문서: https://ecos.bok.or.kr/api/

### fsc_financial_info_source

FSC (금융위원회) 기업 재무정보 API Source.

공공데이터포털(data.go.kr) "금융위원회_기업 재무정보" OpenAPI를 통해,
법인등록번호(crno) + 사업연도(bizYear) 기준으로 기업 재무정보를 조회합니다.

Phase 1 목표:
- 요약재무제표(getSummFinaStat_V2)에서 매출액(enpSaleAmt)을 추출하여
  MET-Revenue에 대한 Tier-1(OFFICIAL) evidence를 제공합니다.

주의:
- 법인등록번호 자동 해소(company_name -> crno)는 별도 API 의존(후속).
- 본 소스는 caller가 corp_reg_no(crno)와 year를 제공해야 합니다.

**클래스**: `FSCCorpFinancialInfoSource`

금융위원회 기업 재무정보(data.go.kr) Source.

### google_search_source

Google Search API Source

Google Custom Search API (v2 리팩토링: BaseSearchSource 활용)

**클래스**: `GoogleSearchSource`

Google Custom Search Source (간결화)

### kosis_source

KOSIS API Source

KOSIS (국가통계포털) OpenAPI를 통한 Evidence 수집

구현 완료 (2025-12-09 ~ 2025-12-10):
- 2개 통계표 매핑 (인구, 가구)
- 17개 지역 코드 지원 (전국 + 시도별)
- 시계열 데이터 조회 (start_year ~ end_year)
- 동적 파라미터 처리 (objL1, objL2, itmId)
- JavaScript JSON 파싱 안정성 개선

검증 결과:
- 2024년 전국 인구: 51,217,221명
- Official tier, Confidence: 0.95
- 지역별 조회: 서울, 부산, 경기 등
- 시계열 조회: 2020-2024

핵심 파라미터:
- loadGubun=2 (필수!)
- itmId (통계표별 동적 매핑)
- objL1 (지역 코드, REGION_CODES 참조)
- objL2='ALL' (필수!)
- prdSe (Y=년, Q=분기, M=월)

형식: JSON (JavaScript JSON 파싱)

**클래스**: `KOSISSource`

KOSIS (국가통계포털) API Source

기능:
- 인구 통계 조회
- 가구 통계 조회
- 시계열 데이터 조회
- 지역별 데이터 조회 (전국, 17개 시도)

지원 통계표:
- DT_1B04006: 주민등록인구
- DT_1B04005N: 가구 및 세대 현황

API 문서: https://kosis.kr/openapi/

### search_v3_source

Search v3 Evidence Source (SSV3-10).

의도:
- SearchKernelV1(Search Strategy v3)을 EvidenceEngine의 commercial tier source로 연결합니다.
- 기존 BaseDataSource 인터페이스를 유지하기 위해, EvidenceExecutor에서
  `fetch_with_policy(request, policy)`를 지원하도록 확장합니다.

**클래스**: `SearchV3Source`

Search Strategy v3 (GenericWebSearch + DocumentFetcher) source.

### sga_extractor

SG&A Extractor

판매비와관리비 세부 항목 추출 (HTML + LLM)

v7 대비 개선:
- HTML 크롤링 간소화
- LLM으로 항목 해석 (유연성 향상)

**클래스**: `SGAExtractor`

SG&A 세부 항목 추출

프로세스:
1. DART API로 사업보고서 원문 다운로드
2. HTML에서 판관비 섹션 추출
3. LLM으로 세부 항목 해석

### sources

CMIS Evidence Sources

BaseDataSource 구현체들

**클래스**: `DARTSource`

DART API Source

기존 DARTConnector를 BaseDataSource 인터페이스로 래핑

### worldbank_source

World Bank API Source

세계은행 국가별 경제/사회 지표 조회

2025-12-10: OFFICIAL Tier 확장 (글로벌)
- GDP, 인구, 교육, 인터넷 보급률 등
- Official tier, Confidence: 0.95
- 인증 불필요 (Public API)

API: https://api.worldbank.org/v2/
문서: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392

**클래스**: `WorldBankSource`

World Bank API Source

기능:
- GDP 조회 (국가별)
- 인구 조회
- 교육 지출
- 인터넷 보급률
- 실업률, 인플레이션 등

특징:
- 인증 불필요 (Public API)
- 200+ 국가 지원
- 1,400+ 지표

API 문서: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392

---

## 3. Evidence 관련 유틸리티

### evidence_builder.py

Evidence Builder - 검색 결과 → EvidenceRecord 변환

Raw 검색 결과에서 EvidenceRecord 조립

2025-12-10: Search Strategy v2.0

### evidence_quality.py

Evidence Quality - 신선도 및 품질 관리

Evidence의 신선도, 품질 점수 계산

2025-12-10: Evidence Engine v2.2

### evidence_validation.py

Evidence Validation - Cross-Source 검증

여러 Source 간 일치도 검증 및 신뢰도 조정

2025-12-10: Evidence Engine v2.2

### evidence_store.py

CMIS Evidence Store

Evidence 저장/조회/캐싱 관리

설계 원칙:
- Metric 단위 캐싱
- TTL 기반 만료
- SQLite/메모리 백엔드 지원
- Lineage 추적

### evidence_batch.py

Evidence Batch Fetching - 일괄 수집

여러 Metric을 Source별로 그룹화하여 일괄 수집

2025-12-10: Evidence Engine v2.2

### evidence_parallel.py

Evidence Parallel Fetching - 병렬 수집

동일 Tier 내 Source를 병렬로 호출하여 성능 향상

2025-12-10: Evidence Engine v2.2

### evidence_retry.py

Evidence Retry - 재시도 전략

네트워크 오류 등 일시적 실패 시 재시도

2025-12-10: Evidence Engine v2.2
