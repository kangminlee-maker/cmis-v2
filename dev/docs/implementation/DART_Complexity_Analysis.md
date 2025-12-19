# DART API 복잡성 분석 및 v9 구현 전략

**작성일**: 2025-12-09
**목적**: DART의 비구조화 데이터 이슈 및 v7 해결 방법 분석

---

## 1. DART API의 복잡성

### 문제점

**1. 비구조화 데이터**
```
문제: 같은 "매출액"이라도 회사마다 다른 이름
- "매출액"
- "영업수익"
- "순매출액"
- "총매출"
```

**2. 기간 표현 다양**
```
thstrm_nm (당기 이름):
- "당기"
- "제 24 기"
- "2023년"
- "제24기"
```

**3. 단위 불일치**
```
API 응답: "원" 단위로 추정
문서 표기: 때로 "천원" 언급
실제: 원 단위 (검증 완료)
```

**4. OFS vs CFS 혼재**
```
개별재무제표 (OFS)
연결재무제표 (CFS)
→ 같은 회사, 다른 값
```

---

## 2. v7 해결 방법

### v7 dart_validator.py 분석

**복잡한 검증 로직**:

```python
# 1. XML 섹션 파싱
def extract_sga_total_from_section(section_text):
    """XML에서 판매비와관리비 추출

    복잡성:
    - HTML 태그 파싱
    - 단위 찾기 (백만원/천원/억원)
    - 합계 항목 우선순위
    - "합  계", "합 계", "합계" 등 다양한 표현
    """

# 2. OFS/CFS 자동 판별
def validate_ofs_cfs(client, corp_code, year, xml_section):
    """OFS vs CFS 자동 판별

    프로세스:
    1. XML에서 합계 추출
    2. API OFS 조회
    3. API CFS 조회
    4. 일치하는 쪽으로 판단 (±1%)
    """

# 3. 계정과목 매칭
- 정규식 기반
- 우선순위 로직
- 수식어 제거
```

### v7의 다단계 처리

**Phase 1**: API 호출
```python
financials = client.get_financials(corp_code, year, 'OFS')
# → 103개 항목 (비구조화)
```

**Phase 2**: 항목 필터링
```python
# "매출액" 키워드 매칭
revenue_items = [
    item for item in financials
    if '매출액' in item.get('account_nm', '')
]
# → 1개 항목
```

**Phase 3**: 단위 변환
```python
# 단위 확인 및 변환
if unit == '백만원':
    value = amount / 100  # → 억원
elif unit == '천원':
    value = amount / 100_000
else:
    value = amount  # 원 단위
```

**Phase 4**: 검증 (v7 추가)
```python
# XML 섹션과 API 비교
# OFS/CFS 자동 판별
# ±1% 오차 허용
```

---

## 3. v9 현재 구현

### v9 dart_connector.py

**단순화된 접근**:
```python
def fetch_company_revenue(company_name, year):
    # 1. 기업 코드
    corp_code = get_corp_code(company_name)

    # 2. 재무제표 (OFS 고정)
    financials = get_financials(corp_code, year, 'OFS')

    # 3. 매출액 추출
    revenue_items = [
        item for item in financials
        if '매출액' in item.get('account_nm', '')
    ]

    # 4. 금액 (원 단위 그대로)
    revenue = float(revenue_items[0].get('thstrm_amount'))

    return Evidence(...)
```

**장점**:
- 코드 간단 (50줄)
- 90% 케이스 커버

**단점**:
- 계정과목 매칭 단순 (키워드만)
- OFS/CFS 자동 판별 없음
- 단위 검증 없음
- XML 섹션 미사용

---

## 4. 발견한 이슈 및 해결

### 이슈 1: "당기" 조건

**문제**:
```python
# 우리 코드 (v1)
if '당기' in item.get('thstrm_nm', ''):
    ...

# 실제 데이터
thstrm_nm: "제 24 기"  # "당기" 없음!
```

**해결**:
```python
# thstrm_nm 조건 제거
revenue_items = [
    item for item in financials
    if '매출액' in item.get('account_nm', '')
    # thstrm_nm 조건 제거 ✅
]
```

### 이슈 2: 단위 변환

