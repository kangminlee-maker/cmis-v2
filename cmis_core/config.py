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
    """Metric 스펙 (cmis.yaml에서 로드)"""
    
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
        
        # Environment 설정
        self.env = Settings()
    
    def _index_metrics(self) -> Dict[str, MetricSpec]:
        """Metric 스펙 인덱싱"""
        metrics = {}
        
        try:
            engines = self.cmis["planes"]["cognition_plane"]["engines"]
            value_engine = engines.get("value_engine", {})
            metrics_spec = value_engine.get("metrics_spec", {})
            metrics_list = metrics_spec.get("metrics", [])
            
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
            engines = self.cmis["planes"]["cognition_plane"]["engines"]
            value_engine = engines.get("value_engine", {})
            metrics_spec = value_engine.get("metrics_spec", {})
            return metrics_spec.get("metric_sets", {})
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


# 싱글톤 패턴 (선택적)
_global_config: Optional[CMISConfig] = None


def get_config(yaml_path: str | Path = "cmis.yaml") -> CMISConfig:
    """전역 Config 인스턴스 가져오기"""
    global _global_config
    
    if _global_config is None:
        _global_config = CMISConfig(yaml_path)
    
    return _global_config
