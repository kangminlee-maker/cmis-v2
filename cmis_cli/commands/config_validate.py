"""config-validate 명령어

YAML 설정 검증 (Cross-reference 포함)

2025-12-11: Workflow CLI Phase 2
"""

from __future__ import annotations

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def _looks_like_path_ref(value: str) -> bool:
    """파일/디렉토리 레퍼런스로 보이는 문자열인지 판단"""
    if value.endswith("/"):
        return True
    if value.endswith((".yaml", ".yml")):
        return True
    if (".yaml#" in value) or (".yml#" in value):
        return True
    return False


def _split_ref(ref: str) -> tuple[str, str | None]:
    """'path#fragment' 형태를 분해"""
    if "#" not in ref:
        return ref, None
    path, frag = ref.split("#", 1)
    frag = frag.strip()
    return path, frag or None


def _resolve_fragment(doc: object, fragment: str) -> bool:
    """YAML 문서에서 dot-path fragment 존재 여부 확인"""
    node = doc
    for part in fragment.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
            continue
        return False
    return True


def _collect_string_refs(node: object, out: list[str]) -> None:
    """cmis.yaml 전체에서 path-like 문자열 레퍼런스 수집"""
    if isinstance(node, dict):
        for _, v in node.items():
            _collect_string_refs(v, out)
        return
    if isinstance(node, list):
        for v in node:
            _collect_string_refs(v, out)
        return
    if isinstance(node, str) and _looks_like_path_ref(node):
        out.append(node)


def _validate_ref(project_root: Path, ref: str, doc_cache: dict[Path, object]) -> list[str]:
    """레퍼런스 1개 검증 (에러 메시지 리스트 반환)"""
    errors: list[str] = []

    path_str, fragment = _split_ref(ref)
    p = Path(path_str)
    if not p.is_absolute():
        p = (project_root / p).resolve()

    if path_str.endswith("/"):
        if not p.exists():
            errors.append(f"missing directory: {ref} -> {p}")
        elif not p.is_dir():
            errors.append(f"not a directory: {ref} -> {p}")
        return errors

    if not p.exists():
        errors.append(f"missing file: {ref} -> {p}")
        return errors
    if not p.is_file():
        errors.append(f"not a file: {ref} -> {p}")
        return errors

    if fragment:
        if p not in doc_cache:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    doc_cache[p] = yaml.safe_load(f) or {}
            except Exception as e:
                errors.append(f"failed to load YAML for fragment check: {ref} ({e})")
                return errors

        if not _resolve_fragment(doc_cache[p], fragment):
            errors.append(f"missing fragment: {ref}")

    return errors


