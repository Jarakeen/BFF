from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient, UespClientError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only probe for exact UESP page titles. Writes no encounter JSON or database rows."
    )
    parser.add_argument("titles", nargs="+", help="UESP page titles to test")
    parser.add_argument("--rate-limit", type=float, default=2.0)
    parser.add_argument("--cache-dir", type=Path, default=Path("data/uesp/.cache"))
    parser.add_argument("--refresh", action="store_true", help="Ignore cached API responses")
    args = parser.parse_args()

    client = UespClient(
        cache_dir=args.cache_dir,
        min_request_interval=args.rate_limit,
    )

    print("=" * 72)
    print(" UESP PAGE TITLE PROBE - READ ONLY")
    print("=" * 72)

    failures = 0
    for title in args.titles:
        try:
            page = client.get_page(title, use_cache=not args.refresh)
        except UespClientError as exc:
            failures += 1
            print(f"MISS  {title}")
            print(f"      {exc}")
            continue

        print(f"FOUND {title}")
        print(f"      resolved title: {page.title}")
        print(f"      page id:        {page.page_id}")
        print(f"      revision:       {page.revision_id}")
        bossish = any("boss" in category.casefold() for category in page.categories)
        print(f"      boss category:  {'yes' if bossish else 'no'}")

    print()
    print("No source JSON files or database rows were changed.")
    return 1 if failures == len(args.titles) else 0


if __name__ == "__main__":
    raise SystemExit(main())
