from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from importers.scribing_crafted_description_importer import UespCraftedScriptDescriptionImporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import UESP Update 51 PTS crafted-script descriptions into data/eso.db."
    )
    parser.add_argument("source_html", help="Saved UESP craftedScriptDescriptions51pts HTML file")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE), help=f"Target DB (default: {DEFAULT_DATABASE})")
    parser.add_argument("--normalized-json", help="Optional path to write a normalized JSON snapshot")
    args = parser.parse_args()

    source = Path(args.source_html).expanduser().resolve()
    database = Path(args.database).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source HTML not found: {source}")
    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")

    importer = UespCraftedScriptDescriptionImporter(database)
    summary = importer.run(source_path=source)
    if args.normalized_json:
        importer.write_normalized_json(source, Path(args.normalized_json).expanduser().resolve())

    print("========================================")
    print(" ESO U51 PTS SCRIBING DESCRIPTION IMPORT")
    print("========================================")
    print(f"Source:             {source}")
    print(f"Database:           {database}")
    print(f"Rows imported:      {summary.rows:,}")
    print(f"Crafted abilities:  {summary.crafted_abilities}")
    print(f"Scripts:            {summary.scripts}")
    print(f"Class variants:     {summary.classes}")
    print(f"Ability IDs:        {summary.abilities}")
    print(f"Result names:       {summary.names}")
    print(f"Source key:         {summary.source_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
