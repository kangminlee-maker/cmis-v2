"""SG&A Extractor

판매비와관리비 세부 항목 추출 (HTML + LLM)

v7 대비 개선:
- HTML 크롤링 간소화
- LLM으로 항목 해석 (유연성 향상)
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

from ..llm.service import LLMService
from ..llm.types import CMISTaskType
from .dart_connector import DARTConnector


class SGAExtractor:
    """SG&A 세부 항목 추출

    프로세스:
    1. DART API로 사업보고서 원문 다운로드
    2. HTML에서 판관비 섹션 추출
    3. LLM으로 세부 항목 해석
    """

    def __init__(
        self,
        dart_connector: DARTConnector,
        llm_service: Optional[LLMService] = None
    ):
        """
        Args:
            dart_connector: DARTConnector
            llm_service: LLMService (None이면 Rule-based만)
        """
        self.dart = dart_connector
        self.llm = llm_service

    def extract_sga_details(
        self,
        company_name: str,
        year: int,
        use_llm: bool = True
    ) -> Optional[Dict]:
        """SG&A 세부 항목 추출

        Args:
            company_name: 회사명
            year: 사업연도
            use_llm: LLM 사용 여부

        Returns:
            {
                "company": str,
                "year": int,
                "items": {항목명: 금액(억원)},
                "total": float,
                "method": "llm" or "rule"
            }
        """
        # 1. 기업 코드
        corp_code = self.dart.get_corp_code(company_name)
        if not corp_code:
            return None

        # 2. 사업보고서 접수번호
        rcept_no = self._get_annual_report_rcept_no(corp_code, year)
        if not rcept_no:
            return None

        # 3. 원문 다운로드 (ZIP)
        xml_content = self.dart.download_document(rcept_no)
        if not xml_content:
            return None

        # 4. 판관비 섹션 추출
        sga_section = self._extract_sga_section(xml_content)
        if not sga_section:
            return None

        # 5. 세부 항목 추출
        if use_llm and self.llm:
            items = self._extract_with_llm(sga_section, company_name, year)
        else:
            items = self._extract_with_rule(sga_section)

        if not items:
            return None

        return {
            "company": company_name,
            "year": year,
            "items": items,
            "total": sum(items.values()),
            "method": "llm" if (use_llm and self.llm) else "rule"
        }

    def _get_annual_report_rcept_no(
        self,
        corp_code: str,
        year: int
    ) -> Optional[str]:
        """사업보고서 접수번호 조회

        사업연도 year → year+1년 3월 공시
        """
        reports = self.dart.get_report_list(corp_code, year)

        if not reports:
            return None

        # 원본 사업보고서 찾기 ([첨부정정], [기재정정] 제외)
        for report in reports:
            report_nm = report.get('report_nm', '')

            if '사업보고서' in report_nm:
                # [xxx] 형태의 수식어 제외
                if '[' not in report_nm:
                    return report.get('rcept_no')

        # 못 찾으면 첫 번째 사업보고서
        for report in reports:
            if '사업보고서' in report.get('report_nm', ''):
                return report.get('rcept_no')

        return None

    def _extract_sga_section(self, xml_content: str) -> Optional[str]:
        """XML에서 판관비 세부 테이블 추출

        전략:
        1. BeautifulSoup으로 모든 테이블 찾기
        2. "급여", "복리후생", "광고", "감가상각" 포함 테이블 선택

        Args:
            xml_content: DART 원문 XML/HTML

        Returns:
            SG&A 테이블 HTML or None
        """
        soup = BeautifulSoup(xml_content, 'html.parser')
        tables = soup.find_all('table')

        # SG&A 특징 키워드
        required_keywords = ['급여', '복리후생']  # 필수
        bonus_keywords = ['광고', '감가상각']      # 추가 점수

        best_table = None
        best_score = 0

        for table in tables:
            table_text = table.get_text()

            # 점수 계산
            score = 0

            for kw in required_keywords:
                if kw in table_text:
                    score += 10

            for kw in bonus_keywords:
                if kw in table_text:
                    score += 5

            # 최소 점수 (급여, 복리후생 모두 있어야)
            if score >= 20 and score > best_score:
                best_score = score
                best_table = table

        if best_table:
            return str(best_table)

        return None

    def _extract_with_llm(
        self,
        sga_section: str,
        company_name: str,
        year: int
    ) -> Optional[Dict[str, float]]:
        """LLM으로 SG&A 세부 항목 추출

        Args:
            sga_section: 판관비 테이블 HTML
            company_name: 회사명
            year: 연도

        Returns:
            {항목명: 금액(억원)}
        """
        # sga_section은 이미 테이블 HTML
        soup = BeautifulSoup(sga_section, 'html.parser')
        table_text = soup.get_text()

        # LLM Prompt (간결하게)
        prompt = f"""{company_name} {year}년 판매비와관리비 테이블:

