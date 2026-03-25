"""CMIS v2 Ontology Migration — Version compatibility and migration management.

Manages compatibility between ontology versions and provides migration
paths when ontology.yaml is updated with breaking changes.

This module is designed to be called by RLM's LM as a custom_tool.
All inputs/outputs are plain dicts (JSON-serializable).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_ONTOLOGY_PATH = _ROOT / "schemas" / "ontology.yaml"
_MIGRATIONS_DIR = _ROOT / "schemas" / "migrations"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_current_ontology_version() -> str:
    """Read current version from schemas/ontology.yaml.

    Returns:
        Version string, e.g. "1.0.0".
    """
    try:
        with open(_ONTOLOGY_PATH, encoding="utf-8") as f:
            raw: dict[str, Any] = yaml.safe_load(f)
        return raw["ontology"]["version"]
    except Exception as e:
        return f"error: {e}"


def check_compatibility(project_id: str) -> dict[str, Any]:
    """Check if a project's ontology version is compatible with current.

    Reads project manifest's ontology_version and compares with
    current ontology.yaml version.

    Args:
        project_id: The project ID to check.

    Returns:
        Dict with compatible (bool), project_version, current_version,
        and breaking_changes list.
    """
    current_version = get_current_ontology_version()
    if current_version.startswith("error:"):
        return {"error": f"Cannot read ontology version: {current_version}"}

    # Try to load project manifest
    try:
        from cmis_v2.project import load_project

        manifest = load_project(project_id)
        if "error" in manifest:
            return {"error": f"Cannot load project: {manifest['error']}"}
    except Exception as e:
        return {"error": f"Cannot load project: {e}"}

    project_version = manifest.get("ontology_version", current_version)

    # Simple version comparison
    compatible = project_version == current_version
    breaking_changes: list[str] = []

    if not compatible:
        # Check if a migration map exists
        migration_file = (
            _MIGRATIONS_DIR / f"{project_version}_to_{current_version}.yaml"
        )
        if migration_file.exists():
            try:
                with open(migration_file, encoding="utf-8") as f:
                    migration = yaml.safe_load(f)
                migration_info = migration.get("migration", migration)
                renames = migration_info.get("renames", {})
                removals = migration_info.get("removals", [])
                for old_id, new_id in renames.items():
                    breaking_changes.append(f"{old_id} renamed to {new_id}")
                for removed_id in removals:
                    breaking_changes.append(f"{removed_id} removed")
            except Exception:
                breaking_changes.append(
                    f"Migration map exists but could not be read: {migration_file}"
                )
        else:
            breaking_changes.append(
                f"No migration map found for {project_version} -> {current_version}"
            )

    return {
        "compatible": compatible,
        "project_version": project_version,
        "current_version": current_version,
        "breaking_changes": breaking_changes,
    }


def create_migration_map(
    from_version: str,
    to_version: str,
    renames: dict | None = None,
    removals: list | None = None,
) -> dict[str, Any]:
    """Create a migration map for ontology version changes.

    Args:
        from_version: Source version (e.g. "1.0.0").
        to_version: Target version (e.g. "1.1.0").
        renames: Mapping of old metric/trait IDs to new IDs.
        removals: List of removed metric/trait IDs.

    Returns:
        Dict with path to saved migration file and migration details.
    """
    if not from_version or not to_version:
        return {"error": "Both from_version and to_version are required"}

    if from_version == to_version:
        return {"error": "from_version and to_version must be different"}

    _MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

    migration_data: dict[str, Any] = {
        "migration": {
            "from_version": from_version,
            "to_version": to_version,
            "created_at": datetime.now().isoformat(),
            "renames": renames or {},
            "removals": removals or [],
        }
    }

    filename = f"{from_version}_to_{to_version}.yaml"
    filepath = _MIGRATIONS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(migration_data, f, default_flow_style=False, allow_unicode=True)

    return {
        "path": str(filepath),
        "from_version": from_version,
        "to_version": to_version,
        "renames": renames or {},
        "removals": removals or [],
    }


def migrate_project(
    project_id: str,
    migration_map_path: str = "",
) -> dict[str, Any]:
    """Apply migration to a project's data.

    Reads the migration map and updates project events/manifest
    to use new ontology terms.

    Args:
        project_id: The project to migrate.
        migration_map_path: Path to migration YAML. If empty, auto-detect
            based on project version and current ontology version.

    Returns:
        Dict with migration result details.
    """
    current_version = get_current_ontology_version()

    # Load project
    try:
        from cmis_v2.project import load_project

        manifest = load_project(project_id)
        if "error" in manifest:
            return {"error": f"Cannot load project: {manifest['error']}"}
    except Exception as e:
        return {"error": f"Cannot load project: {e}"}

    project_version = manifest.get("ontology_version", current_version)

    if project_version == current_version:
        return {"info": "Project already at current ontology version", "version": current_version}

    # Resolve migration map
    if not migration_map_path:
        migration_map_path = str(
            _MIGRATIONS_DIR / f"{project_version}_to_{current_version}.yaml"
        )

    migration_path = Path(migration_map_path)
    if not migration_path.exists():
        return {
            "error": (
                f"Migration map not found: {migration_map_path}. "
                f"Create one with create_migration_map()."
            )
        }

    try:
        with open(migration_path, encoding="utf-8") as f:
            migration = yaml.safe_load(f)
    except Exception as e:
        return {"error": f"Cannot read migration map: {e}"}

    migration_info = migration.get("migration", {})
    renames = migration_info.get("renames", {})
    removals = migration_info.get("removals", [])

    changes_applied: list[str] = []

    # 1. Update manifest ontology_version
    manifest["ontology_version"] = current_version
    changes_applied.append(f"Updated ontology_version from {project_version} to {current_version}")

    from cmis_v2.project import _write_manifest
    _write_manifest(project_id, manifest)

    # 2. Migrate engine_store data (rename/remove metric/trait IDs)
    from cmis_v2.config import PROJECTS_DIR
    from cmis_v2.engine_store import list_engine_keys, load_engine_data, save_engine_data

    # Dynamic engine discovery: scan engine_data subdirectories instead of hardcoded list
    engine_data_dir = PROJECTS_DIR / project_id / "engine_data"

    if engine_data_dir.exists():
        engines = sorted(d.name for d in engine_data_dir.iterdir() if d.is_dir())
        for engine_name in engines:
            keys = list_engine_keys(project_id, engine_name)
            for key in keys:
                data = load_engine_data(project_id, engine_name, key)
                if data is None:
                    continue
                original = json.dumps(data, ensure_ascii=False)
                updated = original
                # Apply renames as string replacement on serialized JSON
                for old_id, new_id in renames.items():
                    updated = updated.replace(f'"{old_id}"', f'"{new_id}"')
                # Apply removals: remove dict entries with removed keys
                if updated != original or removals:
                    new_data = json.loads(updated)
                    if removals:
                        new_data = _remove_keys_recursive(new_data, set(removals))
                    save_engine_data(project_id, engine_name, key, new_data)
                    if updated != original:
                        changes_applied.append(f"{engine_name}/{key}: renamed IDs applied")
                    if removals:
                        changes_applied.append(f"{engine_name}/{key}: removals checked")

    return {
        "project_id": project_id,
        "from_version": project_version,
        "to_version": current_version,
        "changes_applied": changes_applied,
        "renames": renames,
        "removals": removals,
    }


def _remove_keys_recursive(obj: Any, removal_ids: set[str]) -> Any:
    """Recursively remove dict entries whose values match removal IDs."""
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(v, str) and v in removal_ids:
                continue
            if k in removal_ids:
                continue
            cleaned[k] = _remove_keys_recursive(v, removal_ids)
        return cleaned
    elif isinstance(obj, list):
        return [
            _remove_keys_recursive(item, removal_ids)
            for item in obj
            if not (isinstance(item, str) and item in removal_ids)
        ]
    return obj
