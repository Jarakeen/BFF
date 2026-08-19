#!/usr/bin/env python3
# tools/import_to_db.py
"""
Loads the normalized JSON under data/uesp/ into eso.db.

This is a deliberately separate tool from tools/import_uesp.py:
import_uesp.py talks to UESP and produces JSON; this tool never
touches the network, and only knows how to read that JSON and write
SQLite rows. Run them as two steps:

    python tools/import_uesp.py --all
    python tools/import_to_db.py

Usage:
    python tools/import_to_db.py
    python tools/import_to_db.py --content-file data/uesp/trials/rockgrove.json
    python tools/import_to_db.py --boss-file data/uesp/bosses/xalvakka.json
    python tools/import_to_db.py --db-path data/eso.db --uesp-root data/uesp
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.eso_db.eso_db_importer import EsoDbImportError, EsoDbImporter


DEFAULT_UESP_ROOT = REPO_ROOT / "data" / "uesp"
DEFAULT_DB_PATH = REPO_ROOT / "data" / "eso.db"


def build_arg_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Load the normalized JSON under data/uesp/ into eso.db.",
    )

    parser.add_argument(
        "--content-file",
        type=Path,
        help="Import a single content (trial/dungeon/arena) JSON file instead of the whole directory.",
    )
    parser.add_argument(
        "--boss-file",
        type=Path,
        help="Import a single boss JSON file instead of the whole directory.",
    )
    parser.add_argument(
        "--uesp-root",
        type=Path,
        default=DEFAULT_UESP_ROOT,
        help=f"Directory to import from (default: {DEFAULT_UESP_ROOT}).",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite database to write to (default: {DEFAULT_DB_PATH}).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:

    args = build_arg_parser().parse_args(argv)

    with EsoDbImporter(db_path=args.db_path) as importer:

        if args.content_file:
            try:
                importer.import_content_file(args.content_file)
                print(f"Imported content: {args.content_file}")
            except (OSError, EsoDbImportError) as exc:
                print(f"ERROR importing {args.content_file}: {exc}")
                return 1
            return 0

        if args.boss_file:
            try:
                importer.import_boss_file(args.boss_file)
                print(f"Imported boss: {args.boss_file}")
            except (OSError, EsoDbImportError) as exc:
                print(f"ERROR importing {args.boss_file}: {exc}")
                return 1
            return 0

        counts = importer.import_directory(args.uesp_root)

        print(
            f"Content imported: {counts['content']}  "
            f"Bosses imported: {counts['bosses']}  "
            f"Errors: {counts['errors']}"
        )
        print(f"Database: {args.db_path}")

        return 1 if counts["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
