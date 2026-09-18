from __future__ import annotations

"""Audit static armor/jewelry glyph-family coverage for Extreme MOST Actual Heal."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from services.extreme_actual_heal_static_enchant_denominator_service import (
    ExtremeActualHealStaticEnchantDenominatorService,
)


def main() -> int:
    database = get_data_dir() / "eso.db"
    result = ExtremeActualHealStaticEnchantDenominatorService(database).build()

    print("EXTREME E2 H1 STATIC ENCHANT DENOMINATOR")
    print(f"database={database}")
    print(f"armor_family_count={len(result.armor_families)}")
    print(f"jewelry_family_count={len(result.jewelry_families)}")
    print(f"static_family_count={result.static_family_count}")
    print(f"searched_armor_count={len(result.searched_armor_families)}")
    print(f"searched_jewelry_count={len(result.searched_jewelry_families)}")
    print(f"irrelevant_jewelry_count={len(result.irrelevant_jewelry_families)}")
    print(f"accounted_family_count={result.accounted_family_count}")
    print(f"unresolved_count={len(result.unresolved)}")
    for message in result.unresolved:
        print(f"UNRESOLVED: {message}")
    print(f"static_enchant_denominator_proven={result.denominator_proven}")
    print(
        "weapon_enchantment_boundary=runtime proc/cooldown/trigger evidence; "
        "not part of this static denominator"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