{table_text}

세부 항목과 "당기" 금액을 JSON으로 추출하세요.

JSON만 출력:
{{"급여": 2432031, "퇴직급여": 143109, "복리후생비": 496669, ...}}

주의:
- 단위: 백만원 그대로 (변환하지 마세요!)
- "합계" 제외
- 숫자만 (콤마 제거)
"""

        # LLM 호출
        try:
            response = self.llm.call_structured(
                CMISTaskType.EVIDENCE_NUMBER_EXTRACTION,
                prompt,
                context={"company_name": company_name, "year": year}
            )

            # JSON 파싱 성공 시
            if isinstance(response, dict) and "raw" not in response:
                items = {}

                for key, val in response.items():
                    # "합계" 제외
                    if key in ['합계', '합', '총계', '계']:
                        continue

                    try:
                        amount_million = float(val)  # 백만원
                        amount_billion = amount_million / 100  # 억원으로 변환

                        # 최소값 (0.1억원)
                        if amount_billion > 0.1:
                            items[key] = amount_billion
                    except (ValueError, TypeError):
                        continue

                return items if items else None

            # raw 응답이면 Rule-based fallback
            return self._extract_with_rule(sga_section)

        except Exception:
            return self._extract_with_rule(sga_section)

    def _extract_with_rule(self, sga_section: str) -> Optional[Dict[str, float]]:
        """Rule-based 추출 (v7 로직 간소화)

        Args:
            sga_section: 판관비 섹션

        Returns:
            {항목명: 금액(억원)}
        """
        soup = BeautifulSoup(sga_section, 'html.parser')
        tables = soup.find_all('table')

        if not tables:
            return None

        table = tables[0]
        rows = table.find_all('tr')

        # 단위 감지
        table_text = table.get_text()
        unit = '백만원'  # 기본

        unit_match = re.search(r'단위\s*[:：]\s*(백만원|천원|억원|원)', table_text)
        if unit_match:
            unit = unit_match.group(1)

        items = {}

        for row in rows:
            cells = row.find_all(['td', 'th'])

            if len(cells) >= 2:
                item_name = cells[0].get_text(strip=True)
                amount_str = cells[1].get_text(strip=True)

                # 숫자 추출
                amount_clean = re.sub(r'[^\d-]', '', amount_str)

                if item_name and amount_clean:
                    # 헤더/합계 제외
                    if item_name in ['과목', '당기', '전기', '합계', '계']:
                        continue

                    if re.match(r'^(합|총|소)\s*계$', item_name):
                        continue

                    try:
                        amount = float(amount_clean)

                        # 단위 변환 (억원으로)
                        if unit == '백만원':
                            amount_billion = amount / 100
                        elif unit == '천원':
                            amount_billion = amount / 100_000
                        elif unit == '원':
                            amount_billion = amount / 100_000_000
                        else:
                            amount_billion = amount

                        if amount_billion > 0.1:  # 최소 0.1억원
                            items[item_name] = amount_billion

                    except ValueError:
                        continue

        return items if items else None


