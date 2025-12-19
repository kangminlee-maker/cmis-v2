"""Strategy Library - 전략 템플릿 및 과거 전략 저장소

StrategyTemplate, 성공/실패 전략 관리

2025-12-11: StrategyEngine Phase 3
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from .types import Strategy


class StrategyLibrary:
    """Strategy 라이브러리

    역할:
    1. StrategyTemplate YAML 로딩
    2. 과거 Strategy 조회
    3. LearningEngine 연동 준비
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Args:
            template_dir: Strategy 템플릿 디렉토리
        """
        if template_dir is None:
            current_dir = Path(__file__).parent
            root_dir = current_dir.parent
            template_dir = root_dir / "config" / "strategy_templates"

        self.template_dir = Path(template_dir)
        self.templates: Dict[str, Dict] = {}
        self.strategies_history: List[Strategy] = []

    def load_templates(self) -> None:
        """StrategyTemplate YAML 로딩

        Phase 3: 기본 구조만
        """
        if not self.template_dir.exists():
            return

        yaml_files = list(self.template_dir.glob("*.yaml"))

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                if data and 'strategy_template' in data:
                    template = data['strategy_template']
                    template_id = template.get('template_id')

                    if template_id:
                        self.templates[template_id] = template

            except Exception as e:
                print(f"Warning: Failed to load {yaml_file.name}: {e}")

    def get_template(self, template_id: str) -> Optional[Dict]:
        """템플릿 조회

        Args:
            template_id: Template ID

        Returns:
            Template dict 또는 None
        """
        return self.templates.get(template_id)

    def get_strategies_by_pattern(
        self,
        pattern_id: str
    ) -> List[Strategy]:
        """특정 Pattern 사용 전략 조회

        Args:
            pattern_id: Pattern ID

        Returns:
            Strategy 리스트
        """
        return [
            s for s in self.strategies_history
            if pattern_id in s.pattern_composition
        ]

    def add_strategy_to_history(
        self,
        strategy: Strategy
    ) -> None:
        """전략을 히스토리에 추가

        LearningEngine 연동 준비

        Args:
            strategy: Strategy
        """
        self.strategies_history.append(strategy)

    def get_successful_strategies(
        self,
        min_roi: float = 1.5
    ) -> List[Strategy]:
        """성공한 전략 조회

        Phase 3: ROI 기준만
        LearningEngine에서 실제 Outcome 기반으로 업데이트

        Args:
            min_roi: 최소 ROI

        Returns:
            Strategy 리스트
        """
        return [
            s for s in self.strategies_history
            if s.expected_outcomes.get("roi", 0) >= min_roi
        ]
