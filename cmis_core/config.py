"""CMIS Configuration Loader

Loads and validates cmis.yaml configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based settings (.env)"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='allow'
    )

    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)

    # API Keys
    dart_api_key: Optional[str] = Field(default=None)
    google_api_key: Optional[str] = Field(default=None)
    google_search_engine_id: Optional[str] = Field(default=None)
    kosis_api_key: Optional[str] = Field(default=None)

    # Logging
    log_level: str = Field(default="INFO")


class MetricSpec:
    """Metric 스펙 (metrics_spec.yaml에서 로드)"""

    def __init__(self, metric_data: Dict[str, Any]):
        self.metric_id: str = metric_data["metric_id"]
        self.name: str = metric_data["name"]
        self.category: str = metric_data["category"]
        self.direct_evidence_sources: List[str] = metric_data.get("direct_evidence_sources", [])
        self.derived_paths: List[Dict] = metric_data.get("derived_paths", [])
        self.resolution_protocol: Dict = metric_data.get("resolution_protocol", {})
        self.default_quality_profile: str = metric_data.get("default_quality_profile", "decision_balanced")


class PatternSpec:
    """Pattern 스펙"""

    def __init__(self, pattern_id: str, name: str, constraints: Dict[str, Any]):
        self.pattern_id = pattern_id
        self.name = name
        self.constraints = constraints


class CMISConfig:
    """CMIS 메인 설정 클래스

    cmis.yaml 로딩 및 스펙 인덱싱
    """

    def __init__(self, yaml_path: str | Path = "cmis.yaml"):
        """
        Args:
            yaml_path: YAML 설정 파일 경로
        """
        self.yaml_path = Path(yaml_path)
        self.project_root = self.yaml_path.parent.resolve()

        # YAML 로드
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            self.raw_yaml = yaml.safe_load(f)

        # cmis 루트 접근
        self.cmis = self.raw_yaml.get("cmis", {})

        # 인덱싱
        self.metrics: Dict[str, MetricSpec] = self._index_metrics()
        self.metric_sets: Dict[str, List[str]] = self._index_metric_sets()
        self.patterns: Dict[str, PatternSpec] = self._index_patterns()
        self.data_sources: Dict[str, Dict] = self._index_data_sources()
        self.policies: Dict[str, Dict] = self._index_policies()
        self.tool_and_resource_registry: Dict[str, Any] = self._index_tool_and_resource_registry()

        # Environment 설정
        self.env = Settings()

    def _resolve_path(self, path: str | Path) -> Path:
        """cmis.yaml 기준 상대 경로를 절대 경로로 변환"""
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.project_root / p).resolve()

    def _load_yaml_file(self, path: str | Path) -> Dict[str, Any]:
        """외부 YAML 파일 로딩 (없으면 빈 dict 반환)"""
        p = self._resolve_path(path)
        if not p.exists():
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_metrics_spec_doc(self) -> Dict[str, Any]:
        """metrics_spec.yaml 로딩"""
        metrics_path = (
            self.cmis.get("modules", {})
            .get("libraries", {})
            .get("metrics_spec", "libraries/metrics_spec.yaml")
        )
        return self._load_yaml_file(metrics_path)

    def _index_metrics(self) -> Dict[str, MetricSpec]:
        """Metric 스펙 인덱싱"""
        metrics = {}

        try:
            metrics_spec = self._load_metrics_spec_doc()
            metrics_list = metrics_spec.get("metrics", []) or []

            for m in metrics_list:
                metric_id = m.get("metric_id")
                if metric_id:
                    metrics[metric_id] = MetricSpec(m)

        except KeyError as e:
            print(f"Warning: Metric 스펙 로딩 실패 - {e}")

        return metrics

    def _index_metric_sets(self) -> Dict[str, List[str]]:
        """Metric Set 인덱싱"""
        try:
            metrics_spec = self._load_metrics_spec_doc()
            metric_sets = metrics_spec.get("metric_sets", {}) or {}
            if not isinstance(metric_sets, dict):
                return {}
            return metric_sets
        except KeyError:
            return {}

    def _index_patterns(self) -> Dict[str, PatternSpec]:
        """Pattern 스펙 인덱싱"""
        # 현재는 코드 기반 패턴 정의
        # Pattern Graph로 확장 가능
        return {}

    def _index_data_sources(self) -> Dict[str, Dict]:
        """Data Source 인덱싱"""
        sources = {}

        try:
            substrate = self.cmis["planes"]["substrate_plane"]
            data_sources = substrate.get("data_sources", {})
            sources_list = data_sources.get("sources", [])

            for src in sources_list:
                source_id = src.get("id")
                if source_id:
                    sources[source_id] = src

        except KeyError as e:
            print(f"Warning: Data Sources 로딩 실패 - {e}")

        return sources

    def _index_policies(self) -> Dict[str, Dict]:
        """Policy 인덱싱"""
        try:
            policies = self.cmis.get("policies", {})
            return {
                "quality_profiles": policies.get("quality_profiles", {})
            }
        except KeyError:
            return {"quality_profiles": {}}

    def _index_tool_and_resource_registry(self) -> Dict[str, Any]:
        """Tool/Resource registry 인덱싱 (cmis.yaml contract)."""
        try:
            orch = (self.cmis.get("planes", {}) or {}).get("orchestration_plane", {}) or {}
            reg = orch.get("tool_and_resource_registry", {}) or {}
            return reg if isinstance(reg, dict) else {}
        except Exception:
            return {}

    # --- 편의 메서드 ---

    def get_metric_spec(self, metric_id: str) -> Optional[MetricSpec]:
        """Metric 스펙 조회"""
        return self.metrics.get(metric_id)

    def get_metric_set(self, set_name: str) -> List[str]:
        """Metric Set 조회 (예: "structure_core_economics")"""
        return self.metric_sets.get(set_name, [])

    def get_data_source(self, source_id: str) -> Optional[Dict]:
        """Data Source 조회"""
        return self.data_sources.get(source_id)

    def list_tool_ids(self) -> List[str]:
        """등록된 Tool ID 목록 반환 (없으면 빈 리스트)."""
        tools = self.tool_and_resource_registry.get("tools", []) or []
        if not isinstance(tools, list):
            return []
        ids: List[str] = []
        for t in tools:
            if isinstance(t, dict) and t.get("id"):
                ids.append(str(t.get("id")))
        return ids

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Tool registry entry 조회."""
        tools = self.tool_and_resource_registry.get("tools", []) or []
        if not isinstance(tools, list):
            return None
        for t in tools:
            if isinstance(t, dict) and str(t.get("id")) == str(tool_id):
                return t
        return None


# 싱글톤 패턴 (선택적)
_global_config: Optional[CMISConfig] = None


def get_config(yaml_path: str | Path = "cmis.yaml") -> CMISConfig:
    """전역 Config 인스턴스 가져오기"""
    global _global_config

    if _global_config is None:
        _global_config = CMISConfig(yaml_path)

    return _global_config
