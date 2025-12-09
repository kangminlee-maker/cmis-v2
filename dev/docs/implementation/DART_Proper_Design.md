# DART 올바른 구현 설계 (LLM 기반)

**작성일**: 2025-12-09
**목적**: 하드코딩 없이 유연한 계정과목 매칭

---

## 1. 현재 구현의 문제점 ❌

### 잘못된 접근

```python
# ❌ 특정 회사 하드코딩
if company == "삼성전자":
    use_account = "영업수익"

# ❌ Dictionary 매핑 (끝없는 variation)
REVENUE_MAPPING = {
    "매출액": ["매출액", "순매출액"],
    "영업수익": ["영업수익", "영업수입"],
    ...  # 끝없이 추가 필요
}

# ❌ 우선순위 키워드 (현재 우리 구현)
keywords = [
    ['매출액'],      # 1순위
    ['영업수익'],    # 2순위 ← 하드코딩!
    ['수익', '매출'], # 3순위
]
```

**문제**:
1. 회사마다 다른 표현 (미리 알 수 없음)
2. 끝없는 variation
3. 새 케이스마다 코드 수정 필요

---

## 2. v7의 올바른 접근

### 전략: Rule + LLM Hybrid

```
┌─────────────────────────────────────┐
│  Step 1: Rule-based Filtering       │
│  - "매출", "수익" 포함 항목 수집     │
│  - 명확한 제외 (자산, 부채 등)       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Step 2: LLM-based Interpretation   │
│  - "이 중 매출액은?" → LLM 판단     │
│  - Context: 항목명, 금액, 회사      │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Step 3: Validation                 │
│  - 금액 범위 체크                    │
│  - 상식 검증                         │
└─────────────────────────────────────┘
```

---

## 3. 올바른 v9 설계

### 3.1 AccountMatcher 아키텍처

```python
class AccountMatcher:
    """계정과목 매칭 (Rule + LLM Hybrid)"""
    
    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.rule_matcher = RuleBasedMatcher()
        self.llm_matcher = LLMBasedMatcher(llm_provider)
    
    def find_revenue_account(
        self,
        financials: List[Dict],
        context: Dict
    ) -> Optional[Dict]:
        """매출액 계정 찾기
        
        Args:
            financials: 재무제표 항목 리스트
            context: {"company_name": ..., "year": ...}
        
        Returns:
            매칭된 항목 or None
        
        알고리즘:
        1. Rule-based Filtering (확실한 후보만)
        2. LLM Interpretation (애매한 경우)
        3. Validation (상식 검증)
        """
        # Step 1: Rule-based Filtering
        candidates = self.rule_matcher.filter_candidates(
            financials,
            target_concept="revenue"
        )
        
        if not candidates:
            return None
        
        # 1개면 즉시 반환 (확실)
        if len(candidates) == 1:
            return candidates[0]
        
        # Step 2: LLM Interpretation (여러 후보)
        best_match = self.llm_matcher.select_best(
            candidates,
            target_concept="revenue",
            context=context
        )
        
        return best_match
```

### 3.2 RuleBasedMatcher (확장 가능)

```python
class RuleBasedMatcher:
    """Rule 기반 필터링 (명확한 것만)"""
    
    # 고정 규칙 (확실한 것만)
    INCLUDE_KEYWORDS = {
        "revenue": ["매출", "수익", "영업"],
        "operating_income": ["영업이익", "영업손익"],
        "net_income": ["순이익", "당기순"],
    }
    
    # 명확한 제외 (확실)
    EXCLUDE_KEYWORDS = [
        "자산", "부채", "자본",
        "채권", "채무",
        "현금", "예금",
        "비용", "원가",
    ]
    
    def filter_candidates(
        self,
        financials: List[Dict],
        target_concept: str
    ) -> List[Dict]:
        """후보 필터링 (명확한 것만)
        
        Returns:
            후보 리스트 (0~N개)
        """
        include_kw = self.INCLUDE_KEYWORDS.get(target_concept, [])
        
        candidates = []
        
        for item in financials:
            account_nm = item.get('account_nm', '')
            
            # 제외 키워드 체크 (명확)
            if any(ex in account_nm for ex in self.EXCLUDE_KEYWORDS):
                continue
            
            # 포함 키워드 체크
            if any(inc in account_nm for inc in include_kw):
                candidates.append(item)
        
        return candidates
```

### 3.3 LLMBasedMatcher (핵심!)

