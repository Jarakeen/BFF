from __future__ import annotations

"""Audit the reusable Extreme foundation for the Magicka Recovery record.

This is a denominator/discovery audit, not a final record claim.  It deliberately
reuses objective-neutral Extreme services that already understand Recovery and
prints the remaining source-family blockers explicitly rather than interpreting
unreviewed mechanics as zero.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_MAGICKA_RECOVERY
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.combat_effect_semantics import GameUpdate
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.mundus_repository import MundusRepository
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.race_repository import RaceRepository
from services.extreme_armor_mundus_joint_objective_service import (
    ExtremeArmorMundusJointObjectiveService,
)
from services.extreme_champion_point_objective_service import (
    ExtremeChampionPointObjectiveService,
)
from services.extreme_enchantment_objective_service import (
    ExtremeEnchantmentObjectiveService,
)
from services.extreme_objective_coverage_service import ExtremeObjectiveCoverageService
from services.extreme_race_objective_service import ExtremeRaceObjectiveService
from services.extreme_recovery_potion_projection_service import (
    ExtremeRecoveryPotionProjectionService,
)
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)


OBJECTIVE = "magicka_recovery"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _positive_slottable_cp(repository: ChampionPointStaticRepository):
    rows = ExtremeChampionPointObjectiveService.slottable_candidates_for_objective(
        repository,
        OBJECTIVE,
    )
    return tuple(
        row
        for row in rows
        if row.reviewed_delta is not None and float(row.reviewed_delta) > 0.0
    ), tuple(row for row in rows if row.reviewed_delta is None)


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    race_repository = RaceRepository(database)
    race_rows = ExtremeRaceObjectiveService.candidates_for_objective(
        race_repository,
        OBJECTIVE,
    )
    race_best = race_rows[0] if race_rows else None

    mundus_repository = MundusRepository(database, initialize=False)
    armor_mundus = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        mundus_repository,
        OBJECTIVE,
        reference_value=BASE_MAGICKA_RECOVERY,
    )

    jewelry = ExtremeEnchantmentObjectiveService.best_three_jewelry_loadout(
        JewelryGlyphEffectRepository(database),
        OBJECTIVE,
    )

    provisioning = ExtremeRecoveryProvisioningProjectionService.build(
        database,
        objective_key=OBJECTIVE,
    )

    potion = ExtremeRecoveryPotionProjectionService(
        PotionAvailabilityRepository(database, game_update=GameUpdate.U50)
    ).build(OBJECTIVE)

    cp_repository = ChampionPointStaticRepository(database)
    cp_non_slottable = ExtremeChampionPointObjectiveService.non_slottable_baseline_for_objective(
        cp_repository,
        OBJECTIVE,
    )
    cp_positive, cp_unresolved = _positive_slottable_cp(cp_repository)

    coverage = ExtremeObjectiveCoverageService.coverage_for(OBJECTIVE)

    print("EXTREME MAGICKA RECOVERY FOUNDATION AUDIT")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"base_magicka_recovery={BASE_MAGICKA_RECOVERY:.3f}")
    print()

    print("RACE STRUCTURED FRONTIER")
    if race_best is None:
        print("structured_race_candidate=None")
    else:
        print(f"structured_race_candidate={race_best.race_name!r}")
        print(f"structured_race_delta={race_best.projected_delta:.3f}")
        print(f"structured_race_boundary_count={len(race_best.boundaries)}")
        for boundary in race_best.boundaries:
            print(f"  boundary: {boundary}")
    print(f"structured_race_candidates={len(race_rows)}")
    print()

    print("ARMOR / MUNDUS FRONTIER")
    if armor_mundus is None:
        print("armor_mundus_candidate=None")
    else:
        print(f"armor_composition={armor_mundus.composition_label}")
        print(f"armor_divines_count={armor_mundus.divines_count}")
        print(f"mundus={armor_mundus.mundus_name!r}")
        print(f"armor_direct_delta={armor_mundus.armor_direct_delta:.3f}")
        print(f"armor_passive_delta={armor_mundus.armor_passive_delta:.3f}")
        print(f"mundus_delta={armor_mundus.mundus_delta:.3f}")
        print(f"armor_mundus_total_delta={armor_mundus.total_delta:.3f}")
    print()

    print("JEWELRY GLYPH FRONTIER")
    if jewelry is None:
        print("jewelry_loadout=None")
    else:
        print(f"jewelry_glyph={jewelry.glyph_name!r}")
        print(f"jewelry_slot_multipliers={jewelry.slot_multipliers}")
        print(f"jewelry_projected_delta={float(jewelry.projected_delta or 0.0):.3f}")
        print(f"jewelry_unresolved={len(jewelry.unresolved)}")
    print("jewelry_trait_opportunity_cost_review_pending=True")
    print()

    print("PROVISIONING FRONTIER")
    print(f"provisioning_reviewed_names={provisioning.reviewed_names}")
    print(f"provisioning_comparison_proven={provisioning.comparison_proven}")
    if provisioning.food is not None:
        print(f"best_food={provisioning.food.name!r} delta={provisioning.food.delta:.3f}")
    if provisioning.drink is not None:
        print(f"best_drink={provisioning.drink.name!r} delta={provisioning.drink.delta:.3f}")
    for unresolved in provisioning.unresolved:
        print(f"  unresolved: {unresolved}")
    print()

    print("POTION FRONTIER")
    print(f"potion_formulas_reviewed={potion.formulas_reviewed}")
    print(f"potion_denominator_proven={potion.denominator_proven}")
    print(f"potion_relevant_buffs={potion.relevant_buffs}")
    print(f"potion_relevant_formula_count={len(potion.relevant_formulas)}")
    for unresolved in potion.unresolved:
        print(f"  unresolved: {unresolved}")
    print()

    print("CHAMPION POINT STATIC FRONTIER")
    print(f"non_slottable_static_lower_bound={cp_non_slottable.reviewed_lower_bound:.3f}")
    print(f"non_slottable_mechanic_complete={cp_non_slottable.mechanic_complete}")
    print(f"non_slottable_unresolved={len(cp_non_slottable.unresolved_candidates)}")
    print(f"positive_slottable_static_candidates={len(cp_positive)}")
    for row in cp_positive:
        print(f"  candidate: {row.name} delta={float(row.reviewed_delta or 0.0):.3f}")
    print(f"slottable_runtime_or_unresolved_candidates={len(cp_unresolved)}")
    for row in cp_unresolved:
        print(f"  unresolved: {row.name}: {'; '.join(row.unresolved)}")
    print("legal_four_star_cp_loadout_review_pending=True")
    print()

    print("SOURCE COVERAGE")
    print(f"source_universe_reviewed={coverage.source_universe_reviewed}")
    print(f"global_maximum_ready={coverage.global_maximum_ready}")
    print(f"claim={coverage.claim.value}")
    print(f"blocking_source_count={len(coverage.blocking_sources)}")
    for source in coverage.blocking_sources:
        print(f"  {source.source_family}: {source.status.value} | {source.note}")
    print()

    foundation_numeric_axes_available = all(
        (
            race_best is not None,
            armor_mundus is not None,
            jewelry is not None,
            provisioning.comparison_proven,
            potion.denominator_proven,
        )
    )
    print(f"foundation_numeric_axes_available={foundation_numeric_axes_available}")
    print("magicka_recovery_record_closed=False")
    print(
        "NEXT_STEP=close the Magicka Recovery passive/class-route denominator, legal CP loadout, "
        "jewelry trait opportunity cost, and ordinary/special named-gear frontier before whole-record scoring"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
