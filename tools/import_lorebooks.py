from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from importers.lorebook_importer import UespLorebookImporter


def main() -> int:
    parser = argparse.ArgumentParser(description="Import UESP lorebooks into eso.db.")
    parser.add_argument("--books", required=True, help="Path to UESP books.json export")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE), help=f"Target SQLite database (default: {DEFAULT_DATABASE})")
    args = parser.parse_args()

    summary = UespLorebookImporter(Path(args.database)).run(books_path=Path(args.books))
    print("========================================")
    print(" LOREBOOK IMPORT")
    print("========================================")
    print(f"Source records:          {summary.source_records:,}")
    print(f"Lore source records:     {summary.lore_source_records:,}")
    print(f"Canonical lorebooks:     {summary.canonical_lorebooks:,}")
    print(f"Collapsed occurrences:   {summary.collapsed_occurrences:,}")
    print(f"Unresolved:              {len(summary.unresolved):,}")
    if summary.unresolved:
        print("\nUnresolved sample:")
        for item in summary.unresolved[:25]:
            print(f"  - {item}")
        if len(summary.unresolved) > 25:
            print(f"  ... {len(summary.unresolved) - 25:,} more")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
