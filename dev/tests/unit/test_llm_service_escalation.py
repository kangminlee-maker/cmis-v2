"""LLMService Phase 2: quality gate + escalation integration test.

시나리오:
- 1차 시도: prompt_profile=default → Mock이 NOT_JSON 반환 → json_parseable gate 실패
- 2차 시도: escalation_ladder 적용 → prompt_profile=strict_json → Mock이 JSON 반환 → 성공
"""

from __future__ import annotations

from pathlib import Path

from cmis_core.config import CMISConfig
from cmis_core.llm.model_registry import ModelRegistry
from cmis_core.llm.model_selector import ModelSelector
from cmis_core.llm.service import create_llm_service
from cmis_core.llm.task_spec_registry import TaskSpecRegistry
from cmis_core.llm.types import CMISTaskType
from cmis_core.policy_engine import PolicyEngine
from cmis_core.stores.run_store import RunStore


def test_llm_service_escalates_on_json_parseable_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_STORAGE_ROOT", str(tmp_path))

    policies = tmp_path / "policies.yaml"
    policies.write_text(
        """---
policy_pack:
  schema_version: 2
  routing:
    by_usage: {}
    by_role: {}
    fallback: reporting_strict
  profiles:
    evidence_profiles:
      e1:
        min_sources: 0
        require_official_sources: false
        allowed_source_tiers: ["web"]
        max_age_days: 999999
        allow_web: true
    value_profiles:
      v1:
        min_literal_ratio: 0.0
        max_spread_ratio: 1.0
        min_confidence: 0.0
        metric_specific: {}
    prior_profiles:
      p1:
        allow_prior: true
        max_prior_ratio: 1.0
        allowed_prior_types: []
    convergence_profiles:
      c1:
        default_threshold: 0.3
        default_methods_required: 1
        metric_specific: {}
    orchestration_profiles:
      o1:
        stall_threshold: 2
        allow_partial_replan: true
        require_human_approval: false
  modes:
    reporting_strict:
      description: "test"
      profiles:
        evidence: e1
        value: v1
        prior: p1
        convergence: c1
        orchestration: o1
      gates: []
      use_cases: []
""",
        encoding="utf-8",
    )

    llm_routing = tmp_path / "llm_routing.yaml"
    llm_routing.write_text(
        """---
schema_version: 1
policies:
  reporting_strict:
    llm:
      execution_profile: "test"
      max_cost_per_call_usd: 1.0
      default_tier_preference: ["test"]
      allow_models: ["mock"]
      task_overrides:
        evidence_number_extraction:
          preferred_models: ["mock"]
          prompt_profile: "default"
          escalation_ladder:
            - when: "gate_failed:json_parseable"
              next: { model: "mock", prompt_profile: "strict_json" }
""",
        encoding="utf-8",
    )
    pe = PolicyEngine(project_root=tmp_path, policies_path=policies, llm_routing_path=llm_routing)

    mr_path = tmp_path / "model_registry.yaml"
    mr_path.write_text(
        """---
schema_version: 1
registry_version: "t"
models:
  mock:
    provider: "mock"
    display_name: "Mock"
    version: "1"
    capabilities:
      max_input_tokens: 1024
      max_output_tokens: 1024
      supports_json_mode: true
      supports_tool_calling: false
      multimodal: false
    cost_model:
      currency: "USD"
      input_per_1m_tokens: 0.0
      output_per_1m_tokens: 0.0
    performance_tier: "test"
    availability:
      allowed_profiles: ["test"]
""",
        encoding="utf-8",
    )
    mr = ModelRegistry(mr_path)
    mr.compile()

    ts_path = tmp_path / "task_specs.yaml"
    ts_path.write_text(
        """---
schema_version: 1
registry_version: "t"
tasks:
  evidence_number_extraction:
    required_capabilities:
      supports_json_mode: true
    output_contract:
      format: "json"
    quality_gates:
      - gate_id: "json_parseable"
  _default:
    required_capabilities: {}
    output_contract:
      format: "text"
    quality_gates: []
""",
        encoding="utf-8",
    )
    ts = TaskSpecRegistry(ts_path)
    ts.compile()

    selector = ModelSelector(model_registry=mr, task_specs=ts)
    rs = RunStore(project_root=tmp_path)

    service = create_llm_service(config=CMISConfig(), mode="mock")
    service.policy_engine = pe
    service.model_registry = mr
    service.task_specs = ts
    service.model_selector = selector
    service.run_store = rs

    mock = service.registry.get_provider("mock")
    assert mock is not None
    mock.default_response = "NOT_JSON"
    # strict_json 프롬프트일 때만 성공 JSON 반환
    mock.responses["중요: 반드시 JSON만 출력"] = '{"ok": true}'

    run_id = "RUN-TEST-ESC-1"
    out = service.call_structured(
        CMISTaskType.EVIDENCE_NUMBER_EXTRACTION,
        "json test",
        context={"company_name": "ACME", "year": 2024},
        policy_ref="reporting_strict",
        run_id=run_id,
        max_attempts=2,
    )
    assert out.get("ok") is True

    decisions = rs.list_decisions(run_id)
    sel = [d for d in decisions if d.get("type") == "llm_selection_decision"]
    gates = [d for d in decisions if d.get("type") == "llm_quality_gate_result"]
    assert len(sel) >= 2, "should have at least 2 selection decisions (initial + escalated)"
    assert len(gates) >= 2, "should have at least 2 gate results (initial fail + success)"

    rs.close()


