"""Engine data persistence — saves/loads engine data to project directory."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECTS_DIR = Path(__file__).parent.parent / "projects"


def save_engine_data(project_id: str, engine: str, key: str, data: dict) -> None:
    """Save engine data to projects/{project_id}/engine_data/{engine}/{key}.json"""
    dir_path = PROJECTS_DIR / project_id / "engine_data" / engine
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{key}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def load_engine_data(project_id: str, engine: str, key: str) -> dict[str, Any] | None:
    """Load engine data. Returns None if not found."""
    path = PROJECTS_DIR / project_id / "engine_data" / engine / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_engine_keys(project_id: str, engine: str) -> list[str]:
    """List all saved keys for an engine in a project."""
    dir_path = PROJECTS_DIR / project_id / "engine_data" / engine
    if not dir_path.exists():
        return []
    return [f.stem for f in dir_path.glob("*.json")]
