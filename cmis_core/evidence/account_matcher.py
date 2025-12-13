"""Account Matcher

DART 계정과목 매칭 (Rule + LLM Hybrid)
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any

from ..llm.service import LLMService
from ..llm.types import CMISTaskType


class AccountMatcher:
    """계정과목 매칭 (Rule + LLM Hybrid)

    전략:
    1. Rule-based Filtering (넓게 수집, 명확히 제외)
    2. Fallback: 가장 큰 금액
    3. LLM (선택적): 여러 후보 중 최적 선택
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Args:
            llm_service: LLMService (None이면 LLM 미사용)
        """
        self.llm = llm_service

    def find_account(
        self,
        financials: List[Dict],
        target_metric: str,
        context: Optional[Dict] = None,
        use_llm: bool = False
    ) -> Optional[Dict]:
        """계정과목 찾기

        Args:
            financials: 재무제표 항목 리스트
            target_metric: 찾을 지표 (예: "매출액", "영업이익")
            context: 컨텍스트 (company_name, year 등)
            use_llm: LLM 사용 여부

        Returns:
            매칭된 항목 or None
        """
        # Step 1: Rule-based Filtering
        candidates = self._filter_candidates(financials, target_metric)

        if not candidates:
            return None

        # 1개면 확실
        if len(candidates) == 1:
            return candidates[0]

        # Step 2: LLM 선택 (선택적)
        if use_llm and self.llm and len(candidates) <= 10:
            try:
                return self._select_with_llm(candidates, target_metric, context)
            except Exception:
                # LLM 실패 시 Fallback
                pass

        # Step 3: Fallback - 가장 큰 금액
        return self._select_by_amount(candidates)

    def _filter_candidates(
        self,
        financials: List[Dict],
        target_metric: str
    ) -> List[Dict]:
        """후보 필터링 (Rule-based)"""
        # Metric별 포함 키워드
        INCLUDE_MAP = {
            "매출액": ['매출', '수익', '영업'],
            "영업이익": ['영업이익', '영업손익'],
            "순이익": ['순이익', '당기순'],
        }

        include_keywords = INCLUDE_MAP.get(target_metric, [target_metric])

        # 포함 키워드로 수집
        candidates = [
            item for item in financials
            if any(kw in item.get('account_nm', '') for kw in include_keywords)
        ]

        # 명확한 제외
        EXCLUDE = ['자산', '부채', '채권', '채무', '원가', '비용', '현금', '예금']

        filtered = [
            c for c in candidates
            if not any(ex in c.get('account_nm', '') for ex in EXCLUDE)
        ]

        return filtered

    def _select_by_amount(self, candidates: List[Dict]) -> Dict:
        """가장 큰 금액 선택 (Fallback)"""
        return max(
            candidates,
            key=lambda x: abs(float(x.get('thstrm_amount', 0)))
        )

    def _select_with_llm(
        self,
        candidates: List[Dict],
        target_metric: str,
        context: Optional[Dict]
    ) -> Optional[Dict]:
        """LLM으로 최적 선택

        Args:
            candidates: 후보 리스트 (2~10개)
            target_metric: 목표 지표
            context: 컨텍스트

        Returns:
            선택된 항목
        """
        # Prompt 구성
        prompt = self._build_llm_prompt(candidates, target_metric, context)

        # LLM 호출
        response = self.llm.call(
            CMISTaskType.EVIDENCE_ACCOUNT_MATCHING,
            prompt,
            context=context
        )

        # 응답 파싱 (숫자 추출)
        selected_idx = self._parse_llm_response(response)

        if selected_idx is not None and 0 <= selected_idx < len(candidates):
            return candidates[selected_idx]

        # 파싱 실패 → Fallback
        return self._select_by_amount(candidates)

    def _build_llm_prompt(
        self,
        candidates: List[Dict],
        target_metric: str,
        context: Optional[Dict]
    ) -> str:
        """LLM Prompt 생성"""
        company = context.get('company_name', '') if context else ''
        year = context.get('year', '') if context else ''

        concept_map = {
            "매출액": "매출액 (Revenue)",
            "영업이익": "영업이익 (Operating Income)",
            "순이익": "순이익 (Net Income)",
        }

        target_name = concept_map.get(target_metric, target_metric)

        prompt = f"""다음은 {company}의 {year}년 재무제표 항목입니다.
이 중에서 "{target_name}"에 해당하는 항목을 선택해주세요.

항목 목록:
"""

        for i, item in enumerate(candidates):
            account_nm = item.get('account_nm', '')
            amount = float(item.get('thstrm_amount', 0))

            prompt += f"{i}. {account_nm}: {amount/1_000_000_000_000:.2f}조원\n"

        prompt += f"""
"{target_name}"에 가장 적합한 항목의 번호를 선택하세요.
애매한 경우, 금액이 가장 큰 것을 선택하세요.

응답 형식: 숫자만 (예: 0, 1, 2)
"""

        return prompt

    def _parse_llm_response(self, response: str) -> Optional[int]:
        """LLM 응답 파싱 (숫자 추출)"""
        import re

        # 첫 번째 숫자 추출
        match = re.search(r'\d+', response)

        if match:
            return int(match.group())

        return None


