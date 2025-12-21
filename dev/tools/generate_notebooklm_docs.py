"""NotebookLM용 고품질 문서 자동 생성 스크립트

CMIS 코드베이스를 분석하여 NotebookLM이 학습할 수 있는 마크다운 문서를 생성합니다.
- Python 파일: AST 파싱, docstring/타입 힌트 추출
- YAML 파일: 구조 파싱 및 설명
- 계층적 문서 구조: 9개 핵심 문서 생성

Usage:
    python dev/tools/generate_notebooklm_docs.py

Output:
    dev/docs/notebooklm_export/*.md (9개 파일)
"""

import ast
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FunctionInfo:
    """함수 정보"""
    name: str
    docstring: Optional[str]
    signature: str
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ClassInfo:
    """클래스 정보"""
    name: str
    docstring: Optional[str]
    bases: List[str]
    methods: List[FunctionInfo] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ModuleInfo:
    """모듈 정보"""
    path: str
    docstring: Optional[str]
    imports: List[str] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)


class PythonAnalyzer:
    """Python 코드 분석기 (AST 기반)"""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def analyze_file(self, filepath: Path) -> Optional[ModuleInfo]:
        """Python 파일 분석"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source, filename=str(filepath))
            module_doc = ast.get_docstring(tree)

            # Imports 추출
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"from {module} import {alias.name}")

            # 최상위 클래스/함수만 추출
            classes = []
            functions = []

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    classes.append(self._extract_class(node))
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    functions.append(self._extract_function(node))

            return ModuleInfo(
                path=str(filepath.relative_to(self.repo_root)),
                docstring=module_doc,
                imports=imports[:10],  # 상위 10개만
                classes=classes,
                functions=functions
            )

        except Exception as e:
            print(f"Warning: Failed to parse {filepath}: {e}")
            return None

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """클래스 정보 추출"""
        bases = [self._get_name(base) for base in node.bases]
        methods = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(item))

        return ClassInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            bases=bases,
            methods=methods,
            line_number=node.lineno
        )

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        """함수 정보 추출"""
        # 시그니처 생성
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_name(arg.annotation)}"
            args.append(arg_str)

        return_type = ""
        if node.returns:
            return_type = f" -> {self._get_name(node.returns)}"

        signature = f"def {node.name}({', '.join(args)}){return_type}"

        decorators = [self._get_name(dec) for dec in node.decorator_list]

        return FunctionInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            signature=signature,
            decorators=decorators,
            line_number=node.lineno
        )

    def _get_name(self, node) -> str:
        """AST 노드에서 이름 추출"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        else:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)


