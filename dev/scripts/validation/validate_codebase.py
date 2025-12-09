"""UMIS v9 Codebase 무결성 종합 검증

검증 항목:
1. Python 문법 (모든 .py 파일)
2. Import 순환 참조
3. YAML 무결성
4. 테스트 실행
5. 타입 힌트 검증
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Set
import yaml


def check_python_syntax() -> Tuple[bool, List[str]]:
    """Python 파일 문법 검증"""
    print("=" * 60)
    print("1. Python 문법 검증")
    print("=" * 60)
    
    errors = []
    py_files = list(Path("umis_v9_core").glob("**/*.py"))
    py_files.extend(Path("umis_v9_cli").glob("**/*.py"))
    py_files.extend(Path("tests").glob("**/*.py"))
    
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                code = f.read()
                ast.parse(code)
        except SyntaxError as e:
            errors.append(f"❌ {py_file}: {e}")
    
    if errors:
        for e in errors:
            print(f"   {e}")
        return False, errors
    else:
        print(f"✅ {len(py_files)}개 Python 파일 문법 정상")
        return True, []


def check_imports() -> Tuple[bool, List[str]]:
    """Import 검증"""
    print("\n" + "=" * 60)
    print("2. Import 검증")
    print("=" * 60)
    
    errors = []
    
    # 모든 모듈 import 시도
    modules = [
        "umis_v9_core.types",
        "umis_v9_core.graph",
        "umis_v9_core.config",
        "umis_v9_core.world_engine",
        "umis_v9_core.value_engine",
        "umis_v9_core.pattern_engine",
        "umis_v9_core.workflow",
        "umis_v9_core.report_generator",
        "umis_v9_core.evidence.dart_connector",
    ]
    
    for module_name in modules:
        try:
            __import__(module_name)
        except ImportError as e:
            errors.append(f"❌ {module_name}: {e}")
        except Exception as e:
            errors.append(f"⚠️  {module_name}: {e}")
    
    if errors:
        for e in errors:
            print(f"   {e}")
        return False, errors
    else:
        print(f"✅ {len(modules)}개 모듈 import 정상")
        return True, []


def check_yaml_files() -> Tuple[bool, List[str]]:
    """YAML 파일 검증"""
    print("\n" + "=" * 60)
    print("3. YAML 무결성 검증")
    print("=" * 60)
    
    errors = []
    yaml_files = [
        "umis_v9.yaml",
        "domain_registry.yaml",
        "umis_v9_process_phases.yaml",
        "umis_v9_agent_protocols.yaml",
        "umis_v9_validation_gates.yaml",
    ]
    
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"❌ {yaml_file}: {e}")
        except FileNotFoundError:
            errors.append(f"⚠️  {yaml_file}: 파일 없음")
    
    if errors:
        for e in errors:
            print(f"   {e}")
        return False, errors
    else:
        print(f"✅ {len([f for f in yaml_files if Path(f).exists()])}개 YAML 파일 정상")
        return True, []


def check_critical_files() -> Tuple[bool, List[str]]:
    """필수 파일 존재 확인"""
    print("\n" + "=" * 60)
    print("4. 필수 파일 존재 확인")
    print("=" * 60)
    
    errors = []
    required_files = [
        "umis_v9.yaml",
        "domain_registry.yaml",
        "seeds/Adult_Language_Education_KR_reality_seed.yaml",
        "umis_v9_core/__init__.py",
        "umis_v9_core/types.py",
        "umis_v9_core/graph.py",
        "umis_v9_core/config.py",
        "umis_v9_core/world_engine.py",
        "umis_v9_core/value_engine.py",
        "umis_v9_core/pattern_engine.py",
        "umis_v9_core/workflow.py",
        "umis_v9_core/evidence/dart_connector.py",
        "umis_v9_cli/__main__.py",
        "requirements.txt",
        "README_v1.md",
    ]
    
    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
            errors.append(f"❌ 필수 파일 없음: {file_path}")
    
    if errors:
        for e in errors:
            print(f"   {e}")
        return False, errors
    else:
        print(f"✅ {len(required_files)}개 필수 파일 모두 존재")
        return True, []


def check_type_hints() -> Tuple[bool, List[str]]:
    """타입 힌트 기본 검증"""
    print("\n" + "=" * 60)
    print("5. 타입 힌트 검증")
    print("=" * 60)
    
    warnings = []
    core_files = list(Path("umis_v9_core").glob("*.py"))
    
    for py_file in core_files:
        if py_file.name == "__init__.py":
            continue
        
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # from __future__ import annotations 확인
        if "from __future__ import annotations" not in content:
            warnings.append(f"⚠️  {py_file.name}: future annotations 없음")
        
        # typing import 확인
        if "from typing import" not in content and "import typing" not in content:
            if "def " in content:  # 함수가 있는데 typing이 없으면
                warnings.append(f"⚠️  {py_file.name}: typing import 없음")
    
    if warnings:
        for w in warnings:
            print(f"   {w}")
    
    print(f"✅ 타입 힌트 기본 검증 완료 ({len(warnings)}개 경고)")
    return True, warnings


def run_tests() -> Tuple[bool, str]:
    """테스트 실행"""
    print("\n" + "=" * 60)
    print("6. 테스트 실행")
    print("=" * 60)
    
    import subprocess
    
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        # 마지막 줄에서 통과 개수 추출
        last_line = result.stdout.strip().split('\n')[-1]
        print(f"✅ {last_line}")
        return True, last_line
    else:
        print(f"❌ 테스트 실패")
        print(result.stdout)
        return False, result.stdout


def main():
    """메인 검증 함수"""
    print("\n" + "=" * 60)
    print("UMIS v9 Codebase 무결성 종합 검증")
    print("=" * 60)
    print()
    
    all_passed = True
    summary = []
    
    # 1. Python 문법
    passed, errors = check_python_syntax()
    summary.append(("Python 문법", passed))
    if not passed:
        all_passed = False
    
    # 2. Import
    passed, errors = check_imports()
    summary.append(("Import", passed))
    if not passed:
        all_passed = False
    
    # 3. YAML
    passed, errors = check_yaml_files()
    summary.append(("YAML", passed))
    if not passed:
        all_passed = False
    
    # 4. 필수 파일
    passed, errors = check_critical_files()
    summary.append(("필수 파일", passed))
    if not passed:
        all_passed = False
    
    # 5. 타입 힌트
    passed, warnings = check_type_hints()
    summary.append(("타입 힌트", passed))
    
    # 6. 테스트
    passed, output = run_tests()
    summary.append(("테스트", passed))
    if not passed:
        all_passed = False
    
    # 최종 요약
    print("\n" + "=" * 60)
    print("최종 결과")
    print("=" * 60)
    
    for check_name, passed in summary:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {check_name}")
    
    print()
    
    if all_passed:
        print("🎉 무결성 검증 완료! 모든 검사 통과")
        return 0
    else:
        print("❌ 일부 검사 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
