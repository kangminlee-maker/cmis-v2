"""PromptProfileRegistry unit tests (Phase 2)."""

from __future__ import annotations

from pathlib import Path

from cmis_core.llm.prompt_profile_registry import PromptProfileRegistry


def test_prompt_profile_registry_digest_is_deterministic(tmp_path: Path) -> None:
    p = tmp_path / "prompt_profiles.yaml"
    p.write_text(
        """---
schema_version: 1
registry_version: "t"
profiles:
  default:
    description: "d"
    prefix: ""
  strict_json:
    description: "s"
    prefix: "JSON only"
""",
        encoding="utf-8",
    )

    r1 = PromptProfileRegistry(p)
    r1.compile()
    d1 = r1.get_ref().prompt_profile_digest

    r2 = PromptProfileRegistry(p)
    r2.compile()
    d2 = r2.get_ref().prompt_profile_digest

    assert d1 == d2


def test_prompt_profile_registry_unknown_profile_falls_back_to_default(tmp_path: Path) -> None:
    p = tmp_path / "prompt_profiles.yaml"
    p.write_text(
        """---
schema_version: 1
registry_version: "t"
profiles:
  default:
    description: "d"
    prefix: ""
""",
        encoding="utf-8",
    )

    r = PromptProfileRegistry(p)
    r.compile()

    prof = r.get_profile("does_not_exist")
    assert prof.profile_id == "default"


