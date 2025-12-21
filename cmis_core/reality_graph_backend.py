"""Reality Graph Backend - 영속성 및 인덱싱

Phase C: 성능 최적화
- 파일 시스템 백엔드
- 인덱싱 (domain, region, as_of)
- 쿼리 최적화

2025-12-11: World Engine Phase C
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .graph import InMemoryGraph, Node, Edge
from cmis_core.stores.sqlite_base import StoragePaths


class RealityGraphBackend:
    """Reality Graph 영속성 백엔드

    역할:
    - R-Graph 저장 및 로딩
    - 인덱스 관리
    - 쿼리 최적화

    Phase C: 파일 시스템 백엔드
    미래: SQLite, PostgreSQL 등
    """

    def __init__(self, storage_dir: Optional[Path] = None, *, project_root: Optional[Path] = None):
        """
        Args:
            storage_dir: 저장 디렉토리 (None이면 기본 경로)
            project_root: 프로젝트 루트(선택). storage_dir 미지정 시 StoragePaths 기준으로 기본 경로를 결정합니다.
        """
        if storage_dir is None:
            storage_dir = StoragePaths.resolve(project_root).reality_graphs_dir

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 인덱스 디렉토리
        self.index_dir = self.storage_dir / "indexes"
        self.index_dir.mkdir(exist_ok=True)

        # 인덱스
        self.domain_index: Dict[str, Path] = {}
        self.region_index: Dict[str, List[str]] = {}
        self.as_of_index: Dict[str, List[str]] = {}

        # 인덱스 로딩
        self._load_indexes()

    def save_graph(
        self,
        domain_id: str,
        graph: InMemoryGraph,
        meta: Dict[str, Any]
    ) -> None:
        """그래프 저장

        Args:
            domain_id: 도메인 ID
            graph: InMemoryGraph
            meta: Meta 정보
        """
        # 도메인별 디렉토리
        domain_dir = self.storage_dir / domain_id
        domain_dir.mkdir(exist_ok=True)

        # 그래프 저장 (pickle)
        graph_path = domain_dir / "graph.pkl"
        with open(graph_path, 'wb') as f:
            pickle.dump(graph, f)

        # Meta 저장 (JSON)
        meta_path = domain_dir / "meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 인덱스 업데이트
        self._update_indexes(domain_id, meta, graph_path)

    def load_graph(
        self,
        domain_id: str
    ) -> Optional[tuple[InMemoryGraph, Dict[str, Any]]]:
        """그래프 로딩

        Args:
            domain_id: 도메인 ID

        Returns:
            (InMemoryGraph, meta) 또는 None
        """
        domain_dir = self.storage_dir / domain_id

        if not domain_dir.exists():
            return None

        graph_path = domain_dir / "graph.pkl"
        meta_path = domain_dir / "meta.json"

        if not graph_path.exists() or not meta_path.exists():
            return None

        # 그래프 로딩
        with open(graph_path, 'rb') as f:
            graph = pickle.load(f)

        # Meta 로딩
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        return (graph, meta)

    def has_domain(self, domain_id: str) -> bool:
        """도메인 존재 여부

        Args:
            domain_id: 도메인 ID

        Returns:
            존재 여부
        """
        return domain_id in self.domain_index

    def _update_indexes(
        self,
        domain_id: str,
        meta: Dict[str, Any],
        graph_path: Path
    ) -> None:
        """인덱스 업데이트

        Args:
            domain_id: 도메인 ID
            meta: Meta 정보
            graph_path: 그래프 파일 경로
        """
        # domain_index
        self.domain_index[domain_id] = graph_path

        # region_index
        region = meta.get("region", "unknown")
        if region not in self.region_index:
            self.region_index[region] = []
        if domain_id not in self.region_index[region]:
            self.region_index[region].append(domain_id)

        # as_of_index
        as_of = meta.get("as_of", "latest")
        if as_of not in self.as_of_index:
            self.as_of_index[as_of] = []
        if domain_id not in self.as_of_index[as_of]:
            self.as_of_index[as_of].append(domain_id)

        # 인덱스 저장
        self._save_indexes()

    def _load_indexes(self) -> None:
        """인덱스 로딩"""
        index_file = self.index_dir / "indexes.json"

        if not index_file.exists():
            return

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # domain_index: path를 Path 객체로 변환
            self.domain_index = {
                k: Path(v) for k, v in data.get("domain_index", {}).items()
            }
            self.region_index = data.get("region_index", {})
            self.as_of_index = data.get("as_of_index", {})
        except Exception as e:
            print(f"Warning: Failed to load indexes: {e}")

    def _save_indexes(self) -> None:
        """인덱스 저장"""
        index_file = self.index_dir / "indexes.json"

        data = {
            "domain_index": {k: str(v) for k, v in self.domain_index.items()},
            "region_index": self.region_index,
            "as_of_index": self.as_of_index,
            "updated_at": datetime.now().isoformat()
        }

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def query_by_region(self, region: str) -> List[str]:
        """지역별 도메인 조회

        Args:
            region: 지역 (예: "KR")

        Returns:
            도메인 ID 리스트
        """
        return self.region_index.get(region, [])

    def query_by_as_of(self, as_of: str) -> List[str]:
        """시점별 도메인 조회

        Args:
            as_of: 시점

        Returns:
            도메인 ID 리스트
        """
        return self.as_of_index.get(as_of, [])

    def clear(self, domain_id: Optional[str] = None) -> None:
        """저장소 클리어

        Args:
            domain_id: 특정 도메인만 삭제 (None이면 전체)
        """
        if domain_id:
            # 특정 도메인만
            domain_dir = self.storage_dir / domain_id
            if domain_dir.exists():
                import shutil
                shutil.rmtree(domain_dir)

            # 인덱스에서 제거
            if domain_id in self.domain_index:
                del self.domain_index[domain_id]

            for region_domains in self.region_index.values():
                if domain_id in region_domains:
                    region_domains.remove(domain_id)

            for as_of_domains in self.as_of_index.values():
                if domain_id in as_of_domains:
                    as_of_domains.remove(domain_id)

            self._save_indexes()
        else:
            # 전체 삭제
            import shutil
            if self.storage_dir.exists():
                shutil.rmtree(self.storage_dir)

            # 재생성
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.index_dir.mkdir(exist_ok=True)

            # 인덱스 초기화
            self.domain_index = {}
            self.region_index = {}
            self.as_of_index = {}


class GraphCache:
    """Snapshot 결과 캐싱

    snapshot() 결과를 캐싱하여 성능 향상
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Args:
            ttl_seconds: 캐시 유효 시간 (기본 1시간)
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Any] = {}
        # cache_key → (snapshot, cached_at)

    def get_cache_key(
        self,
        domain_id: str,
        region: str,
        segment: Optional[str],
        as_of: Optional[str],
        focal_actor_context_id: Optional[str],
    ) -> str:
        """캐시 키 생성

        Args:
            domain_id, region, segment, as_of, focal_actor_context_id

        Returns:
            캐시 키
        """
        parts = [
            domain_id,
            region,
            segment or "none",
            as_of or "none",
            focal_actor_context_id or "none",
        ]
        return "|".join(parts)

    def get(self, cache_key: str) -> Optional[Any]:
        """캐시 조회

        Args:
            cache_key: 캐시 키

        Returns:
            캐시된 snapshot 또는 None
        """
        if cache_key not in self.cache:
            return None

        snapshot, cached_at = self.cache[cache_key]

        # TTL 확인
        age = (datetime.now() - cached_at).total_seconds()
        if age > self.ttl_seconds:
            # 만료
            del self.cache[cache_key]
            return None

        return snapshot

    def put(self, cache_key: str, snapshot: Any) -> None:
        """캐시 저장

        Args:
            cache_key: 캐시 키
            snapshot: RealityGraphSnapshot
        """
        self.cache[cache_key] = (snapshot, datetime.now())

    def invalidate(self, domain_id: str) -> None:
        """도메인별 캐시 무효화

        Args:
            domain_id: 도메인 ID
        """
        # domain_id 포함하는 모든 캐시 제거
        keys_to_remove = [
            key for key in self.cache.keys()
            if key.startswith(domain_id + "|")
        ]

        for key in keys_to_remove:
            del self.cache[key]

    def clear(self) -> None:
        """전체 캐시 클리어"""
        self.cache = {}

    def stats(self) -> Dict[str, Any]:
        """캐시 통계

        Returns:
            통계 정보
        """
        total = len(self.cache)

        # 만료된 항목
        expired = 0
        now = datetime.now()

        for _, cached_at in self.cache.values():
            age = (now - cached_at).total_seconds()
            if age > self.ttl_seconds:
                expired += 1

        return {
            "total_items": total,
            "active_items": total - expired,
            "expired_items": expired,
            "ttl_seconds": self.ttl_seconds
        }
