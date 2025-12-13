"""Cursor CLI integration tests (v2).

subprocess로 실제 `python -m cmis_cli cursor ask`를 실행해
run folder(export view)가 생성되는지 확인합니다.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path


def test_cursor_ask_creates_run_folder(project_root: Path) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["CMIS_STORAGE_ROOT"] = tmpdir

        result = subprocess.run(
            [
                "python3",
                "-m",
                "cmis_cli",
                "cursor",
                "ask",
                "한국 어학 시장 분석",
                "--domain",
                "Adult_Language_Education_KR",
                "--region",
                "KR",
                "--policy",
                "exploration_friendly",
                "--max-iterations",
                "1",
                "--max-time-sec",
                "30",
            ],
            cwd=str(project_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, result.stderr

        m = re.search(r"run_dir:\s*(.+)", result.stdout)
        assert m, result.stdout

        run_dir = Path(m.group(1).strip())
        assert run_dir.exists()
        assert (run_dir / "results.md").exists()
        assert (run_dir / "request.yaml").exists()


