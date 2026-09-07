from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from importers.scribing_u51_catalog_importer import U51ScribingCatalogImporter


DEFAULT_CATALOG = PROJECT_ROOT / "data" / "scribing" / "u51_pts_catalog.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import the bundled normalized UESP Update 51 PTS scribing catalog."
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG),
        help=f"Normalized catalog JSON (default: {DEFAULT_CATALOG})",
    )
    parser.add_argument(
        "--database",
        default=str(DEFAULT_DATABASE),
        help=f"Target database (default: {DEFAULT_DATABASE})",
    )
    args = parser.parse_args()

    catalog = Path(args.catalog).expanduser().resolve()
    database = Path(args.database).expanduser().resolve()
    if not catalog.is_file():
        raise FileNotFoundError(f"Bundled U51 scribing catalog not found: {catalog}")
    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")

    summary = U51ScribingCatalogImporter(database).run(catalog_path=catalog)

    print("========================================")
    print(" U51 PTS SCRIBING CATALOG IMPORT")
    print("========================================")
    print(f"Catalog:             {catalog}")
    print(f"Database:            {database}")
    print(f"Scripts:             {summary.scripts:,}")
    print(f"Crafted skills:      {summary.skills:,}")
    print(f"Skill ability IDs:   {summary.skill_abilities:,}")
    print(f"Compatibility rows:  {summary.compatibility_rows:,}")
    print(f"Descriptions:        {summary.descriptions:,}")
    print(f"Source:              {summary.source_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
