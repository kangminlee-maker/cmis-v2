"""LLM QualityGate engine (Phase 2).

목적(비개발자 설명):
- LLM의 출력이 "원하는 형태/품질"을 만족하는지 자동으로 점검합니다.
- 예: JSON 추출 작업이면 "JSON 파싱 가능"해야 하고, 전략 생성이면 "전략 목록"이 포함돼야 합니다.
- 점검 결과는 failure_code로 표준화되어, 이후 bounded escalation(재시도/모델 변경) 판단에 사용됩니다.

Phase 2 최소 범위:
- `task_specs_minimal.yaml`에서 사용하는 핵심 게이트만 우선 지원합니다.
  - json_parseable
  - has_claims
  - has_strategies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cmis_core.llm.task_spec_registry import TaskSpec


@dataclass(frozen=True)
class GateResult:
    """단일 게이트 검사 결과."""

    gate_id: str
    passed: bool
    failure_code: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": str(self.gate_id),
            "passed": bool(self.passed),
            "failure_code": self.failure_code,
            "message": str(self.message),
            "details": dict(self.details or {}),
        }


@dataclass(frozen=True)
class QualityGateReport:
    """Task 출력에 대한 품질 게이트 결과."""

    task_type: str
    passed: bool
    results: List[GateResult] = field(default_factory=list)
    failure_codes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": str(self.task_type),
            "passed": bool(self.passed),
            "results": [r.to_dict() for r in (self.results or [])],
            "failure_codes": list(self.failure_codes or []),
        }


class QualityGateEngine:
    """TaskSpec 기반 품질 게이트 실행기."""

    def evaluate(self, *, task_spec: TaskSpec, output: Any) -> QualityGateReport:
        """task_spec.quality_gates를 순서대로 평가합니다."""

        task_type = str(task_spec.task_type or "")
        results: List[GateResult] = []
        failure_codes: List[str] = []

        for g in (task_spec.quality_gates or []):
            gate_id = str(getattr(g, "gate_id", "") or "").strip()
            if not gate_id:
                continue

            if gate_id == "json_parseable":
                r = _gate_json_parseable(output)
            elif gate_id == "has_claims":
                r = _gate_has_claims(output)
            elif gate_id == "has_strategies":
                r = _gate_has_strategies(output)
            else:
                # Phase 2 minimal: unknown gate는 실패로 처리하지 않고 "미지원"으로만 기록합니다.
                r = GateResult(gate_id=gate_id, passed=True, message="gate_not_implemented_in_phase2_minimal")

            results.append(r)
            if not r.passed and r.failure_code:
                failure_codes.append(str(r.failure_code))

        passed = all(r.passed for r in results) if results else True
        return QualityGateReport(task_type=task_type, passed=bool(passed), results=results, failure_codes=failure_codes)


def _gate_json_parseable(output: Any) -> GateResult:
    """JSON 파싱 가능 여부.

    기대:
    - output이 dict이고, 파싱 실패를 의미하는 키/필드가 없어야 합니다.
    """

    gate_id = "json_parseable"

    if not isinstance(output, dict):
        return GateResult(
            gate_id=gate_id,
            passed=False,
            failure_code="gate_failed:json_parseable",
            message="output_is_not_a_dict",
        )

    # BaseLLM.call_structured()의 fallback 규약:
    # - {"raw": "...", "error": "json_parse_failed"}
    err = output.get("error")
    if err:
        code = str(err)
        if code == "json_parse_failed":
            return GateResult(
                gate_id=gate_id,
                passed=False,
                failure_code="gate_failed:json_parseable",
                message="json_parse_failed",
                details={"error": code},
            )
        return GateResult(
            gate_id=gate_id,
            passed=False,
            failure_code="gate_failed:json_parseable",
            message="json_parse_error",
            details={"error": code},
        )

    return GateResult(gate_id=gate_id, passed=True)


def _gate_has_claims(output: Any) -> GateResult:
    """'주장/핵심 포인트'가 포함된 텍스트인지(Phase 2 minimal heuristic)."""

    gate_id = "has_claims"

    if not isinstance(output, str):
        return GateResult(
            gate_id=gate_id,
            passed=False,
            failure_code="gate_failed:has_claims",
            message="output_is_not_text",
        )

    s = output.strip()
    # 매우 단순한 휴리스틱: 목록형 항목(최소 1개)이 있으면 claims가 있다고 간주
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    bulletish = [ln for ln in lines if ln.startswith(("-", "•")) or ln[:2].isdigit()]
    if len(bulletish) < 1:
        return GateResult(
            gate_id=gate_id,
            passed=False,
            failure_code="gate_failed:has_claims",
            message="no_claim_like_items",
        )

    return GateResult(gate_id=gate_id, passed=True)


def _gate_has_strategies(output: Any) -> GateResult:
    """'전략 목록'이 포함된 텍스트인지(Phase 2 minimal heuristic)."""

    gate_id = "has_strategies"

    if not isinstance(output, str):
        return GateResult(
            gate_id=gate_id,
            passed=False,
            failure_code="gate_failed:has_strategies",
            message="output_is_not_text",
        )

    s = output.strip()
    # 간단 기준: 목록형 항목이 2개 이상 존재
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    bulletish = [ln for ln in lines if ln.startswith(("-", "•")) or ln[:2].isdigit()]
    if len(bulletish) < 2:
        return GateResult(
            gate_id=gate_id,
            passed=False,
            failure_code="gate_failed:has_strategies",
            message="insufficient_strategy_items",
            details={"bulletish_count": len(bulletish)},
        )

    return GateResult(gate_id=gate_id, passed=True)


