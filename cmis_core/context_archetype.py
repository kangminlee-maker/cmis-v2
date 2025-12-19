"""Context Archetype - 시장/산업 전형 판별

특정 시장/산업의 전형적인 특징을 파악하고 Expected Pattern Set 제공

2025-12-10: Phase 2
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .types import ContextArchetype, FocalActorContext
from .graph import InMemoryGraph


class ContextArchetypeLibrary:
    """Context Archetype 저장소

    역할:
    1. Archetype YAML 로딩
    2. Archetype 조회 (criteria 기반)
    3. Expected Pattern Set 제공
    """

    def __init__(self, archetype_dir: Optional[str] = None):
        """
        Args:
            archetype_dir: Archetype YAML 디렉토리
        """
        self.archetype_dir = archetype_dir or self._get_default_dir()
        self.archetypes: Dict[str, ContextArchetype] = {}
        self.fallback_archetype: Optional[ContextArchetype] = None

    def _get_default_dir(self) -> str:
        """기본 디렉토리"""
        current_dir = Path(__file__).parent
        root_dir = current_dir.parent
        return str(root_dir / "config" / "archetypes")

    def load_all(self) -> None:
        """모든 Archetype 로딩"""
        archetype_dir_path = Path(self.archetype_dir)

        if not archetype_dir_path.exists():
            print(f"Warning: Archetype directory not found: {self.archetype_dir}")
            self._create_fallback()
            return

        yaml_files = list(archetype_dir_path.glob("*.yaml"))

        if not yaml_files:
            print(f"Warning: No archetype YAML files found")
            self._create_fallback()
            return

        for yaml_file in yaml_files:
            try:
                self._load_yaml(yaml_file)
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file.name}: {e}")

        self._create_fallback()
        print(f"Loaded {len(self.archetypes)} archetypes")

    def _load_yaml(self, yaml_path: Path) -> None:
        """단일 YAML 로딩"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data or 'archetype' not in data:
            return

        arch_data = data['archetype']

        archetype = ContextArchetype(
            archetype_id=arch_data['archetype_id'],
            name=arch_data['name'],
            description=arch_data['description'],
            criteria=arch_data.get('criteria', {}),
            expected_patterns=arch_data.get('expected_patterns', {})
        )

        self.archetypes[archetype.archetype_id] = archetype

    def _create_fallback(self) -> None:
        """Fallback Archetype 생성"""
        self.fallback_archetype = ContextArchetype(
            archetype_id="ARCH-fallback",
            name="Fallback Archetype",
            description="기본 Archetype (판별 불가 시)",
            criteria={},
            expected_patterns={
                "core": [],
                "common": [],
                "rare": []
            },
            confidence=0.3
        )

    def find_by_criteria(self, **criteria) -> Optional[ContextArchetype]:
        """Criteria 기반 Archetype 검색

        Args:
            **criteria: domain, region, delivery_channel 등

        Returns:
            매칭되는 Archetype (없으면 None)
        """
        for archetype in self.archetypes.values():
            if self._criteria_matches(archetype.criteria, criteria):
                return archetype

        return None

    def _criteria_matches(
        self,
        archetype_criteria: Dict,
        search_criteria: Dict
    ) -> bool:
        """Criteria 매칭 여부

        Args:
            archetype_criteria: Archetype의 criteria
            search_criteria: 검색 criteria

        Returns:
            매칭 여부
        """
        # 모든 archetype_criteria 키가 search_criteria에 일치해야 함
        for key, value in archetype_criteria.items():
            if key not in search_criteria:
                return False

            if isinstance(value, list):
                if search_criteria[key] not in value:
                    return False
            else:
                if search_criteria[key] != value:
                    return False

        return True

    def get_fallback(self) -> ContextArchetype:
        """Fallback Archetype 반환"""
        return self.fallback_archetype

    def get(self, archetype_id: str) -> Optional[ContextArchetype]:
        """Archetype 조회"""
        return self.archetypes.get(archetype_id)


# ========================================
# Context Archetype 결정 (3단계)
# ========================================

def determine_context_archetype(
    graph: InMemoryGraph,
    focal_actor_context_id: Optional[str] = None,
    archetype_library: Optional[ContextArchetypeLibrary] = None
) -> Optional[ContextArchetype]:
    """Context Archetype 결정 (3단계)

    우선순위:
    1. Project Context의 scope 사용 (confidence 0.95)
    2. RealityGraph의 Actor/Resource trait voting (confidence 0.7)
    3. Fallback archetype (confidence 0.3)

    Args:
        graph: Reality Graph
        focal_actor_context_id: FocalActorContext ID (선택)
        archetype_library: Archetype 라이브러리 (None이면 새로 로딩)

    Returns:
        ContextArchetype (신뢰도 포함)
    """
    if archetype_library is None:
        archetype_library = ContextArchetypeLibrary()
        archetype_library.load_all()

    # 1차: FocalActorContext 기반 (가장 정확)
    if focal_actor_context_id:
        # Phase 2: store-first 로딩
        try:
            from .stores.focal_actor_context_store import FocalActorContextStore

            store = FocalActorContextStore()
            try:
                record = store.get_latest(focal_actor_context_id)
            finally:
                store.close()

            scope = dict(record.scope) if record is not None else {}

            archetype = archetype_library.find_by_criteria(
                domain=scope.get("domain_id"),
                region=scope.get("region")
            )

            if archetype:
                archetype.confidence = 0.95
                return archetype
        except Exception:
            pass

    # 2차: RealityGraph Trait 기반 (Majority Voting)
    trait_votes = defaultdict(int)

    actors = graph.nodes_by_type("actor")
    resources = graph.nodes_by_type("resource")

    for actor in actors:
        traits = actor.data.get("traits", {})

        # Domain expertise
        if "domain_expertise" in traits:
            trait_votes[("domain", traits["domain_expertise"])] += 1

        # Institution type
        if "institution_type" in traits:
            trait_votes[("institution_type", traits["institution_type"])] += 1

    for resource in resources:
        traits = resource.data.get("traits", {})

        # Delivery channel
        if "delivery_channel" in traits:
            trait_votes[("channel", traits["delivery_channel"])] += 1

        # Resource kind
        if "kind" in resource.data:
            trait_votes[("resource_kind", resource.data["kind"])] += 1

    # 가장 많이 나타난 trait 조합으로 검색
    if trait_votes:
        top_traits = sorted(trait_votes.items(), key=lambda x: x[1], reverse=True)

        criteria = {}
        for (trait_type, value), _ in top_traits[:3]:  # 상위 3개
            criteria[trait_type] = value

        archetype = archetype_library.find_by_criteria(**criteria)

        if archetype:
            archetype.confidence = 0.7
            return archetype

    # 3차: Fallback
    fallback = archetype_library.get_fallback()
    fallback.confidence = 0.3
    return fallback
