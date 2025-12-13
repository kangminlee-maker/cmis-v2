"""CMIS Cursor bootstrap helper (developer-friendly).

목표:
- Cursor IDE에서 비전문가가 바로 실행할 수 있도록 환경을 자동 구성
- venv 생성/의존성 설치/.env 생성/CMIS bootstrap 실행을 한 번에 수행

사용 예:
  python3 dev/setup/cursor_bootstrap.py
  python3 dev/setup/cursor_bootstrap.py --skip-venv --no-install
  python3 dev/setup/cursor_bootstrap.py --smoke-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _project_root_from_here() -> Path:
    # dev/setup/cursor_bootstrap.py -> project root = 2 levels up from dev/
    return Path(__file__).resolve().parent.parent.parent


def _venv_python(project_root: Path) -> Path:
    if os.name == "nt":
        return project_root / ".venv" / "Scripts" / "python.exe"
    return project_root / ".venv" / "bin" / "python"


def _run(cmd: list[str], *, cwd: Path, env: Optional[dict[str, str]] = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="CMIS Cursor bootstrap helper")
    parser.add_argument("--project-root", dest="project_root", help="프로젝트 루트 (기본: 자동 탐지)")
    parser.add_argument("--skip-venv", dest="skip_venv", action="store_true", help=".venv 생성/사용을 건너뜀")
    parser.add_argument("--no-install", dest="no_install", action="store_true", help="의존성 설치를 건너뜀")
    parser.add_argument("--force-env", dest="force_env", action="store_true", help=".env를 env.example로 덮어씀 (위험)")
    parser.add_argument("--smoke-run", dest="smoke_run", action="store_true", help="bootstrap 이후 간단 smoke run 실행")
    parser.add_argument("--domain", default="Adult_Language_Education_KR", help="smoke run domain")
    parser.add_argument("--region", default="KR", help="smoke run region")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve() if args.project_root else _project_root_from_here()
    if not (project_root / "cmis_cli").exists():
        print(f"ERROR: invalid project_root: {project_root}")
        return 2

    print("CMIS Cursor bootstrap helper")
    print("- project_root:", project_root)

    # 1) venv
    py = Path(sys.executable)
    vpy = _venv_python(project_root)
    if not args.skip_venv:
        if not vpy.exists():
            _run([str(py), "-m", "venv", str(project_root / ".venv")], cwd=project_root)
        if not args.no_install:
            _run([str(vpy), "-m", "pip", "install", "-r", "requirements.txt"], cwd=project_root)
        py_to_use = vpy
    else:
        if not args.no_install:
            _run([str(py), "-m", "pip", "install", "-r", "requirements.txt"], cwd=project_root)
        py_to_use = py

    # 2) .env
    env_path = project_root / ".env"
    env_example = project_root / "env.example"
    if env_example.exists():
        if args.force_env or not env_path.exists():
            shutil.copyfile(str(env_example), str(env_path))
            print("- .env:", "overwritten" if args.force_env else "created")
        else:
            print("- .env: exists (skip)")
    else:
        print("- .env: env.example missing (skip)")

    # 3) bootstrap (no-env because we already handled .env above)
    bootstrap_cmd = [
        str(py_to_use),
        "-m",
        "cmis_cli",
        "cursor",
        "bootstrap",
        "--no-env",
    ]
    if args.force_env:
        bootstrap_cmd.append("--force-env")
    if args.smoke_run:
        bootstrap_cmd.extend(
            [
                "--smoke-run",
                "--domain",
                args.domain,
                "--region",
                args.region,
            ]
        )
    _run(bootstrap_cmd, cwd=project_root)

    print("OK: bootstrap completed")
    print("Next:")
    print(f"  {py_to_use} -m cmis_cli cursor ask \"<query>\" --domain {args.domain} --region {args.region}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

