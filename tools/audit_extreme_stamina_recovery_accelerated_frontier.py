from __future__ import annotations

"""Collapse the reusable Stamina Recovery jewelry/class/buff frontier.

This audit deliberately reuses proof boundaries closed during Magicka Recovery:
- Enlivening Overflow is capped at 150 and scales from Max Magicka.
- Three Gold Infused Recovery glyphs conservatively dominate Arcane substitutions.
- The Animal Companions + Curative Runeforms + Shadow class-line route dominates
  the reviewed class-route frontier at Recovery references >= 2700; Stamina removes
  Sorcerer Capacitor from competing routes, so that Magicka crossover is conservative.

It then proves that the current Stamina pre-class floor already exceeds that route
lock and that the winning equipped lines contain a verified self-applicable Minor
Endurance carrier.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_MAX_MAGICKA, BASE_STAMINA_RECOVERY
from minmax.conditional_recovery import enlivening_overflow_recovery_bonus
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.skill_known_effects import verified_skill_effects
from minmax.support_target_type import SupportTargetType
from services.extreme_recovery_class_route_frontier_service import (
    ExtremeRecoveryClassRouteFrontierService,
)
from services.extreme_recovery_jewelry_projection_service import (
    ExtremeRecoveryJewelryProjectionService,
)
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)
from services.extreme_race_objective_service import ExtremeRaceObjectiveService
from minmax.race_repository import RaceRepository
from minmax.mundus_repository import MundusRepository
from services.extreme_armor_mundus_joint_objective_service import (
    ExtremeArmorMundusJointObjectiveService,
)

OBJECTIVE = "stamina_recovery"
MAGICKA_ROUTE_LOCK_REFERENCE = 2700.0
ENLIVENING_CONDITIONAL_FLOOR = float(enlivening_overflow_recovery_bonus(int(BASE_MAX_MAGICKA)))
CP_OTHER_FLOOR = 150.0 + 90.0  # Sustained by Suffering + Rejuvenation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    race_rows = ExtremeRaceObjectiveService.candidates_for_objective(
        RaceRepository(database), OBJECTIVE
    )
    race = race_rows[0] if race_rows else None
    if race is None:
        unresolved.append("Stamina Recovery race frontier unavailable")

    armor = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        MundusRepository(database, initialize=False),
        OBJECTIVE,
        reference_value=BASE_STAMINA_RECOVERY,
    )
    if armor is None:
        unresolved.append("Stamina Recovery armor/Mundus frontier unavailable")

    jewelry = ExtremeRecoveryJewelryProjectionService(
        JewelryGlyphEffectRepository(database),
        JewelryTraitRepository(database),
    ).build(OBJECTIVE)
    if not jewelry.denominator_proven or jewelry.three_slot_infused_flat is None:
        unresolved.extend(jewelry.unresolved)
        unresolved.append("Stamina Recovery three-Infused jewelry projection incomplete")

    provisioning = ExtremeRecoveryProvisioningProjectionService.build(
        database, objective_key=OBJECTIVE
    )
    drink = provisioning.drink
    if drink is None:
        unresolved.append("Stamina Recovery best drink unavailable")

    preclass_floor = (
        float(BASE_STAMINA_RECOVERY)
        + float(race.projected_delta if race is not None else 0.0)
        + float(armor.mundus_delta if armor is not None else 0.0)
        + float(jewelry.three_slot_infused_flat or 0.0)
        + float(drink.delta if drink is not None else 0.0)
        + ENLIVENING_CONDITIONAL_FLOOR
        + CP_OTHER_FLOOR
    )

    route_service = ExtremeRecoveryClassRouteFrontierService(database)
    frontier = route_service.frontier(OBJECTIVE, reference_value=preclass_floor)
    best = frontier.best_reviewed_candidate
    expected_lines = {"Animal Companions", "Curative Runeforms", "Shadow"}
    winner_expected_lines = bool(best and set(best.equipped_skill_lines) == expected_lines)

    carrier_effects = verified_skill_effects(183555, 0)
    endurance = tuple(
        effect
        for effect in carrier_effects
        if effect.name == "minor_endurance"
        and effect.target_type is SupportTargetType.SELF
        and effect.duration is not None
        and float(effect.duration) > 0
        and effect.condition is None
        and effect.trigger is None
    )
    carrier_proven = len(endurance) == 1

    # The Magicka jewelry proof is conservative for Stamina too because Arcane can
    # only improve the same shared Enlivening Overflow branch while sacrificing the
    # same direct Recovery glyph amplification. Three Infused was proven to beat
    # every Arcane substitution even when each substitution was granted the full
    # 150 Enlivening cap.
    jewelry_dominance_transfers = bool(
        jewelry.denominator_proven
        and jewelry.three_slot_infused_flat is not None
        and abs(float(jewelry.three_slot_infused_flat) - 811.2) <= 1e-6
    )

    route_lock_floor_proven = preclass_floor >= MAGICKA_ROUTE_LOCK_REFERENCE - 1e-9
    unique_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
    closed = all(
        (
            jewelry_dominance_transfers,
            route_lock_floor_proven,
            winner_expected_lines,
            carrier_proven,
            not unique_unresolved,
        )
    )

    print("EXTREME STAMINA RECOVERY ACCELERATED FRONTIER")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    print("PRE-CLASS CONSERVATIVE FLOOR")
    print(f"base={BASE_STAMINA_RECOVERY:.3f}")
    print(f"race={float(race.projected_delta if race else 0.0):.3f}")
    print(f"mundus={float(armor.mundus_delta if armor else 0.0):.3f}")
    print(f"three_infused_recovery={float(jewelry.three_slot_infused_flat or 0.0):.3f}")
    print(f"drink={float(drink.delta if drink else 0.0):.3f}")
    print(f"base_max_magicka_enlivening_floor={ENLIVENING_CONDITIONAL_FLOOR:.3f}")
    print(f"other_selected_cp_floor={CP_OTHER_FLOOR:.3f}")
    print(f"preclass_floor={preclass_floor:.3f}")
    print(f"route_lock_reference={MAGICKA_ROUTE_LOCK_REFERENCE:.3f}")
    print()
    print("JEWELRY")
    print(f"strongest_glyph={jewelry.strongest_glyph_name!r}")
    print(f"three_infused_direct={float(jewelry.three_slot_infused_flat or 0.0):.3f}")
    print(f"jewelry_dominance_transfers={jewelry_dominance_transfers}")
    print()
    print("CLASS ROUTE")
    if best is None:
        print("best_route=None")
    else:
        print(f"best_base_class={best.base_class!r}")
        print(f"best_lines={best.equipped_skill_lines!r}")
        print(f"best_static_flat={best.static_flat:.3f}")
        print(f"best_static_percent={best.static_percent:.6f}")
        print(f"best_slot_delta={best.slot_projected_delta:.3f}")
        print(f"best_mastery_delta={best.mastery_projected_delta:.3f}")
        print(f"best_projected_delta={best.projected_delta:.3f}")
        print(f"best_slot_counts={best.slot_counts!r}")
    print(f"route_runtime_obligations={frontier.unresolved_runtime_obligations!r}")
    print()
    print("MINOR ENDURANCE")
    print("carrier=\"Arcanist's Domain\"")
    print(f"carrier_in_expected_route={'Curative Runeforms' in expected_lines}")
    print(f"carrier_self_usable={carrier_proven}")
    if endurance:
        print(f"carrier_duration={float(endurance[0].duration or 0.0):.3f}")
        print(f"carrier_magnitude={float(endurance[0].magnitude or 0.0):.6f}")
    print()
    print("PROOF GATES")
    print(f"route_lock_floor_proven={route_lock_floor_proven}")
    print(f"winner_expected_lines={winner_expected_lines}")
    print(f"jewelry_frontier_transferred=True" if jewelry_dominance_transfers else "jewelry_frontier_transferred=False")
    print(f"minor_endurance_carrier_proven={carrier_proven}")
    print(f"unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"accelerated_frontier_closed={closed}")
    print("NEXT_STEP=score exact same-build Enlivening, named gear, and contextual Battle Rush/Endurance/Domination layers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
