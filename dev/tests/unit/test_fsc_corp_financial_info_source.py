"""FSCCorpFinancialInfoSource unit tests.

원칙:
- 외부 네트워크 호출 없이 requests mocking으로 재현 가능해야 합니다.
"""

from __future__ import annotations

import pytest

import cmis_core.evidence.fsc_financial_info_source as fsc_mod
from cmis_core.evidence_engine import DataNotFoundError
from cmis_core.evidence.fsc_financial_info_source import FSCCorpFinancialInfoSource
from cmis_core.types import EvidenceRequest


class _DummyResponse:
    def __init__(self, *, status_code: int, payload):
        self.status_code = int(status_code)
        self._payload = payload

    def json(self):
        return self._payload


def test_fsc_source_can_handle_requires_fields() -> None:
    src = FSCCorpFinancialInfoSource(api_key="dummy")

    # OK
    req = EvidenceRequest(
        request_id="REQ-1",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "corp_reg_no": "110111-1111111", "year": 2024},
        required_capabilities=["company_filings"],
    )
    assert src.can_handle(req) is True

    # Missing corp_reg_no
    req2 = EvidenceRequest(
        request_id="REQ-2",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "year": 2024},
        required_capabilities=["company_filings"],
    )
    assert src.can_handle(req2) is False

    # Wrong metric
    req3 = EvidenceRequest(
        request_id="REQ-3",
        request_type="metric",
        metric_id="MET-TAM",
        context={"region": "KR", "corp_reg_no": "110111-1111111", "year": 2024},
        required_capabilities=["company_filings"],
    )
    assert src.can_handle(req3) is False


def test_fsc_source_fetch_parses_enpSaleAmt(monkeypatch) -> None:
    src = FSCCorpFinancialInfoSource(api_key="dummy", timeout=1)

    payload = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
        "body": {
            "numOfRows": 10,
            "pageNo": 1,
            "totalCount": 2,
            "items": {
                "item": [
                    {
                        "basDt": "20231231",
                        "bizYear": "2023",
                        "crno": "1101111111111",
                        "curCd": "KRW",
                        "enpSaleAmt": "100,000",
                        "fnclDcd": "11011",
                        "fnclDcdNm": "재무제표",
                    },
                    {
                        "basDt": "20241231",
                        "bizYear": "2024",
                        "crno": "1101111111111",
                        "curCd": "KRW",
                        "enpSaleAmt": "290000000000",
                        "fnclDcd": "11011",
                        "fnclDcdNm": "재무제표",
                    },
                ]
            },
        },
    }

    def fake_get(url, params=None, timeout=None):
        assert url.endswith("/getSummFinaStat_V2")
        assert params is not None
        assert params.get("crno") == "1101111111111"
        assert params.get("bizYear") == "2024"
        assert params.get("resultType") == "json"
        return _DummyResponse(status_code=200, payload=payload)

    monkeypatch.setattr(fsc_mod.requests, "get", fake_get)

    req = EvidenceRequest(
        request_id="REQ-4",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "corp_reg_no": "110111-1111111", "year": 2024},
        required_capabilities=["company_filings"],
    )

    record = src.fetch(req)
    assert record.source_id == "FSC_CorpFinancialInfo"
    assert record.source_tier == "official"
    assert record.value == 290000000000.0
    assert record.metadata.get("year") == 2024
    assert record.metadata.get("corp_reg_no") == "1101111111111"
    assert record.metadata.get("statement") == "summary"


def test_fsc_source_fetch_raises_on_error_code(monkeypatch) -> None:
    src = FSCCorpFinancialInfoSource(api_key="dummy", timeout=1)

    payload = {
        "header": {"resultCode": "99", "resultMsg": "ERROR"},
        "body": {"items": {"item": []}},
    }

    def fake_get(url, params=None, timeout=None):
        return _DummyResponse(status_code=200, payload=payload)

    monkeypatch.setattr(fsc_mod.requests, "get", fake_get)

    req = EvidenceRequest(
        request_id="REQ-5",
        request_type="metric",
        metric_id="MET-Revenue",
        context={"region": "KR", "corp_reg_no": "110111-1111111", "year": 2024},
        required_capabilities=["company_filings"],
    )

    with pytest.raises(DataNotFoundError):
        _ = src.fetch(req)
