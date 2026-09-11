from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_resource_runtime_skill_witness_catalog_service import (
    ExtremeResourceRuntimeSkillWitnessCatalogService,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit canonical skill witnesses for Extreme resource runtime conditions."
    )
    parser.add_argument("--database", default="data/eso.db")
    return parser


def _print_rows(title: str, rows) -> None:
    print(f"\n{title} ({len(rows)})")
    for row in rows:
        print(
            f"  {row.canonical_id} | name={row.name} | "
            f"line={row.canonical_skill_line_id}"
        )


def main() -> int:
    args = _parser().parse_args()
    catalog = ExtremeResourceRuntimeSkillWitnessCatalogService(Path(args.database)).build()

    print(f"active_skills_reviewed={catalog.active_skills_reviewed}")
    print(f"denominator_proven={catalog.denominator_proven}")
    _print_rows("ARMOR ABILITY WITNESSES", catalog.armor_abilities)
    _print_rows("PET WITNESSES", catalog.pet_abilities)
    _print_rows("TRANSFORMATION ULTIMATE WITNESSES", catalog.transformation_ultimates)

    if catalog.unresolved:
        print("\nUNRESOLVED")
        for item in catalog.unresolved:
            print(f"  {item}")

    return 0 if catalog.denominator_proven else 2


if __name__ == "__main__":
    raise SystemExit(main())
