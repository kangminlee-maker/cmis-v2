"""LLM Model Management Phase 1 tests.

목표:
- ModelRegistry/TaskSpecRegistry digest 결정성 보장
- PolicyEngine의 effective_policy.llm resolve + digest 캐싱 계약 보장
- ModelSelector의 결정적 선택(동일 입력 → 동일 decision_id) 보장
"""

from __future__ import annotations

from pathlib import Path

from cmis_core.llm.model_registry import ModelRegistry
from cmis_core.llm.model_selector import ModelSelector, SelectionRequest
from cmis_core.llm.task_spec_registry import TaskSpecRegistry
from cmis_core.policy_engine import PolicyEngine


def test_model_registry_digest_is_deterministic(tmp_path: Path) -> None:
    p = tmp_path / "model_registry.yaml"
    p.write_text(
        """---
schema_version: 1
registry_version: "t"
models:
  a:
    provider: "openai"
    display_name: "A"
    version: "v"
    capabilities:
      max_input_tokens: 10
      max_output_tokens: 10
      supports_json_mode: true
      supports_tool_calling: false
      multimodal: false
    cost_model:
      currency: "USD"
      input_per_1m_tokens: 0.1
      output_per_1m_tokens: 0.2
    performance_tier: "fast"
    availability:
      allowed_profiles: ["prod"]
""",
        encoding="utf-8",
    )

    r1 = ModelRegistry(p)
    r1.compile()
    d1 = r1.get_ref().registry_digest

    r2 = ModelRegistry(p)
    r2.compile()
    d2 = r2.get_ref().registry_digest

    assert d1 == d2


def test_task_specs_digest_is_deterministic(tmp_path: Path) -> None:
    p = tmp_path / "task_specs.yaml"
    p.write_text(
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

    s1 = TaskSpecRegistry(p)
    s1.compile()
    d1 = s1.get_ref().task_spec_digest

    s2 = TaskSpecRegistry(p)
    s2.compile()
    d2 = s2.get_ref().task_spec_digest

    assert d1 == d2


def test_policy_engine_resolves_effective_policy_llm_and_is_cached(tmp_path: Path) -> None:
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
      execution_profile: "prod"
      max_cost_per_call_usd: 0.01
      default_tier_preference: ["accurate", "balanced", "fast"]
      allow_models: ["gpt-4o-mini", "gpt-4"]
      forbidden_tasks: []
      task_overrides:
        evidence_number_extraction:
          preferred_models: ["gpt-4o-mini"]
          prompt_profile: "strict_json"
""",
        encoding="utf-8",
    )

    pe = PolicyEngine(project_root=tmp_path, policies_path=policies, llm_routing_path=llm_routing)

    e1 = pe.resolve_effective_policy("reporting_strict")
    e2 = pe.resolve_effective_policy("reporting_strict")

    assert e1.effective_policy_digest == e2.effective_policy_digest
    assert e1.llm.execution_profile == "prod"
    assert "gpt-4o-mini" in e1.llm.allow_models


def test_model_selector_is_deterministic_given_same_inputs(tmp_path: Path) -> None:
    # ---- registries ----
    mr_path = tmp_path / "model_registry.yaml"
    mr_path.write_text(
        """---
schema_version: 1
registry_version: "t"
models:
  gpt-4o-mini:
    provider: "openai"
    display_name: "GPT-4o mini"
    version: "x"
    capabilities:
      max_input_tokens: 20000
      max_output_tokens: 1000
      supports_json_mode: true
      supports_tool_calling: false
      multimodal: false
    cost_model:
      currency: "USD"
      input_per_1m_tokens: 0.1
      output_per_1m_tokens: 0.2
    performance_tier: "fast"
    availability:
      allowed_profiles: ["prod"]
  gpt-4:
    provider: "openai"
    display_name: "GPT-4"
    version: "x"
    capabilities:
      max_input_tokens: 20000
      max_output_tokens: 1000
      supports_json_mode: true
      supports_tool_calling: false
      multimodal: false
    cost_model:
      currency: "USD"
      input_per_1m_tokens: 10.0
      output_per_1m_tokens: 20.0
    performance_tier: "accurate"
    availability:
      allowed_profiles: ["prod"]
""",
        encoding="utf-8",
    )

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

    mr = ModelRegistry(mr_path)
    mr.compile()
    ts = TaskSpecRegistry(ts_path)
    ts.compile()

    # ---- effective policy ----
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
      execution_profile: "prod"
      max_cost_per_call_usd: 0.5
      default_tier_preference: ["accurate", "fast"]
      allow_models: ["gpt-4o-mini", "gpt-4"]
      task_overrides:
        evidence_number_extraction:
          preferred_models: ["gpt-4o-mini", "gpt-4"]
          prompt_profile: "strict_json"
""",
        encoding="utf-8",
    )

    pe = PolicyEngine(project_root=tmp_path, policies_path=policies, llm_routing_path=llm_routing)
    eff = pe.resolve_effective_policy("reporting_strict")

    selector = ModelSelector(model_registry=mr, task_specs=ts)

    req = SelectionRequest(
        task_type="evidence_number_extraction",
        policy_ref="reporting_strict",
        effective_policy_digest=eff.effective_policy_digest,
        call_intent="extract",
        quality_target="medium",
        budget_remaining_usd=10.0,
        attempt_index=0,
        failure_codes=[],
    )

    d1 = selector.select(request=req, effective_policy=eff)
    d2 = selector.select(request=req, effective_policy=eff)

    assert d1.decision_id == d2.decision_id
    assert d1.model_id == "gpt-4o-mini"
    assert d1.prompt_profile == "strict_json"


