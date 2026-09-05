from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from importers.scribing_reference_importer import UespScribingReferenceImporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import normalized UESP Scribing reference data into FoundryDock's canonical database."
    )
    parser.add_argument("source", help="Path to normalized scribing_uesp_*.json")
    parser.add_argument(
        "--database",
        default=str(DEFAULT_DATABASE),
        help=f"Target SQLite database (default: {DEFAULT_DATABASE})",
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    database = Path(args.database).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Scribing source file not found: {source}")
    if not database.is_file():
        raise FileNotFoundError(f"Canonical database not found: {database}")

    summary = UespScribingReferenceImporter(database).run(source_path=source)

    print("========================================")
    print(" UESP SCRIBING REFERENCE IMPORT")
    print("========================================")
    print(f"Revision:             {summary.revision_id or 'unresolved'}")
    print(f"Grimoires:            {summary.grimoires:,}")
    print(f"Scripts:              {summary.scripts:,}")
    print(f"Compatibility rows:   {summary.compatibility_rows:,}")
    print(f"Reference sections:   {summary.sections:,}")

    with sqlite3.connect(database) as connection:
        counts = {
            "scribing_grimoire": connection.execute("SELECT COUNT(*) FROM scribing_grimoire").fetchone()[0],
            "scribing_script": connection.execute("SELECT COUNT(*) FROM scribing_script").fetchone()[0],
            "scribing_script_grimoire": connection.execute("SELECT COUNT(*) FROM scribing_script_grimoire").fetchone()[0],
            "scribing_reference_section": connection.execute("SELECT COUNT(*) FROM scribing_reference_section").fetchone()[0],
        }

    print()
    print("Database totals:")
    for table, count in counts.items():
        print(f"  {table}: {count:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
