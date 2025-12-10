"""Base Search Source

웹 검색 공통 로직 (Google, DuckDuckGo 등)
"""

from __future__ import annotations

import re
import statistics
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from ..types import EvidenceRequest, EvidenceRecord, EvidenceValueKind, SourceTier
from ..evidence_engine import BaseDataSource, DataNotFoundError


class BaseSearchSource(BaseDataSource):
    """웹 검색 Base Class
    
    공통 기능:
    - 검색 쿼리 구성
    - 숫자 추출 (정규식)
    - Consensus 알고리즘
    - 페이지 크롤링
    
    하위 클래스:
    - GoogleSearchSource
    - DuckDuckGoSource
    """
    
    def __init__(
        self,
        source_id: str,
        source_tier: SourceTier,
        capabilities: Dict[str, Any],
        fetch_full_page: bool = False,
        max_results: int = 5,
        timeout: int = 10
    ):
        super().__init__(source_id, source_tier, capabilities)
        
        self.fetch_full_page = fetch_full_page
        self.max_results = max_results
        self.timeout = timeout
    
    # ========================================
    # Abstract: 검색 API (하위 클래스 구현)
    # ========================================
    
    def _search(self, query: str) -> List[Dict[str, Any]]:
        """검색 API 호출 (하위 클래스에서 구현)
        
        Args:
            query: 검색 쿼리
        
        Returns:
            검색 결과 리스트
        """
        raise NotImplementedError("Subclass must implement _search()")
    
    # ========================================
    # 공통: 쿼리 구성
    # ========================================
    
    def build_search_query(self, request: EvidenceRequest) -> str:
        """검색 쿼리 구성 (개선)"""
        parts = []
        
        # domain_id
        domain = request.context.get("domain_id", "")
        if domain:
            domain_words = domain.replace("_", " ").lower()
            parts.append(domain_words)
        
        # region
        region = request.context.get("region", "")
        if region:
            region_map = {"KR": "Korea", "US": "United States", "JP": "Japan"}
            parts.append(region_map.get(region, region))
        
        # metric_id - 더 구체적인 키워드
        if request.metric_id:
            metric_id = request.metric_id.lower()
            
            # Revenue, TAM 등은 "market size" 추가
            if "revenue" in metric_id or "tam" in metric_id:
                parts.append("market size")
            
            if "revenue" in metric_id:
                parts.append("revenue")
            elif "tam" in metric_id:
                parts.append("total addressable market")
            else:
                metric_word = request.metric_id.replace("MET-", "").replace("_", " ").lower()
                parts.append(metric_word)
        
        # year
        year = request.context.get("year")
        if year:
            parts.append(str(year))
        
        query = " ".join(parts)
        return query or "market data"
    
    # ========================================
    # 공통: 숫자 추출
    # ========================================
    
    def extract_numbers(
        self,
        results: List[Dict[str, Any]]
    ) -> List[float]:
        """검색 결과에서 숫자 추출 (공통)"""
        numbers = []
        
        for result in results:
            # 텍스트 추출
            if 'full_content' in result:
                text = result['full_content']
            elif 'body' in result:
                text = result['body']
            else:
                text = result.get('snippet', '')
            
            # 숫자 추출
            extracted = self.extract_numbers_from_text(text)
            numbers.extend(extracted)
        
        return numbers
    
    def extract_all_evidence_with_hints(
        self,
        results: List[Dict[str, Any]],
        request: EvidenceRequest
    ) -> Dict[str, Any]:
        """모든 Evidence 추출 (primary + hints)
        
        Args:
            results: 검색 결과
            request: Evidence 요청
        
        Returns:
            {
                "primary": {"value": float, "confidence": float},
                "all_numbers": [float, ...],
                "hints": [
                    {
                        "value": float,
                        "context": str,
                        "snippet": str,
                        "url": str,
                        "confidence": float
                    }
                ]
            }
        """
        all_numbers = []
        hints = []
        
        for i, result in enumerate(results):
            # 텍스트 추출
            if 'full_content' in result:
                text = result['full_content']
            elif 'body' in result:
                text = result['body']
            else:
                text = result.get('snippet', '')
            
            # 숫자 추출
            result_numbers = self.extract_numbers_from_text(text)
            all_numbers.extend(result_numbers)
            
            # Hint로 저장
            for num in result_numbers:
                hints.append({
                    "value": num,
                    "context": result.get('title', '')[:100],
                    "snippet": text[:200],
                    "source_url": result.get('link', '') or result.get('href', ''),
                    "confidence": 0.5,  # Hint 기본 신뢰도
                    "result_index": i,
                    "metric_id": request.metric_id,
                    "domain_id": request.context.get("domain_id", ""),
                    "region": request.context.get("region", "")
                })
        
        # Primary (consensus)
        if all_numbers:
            primary_value, primary_confidence = self.calculate_consensus(all_numbers)
        else:
            primary_value, primary_confidence = None, 0.0
        
        return {
            "primary": {
                "value": primary_value,
                "confidence": primary_confidence
            },
            "all_numbers": all_numbers,
            "hints": hints
        }
    
    def extract_numbers_from_text(self, text: str) -> List[float]:
        """텍스트에서 숫자 추출 (공통)
        
        패턴:
        - 한국어: "100억", "1.2조"
        - 영어: "$500M", "$1.5B"
        - 숫자: "1,234,567"
        """
        numbers = []
        
        # 한국어 (억, 조)
        pattern_kr = r'([\d,\.]+)\s*(억|조)원?'
        matches = re.findall(pattern_kr, text)
        
        for match in matches:
            try:
                num = float(match[0].replace(',', ''))
                unit = match[1]
                
                if unit == '억':
                    num *= 100_000_000
                elif unit == '조':
                    num *= 1_000_000_000_000
                
                numbers.append(num)
            except ValueError:
                continue
        
        # 영어 (M, B, T)
        pattern_en = r'\$?\s*([\d,\.]+)\s*([MBT])'
        matches = re.findall(pattern_en, text, re.IGNORECASE)
        
        for match in matches:
            try:
                num = float(match[0].replace(',', ''))
                unit = match[1].upper()
                
                if unit == 'M':
                    num *= 1_000_000
                elif unit == 'B':
                    num *= 1_000_000_000
                elif unit == 'T':
                    num *= 1_000_000_000_000
                
                numbers.append(num)
            except ValueError:
                continue
        
        # 순수 숫자 (큰 수만)
        pattern_num = r'([\d,]+)'
        matches = re.findall(pattern_num, text)
        
        for match in matches:
            try:
                num_str = match.replace(',', '')
                if len(num_str) >= 7:  # 100만 이상
                    num = float(num_str)
                    numbers.append(num)
            except ValueError:
                continue
        
        return numbers
    
    # ========================================
    # 공통: Consensus
    # ========================================
    
    def calculate_consensus(
        self,
        numbers: List[float]
    ) -> tuple[float, float]:
        """Consensus 계산 (공통)
        
        Returns:
            (value, confidence)
        """
        if not numbers:
            return 0.0, 0.0
        
        if len(numbers) == 1:
            return numbers[0], self.get_single_source_confidence()
        
        # Outlier 제거
        filtered = self.remove_outliers(numbers) if len(numbers) >= 4 else numbers
        
        # 중앙값
        value = statistics.median(filtered)
        
        # Confidence
        confidence = self.calculate_confidence(filtered)
        
        return value, confidence
    
    def remove_outliers(self, numbers: List[float]) -> List[float]:
        """Outlier 제거 (IQR, 공통)"""
        if len(numbers) < 4:
            return numbers
        
        sorted_nums = sorted(numbers)
        q1 = statistics.median(sorted_nums[:len(sorted_nums)//2])
        q3 = statistics.median(sorted_nums[len(sorted_nums)//2:])
        iqr = q3 - q1
        
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        
        filtered = [n for n in numbers if lower <= n <= upper]
        return filtered if filtered else numbers
    
    def calculate_confidence(self, numbers: List[float]) -> float:
        """Confidence 계산 (공통)"""
        if not numbers:
            return 0.0
        
        if len(numbers) == 1:
            return self.get_single_source_confidence()
        
        # Source 개수 점수
        count_score = min(len(numbers) / 10, 0.2)
        
        # 분산 점수
        if len(numbers) >= 2:
            mean = statistics.mean(numbers)
            stdev = statistics.stdev(numbers)
            cv = stdev / mean if mean > 0 else 1.0
            variance_score = max(0, 0.25 * (1 - cv))
        else:
            variance_score = 0.1
        
        # 기본 + 보너스
        base = self.get_base_confidence()
        confidence = base + count_score + variance_score
        
        return min(confidence, self.get_max_confidence())
    
    # ========================================
    # 공통: 페이지 크롤링
    # ========================================
    
    def fetch_page_content(self, url: str) -> Optional[str]:
        """웹 페이지 크롤링 (공통)"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                tag.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            text = ' '.join(text.split())
            
            if len(text) > 10000:
                text = text[:10000]
            
            return text
        
        except (requests.Timeout, requests.RequestException, Exception):
            return None
    
    # ========================================
    # 하위 클래스 Override 가능
    # ========================================
    
    def get_base_confidence(self) -> float:
        """기본 Confidence (하위 클래스 override 가능)"""
        return 0.5
    
    def get_single_source_confidence(self) -> float:
        """단일 source Confidence"""
        return 0.6
    
    def get_max_confidence(self) -> float:
        """최대 Confidence"""
        return 0.85
