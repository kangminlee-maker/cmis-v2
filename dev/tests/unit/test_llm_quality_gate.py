"""LLM QualityGateEngine unit tests (Phase 2).

주의:
- 외부 호출 없이 결정적으로 동작해야 합니다.
"""

from __future__ import annotations

from cmis_core.llm.quality_gate import QualityGateEngine
from cmis_core.llm.task_spec_registry import OutputContract, QualityGateSpec, RequiredCapabilities, TaskSpec


def test_quality_gate_json_parseable_passes_for_dict() -> None:
    spec = TaskSpec(
        task_type="evidence_number_extraction",
        required_capabilities=RequiredCapabilities(supports_json_mode=True),
        output_contract=OutputContract(format="json"),
        quality_gates=[QualityGateSpec(gate_id="json_parseable")],
    )
    engine = QualityGateEngine()
    r = engine.evaluate(task_spec=spec, output={"ok": True})
    assert r.passed is True
    assert r.failure_codes == []


def test_quality_gate_json_parseable_fails_for_parse_error_payload() -> None:
    spec = TaskSpec(
        task_type="evidence_number_extraction",
        required_capabilities=RequiredCapabilities(supports_json_mode=True),
        output_contract=OutputContract(format="json"),
        quality_gates=[QualityGateSpec(gate_id="json_parseable")],
    )
    engine = QualityGateEngine()
    r = engine.evaluate(task_spec=spec, output={"raw": "NOT_JSON", "error": "json_parse_failed"})
    assert r.passed is False
    assert "gate_failed:json_parseable" in r.failure_codes


def test_quality_gate_has_claims_minimal() -> None:
    spec = TaskSpec(
        task_type="pattern_recognition",
        required_capabilities=RequiredCapabilities(),
        output_contract=OutputContract(format="structured_text"),
        quality_gates=[QualityGateSpec(gate_id="has_claims")],
    )
    engine = QualityGateEngine()
    r = engine.evaluate(task_spec=spec, output="- claim a\n- claim b\n")
    assert r.passed is True

    r2 = engine.evaluate(task_spec=spec, output="too short")
    assert r2.passed is False
    assert "gate_failed:has_claims" in r2.failure_codes


def test_quality_gate_has_strategies_minimal() -> None:
    spec = TaskSpec(
        task_type="strategy_generation",
        required_capabilities=RequiredCapabilities(),
        output_contract=OutputContract(format="structured_text"),
        quality_gates=[QualityGateSpec(gate_id="has_strategies")],
    )
    engine = QualityGateEngine()
    ok = "전략:\n- A\n- B\n"
    r = engine.evaluate(task_spec=spec, output=ok)
    assert r.passed is True

    bad = "전략:\n- only one\n"
    r2 = engine.evaluate(task_spec=spec, output=bad)
    assert r2.passed is False
    assert "gate_failed:has_strategies" in r2.failure_codes


def test_quality_gate_unknown_gate_is_non_blocking_in_phase2_minimal() -> None:
    spec = TaskSpec(
        task_type="x",
        required_capabilities=RequiredCapabilities(),
        output_contract=OutputContract(format="text"),
        quality_gates=[QualityGateSpec(gate_id="unknown_gate")],
    )
    engine = QualityGateEngine()
    r = engine.evaluate(task_spec=spec, output="anything")
    assert r.passed is True


