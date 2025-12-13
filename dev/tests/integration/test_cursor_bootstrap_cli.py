"""Cursor bootstrap CLI integration test (v2)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


def test_cursor_bootstrap_saves_manifest(project_root: Path) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["CMIS_STORAGE_ROOT"] = tmpdir

        result = subprocess.run(
            [
                "python3",
                "-m",
                "cmis_cli",
                "cursor",
                "bootstrap",
                "--no-env",
            ],
            cwd=str(project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, result.stderr
        assert "Bootstrap: OK" in result.stdout

        manifest_path = Path(tmpdir) / ".cmis" / "manifest.json"
        assert manifest_path.exists()

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("schema_version") == 1
        assert "workflows" in data


