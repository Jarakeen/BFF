from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from importers.provisioning_importer import UespProvisioningImporter


def _first_existing(candidates: tuple[Path, ...]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


DEFAULT_FOOD = _first_existing(
    (
        ROOT / "data" / "raw" / "food.json",
        ROOT / "data" / "raw" / "food_raw.json",
    )
)
DEFAULT_DRINK = _first_existing(
    (
        ROOT / "data" / "raw" / "drink.json",
        ROOT / "data" / "raw" / "drinks_raw.json",
    )
)


def run(database: Path, food: Path, drink: Path) -> int:
    print()
    print("========================================")
    print(" UESP PROVISIONING IMPORT")
    print("========================================")
    print(f"Database: {database}")
    print(f"Food:     {food}")
    print(f"Drink:    {drink}")
    print(
        "Provenance: UESP ESO Log Collector minedItemSummary exports; "
        "game update, API version, retrieval time, and export filters unresolved"
    )
    print()

    missing = [path for path in (food, drink) if not path.exists()]
    if missing:
        for path in missing:
            print(f"Source file not found: {path}")
        return 1
    if not database.exists():
        print(f"Database not found: {database}")
        return 2

    try:
        summary = UespProvisioningImporter(database).run(
            food_path=food,
            drink_path=drink,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Import failed: {exc}")
        return 3

    print(f"Source records:     {summary.source_records:,}")
    print(f"Entities created:   {summary.entities_created:,}")
    print(f"Entities existing:  {summary.entities_existing:,}")
    print(f"Mappings inserted:  {summary.mappings_inserted:,}")
    print(f"Mappings updated:   {summary.mappings_updated:,}")
    print()
    print("Unresolved source records:")
    if summary.unresolved:
        for message in summary.unresolved[:50]:
            print(f"  - {message}")
        if len(summary.unresolved) > 50:
            print(f"  ... and {len(summary.unresolved) - 50:,} more")
    else:
        print("  (none)")
    print()
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import canonical food and drink entities from UESP "
            "minedItemSummary JSON exports."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--food", type=Path, default=DEFAULT_FOOD)
    parser.add_argument("--drink", type=Path, default=DEFAULT_DRINK)
    return parser


if __name__ == "__main__":
    arguments = _parser().parse_args()
    raise SystemExit(run(arguments.database, arguments.food, arguments.drink))
