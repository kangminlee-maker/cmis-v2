"""cache-manage 명령어

Evidence/Result 캐시 관리

2025-12-11: Workflow CLI Phase 2
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def cmd_cache_manage(args):
    """cache-manage 명령 실행

    Args:
        args: Argparse args
    """
    print("=" * 60)
    print("CMIS - Cache Management")
    print("=" * 60)
    print()

    from cmis_core.stores.sqlite_base import StoragePaths

    project_root = Path(args.project_root) if getattr(args, "project_root", None) else None
    paths = StoragePaths.resolve(project_root)

    if args.status:
        # 캐시 상태
        print("[캐시 상태]")
        print()

        # Evidence 캐시
        print("Evidence Cache:")
        print("  유형: EvidenceStore (Memory 기본 / SQLite 선택)")
        print(f"  SQLite 경로(legacy): {paths.evidence_cache_db_path}")
        print("  TTL: 기본 24시간(요청별 TTL 설정 가능)")
        print()

        # Snapshot 캐시
        print("Snapshot Cache:")
        print("  위치: WorldEngine.cache (인메모리)")
        print("  TTL: 1시간")
        print()

        # Result 캐시
        print("Result Cache:")
        print(f"  위치: {paths.results_dir}")
        print("  TTL: 1시간")
        print()

    elif args.clear:
        # 캐시 클리어
        cache_type = args.type or "all"

        print(f"[캐시 클리어: {cache_type}]")
        print()

        if cache_type in ["evidence", "all"]:
            print("Evidence 캐시 클리어...")
            try:
                p = Path(paths.evidence_cache_db_path)
                if p.exists():
                    p.unlink()
                    print(f"  [OK] 삭제됨: {p}")
                else:
                    print("  (캐시 파일 없음)")
            except Exception as e:
                print(f"  [WARN] 삭제 실패: {e}")

        if cache_type in ["snapshots", "all"]:
            print("Snapshot 캐시 클리어...")
            print("  (인메모리 캐시이므로, 실행 프로세스 재시작 또는 엔진 API 연동이 필요)")

        if cache_type in ["results", "all"]:
            print("Result 캐시 클리어...")
            cache_dir = Path(paths.results_dir)

            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                print(f"  [OK] 클리어됨: {cache_dir}")
            else:
                print(f"  (캐시 없음)")

        print()

    elif args.stats:
        # 캐시 통계
        print("[캐시 통계]")
        print()
        try:
            evidence_path = Path(paths.evidence_cache_db_path)
            if evidence_path.exists():
                size = evidence_path.stat().st_size
                print(f"- evidence_cache_db: {evidence_path} size_bytes={size}")
            else:
                print("- evidence_cache_db: (none)")
        except Exception as e:
            print(f"- evidence_cache_db: [WARN] {e}")

        try:
            results_dir = Path(paths.results_dir)
            if results_dir.exists():
                files = [p for p in results_dir.glob("*") if p.is_file()]
                print(f"- results_cache: {results_dir} files={len(files)}")
            else:
                print("- results_cache: (none)")
        except Exception as e:
            print(f"- results_cache: [WARN] {e}")
        print()

    else:
        print("사용법:")
        print("  cmis cache-manage --status [--project-root <path>]")
        print("  cmis cache-manage --clear [--type evidence|snapshots|results|all] [--project-root <path>]")
        print("  cmis cache-manage --stats [--project-root <path>]")