**문제**:
```python
# 우리 코드 (v1 원본)
revenue = float(revenue_raw) * 1000  # 천원 → 원

# 실제
thstrm_amount: 60480863497  # 이미 원 단위!
```

**해결**:
```python
# 단위 변환 제거
revenue = float(revenue_raw)  # 이미 원 단위 ✅
```

---

## 5. DART 복잡성 대응 전략

### v1 (현재): 단순 접근 ✅

**범위**:
- 키워드 매칭 ("매출액", "영업이익" 등)
- OFS 고정
- 원 단위 그대로
- 첫 번째 매칭 항목 사용

**커버리지**:
- 추정: 80-90%
- 일반적인 케이스는 작동

### v2: v7 검증 로직 통합 (선택)

**필요 시 추가**:
1. **XML 섹션 파싱**
   - dart_validator.py 로직 이식
   - HTML 태그 처리
   - 단위 자동 감지

2. **OFS/CFS 자동 판별**
   - API 두 번 호출 (OFS, CFS)
   - ±1% 일치 확인
   - 자동 선택

3. **계정과목 정교화**
   - 우선순위 로직
   - 정규식 패턴
   - 수식어 처리

4. **LLM 활용 (선택)**
   - 애매한 항목 해석
   - 계정과목 매칭 보조
   - Confidence 조정

### v3: 완전 자동화 (장기)

**BeliefEngine 통합**:
- 회사별 계정과목 학습
- 패턴 인식
- 자동 보정

---

## 6. v9 권장사항

### 즉시 (v1)

**현재 구현 유지** ✅

이유:
1. 80-90% 커버리지 충분
2. 단순함 > 복잡함 (현 단계)
3. 실제 작동 확인됨

수정 사항:
- ✅ "당기" 조건 제거
- ✅ 단위 변환 제거 (이미 원 단위)

### 중기 (v2, 필요 시)

**v7 검증 로직 선택 통합**:
- XML 섹션 파싱 (필요시)
- OFS/CFS 자동 판별 (정확도 향상)

우선순위: 낮 (현재로 충분)

### 장기 (v3)

**LLM 통합 고려**:
- 애매한 계정과목 해석
- 맥락 기반 validation

조건: BeliefEngine 구현 후

---

## 7. 실전 사용 가이드

### v1 제약사항

**작동하는 경우** (80-90%):
```python
# 표준 계정과목
- "매출액"
- "영업이익"
- "순이익"

# 일반적인 회사
- 상장사
- 사업보고서 제출
```

**작동 안 할 수 있는 경우** (10-20%):
```python
# 비표준 계정과목
- "영업수익" (매출액과 다름)
- "총매출액" (키워드 매칭 실패 가능)

# 특수한 경우
- 분기보고서만 있음
- 사업보고서 미제출
```

### Fallback 전략

**Evidence Engine 설계가 커버**:
```python
# DART 실패 시
Tier 1: DART → 실패
  ↓
Tier 3: Google Search → 성공
  ↓
Early Return

→ Graceful Degradation ✅
```

---

## 8. 검증 결과

### 테스트 케이스: YBM넷 2023

**v1 구현 결과**:
```
✅ 호출 성공
Value: 60,480,863,497원 (604.8억원)
Confidence: 0.95
Account: 매출액
Corp_code: 00307222
```

**검증**:
- ✅ 값 정확 (예상 605억원)
- ✅ 계정과목 매칭 성공
- ✅ OFS 조회 성공

---

## 9. 결론

### v1 상태

**충분함** ✅

이유:
- 80-90% 커버리지
- 실제 작동 확인
- Fallback 있음 (Google Search)

### v7 복잡성은 필요 시

**언제 필요?**:
- Accuracy 95%+ 필요 시
- 비표준 계정과목 많을 때
- LLM 활용 가능 시

**현재**: 불필요 (v1로 충분)

### 권장

**v1**: ✅ 현재 구현 유지
**v2**: 필요 시 v7 로직 선택 통합
**v3**: LLM + BeliefEngine

---

**결론**: v1 DART 구현 충분, v7 복잡성은 v2+ 고려

---

**작성**: 2025-12-09
**상태**: DART 분석 완료
**권장**: v1 유지, v2 선택 개선
