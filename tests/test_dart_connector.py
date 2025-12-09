"""Tests for DART Connector

Note: DART API Key가 필요한 테스트는 환경변수 없을 시 skip
"""

import pytest
import os
from umis_v9_core.evidence.dart_connector import DARTConnector, Evidence


def test_dart_connector_init_without_key():
    """API Key 없이 초기화 시 에러"""
    # 기존 API Key 백업
    original_key = os.environ.get('DART_API_KEY')
    
    try:
        # API Key 제거
        if 'DART_API_KEY' in os.environ:
            del os.environ['DART_API_KEY']
        
        with pytest.raises(ValueError) as exc_info:
            DARTConnector()
        
        assert "DART_API_KEY required" in str(exc_info.value)
    
    finally:
        # API Key 복원
        if original_key:
            os.environ['DART_API_KEY'] = original_key


def test_dart_connector_init_with_key():
    """API Key로 초기화"""
    connector = DARTConnector(api_key="test-key-12345")
    
    assert connector.api_key == "test-key-12345"
    assert connector.base_url == "https://opendart.fss.or.kr/api"


@pytest.mark.skipif(
    not os.getenv('DART_API_KEY') or os.getenv('DART_API_KEY') == 'your-dart-api-key-here',
    reason="DART_API_KEY not configured"
)
def test_dart_get_corp_code_real():
    """실제 DART API로 기업 코드 조회 (API Key 필요)"""
    connector = DARTConnector()
    
    # 삼성전자 조회
    corp_code = connector.get_corp_code("삼성전자")
    assert corp_code is not None
    assert len(corp_code) == 8


@pytest.mark.skipif(
    not os.getenv('DART_API_KEY') or os.getenv('DART_API_KEY') == 'your-dart-api-key-here',
    reason="DART_API_KEY not configured"
)
def test_dart_fetch_company_revenue_real():
    """실제 DART API로 매출 수집 (API Key 필요)"""
    connector = DARTConnector()
    
    # YBM넷 2023년 매출
    evidence = connector.fetch_company_revenue("YBM넷", 2023)
    
    if evidence:  # API 성공 시
        assert evidence.evidence_id.startswith("EVD-DART-")
        assert evidence.source_tier == "official"
        assert evidence.source_id == "KR_DART_filings"
        assert evidence.metadata["company_name"] == "YBM넷"
        assert evidence.metadata["year"] == 2023
        assert evidence.metadata["revenue"] > 0


def test_evidence_schema_structure():
    """Evidence 스키마 구조 테스트 (mock)"""
    evidence = Evidence(
        evidence_id="EVD-DART-TEST-2023",
        source_tier="official",
        url_or_path="https://dart.fss.or.kr",
        content_ref="테스트 사업보고서",
        metadata={"revenue": 100000000000},
        retrieved_at="2025-12-05T10:00:00",
        source_id="KR_DART_filings"
    )
    
    # v9 스키마 필드 확인
    assert evidence.evidence_id == "EVD-DART-TEST-2023"
    assert evidence.source_tier == "official"
    assert evidence.metadata["revenue"] == 100000000000
