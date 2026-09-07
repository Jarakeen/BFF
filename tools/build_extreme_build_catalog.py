from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.extreme_build_catalog_service import ExtremeBuildCatalogService


DEFAULT_OUTPUT = get_data_dir() / "generated" / "extreme_build_catalog.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Precompute the reusable structural catalog used by Extreme Build Lab. "
            "The catalog stores legality, bar allocation shapes, skill families, "
            "and passive formulas, while leaving context-sensitive ranking dynamic."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help=f"Canonical ESO database (default: {DEFAULT_DATABASE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Generated catalog path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    service = ExtremeBuildCatalogService(args.database)
    output = service.write(args.output)
    catalog = service.build()

    print("========================================")
    print(" EXTREME BUILD CATALOG")
    print("========================================")
    print(f"Database:       {args.database}")
    print(f"Output:         {output}")
    print(f"Schema:         {catalog['metadata']['schema_version']}")
    print(f"Rule version:   {catalog['metadata']['subclass_rule_version']}")
    print(f"DB fingerprint: {catalog['metadata']['source_database_sha256']}")
    print(f"Configurations: {len(catalog['class_configurations']['rows'])}")
    print(f"Line sets:      {len(catalog['bar_allocations']['by_line_set'])}")
    print(f"Skill lines:    {len(catalog['skill_families']['by_skill_line'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
