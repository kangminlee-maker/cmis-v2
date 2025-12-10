"""KOSIS API Source

KOSIS (국가통계포털) OpenAPI를 통한 Evidence 수집

구현 완료 (2025-12-09 ~ 2025-12-10):
- 2개 통계표 매핑 (인구, 가구)
- 17개 지역 코드 지원 (전국 + 시도별)
- 시계열 데이터 조회 (start_year ~ end_year)
- 동적 파라미터 처리 (objL1, objL2, itmId)
- JavaScript JSON 파싱 안정성 개선

검증 결과:
- 2024년 전국 인구: 51,217,221명
- Official tier, Confidence: 0.95
- 지역별 조회: 서울, 부산, 경기 등
- 시계열 조회: 2020-2024

핵심 파라미터:
- loadGubun=2 (필수!)
- itmId (통계표별 동적 매핑)
- objL1 (지역 코드, REGION_CODES 참조)
- objL2='ALL' (필수!)
- prdSe (Y=년, Q=분기, M=월)

형식: JSON (JavaScript JSON 파싱)
"""

from __future__ import annotations

import os
import re
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


class KOSISSource(BaseDataSource):
    """KOSIS (국가통계포털) API Source
    
    기능:
    - 인구 통계 조회
    - 가구 통계 조회
    - 시계열 데이터 조회
    - 지역별 데이터 조회 (전국, 17개 시도)
    
    지원 통계표:
    - DT_1B04006: 주민등록인구
    - DT_1B04005N: 가구 및 세대 현황
    
    API 문서: https://kosis.kr/openapi/
    """
    
    # YAML에서 로딩 (하드코딩 제거)
    _tables_cache = None
    _regions_cache = None
    
    @classmethod
    def _load_stat_tables(cls) -> Dict:
        """config/sources/kosis_tables.yaml 로딩"""
        if cls._tables_cache is not None:
            return cls._tables_cache
        
        config_path = Path(__file__).parent.parent.parent / "config" / "sources" / "kosis_tables.yaml"
        
        if not config_path.exists():
            # Fallback: 기본값
            return {
                "population": {
                    "orgId": "101",
                    "tblId": "DT_1B04006",
                    "itmId": "T2",
                    "prdSe": "Y"
                }
            }
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 리스트 → 딕셔너리 변환
        tables = {}
        for table in data.get("tables", []):
            stat_type = table.pop("stat_type")
            tables[stat_type] = table
        
        cls._tables_cache = tables
        return tables
    
    @classmethod
    def _load_region_codes(cls) -> Dict:
        """config/sources/kosis_regions.yaml 로딩"""
        if cls._regions_cache is not None:
            return cls._regions_cache
        
        config_path = Path(__file__).parent.parent.parent / "config" / "sources" / "kosis_regions.yaml"
        
        if not config_path.exists():
            # Fallback
            return {"KR": "00", "전국": "00"}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 리스트 → 딕셔너리 변환
        codes = {}
        for region in data.get("regions", []):
            codes[region["name"]] = region["code"]
        
        cls._regions_cache = codes
        return codes
    
    @property
    def STAT_TABLES(self):
        """동적 로딩"""
        return self._load_stat_tables()
    
    @property
    def REGION_CODES(self):
        """동적 로딩"""
        return self._load_region_codes()
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 10
    ):
        """
        Args:
            api_key: KOSIS API Key (None이면 환경변수)
            timeout: 요청 timeout (초)
        """
        super().__init__(
            source_id="KOSIS",
            source_tier=SourceTier.OFFICIAL,
            capabilities={
                "provides": [
                    "population_stats",
                    "household_stats",
                    "income_distribution",
                    "macro_indicators"
                ],
                "regions": ["KR"],
                "data_types": ["numeric", "table"]
            }
        )
        
        self.api_key = api_key or os.getenv("KOSIS_API_KEY")
        self.base_url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
        self.timeout = timeout
        
        if not self.api_key:
            raise SourceNotAvailableError(
                "KOSIS_API_KEY required. "
                "Get key at: https://kosis.kr/openapi/"
            )
    
    def fetch(self, request: EvidenceRequest) -> EvidenceRecord:
        """Evidence 수집
        
        프로세스:
        1. Context에서 통계 유형 결정
        2. 적절한 통계표 선택
        3. KOSIS API 호출
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
            raise DataNotFoundError("Cannot determine KOSIS stat type from request")
        
        stat_info = self.STAT_TABLES.get(stat_type)
        
        if not stat_info:
            raise DataNotFoundError(f"Unknown stat type: {stat_type}")
        
        # 2. API 호출
        try:
            data = self._fetch_stat_data(
                stat_info["orgId"],
                stat_info["tblId"],
                request.context,
                stat_info
            )
        except requests.Timeout:
            raise SourceTimeoutError(f"KOSIS API timeout")
        except Exception as e:
            raise SourceNotAvailableError(f"KOSIS API error: {e}")
        
        if not data:
            raise DataNotFoundError(f"No KOSIS data for {stat_type}")
        
        # 3. 데이터 파싱
        value = self._parse_stat_data(data, request)
        
        if value is None:
            raise DataNotFoundError(f"Cannot parse KOSIS data")
        
        # 4. EvidenceRecord 생성
        return EvidenceRecord(
            evidence_id=f"EVD-KOSIS-{uuid.uuid4().hex[:8]}",
            source_tier=self.source_tier.value,
            source_id=self.source_id,
            value=value,
            value_kind=EvidenceValueKind.NUMERIC,
            schema_ref="kosis_stats_v1",
            confidence=0.95,  # 공식 통계는 신뢰도 높음
            metadata={
                "stat_type": stat_type,
                "orgId": stat_info["orgId"],
                "tblId": stat_info["tblId"],
                "stat_name": stat_info["name"],
                "itmId": stat_info.get("itmId"),
                "context": request.context
            },
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            lineage={
                "api": "kosis_openapi",
                "table": stat_info["tblId"]
            }
        )
    
    def can_handle(self, request: EvidenceRequest) -> bool:
        """처리 가능 여부
        
        조건:
        - region: KR만 지원
        - 인구/가구 관련 metric
        """
        # KR region만 지원
        if request.context.get("region") != "KR":
            return False
        
        # 통계 유형 결정 가능한지 체크
        stat_type = self._determine_stat_type(request)
        
        return stat_type is not None
    
    # ========================================
    # KOSIS API 호출
    # ========================================
    
    def _fetch_stat_data(
        self,
        org_id: str,
        tbl_id: str,
        context: Dict[str, Any],
        stat_info: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict]]:
        """KOSIS 통계표 데이터 조회
        
        Args:
            org_id: 기관 ID (예: "101" = 통계청)
            tbl_id: 통계표 ID (예: "DT_1B04006")
            context: 컨텍스트 (year, region 등)
            stat_info: 통계표 메타 정보 (itmId, prdSe 등)
        
        Returns:
            통계 데이터 리스트 (JavaScript JSON → Python dict 변환)
        """
        # 기본 파라미터
        params = {
            'method': 'getList',
            'apiKey': self.api_key,
            'orgId': org_id,
            'tblId': tbl_id,
            'format': 'json',
            'jsonVD': 'Y',
            'loadGubun': '2',
        }
        
        # 통계표 정보에서 파라미터 설정
        if stat_info:
            params['itmId'] = stat_info.get('itmId', 'T2') + '+'
            params['prdSe'] = stat_info.get('prdSe', 'Y')
        else:
            params['itmId'] = 'T2+'
            params['prdSe'] = 'Y'
        
        # 지역 코드 설정 (objL1)
        region = context.get("region", "KR")
        area = context.get("area", region)
        region_code = self.REGION_CODES.get(area, "00")
        params['objL1'] = region_code + '+'
        
        # objL2~objL8 설정
        params['objL2'] = context.get('objL2', 'ALL')
        params['objL3'] = context.get('objL3', '')
        params['objL4'] = context.get('objL4', '')
        params['objL5'] = context.get('objL5', '')
        params['objL6'] = context.get('objL6', '')
        params['objL7'] = context.get('objL7', '')
        params['objL8'] = context.get('objL8', '')
        
        # 시계열 파라미터 설정
        year = context.get("year")
        start_year = context.get("start_year")
        end_year = context.get("end_year")
        
        if start_year and end_year:
            # 시계열 조회
            params['startPrdDe'] = str(start_year)
            params['endPrdDe'] = str(end_year)
        elif year:
            # 단일 연도 조회
            params['startPrdDe'] = str(year)
            params['endPrdDe'] = str(year)
        else:
            # 최근 1개 시점
            params['newEstPrdCnt'] = '1'
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise SourceNotAvailableError(
                    f"KOSIS API HTTP {response.status_code}"
                )
            
            # JavaScript JSON → Python dict 변환
            data = self._parse_javascript_json(response.text)
            
            # 오류 체크
            if isinstance(data, dict) and 'err' in data:
                err_code = data.get('err')
                err_msg = data.get('errMsg', '')
                
                if err_code and err_code != '0':
                    raise SourceNotAvailableError(
                        f"KOSIS API error {err_code}: {err_msg}"
                    )
            
            return data
        
        except requests.Timeout:
            raise SourceTimeoutError("KOSIS API timeout")
        except SourceNotAvailableError:
            raise
        except Exception as e:
            raise SourceNotAvailableError(f"KOSIS API failed: {e}")
    
    def _parse_javascript_json(self, text: str) -> Any:
        """KOSIS JavaScript JSON → Python dict 변환
        
        KOSIS는 jsonVD=Y 사용 시 JavaScript 형식 반환:
        {ORG_ID:"101",TBL_NM:"인구"} → {"ORG_ID":"101","TBL_NM":"인구"}
        
        Args:
            text: JavaScript JSON 텍스트
        
        Returns:
            Python dict 또는 list
        """
        import re
        import json
        
        if not text or not text.strip():
            raise SourceNotAvailableError("Empty response from KOSIS API")
        
        # {key:value} → {"key":value} 변환
        # 주의: 값 안의 콤마는 건드리지 않도록
        text_fixed = re.sub(r'([{,])(\w+):', r'\1"\2":', text)
        
        try:
            result = json.loads(text_fixed)
            
            # 빈 결과 체크
            if isinstance(result, list) and len(result) == 0:
                return []
            
            # 에러 응답 체크 (dict with err field)
            if isinstance(result, dict):
                if 'err' in result and result.get('err') != '0':
                    err_msg = result.get('errMsg', 'Unknown error')
                    raise SourceNotAvailableError(f"KOSIS API error: {err_msg}")
            
            return result
            
        except json.JSONDecodeError as e:
            raise SourceNotAvailableError(
                f"Failed to parse KOSIS JSON: {e}\nText: {text[:200]}"
            )
    
    def _parse_stat_data(
        self,
        data: Any,
        request: EvidenceRequest
    ) -> Any:
        """KOSIS 통계 데이터 파싱
        
        Args:
            data: KOSIS API 응답 (list 또는 dict)
            request: EvidenceRequest
        
        Returns:
            파싱된 값 (시계열이면 list, 단일값이면 float, None이면 실패)
        """
        # KOSIS는 list 반환
        # 예: [{"C1": "2024", "DT": "50000000", "UNIT_NM": "명"}, ...]
        
        if not isinstance(data, list):
            return None
        
        if not data:
            return None
        
        # 시계열 여부 확인 (start_year, end_year context)
        is_timeseries = (
            request.context.get("start_year") is not None and
            request.context.get("end_year") is not None
        )
        
        if is_timeseries:
            # 시계열 데이터: 연도별로 그룹화하여 합계만 추출
            # KOSIS는 objL2='ALL'일 때 연령대별 등 세부 항목 반환
            # 첫 번째 항목이 보통 합계
            year_data = {}
            
            for item in data:
                prd_de = item.get('PRD_DE', '')
                dt_value = item.get('DT', '')
                
                # 첫 번째 항목만 사용 (합계)
                if prd_de and prd_de not in year_data:
                    try:
                        value = float(dt_value.replace(',', ''))
                        year_data[prd_de] = {
                            'period': prd_de,
                            'value': value,
                            'unit': item.get('UNIT_NM', '')
                        }
                    except (ValueError, AttributeError):
                        continue
            
            # 정렬된 시계열 리스트 반환
            timeseries = [year_data[year] for year in sorted(year_data.keys())]
            return timeseries if timeseries else None
        
        # 단일 시점 데이터: 첫 번째 항목 (합계) 사용
        first_item = data[0]
        dt_value = first_item.get('DT', '')
        
        try:
            # 콤마 제거 후 float 변환
            value = float(dt_value.replace(',', ''))
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
        
        for stat_type, info in self.STAT_TABLES.items():
            keywords = info.get("keywords", [])
            
            if any(kw in search_text for kw in keywords):
                return stat_type
        
        # Fallback
        if request.context.get("region") == "KR":
            return "population"
        
        return None


