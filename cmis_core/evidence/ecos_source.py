"""ECOS (한국은행 경제통계) Source

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


class ECOSSource(BaseDataSource):
    """ECOS (한국은행 경제통계시스템) API Source

    기능:
    - GDP 조회 (국내총생산)
    - CPI 조회 (소비자물가지수)
    - 금리 조회 (기준금리, 예금은행 금리)
    - 산업생산지수
    - 통화량

    API 문서: https://ecos.bok.or.kr/api/
    """

    # YAML에서 로딩 (하드코딩 제거)
    _statistics_cache = None

    @classmethod
    def _load_key_statistics(cls) -> Dict:
        """config/sources/ecos_statistics.yaml 로딩"""
        if cls._statistics_cache is not None:
            return cls._statistics_cache

        config_path = Path(__file__).parent.parent.parent / "config" / "sources" / "ecos_statistics.yaml"

        if not config_path.exists():
            # Fallback
            return {
                "gdp": {
                    "keyword": "GDP(명목, 계절조정)",
                    "name": "GDP",
                    "unit": "십억원"
                }
            }

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 리스트 → 딕셔너리
        stats = {}
        for stat in data.get("statistics", []):
            stat_type = stat.pop("stat_type")
            stats[stat_type] = stat

        cls._statistics_cache = stats
        return stats

    @property
    def KEY_STATISTICS(self):
        """동적 로딩"""
        return self._load_key_statistics()

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 10
    ):
        """
        Args:
            api_key: ECOS API Key (None이면 환경변수)
            timeout: 요청 timeout (초)
        """
        super().__init__(
            source_id="ECOS",
            source_tier=SourceTier.OFFICIAL,
            capabilities={
                "provides": [
                    "gdp_stats",
                    "cpi_stats",
                    "interest_rate",
                    "monetary_stats",
                    "industrial_production"
                ],
                "regions": ["KR"],
                "data_types": ["numeric"]
            }
        )

        self.api_key = api_key or os.getenv("ECOS_API_KEY")
        self.base_url = "https://ecos.bok.or.kr/api"
        self.timeout = timeout

        if not self.api_key:
            raise SourceNotAvailableError(
                "ECOS_API_KEY required. "
                "Get key at: https://ecos.bok.or.kr/api/"
            )

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """Evidence 수집

        프로세스:
        1. Context에서 통계 유형 결정
        2. 적절한 통계표 선택
        3. ECOS API 호출
        4. 데이터 파싱
        5. EvidenceRecord 생성

        Args:
            request: EvidenceRequest

        Returns:
            EvidenceRecord

        Raises:
            DataNotFoundError: 데이터 없음
            SourceTimeoutError: Timeout
            SourceNotAvailableError: API 오류
        """
        # 1. 통계 유형 결정
        stat_type = self._determine_stat_type(request)

        if not stat_type:
            raise DataNotFoundError("Cannot determine ECOS stat type from request")

        stat_info = self.KEY_STATISTICS.get(stat_type)

        if not stat_info:
            raise DataNotFoundError(f"Unknown stat type: {stat_type}")

        # 2. API 호출 (100대 통계지표)
        try:
            data = self._fetch_key_statistic(
                stat_info["keyword"],
                request.context
            )
        except requests.Timeout:
            raise SourceTimeoutError(f"ECOS API timeout")
        except Exception as e:
            raise SourceNotAvailableError(f"ECOS API error: {e}")

        if not data:
            raise DataNotFoundError(f"No ECOS data for {stat_type}")

        # 3. 데이터 파싱
        value = self._parse_stat_data(data, request)

        if value is None:
            raise DataNotFoundError(f"Cannot parse ECOS data")

        # 4. EvidenceRecord 생성
        return EvidenceRecord(
            evidence_id=f"EVD-ECOS-{uuid.uuid4().hex[:8]}",
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=value,
            value_kind=EvidenceValueKind.NUMERIC,
            schema_ref="ecos_stats_v1",
            confidence=0.95,  # 공식 통계는 신뢰도 높음
            metadata={
                "stat_type": stat_type,
                "keyword": stat_info["keyword"],
                "stat_name": stat_info["name"],
                "unit": stat_info["unit"],
                "context": request.context
            },
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            lineage={
                "api": "ecos_keystatistic",
                "keyword": stat_info["keyword"]
            }
        )

    def can_handle(self, request: EvidenceRequest) -> bool:
        """처리 가능 여부

        조건:
        - region: KR만 지원
        - GDP/CPI/금리 관련 metric
        """
        # KR region만 지원
        if request.context.get("region") != "KR":
            return False

        # 통계 유형 결정 가능한지 체크
        stat_type = self._determine_stat_type(request)

        return stat_type is not None

    # ========================================
    # ECOS API 호출
    # ========================================

    def _fetch_key_statistic(
        self,
        keyword: str,
        context: Dict[str, Any]
    ) -> Optional[List[Dict]]:
        """ECOS 100대 통계지표 조회

        API: KeyStatisticList
        URL: /KeyStatisticList/{key}/json/kr/1/100

        Args:
            keyword: 통계 지표명 키워드
            context: 컨텍스트 (사용 안 함, 최신 데이터 반환)

        Returns:
            통계 데이터 리스트
        """
        # URL 구성
        url = (
            f"{self.base_url}/KeyStatisticList/"
            f"{self.api_key}/json/kr/1/100"
        )

        try:
            response = requests.get(url, timeout=self.timeout)

            if response.status_code != 200:
                raise SourceNotAvailableError(
                    f"ECOS API HTTP {response.status_code}"
                )

            data = response.json()

            # KeyStatisticList 추출
            if "KeyStatisticList" not in data:
                # 에러 응답 확인
                if "RESULT" in data:
                    result = data["RESULT"]
                    code = result.get("CODE", "")
                    message = result.get("MESSAGE", "")

                    if "200" in code:
                        raise DataNotFoundError(f"ECOS: 해당 데이터 없음")
                    else:
                        raise SourceNotAvailableError(
                            f"ECOS API error {code}: {message}"
                        )

                raise DataNotFoundError("No KeyStatisticList in response")

            rows = data["KeyStatisticList"]["row"]

            # Keyword로 필터링
            matched = [
                row for row in rows
                if keyword in row.get("KEYSTAT_NAME", "")
            ]

            if not matched:
                raise DataNotFoundError(f"No data for keyword: {keyword}")

            return matched

        except requests.Timeout:
            raise SourceTimeoutError("ECOS API timeout")
        except (DataNotFoundError, SourceNotAvailableError, SourceTimeoutError):
            raise
        except Exception as e:
            raise SourceNotAvailableError(f"ECOS API failed: {e}")

    def _parse_stat_data(
        self,
        data: Any,
        request: EvidenceRequest
    ) -> Optional[float]:
        """ECOS 통계 데이터 파싱

        Args:
            data: ECOS API 응답 (list of dict)
            request: EvidenceRequest

        Returns:
            파싱된 값 (None이면 실패)
        """
        if not isinstance(data, list):
            return None

        if not data:
            return None

        # 최신 데이터 (마지막 항목)
        latest = data[-1]
        data_value = latest.get('DATA_VALUE', '')

        try:
            # 쉼표 제거 후 float 변환
            value = float(data_value.replace(',', ''))
            return value
        except (ValueError, AttributeError):
            return None

    def _determine_stat_type(
        self,
        request: EvidenceRequest
    ) -> Optional[str]:
        """통계 유형 결정 (패턴 매칭, YAML 기반)

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

        for stat_type, info in self.KEY_STATISTICS.items():
            keywords_match = info.get("keywords_match", [])
            keywords_exclude = info.get("keywords_exclude", [])

            # 모든 match keywords가 있어야 함
            if all(kw in search_text for kw in keywords_match):
                # exclude keywords가 없어야 함
                if not any(ex in search_text for ex in keywords_exclude):
                    return stat_type

        return None


