# KOSIS API 구현 이슈 분석

**작성일**: 2025-12-09
**상태**: 파라미터 구조 파악 필요

---

## 1. 현재 상황

### 테스트 결과

**모든 시도 실패**:
```
Error 20: 필수요청변수값이 누락되었습니다. (objL)
Error 21: 요청변수값이 잘못되었습니다.
```

**시도한 방법**:
1. ❌ `objL1='ALL'`
2. ❌ `objL='00+11+26+...'` (지역 코드)
3. ❌ `userStatsId` 방식

### 문제점

1. **파라미터 복잡도**
   - objL1~objL8 (최대 8개 분류)
   - itmId (항목 코드)
   - 통계표마다 다른 구조

2. **문서 부족**
   - PDF 파싱 실패
   - 웹 예제 부족
   - 실제 작동하는 예제 찾기 어려움

3. **API 복잡성**
   - 통계표 구조 사전 파악 필요
   - 메타정보 조회 → 파라미터 확인 → 데이터 조회 (2단계)

---

## 2. JSON vs SDMX 권장

### 결론: **JSON 사용 권장** ✅

**이유**:

| 측면 | JSON | SDMX | Evidence Engine 우선순위 |
|------|------|------|------------------------|
| 파싱 | ✅ 간단 (3줄) | ⚠️ 복잡 (sdmx 라이브러리) | ⭐⭐⭐ |
| 값 추출 | ✅ dict['DT'] | ✅ obs.value | ⭐⭐⭐ |
| 메타데이터 | △ 제한적 | ✅ 풍부 | ⭐ |
| Python | ✅ 기본 | ⚠️ 추가 라이브러리 | ⭐⭐⭐ |
| 디버깅 | ✅ print로 즉시 | ⚠️ XML 구조 | ⭐⭐⭐ |

**Evidence Engine 관점**:
- 주 목적: 값 추출 (메타데이터는 부수적)
- 단순성 > 표준 준수
- 유지보수 중요

**구현 예시 (JSON)**:
```python
# 간단
data = response.json()
value = float(data['data'][0]['DT'].replace(',', ''))

# vs SDMX
msg = sdmx.read_sdmx(response.content)
value = msg.data[0].series[0].observations[0].value
```

---

## 3. KOSIS 구현 전략 (수정)

### v1 상태 (현재)

**완료**:
- ✅ 기본 구조 (BaseDataSource)
- ✅ Source 등록
- ✅ can_handle()
- ✅ JSON 형식 선택

**미완료**:
- ⏭️ 정확한 파라미터 조합
- ⏭️ 통계표 매핑 테이블
- ⏭️ 실제 데이터 조회

### v2 계획 (수정)

**Step 1: 통계표 메타정보 확보**
```python
# 1. KOSIS 웹사이트에서 실제 통계표 확인
# 2. 브라우저 개발자 도구로 실제 API 호출 캡처
# 3. 작동하는 파라미터 조합 확인

# 예상 필요 정보:
STAT_TABLES = {
    "population": {
        "orgId": "101",
        "tblId": "DT_1B040A3",
        "itmId": "???",  # 실제 확인 필요
        "objL1": "???",  # 실제 확인 필요
        "objL2": "???",
    }
}
```

**Step 2: 단계적 구현**
```python
# Phase 1: 하나의 통계표만 (인구)
# Phase 2: 추가 통계표 (가구, 소득)
# Phase 3: 동적 파라미터 생성
```

### v2 대안: KOSIS 스킵, 다른 Source 활용

**현재 작동 중인 Source**:
- ✅ DART (Official)
- ✅ Google Search (Commercial)
- ✅ DuckDuckGo (Commercial)

**충분한 커버리지**:
- Official tier: DART
- Commercial tier: Google, DuckDuckGo
- KR 지역 데이터: 3개 source로 커버 가능

---

## 4. 권장사항

### 즉시 (v1)

**KOSIS는 스텁으로 유지** ⏭️

이유:
1. 파라미터 복잡도 높음
2. 실제 문서/예제 필요
3. 다른 3개 Source로 충분

**집중 항목**:
- ✅ Google Search (작동 확인)
- ✅ DuckDuckGo (구현 완료)
- ✅ DART (작동 확인)

### 중기 (v2, 1-2주)

**KOSIS 완성**:
1. KOSIS 웹사이트에서 실제 통계표 분석
2. 브라우저 개발자 도구로 API 호출 캡처
3. 작동하는 파라미터 확인
4. 통계표 매핑 테이블 구축

**우선순위**: 중 (다른 source로 대체 가능)

### 장기 (v3+)

**SDMX 고려**:
- 국제 데이터 통합 시
- OECD, World Bank 연동 시

---

## 5. 실전 배포 가능 여부

### 현재 Evidence Engine 상태

**작동하는 Source (3개)**:
```
Tier 1 (Official):
  ✅ DART (한국 기업 재무)

Tier 3 (Commercial):
  ✅ Google Search (웹 데이터)
  ✅ DuckDuckGo (웹 데이터)

커버리지: 한국 시장 데이터 충분
```

**KOSIS 없이도 충분한 이유**:
- DART: 기업 재무 데이터 (공식)
- Google/DuckDuckGo: 시장 규모, 트렌드
- 인구 데이터: Google에서도 추출 가능

### 실전 배포 판단

**✅ Production Ready (KOSIS 없이도)**

이유:
- 3개 Source 작동
- Tier 1 (Official) 커버
- Tier 3 (Commercial) 커버
- Early Return 작동
- 캐시 작동

---

## 6. 결론

### JSON vs SDMX

**권장**: ✅ **JSON 형식**
- 단순함
- Python 친화적
- 디버깅 쉬움

### KOSIS 구현

**v1**: ⏭️ 스텁 유지 (3개 Source로 충분)
**v2**: 🔨 실제 구현 (웹사이트 분석 후)
**v3**: 📝 SDMX 고려 (국제 데이터 통합 시)

### 실전 배포

**상태**: ✅ **KOSIS 없이도 Production Ready**

**근거**:
- DART (Official)
- Google (Commercial, 검증 완료)
- DuckDuckGo (Commercial)
- 107개 테스트 통과

---

**최종 권장**:

1. ✅ **JSON 형식 사용** (v1/v2)
2. ⏭️ **KOSIS는 v2로 연기** (파라미터 복잡)
3. ✅ **현재 상태로 배포 가능** (3개 Source 충분)

---

**작성**: 2025-12-09
**상태**: KOSIS 이슈 분석 완료
**권장**: JSON + v2 연기



