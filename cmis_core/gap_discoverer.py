"""Gap Discoverer - Pattern Gap 탐지

Expected Pattern과 Matched Pattern을 비교하여 기회 발굴

2025-12-10: Phase 2
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any

from .types import PatternMatch, GapCandidate, ContextArchetype
from .graph import InMemoryGraph
from .context_archetype import (
    determine_context_archetype,
    ContextArchetypeLibrary
)
from .pattern_library import PatternLibrary


class GapDiscoverer:
    """Gap Discovery 엔진
    
    역할:
    1. Context Archetype 결정
    2. Expected Pattern Set 조회
    3. Gap = Expected - Matched 계산
    4. Feasibility 평가
    """
    
    def __init__(
        self,
        archetype_library: Optional[ContextArchetypeLibrary] = None,
        pattern_library: Optional[PatternLibrary] = None
    ):
        """
        Args:
            archetype_library: Archetype 라이브러리
            pattern_library: Pattern 라이브러리
        """
        self.archetype_library = archetype_library or ContextArchetypeLibrary()
        self.pattern_library = pattern_library or PatternLibrary()
        
        # 초기화
        try:
            self.archetype_library.load_all()
        except Exception as e:
            print(f"Warning: Archetype loading failed: {e}")
        
        try:
            self.pattern_library.load_all()
        except Exception as e:
            print(f"Warning: Pattern loading failed: {e}")
    
    def discover_gaps(
        self,
        graph: InMemoryGraph,
        matched_patterns: List[PatternMatch],
        project_context_id: Optional[str] = None
    ) -> List[GapCandidate]:
        """Gap 탐지
        
        프로세스:
        1. Context Archetype 결정
        2. Expected Pattern Set 조회
        3. Gap = Expected - Matched
        4. Feasibility 평가 (execution_fit 재사용)
        
        Args:
            graph: Reality Graph
            matched_patterns: 이미 매칭된 Pattern 리스트
            project_context_id: Project Context ID (선택)
        
        Returns:
            GapCandidate 리스트 (정렬: expected_level → feasibility)
        """
        # 1. Context Archetype 결정
        archetype = determine_context_archetype(
            graph,
            project_context_id,
            self.archetype_library
        )
        
        if not archetype:
            return []  # Archetype 판별 불가
        
        # 2. Expected Pattern Set
        expected_patterns = archetype.expected_patterns
        
        # 3. Matched Pattern IDs
        matched_ids = {m.pattern_id for m in matched_patterns}
        
        # 4. Gap Identification
        gaps = []
        
        for level in ["core", "common", "rare"]:
            for expected in expected_patterns.get(level, []):
                pattern_id = expected["pattern_id"]
                
                if pattern_id not in matched_ids:
                    # Gap 발견!
                    pattern = self.pattern_library.get(pattern_id)
                    
                    if not pattern:
                        continue  # Pattern 정의 없음
                    
                    # Feasibility 평가
                    feasibility, execution_fit = self._evaluate_feasibility(
                        pattern,
                        matched_patterns,
                        project_context_id
                    )
                    
                    gap = GapCandidate(
                        pattern_id=pattern_id,
                        description=f"Missing: {pattern.name}",
                        expected_level=level,
                        feasibility=feasibility,
                        execution_fit_score=execution_fit,
                        related_pattern_ids=pattern.composes_with,
                        evidence={
                            "archetype": archetype.archetype_id,
                            "archetype_confidence": archetype.confidence,
                            "expected_level": level,
                            "expected_weight": expected.get("weight", 0.5),
                            "rationale": expected.get("rationale", "")
                        }
                    )
                    
                    gaps.append(gap)
        
        # 5. 정렬
        gaps = self._sort_gaps(gaps)
        
        return gaps
    
    def _evaluate_feasibility(
        self,
        pattern: Any,
        matched_patterns: List[PatternMatch],
        project_context_id: Optional[str]
    ) -> tuple[str, Optional[float]]:
        """Feasibility 평가
        
        Args:
            pattern: Gap Pattern
            matched_patterns: 이미 매칭된 Pattern 리스트
            project_context_id: Project Context ID
        
        Returns:
            (feasibility, execution_fit_score)
            - feasibility: "high" | "medium" | "low" | "unknown"
            - execution_fit_score: 0.0 ~ 1.0 or None
        """
        if not project_context_id:
            return ("unknown", None)
        
        # Execution Fit 계산 (PatternScorer 재사용)
        from .pattern_scorer import PatternScorer
        from .types import ProjectContext
        
        scorer = PatternScorer()
        
        # Project Context 로딩 (간단한 버전)
        project_context = scorer._load_project_context(project_context_id)
        
        execution_fit = scorer.calculate_execution_fit(pattern, project_context)
        
        # Feasibility 레벨 결정
        if execution_fit >= 0.7:
            feasibility = "high"
        elif execution_fit >= 0.4:
            feasibility = "medium"
        else:
            feasibility = "low"
        
        return (feasibility, execution_fit)
    
    def _sort_gaps(self, gaps: List[GapCandidate]) -> List[GapCandidate]:
        """Gap 정렬
        
        정렬 기준:
        1. expected_level (core > common > rare)
        2. feasibility (high > medium > low > unknown)
        3. execution_fit_score (높은 순)
        
        Args:
            gaps: GapCandidate 리스트
        
        Returns:
            정렬된 GapCandidate 리스트
        """
        level_order = {"core": 3, "common": 2, "rare": 1}
        feasibility_order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
        
        gaps.sort(
            key=lambda g: (
                level_order.get(g.expected_level, 0),
                feasibility_order.get(g.feasibility, 0),
                g.execution_fit_score or 0.0
            ),
            reverse=True
        )
        
        return gaps

