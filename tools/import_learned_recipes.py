from __future__ import annotations

import argparse
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from importers.learned_recipe_importer import UespLearnedRecipeImporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import UESP provisioning recipes and furnishing plans into eso.db."
    )
    parser.add_argument("--recipes", required=True, help="Path to UESP minedItemSummary recipe JSON")
    parser.add_argument(
        "--furnishings",
        help="Optional path to UESP viewFurnishings export for plan/result cross-checking",
    )
    parser.add_argument(
        "--database",
        default=str(DEFAULT_DATABASE),
        help=f"Target SQLite database (default: {DEFAULT_DATABASE})",
    )
    args = parser.parse_args()

    summary = UespLearnedRecipeImporter(Path(args.database)).run(
        recipe_path=Path(args.recipes),
        furnishing_path=Path(args.furnishings) if args.furnishings else None,
    )

    print("========================================")
    print(" LEARNABLE RECIPE / FURNISHING IMPORT")
    print("========================================")
    print(f"Source records:            {summary.source_records:,}")
    print(f"Provisioning recipes:      {summary.provisioning_recipes:,}")
    print(f"Furnishing plans:          {summary.furnishing_plans:,}")
    print(f"Furnishing mappings:       {summary.furnishing_mappings:,}")
    print(f"Furnishings without plans: {summary.furnishing_rows_without_plan:,}")
    print(f"Unresolved:                {len(summary.unresolved):,}")
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
