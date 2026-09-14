from __future__ import annotations

"""Close the armor-weight / armor-trait / Mundus frontier for Extreme Magicka Recovery.

The audit deliberately composes the existing canonical owners rather than trusting the
local armor/Mundus delta in isolation. Recovery flats are summed first; the locked
class-route percentage and Light Armor Evocation percentage are then applied together.

To keep the proof conservative, the baseline excludes racial Recovery and later named
gear / potion / contextual sources. Those omitted sources are non-negative. If the
winner is already ahead at this floor and also has the greatest total Recovery-percent
slope, later additive sources can only widen its lead.

Armor-weight diversity is still allowed to affect Enlivening Overflow through Undaunted
Mettle. That cross-axis coupling is scored explicitly so a mixed-weight challenger is not
silently denied its Max Magicka advantage.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_MAGICKA_RECOVERY, BaseCharacterCalculator, ResourceInputs
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.passive_math import undaunted_mettle_resource_percent
from minmax.race_repository import RaceRepository
from services.extreme_armor_mundus_joint_objective_service import (
    ExtremeArmorMundusJointCandidate,
    ExtremeArmorMundusJointObjectiveService,
)
from services.extreme_armor_weight_objective_service import ExtremeArmorWeightObjectiveService
from services.extreme_recovery_final_score_service import (
    ExtremeRecoveryFinalScoreService,
    ExtremeRecoveryScoreComponent,
)
from services.extreme_recovery_jewelry_projection_service import ExtremeRecoveryJewelryProjectionService
from services.extreme_recovery_provisioning_projection_service import ExtremeRecoveryProvisioningProjectionService
from services.extreme_recovery_class_route_frontier_service import ExtremeRecoveryClassRouteFrontierService
from tools.audit_extreme_magicka_recovery_same_build_enlivening import (
    _arcane_supremacy,
    _best_racial_recovery_witness,
    _recovery_cp_loadout,
    exact_enlivening_value,
    prove_route_lock,
)
from tools.audit_extreme_health_recovery_final_record import _armor_magicka_glyph_flat

OBJECTIVE = "magicka_recovery"
EXPECTED_ROUTE_IDS = frozenset({"animal_companions", "curative_runeforms", "shadow"})


@dataclass(frozen=True)
class ArmorMundusComposedCandidate:
    source: ExtremeArmorMundusJointCandidate
    light_pieces: int
    medium_pieces: int
    heavy_pieces: int
    armor_percent: float
    class_percent: float
    undaunted_percent: float
    same_build_max_magicka: float
    enlivening: float
    final_value: float
    future_additive_slope: float

    @property
    def weight_type_count(self) -> int:
        return sum(1 for value in (self.light_pieces, self.medium_pieces, self.heavy_pieces) if value > 0)


def _line_id(value: str) -> str:
    return str(value or "").strip().casefold().replace(" ", "_")


def _counts(candidate: ExtremeArmorMundusJointCandidate) -> tuple[int, int, int]:
    light = sum(1 for piece in candidate.pieces if piece.weight == "Light")
    medium = sum(1 for piece in candidate.pieces if piece.weight == "Medium")
    heavy = sum(1 for piece in candidate.pieces if piece.weight == "Heavy")
    return light, medium, heavy


def _same_build_max_magicka_for_weight_types(database: Path, weight_type_count: int) -> tuple[float, tuple[str, ...]]:
    unresolved: list[str] = []
    race_row, race_unresolved, _ = _best_racial_recovery_witness(database)
    unresolved.extend(f"racial Recovery unresolved: {name}" for name in race_unresolved)
    if race_row is None:
        return 0.0, tuple(dict.fromkeys((*unresolved, "No racial Magicka Recovery winner resolved")))

    race_name = race_row[2].skill_line.removesuffix(" Skills")
    race_flat = float(RaceRepository(database).get_stat_map_by_name(race_name).get("max_magicka", 0.0))

    armor_glyph_flat = _armor_magicka_glyph_flat(database)
    if armor_glyph_flat is None:
        unresolved.append("Canonical seven-piece Max Magicka armor glyph value unresolved")
        armor_glyph_flat = 0.0

    arcane_flat, _, arcane_slottable, arcane_unresolved = _arcane_supremacy(database)
    unresolved.extend(arcane_unresolved)
    if not arcane_slottable:
        unresolved.append("Arcane Supremacy is not structurally slottable")

    trace = BaseCharacterCalculator().max_magicka(
        ResourceInputs(
            attribute_points=64,
            item_flat=float(armor_glyph_flat),
            champion_flat=float(arcane_flat if arcane_slottable else 0.0),
            race_flat=float(race_flat),
            other_percent=undaunted_mettle_resource_percent(weight_type_count),
        )
    )
    return float(trace.raw_value), tuple(dict.fromkeys(unresolved))


def compose_candidate(
    candidate: ExtremeArmorMundusJointCandidate,
    *,
    fixed_additive_floor: float,
    non_enlivening_cp: float,
    class_percent: float,
    same_build_max_magicka: float,
) -> ArmorMundusComposedCandidate:
    light, medium, heavy = _counts(candidate)
    armor = ExtremeArmorWeightObjectiveService.candidate_for_composition(
        OBJECTIVE,
        light_pieces=light,
        medium_pieces=medium,
        heavy_pieces=heavy,
        reference_value=fixed_additive_floor + non_enlivening_cp,
    )
    armor_percent = float(armor.percent_of_reference)
    enlivening = exact_enlivening_value(same_build_max_magicka)

    score = ExtremeRecoveryFinalScoreService.compose(
        objective_key=OBJECTIVE,
        base_value=BASE_MAGICKA_RECOVERY,
        additive_components=(
            ExtremeRecoveryScoreComponent("fixed_floor_excluding_base_and_cp", fixed_additive_floor),
            ExtremeRecoveryScoreComponent("non_enlivening_cp", non_enlivening_cp),
            ExtremeRecoveryScoreComponent("enlivening_overflow", enlivening),
            ExtremeRecoveryScoreComponent("armor_traits", float(candidate.armor_direct_delta)),
            ExtremeRecoveryScoreComponent("mundus", float(candidate.mundus_delta)),
        ),
        percent_components=(
            ExtremeRecoveryScoreComponent("locked_class_route", class_percent * 100.0),
            ExtremeRecoveryScoreComponent("light_armor_evocation", armor_percent * 100.0),
        ),
    )
    return ArmorMundusComposedCandidate(
        source=candidate,
        light_pieces=light,
        medium_pieces=medium,
        heavy_pieces=heavy,
        armor_percent=armor_percent,
        class_percent=class_percent,
        undaunted_percent=undaunted_mettle_resource_percent(
            sum(1 for count in (light, medium, heavy) if count > 0)
        ),
        same_build_max_magicka=same_build_max_magicka,
        enlivening=enlivening,
        final_value=float(score.final_value),
        future_additive_slope=1.0 + class_percent + armor_percent,
    )


def globally_locked_winner(rows: tuple[ArmorMundusComposedCandidate, ...]) -> tuple[bool, float]:
    if not rows:
        return False, 0.0
    ordered = sorted(rows, key=lambda row: (-row.final_value, -row.future_additive_slope))
    winner = ordered[0]
    margin = min(
        (winner.final_value - challenger.final_value for challenger in ordered[1:]),
        default=0.0,
    )
    max_challenger_slope = max(
        (challenger.future_additive_slope for challenger in ordered[1:]),
        default=winner.future_additive_slope,
    )
    return margin >= -1e-9 and winner.future_additive_slope + 1e-9 >= max_challenger_slope, margin


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    jewelry = ExtremeRecoveryJewelryProjectionService(
        JewelryGlyphEffectRepository(database),
        JewelryTraitRepository(database),
    ).build(OBJECTIVE)
    unresolved.extend(jewelry.unresolved)
    three_infused = float(jewelry.three_slot_infused_flat or 0.0)

    provisioning = ExtremeRecoveryProvisioningProjectionService.build(database, objective_key=OBJECTIVE)
    unresolved.extend(provisioning.unresolved)
    drink = provisioning.drink
    if drink is None:
        unresolved.append("No reviewed Magicka Recovery drink winner resolved")
    drink_recovery = float(drink.delta) if drink else 0.0

    cp_without_enlivening, cp_unresolved = _recovery_cp_loadout(database, enlivening_value=0.0)
    unresolved.extend(cp_unresolved)
    non_enlivening_cp = float(cp_without_enlivening.total_flat_ceiling)

    # Conservative floor: exclude racial Recovery, Enlivening, Mundus, armor traits,
    # named gear, potion buffs, and contextual shared Recovery. All are non-negative.
    fixed_additive_floor = three_infused + drink_recovery
    preclass_floor = float(BASE_MAGICKA_RECOVERY) + fixed_additive_floor + non_enlivening_cp

    route_lock = prove_route_lock(
        ExtremeRecoveryClassRouteFrontierService(database),
        reference_value=preclass_floor,
    )
    route = route_lock.winner
    route_ids = frozenset(_line_id(value) for value in route.equipped_skill_lines) if route else frozenset()
    route_expected = bool(route and route_ids == EXPECTED_ROUTE_IDS)
    class_percent = float(route_lock.winner_slope or 0.0)

    max_magicka_by_types: dict[int, float] = {}
    for count in (1, 2, 3):
        value, messages = _same_build_max_magicka_for_weight_types(database, count)
        max_magicka_by_types[count] = value
        unresolved.extend(messages)

    joint_rows = ExtremeArmorMundusJointObjectiveService.candidates_for_objective(
        MundusRepository(database),
        OBJECTIVE,
        reference_value=preclass_floor,
    )
    composed: list[ArmorMundusComposedCandidate] = []
    for row in joint_rows:
        light, medium, heavy = _counts(row)
        type_count = sum(1 for value in (light, medium, heavy) if value > 0)
        composed.append(
            compose_candidate(
                row,
                fixed_additive_floor=fixed_additive_floor,
                non_enlivening_cp=non_enlivening_cp,
                class_percent=class_percent,
                same_build_max_magicka=max_magicka_by_types[type_count],
            )
        )

    ranked = tuple(sorted(composed, key=lambda row: (-row.final_value, -row.future_additive_slope)))
    winner = ranked[0] if ranked else None
    global_lock, minimum_margin = globally_locked_winner(ranked)
    winner_all_light = bool(winner and winner.light_pieces == 7)
    winner_all_divines = bool(winner and winner.source.divines_count == 7)
    winner_atronach = bool(winner and winner.source.mundus_name == "The Atronach")
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        jewelry.denominator_proven
        and provisioning.comparison_proven
        and cp_without_enlivening.denominator_proven
        and route_expected
        and route_lock.globally_locked_above_reference
        and winner_all_light
        and winner_all_divines
        and winner_atronach
        and global_lock
        and not unique_unresolved
    )

    print("EXTREME MAGICKA RECOVERY ARMOR / MUNDUS FRONTIER")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    print("CONSERVATIVE LOCKING FLOOR")
    print(f"base_magicka_recovery={BASE_MAGICKA_RECOVERY:.3f}")
    print(f"three_infused_jewelry={three_infused:.3f}")
    print(f"provisioning={drink.name if drink else '<unresolved>'!r} delta={drink_recovery:.3f}")
    print(f"legal_non_enlivening_cp={non_enlivening_cp:.3f}")
    print(f"preclass_floor_without_race_enlivening_mundus_armor={preclass_floor:.3f}")
    print(f"locked_route_ids={tuple(sorted(route_ids))!r}")
    print(f"locked_class_percent={class_percent * 100.0:.3f}")
    print(f"route_globally_locked={route_lock.globally_locked_above_reference}")
    print()
    print("UNDATED METTLE / ENLIVENING CROSS-AXIS")
    for count in (1, 2, 3):
        max_magicka = max_magicka_by_types[count]
        print(
            f"armor_weight_types={count} undaunted_mettle_percent={undaunted_mettle_resource_percent(count) * 100.0:.3f} "
            f"same_build_max_magicka={max_magicka:.3f} enlivening={exact_enlivening_value(max_magicka):.3f}"
        )
    print()
    print("TOP COMPOSED ARMOR / MUNDUS CANDIDATES")
    for index, row in enumerate(ranked[:8], start=1):
        traits = {"Divines": 0, "Invigorating": 0, "Other": 0}
        for piece in row.source.pieces:
            if piece.trait in traits:
                traits[piece.trait] += 1
            else:
                traits["Other"] += 1
        print(
            f"rank={index} composition={row.source.composition_label} "
            f"divines={traits['Divines']} invigorating={traits['Invigorating']} other_traits={traits['Other']} "
            f"mundus={row.source.mundus_name!r} armor_direct={row.source.armor_direct_delta:.3f} "
            f"mundus_delta={row.source.mundus_delta:.3f} armor_percent={row.armor_percent * 100.0:.3f} "
            f"enlivening={row.enlivening:.3f} total_percent={(row.class_percent + row.armor_percent) * 100.0:.3f} "
            f"composed_recovery={row.final_value:.3f} future_additive_slope={row.future_additive_slope:.6f}"
        )
    print()
    print("PROOF GATES")
    print(f"locked_high_reference_route={route_expected and route_lock.globally_locked_above_reference}")
    print(f"winner_all_light={winner_all_light}")
    print(f"winner_all_divines={winner_all_divines}")
    print(f"winner_atronach={winner_atronach}")
    print(f"future_nonnegative_additive_lock={global_lock}")
    print(f"minimum_current_margin={minimum_margin:.3f}")
    print(f"unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"magicka_recovery_armor_mundus_frontier_closed={closed}")
    if closed:
        print(
            "NEXT_STEP=compose ordinary named-gear Recovery candidates against the locked "
            "7-Light / 7-Divines / Atronach armor frontier and prove physical set compatibility"
        )
    else:
        print("NEXT_STEP=close only the reported armor/Mundus frontier blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
