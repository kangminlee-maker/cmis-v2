#!/usr/bin/env python3
"""Validate pattern YAML files against the ontology-derived validators.

Usage:
    python scripts/validate_patterns.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

# Ensure the project root is on sys.path so that cmis_v2 can be imported.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cmis_v2.generated.validators import validate_pattern_spec  # noqa: E402

PATTERNS_DIR = ROOT / "libraries" / "patterns"


def main() -> None:
    pattern_files = sorted(PATTERNS_DIR.glob("*.yaml"))
    if not pattern_files:
        print(f"No pattern files found in {PATTERNS_DIR}")
        sys.exit(1)

    total_errors: list[str] = []
    checked = 0

    for pf in pattern_files:
        with open(pf, encoding="utf-8") as f:
            raw: dict[str, Any] = yaml.safe_load(f)

        spec: dict[str, Any] | None = raw.get("pattern")
        if spec is None:
            total_errors.append(f"[{pf.name}] Missing top-level 'pattern' key")
            continue

        errors = validate_pattern_spec(spec)
        checked += 1
        if errors:
            for err in errors:
                total_errors.append(f"[{pf.name}] {err}")
        else:
            print(f"  OK: {pf.name}")

    print(f"\nChecked {checked} pattern(s), {len(total_errors)} error(s).")

    if total_errors:
        print("\nErrors:")
        for err in total_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("All patterns valid.")


if __name__ == "__main__":
    main()
