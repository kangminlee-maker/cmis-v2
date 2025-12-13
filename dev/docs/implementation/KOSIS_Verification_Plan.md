# KOSIS 검증 계획

**작성일**: 2025-12-10
**목적**: KOSIS API 다양한 옵션 검증

---

## 1. 현재 상태

### 작동 확인

**기본 설정**:
```python
params = {
    'itmId': 'T2+',      # 인구수
    'objL1': '00+',      # 전국
    'objL2': 'ALL',      # 전체
    'prdSe': 'Y',        # 연도
}

# 결과: 51,217,221명 (2024 전국 인구) ✅
```

### 미검증 영역

**통계표**:
- 인구 (DT_1B04006) ✅ 검증됨
- 가구 (DT_1B04005N) ⚠️ 미검증
- 소득 분포 ❌ 미검증
- 산업 통계 ❌ 미검증

**파라미터**:
- objL1, objL2 조합 ⚠️ 전국만
- itmId 항목 코드 ⚠️ T2만
- 시계열 (startPrdDe~endPrdDe) ⚠️ 단일 연도만

---

## 2. 검증 항목

### 2.1 통계표 확장

**인구 통계** (DT_1B04006):
- [ ] 전국 인구 (현재 작동)
- [ ] 시도별 인구 (objL1 = 지역 코드)
- [ ] 성별/연령별 (objL2 추가)
- [ ] 시계열 (2020-2024)

**가구 통계** (DT_1B04005N):
- [ ] 전국 가구 수
- [ ] 시도별 가구
- [ ] 가구원 수별

**소득 분포**:
- [ ] 통계표 ID 확인
- [ ] 소득 분위별
- [ ] 지역별

---

### 2.2 파라미터 조합

**objL1 (지역 코드)**:
```python
# 확인 필요
objL1_codes = {
    '00': '전국',     # ✅ 작동
    '11': '서울',
    '26': '부산',
    '27': '대구',
    ...
}
```

**objL2 (세부 분류)**:
```python
# 통계표마다 다름
objL2 = {
    'ALL': '전체',     # ✅ 작동
    '1': '남성',
    '2': '여성',
    ...
}
```

**itmId (항목 코드)**:
```python
# 통계표마다 다름
itmId = {
    'T2': '인구수',    # ✅ 작동
    'T3': '가구수',
    'T4': '....',
}
```

---

### 2.3 시계열 데이터

**단일 연도**:
```python
startPrdDe: '2024'
endPrdDe: '2024'
# ✅ 작동
```

**복수 연도**:
```python
startPrdDe: '2020'
endPrdDe: '2024'
# ⚠️ 검증 필요
```

**최신 N개**:
```python
newEstPrdCnt: '5'  # 최근 5개 시점
# ⚠️ 검증 필요
```

---

## 3. 검증 전략

### Phase 1: 기본 통계표 (1-2일)

**목표**: 주요 3개 통계표 작동 확인

**작업**:
1. 인구 통계 확장
   - 시도별
   - 성별/연령별
   - 시계열

2. 가구 통계 구현
   - 전국 가구 수
   - 시도별

3. 소득 분포 구현
   - 통계표 ID 확인
   - 기본 조회

**검증**: 각 통계표당 3-5개 케이스

---

### Phase 2: 파라미터 매핑 (2-3일)

**목표**: objL, itmId 체계 구축

**작업**:
1. 지역 코드 매핑
   ```python
   REGION_CODES = {
       '전국': '00',
       '서울': '11',
       '부산': '26',
       ...
   }
   ```

2. 항목 코드 매핑
   ```python
   ITEM_CODES = {
       'DT_1B04006': {  # 인구
           'T2': '인구수',
           'T3': '가구수',
           ...
       }
   }
   ```

3. 동적 파라미터 생성
   ```python
   def _build_kosis_params(stat_type, region, items):
       # Context → KOSIS 파라미터 자동 변환
   ```

---

### Phase 3: 안정성 검증 (1-2일)

**목표**: Edge case 테스트

**케이스**:
1. 데이터 없는 경우
2. 40,000건 제한 초과
3. 잘못된 파라미터
4. JavaScript JSON 파싱 edge case
5. 네트워크 오류

**검증**: 각 케이스당 2-3개 테스트

---

## 4. 구현 계획

### KOSISSource 확장

**현재** (기본만):
```python
def fetch(request):
    stat_type = _determine_stat_type(request)  # population만
    stat_info = STAT_TABLES[stat_type]         # DT_1B04006만

    params = {
        'objL1': '00+',   # 전국 고정
        'objL2': 'ALL',   # 전체 고정
        'itmId': 'T2+',   # 인구수 고정
    }
```

**개선** (유연):
```python
def fetch(request):
    # 1. 통계표 선택 (확장)
    stat_type = _determine_stat_type(request)
    stat_table = STAT_TABLES[stat_type]

    # 2. 파라미터 동적 생성
    params = _build_params(request.context, stat_table)
    # → region: "서울" → objL1: "11"
    # → items: ["인구수", "가구수"] → itmId: "T2+T3+"

    # 3. API 호출
    data = _fetch_stat_data(params)

    # 4. 유연한 파싱
    value = _parse_data(data, request.context)
```

---

## 5. 테스트 케이스

### 인구 통계 (확장)

```python
# 1. 전국 인구 (현재)
context = {"region": "KR", "year": 2024}
# → objL1: "00+", 결과: 51M명 ✅

# 2. 서울 인구
context = {"region": "KR", "area": "서울", "year": 2024}
# → objL1: "11+", 결과: 9M명 예상

# 3. 성별
context = {"region": "KR", "gender": "남성", "year": 2024}
# → objL2: "1", 결과: 25M명 예상

# 4. 시계열
context = {"region": "KR", "year_range": (2020, 2024)}
# → startPrdDe: "2020", endPrdDe: "2024"
# → 결과: 5개 연도 데이터
```

### 가구 통계 (신규)

```python
context = {"region": "KR", "year": 2024}
# → tblId: "DT_1B04005N"
# → 결과: 21M가구 예상
```

---

## 6. 우선순위

### 즉시 (다음 세션)

**중요도**: 중간
**소요**: 1주

**작업**:
1. 통계표 3개 확장
2. 지역 코드 매핑
3. 10+ 케이스 테스트

### 중기 (v3)

**중요도**: 낮음
**소요**: 1-2주

**작업**:
1. 모든 통계표 매핑
2. 동적 파라미터 생성
3. Edge case 처리

---

## 7. 성공 기준

**Phase 1 완료**:
- [ ] 3개 통계표 작동
- [ ] 지역별 조회 가능
- [ ] 시계열 조회 가능
- [ ] 15+ 테스트 통과

**Phase 2 완료**:
- [ ] objL, itmId 매핑 완성
- [ ] 동적 파라미터 생성
- [ ] 30+ 테스트 통과

---

**작성**: 2025-12-10
**우선순위**: 중간 (다음 세션 또는 v3)
**예상 소요**: 1주