def cmd_config_validate(args):
    """config-validate 명령 실행

    Args:
        args: Argparse args
    """
    print("=" * 60)
    print("CMIS - Config Validation")
    print("=" * 60)
    print()

    # cmis.yaml
    config_path = Path(args.file) if args.file else Path("cmis.yaml")

    if not config_path.exists():
        print(f"[ERROR] Config 파일 없음: {config_path}")
        return

    print(f"검증 대상: {config_path}")
    print()

    # YAML 로딩
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        print("YAML 구문: OK")
    except Exception as e:
        print(f"[ERROR] YAML 구문 오류: {e}")
        return

    print()

    overall_ok = True

    # Seeds 확인
    if args.check_seeds or args.check_all:
        print("[Seeds 검증]")

        seeds_dir = Path("seeds")
        if seeds_dir.exists():
            yaml_files = list(seeds_dir.glob("*.yaml"))
            print(f"Seeds: {len(yaml_files)}개 파일")
        else:
            print("[WARN] Seeds 디렉토리 없음")

        print()

    # Registry / References 확인
    if getattr(args, "check_registry", False) or args.check_all:
        print("[Registry/References 검증]")

        project_root = config_path.parent.resolve()
        doc_cache: dict[Path, object] = {}

        errors: list[str] = []
        warnings: list[str] = []

        cmis_root = data.get("cmis", {}) if isinstance(data, dict) else {}

        # 1) modules: 존재성 검증
        modules = cmis_root.get("modules", {}) if isinstance(cmis_root, dict) else {}
        module_refs: list[str] = []
        _collect_string_refs(modules, module_refs)
        for ref in sorted(set(module_refs)):
            errors.extend(_validate_ref(project_root, ref, doc_cache))

        # 2) registries: 존재성 + fragment 검증
        registries = cmis_root.get("registries", {}) if isinstance(cmis_root, dict) else {}
        registry_refs: list[str] = []
        _collect_string_refs(registries, registry_refs)
        for ref in sorted(set(registry_refs)):
            errors.extend(_validate_ref(project_root, ref, doc_cache))

        # 3) cmis.yaml 전체에서 ref-like 문자열을 찾아 검증 (모듈/레지스트리 외 포함)
        all_refs: list[str] = []
        _collect_string_refs(cmis_root, all_refs)
        for ref in sorted(set(all_refs)):
            errors.extend(_validate_ref(project_root, ref, doc_cache))

        # 4) 루트 계약 규칙: canonical_workflows는 외부 YAML로만
        wf_registry = (
            cmis_root.get("planes", {})
            .get("orchestration_plane", {})
            .get("workflow_registry", {})
        )
        if isinstance(wf_registry, dict) and "canonical_workflows" in wf_registry:
            warnings.append("cmis.yaml에 canonical_workflows가 존재합니다. 외부 YAML(ref)로만 유지하세요.")

        if errors:
            overall_ok = False
            print("[ERROR] Registry/References errors:")
            for e in errors:
                print(f"  - {e}")
        else:
            print("Registry/References: OK")

        if warnings:
            print("[WARN] Registry/References warnings:")
            for w in warnings:
                print(f"  - {w}")

        print()

    # Patterns 확인
    if args.check_patterns or args.check_all:
        print("[Patterns 검증]")

        project_root = config_path.parent.resolve()
        modules = data.get("cmis", {}).get("modules", {})
        patterns_dir_str = modules.get("libraries", {}).get("pattern_library", "libraries/patterns/")
        patterns_dir = Path(patterns_dir_str)
        if not patterns_dir.is_absolute():
            patterns_dir = project_root / patterns_dir

        if patterns_dir.exists():
            yaml_files = list(patterns_dir.glob("*.yaml"))
            print(f"Patterns: {len(yaml_files)}개")
        else:
            print(f"[WARN] Patterns 디렉토리 없음: {patterns_dir}")

        print()

    # Workflows 확인
    if args.check_workflows or args.check_all:
        print("[Workflows 검증]")

        project_root = config_path.parent.resolve()
        modules = data.get("cmis", {}).get("modules", {})
        workflows_path_str = modules.get("config", {}).get("workflows", "config/workflows.yaml")
        workflows_path = Path(workflows_path_str)
        if not workflows_path.is_absolute():
            workflows_path = project_root / workflows_path

        try:
            with open(workflows_path, "r", encoding="utf-8") as f:
                wf_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[ERROR] workflows.yaml 로딩 실패: {e}")
            wf_data = {}

        canonical_workflows = wf_data.get("canonical_workflows", {}) or {}
        if not isinstance(canonical_workflows, dict):
            canonical_workflows = {}

        print(f"Workflows: {len(canonical_workflows)}개")

        for wf_key, wf in canonical_workflows.items():
            if not isinstance(wf, dict):
                continue
            wf_id = wf.get("id") or wf_key
            role_id = wf.get("role_id") or ""
            print(f"  - {wf_id} (role: {role_id})")

        print()

    # Cross-reference
    if args.check_all:
        print("[Cross-references]")

        warnings = []

        # Workflow → Engines
        print("  Workflow → Engines: (Phase 3)")

        # Pattern → Metrics
        print("  Pattern → Metrics: (Phase 3)")

        if warnings:
            print()
            print("[WARN] Warnings:")
            for w in warnings:
                print(f"  - {w}")
        else:
            print("  OK")

        print()

    print("Overall: PASS" if overall_ok else "Overall: FAIL")
