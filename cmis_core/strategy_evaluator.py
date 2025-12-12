"""Strategy Evaluator - 전략 평가

Execution Fit, ROI, Risk 계산

2025-12-11: StrategyEngine Phase 1
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from .types import Strategy, PatternMatch, ProjectContext
from .pattern_library import PatternLibrary
from .pattern_scorer import PatternScorer
from .value_engine import ValueEngine


class StrategyEvaluator:
    """전략 평가기
    
    역할:
    1. Execution Fit 계산 (PatternScorer 재사용)
    2. ROI/Outcomes 예측 (ValueEngine 연동)
    3. Risk 평가
    """
    
    def __init__(
        self,
        pattern_library: Optional[PatternLibrary] = None,
        pattern_scorer: Optional[PatternScorer] = None,
        value_engine: Optional[ValueEngine] = None
    ):
        """
        Args:
            pattern_library: Pattern 라이브러리
            pattern_scorer: Pattern Scorer
            value_engine: Value Engine
        """
        if pattern_library is None:
            pattern_library = PatternLibrary()
            try:
                pattern_library.load_all()
            except Exception:
                pass
        
        self.pattern_library = pattern_library
        self.pattern_scorer = pattern_scorer or PatternScorer()
        self.value_engine = value_engine
    
    def calculate_execution_fit(
        self,
        strategy: Strategy,
        project_context: ProjectContext
    ) -> float:
        """Strategy Execution Fit 계산
        
        각 Pattern의 Execution Fit 평균 또는 최소값
        
        Args:
            strategy: Strategy
            project_context: ProjectContext
        
        Returns:
            Execution Fit (0.0 ~ 1.0)
        """
        if not strategy.pattern_composition:
            return 0.0
        
        pattern_fits = []
        
        for pattern_id in strategy.pattern_composition:
            pattern = self.pattern_library.get(pattern_id)
            
            if pattern:
                # PatternScorer 재사용
                fit = self.pattern_scorer.calculate_execution_fit(
                    pattern,
                    project_context
                )
                pattern_fits.append(fit)
        
        if not pattern_fits:
            return 0.0
        
        # 보수적: 최소값 (모든 Pattern이 실행 가능해야 함)
        return min(pattern_fits)
    
    def predict_outcomes(
        self,
        strategy: Strategy,
        baseline_state: Dict[str, Any],
        horizon_years: int = 3
    ) -> Dict[str, Any]:
        """ROI/Outcomes 예측
        
        Phase 1: Pattern Benchmark 기반 간단한 계산
        Phase 2: ValueEngine 시뮬레이션
        
        Args:
            strategy: Strategy
            baseline_state: 현재 상태
            horizon_years: 예측 기간 (년)
        
        Returns:
            Outcomes dict
        """
        # 1. Pattern Benchmark 통합
        benchmarks = self._aggregate_pattern_benchmarks(
            strategy.pattern_composition
        )
        
        # 2. Baseline
        current_revenue = baseline_state.get("current_revenue", 0)
        current_customers = baseline_state.get("current_customers", 0)
        current_margin = baseline_state.get("gross_margin", 0.5)
        
        # 3. Growth 시뮬레이션
        # Revenue
        revenue_growth = benchmarks.get("revenue_growth_yoy", [0.3, 0.5])
        avg_revenue_growth = sum(revenue_growth) / len(revenue_growth) if revenue_growth else 0.3
        
        future_revenue = current_revenue * ((1 + avg_revenue_growth) ** horizon_years)
        
        # Customer
        customer_growth = benchmarks.get("customer_growth_yoy", [0.25, 0.4])
        avg_customer_growth = sum(customer_growth) / len(customer_growth) if customer_growth else 0.25
        
        future_customers = current_customers * ((1 + avg_customer_growth) ** horizon_years)
        
        # Margin
        target_margin_range = benchmarks.get("gross_margin", [0.6, 0.8])
        target_margin = sum(target_margin_range) / len(target_margin_range) if target_margin_range else 0.7
        
        # 4. 투자 추정
        # Pattern family 기반 대략적 추정
        required_investment = self._estimate_investment(strategy, benchmarks)
        required_timeline = horizon_years * 12  # months
        required_team = self._estimate_team_size(strategy, benchmarks)
        
        # 5. ROI 계산
        if current_revenue > 0 and required_investment > 0:
            revenue_increase = future_revenue - current_revenue
            roi = revenue_increase / required_investment
        else:
            roi = 2.0  # 기본값
        
        # 6. Outcomes
        outcomes = {
            "revenue_3y": future_revenue,
            "customers_3y": future_customers,
            "gross_margin_3y": target_margin,
            "revenue_cagr": avg_revenue_growth,
            "customer_cagr": avg_customer_growth,
            "roi": roi,
            "required_investment": required_investment,
            "required_timeline_months": required_timeline,
            "required_team_size": required_team,
            "confidence": 0.6,  # Pattern Prior 기반
            "method": "pattern_benchmark_projection",
            "lineage": {
                "patterns": strategy.pattern_composition,
                "engine": "strategy_evaluator_phase1",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return outcomes
    
    def assess_risks(
        self,
        strategy: Strategy,
        project_context: Optional[ProjectContext],
        matched_patterns: List[PatternMatch]
    ) -> List[Dict[str, Any]]:
        """Risk 평가
        
        Risk 타입:
        1. Execution Risk (Execution Fit 낮음)
        2. Resource Risk (필요 > 가용)
        3. Cannibalization Risk (기존 사업 충돌)
        4. Market Risk (경쟁 강도)
        
        Args:
            strategy: Strategy
            project_context: ProjectContext (선택)
            matched_patterns: 이미 매칭된 Pattern
        
        Returns:
            Risk 리스트
        """
        risks = []
        
        # 1. Execution Risk
        if strategy.execution_fit_score is not None:
            if strategy.execution_fit_score < 0.5:
                risks.append({
                    "type": "execution",
                    "severity": "high",
                    "description": f"Execution Fit 낮음 ({strategy.execution_fit_score:.2f})",
                    "mitigation": "역량 강화 또는 파트너십 고려"
                })
            elif strategy.execution_fit_score < 0.7:
                risks.append({
                    "type": "execution",
                    "severity": "medium",
                    "description": f"Execution Fit 보통 ({strategy.execution_fit_score:.2f})"
                })
        
        # 2. Resource Risk (Brownfield만)
        if project_context:
            required = strategy.expected_outcomes.get("required_investment", 0)
            available = project_context.assets_profile.get("budget", float('inf'))
            
            if required > available:
                risks.append({
                    "type": "resource",
                    "severity": "high",
                    "description": f"예산 부족 (필요: {required:,.0f}, 가용: {available:,.0f})"
                })
        
        # 3. Cannibalization Risk
        matched_pattern_ids = {pm.pattern_id for pm in matched_patterns}
        
        for pattern_id in strategy.pattern_composition:
            if pattern_id in matched_pattern_ids:
                # 이미 매칭된 Pattern → 기존 사업 충돌 가능
                risks.append({
                    "type": "cannibalization",
                    "severity": "low",
                    "description": f"{pattern_id} 기존 사업과 overlap",
                    "mitigation": "시장 세분화 또는 차별화 전략"
                })
        
        # 4. Market Risk (간단한 휴리스틱)
        if len(strategy.pattern_composition) > 2:
            # 복잡한 조합 → 실행 리스크
            risks.append({
                "type": "complexity",
                "severity": "medium",
                "description": f"{len(strategy.pattern_composition)}개 Pattern 조합 복잡도"
            })
        
        return risks
    
    def _aggregate_pattern_benchmarks(
        self,
        pattern_ids: List[str]
    ) -> Dict[str, Any]:
        """Pattern Benchmark 통합
        
        여러 Pattern의 quantitative_bounds 통합
        
        Args:
            pattern_ids: Pattern ID 리스트
        
        Returns:
            통합 Benchmark
        """
        benchmarks = {}
        
        for pattern_id in pattern_ids:
            pattern = self.pattern_library.get(pattern_id)
            
            if not pattern or not pattern.quantitative_bounds:
                continue
            
            for metric_id, bounds in pattern.quantitative_bounds.items():
                if metric_id not in benchmarks:
                    benchmarks[metric_id] = bounds.get("typical", [])
        
        return benchmarks
    
    def _estimate_investment(
        self,
        strategy: Strategy,
        benchmarks: Dict[str, Any]
    ) -> float:
        """투자 규모 추정
        
        Phase 1: Pattern family 기반 대략 추정
        
        Args:
            strategy: Strategy
            benchmarks: Pattern benchmarks
        
        Returns:
            필요 투자 (KRW)
        """
        # 간단한 휴리스틱
        # - asset_light: 낮음
        # - capital_intensive: 높음
        # - platform: 중간-높음
        
        base_investment = 500000000  # 기본 5억
        
        for pattern_id in strategy.pattern_composition:
            pattern = self.pattern_library.get(pattern_id)
            
            if pattern:
                family = pattern.family
                
                if "capital_intensive" in pattern_id or "capital" in family:
                    base_investment *= 3
                elif "platform" in pattern_id or "platform" in family:
                    base_investment *= 2
                elif "asset_light" in pattern_id:
                    base_investment *= 0.5
        
        return base_investment
    
    def _estimate_team_size(
        self,
        strategy: Strategy,
        benchmarks: Dict[str, Any]
    ) -> int:
        """팀 규모 추정
        
        Args:
            strategy: Strategy
            benchmarks: Benchmarks
        
        Returns:
            필요 팀 규모
        """
        base_team = 10
        
        # Pattern 수에 따라
        base_team += len(strategy.pattern_composition) * 5
        
        return min(base_team, 50)  # 최대 50
