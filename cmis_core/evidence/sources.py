"""CMIS Evidence Sources

BaseDataSource 구현체들
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

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
)
from .dart_connector import DARTConnector


# Re-export
__all__ = [
    "DARTSource",
    "StubSource",
    "KOSISSource",
]

# GoogleSearchSource는 별도 import 필요 (의존성 때문에)
# from cmis_core.evidence.google_search_source import GoogleSearchSource


# ========================================
# DARTSource
# ========================================

class DARTSource(BaseDataSource):
    """DART API Source

    기존 DARTConnector를 BaseDataSource 인터페이스로 래핑
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: DART API Key (None이면 환경변수)
        """
        super().__init__(
            source_id="DART",
            source_tier=SourceTier.OFFICIAL,
            capabilities={
                "provides": ["financial_statements", "company_filings"],
                "regions": ["KR"],
                "data_types": ["numeric", "table"]
            }
        )

        try:
            self.connector = DARTConnector(api_key)
        except ValueError as e:
            raise SourceNotAvailableError(f"DART initialization failed: {e}")

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """Evidence 수집

        Args:
            request: Evidence 요청

        Returns:
            EvidenceRecord

        Raises:
            DataNotFoundError: 데이터 없음
            SourceNotAvailableError: API 오류
        """
        # Context에서 필요 정보 추출
        company_name = request.context.get("company_name")
        year = request.context.get("year")

        if not company_name or not year:
            raise DataNotFoundError(
                f"DART requires company_name and year in context"
            )

        # DART connector 호출
        try:
            evidence = self.connector.fetch_company_revenue(company_name, year)
        except Exception as e:
            raise SourceNotAvailableError(f"DART API error: {e}")

        if not evidence:
            raise DataNotFoundError(
                f"No DART data for {company_name} {year}"
            )

        # v9 Evidence → EvidenceRecord 변환
        return EvidenceRecord(
            evidence_id=evidence.evidence_id,
            source_tier=evidence.source_tier,
            source_id=self.source_id,
            value=evidence.metadata.get("revenue"),
            value_kind=EvidenceValueKind.NUMERIC,
            schema_ref="dart_filings_v1",
            confidence=0.95,  # 공식 공시는 신뢰도 높음
            metadata=evidence.metadata,
            retrieved_at=evidence.retrieved_at,
            lineage={
                "query": f"{company_name} {year}",
                "corp_code": evidence.metadata.get("corp_code")
            }
        )

    def can_handle(self, request: EvidenceRequest) -> bool:
        """요청 처리 가능 여부

        체크:
        - region: KR만 지원
        - company_name, year 필수
        """
        # region 체크
        if request.context.get("region") != "KR":
            return False

        # 필수 필드 체크
        if not request.context.get("company_name"):
            return False

        if not request.context.get("year"):
            return False

        return True


# ========================================
# StubSource (테스트용)
# ========================================

class StubSource(BaseDataSource):
    """테스트용 stub source

    실제 API 호출 없이 더미 데이터 반환
    """

    def __init__(
        self,
        source_id: str,
        source_tier: SourceTier,
        stub_data: Dict[str, Any]
    ):
        """
        Args:
            source_id: Source ID
            source_tier: Tier
            stub_data: 반환할 더미 데이터
        """
        super().__init__(
            source_id=source_id,
            source_tier=source_tier,
            capabilities={
                "provides": ["*"],
                "regions": ["*"],
                "data_types": ["numeric"]
            }
        )
        self.stub_data = stub_data

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """더미 데이터 반환"""
        return EvidenceRecord(
            evidence_id=f"EVD-{self.source_id}-{uuid.uuid4().hex[:8]}",
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=self.stub_data.get("value", 1000000),
            value_kind=EvidenceValueKind.NUMERIC,
            confidence=0.8,
            metadata=self.stub_data,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            lineage={"stub": True}
        )

    def can_handle(self, request: EvidenceRequest) -> bool:
        """모든 요청 처리 가능"""
        return True


# ========================================
# OfficialSource (스텁, 향후 확장)
# ========================================

class _LegacyKOSISSourceStub(BaseDataSource):
    """Legacy stub for KOSISSource.

    NOTE:
    - 실제 KOSIS OpenAPI 구현은 `cmis_core.evidence.kosis_source.KOSISSource`에 존재합니다.
    - 이 스텁은 fallback 용도로만 유지합니다.
    """

    def __init__(self):
        super().__init__(
            source_id="KOSIS",
            source_tier=SourceTier.OFFICIAL,
            capabilities={
                "provides": ["population_stats", "macro_indicators"],
                "regions": ["KR"],
                "data_types": ["numeric", "table"]
            }
        )

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """v1: 스텁 구현

        향후 KOSIS OpenAPI 연동 예정
        """
        raise DataNotFoundError("KOSIS integration not yet implemented")

    def can_handle(self, request: EvidenceRequest) -> bool:
        """v1: 기본 체크만"""
        return request.context.get("region") == "KR"


# Prefer real KOSIS OpenAPI implementation (keep import compatibility).
try:
    from cmis_core.evidence.kosis_source import KOSISSource as KOSISSource  # type: ignore
except Exception:
    KOSISSource = _LegacyKOSISSourceStub  # type: ignore



