#!/usr/bin/env python3
# tools/import_uesp.py
"""
CLI importer for the local UESP encounter knowledge base.

Usage:
    python tools/import_uesp.py --content "Rockgrove"
    python tools/import_uesp.py --boss "Bahsei"
    python tools/import_uesp.py --all-trials
    python tools/import_uesp.py --all-dungeons
    python tools/import_uesp.py --all-arenas
    python tools/import_uesp.py --all

See data/uesp/README.md for the data layout, UESP's license/
attribution terms, and rate-limit/caching behavior.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import data_paths as canonical_data_paths
from services.uesp.uesp_client import UespClient
from services.uesp.uesp_importer import ImportResult, UespImporter
from services.uesp.uesp_store import UespStore


DEFAULT_DATA_ROOT = canonical_data_paths.UESP_DATA_ROOT


def data_paths(data_root: Path) -> tuple[Path, Path]:
    """Return the cache and import-log locations for an explicit corpus root."""
    root = Path(data_root)
    return root / ".cache", root / "import_log.jsonl"


def build_arg_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "Import ESO trial/dungeon/arena/boss data from UESP's "
            "official API into a local structured knowledge base."
        ),
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--content",
        metavar="TITLE",
        help='Import one trial/dungeon/arena overview page by title (e.g. "Rockgrove").',
    )
    group.add_argument(
        "--boss",
        metavar="TITLE",
        help='Import one boss page by title (e.g. "Bahsei").',
    )
    group.add_argument(
        "--all-trials",
        action="store_true",
        help="Import every page in Category:Online-Trials.",
    )
    group.add_argument(
        "--all-dungeons",
        action="store_true",
        help="Import every page in Category:Online-Dungeons.",
    )
    group.add_argument(
        "--all-arenas",
        action="store_true",
        help="Import every page in Category:Online-Arenas.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Import trials, dungeons, and arenas.",
    )

    parser.add_argument(
        "--content-type",
        choices=["trial", "dungeon", "arena"],
        default="trial",
        help=(
            "Content type for --content, used only as a fallback if it "
            "can't be detected from the page's own wiki categories "
            "(default: trial).")
        )

    group.add_argument(
        "--list-categories",
        action="store_true",
        help="List UESP categories matching --category-prefix.",
        )

    parser.add_argument(
        "--category-prefix",
        default="Online",
        help="Category prefix used with --list-categories.",
    )
    group.add_argument(
        "--category-members",
        metavar="CATEGORY",
        help="List pages belonging to a UESP category.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-import even if the stored revision id is already current.",
        )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=2.0,
        help="Minimum seconds between UESP API requests (default: 2.0).",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help=f"Output directory (default: {DEFAULT_DATA_ROOT}).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:

    args = build_arg_parser().parse_args(argv)

    data_root: Path = args.data_root
    cache_root, log_path = data_paths(data_root)

    client = UespClient(cache_dir=cache_root, min_request_interval=args.rate_limit)
    store = UespStore(root=data_root)
    importer = UespImporter(client=client, store=store, log_path=log_path, force=args.force)

    results: list[ImportResult] = []

    if args.content:
        results.append(importer.import_content(args.content, content_type=args.content_type))
    if args.list_categories:
        categories = client.get_categories(
        prefix=args.category_prefix
        )

        print()
        print(
            f"UESP categories beginning with "
            f"'{args.category_prefix}':"
        )

        for category in categories:
            print(f"  {category}")
    if args.category_members:
        members = client.get_category_members(
            args.category_members
        )

        print()
        print(
            f"UESP pages in "
            f"'{args.category_members}':"
        )

        for member in members:
            print(f"  {member}")

        print()
        print(f"Total: {len(members)}")

        return 0
    elif args.boss:
        results.append(importer.import_boss(args.boss))
    elif args.all_trials:
        results.extend(importer.import_all_trials())
    elif args.all_dungeons:
        results.extend(importer.import_all_dungeons())
    elif args.all_arenas:
        results.extend(importer.import_all_arenas())
    elif args.all:
        results.extend(importer.import_all())

    _print_summary(results)

    return 1 if any(result.status == "error" for result in results) else 0

    return 0

def _print_summary(results: list[ImportResult]) -> None:

    imported = sum(1 for r in results if r.status == "imported")
    skipped = sum(1 for r in results if r.status == "skipped_up_to_date")
    errors = [r for r in results if r.status == "error"]

    print()
    print(f"Imported: {imported}  Skipped (up to date): {skipped}  Errors: {len(errors)}")

    for result in errors:
        print(f"  ERROR  {result.title}: {result.detail}")


if __name__ == "__main__":
    raise SystemExit(main())
