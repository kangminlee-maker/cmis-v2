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

    if args.status:
        # 캐시 상태
        print("[캐시 상태]")
        print()

        # Evidence 캐시
        print("Evidence Cache:")
        print("  위치: evidence_store (SQLite)")
        print("  관리: EvidenceEngine")
        print("  TTL: 24시간")
        print()

        # Snapshot 캐시
        print("Snapshot Cache:")
        print("  위치: WorldEngine.cache (인메모리)")
        print("  TTL: 1시간")
        print()

        # Result 캐시
        print("Result Cache:")
        print("  위치: ~/.cmis/cache/results/")
        print("  TTL: 1시간")
        print()

    elif args.clear:
        # 캐시 클리어
        cache_type = args.type or "all"

        print(f"[캐시 클리어: {cache_type}]")
        print()

        if cache_type in ["evidence", "all"]:
            print("Evidence 캐시 클리어...")
            print("  → EvidenceEngine.cache.clear() 호출 필요")
            print("  (Phase 2: 엔진 통합)")

        if cache_type in ["snapshots", "all"]:
            print("Snapshot 캐시 클리어...")
            print("  → WorldEngine.cache.clear() 호출 필요")
            print("  (Phase 2: 엔진 통합)")

        if cache_type in ["results", "all"]:
            print("Result 캐시 클리어...")
            cache_dir = Path.home() / ".cmis" / "cache" / "results"

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
        print("Phase 2: 엔진 연동 후 구현 예정")
        print()

    else:
        print("사용법:")
        print("  cmis cache-manage --status")
        print("  cmis cache-manage --clear [--type evidence|snapshots|results|all]")
        print("  cmis cache-manage --stats")


