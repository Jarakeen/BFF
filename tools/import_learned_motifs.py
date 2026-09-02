from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from importers.learned_motif_importer import UespLearnedMotifImporter


def main() -> int:
    parser = argparse.ArgumentParser(description="Import UESP crafting motifs into eso.db.")
    parser.add_argument("--motifs", required=True, help="Path to UESP minedItemSummary motif JSON")
    parser.add_argument(
        "--database",
        default=str(DEFAULT_DATABASE),
        help=f"Target SQLite database (default: {DEFAULT_DATABASE})",
    )
    args = parser.parse_args()

    summary = UespLearnedMotifImporter(Path(args.database)).run(motif_path=Path(args.motifs))

    print("========================================")
    print(" LEARNABLE MOTIF IMPORT")
    print("========================================")
    print(f"Source records:          {summary.source_records:,}")
    print(f"Canonical learnables:    {summary.canonical_learnables:,}")
    print(f"Full-style books:        {summary.full_style_books:,}")
    print(f"Chapter learnables:      {summary.chapter_learnables:,}")
    print(f"Collapsed item variants: {summary.collapsed_variants:,}")
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
