"""Evidence Builder - 검색 결과 → EvidenceRecord 변환

Raw 검색 결과에서 EvidenceRecord 조립

2025-12-10: Search Strategy v2.0
"""

from __future__ import annotations

import uuid
import statistics
from typing import List, Dict, Any
from datetime import datetime, timezone

from .types import EvidenceRecord, EvidenceValueKind, MetricRequest, QueryResultQuality
from .search_executor import RawSearchResult


class EvidenceBuilder:
    """EvidenceRecord 조립자

    역할:
    - 숫자 추출
    - 품질 평가 (QueryResultQuality)
    - Consensus 계산
    - EvidenceRecord 조립
    """

    def from_search_results(
        self,
        raw_results: List[RawSearchResult],
        metric_request: MetricRequest
    ) -> List[EvidenceRecord]:
        """RawSearchResult → EvidenceRecord 변환

        Args:
            raw_results: 검색 결과들
            metric_request: Metric 요청

        Returns:
            EvidenceRecord 리스트
        """
        evidence_records = []

        for result in raw_results:
            # 1. 숫자 추출
            numbers = self._extract_numbers(result.content)

            if not numbers:
                continue

            # 2. 품질 평가
            quality = self._evaluate_quality(
                result,
                numbers,
                metric_request
            )

            if quality.score < 0.4:
                continue  # 품질 낮으면 제외

            # 3. Consensus
            value = statistics.median(numbers)
            confidence = self._calculate_confidence(numbers, quality)

            # 4. EvidenceRecord 생성
            record = EvidenceRecord(
                evidence_id=f"EVD-Search-{uuid.uuid4().hex[:8]}",
                source_tier="commercial",
                source_id=result.source_id,
                value=value,
                value_kind=EvidenceValueKind.NUMERIC,
                confidence=confidence,
                metadata={
                    "query": result.query,
                    "language": result.language,
                    "quality": {
                        "score": quality.score,
                        "has_numbers": quality.has_numbers,
                        "num_numbers": quality.num_numbers,
                        "year_match": quality.year_match
                    },
                    "hints": self._extract_hints(result, numbers)
                },
                retrieved_at=result.timestamp
            )

            evidence_records.append(record)

        return evidence_records

    def _extract_numbers(self, content: List[Dict]) -> List[float]:
        """숫자 추출 (간단한 버전)"""
        # Phase 2에서 base_search_source의 로직 재사용
        return []

    def _evaluate_quality(
        self,
        result: RawSearchResult,
        numbers: List[float],
        metric_request: MetricRequest
    ) -> QueryResultQuality:
        """품질 평가

        Returns:
            QueryResultQuality
        """
        # 기본 점수
        score = 0.0

        # 숫자 있으면 +0.3
        if numbers:
            score += 0.3

        # 결과 개수 (많을수록 +)
        score += min(len(result.content) / 10, 0.2)

        # 언어 매칭 (+0.1)
        if result.language == "ko" and "KR" in metric_request.context.get("region", ""):
            score += 0.1

        # 연도 매칭
        year_match = str(metric_request.context.get("year", "")) in result.query
        if year_match:
            score += 0.1

        # Source tier
        source_tier = "commercial"  # 검색 결과는 commercial

        return QueryResultQuality(
            score=min(score, 1.0),
            has_numbers=len(numbers) > 0,
            num_numbers=len(numbers),
            year_match=year_match,
            source_tier=source_tier,
            source_id=result.source_id,
            language=result.language,
            query=result.query
        )

    def _calculate_confidence(
        self,
        numbers: List[float],
        quality: QueryResultQuality
    ) -> float:
        """Confidence 계산"""

        base = 0.5  # 검색 결과 기본

        # 품질 점수 반영
        confidence = base + (quality.score * 0.3)

        # 숫자 일치도
        if len(numbers) >= 2:
            cv = statistics.stdev(numbers) / statistics.mean(numbers)
            variance_bonus = max(0, 0.15 * (1 - cv))
            confidence += variance_bonus

        return min(confidence, 0.85)

    def _extract_hints(
        self,
        result: RawSearchResult,
        numbers: List[float]
    ) -> List[Dict]:
        """Hints 추출"""
        hints = []

        for num in numbers:
            hints.append({
                "value": num,
                "query": result.query,
                "language": result.language,
                "confidence": 0.5
            })

        return hints
