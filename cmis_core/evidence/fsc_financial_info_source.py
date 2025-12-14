"""FSC (금융위원회) 기업 재무정보 API Source.

공공데이터포털(data.go.kr) "금융위원회_기업 재무정보" OpenAPI를 통해,
법인등록번호(crno) + 사업연도(bizYear) 기준으로 기업 재무정보를 조회합니다.

Phase 1 목표:
- 요약재무제표(getSummFinaStat_V2)에서 매출액(enpSaleAmt)을 추출하여
  MET-Revenue에 대한 Tier-1(OFFICIAL) evidence를 제공합니다.

주의:
- 법인등록번호 자동 해소(company_name -> crno)는 별도 API 의존(후속).
- 본 소스는 caller가 corp_reg_no(crno)와 year를 제공해야 합니다.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from cmis_core.evidence_engine import BaseDataSource, DataNotFoundError, SourceNotAvailableError, SourceTimeoutError
from cmis_core.types import EvidenceRecord, EvidenceRequest, EvidenceValueKind, SourceTier


def _normalize_corp_reg_no(value: Any) -> str:
    """법인등록번호를 digits-only로 정규화합니다."""

    s = str(value or "").strip()
    if not s:
        return ""
    return re.sub(r"\D+", "", s)


def _parse_amount(value: Any) -> Optional[float]:
    """금액 문자열을 float로 파싱합니다.

    data.go.kr 응답은 문자열 금액(enpSaleAmt 등)을 반환합니다.
    """

    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    # 흔한 구분자 제거
    s = s.replace(",", "")

    try:
        return float(s)
    except (TypeError, ValueError):
        return None


class FSCCorpFinancialInfoSource(BaseDataSource):
    """금융위원회 기업 재무정보(data.go.kr) Source."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        timeout: int = 10,
        base_url: str = "https://apis.data.go.kr/1160100/service/GetFinaStatInfoService_V2",
    ) -> None:
        super().__init__(
            source_id="FSC_CorpFinancialInfo",
            source_tier=SourceTier.OFFICIAL,
            capabilities={
                # EvidenceEngine의 capability 매칭은 metrics_spec.direct_evidence_sources와의 교집합을 사용합니다.
                # MET-Revenue는 company_filings를 포함하므로, Phase 1에서는 해당 capability로 매칭되도록 제공합니다.
                "provides": ["company_filings", "financial_statements", "official_statistics"],
                "regions": ["KR"],
                "data_types": ["numeric", "table"],
            },
        )

        self.api_key = api_key or os.getenv("DATAGOKR_API_KEY")
        self.timeout = int(timeout)
        self.base_url = str(base_url).rstrip("/")

        if not self.api_key:
            raise SourceNotAvailableError(
                "DATAGOKR_API_KEY required. "
                "Get key at: https://www.data.go.kr/"
            )

    def can_handle(self, request: EvidenceRequest) -> bool:
        """처리 가능 여부.

        Phase 1(최소):
        - request_type == "metric"
        - metric_id == "MET-Revenue"
        - region == "KR"
        - corp_reg_no(crno) + year(bizYear) 존재
        """

        if request.request_type != "metric":
            return False

        if str(request.metric_id or "") != "MET-Revenue":
            return False

        if request.context.get("region") != "KR":
            return False

        crno = _normalize_corp_reg_no(request.context.get("corp_reg_no") or request.context.get("crno"))
        if not crno:
            return False

        year = request.context.get("year") or request.context.get("bizYear")
        try:
            int(year)
        except Exception:
            return False

        return True

    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """요약재무제표 조회(getSummFinaStat_V2) 기반으로 매출액을 반환합니다."""

        crno = _normalize_corp_reg_no(request.context.get("corp_reg_no") or request.context.get("crno"))
        if not crno:
            raise DataNotFoundError("FSC requires corp_reg_no(crno) in context")

        year_raw = request.context.get("year") or request.context.get("bizYear")
        try:
            biz_year = int(year_raw)
        except Exception as e:
            raise DataNotFoundError(f"FSC requires year(bizYear) in context: {e}")

        endpoint = f"{self.base_url}/getSummFinaStat_V2"

        params: Dict[str, Any] = {
            "serviceKey": self.api_key,
            "numOfRows": "10",
            "pageNo": "1",
            "resultType": "json",
            "crno": crno,
            "bizYear": str(biz_year),
        }

        try:
            resp = requests.get(endpoint, params=params, timeout=self.timeout)
        except requests.Timeout:
            raise SourceTimeoutError("FSC API timeout")
        except Exception as e:
            raise SourceNotAvailableError(f"FSC API error: {e}")

        if resp.status_code != 200:
            raise SourceNotAvailableError(f"FSC API HTTP {resp.status_code}")

        try:
            data = resp.json()
        except Exception as e:
            raise SourceNotAvailableError(f"FSC API invalid JSON: {e}")

        header = data.get("header") if isinstance(data, dict) else None
        if isinstance(header, dict):
            result_code = str(header.get("resultCode") or "").strip()
            result_msg = str(header.get("resultMsg") or "").strip()
            # data.go.kr 표준: resultCode == "00"이면 성공
            if result_code and result_code != "00":
                raise DataNotFoundError(f"FSC API error {result_code}: {result_msg}")

        body = data.get("body") if isinstance(data, dict) else None
        items = (body or {}).get("items") if isinstance(body, dict) else None
        item = (items or {}).get("item") if isinstance(items, dict) else None

        rows: List[Dict[str, Any]] = []
        if isinstance(item, list):
            rows = [r for r in item if isinstance(r, dict)]
        elif isinstance(item, dict):
            rows = [item]

        if not rows:
            raise DataNotFoundError("FSC: empty items")

        # 동일 bizYear에 여러 행이 있을 수 있으므로, basDt 기준 최신을 우선 선택합니다.
        def _bas_dt_key(d: Dict[str, Any]) -> str:
            return str(d.get("basDt") or "")

        rows.sort(key=_bas_dt_key)
        best = rows[-1]

        sale_amt = _parse_amount(best.get("enpSaleAmt"))
        if sale_amt is None:
            raise DataNotFoundError("FSC: enpSaleAmt not found")

        cur_cd = str(best.get("curCd") or "KRW")
        as_of = str(best.get("basDt") or "") or None

        return EvidenceRecord(
            evidence_id=f"EVD-FSC-{crno}-{biz_year}-{uuid.uuid4().hex[:8]}",
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=sale_amt,
            value_kind=EvidenceValueKind.NUMERIC,
            schema_ref="fsc_corp_financial_info_v1",
            confidence=0.95,
            metadata={
                "metric_id": str(request.metric_id or ""),
                "corp_reg_no": crno,
                "year": biz_year,
                "statement": "summary",
                "curCd": cur_cd,
                "unit": cur_cd,
                "fnclDcd": best.get("fnclDcd"),
                "fnclDcdNm": best.get("fnclDcdNm"),
                "raw_fields": dict(best),
            },
            context=dict(request.context or {}),
            as_of=as_of,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            lineage={
                "api": "data_go_kr",
                "operation": "getSummFinaStat_V2",
                "endpoint": endpoint,
                "query": {
                    "crno": crno,
                    "bizYear": str(biz_year),
                    "numOfRows": str(params.get("numOfRows")),
                    "pageNo": str(params.get("pageNo")),
                    "resultType": str(params.get("resultType")),
                },
                "picked_basDt": best.get("basDt"),
                "picked_fnclDcd": best.get("fnclDcd"),
            },
        )
