"""Pattern Engine v2 - Phase 1 Core Infrastructure

Trait 기반 패턴 매칭 및 구조 적합도 계산

2025-12-10: v1.1 설계 반영
- PatternSpec 13개 필드
- PatternMatch 8개 필드
- Structure Fit (Trait + Graph)
- 5개 Pattern 지원
"""

from __future__ import annotations

from typing import List, Optional

from .types import PatternSpec, PatternMatch, GapCandidate
from .graph import InMemoryGraph
from .pattern_library import PatternLibrary
from .pattern_matcher import PatternMatcher
from .pattern_scorer import PatternScorer
from .gap_discoverer import GapDiscoverer


class PatternEngineV2:
    """Pattern Engine v2 (Phase 1)

    기능:
    - Pattern 매칭 (Trait + Graph 기반)
    - Structure Fit 계산
    - 5개 Pattern 지원 (각 Family 1개)

    Phase 1: Core Infrastructure
    Phase 2: Execution Fit, Gap Discovery
    Phase 3: P-Graph 통합, Learning
    """

    def __init__(self, pattern_dir: Optional[str] = None):
        """
        Args:
            pattern_dir: Pattern YAML 디렉토리 (None이면 기본 경로)
        """
        self.library = PatternLibrary(pattern_dir)
        self.matcher = PatternMatcher()
        self.scorer = PatternScorer()
        self.gap_discoverer = GapDiscoverer(pattern_library=self.library)

        # Pattern 로딩
        try:
            self.library.load_all()
        except Exception as e:
            print(f"Warning: Pattern loading failed: {e}")
            print("PatternEngine initialized with empty pattern library")

    def match_patterns(
        self,
        graph: InMemoryGraph,
        focal_actor_context_id: Optional[str] = None,
    ) -> List[PatternMatch]:
        """Pattern 매칭

        프로세스:
        1. 후보 Pattern 조회 (Phase 1: 전체, Phase 2: Index 활용)
        2. Trait/Graph 매칭
        3. Structure Fit 계산
        4. (Phase 2) Execution Fit 계산
        5. Combined Score 계산 및 정렬

        Args:
            graph: Reality Graph (InMemoryGraph)
            focal_actor_context_id: FocalActorContext ID (선택)

        Returns:
            PatternMatch 리스트 (combined_score 기준 정렬)
        """
        # 1. 후보 Pattern 조회
        pattern_candidates = self.library.get_all()

        if not pattern_candidates:
            return []

        # 2. 매칭
        match_results = self.matcher.match(graph, pattern_candidates)

        if not match_results:
            return []

        # 3. 점수 계산
        scored_matches = self.scorer.score_all(match_results, focal_actor_context_id)

        return scored_matches

    def discover_gaps(
        self,
        graph: InMemoryGraph,
        focal_actor_context_id: Optional[str] = None,
        precomputed_matches: Optional[List[PatternMatch]] = None
    ) -> List[GapCandidate]:
        """Gap 탐지

        프로세스:
        1. precomputed_matches 재사용 (있다면)
        2. Context Archetype 결정
        3. Expected - Matched 계산
        4. Feasibility 평가

        Args:
            graph: Reality Graph
            focal_actor_context_id: FocalActorContext ID (선택)
            precomputed_matches: 이미 계산된 매칭 결과 (성능 최적화)

        Returns:
            GapCandidate 리스트
        """
        # 1. Matched Patterns 확보 (재사용 또는 새로 계산)
        if precomputed_matches is None:
            precomputed_matches = self.match_patterns(graph, focal_actor_context_id)

        # 2. Gap Discovery
        gaps = self.gap_discoverer.discover_gaps(
            graph,
            precomputed_matches,
            focal_actor_context_id,
        )

        return gaps

    def get_pattern(self, pattern_id: str) -> Optional[PatternSpec]:
        """Pattern 조회

        Args:
            pattern_id: Pattern ID

        Returns:
            PatternSpec (없으면 None)
        """
        return self.library.get(pattern_id)

    def get_all_patterns(self) -> List[PatternSpec]:
        """모든 Pattern 조회

        Returns:
            PatternSpec 리스트
        """
        return self.library.get_all()