class YAMLAnalyzer:
    """YAML 설정 파일 분석기"""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def analyze_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """YAML 파일 파싱"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return {
                'path': str(filepath.relative_to(self.repo_root)),
                'data': data
            }
        except Exception as e:
            print(f"Warning: Failed to parse {filepath}: {e}")
            return None


class DocumentGenerator:
    """마크다운 문서 생성기"""

    def __init__(self, repo_root: Path, output_dir: Path):
        self.repo_root = repo_root
        self.output_dir = output_dir
        self.py_analyzer = PythonAnalyzer(repo_root)
        self.yaml_analyzer = YAMLAnalyzer(repo_root)

    def generate_all(self):
        """모든 문서 생성"""
        print("🚀 NotebookLM 학습용 문서 생성 시작...")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 문서 생성 순서
        docs = [
            ("00_CMIS_System_Overview.md", self.generate_system_overview),
            ("01_Core_Types_and_Schemas.md", self.generate_types_and_schemas),
            ("02_Core_Engines_Implementation.md", self.generate_core_engines),
            ("03_Evidence_System_Detail.md", self.generate_evidence_system),
            ("04_Orchestration_Implementation.md", self.generate_orchestration),
            ("05_Search_Strategy_v3.md", self.generate_search_v3),
            ("06_CLI_Commands_Reference.md", self.generate_cli_commands),
            ("07_Configuration_Reference.md", self.generate_configuration),
            ("08_Stores_and_Persistence.md", self.generate_stores),
            ("09_Integration_Guide.md", self.generate_integration_guide),
        ]

        for filename, generator_func in docs:
            print(f"📝 생성 중: {filename}")
            content = generator_func()
            output_path = self.output_dir / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 완료: {output_path}")

        print(f"\n🎉 총 {len(docs)}개 문서 생성 완료!")
        print(f"📁 출력 디렉토리: {self.output_dir}")

    def generate_system_overview(self) -> str:
        """시스템 전체 개요"""
        content = [
            "# CMIS 시스템 전체 개요",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: NotebookLM 학습용 CMIS 시스템 전체 구조 및 철학",
            "",
            "---",
            "",
            "## 1. CMIS란?",
            "",
            "**CMIS (Contextual Market Intelligence System)**는 시장 분석을 위한 Evidence-first 시스템입니다.",
            "",
            "### 핵심 철학",
            "",
            "1. **Evidence-first, Prior-last**: 증거 우선, 가정 최소화",
            "2. **Substrate = SSoT**: Stores + Graphs + Lineage가 단일 진실 공급원",
            "3. **Model → Number**: 구조 먼저 정의, 숫자는 나중",
            "4. **Graph-of-Graphs**: Reality/Pattern/Value/Decision 그래프 분리",
            "5. **Objective-Oriented**: 목표 중심, 프로세스 동적 조정",
            "6. **Agent = Persona + Workflow**: 엔진은 도구, Agent는 워크플로우",
            "",
            "---",
            "",
            "## 2. 시스템 아키텍처",
            "",
        ]

        # cmis.yaml 구조 읽기
        cmis_yaml_path = self.repo_root / "cmis.yaml"
        if cmis_yaml_path.exists():
            cmis_data = self.yaml_analyzer.analyze_file(cmis_yaml_path)
            if cmis_data:
                content.extend([
                    "### 2.1 레지스트리 구조 (cmis.yaml)",
                    "",
                    "```yaml",
                    "# 주요 섹션:",
                ])

                data = cmis_data['data']
                if 'registries' in data:
                    for reg_type, reg_data in data['registries'].items():
                        if isinstance(reg_data, dict):
                            count = len(reg_data)
                            content.append(f"# - {reg_type}: {count}개 등록")

                content.extend([
                    "```",
                    "",
                ])

        # 폴더 구조
        content.extend([
            "### 2.2 디렉토리 구조",
            "",
            "```",
            "cmis/",
            "├── cmis.yaml              # 중앙 레지스트리",
            "├── schemas/               # 타입 시스템",
            "├── libraries/             # 도메인 지식",
            "├── config/                # 런타임 설정",
            "├── cmis_core/             # 9개 엔진 (핵심)",
            "├── cmis_cli/              # CLI 인터페이스",
            "└── dev/                   # 개발 자료",
            "```",
            "",
            "---",
            "",
            "## 3. 9개 핵심 엔진",
            "",
        ])

        # 엔진 목록
        engines = [
            ("belief_engine.py", "BeliefEngine", "Prior 관리 및 Bayesian 업데이트"),
            ("world_engine.py", "WorldEngine", "Reality Graph 구성 (Actor/Money/Event)"),
            ("pattern_engine_v2.py", "PatternEngine", "패턴 매칭 및 Context 학습"),
            ("value_engine.py", "ValueEngine", "가치 평가 및 밸류에이션"),
            ("strategy_engine.py", "StrategyEngine", "전략 생성 및 평가"),
            ("learning_engine.py", "LearningEngine", "학습 및 피드백 루프"),
            ("evidence_engine.py", "EvidenceEngine", "증거 수집 및 검증"),
            ("policy_engine.py", "PolicyEngine", "정책 적용 및 제약 관리"),
            ("workflow.py", "WorkflowOrchestrator", "워크플로우 실행 및 조정"),
        ]

        for filename, engine_name, description in engines:
            file_path = self.repo_root / "cmis_core" / filename
            if file_path.exists():
                module = self.py_analyzer.analyze_file(file_path)
                if module and module.docstring:
                    content.append(f"### 3.{engines.index((filename, engine_name, description)) + 1} {engine_name}")
                    content.append(f"**파일**: `{filename}`")
                    content.append(f"**역할**: {description}")
                    content.append("")
                    content.append(f"```")
                    content.append(module.docstring.strip())
                    content.append("```")
                    content.append("")

        content.extend([
            "---",
            "",
            "## 4. 데이터 흐름",
            "",
            "```mermaid",
            "graph TB",
            "    A[사용자 질의] --> B[Workflow Orchestrator]",
            "    B --> C[Evidence Engine]",
            "    C --> D[World Engine]",
            "    D --> E[Pattern Engine]",
            "    E --> F[Value Engine]",
            "    F --> G[Strategy Engine]",
            "    G --> H[Learning Engine]",
            "    H --> I[결과 반환]",
            "    ",
            "    B -.-> J[Policy Engine]",
            "    J -.-> C",
            "    J -.-> D",
            "```",
            "",
            "---",
            "",
            "## 5. 핵심 개념",
            "",
            "### 5.1 Reality Graph",
            "- Actor, MoneyFlow, Event, Resource, Contract 노드",
            "- 실제 시장 구조를 그래프로 표현",
            "",
            "### 5.2 Pattern Graph",
            "- 비즈니스 패턴 (예: Marketplace, Subscription)",
            "- Context와 Pattern 매칭",
            "",
            "### 5.3 Value Graph",
            "- Metric → Valuation → Outcome",
            "- 불확실성 전파 (Monte Carlo)",
            "",
            "### 5.4 Decision Graph",
            "- Goal → Task → Verification",
            "- 동적 재계획 (Reconcile Loop)",
            "",
            "---",
            "",
            "## 6. 실행 모드",
            "",
            "### CLI 인터페이스",
            "",
            "```bash",
            "# 구조 분석",
            "python -m cmis_cli structure-analysis --domain DOMAIN --actor ACTOR",
            "",
            "# 기회 발견",
            "python -m cmis_cli opportunity-discovery --context CONTEXT",
            "",
            "# 워크플로우 실행",
            "python -m cmis_cli workflow-run --workflow-id WF_ID",
            "```",
            "",
            "---",
            "",
            "이 문서는 CMIS 시스템의 전체 개요를 제공합니다.",
            "상세 구현은 후속 문서(01~09)를 참조하세요.",
            "",
        ])

        return "\n".join(content)

    def generate_types_and_schemas(self) -> str:
        """타입 및 스키마 문서"""
        content = [
            "# CMIS Core Types 및 스키마",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: CMIS 시스템의 모든 데이터 타입 및 스키마 정의",
            "",
            "---",
            "",
            "## 1. Core Types (types.py)",
            "",
        ]

        # types.py 분석
        types_path = self.repo_root / "cmis_core" / "types.py"
        if types_path.exists():
            module = self.py_analyzer.analyze_file(types_path)
            if module:
                content.append(f"**파일**: `{module.path}`")
                content.append("")
                if module.docstring:
                    content.append(f"```")
                    content.append(module.docstring.strip())
                    content.append("```")
                    content.append("")

                # 주요 클래스 문서화
                content.append("### 1.1 주요 데이터 클래스")
                content.append("")

                for cls in module.classes[:30]:  # 상위 30개 클래스
                    content.append(f"#### `{cls.name}`")
                    content.append("")
                    if cls.docstring:
                        content.append(f"**설명**: {cls.docstring.strip()}")
                        content.append("")
                    if cls.bases:
                        content.append(f"**상속**: `{', '.join(cls.bases)}`")
                        content.append("")

                    # 주요 메서드 (최대 5개)
                    if cls.methods:
                        content.append("**주요 메서드**:")
                        content.append("")
                        for method in cls.methods[:5]:
                            if not method.name.startswith('_'):
                                content.append(f"- `{method.signature}`")
                                if method.docstring:
                                    # 첫 줄만
                                    first_line = method.docstring.split('\n')[0].strip()
                                    content.append(f"  - {first_line}")
                        content.append("")

        content.extend([
            "---",
            "",
            "## 2. 스키마 정의 (schemas/)",
            "",
        ])

        # schemas/ 디렉토리의 YAML 파일들
        schemas_dir = self.repo_root / "schemas"
        if schemas_dir.exists():
            for yaml_file in sorted(schemas_dir.glob("*.yaml")):
                schema_data = self.yaml_analyzer.analyze_file(yaml_file)
                if schema_data:
                    content.append(f"### 2.{list(schemas_dir.glob('*.yaml')).index(yaml_file) + 1} {yaml_file.name}")
                    content.append("")
                    content.append(f"**경로**: `{schema_data['path']}`")
                    content.append("")

                    # YAML 구조 요약
                    data = schema_data['data']
                    if data:
                        content.append("**구조**:")
                        content.append("")
                        content.append("```yaml")
                        # 최상위 키만 표시
                        for key in data.keys():
                            if isinstance(data[key], dict):
                                content.append(f"{key}:")
                                # 2단계 깊이까지만
                                for subkey in list(data[key].keys())[:5]:
                                    content.append(f"  {subkey}: ...")
                                if len(data[key]) > 5:
                                    content.append(f"  # ... ({len(data[key]) - 5}개 더)")
                            elif isinstance(data[key], list):
                                content.append(f"{key}: [{len(data[key])}개 항목]")
                            else:
                                content.append(f"{key}: {data[key]}")
                        content.append("```")
                        content.append("")

        content.extend([
            "---",
            "",
            "이 문서는 CMIS의 모든 타입 정의를 포함합니다.",
            "",
        ])

        return "\n".join(content)

    def generate_core_engines(self) -> str:
        """핵심 엔진 구현 상세"""
        content = [
            "# CMIS 핵심 엔진 구현 상세",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: 9개 핵심 엔진의 구현 세부사항",
            "",
            "---",
            "",
        ]

        engines = [
            "belief_engine.py",
            "prior_manager.py",
            "belief_updater.py",
            "uncertainty_propagator.py",
            "world_engine.py",
            "pattern_engine_v2.py",
            "pattern_matcher.py",
            "pattern_learner.py",
            "value_engine.py",
            "strategy_engine.py",
            "strategy_generator.py",
            "strategy_evaluator.py",
            "learning_engine.py",
            "learning_policy.py",
            "evidence_engine.py",
            "policy_engine.py",
            "workflow.py",
        ]

        for idx, engine_file in enumerate(engines, 1):
            file_path = self.repo_root / "cmis_core" / engine_file
            if file_path.exists():
                module = self.py_analyzer.analyze_file(file_path)
                if module:
                    content.append(f"## {idx}. {engine_file}")
                    content.append("")
                    content.append(f"**경로**: `{module.path}`")
                    content.append("")

                    if module.docstring:
                        content.append("### 모듈 설명")
                        content.append("")
                        content.append("```")
                        content.append(module.docstring.strip())
                        content.append("```")
                        content.append("")

                    # 주요 클래스
                    if module.classes:
                        content.append("### 주요 클래스")
                        content.append("")

                        for cls in module.classes[:3]:  # 상위 3개
                            content.append(f"#### `{cls.name}`")
                            content.append("")
                            if cls.docstring:
                                content.append(f"{cls.docstring.strip()}")
                                content.append("")

                            # 주요 메서드
                            public_methods = [m for m in cls.methods if not m.name.startswith('_')]
                            if public_methods:
                                content.append("**Public 메서드**:")
                                content.append("")
                                for method in public_methods[:5]:
                                    content.append(f"```python")
                                    content.append(method.signature)
                                    content.append("```")
                                    if method.docstring:
                                        first_line = method.docstring.split('\n')[0].strip()
                                        content.append(f"{first_line}")
                                    content.append("")

                    # 주요 함수
                    if module.functions:
                        content.append("### 주요 함수")
                        content.append("")
                        for func in module.functions[:3]:
                            content.append(f"```python")
                            content.append(func.signature)
                            content.append("```")
                            if func.docstring:
                                content.append(f"{func.docstring.strip()}")
                            content.append("")

                    content.append("---")
                    content.append("")

        return "\n".join(content)

    def generate_evidence_system(self) -> str:
        """Evidence 시스템 상세"""
        content = [
            "# Evidence 시스템 구현 상세",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: Evidence 수집, 검증, 저장 시스템",
            "",
            "---",
            "",
            "## 1. Evidence Engine",
            "",
        ]

        # Evidence Engine
        evidence_engine_path = self.repo_root / "cmis_core" / "evidence_engine.py"
        if evidence_engine_path.exists():
            module = self.py_analyzer.analyze_file(evidence_engine_path)
            if module:
                self._add_module_detail(content, module)

        content.extend([
            "---",
            "",
            "## 2. Evidence Sources",
            "",
        ])

        # Evidence sources
        evidence_dir = self.repo_root / "cmis_core" / "evidence"
        if evidence_dir.exists():
            for py_file in sorted(evidence_dir.glob("*.py")):
                if py_file.name != "__init__.py":
                    module = self.py_analyzer.analyze_file(py_file)
                    if module:
                        content.append(f"### {py_file.stem}")
                        content.append("")
                        if module.docstring:
                            content.append(f"{module.docstring.strip()}")
                            content.append("")

                        # 주요 클래스 1개만
                        if module.classes:
                            cls = module.classes[0]
                            content.append(f"**클래스**: `{cls.name}`")
                            content.append("")
                            if cls.docstring:
                                content.append(f"{cls.docstring.strip()}")
                                content.append("")

        content.extend([
            "---",
            "",
            "## 3. Evidence 관련 유틸리티",
            "",
        ])

        utils = [
            "evidence_builder.py",
            "evidence_quality.py",
            "evidence_validation.py",
            "evidence_store.py",
            "evidence_batch.py",
            "evidence_parallel.py",
            "evidence_retry.py",
        ]

        for util_file in utils:
            file_path = self.repo_root / "cmis_core" / util_file
            if file_path.exists():
                module = self.py_analyzer.analyze_file(file_path)
                if module:
                    content.append(f"### {util_file}")
                    content.append("")
                    if module.docstring:
                        content.append(f"{module.docstring.strip()}")
                        content.append("")

        return "\n".join(content)

    def generate_orchestration(self) -> str:
        """Orchestration 구현 상세"""
        content = [
            "# Orchestration Kernel 구현",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: Reconcile Loop 기반 실행 관리",
            "",
            "---",
            "",
            "## 개요",
            "",
            "CMIS Orchestration Kernel은 Kubernetes의 Reconcile Loop 패턴을 차용하여",
            "Goal → Task → Verification → Replanning의 동적 실행을 관리합니다.",
            "",
            "---",
            "",
        ]

        orchestration_dir = self.repo_root / "cmis_core" / "orchestration"
        if orchestration_dir.exists():
            files = [
                "kernel.py",
                "goal.py",
                "task.py",
                "executor.py",
                "verifier.py",
                "replanner.py",
                "ledgers.py",
                "governor.py",
            ]

            for idx, filename in enumerate(files, 1):
                file_path = orchestration_dir / filename
                if file_path.exists():
                    module = self.py_analyzer.analyze_file(file_path)
                    if module:
                        content.append(f"## {idx}. {filename}")
                        content.append("")
                        self._add_module_detail(content, module)
                        content.append("---")
                        content.append("")

        return "\n".join(content)

    def generate_search_v3(self) -> str:
        """Search v3 구현 상세"""
        content = [
            "# Search Strategy v3 구현",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: 3단계 검색 전략 (SERP → Document → Synthesis)",
            "",
            "---",
            "",
            "## 1. Search v3 아키텍처",
            "",
            "```",
            "Query → SERP Search → Candidate Extract → Document Fetch → Synthesize → Evidence",
            "```",
            "",
            "---",
            "",
        ]

        search_dir = self.repo_root / "cmis_core" / "search_v3"
        if search_dir.exists():
            for py_file in sorted(search_dir.glob("*.py")):
                if py_file.name != "__init__.py":
                    module = self.py_analyzer.analyze_file(py_file)
                    if module:
                        content.append(f"## {py_file.stem}")
                        content.append("")
                        self._add_module_detail(content, module)
                        content.append("---")
                        content.append("")

        return "\n".join(content)

    def generate_cli_commands(self) -> str:
        """CLI 명령어 레퍼런스"""
        content = [
            "# CMIS CLI 명령어 레퍼런스",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: 모든 CLI 명령어 사용법",
            "",
            "---",
            "",
        ]

        cli_dir = self.repo_root / "cmis_cli" / "commands"
        if cli_dir.exists():
            for py_file in sorted(cli_dir.glob("*.py")):
                if py_file.name != "__init__.py":
                    module = self.py_analyzer.analyze_file(py_file)
                    if module:
                        content.append(f"## {py_file.stem}")
                        content.append("")
                        self._add_module_detail(content, module)
                        content.append("---")
                        content.append("")

        return "\n".join(content)

    def generate_configuration(self) -> str:
        """설정 파일 레퍼런스"""
        content = [
            "# CMIS 설정 레퍼런스",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: 모든 YAML 설정 파일 상세",
            "",
            "---",
            "",
        ]

        config_dir = self.repo_root / "config"
        if config_dir.exists():
            # 루트 YAML들
            for yaml_file in sorted(config_dir.glob("*.yaml")):
                self._add_yaml_detail(content, yaml_file)

            # 서브디렉토리
            for subdir in ["archetypes", "sources"]:
                subdir_path = config_dir / subdir
                if subdir_path.exists():
                    content.append(f"## {subdir}/")
                    content.append("")
                    for yaml_file in sorted(subdir_path.glob("*.yaml")):
                        self._add_yaml_detail(content, yaml_file)

        return "\n".join(content)

    def generate_stores(self) -> str:
        """Stores 및 영속화"""
        content = [
            "# CMIS Stores 및 영속화",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: 데이터 저장 및 관리 시스템",
            "",
            "---",
            "",
        ]

        stores_dir = self.repo_root / "cmis_core" / "stores"
        if stores_dir.exists():
            for py_file in sorted(stores_dir.glob("*.py")):
                if py_file.name != "__init__.py":
                    module = self.py_analyzer.analyze_file(py_file)
                    if module:
                        content.append(f"## {py_file.stem}")
                        content.append("")
                        self._add_module_detail(content, module)
                        content.append("---")
                        content.append("")

        # Brownfield stores
        brownfield_dir = self.repo_root / "cmis_core" / "brownfield"
        if brownfield_dir.exists():
            content.append("## Brownfield Stores")
            content.append("")
            for py_file in sorted(brownfield_dir.glob("*_store.py")):
                module = self.py_analyzer.analyze_file(py_file)
                if module:
                    content.append(f"### {py_file.stem}")
                    content.append("")
                    if module.docstring:
                        content.append(f"{module.docstring.strip()}")
                        content.append("")

        return "\n".join(content)

    def generate_integration_guide(self) -> str:
        """통합 가이드"""
        content = [
            "# CMIS 통합 가이드",
            "",
            f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**목적**: CMIS 시스템 통합 및 사용 예제",
            "",
            "---",
            "",
            "## 1. 기본 사용 흐름",
            "",
            "### 1.1 환경 설정",
            "",
            "```bash",
            "# 의존성 설치",
            "pip install -r requirements.txt",
            "",
            "# 환경 변수 설정",
            "cp env.example .env",
            "vi .env",
            "```",
            "",
            "### 1.2 Cursor Agent 온보딩",
            "",
            "```bash",
            "# 초기 환경 점검",
            "python3 -m cmis_cli cursor bootstrap",
            "",
            "# 시스템 진단",
            "python3 -m cmis_cli cursor doctor",
            "",
            "# 기능 목록 확인",
            "python3 -m cmis_cli cursor manifest",
            "```",
            "",
            "---",
            "",
            "## 2. 주요 워크플로우",
            "",
            "### 2.1 구조 분석",
            "",
            "```bash",
            "python -m cmis_cli structure-analysis \\",
            "  --domain \"Adult_Language_KR\" \\",
            "  --actor \"Ringle\" \\",
            "  --output analysis_result.json",
            "```",
            "",
            "### 2.2 기회 발견",
            "",
            "```bash",
            "python -m cmis_cli opportunity-discovery \\",
            "  --context \"context.yaml\" \\",
            "  --output opportunities.json",
            "```",
            "",
            "---",
            "",
            "## 3. 프로그래밍 인터페이스",
            "",
            "### 3.1 기본 사용",
            "",
            "```python",
            "from cmis_core import (",
            "    WorldEngine,",
            "    EvidenceEngine,",
            "    PatternEngine,",
            "    ValueEngine,",
            ")",
            "",
            "# Evidence 수집",
            "evidence_engine = EvidenceEngine()",
            "evidence = evidence_engine.collect(",
            "    query=\"Ringle revenue 2024\",",
            "    sources=[\"dart\", \"news\"]",
            ")",
            "",
            "# Reality Graph 구성",
            "world_engine = WorldEngine()",
            "reality_graph = world_engine.build_reality(",
            "    domain=\"Adult_Language_KR\",",
            "    evidence=evidence",
            ")",
            "",
            "# Pattern 매칭",
            "pattern_engine = PatternEngine()",
            "matched_patterns = pattern_engine.match(",
            "    reality_graph=reality_graph",
            ")",
            "",
            "# Value 평가",
            "value_engine = ValueEngine()",
            "valuation = value_engine.evaluate(",
            "    reality_graph=reality_graph,",
            "    patterns=matched_patterns",
            ")",
            "```",
            "",
            "---",
            "",
            "## 4. 데이터 모델",
            "",
            "### 4.1 Reality Graph",
            "",
            "```python",
            "from cmis_core.types import Node, Edge, RealityGraph",
            "",
            "# Actor 노드",
            "actor = Node(",
            "    id=\"actor-ringle\",",
            "    type=\"actor\",",
            "    data={",
            "        \"name\": \"Ringle\",",
            "        \"domain\": \"Adult_Language_KR\"",
            "    }",
            ")",
            "",
            "# MoneyFlow 노드",
            "revenue_flow = Node(",
            "    id=\"flow-subscription-revenue\",",
            "    type=\"money_flow\",",
            "    data={",
            "        \"amount\": {\"value\": 5000000, \"currency\": \"KRW\"}",
            "    }",
            ")",
            "",
            "# Edge",
            "edge = Edge(",
            "    type=\"actor_receives_money\",",
            "    source=\"actor-customer\",",
            "    target=\"actor-ringle\",",
            "    data={\"flow_id\": \"flow-subscription-revenue\"}",
            ")",
            "```",
            "",
            "---",
            "",
            "## 5. 확장 및 커스터마이징",
            "",
            "### 5.1 커스텀 Evidence Source",
            "",
            "```python",
            "from cmis_core.evidence.base_search_source import BaseSearchSource",
            "",
            "class CustomSource(BaseSearchSource):",
            "    def search(self, query: str) -> List[SearchResult]:",
            "        # 커스텀 검색 로직",
            "        pass",
            "```",
            "",
            "### 5.2 커스텀 Pattern",
            "",
            "```yaml",
            "# libraries/patterns/custom_pattern.yaml",
            "pattern_id: \"PATTERN-Custom\"",
            "name: \"Custom Business Pattern\"",
            "description: \"커스텀 비즈니스 패턴\"",
            "",
            "structure:",
            "  actors:",
            "    - role: provider",
            "      count: 1",
            "  money_flows:",
            "    - type: subscription",
            "      direction: customer_to_provider",
            "```",
            "",
            "---",
            "",
            "이 문서는 CMIS 시스템의 통합 가이드를 제공합니다.",
            "",
        ]

        return "\n".join(content)

    def _add_module_detail(self, content: List[str], module: ModuleInfo):
        """모듈 상세 정보 추가"""
        if module.docstring:
            content.append("### 모듈 설명")
            content.append("")
            content.append("```")
            content.append(module.docstring.strip())
            content.append("```")
            content.append("")

        # 주요 클래스
        if module.classes:
            content.append("### 주요 클래스")
            content.append("")
            for cls in module.classes[:2]:
                content.append(f"#### `{cls.name}`")
                content.append("")
                if cls.docstring:
                    content.append(f"{cls.docstring.strip()}")
                    content.append("")

                public_methods = [m for m in cls.methods if not m.name.startswith('_')]
                if public_methods:
                    content.append("**Public 메서드**:")
                    content.append("")
                    for method in public_methods[:3]:
                        content.append(f"```python")
                        content.append(method.signature)
                        content.append("```")
                        if method.docstring:
                            first_line = method.docstring.split('\n')[0].strip()
                            content.append(f"{first_line}")
                        content.append("")

    def _add_yaml_detail(self, content: List[str], yaml_path: Path):
        """YAML 파일 상세 정보 추가"""
        yaml_data = self.yaml_analyzer.analyze_file(yaml_path)
        if yaml_data:
            content.append(f"### {yaml_path.name}")
            content.append("")
            content.append(f"**경로**: `{yaml_data['path']}`")
            content.append("")

            data = yaml_data['data']
            if data:
                content.append("```yaml")
                # 전체 YAML 출력 (간소화)
                self._format_yaml_recursive(content, data, indent=0, max_depth=3)
                content.append("```")
                content.append("")

    def _format_yaml_recursive(self, content: List[str], data: Any, indent: int = 0, max_depth: int = 3):
        """YAML 데이터를 재귀적으로 포맷팅"""
        if indent >= max_depth:
            return

        prefix = "  " * indent

        if isinstance(data, dict):
            for key, value in list(data.items())[:10]:  # 최대 10개 항목
                if isinstance(value, (dict, list)):
                    content.append(f"{prefix}{key}:")
                    self._format_yaml_recursive(content, value, indent + 1, max_depth)
                else:
                    content.append(f"{prefix}{key}: {value}")
            if len(data) > 10:
                content.append(f"{prefix}# ... ({len(data) - 10}개 더)")

        elif isinstance(data, list):
            for item in data[:5]:  # 최대 5개 항목
                if isinstance(item, (dict, list)):
                    content.append(f"{prefix}-")
                    self._format_yaml_recursive(content, item, indent + 1, max_depth)
                else:
                    content.append(f"{prefix}- {item}")
            if len(data) > 5:
                content.append(f"{prefix}# ... ({len(data) - 5}개 더)")


def main():
    """메인 실행 함수"""
    repo_root = Path(__file__).resolve().parent.parent.parent
    output_dir = repo_root / "dev" / "docs" / "notebooklm_export"

    print(f"📁 Repo Root: {repo_root}")
    print(f"📁 Output Dir: {output_dir}")
    print()

    generator = DocumentGenerator(repo_root, output_dir)
    generator.generate_all()

    print()
    print("=" * 60)
    print("NotebookLM에 다음 파일들을 업로드하세요:")
    print("=" * 60)
    for md_file in sorted(output_dir.glob("*.md")):
        print(f"  - {md_file.name}")
    print("=" * 60)


if __name__ == "__main__":
    main()

