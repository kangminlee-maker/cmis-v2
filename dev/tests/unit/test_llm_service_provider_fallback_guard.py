"""LLMService 운영 안전 테스트: 선택된 provider에 대해 침묵 fallback 금지.

배경:
- ModelSelector가 정책/레지스트리 기준으로 'openai'를 선택했는데,
  LLMService가 provider 미설정 상태에서 __default__(mock 등)로 조용히 떨어지면
  prod에서 'mock 금지' 같은 운영 규칙이 무력화될 수 있습니다.

수용기준:
- policy_ref로 ModelSelector 경로가 활성화되고 decision이 존재하는 경우,
  선택된 provider가 없으면 ProviderNotAvailableError로 실패해야 합니다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cmis_core.config import CMISConfig
from cmis_core.llm.model_registry import ModelRegistry
from cmis_core.llm.model_selector import ModelSelector
from cmis_core.llm.service import create_llm_service
from cmis_core.llm.task_spec_registry import TaskSpecRegistry
from cmis_core.llm.types import CMISTaskType, ProviderNotAvailableError
from cmis_core.policy_engine import PolicyEngine


def test_llm_service_raises_if_selected_provider_is_missing(tmp_path: Path) -> None:
    # ---- minimal PolicyEngine inputs ----
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
      max_cost_per_call_usd: 1.0
      default_tier_preference: ["fast"]
      allow_models: ["gpt-4o-mini"]
      forbidden_tasks: []
      task_overrides:
        evidence_number_extraction:
          preferred_models: ["gpt-4o-mini"]
          prompt_profile: "strict_json"
""",
        encoding="utf-8",
    )

    pe = PolicyEngine(project_root=tmp_path, policies_path=policies, llm_routing_path=llm_routing)

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
      max_input_tokens: 16384
      max_output_tokens: 4096
      supports_json_mode: true
      supports_tool_calling: true
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

    # ---- service in mock mode (no openai provider) ----
    service = create_llm_service(config=CMISConfig(), mode="mock")
    service.policy_engine = pe
    service.model_registry = mr
    service.task_specs = ts
    service.model_selector = selector
    # 환경에 따라 CMISConfig에서 openai provider가 자동 등록될 수 있으므로,
    # 이 테스트에서는 "선택된 provider가 실제로 없을 때"만을 강제합니다.
    service.registry._providers.pop("openai", None)

    with pytest.raises(ProviderNotAvailableError):
        service.call_structured(
            CMISTaskType.EVIDENCE_NUMBER_EXTRACTION,
            "json test",
            policy_ref="reporting_strict",
        )


