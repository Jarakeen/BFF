from __future__ import annotations

"""Audit two reusable U50 Weapon Damage axes together: armor/Mundus and CP.

This is a focused frontier audit, not a whole-record claim. It reuses canonical
owners for armor weight + Divines/Mundus scoring and Champion Point stat projection,
then reports only objective-relevant unresolved mechanics.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from services.champion_point_loadout_service import (
    CHAMPION_POINT_SLOTS_PER_DISCIPLINE,
    ChampionPointLoadoutCandidate,
    ChampionPointLoadoutService,
)
from services.extreme_armor_mundus_joint_objective_service import (
    ExtremeArmorMundusJointObjectiveService,
)
from services.extreme_champion_point_objective_service import (
    ExtremeChampionPointObjectiveService,
)

OBJECTIVE = "weapon_damage"
REFERENCE_VALUE = 3000.0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--reference-value", type=float, default=REFERENCE_VALUE)
    return parser


def _mentions_weapon_damage(text: str) -> bool:
    value = " ".join(str(text or "").casefold().split())
    return (
        "weapon damage" in value
        or "weapon and spell damage" in value
        or "weapon & spell damage" in value
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    reference_value = float(args.reference_value)

    mundus_repository = MundusRepository(database, game_update=U50_GAME_UPDATE)
    armor_mundus = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        mundus_repository,
        OBJECTIVE,
        reference_value=reference_value,
    )

    unresolved: list[str] = []
    if armor_mundus is None:
        unresolved.append("No legal armor/Mundus Weapon Damage candidate resolved")

    cp_repository = ChampionPointStaticRepository(database)
    cp_candidates: list[ChampionPointLoadoutCandidate] = []
    cp_relevant_unresolved: list[str] = []

    for record in cp_repository.slottable_records():
        projected = ExtremeChampionPointObjectiveService.candidate_for_record(
            cp_repository,
            record,
            OBJECTIVE,
            reference_value=reference_value,
        )
        if projected.reviewed_delta is not None:
            if projected.reviewed_delta > 0.0:
                cp_candidates.append(
                    ChampionPointLoadoutCandidate(
                        name=record.name,
                        discipline_index=record.discipline_index,
                        flat_ceiling=float(projected.reviewed_delta),
                        condition=None,
                    )
                )
            continue
        if _mentions_weapon_damage(record.description):
            cp_relevant_unresolved.append(
                f"{record.name}: {'; '.join(projected.unresolved)}"
            )

    cp_loadout = ChampionPointLoadoutService.build(tuple(cp_candidates))
    unresolved.extend(cp_loadout.unresolved)

    cp_baseline = ExtremeChampionPointObjectiveService.non_slottable_baseline_for_objective(
        cp_repository,
        OBJECTIVE,
        reference_value=reference_value,
    )
    non_slottable_records = {
        record.name.casefold(): record for record in cp_repository.non_slottable_records()
    }
    for projected in cp_baseline.unresolved_candidates:
        record = non_slottable_records.get(projected.name.casefold())
        if record is not None and _mentions_weapon_damage(record.description):
            cp_relevant_unresolved.append(
                f"non-slottable {record.name}: {'; '.join(projected.unresolved)}"
            )

    unresolved.extend(cp_relevant_unresolved)
    unique_unresolved = tuple(dict.fromkeys(unresolved))

    print("EXTREME WEAPON DAMAGE ARMOR / MUNDUS / CP FRONTIER")
    print(f"database={database}")
    print(f"reference_value={reference_value:.3f}")
    print()
    print("ARMOR + MUNDUS")
    if armor_mundus is None:
        print("winner=<none>")
    else:
        print(f"composition={armor_mundus.composition_label!r}")
        print(f"divines_count={armor_mundus.divines_count}")
        print(f"mundus={armor_mundus.mundus_name!r}")
        print(f"armor_direct_delta={armor_mundus.armor_direct_delta:.3f}")
        print(f"armor_passive_delta={armor_mundus.armor_passive_delta:.3f}")
        print(f"mundus_delta={armor_mundus.mundus_delta:.3f}")
        print(f"total_delta_at_reference={armor_mundus.total_delta:.3f}")
        print(f"divines_multiplier={armor_mundus.divines_multiplier:.6f}")
        print(f"piece_traits={tuple((row.slot, row.weight, row.trait) for row in armor_mundus.pieces)!r}")
    print()
    print("CHAMPION POINTS")
    print(f"slots_per_discipline={CHAMPION_POINT_SLOTS_PER_DISCIPLINE}")
    for row in cp_candidates:
        print(
            f"  candidate: {row.name} discipline={row.discipline_index} "
            f"delta={row.flat_ceiling:.3f}"
        )
    print(f"discipline_slot_counts={cp_loadout.discipline_slot_counts}")
    for row in cp_loadout.selected:
        print(
            f"  selected: {row.name} discipline={row.discipline_index} "
            f"delta={row.flat_ceiling:.3f}"
        )
    print(f"slottable_total_delta={cp_loadout.total_flat_ceiling:.3f}")
    print(f"non_slottable_reviewed_lower_bound={cp_baseline.reviewed_lower_bound:.3f}")
    print(f"weapon_damage_relevant_cp_unresolved_count={len(cp_relevant_unresolved)}")
    print()
    print("PROOF GATES")
    print(f"armor_mundus_frontier_resolved={armor_mundus is not None}")
    print(f"cp_four_slot_denominator_proven={cp_loadout.denominator_proven}")
    print(f"cp_weapon_damage_denominator_closed={not cp_relevant_unresolved and cp_loadout.denominator_proven}")
    print(f"unresolved_count={len(unique_unresolved)}")
    for row in unique_unresolved:
        print(f"  unresolved: {row}")
    closed = armor_mundus is not None and cp_loadout.denominator_proven and not unique_unresolved
    print(f"weapon_damage_armor_mundus_cp_frontier_closed={closed}")
    print(
        "NEXT_STEP=compose the closed armor/Mundus and CP winners with the Bloodthirsty jewelry frontier; then close weapon trait/enchantment, named gear, class/passive, and runtime power challengers"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
