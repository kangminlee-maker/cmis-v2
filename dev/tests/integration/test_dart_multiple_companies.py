"""DART 복수 기업 통합 테스트

다양한 계정과목 패턴 검증
"""

import pytest

from cmis_core.evidence.dart_connector import DARTConnector
from cmis_core.evidence.sources import DARTSource
from cmis_core.types import EvidenceRequest


# ========================================
# 검증 기업 목록 (v7 기반)
# ========================================

TEST_COMPANIES = [
    {
        "name": "YBM넷",
        "year": 2023,
        "expected_revenue_billion": 605,
        "account_pattern": "매출액"
    },
    {
        "name": "삼성전자",
        "year": 2023,
        "expected_revenue_billion": 1_703_700,  # 170조
        "account_pattern": "영업수익"
    },
    {
        "name": "LG전자",
        "year": 2023,
        "expected_revenue_billion": 288_683,  # 28조
        "account_pattern": "매출액"
    },
]


# ========================================
# DARTConnector Tests
# ========================================

@pytest.mark.parametrize("company_data", TEST_COMPANIES)
def test_dart_connector_multiple_companies(company_data):
    """DART Connector 복수 기업 테스트"""
    connector = DARTConnector()
    
    company = company_data["name"]
    year = company_data["year"]
    expected = company_data["expected_revenue_billion"]
    
    evidence = connector.fetch_company_revenue(company, year)
    
    assert evidence is not None, f"{company} Evidence 생성 실패"
    
    revenue = evidence.metadata.get("revenue", 0)
    revenue_billion = revenue / 100_000_000
    
    # 오차 허용 (±5%)
    diff_pct = abs(revenue_billion - expected) / expected * 100
    
    print(f"\n{company}:")
    print(f"  예상: {expected:,.0f}억원")
    print(f"  실제: {revenue_billion:,.1f}억원")
    print(f"  오차: {diff_pct:.2f}%")
    print(f"  계정: {evidence.metadata.get('account_name')}")
    
    assert diff_pct < 5.0, f"{company} 오차 과다: {diff_pct:.2f}%"


def test_dart_account_matching_priority():
    """계정과목 우선순위 매칭 테스트"""
    connector = DARTConnector()
    
    # 삼성전자: "영업수익" 사용
    corp_code = connector.get_corp_code("삼성전자")
    financials = connector.get_financials(corp_code, 2023, 'OFS')
    
    if financials and isinstance(financials, list):
        # "매출액" 없어야 함
        매출액_items = [
            item for item in financials
            if item.get('account_nm', '') == '매출액'
        ]
        
        # "영업수익" 있어야 함
        영업수익_items = [
            item for item in financials
            if '영업수익' in item.get('account_nm', '')
        ]
        
        print(f"\n삼성전자 계정과목:")
        print(f"  '매출액': {len(매출액_items)}개")
        print(f"  '영업수익': {len(영업수익_items)}개")
        
        assert len(영업수익_items) > 0, "삼성전자는 '영업수익' 사용"
        
        # fetch_company_revenue가 올바르게 매칭해야 함
        evidence = connector.fetch_company_revenue("삼성전자", 2023)
        assert evidence is not None
        assert "영업수익" in evidence.metadata.get("account_name", "")


# ========================================
# DARTSource Tests
# ========================================

def test_dart_source_samsung():
    """DARTSource 삼성전자 테스트"""
    source = DARTSource()
    
    request = EvidenceRequest(
        request_id="test",
        request_type="metric",
        metric_id="MET-Revenue",
        context={
            "company_name": "삼성전자",
            "year": 2023,
            "region": "KR"
        }
    )
    
    record = source.fetch(request)
    
    assert record.source_id == "DART"
    assert record.source_tier == "official"
    assert record.confidence == 0.95
    
    # 170조원 정도
    assert record.value > 100_000_000_000_000  # 100조 이상
    assert record.value < 200_000_000_000_000  # 200조 이하
    
    print(f"\n삼성전자 DARTSource:")
    print(f"  Value: {record.value/1_000_000_000_000:.2f}조원")
    print(f"  Metadata: {record.metadata}")


def test_dart_financials_multiple_metrics():
    """여러 Metric 동시 조회"""
    connector = DARTConnector()
    
    evidence = connector.fetch_company_financials(
        "삼성전자",
        2023,
        metrics=["매출액", "영업이익", "순이익"]
    )
    
    assert evidence is not None
    
    financials = evidence.metadata.get("financials", {})
    
    print(f"\n삼성전자 재무 지표:")
    for metric, value in financials.items():
        if value:
            print(f"  {metric}: {value/100_000_000:,.1f}억원")
    
    # 매출액 (영업수익)
    assert financials.get("매출액") is not None
    assert financials.get("매출액") > 100_000_000_000_000  # 100조 이상
    
    # 영업이익
    assert financials.get("영업이익") is not None
