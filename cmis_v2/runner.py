"""CMIS v2 runner — user entry point for analysis sessions.

Provides CLI commands to start new analyses, resume from user gates,
and manage execution parameters.  Bridges the CMIS v2 project lifecycle
with the RLM completion engine.

Usage examples::

    # New analysis
    python -m cmis_v2.runner "한국 전기차 충전 인프라 시장 분석"

    # Check project status
    python -m cmis_v2.runner --status PROJECT_ID

    # Resume after user gate
    python -m cmis_v2.runner --resume PROJECT_ID --approve
    python -m cmis_v2.runner --resume PROJECT_ID --revise "시장 범위를 B2C로 한정"
    python -m cmis_v2.runner --resume PROJECT_ID --select "PAT-subscription_model"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cmis_v2.config import PROJECTS_DIR
from cmis_v2.project import (
    create_project,
    get_current_state,
    get_project_events,
    load_project,
    save_deliverable,
    transition,
)
from cmis_v2.state_machine import is_terminal, is_user_gate
from cmis_v2.system_prompt import build_prompt, build_system_prompt
from cmis_v2.tools import CMISTools

# ---------------------------------------------------------------------------
# Auto-advance helper
# ---------------------------------------------------------------------------


def _auto_advance(project_id: str) -> str:
    """Automatically advance through states that have 'auto' trigger."""
    from cmis_v2.state_machine import can_transition, is_terminal, is_user_gate
    from cmis_v2.project import get_current_state, transition as do_transition

    current = get_current_state(project_id)
    while not is_terminal(current) and not is_user_gate(current):  # type: ignore[arg-type]
        if can_transition(current, "auto"):  # type: ignore[arg-type]
            result = do_transition(project_id, "auto", "system")
            if "error" in result:
                break
            current = result.get("current_state", current)
        else:
            break
    return current


# ---------------------------------------------------------------------------
# State -> prompt strategy mapping
# ---------------------------------------------------------------------------

_STATE_PROMPTS: dict[str, str] = {
    "requested": (
        "Analysis target: {target}. "
        "Create the project, transition to discovery, and perform initial market discovery. "
        "Identify the domain, key actors, and preliminary market scope."
    ),
    "discovery": (
        "Continue discovery for: {target}. "
        "Collect initial evidence, identify the domain structure, and prepare a scope proposal. "
        "When ready, transition to scope_review with a summary."
    ),
    "scope_locked": (
        "Scope: {scope}. "
        "Collect detailed data (collect_evidence, add_record), "
        "then build the R-Graph (build_snapshot, add_node, add_edge), "
        "evaluate key metrics (evaluate_metrics, set_metric_value), "
        "and perform structure analysis (match_patterns). "
        "When complete, transition through data_collection and structure_analysis to finding_review."
    ),
    "data_collection": (
        "Scope: {scope}. "
        "Collect evidence using collect_evidence and add_record. "
        "When data quality is sufficient, transition to structure_analysis."
    ),
    "structure_analysis": (
        "Scope: {scope}. "
        "Build the R-Graph (build_snapshot, add_node, add_edge), "
        "run match_patterns, and evaluate_metrics. "
        "When analysis is complete, transition to finding_review with a structured summary."
    ),
    "finding_locked": (
        "Market Reality Report is ready. "
        "Present findings summary. User decides whether to proceed with opportunity discovery."
    ),
    "opportunity_discovery": (
        "Discover opportunities using discover_gaps and pattern analysis. "
        "When complete, transition to opportunity_review with ranked opportunities."
    ),
    "strategy_design": (
        "Selected opportunity: {selected}. "
        "Design a strategy: define the business model, go-to-market plan, "
        "key metrics, and risk assessment. "
        "When complete, transition to decision_review with the strategy proposal."
    ),
    "synthesis": (
        "All analysis stages complete. "
        "Compile the final comprehensive report. "
        "Save deliverables via save_deliverable, then transition to completed."
    ),
}

# ---------------------------------------------------------------------------
# User gate -> trigger mapping
# ---------------------------------------------------------------------------

_GATE_ACTION_MAP: dict[str, dict[str, str]] = {
    "scope_review": {
        "approve": "scope_approved",
        "revise": "scope_revised",
        "reject": "scope_rejected",
    },
    "finding_review": {
        "approve": "finding_approved",
        "revise": "finding_deepened",
        "complete": "finding_completed_early",
    },
    "opportunity_review": {
        "approve": "opportunity_selected",
        "select": "opportunity_selected",
        "revise": "opportunity_deepened",
        "complete": "opportunity_completed_early",
    },
    "finding_locked": {
        "include_opportunity": "opportunity_included",
        "skip_opportunity": "opportunity_not_included",
    },
    "decision_review": {
        "approve": "decision_approved",
        "revise": "decision_revised",
    },
}

# ---------------------------------------------------------------------------
# Gate display metadata — Korean labels for non-developer users
# ---------------------------------------------------------------------------

_GATE_LABELS: dict[str, dict[str, str]] = {
    "scope_review": {
        "title": "범위 검토",
        "description": "분석 범위가 제안되었습니다. 범위를 검토하고 승인, 수정, 또는 거부를 선택하세요.",
        "approve_desc": "현재 범위를 승인하고 데이터 수집 단계로 진행합니다.",
        "revise_desc": "수정 사항을 전달하고 탐색 단계로 돌아갑니다.",
        "reject_desc": "분석을 중단합니다.",
    },
    "finding_review": {
        "title": "발견사항 검토",
        "description": "시장 분석 결과가 도출되었습니다. 발견사항을 검토하세요.",
        "approve_desc": "발견사항을 승인하고 기회 탐색 단계로 진행합니다.",
        "revise_desc": "추가 분석을 요청하고 구조 분석 단계로 돌아갑니다.",
        "complete_desc": "현재 발견사항으로 최종 보고서를 작성합니다.",
    },
    "finding_locked": {
        "title": "발견사항 확정",
        "description": "시장 분석 결과가 확정되었습니다. 기회 탐색을 진행할지 결정하세요.",
        "include_opportunity_desc": "기회 탐색 단계로 진행합니다.",
        "skip_opportunity_desc": "기회 탐색을 건너뛰고 최종 보고서를 작성합니다.",
    },
    "opportunity_review": {
        "title": "기회 검토",
        "description": "시장 기회가 식별되었습니다. 기회를 검토하고 선택하세요.",
        "approve_desc": "기회를 선택하고 전략 설계 단계로 진행합니다.",
        "select_desc": "특정 기회를 지정하여 선택합니다.",
        "revise_desc": "추가 기회 탐색을 요청합니다.",
        "complete_desc": "현재 결과로 최종 보고서를 작성합니다.",
    },
    "decision_review": {
        "title": "전략 검토",
        "description": "전략 제안이 완성되었습니다. 전략을 검토하세요.",
        "approve_desc": "전략을 승인하고 최종 보고서 작성으로 진행합니다.",
        "revise_desc": "전략 수정을 요청하고 전략 설계 단계로 돌아갑니다.",
    },
}

# State progression order for visual display
_STATE_ORDER: list[str] = [
    "requested", "discovery", "scope_review", "scope_locked",
    "data_collection", "structure_analysis", "finding_review", "finding_locked",
    "opportunity_discovery", "opportunity_review", "strategy_design",
    "decision_review", "synthesis", "completed",
]

# Revision-related event types — used to find the last user gate decision
_REVISION_EVENT_TYPES: set[str] = {
    "scope.revised", "scope.approved", "scope.rejected",
    "finding.approved", "finding.deepened", "finding.completed_early",
    "opportunity.selected", "opportunity.deepened", "opportunity.completed_early",
    "decision.approved", "decision.revised",
}


# ---------------------------------------------------------------------------
# Gate report generation (Finding 2 fix)
# ---------------------------------------------------------------------------


def _generate_gate_report(
    project_id: str,
    gate_state: str,
    result: Any,
) -> str:
    """Generate a human-readable markdown report for a user gate and save it.

    Saves the report to ``deliverables/{gate_state}_report.md`` and returns
    a terminal-friendly text summary.

    Args:
        project_id: The project ID.
        gate_state: The user gate state name (e.g. "scope_review").
        result: The RLM completion result (may be str or dict).

    Returns:
        Formatted text for terminal display.
    """
    manifest = load_project(project_id)
    if "error" in manifest:
        return f"[오류] 프로젝트를 불러올 수 없습니다: {manifest['error']}"

    gate_info = _GATE_LABELS.get(gate_state, {})
    gate_title = gate_info.get("title", gate_state)
    gate_description = gate_info.get("description", "")

    project_name = manifest.get("description", manifest.get("name", project_id))
    created_at = manifest.get("created_at", "")[:19].replace("T", " ")

    # Extract result text
    if isinstance(result, dict):
        result_text = result.get("result", result.get("text", ""))
        if isinstance(result_text, dict):
            result_text = json.dumps(result_text, indent=2, ensure_ascii=False)
        elif not isinstance(result_text, str):
            result_text = str(result_text)
    elif isinstance(result, str):
        result_text = result
    else:
        result_text = str(result) if result else "(분석 결과 없음)"

    # Collect event statistics
    events = get_project_events(project_id)
    evidence_count = sum(1 for e in events if e.get("type") == "engine.called"
                        and e.get("payload", {}).get("tool") in ("collect_evidence", "add_record"))
    tool_calls = sum(1 for e in events if e.get("type") == "engine.called")

    # Build markdown report
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md_lines: list[str] = [
        f"# {gate_title} 보고서",
        "",
        f"- **프로젝트**: {project_name}",
        f"- **프로젝트 ID**: {project_id}",
        f"- **생성일**: {created_at}",
        f"- **보고서 생성**: {now_str}",
        f"- **현재 단계**: {gate_state} ({gate_title})",
        "",
        "---",
        "",
        "## 분석 결과 요약",
        "",
        result_text,
        "",
        "---",
        "",
        "## 통계",
        "",
        f"- 총 도구 호출 횟수: {tool_calls}건",
        f"- 근거 수집 횟수: {evidence_count}건",
        f"- 총 이벤트 수: {len(events)}건",
        "",
    ]

    # Add scope info if available
    scope = manifest.get("scope")
    if scope:
        md_lines.extend([
            "## 분석 범위",
            "",
        ])
        if isinstance(scope, dict):
            for k, v in scope.items():
                if k == "locked_at":
                    continue
                md_lines.append(f"- **{k}**: {v}")
        else:
            md_lines.append(str(scope))
        md_lines.append("")

    # Add available actions
    gate_actions = _GATE_ACTION_MAP.get(gate_state, {})
    if gate_actions:
        md_lines.extend([
            "---",
            "",
            "## 다음 행동 선택지",
            "",
        ])
        for action_name in gate_actions:
            desc_key = f"{action_name}_desc"
            desc = gate_info.get(desc_key, "")
            cmd = f"python -m cmis_v2.runner --resume {project_id} --{action_name}"
            if action_name in ("revise",):
                cmd += ' "수정 내용을 입력하세요"'
            elif action_name in ("select",):
                cmd += " 기회_ID"
            md_lines.append(f"### --{action_name}")
            if desc:
                md_lines.append(f"{desc}")
            md_lines.append(f"```")
            md_lines.append(cmd)
            md_lines.append(f"```")
            md_lines.append("")

    md_content = "\n".join(md_lines)

    # Save to deliverables
    filename = f"{gate_state}_report.md"
    save_deliverable(project_id, filename, md_content)
    report_path = PROJECTS_DIR / project_id / "deliverables" / filename

    # Build terminal summary
    sep = "=" * 60
    terminal_lines: list[str] = [
        "",
        sep,
        f"  프로젝트: {project_name}",
        f"  현재 상태: {gate_state} ({gate_title})",
        sep,
        "",
        f"[상태 설명]",
        f"  {gate_description}",
        "",
        f"[분석 요약]",
    ]

    # Show first ~500 chars of result as summary
    summary_text = result_text[:500]
    if len(result_text) > 500:
        summary_text += " ..."
    for line in summary_text.split("\n"):
        terminal_lines.append(f"  {line}")

    terminal_lines.extend([
        "",
        f"[통계]",
        f"  - 도구 호출: {tool_calls}건 / 근거 수집: {evidence_count}건",
        "",
        f"[다음 행동 선택지]",
    ])

    for action_name in gate_actions:
        desc_key = f"{action_name}_desc"
        desc = gate_info.get(desc_key, "")
        terminal_lines.append(f"  --{action_name:10s} : {desc}")

    terminal_lines.extend([
        "",
        f"[상세 보고서]",
        f"  {report_path}",
        "",
        f"[사용 예시]",
        f"  python -m cmis_v2.runner --resume {project_id} --approve",
        f"  python -m cmis_v2.runner --resume {project_id} --revise \"수정 내용\"",
        "",
        sep,
    ])

    return "\n".join(terminal_lines)


# ---------------------------------------------------------------------------
# Last gate context extraction (Finding 9 fix)
# ---------------------------------------------------------------------------


def _extract_last_gate_context(project_id: str) -> dict[str, Any]:
    """Extract the most recent user gate decision from the event log.

    Searches ``events.db`` for the last revision/approval/selection event
    and returns its payload so that the LM prompt can include the user's
    instructions.

    Returns:
        dict with keys: gate, action, revision_note, selected, timestamp.
        Empty dict if no gate event is found.
    """
    events = get_project_events(project_id)

    for evt in reversed(events):
        evt_type: str = evt.get("type", "")
        if evt_type in _REVISION_EVENT_TYPES:
            payload = evt.get("payload") or {}
            return {
                "gate": evt.get("state_before", ""),
                "action": evt_type,
                "revision_note": payload.get("revision_note"),
                "selected": payload.get("selected"),
                "action_data": payload.get("action_data"),
                "timestamp": evt.get("ts", ""),
            }

    return {}


# ---------------------------------------------------------------------------
# Human-readable output formatter (Finding 2 fix)
# ---------------------------------------------------------------------------


def _format_human_output(result: dict[str, Any]) -> str:
    """Convert a run_new/resume result dict into human-readable terminal text.

    This replaces the raw JSON dump for terminal output.

    Args:
        result: The dict returned by run_new() or resume().

    Returns:
        Formatted string for terminal display.
    """
    if "error" in result:
        return f"\n[오류] {result['error']}\n"

    project_id = result.get("project_id", "(unknown)")
    final_state = result.get("final_state", "(unknown)")
    inner_result = result.get("result", "")

    # If we reached a user gate, _generate_gate_report already produced
    # the terminal output — it is stored in result["_terminal_output"].
    terminal_output = result.get("_terminal_output")
    if terminal_output:
        return terminal_output

    # For terminal / completed states, produce a simple summary
    sep = "=" * 60
    lines: list[str] = [
        "",
        sep,
        f"  프로젝트 ID : {project_id}",
        f"  최종 상태   : {final_state}",
        sep,
        "",
    ]

    if is_terminal(final_state):  # type: ignore[arg-type]
        lines.append("[완료] 프로젝트가 종료되었습니다.")
    else:
        lines.append(f"[진행 중] 현재 상태: {final_state}")

    if inner_result:
        lines.append("")
        lines.append("[결과]")
        result_str = inner_result if isinstance(inner_result, str) else json.dumps(
            inner_result, indent=2, ensure_ascii=False, default=str,
        )
        for line in result_str[:1000].split("\n"):
            lines.append(f"  {line}")
        if len(str(inner_result)) > 1000:
            lines.append("  ...")

    lines.extend(["", sep])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------


def show_status(project_id: str) -> None:
    """Display project status in a human-readable format.

    Prints project metadata, state progression, available actions,
    and recent events to stdout.

    Args:
        project_id: The project to inspect.
    """
    manifest = load_project(project_id)
    if "error" in manifest:
        print(f"\n[오류] {manifest['error']}\n")
        return

    current_state: str = manifest["current_state"]
    project_name = manifest.get("description", manifest.get("name", project_id))
    created_at = manifest.get("created_at", "")[:19].replace("T", " ")
    updated_at = manifest.get("updated_at", "")[:19].replace("T", " ")
    policy_mode = manifest.get("policy_mode", "decision_balanced")
    scope = manifest.get("scope")

    events = get_project_events(project_id)

    sep = "=" * 60
    lines: list[str] = [
        "",
        sep,
        "  프로젝트 상태 보고서",
        sep,
        "",
        "[기본 정보]",
        f"  프로젝트 ID : {project_id}",
        f"  이름        : {project_name}",
        f"  생성일      : {created_at}",
        f"  최종 갱신   : {updated_at}",
        f"  정책 모드   : {policy_mode}",
        "",
    ]

    # Scope info
    if scope and isinstance(scope, dict):
        lines.append("[분석 범위]")
        for k, v in scope.items():
            if k == "locked_at":
                continue
            lines.append(f"  {k}: {v}")
        lines.append("")

    # State progression visualization
    lines.append("[진행 상태]")
    try:
        current_idx = _STATE_ORDER.index(current_state)
    except ValueError:
        current_idx = -1

    progress_parts: list[str] = []
    for i, state_name in enumerate(_STATE_ORDER):
        if i == current_idx:
            progress_parts.append(f"[{state_name}]")
        elif i < current_idx:
            progress_parts.append(state_name)
        else:
            progress_parts.append(f"({state_name})")

    # Print in rows of 4
    row_size = 4
    for row_start in range(0, len(progress_parts), row_size):
        row = progress_parts[row_start:row_start + row_size]
        lines.append("  " + " -> ".join(row))

    lines.append("")

    # User gate actions
    if is_user_gate(current_state):  # type: ignore[arg-type]
        gate_info = _GATE_LABELS.get(current_state, {})
        gate_title = gate_info.get("title", current_state)
        gate_description = gate_info.get("description", "")
        gate_actions = _GATE_ACTION_MAP.get(current_state, {})

        lines.append(f"[사용자 행동 필요] -- {gate_title}")
        lines.append(f"  {gate_description}")
        lines.append("")

        for action_name in gate_actions:
            desc_key = f"{action_name}_desc"
            desc = gate_info.get(desc_key, "")
            cmd = f"python -m cmis_v2.runner --resume {project_id} --{action_name}"
            if action_name == "revise":
                cmd += ' "수정 내용"'
            elif action_name == "select":
                cmd += " 기회_ID"
            lines.append(f"  --{action_name:10s} : {desc}")
            lines.append(f"                 {cmd}")
            lines.append("")

        # Check if gate report exists
        report_path = PROJECTS_DIR / project_id / "deliverables" / f"{current_state}_report.md"
        if report_path.exists():
            lines.append(f"  [상세 보고서] {report_path}")
            lines.append("")

    elif is_terminal(current_state):  # type: ignore[arg-type]
        lines.append(f"[완료] 프로젝트가 종료되었습니다. (상태: {current_state})")
        lines.append("")
    else:
        lines.append(f"[진행 중] 현재 자동 실행 단계입니다. (상태: {current_state})")
        lines.append("")

    # Recent events (last 10)
    lines.append("[최근 이벤트]")
    recent = events[-10:] if len(events) > 10 else events
    if not recent:
        lines.append("  (이벤트 없음)")
    else:
        for evt in recent:
            ts = evt.get("ts", "")[:19].replace("T", " ")
            evt_type = evt.get("type", "")
            actor = evt.get("actor", "")
            state_before = evt.get("state_before", "")
            state_after = evt.get("state_after", "")

            transition_str = ""
            if state_before and state_after:
                transition_str = f"  {state_before} -> {state_after}"

            payload = evt.get("payload", {})
            note = ""
            if payload.get("revision_note"):
                note = f'  "{payload["revision_note"]}"'
            elif payload.get("selected"):
                note = f'  선택: {payload["selected"]}'

            lines.append(f"  {ts}  {evt_type:25s} ({actor}){transition_str}{note}")

    lines.extend(["", sep])
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Approve confirmation (pre-action check)
# ---------------------------------------------------------------------------


def _confirm_action(project_id: str, action: str) -> bool:
    """Ask the user to confirm a gate action before proceeding.

    Displays a summary of the current gate state and the chosen action,
    then prompts for confirmation on stdin.

    Args:
        project_id: The project ID.
        action: The action name (approve, revise, etc.).

    Returns:
        True if the user confirms, False otherwise.
    """
    manifest = load_project(project_id)
    if "error" in manifest:
        return True  # Let the actual resume() handle the error

    current_state: str = manifest["current_state"]
    gate_info = _GATE_LABELS.get(current_state, {})
    gate_title = gate_info.get("title", current_state)
    action_desc = gate_info.get(f"{action}_desc", action)

    project_name = manifest.get("description", manifest.get("name", project_id))

    # Check if report exists
    report_path = PROJECTS_DIR / project_id / "deliverables" / f"{current_state}_report.md"

    sep = "-" * 50
    print(f"\n{sep}")
    print(f"  프로젝트   : {project_name}")
    print(f"  현재 단계  : {gate_title}")
    print(f"  선택 행동  : --{action}")
    print(f"  설명       : {action_desc}")

    if report_path.exists():
        print(f"  상세 보고서: {report_path}")
    else:
        print(f"  (상세 보고서가 아직 생성되지 않았습니다)")

    print(f"{sep}")

    try:
        answer = input(f"\n  '{gate_title}' 단계에서 --{action}을(를) 실행합니다. 계속하시겠습니까? (y/N): ")
        return answer.strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print("\n  취소되었습니다.")
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_context(project_id: str, manifest: dict[str, Any]) -> dict[str, str]:
    """Extract context variables from project state for prompt building."""
    context: dict[str, str] = {}

    # Target from description
    context["target"] = manifest.get("description", manifest.get("name", ""))

    # Scope
    scope = manifest.get("scope")
    if scope:
        context["scope"] = json.dumps(scope, ensure_ascii=False)[:500]
    else:
        context["scope"] = "(not yet defined)"

    # Selected opportunity from events
    events = get_project_events(project_id)
    for evt in reversed(events):
        if evt.get("type") == "opportunity.selected":
            payload = evt.get("payload", {})
            context["selected"] = json.dumps(payload, ensure_ascii=False)[:300]
            break
    if "selected" not in context:
        context["selected"] = "(none)"

    return context


def _build_state_prompt(
    project_id: str,
    manifest: dict[str, Any],
    policy_mode: str,
    execution_mode: str,
) -> str:
    """Build a prompt appropriate for the current project state.

    Includes context from the most recent user gate decision (revision_note,
    selected opportunity, etc.) so the LM can incorporate user feedback.
    """
    state = manifest.get("current_state", "requested")
    context = _extract_context(project_id, manifest)

    # Get state-specific instruction
    template = _STATE_PROMPTS.get(state, "Continue the analysis from state: {state}.")
    # Add state to context for fallback template
    context["state"] = state
    state_instruction = template.format(**context)

    # --- Finding 9 fix: include last gate decision in prompt ---
    gate_context = _extract_last_gate_context(project_id)
    gate_section = ""
    if gate_context:
        gate_section = "\n## Previous User Decision\n\n"
        gate_section += f"- **Gate**: {gate_context.get('gate', '(unknown)')}\n"
        gate_section += f"- **Action**: {gate_context.get('action', '(unknown)')}\n"

        revision_note = gate_context.get("revision_note")
        if revision_note:
            gate_section += f"- **Revision Note**: \"{revision_note}\"\n"

        selected = gate_context.get("selected")
        if selected:
            gate_section += f"- **Selected**: {selected}\n"

        action_data = gate_context.get("action_data")
        if action_data and action_data != revision_note and action_data != selected:
            gate_section += f"- **Additional Data**: {action_data}\n"

        ts = gate_context.get("timestamp", "")
        if ts:
            gate_section += f"- **Timestamp**: {ts}\n"

        gate_section += (
            "\nYou MUST incorporate the above user instructions into your analysis. "
            "If a revision note is provided, address every point in the note. "
            "If a selection is provided, focus on the selected item.\n"
        )

    # Build full prompt
    system = build_system_prompt()
    return (
        f"{system}\n"
        f"## Current Session\n\n"
        f"- **Project ID**: {project_id}\n"
        f"- **Current state**: {state}\n"
        f"- **Policy mode**: {policy_mode}\n"
        f"- **Execution mode**: {execution_mode}\n\n"
        f"{gate_section}"
        f"## Task\n\n"
        f"{state_instruction}\n\n"
        f"When you reach a user gate or terminal state, produce the result as FINAL_VAR().\n"
    )


# ---------------------------------------------------------------------------
# RLM builder
# ---------------------------------------------------------------------------


def build_rlm(
    tools: CMISTools,
    execution_mode: str = "autopilot",
    backend: str = "openai",
    model_name: str = "gpt-5",
) -> Any:
    """Create an RLM instance with CMIS tools registered.

    Args:
        tools: CMISTools instance with project_id set.
        execution_mode: One of "autopilot", "review", "manual".
        backend: LLM backend - "openai" or "anthropic".
        model_name: Model name e.g. "gpt-5".

    Returns:
        Configured RLM instance.
    """
    from rlm import RLM
    from rlm.logger import RLMLogger

    return RLM(
        backend=backend,
        backend_kwargs={"model_name": model_name},
        custom_tools=tools.as_rlm_tools(),
        max_depth=2,
        max_iterations=30,
        max_budget=15.0,
        max_timeout=600.0,
        verbose=True,
        logger=RLMLogger(log_dir="./logs"),
    )


def _run_rlm_with_retry(
    rlm: Any,
    task_prompt: str,
    system_prompt: str,
    max_retries: int = 3,
) -> Any:
    """Run rlm.completion() with retry on transient API errors.

    OpenAI API occasionally returns 400 (JSON parse) or 500 errors
    that succeed on retry with the same payload.
    """
    import time

    for attempt in range(1, max_retries + 1):
        try:
            return rlm.completion(task_prompt, root_prompt=system_prompt)
        except Exception as e:
            error_str = str(e)
            is_transient = any(keyword in error_str for keyword in [
                "could not parse the JSON body",
                "500",
                "502",
                "503",
                "overloaded",
                "rate_limit",
            ])
            if is_transient and attempt < max_retries:
                wait = 2 ** attempt
                print(f"[CMIS] API error (attempt {attempt}/{max_retries}), retrying in {wait}s: {error_str[:120]}")
                time.sleep(wait)
                continue
            raise


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def run_new(
    target: str,
    policy_mode: str = "decision_balanced",
    execution_mode: str = "autopilot",
    backend: str = "openai",
    model_name: str = "gpt-5",
) -> dict[str, Any]:
    """Start a new analysis project.

    1. Create a project.
    2. Transition to discovery.
    3. Build prompt from target + execution_mode + policy_mode.
    4. Create RLM with project_id.
    5. Run rlm.completion().
    6. Return result.
    """
    # 1. Create project
    domain_id = target.replace(" ", "_")[:60]
    manifest = create_project(
        name=domain_id[:30],
        description=target,
        domain_id=domain_id,
    )
    project_id: str = manifest["project_id"]

    # 2. Transition to discovery
    transition(project_id, "project_created", "system")

    # 2b. Auto-advance through any auto-trigger states
    _auto_advance(project_id)

    # 3. Build prompt — separate system prompt (root_prompt) from task (prompt)
    system_prompt = build_system_prompt()
    task_prompt = (
        f"## Current Session\n\n"
        f"- **Project ID**: {project_id}\n"
        f"- **Current state**: discovery\n"
        f"- **Policy mode**: {policy_mode}\n"
        f"- **Execution mode**: {execution_mode}\n\n"
        f"## Task\n\n"
        f"Analyze: {target}\n\n"
        f"Start by collecting evidence with collect_evidence(), then propose a scope "
        f"with lock_scope(). After scope is ready, call transition() with "
        f"'discovery_completed' to move to scope_review.\n"
        f"At scope_review, produce a scope summary as FINAL_VAR() and stop.\n"
    )

    # 4. Build RLM
    tools = CMISTools(project_id=project_id)
    rlm = build_rlm(tools, execution_mode=execution_mode, backend=backend, model_name=model_name)

    # 5. Run completion — system prompt as root_prompt, task as prompt
    result = _run_rlm_with_retry(rlm, task_prompt, system_prompt)

    final_state = get_current_state(project_id)
    output: dict[str, Any] = {
        "project_id": project_id,
        "final_state": final_state,
        "result": result,
    }

    # Finding 2 fix: auto-generate gate report when reaching a user gate
    if is_user_gate(final_state):  # type: ignore[arg-type]
        terminal_text = _generate_gate_report(project_id, final_state, result)
        output["_terminal_output"] = terminal_text

    return output


def resume(
    project_id: str,
    action: str,
    action_data: str = "",
    policy_mode: str = "decision_balanced",
    execution_mode: str = "autopilot",
    backend: str = "openai",
    model_name: str = "gpt-5",
) -> dict[str, Any]:
    """Resume a project from a user gate.

    1. Load project manifest and verify current state.
    2. Map action to the appropriate trigger and execute transition.
    3. If resulting state is not terminal/gate, build prompt and run next segment.

    Args:
        project_id: The project to resume.
        action: One of "approve", "revise", "reject", "complete", "select".
        action_data: Additional data for the action (e.g. revision note, selection ID).
        policy_mode: Policy mode override.
        execution_mode: Execution mode.
        backend: LLM backend.
        model_name: Model name.

    Returns:
        dict with project_id, final_state, result.
    """
    # 1. Load and verify
    manifest = load_project(project_id)
    if "error" in manifest:
        return manifest

    current_state: str = manifest["current_state"]

    if not is_user_gate(current_state):  # type: ignore[arg-type]
        return {"error": f"Project is not at a user gate. Current state: {current_state}"}

    # 2. Determine trigger
    gate_actions = _GATE_ACTION_MAP.get(current_state, {})
    trigger = gate_actions.get(action)
    if trigger is None:
        valid = list(gate_actions.keys())
        return {"error": f"Invalid action '{action}' for state '{current_state}'. Valid: {valid}"}

    # Build payload
    payload: dict[str, Any] = {}
    if action_data:
        payload["action_data"] = action_data
    if action == "revise":
        payload["revision_note"] = action_data
    elif action == "select":
        payload["selected"] = action_data

    # Execute transition
    manifest = transition(project_id, trigger, "user", payload=payload)
    if "error" in manifest:
        return manifest

    # 2b. Auto-advance through any auto-trigger states
    _auto_advance(project_id)
    new_state = get_current_state(project_id)

    # 3. If terminal or gate, stop
    if is_terminal(new_state) or is_user_gate(new_state):  # type: ignore[arg-type]
        return {
            "project_id": project_id,
            "final_state": new_state,
            "result": f"Project transitioned to {new_state}. "
            + ("Project complete." if is_terminal(new_state) else "Awaiting user action."),  # type: ignore[arg-type]
        }

    # 4. Build prompt for next automatic segment — separate system from task
    manifest = load_project(project_id)
    system_prompt = build_system_prompt()
    state = manifest.get("current_state", "requested")
    context = _extract_context(project_id, manifest)
    context["state"] = state
    template = _STATE_PROMPTS.get(state, "Continue the analysis from state: {state}.")
    state_instruction = template.format(**context)

    gate_context = _extract_last_gate_context(project_id)
    gate_section = ""
    if gate_context:
        gate_section = "\n## Previous User Decision\n\n"
        gate_section += f"- **Gate**: {gate_context.get('gate', '(unknown)')}\n"
        gate_section += f"- **Action**: {gate_context.get('action', '(unknown)')}\n"
        revision_note = gate_context.get("revision_note")
        if revision_note:
            gate_section += f"- **Revision Note**: \"{revision_note}\"\n"
        selected = gate_context.get("selected")
        if selected:
            gate_section += f"- **Selected**: {selected}\n"
        action_data = gate_context.get("action_data")
        if action_data and action_data != revision_note and action_data != selected:
            gate_section += f"- **Additional Data**: {action_data}\n"
        gate_section += (
            "\nYou MUST incorporate the above user instructions into your analysis.\n"
        )

    task_prompt = (
        f"## Current Session\n\n"
        f"- **Project ID**: {project_id}\n"
        f"- **Current state**: {state}\n"
        f"- **Policy mode**: {policy_mode}\n"
        f"- **Execution mode**: {execution_mode}\n\n"
        f"{gate_section}"
        f"## Task\n\n"
        f"{state_instruction}\n\n"
        f"When you reach a user gate or terminal state, produce the result as FINAL_VAR().\n"
    )

    # 5. Run RLM — system prompt as root_prompt, task as prompt
    tools = CMISTools(project_id=project_id)
    rlm = build_rlm(tools, execution_mode=execution_mode, backend=backend, model_name=model_name)
    result = _run_rlm_with_retry(rlm, task_prompt, system_prompt)

    final_state = get_current_state(project_id)
    output: dict[str, Any] = {
        "project_id": project_id,
        "final_state": final_state,
        "result": result,
    }

    # Finding 2 fix: auto-generate gate report when reaching a user gate
    if is_user_gate(final_state):  # type: ignore[arg-type]
        terminal_text = _generate_gate_report(project_id, final_state, result)
        output["_terminal_output"] = terminal_text

    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for CMIS v2 runner."""
    parser = argparse.ArgumentParser(
        description="CMIS v2 Market Intelligence Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # New analysis
  python -m cmis_v2.runner "한국 전기차 충전 인프라 시장 분석"

  # Check project status
  python -m cmis_v2.runner --status PROJECT_ID

  # Resume with approval
  python -m cmis_v2.runner --resume PROJECT_ID --approve

  # Resume with revision
  python -m cmis_v2.runner --resume PROJECT_ID --revise "시장 범위를 B2C로 한정"

  # Resume with selection
  python -m cmis_v2.runner --resume PROJECT_ID --select "PAT-subscription_model"
""",
    )

    # Positional: analysis target (for new runs)
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Analysis target description (for new analysis)",
    )

    # Status mode
    parser.add_argument(
        "--status",
        metavar="PROJECT_ID",
        default=None,
        help="Display project status in human-readable format",
    )

    # Resume mode
    parser.add_argument(
        "--resume",
        metavar="PROJECT_ID",
        default=None,
        help="Resume an existing project from a user gate",
    )

    # User gate actions (mutually exclusive)
    gate_group = parser.add_mutually_exclusive_group()
    gate_group.add_argument("--approve", action="store_true", help="Approve at current gate")
    gate_group.add_argument("--revise", metavar="NOTE", default=None, help="Revise with note")
    gate_group.add_argument("--reject", action="store_true", help="Reject (scope_review only)")
    gate_group.add_argument("--complete", action="store_true", help="Complete early")
    gate_group.add_argument("--select", metavar="ID", default=None, help="Select an opportunity")
    gate_group.add_argument("--include-opportunity", action="store_true", dest="include_opportunity", help="Proceed with opportunity discovery (finding_locked gate)")
    gate_group.add_argument("--skip-opportunity", action="store_true", dest="skip_opportunity", help="Skip opportunity discovery (finding_locked gate)")

    # Confirmation skip
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt (for automation/scripts)",
    )

    # Output format
    parser.add_argument(
        "--human",
        action="store_true",
        help="Force human-readable Korean output (default behavior)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output raw JSON instead of human-readable format",
    )
    parser.add_argument(
        "--json-out",
        metavar="PATH",
        default=None,
        dest="json_out_path",
        help="Save JSON output to a file (in addition to terminal output)",
    )

    # Options
    parser.add_argument(
        "--policy",
        choices=["reporting_strict", "decision_balanced", "exploration_friendly"],
        default="decision_balanced",
        help="Policy mode (default: decision_balanced)",
    )
    parser.add_argument(
        "--mode",
        choices=["autopilot", "review", "manual"],
        default="autopilot",
        help="Execution mode (default: autopilot)",
    )
    parser.add_argument(
        "--backend",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM backend (default: openai)",
    )
    parser.add_argument(
        "--model",
        default="gpt-5",
        help="Model name (default: gpt-5)",
    )

    args = parser.parse_args()

    # --- Status mode ---
    if args.status:
        show_status(args.status)
        return

    # --- Resume mode ---
    if args.resume:
        # Determine action
        if args.approve:
            action, action_data = "approve", ""
        elif args.revise is not None:
            action, action_data = "revise", args.revise
        elif args.reject:
            action, action_data = "reject", ""
        elif args.complete:
            action, action_data = "complete", ""
        elif args.select is not None:
            action, action_data = "select", args.select
        elif args.include_opportunity:
            action, action_data = "include_opportunity", ""
        elif args.skip_opportunity:
            action, action_data = "skip_opportunity", ""
        else:
            parser.error("--resume requires one of: --approve, --revise, --reject, --complete, --select, --include-opportunity, --skip-opportunity")
            return

        # Confirmation check for approve/reject/complete (irreversible actions)
        if action in ("approve", "reject", "complete") and not args.yes:
            if not _confirm_action(args.resume, action):
                print("\n  실행이 취소되었습니다.\n")
                return

        result = resume(
            project_id=args.resume,
            action=action,
            action_data=action_data,
            policy_mode=args.policy,
            execution_mode=args.mode,
            backend=args.backend,
            model_name=args.model,
        )

    elif args.target:
        # New analysis mode
        result = run_new(
            target=args.target,
            policy_mode=args.policy,
            execution_mode=args.mode,
            backend=args.backend,
            model_name=args.model,
        )
    else:
        parser.error("Provide an analysis target or use --resume PROJECT_ID or --status PROJECT_ID")
        return

    # Output result
    if args.json_output:
        # Strip internal-only keys before JSON output
        output = {k: v for k, v in result.items() if not k.startswith("_")}
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    else:
        print(_format_human_output(result))

    # Save JSON to file if requested
    if args.json_out_path:
        output = {k: v for k, v in result.items() if not k.startswith("_")}
        out_path = Path(args.json_out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(output, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"\n  JSON 저장됨: {out_path}")


if __name__ == "__main__":
    main()