```python
class LLMBasedMatcher:
    """LLM 기반 계정과목 해석"""
    
    def __init__(self, llm_provider):
        self.llm = llm_provider
    
    def select_best(
        self,
        candidates: List[Dict],
        target_concept: str,
        context: Dict
    ) -> Optional[Dict]:
        """여러 후보 중 최적 선택 (LLM 활용)
        
        Args:
            candidates: 후보 리스트
            target_concept: "revenue", "operating_income" 등
            context: {"company_name": ..., "year": ...}
        
        Returns:
            최적 항목
        """
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return candidates[0]
        
        # LLM Prompt 구성
        prompt = self._build_prompt(candidates, target_concept, context)
        
        # LLM 호출
        response = self.llm.call(prompt)
        
        # 응답 파싱 (선택된 index)
        selected_idx = self._parse_response(response)
        
        if selected_idx is not None and 0 <= selected_idx < len(candidates):
            return candidates[selected_idx]
        
        # Fallback: 가장 큰 금액
        return max(candidates, key=lambda x: abs(float(x.get('thstrm_amount', 0))))
    
    def _build_prompt(
        self,
        candidates: List[Dict],
        target_concept: str,
        context: Dict
    ) -> str:
        """LLM Prompt 생성"""
        
        concept_map = {
            "revenue": "매출액 (Revenue)",
            "operating_income": "영업이익 (Operating Income)",
            "net_income": "순이익 (Net Income)",
        }
        
        target_name = concept_map.get(target_concept, target_concept)
        company = context.get("company_name", "")
        year = context.get("year", "")
        
        prompt = f"""다음은 {company}의 {year}년 재무제표 항목입니다.
이 중에서 "{target_name}"에 해당하는 항목을 선택해주세요.

항목 목록:
"""
        
        for i, item in enumerate(candidates):
            account_nm = item.get('account_nm', '')
            amount = float(item.get('thstrm_amount', 0))
            
            prompt += f"{i}. {account_nm}: {amount/100_000_000:,.1f}억원\n"
        
        prompt += f"""
"{target_name}"에 가장 적합한 항목의 번호를 선택하세요.
애매한 경우, 금액이 가장 큰 것을 선택하세요.

응답 형식: 숫자만 (예: 0, 1, 2)
"""
        
        return prompt
    
    def _parse_response(self, response: str) -> Optional[int]:
        """LLM 응답 파싱"""
        import re
        
        # 첫 번째 숫자 추출
        match = re.search(r'\d+', response)
        
        if match:
            return int(match.group())
        
        return None
```

---

## 4. 올바른 구현 흐름

### 전체 프로세스

```python
def fetch_company_revenue(company_name, year):
    # 1. 기업 코드
    corp_code = get_corp_code(company_name)
    
    # 2. 재무제표
    financials = get_financials(corp_code, year)
    
    # 3. AccountMatcher 사용
    matcher = AccountMatcher(llm_provider)
    
    revenue_item = matcher.find_revenue_account(
        financials,
        context={"company_name": company_name, "year": year}
    )
    
    if not revenue_item:
        return None
    
    # 4. Evidence 생성
    return Evidence(
        value=float(revenue_item['thstrm_amount']),
        metadata={
            "account_name": revenue_item['account_nm'],
            "matched_by": "llm" or "rule",
            ...
        }
    )
```

### Rule vs LLM 분기

```python
# Rule만으로 해결 (80%)
if len(candidates) == 1:
    return candidates[0]  # Rule 충분

# 명확한 패턴 (10%)
if any("매출액" == c.get('account_nm') for c in candidates):
    return next(c for c in candidates if "매출액" == c.get('account_nm'))

# LLM 필요 (10%)
else:
    return llm_matcher.select_best(candidates)
```

---

## 5. v9 구현 전략 (수정)

### Phase 1: Rule-based (v1, 즉시)

**범위**:
- 명확한 필터링만
- LLM 없이 작동 가능
- 80% 케이스 커버

```python
class SimpleRuleMatcher:
    """단순 Rule 매칭 (LLM 없이)"""
    
    def find_revenue(self, financials):
        # 1. "매출", "수익" 포함 수집
        candidates = [
            item for item in financials
            if any(kw in item.get('account_nm', '') 
                   for kw in ['매출', '수익', '영업'])
        ]
        
        # 2. 명확한 제외
        candidates = [
            c for c in candidates
            if not any(ex in c.get('account_nm', '') 
                      for ex in ['자산', '부채', '채권', '원가'])
        ]
        
        # 3. Fallback: 가장 큰 금액
        if candidates:
            return max(candidates, 
                      key=lambda x: abs(float(x.get('thstrm_amount', 0))))
        
        return None
```

### Phase 2: LLM Integration (v2, 1-2주)

**추가**:
- LLMBasedMatcher
- AccountMatcher (Hybrid)
- Confidence 조정

```python
class AccountMatcher:
    """Rule + LLM Hybrid"""
    
    def find_revenue(self, financials, context, use_llm=True):
        # Rule 먼저
        candidates = rule_matcher.filter(financials)
        
        if len(candidates) == 1:
            return candidates[0]  # 확실
        
        if not use_llm:
            # LLM 없이: 가장 큰 금액
            return max(candidates, key=lambda x: ...)
        
        # LLM 사용
        return llm_matcher.select_best(candidates, context)
```

