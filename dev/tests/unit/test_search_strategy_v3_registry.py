"""Search Strategy v3 registry unit tests (SSV3-01).

원칙:
- 외부 네트워크 호출 없이 재현 가능해야 합니다.
- digest는 입력(dict key order)에 대해 결정적으로 동일해야 합니다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cmis_core.search_v3.registry import StrategyRegistryError, StrategyRegistryV3


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_registry_digest_stable_for_provider_key_order(tmp_path: Path) -> None:
    # same content, different mapping order
    a = _write(
        tmp_path,
        "a.yaml",
        """---
registry_version: 3
phases_allowed: [generic_web]
providers:
  GenericWebSearch:
    adapter: google_cse
    api_key_ref: GOOGLE_API_KEY
  DummyProvider:
    adapter: serpapi
    api_key_ref: SERPAPI_API_KEY
metrics:
  MET-TAM:
    decision_balanced:
      phases:
        - phase_id: generic_web
          providers: [GenericWebSearch]
          query_templates: ["{domain} {region} market size {year}"]
""",
    )
    b = _write(
        tmp_path,
        "b.yaml",
        """---
registry_version: 3
phases_allowed: [generic_web]
providers:
  DummyProvider:
    adapter: serpapi
    api_key_ref: SERPAPI_API_KEY
  GenericWebSearch:
    adapter: google_cse
    api_key_ref: GOOGLE_API_KEY
metrics:
  MET-TAM:
    decision_balanced:
      phases:
        - phase_id: generic_web
          providers: [GenericWebSearch]
          query_templates: ["{domain} {region} market size {year}"]
""",
    )

    reg_a = StrategyRegistryV3(a)
    reg_b = StrategyRegistryV3(b)

    digest_a = reg_a.get_strategy_ref().registry_digest
    digest_b = reg_b.get_strategy_ref().registry_digest

    assert digest_a.startswith("sha256:")
    assert digest_a == digest_b


def test_registry_rejects_unknown_provider_reference(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "bad_provider.yaml",
        """---
registry_version: 3
phases_allowed: [generic_web]
providers:
  GenericWebSearch:
    adapter: google_cse
    api_key_ref: GOOGLE_API_KEY
metrics:
  MET-TAM:
    decision_balanced:
      phases:
        - phase_id: generic_web
          providers: [NoSuchProvider]
          query_templates: ["{domain} {region} market size {year}"]
""",
    )

    reg = StrategyRegistryV3(p)
    with pytest.raises(StrategyRegistryError):
        reg.compile()


def test_registry_rejects_unknown_phase_id(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "bad_phase.yaml",
        """---
registry_version: 3
phases_allowed: [generic_web]
providers:
  GenericWebSearch:
    adapter: google_cse
    api_key_ref: GOOGLE_API_KEY
metrics:
  MET-TAM:
    decision_balanced:
      phases:
        - phase_id: weird_phase
          providers: [GenericWebSearch]
          query_templates: ["{domain} {region} market size {year}"]
""",
    )

    reg = StrategyRegistryV3(p)
    with pytest.raises(StrategyRegistryError):
        reg.compile()


def test_registry_resolve_metric_plan_template(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "ok.yaml",
        """---
registry_version: 3
phases_allowed: [generic_web]
providers:
  GenericWebSearch:
    adapter: google_cse
    api_key_ref: GOOGLE_API_KEY
metrics:
  MET-TAM:
    decision_balanced:
      phases:
        - phase_id: generic_web
          providers: [GenericWebSearch]
          query_templates: ["{domain} {region} market size {year}"]
""",
    )

    reg = StrategyRegistryV3(p)
    tpl = reg.resolve_metric_plan_template("MET-TAM", "decision_balanced")
    assert "phases" in tpl
    assert len(tpl["phases"]) == 1


def test_repo_default_registry_file_compiles() -> None:
    reg = StrategyRegistryV3("config/search_strategy_registry_v3.yaml")
    ref = reg.get_strategy_ref()
    assert ref.registry_version == 3
    assert ref.registry_digest.startswith("sha256:")
    provider = reg.get_provider_config("GenericWebSearch")
    assert provider.provider_id == "GenericWebSearch"
    assert provider.provider_config_digest.startswith("sha256:")
