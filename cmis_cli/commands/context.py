"""context 관련 명령어.

MVP:
- `cmis context verify PRJ-...-vN`
"""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Dict

from cmis_core.brownfield.verify import verify_prj


def cmd_context_verify(args) -> None:
    """PRJ-...-vN을 brownfield contracts 기준으로 verify합니다."""

    project_root = Path(args.project_root).resolve() if getattr(args, "project_root", None) else Path.cwd()
    prj_id = str(args.focal_actor_context_id)

    result = verify_prj(project_root=project_root, focal_actor_context_id=prj_id)
    payload: Dict[str, Any] = {"ok": result.ok, "errors": list(result.errors), "warnings": list(result.warnings)}

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not result.ok:
        raise SystemExit(1)