def test_model_selector_applies_escalation_ladder_on_gate_failure(tmp_path: Path) -> None:
    # ---- registries ----
    mr_path = tmp_path / "model_registry.yaml"
    mr_path.write_text(
        """---
schema_version: 1
registry_version: "t"
models:
  gpt-4o-mini:
    provider: "openai"
    display_name: "GPT-4o mini"
    version: "x"
    capabilities:
      max_input_tokens: 20000
      max_output_tokens: 1000
      supports_json_mode: true
      supports_tool_calling: false
      multimodal: false
    cost_model:
      currency: "USD"
      input_per_1m_tokens: 0.1
      output_per_1m_tokens: 0.2
    performance_tier: "fast"
    availability:
      allowed_profiles: ["prod"]
  gpt-4:
    provider: "openai"
    display_name: "GPT-4"
    version: "x"
    capabilities:
      max_input_tokens: 20000
      max_output_tokens: 1000
      supports_json_mode: true
      supports_tool_calling: false
      multimodal: false
    cost_model:
      currency: "USD"
      input_per_1m_tokens: 10.0
      output_per_1m_tokens: 20.0
    performance_tier: "accurate"
    availability:
      allowed_profiles: ["prod"]
""",
        encoding="utf-8",
    )

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

    mr = ModelRegistry(mr_path)
    mr.compile()
    ts = TaskSpecRegistry(ts_path)
    ts.compile()
    selector = ModelSelector(model_registry=mr, task_specs=ts)

    # ---- effective policy ----
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
      execution_profile: "prod"
      max_cost_per_call_usd: 999
      default_tier_preference: ["fast", "accurate"]
      allow_models: ["gpt-4o-mini", "gpt-4"]
      task_overrides:
        evidence_number_extraction:
          preferred_models: ["gpt-4o-mini"]
          prompt_profile: "default"
          escalation_ladder:
            - when: "gate_failed:json_parseable"
              next: { model: "gpt-4", prompt_profile: "strict_json" }
""",
        encoding="utf-8",
    )

    pe = PolicyEngine(project_root=tmp_path, policies_path=policies, llm_routing_path=llm_routing)
    eff = pe.resolve_effective_policy("reporting_strict")

    req = SelectionRequest(
        task_type="evidence_number_extraction",
        policy_ref="reporting_strict",
        effective_policy_digest=eff.effective_policy_digest,
        call_intent="extract",
        quality_target="medium",
        budget_remaining_usd=999,
        attempt_index=1,
        failure_codes=["gate_failed:json_parseable"],
    )

    d = selector.select(request=req, effective_policy=eff)
    assert d.model_id == "gpt-4"
    assert d.prompt_profile == "strict_json"
    assert "escalated_by_policy" in d.rationale_codes


