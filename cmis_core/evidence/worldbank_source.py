"""World Bank API Source

세계은행 국가별 경제/사회 지표 조회

2025-12-10: OFFICIAL Tier 확장 (글로벌)
- GDP, 인구, 교육, 인터넷 보급률 등
- Official tier, Confidence: 0.95
- 인증 불필요 (Public API)

API: https://api.worldbank.org/v2/
문서: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

from __future__ import annotations

import os
import uuid
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

import requests

from ..types import (
    EvidenceRequest,
    EvidenceRecord,
    EvidenceValueKind,
    SourceTier,
)
from ..evidence_engine import (
    BaseDataSource,
    DataNotFoundError,
    SourceNotAvailableError,
    SourceTimeoutError,
)


class WorldBankSource(BaseDataSource):
    """World Bank API Source

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
    """

    # YAML에서 로딩
    _indicators_cache = None

    @classmethod
    def _load_indicators(cls) -> Dict:
        """config/sources/worldbank_indicators.yaml 로딩"""
        if cls._indicators_cache is not None:
            return cls._indicators_cache

        config_path = Path(__file__).parent.parent.parent / "config" / "sources" / "worldbank_indicators.yaml"

        if not config_path.exists():
            # Fallback
            return {
                "gdp": {
                    "indicator_code": "NY.GDP.MKTP.CD",
                    "name": "GDP",
                    "unit": "current US$"
                }
            }

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 리스트 → 딕셔너리
        indicators = {}
        for indicator in data.get("indicators", []):
            stat_type = indicator.pop("stat_type")
            indicators[stat_type] = indicator

        cls._indicators_cache = indicators
        return indicators

    @property
    def INDICATORS(self):
        """동적 로딩"""
        return self._load_indicators()

    def __init__(
        self,
        timeout: int = 10
    ):
        """
        Args:
            timeout: 요청 timeout (초)
        """
        super().__init__(
            source_id="WorldBank",
            source_tier=SourceTier.OFFICIAL,
            capabilities={
                "provides": [
                    "gdp_stats",
                    "population_stats",
                    "education_stats",
                    "internet_penetration",
                    "macro_economic_global"
                ],
                "regions": ["*"],  # 모든 국가
                "data_types": ["numeric"]
            }
        )

        self.base_url = "https://api.worldbank.org/v2"
        self.timeout = timeout

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """Evidence 수집

        Args:
            request: EvidenceRequest

        Returns:
            EvidenceRecord
        """
        # 1. 지표 유형 결정
        stat_type = self._determine_stat_type(request)

        if not stat_type:
            raise DataNotFoundError("Cannot determine WorldBank indicator")

        indicator_info = self.INDICATORS.get(stat_type)

        if not indicator_info:
            raise DataNotFoundError(f"Unknown stat type: {stat_type}")

        # 2. 국가 코드 변환
        region = request.context.get("region", "KR")
        country_code = self._region_to_country_code(region)

        # 3. API 호출
        try:
            data = self._fetch_indicator_data(
                country_code,
                indicator_info["indicator_code"],
                request.context
            )
        except requests.Timeout:
            raise SourceTimeoutError("World Bank API timeout")
        except Exception as e:
            raise SourceNotAvailableError(f"World Bank API error: {e}")

        if not data:
            raise DataNotFoundError(f"No World Bank data for {stat_type}")

        # 4. 데이터 파싱
        value = self._parse_indicator_data(data)

        if value is None:
            raise DataNotFoundError("Cannot parse World Bank data")

        # 5. EvidenceRecord 생성
        return EvidenceRecord(
            evidence_id=f"EVD-WorldBank-{uuid.uuid4().hex[:8]}",
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=value,
            value_kind=EvidenceValueKind.NUMERIC,
            schema_ref="worldbank_v1",
            confidence=0.95,  # 공식 통계
            metadata={
                "stat_type": stat_type,
                "indicator_code": indicator_info["indicator_code"],
                "indicator_name": indicator_info["name"],
                "unit": indicator_info["unit"],
                "country_code": country_code,
                "context": request.context
            },
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            lineage={
                "api": "worldbank_v2",
                "indicator": indicator_info["indicator_code"]
            }
        )

    def can_handle(self, request: EvidenceRequest) -> bool:
        """처리 가능 여부"""
        stat_type = self._determine_stat_type(request)
        return stat_type is not None

    def _fetch_indicator_data(
        self,
        country_code: str,
        indicator_code: str,
        context: Dict[str, Any]
    ) -> Optional[List[Dict]]:
        """World Bank 지표 데이터 조회

        API: /v2/country/{country}/indicator/{indicator}?format=json&date={year}

        Args:
            country_code: 국가 코드 (ISO 3166-1 alpha-3)
            indicator_code: 지표 코드 (예: NY.GDP.MKTP.CD)
            context: 컨텍스트 (year 등)

        Returns:
            지표 데이터 리스트
        """
        # Year 설정
        year = context.get("year", "2023")

        # URL 구성
        url = (
            f"{self.base_url}/country/{country_code}/"
            f"indicator/{indicator_code}"
            f"?format=json&date={year}"
        )

        try:
            response = requests.get(url, timeout=self.timeout)

            if response.status_code != 200:
                raise SourceNotAvailableError(
                    f"World Bank API HTTP {response.status_code}"
                )

            data = response.json()

            # World Bank는 [metadata, data] 형식
            if not isinstance(data, list) or len(data) < 2:
                raise DataNotFoundError("Invalid World Bank response")

            result_data = data[1]

            if not result_data:
                raise DataNotFoundError("No data in response")

            return result_data

        except requests.Timeout:
            raise SourceTimeoutError("World Bank API timeout")
        except (DataNotFoundError, SourceNotAvailableError, SourceTimeoutError):
            raise
        except Exception as e:
            raise SourceNotAvailableError(f"World Bank API failed: {e}")

    def _parse_indicator_data(self, data: Any) -> Optional[float]:
        """World Bank 데이터 파싱

        Args:
            data: World Bank API 응답

        Returns:
            파싱된 값
        """
        if not isinstance(data, list):
            return None

        if not data:
            return None

        # 첫 번째 항목 (최신 또는 요청한 연도)
        first_item = data[0]
        value = first_item.get('value')

        if value is None:
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _determine_stat_type(self, request: EvidenceRequest) -> Optional[str]:
        """지표 유형 결정 (패턴 매칭, YAML 기반)

        Args:
            request: EvidenceRequest

        Returns:
            stat_type or None
        """
        # Context 명시적 지정
        if "stat_type" in request.context:
            return request.context["stat_type"]

        # YAML의 keywords 기반 매칭
        search_text = f"{request.metric_id or ''} {request.context}".lower()

        for stat_type, info in self.INDICATORS.items():
            keywords = info.get("keywords", [])
            exclude = info.get("exclude_keywords", [])

            # Keywords 매칭
            if any(kw in search_text for kw in keywords):
                # Exclude keywords 체크
                if not any(ex in search_text for ex in exclude):
                    return stat_type

        return None

    def _region_to_country_code(self, region: str) -> str:
        """Region → World Bank 국가 코드

        Args:
            region: Region 코드

        Returns:
            ISO 3166-1 alpha-3 코드
        """
        # 간단한 매핑 (향후 YAML로 이동 가능)
        mapping = {
            "KR": "KOR",
            "US": "USA",
            "JP": "JPN",
            "CN": "CHN",
            "GB": "GBR",
            "DE": "DEU",
            "FR": "FRA"
        }

        return mapping.get(region, region)


