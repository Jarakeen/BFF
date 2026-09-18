from __future__ import annotations

"""Audit H1 monster/mythic/arena-weapon canonical denominator."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from services.extreme_actual_heal_special_gear_denominator_service import (
    ExtremeActualHealSpecialGearDenominatorService,
)


def main() -> int:
    database = get_data_dir() / "eso.db"
    report = ExtremeActualHealSpecialGearDenominatorService(database).build()

    print("EXTREME E2 H1 SPECIAL GEAR DENOMINATOR")
    print(f"database={database}")
    print(f"monster_set_count={report.monster_count}")
    print(f"mythic_count={report.mythic_count}")
    print(f"arena_weapon_set_count={report.arena_weapon_count}")
    print(f"entity_only_set_count={report.entity_only_count}")
    print(f"special_gear_row_count={len(report.rows)}")
    print(f"h1_relevant_row_count={len(report.relevant_rows)}")
    print(f"unresolved_row_count={len(report.unresolved_rows)}")
    print(f"special_gear_denominator_proven={report.denominator_proven}")

    for family in ("monster", "mythic", "arena_weapon", "entity_only"):
        family_rows = tuple(row for row in report.rows if row.family == family)
        unresolved = tuple(row for row in family_rows if row.unresolved)
        relevant = tuple(row for row in family_rows if row.h1_relevant)
        conditional = tuple(
            row for row in family_rows if row.conditional_objectives
        )
        print()
        print(f"[{family.upper()}]")
        print(f"canonical_count={len(family_rows)}")
        print(f"h1_relevant_count={len(relevant)}")
        print(f"conditional_count={len(conditional)}")
        print(f"unresolved_count={len(unresolved)}")
        for row in conditional:
            print(
                f"CONDITIONAL family={family} set={row.set_name!r} "
                f"objectives={row.conditional_objectives}"
            )
        for row in unresolved:
            print(
                f"UNRESOLVED family={family} set={row.set_name!r} "
                f"issue_count={len(row.unresolved)}"
            )
            for message in row.unresolved[:6]:
                print(f"  - {message}")
            if len(row.unresolved) > 6:
                print(f"  - ... {len(row.unresolved) - 6} more")

    print()
    print(
        "NOTE=This reconciles normalized special-set mechanic dispositions and "
        "also exposes canonical entity-only gear-set rows that still lack normalized "
        "slot/bonus evidence. Package-shape enumeration/search completeness and "
        "runtime proc activation remain separate proof layers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
