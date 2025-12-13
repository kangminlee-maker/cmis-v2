"""report-generate 명령어

분석 결과를 보고서로 변환 (Lineage 포함)

2025-12-11: Workflow CLI Phase 2
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cmis_cli.formatters import format_markdown


def cmd_report_generate(args):
    """report-generate 명령 실행

    Args:
        args: Argparse args
    """
    print("=" * 60)
    print("CMIS - Report Generate")
    print("=" * 60)
    print()

    # 입력 파일
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"[ERROR] 입력 파일 없음: {input_path}")
        return

    # 결과 로딩
    with open(input_path, 'r', encoding='utf-8') as f:
        result = json.load(f)

    print(f"입력: {input_path}")
    print(f"템플릿: {args.template}")
    print(f"형식: {args.format}")
    print()

    # 템플릿 적용
    if args.template == "structure_analysis":
        # Markdown 생성
        markdown = format_markdown(
            result,
            include_lineage=args.include_lineage
        )

        # 출력
        if args.output:
            output_path = Path(args.output)

            if args.format == "markdown":
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown)

                print(f"[OK] Markdown 저장: {output_path}")

            elif args.format == "html":
                # Markdown → HTML
                try:
                    import markdown2
                    html = markdown2.markdown(markdown)

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(f"<html><body>{html}</body></html>")

                    print(f"[OK] HTML 저장: {output_path}")

                except ImportError:
                    print("[WARN] markdown2 필요: pip install markdown2")
                    print("Markdown 저장...")

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(markdown)
        else:
            # Console 출력
            print(markdown)
    else:
        print(f"[ERROR] 알 수 없는 템플릿: {args.template}")