---

## 6. 즉시 수정안 (v1)

### 현재 문제

```python
# ❌ 하드코딩
revenue_keywords = [
    ['매출액'],      # 1순위
    ['영업수익'],    # 2순위 ← 하드코딩!
    ['수익', '매출'], # 3순위
]
```

### 올바른 v1 구현

```python
# ✅ Rule + Fallback (하드코딩 없음)
def find_revenue_account(financials):
    """매출액 계정 찾기 (Rule + Fallback)
    
    전략:
    1. 포함 키워드로 후보 수집
    2. 제외 키워드로 필터링
    3. 가장 큰 금액 선택 (Fallback)
    """
    # 1. 후보 수집 (넓게)
    candidates = [
        item for item in financials
        if any(kw in item.get('account_nm', '') 
               for kw in ['매출', '수익', '영업'])
    ]
    
    # 2. 명확한 제외 (좁게)
    EXCLUDE = ['자산', '부채', '채권', '채무', '원가', '비용', '현금']
    
    candidates = [
        c for c in candidates
        if not any(ex in c.get('account_nm', '') for ex in EXCLUDE)
    ]
    
    if not candidates:
        return None
    
    # 3. Fallback: 가장 큰 금액
    # 이유: 매출액은 일반적으로 가장 큰 "수익" 항목
    return max(
        candidates,
        key=lambda x: abs(float(x.get('thstrm_amount', 0)))
    )
```

**장점**:
- 하드코딩 없음
- 새 케이스 자동 처리
- 단순하지만 효과적

**커버리지**: 80-90% (검증 필요)

---

## 7. v2 LLM 통합 (향후)

### LLM Prompt 예시

```
회사: 삼성전자
연도: 2023

재무제표 항목:
0. 매출채권: 27.36조원
1. 영업이익: -11.53조원
2. 매출원가: 144.02조원
3. 영업수익: 170.37조원
4. 매출총이익: 26.35조원

질문: 이 중에서 "매출액 (Revenue)"에 해당하는 항목은?

응답: 3 (영업수익)
이유: "영업수익"은 삼성전자의 매출액 표현입니다.
```

### Confidence 조정

```python
if matched_by == "rule" and len(candidates) == 1:
    confidence = 0.95  # 확실

elif matched_by == "rule" and len(candidates) > 1:
    confidence = 0.85  # Fallback

elif matched_by == "llm":
    confidence = 0.90  # LLM 해석

else:
    confidence = 0.70  # 불확실
```

---

## 8. 구현 우선순위

### v1 (즉시 수정, 1시간)

**변경**:
```python
# ❌ 제거
revenue_keywords = [['매출액'], ['영업수익'], ...]

# ✅ 추가
def _find_revenue_with_fallback(financials):
    # Rule + 가장 큰 금액 Fallback
    ...
```

**테스트**:
- 3개 기업 재검증 (YBM, 삼성, LG)
- 추가 기업 (하이브, GS리테일 등)

### v2 (LLM 통합, 1-2주)

**추가**:
- AccountMatcher
- LLMBasedMatcher
- Confidence 조정

**테스트**:
- 10+ 기업
- Edge cases
- LLM vs Rule 비교

---

## 9. 즉시 조치 사항

### 수정 필요 파일

**cmis_core/evidence/dart_connector.py**:
```python
# 현재 (❌ 하드코딩)
revenue_keywords = [
    ['매출액'],
    ['영업수익'],  # ← 제거
    ...
]

# 수정 (✅ Rule + Fallback)
def _find_revenue_account(financials):
    # 포함 키워드 (넓게)
    candidates = [...]
    
    # 제외 키워드 (명확)
    filtered = [...]
    
    # Fallback: 가장 큰 금액
    return max(filtered, key=...)
```

### 테스트 추가

**dev/tests/integration/test_dart_edge_cases.py**:
- 특수 계정과목 (10+ 회사)
- Fallback 검증
- 금액 범위 체크

---

## 10. 최종 설계 원칙

### ✅ 올바른 접근

1. **Rule-based**: 명확한 패턴만
2. **Fallback**: 가장 큰 금액 (통계적으로 합리적)
3. **LLM**: 애매한 경우만 (v2)
4. **No 하드코딩**: 특정 회사/키워드 고정 금지

### ❌ 피해야 할 접근

1. 특정 회사 분기 처리
2. 끝없는 키워드 Dictionary
3. 우선순위 하드코딩

---

**다음 작업**: dart_connector.py 수정 (Rule + Fallback)

**예상 시간**: 1시간

**검증**: 10+ 기업 테스트

---

**작성**: 2025-12-09
**상태**: 설계 수정 완료
**다음**: 즉시 구현
