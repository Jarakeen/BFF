from __future__ import annotations

"""Audit H1 legal weapon configurations and canonical weapon-passive coverage."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from services.extreme_actual_heal_weapon_denominator_service import (
    ExtremeActualHealWeaponDenominatorService,
)


def main() -> int:
    database = get_data_dir() / "eso.db"
    result = ExtremeActualHealWeaponDenominatorService(database).build()

    print("EXTREME E2 H1 WEAPON CONFIGURATION/PASSIVE DENOMINATOR")
    print(f"database={database}")
    print(f"legal_bar_configuration_count={result.legal_bar_configuration_count}")
    print(f"legal_two_bar_configuration_count={result.legal_two_bar_configuration_count}")

    counts = {}
    for row in result.legal_bar_configurations:
        counts[row.skill_line.value] = counts.get(row.skill_line.value, 0) + 1
    for key in sorted(counts):
        print(f"weapon_line_{key}_configuration_count={counts[key]}")

    print(f"canonical_weapon_passive_count={len(result.canonical_weapon_passives)}")
    print(f"reviewed_weapon_passive_count={len(result.reviewed_weapon_passives)}")
    print(f"unresolved_count={len(result.unresolved)}")
    for message in result.unresolved:
        print(f"UNRESOLVED: {message}")

    print(
        f"weapon_configuration_denominator_proven="
        f"{result.configuration_denominator_proven}"
    )
    print(f"weapon_passive_denominator_proven={result.passive_denominator_proven}")
    print(f"weapon_dimension_denominator_proven={result.denominator_proven}")
    print(
        "NOTE=This proves the legal configuration/passive denominator. It does not "
        "yet prove that the H1 optimizer searches every relevant configuration; "
        "candidate integration remains a separate closure step."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
