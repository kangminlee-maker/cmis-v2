"""CMIS Evidence Store

Evidence 저장/조회/캐싱 관리

설계 원칙:
- Metric 단위 캐싱
- TTL 기반 만료
- SQLite/메모리 백엔드 지원
- Lineage 추적
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import asdict

from .types import (
    EvidenceRequest,
    EvidenceBundle,
    EvidenceRecord,
    MetricRequest,
)


# ========================================
# Storage Backend (추상)
# ========================================

class StorageBackend:
    """Storage 백엔드 추상 인터페이스"""
    
    def save(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None):
        """데이터 저장"""
        raise NotImplementedError
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """데이터 조회"""
        raise NotImplementedError
    
    def delete(self, key: str):
        """데이터 삭제"""
        raise NotImplementedError
    
    def clear(self):
        """전체 삭제"""
        raise NotImplementedError


# ========================================
# Memory Backend
# ========================================

class MemoryBackend(StorageBackend):
    """메모리 기반 백엔드 (테스트/개발용)"""
    
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
    
    def save(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None):
        """메모리에 저장"""
        self._data[key] = {
            "value": value,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "ttl": ttl
        }
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """메모리에서 조회"""
        entry = self._data.get(key)
        
        if entry is None:
            return None
        
        # TTL 체크
        if entry.get("ttl"):
            saved_at = datetime.fromisoformat(entry["saved_at"])
            age = (datetime.now(timezone.utc) - saved_at).total_seconds()
            
            if age > entry["ttl"]:
                # 만료됨
                del self._data[key]
                return None
        
        return entry["value"]
    
    def delete(self, key: str):
        """메모리에서 삭제"""
        if key in self._data:
            del self._data[key]
    
    def clear(self):
        """전체 삭제"""
        self._data.clear()


# ========================================
# SQLite Backend
# ========================================

class SQLiteBackend(StorageBackend):
    """SQLite 기반 백엔드 (프로덕션용)"""
    
    def __init__(self, db_path: str = ".cmis/evidence_cache.db"):
        """
        Args:
            db_path: SQLite DB 경로
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_schema()
    
    def _init_schema(self):
        """테이블 생성"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence_cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                saved_at TEXT NOT NULL,
                ttl INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_saved_at
            ON evidence_cache(saved_at)
        """)
        
        self.conn.commit()
    
    def save(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None):
        """SQLite에 저장"""
        value_json = json.dumps(value, ensure_ascii=False)
        saved_at = datetime.now(timezone.utc).isoformat()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO evidence_cache (key, value, saved_at, ttl)
            VALUES (?, ?, ?, ?)
        """, (key, value_json, saved_at, ttl))
        
        self.conn.commit()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """SQLite에서 조회"""
        cursor = self.conn.execute("""
            SELECT value, saved_at, ttl FROM evidence_cache
            WHERE key = ?
        """, (key,))
        
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        value_json, saved_at, ttl = row
        
        # TTL 체크
        if ttl:
            saved_time = datetime.fromisoformat(saved_at)
            age = (datetime.now(timezone.utc) - saved_time).total_seconds()
            
            if age > ttl:
                # 만료됨
                self.delete(key)
                return None
        
        return json.loads(value_json)
    
    def delete(self, key: str):
        """SQLite에서 삭제"""
        self.conn.execute("DELETE FROM evidence_cache WHERE key = ?", (key,))
        self.conn.commit()
    
    def clear(self):
        """전체 삭제"""
        self.conn.execute("DELETE FROM evidence_cache")
        self.conn.commit()
    
    def cleanup_expired(self):
        """만료된 항목 삭제"""
        now = datetime.now(timezone.utc).isoformat()
        
        self.conn.execute("""
            DELETE FROM evidence_cache
            WHERE ttl IS NOT NULL
            AND datetime(saved_at, '+' || ttl || ' seconds') < datetime(?)
        """, (now,))
        
        self.conn.commit()


# ========================================
# EvidenceStore
# ========================================

class EvidenceStore:
    """Evidence 저장소
    
    기능:
    - Evidence 캐싱 (TTL 기반)
    - Evidence 조회
    - Hints 재활용 (v2.2)
    """
    """Evidence 저장소
    
    역할:
    - Evidence 영구 저장 (EvidenceRecord → evidence_store)
    - 캐싱 (동일 요청 재사용)
    - TTL 관리
    - Lineage 추적
    """
    
    def __init__(
        self,
        backend: Optional[StorageBackend] = None,
        default_ttl: int = 86400  # 1일
    ):
        """
        Args:
            backend: 저장소 백엔드 (None이면 메모리)
            default_ttl: 기본 TTL (초)
        """
        if backend is None:
            backend = MemoryBackend()
        
        self.backend = backend
        self.default_ttl = default_ttl
    
    def save(
        self,
        bundle: EvidenceBundle,
        ttl: Optional[int] = None
    ):
        """EvidenceBundle 저장
        
        Args:
            bundle: 저장할 EvidenceBundle
            ttl: TTL (None이면 default_ttl)
        """
        cache_key = self._build_cache_key(bundle.request)
        
        # EvidenceBundle 직렬화
        bundle_dict = self._serialize_bundle(bundle)
        
        # 저장
        self.backend.save(
            cache_key,
            bundle_dict,
            ttl=ttl or self.default_ttl
        )
    
    def get(
        self,
        request: Union[EvidenceRequest, MetricRequest],
        max_age_seconds: Optional[float] = None
    ) -> Optional[EvidenceBundle]:
        """캐시/저장소에서 조회
        
        Args:
            request: Evidence/Metric 요청
            max_age_seconds: 최대 허용 age (None이면 TTL 기준)
        
        Returns:
            저장된 EvidenceBundle (없거나 만료되면 None)
        """
        # MetricRequest → EvidenceRequest 변환
        if isinstance(request, MetricRequest):
            request = self._metric_to_evidence_request(request)
        
        cache_key = self._build_cache_key(request)
        
        # 조회
        bundle_dict = self.backend.get(cache_key)
        
        if bundle_dict is None:
            return None
        
        # 역직렬화
        bundle = self._deserialize_bundle(bundle_dict)
        
        # max_age_seconds 체크
        if max_age_seconds is not None:
            # bundle.created_at 기준으로 age 계산
            created_at = bundle.created_at
            if created_at:
                created_time = datetime.fromisoformat(created_at)
                age = (datetime.now(timezone.utc) - created_time).total_seconds()
                
                if age > max_age_seconds:
                    self.backend.delete(cache_key)
                    return None
        
        return bundle
    
    def invalidate(self, pattern: str):
        """캐시 무효화
        
        Args:
            pattern: 무효화할 request pattern
                     (예: "metric:MET-Revenue", "region:KR")
        """
        # TODO: 패턴 매칭 구현 (v2)
        # 현재는 전체 삭제만 지원
        if pattern == "*":
            self.backend.clear()
    
    def cleanup_expired(self):
        """만료된 항목 삭제 (SQLite 전용)"""
        if isinstance(self.backend, SQLiteBackend):
            self.backend.cleanup_expired()
    
    # ========================================
    # Hints 재활용 (v2.2)
    # ========================================
    
    def query_hints(
        self,
        domain_id: Optional[str] = None,
        region: Optional[str] = None,
        metric_pattern: Optional[str] = None,
        min_confidence: float = 0.4
    ) -> List[Dict[str, Any]]:
        """과거 검색에서 수집한 hints 조회
        
        Args:
            domain_id: Domain 필터
            region: Region 필터
            metric_pattern: Metric 패턴 ("MET-*", "MET-TAM" 등)
            min_confidence: 최소 신뢰도
        
        Returns:
            Hint 리스트 (신뢰도 기준 정렬)
        """
        all_hints = []
        
        # MemoryBackend에서 hints 추출
        if hasattr(self.backend, '_data'):
            for key, entry in self.backend._data.items():
                bundle_dict = entry.get("value")
                
                if not bundle_dict:
                    continue
                
                # Evidence에서 hints 추출
                for evidence in bundle_dict.get("evidence_list", []):
                    hints = evidence.get("metadata", {}).get("hints", [])
                    
                    for hint in hints:
                        # 필터링
                        if self._match_hint_filter(
                            hint,
                            domain_id,
                            region,
                            metric_pattern,
                            min_confidence
                        ):
                            all_hints.append(hint)
        
        # 신뢰도 기준 정렬
        all_hints.sort(key=lambda h: h.get("confidence", 0), reverse=True)
        
        return all_hints
    
    def _match_hint_filter(
        self,
        hint: Dict,
        domain_id: Optional[str],
        region: Optional[str],
        metric_pattern: Optional[str],
        min_confidence: float
    ) -> bool:
        """Hint 필터 매칭"""
        # Confidence
        if hint.get("confidence", 0) < min_confidence:
            return False
        
        # Domain
        if domain_id and hint.get("domain_id") != domain_id:
            return False
        
        # Region
        if region and hint.get("region") != region:
            return False
        
        # Metric
        if metric_pattern:
            hint_metric = hint.get("metric_id", "")
            
            if metric_pattern == "MET-*":
                if not hint_metric.startswith("MET-"):
                    return False
            elif hint_metric != metric_pattern:
                return False
        
        return True
    
    # ========================================
    # 캐시 키 생성
    # ========================================
    
    def _build_cache_key(
        self,
        request: EvidenceRequest
    ) -> str:
        """캐시 키 생성
        
        키 구성:
        - metric_id (or entity_type)
        - context (domain_id, region, year 등)
        - quality_requirements (normalize)
        
        Returns:
            16자리 hex hash
        """
        if request.metric_id:
            key_base = f"metric:{request.metric_id}"
        elif request.entity_type:
            key_base = f"entity:{request.entity_type}"
        else:
            key_base = f"request:{request.request_type}"
        
        # Context 정규화 (순서 무관)
        context_items = sorted(request.context.items())
        context_str = "|".join(f"{k}={v}" for k, v in context_items)
        
        # Quality requirements 정규화
        qual_items = sorted(request.quality_requirements.items())
        qual_str = "|".join(f"{k}={v}" for k, v in qual_items)
        
        # 최종 키
        cache_key_raw = f"{key_base}|{context_str}|{qual_str}"
        
        # Hash (16자리)
        return hashlib.sha256(cache_key_raw.encode()).hexdigest()[:16]
    
    def _metric_to_evidence_request(
        self,
        metric_req: MetricRequest
    ) -> EvidenceRequest:
        """MetricRequest → EvidenceRequest 변환 (간단 버전)"""
        import uuid
        
        return EvidenceRequest(
            request_id=f"REQ-{metric_req.metric_id}-{uuid.uuid4().hex[:8]}",
            request_type="metric",
            metric_id=metric_req.metric_id,
            context=metric_req.context,
            required_capabilities=[],
            quality_requirements={}
        )
    
    # ========================================
    # 직렬화/역직렬화
    # ========================================
    
    def _serialize_bundle(
        self,
        bundle: EvidenceBundle
    ) -> Dict[str, Any]:
        """EvidenceBundle → Dict 직렬화
        
        Args:
            bundle: EvidenceBundle
        
        Returns:
            직렬화된 Dict
        """
        return {
            "request": {
                "request_id": bundle.request.request_id,
                "request_type": bundle.request.request_type,
                "metric_id": bundle.request.metric_id,
                "entity_type": bundle.request.entity_type,
                "context": bundle.request.context,
                "required_capabilities": bundle.request.required_capabilities,
                "quality_requirements": bundle.request.quality_requirements,
            },
            "records": [
                {
                    "evidence_id": r.evidence_id,
                    "source_tier": r.source_tier,
                    "source_id": r.source_id,
                    "value": r.value,
                    "value_kind": r.value_kind.value,
                    "schema_ref": r.schema_ref,
                    "confidence": r.confidence,
                    "metadata": r.metadata,
                    "retrieved_at": r.retrieved_at,
                    "lineage": r.lineage,
                }
                for r in bundle.records
            ],
            "quality_summary": bundle.quality_summary,
            "created_at": bundle.created_at,
            "execution_time_ms": bundle.execution_time_ms,
            "debug_trace": bundle.debug_trace,
        }
    
    def _deserialize_bundle(
        self,
        bundle_dict: Dict[str, Any]
    ) -> EvidenceBundle:
        """Dict → EvidenceBundle 역직렬화
        
        Args:
            bundle_dict: 직렬화된 Dict
        
        Returns:
            EvidenceBundle
        """
        from .types import EvidenceValueKind
        
        # Request 복원
        req_dict = bundle_dict["request"]
        request = EvidenceRequest(
            request_id=req_dict["request_id"],
            request_type=req_dict["request_type"],
            metric_id=req_dict.get("metric_id"),
            entity_type=req_dict.get("entity_type"),
            context=req_dict.get("context", {}),
            required_capabilities=req_dict.get("required_capabilities", []),
            quality_requirements=req_dict.get("quality_requirements", {})
        )
        
        # Records 복원
        records = []
        for r_dict in bundle_dict.get("records", []):
            record = EvidenceRecord(
                evidence_id=r_dict["evidence_id"],
                source_tier=r_dict["source_tier"],
                source_id=r_dict["source_id"],
                value=r_dict["value"],
                value_kind=EvidenceValueKind(r_dict.get("value_kind", "numeric")),
                schema_ref=r_dict.get("schema_ref"),
                confidence=r_dict.get("confidence", 0.0),
                metadata=r_dict.get("metadata", {}),
                retrieved_at=r_dict.get("retrieved_at", ""),
                lineage=r_dict.get("lineage", {})
            )
            records.append(record)
        
        # Bundle 복원
        bundle = EvidenceBundle(
            request=request,
            records=records,
            quality_summary=bundle_dict.get("quality_summary", {}),
            created_at=bundle_dict.get("created_at", ""),
            execution_time_ms=bundle_dict.get("execution_time_ms"),
            debug_trace=bundle_dict.get("debug_trace", [])
        )
        
        return bundle
    
    def _calculate_age(
        self,
        bundle_dict: Dict[str, Any]
    ) -> float:
        """Bundle age 계산 (초)
        
        Args:
            bundle_dict: 직렬화된 bundle
        
        Returns:
            age (seconds)
        """
        created_at = bundle_dict.get("created_at")
        
        if not created_at:
            return float('inf')
        
        created_time = datetime.fromisoformat(created_at)
        age = (datetime.now(timezone.utc) - created_time).total_seconds()
        
        return age


# ========================================
# Factory
# ========================================

def create_evidence_store(
    backend_type: str = "memory",
    **kwargs
) -> EvidenceStore:
    """EvidenceStore 팩토리
    
    Args:
        backend_type: "memory" or "sqlite"
        **kwargs: 백엔드별 옵션
    
    Returns:
        EvidenceStore
    """
    if backend_type == "memory":
        backend = MemoryBackend()
    
    elif backend_type == "sqlite":
        db_path = kwargs.get("db_path", ".cmis/evidence_cache.db")
        backend = SQLiteBackend(db_path)
    
    else:
        raise ValueError(f"Unknown backend_type: {backend_type}")
    
    default_ttl = kwargs.get("default_ttl", 86400)  # 1일
    
    return EvidenceStore(backend, default_ttl)

