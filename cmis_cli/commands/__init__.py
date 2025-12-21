"""CMIS CLI Commands

워크플로우 명령어 모듈

2025-12-11: Workflow CLI Phase 1/2
"""

from .structure_analysis import cmd_structure_analysis
from .opportunity_discovery import cmd_opportunity_discovery
from .workflow_run import cmd_workflow_run
from .compare_contexts import cmd_compare_contexts
from .batch_analysis import cmd_batch_analysis
from .report_generate import cmd_report_generate
from .cache_manage import cmd_cache_manage
from .config_validate import cmd_config_validate
from .cursor import (
    cmd_cursor_init,
    cmd_cursor_doctor,
    cmd_cursor_manifest,
    cmd_cursor_bootstrap,
    cmd_cursor_ask,
)
from .run import (
    cmd_run_explain,
    cmd_run_open,
)
from .eval_run import cmd_eval_run
from .db_manage import cmd_db_manage
from .context import cmd_context_verify
from .brownfield import (
    cmd_brownfield_import,
    cmd_brownfield_preview,
    cmd_brownfield_validate,
    cmd_brownfield_commit,
    cmd_brownfield_reconcile,
)

__all__ = [
    "cmd_structure_analysis",
    "cmd_opportunity_discovery",
    "cmd_workflow_run",
    "cmd_compare_contexts",
    "cmd_batch_analysis",
    "cmd_report_generate",
    "cmd_cache_manage",
    "cmd_config_validate",
    "cmd_cursor_init",
    "cmd_cursor_doctor",
    "cmd_cursor_manifest",
    "cmd_cursor_bootstrap",
    "cmd_cursor_ask",
    "cmd_run_explain",
    "cmd_run_open",
    "cmd_eval_run",
    "cmd_db_manage",
    "cmd_context_verify",
    "cmd_brownfield_import",
    "cmd_brownfield_preview",
    "cmd_brownfield_validate",
    "cmd_brownfield_commit",
    "cmd_brownfield_reconcile",
]



