"""Pattern Library - Pattern 정의 관리 및 검증

Pattern YAML 파일을 로딩하고, 검증하며, P-Graph로 컴파일합니다.

2025-12-10: Phase 1 Core Infrastructure
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from .types import PatternSpec
from .graph import InMemoryGraph


class PatternValidationError(Exception):
    """Pattern 검증 오류"""
    pass


class PatternLibrary:
    """Pattern 정의 저장소
    
    역할:
    1. YAML 파일에서 Pattern 로딩
    2. Pattern 검증 (trait key, metric ID, pattern ID 참조)
    3. P-Graph로 컴파일
    4. Pattern 조회/등록 API
    
    Phase 1: YAML 로딩 + 기본 검증
    Phase 2: P-Graph 컴파일
    Phase 3: Runtime 업데이트 (LearningEngine 연동)
    """
    
    def __init__(self, pattern_dir: Optional[str] = None):
        """
        Args:
            pattern_dir: Pattern YAML 디렉토리 (None이면 config/patterns/)
        """
        self.pattern_dir = pattern_dir or self._get_default_pattern_dir()
        self.patterns: Dict[str, PatternSpec] = {}
        self.p_graph: Optional[InMemoryGraph] = None
    
    def _get_default_pattern_dir(self) -> str:
        """기본 Pattern 디렉토리 경로"""
        # cmis_core/../config/patterns/
        current_dir = Path(__file__).parent
        root_dir = current_dir.parent
        return str(root_dir / "config" / "patterns")
    
    def load_all(self) -> None:
        """모든 Pattern YAML 로딩 및 검증"""
        pattern_dir_path = Path(self.pattern_dir)
        
        if not pattern_dir_path.exists():
            raise PatternValidationError(
                f"Pattern directory not found: {self.pattern_dir}"
            )
        
        # YAML 파일 검색
        yaml_files = list(pattern_dir_path.glob("*.yaml")) + \
                     list(pattern_dir_path.glob("*.yml"))
        
        if not yaml_files:
            raise PatternValidationError(
                f"No YAML files found in: {self.pattern_dir}"
            )
        
        # 각 파일 로딩
        for yaml_file in yaml_files:
            try:
                self._load_yaml(yaml_file)
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file.name}: {e}")
                continue
        
        print(f"Loaded {len(self.patterns)} patterns from {len(yaml_files)} files")
    
    def _load_yaml(self, yaml_path: Path) -> None:
        """단일 YAML 파일 로딩
        
        Args:
            yaml_path: YAML 파일 경로
        """
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'pattern' not in data:
            raise PatternValidationError(
                f"Invalid YAML structure in {yaml_path.name}"
            )
        
        pattern_data = data['pattern']
        
        # PatternSpec 생성
        pattern_spec = PatternSpec(
            pattern_id=pattern_data['pattern_id'],
            name=pattern_data['name'],
            family=pattern_data['family'],
            description=pattern_data['description'],
            trait_constraints=pattern_data.get('trait_constraints', {}),
            graph_structure=pattern_data.get('graph_structure', {}),
            quantitative_bounds=pattern_data.get('quantitative_bounds'),
            composes_with=pattern_data.get('composes_with', []),
            conflicts_with=pattern_data.get('conflicts_with', []),
            specializes=pattern_data.get('specializes'),
            benchmark_metrics=pattern_data.get('benchmark_metrics', []),
            suited_for_contexts=pattern_data.get('suited_for_contexts', []),
            required_capabilities=pattern_data.get('required_capabilities', []),
            required_assets=pattern_data.get('required_assets', {}),
            constraint_checks=pattern_data.get('constraint_checks', [])
        )
        
        # 검증
        errors = self._validate_pattern_spec(pattern_spec)
        
        if errors:
            raise PatternValidationError(
                f"Pattern {pattern_spec.pattern_id} validation failed:\n" +
                "\n".join(f"  - {err}" for err in errors)
            )
        
        # 등록
        self.patterns[pattern_spec.pattern_id] = pattern_spec
    
    def _validate_pattern_spec(self, pattern: PatternSpec) -> List[str]:
        """Pattern 정의 검증
        
        Phase 1: 기본 검증 (필드 존재, 형식)
        Phase 2: Ontology 참조 검증 (trait key, metric ID)
        Phase 3: Pattern 관계 검증 (composes_with, conflicts_with)
        
        Returns:
            에러 메시지 리스트 (빈 리스트면 검증 통과)
        """
        errors = []
        
        # 1. 필수 필드 검증
        if not pattern.pattern_id or not pattern.pattern_id.startswith("PAT-"):
            errors.append(f"Invalid pattern_id: {pattern.pattern_id} (must start with PAT-)")
        
        if not pattern.name:
            errors.append("Name is required")
        
        if not pattern.family:
            errors.append("Family is required")
        
        # 2. trait_constraints 구조 검증
        if not pattern.trait_constraints:
            errors.append("trait_constraints is empty (at least one node_type required)")
        
        for node_type, constraints in pattern.trait_constraints.items():
            if not isinstance(constraints, dict):
                errors.append(f"trait_constraints[{node_type}] must be dict")
                continue
            
            if 'required_traits' not in constraints and 'optional_traits' not in constraints:
                errors.append(
                    f"trait_constraints[{node_type}] must have "
                    "required_traits or optional_traits"
                )
        
        # 3. graph_structure 검증
        if pattern.graph_structure:
            requires = pattern.graph_structure.get('requires', [])
            if not isinstance(requires, list):
                errors.append("graph_structure.requires must be list")
        
        # 4. benchmark_metrics 검증 (Phase 2에서 상세화)
        for metric_id in pattern.benchmark_metrics:
            if not metric_id.startswith("MET-"):
                errors.append(f"Invalid metric_id: {metric_id} (must start with MET-)")
        
        return errors
    
    def get(self, pattern_id: str) -> Optional[PatternSpec]:
        """Pattern 조회
        
        Args:
            pattern_id: Pattern ID
        
        Returns:
            PatternSpec (없으면 None)
        """
        return self.patterns.get(pattern_id)
    
    def get_all(self) -> List[PatternSpec]:
        """모든 Pattern 조회
        
        Returns:
            PatternSpec 리스트
        """
        return list(self.patterns.values())
    
    def get_by_family(self, family: str) -> List[PatternSpec]:
        """Family별 Pattern 조회
        
        Args:
            family: Family 이름
        
        Returns:
            PatternSpec 리스트
        """
        return [
            p for p in self.patterns.values()
            if p.family == family
        ]
    
    def exists(self, pattern_id: str) -> bool:
        """Pattern 존재 여부
        
        Args:
            pattern_id: Pattern ID
        
        Returns:
            존재하면 True
        """
        return pattern_id in self.patterns
    
    def register(self, pattern_spec: PatternSpec) -> None:
        """Pattern 등록 (Custom Pattern 추가용)
        
        Args:
            pattern_spec: PatternSpec
        
        Raises:
            PatternValidationError: 검증 실패
        """
        errors = self._validate_pattern_spec(pattern_spec)
        
        if errors:
            raise PatternValidationError(
                f"Pattern {pattern_spec.pattern_id} validation failed:\n" +
                "\n".join(f"  - {err}" for err in errors)
            )
        
        self.patterns[pattern_spec.pattern_id] = pattern_spec
    
    # ========================================
    # Phase 2: P-Graph 컴파일 (추후 구현)
    # ========================================
    
    def compile_to_p_graph(self) -> InMemoryGraph:
        """Pattern 정의를 P-Graph로 컴파일
        
        프로세스:
        1. pattern_family 노드 생성
        2. pattern 노드 생성
        3. pattern_belongs_to_family edge
        4. pattern 관계 edges (composes_with, conflicts_with, specializes)
        
        Returns:
            P-Graph (InMemoryGraph)
        """
        p_graph = InMemoryGraph()
        
        # 1. Pattern Family 노드 생성
        families = set(p.family for p in self.patterns.values())
        
        for family in families:
            p_graph.upsert_node(
                node_id=family,
                node_type="pattern_family",
                data={"name": family}
            )
        
        # 2. Pattern 노드 생성
        for pattern in self.patterns.values():
            p_graph.upsert_node(
                node_id=pattern.pattern_id,
                node_type="pattern",
                data={
                    "name": pattern.name,
                    "family": pattern.family,
                    "description": pattern.description,
                    "trait_constraints": pattern.trait_constraints,
                    "graph_structure": pattern.graph_structure,
                    "quantitative_bounds": pattern.quantitative_bounds,
                    "benchmark_metrics": pattern.benchmark_metrics
                }
            )
        
        # 3. pattern_belongs_to_family edge
        for pattern in self.patterns.values():
            p_graph.add_edge(
                edge_type="pattern_belongs_to_family",
                source=pattern.pattern_id,
                target=pattern.family,
                data={}
            )
        
        # 4. Pattern 관계 edges
        for pattern in self.patterns.values():
            # composes_with
            for related_id in pattern.composes_with:
                if self.exists(related_id):
                    p_graph.add_edge(
                        edge_type="pattern_composes_with",
                        source=pattern.pattern_id,
                        target=related_id,
                        data={"relationship": "composes_with"}
                    )
            
            # conflicts_with
            for conflicting_id in pattern.conflicts_with:
                if self.exists(conflicting_id):
                    p_graph.add_edge(
                        edge_type="pattern_composes_with",
                        source=pattern.pattern_id,
                        target=conflicting_id,
                        data={"relationship": "conflicts_with"}
                    )
            
            # specializes
            if pattern.specializes and self.exists(pattern.specializes):
                p_graph.add_edge(
                    edge_type="pattern_composes_with",
                    source=pattern.pattern_id,
                    target=pattern.specializes,
                    data={"relationship": "specializes"}
                )
        
        self.p_graph = p_graph
        
        print(f"P-Graph compiled: {len(p_graph.nodes)} nodes, {len(p_graph.edges)} edges")
        
        return p_graph

