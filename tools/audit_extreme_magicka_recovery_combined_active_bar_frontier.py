from __future__ import annotations

"""Audit the combined class / Support / Mages Guild active-bar frontier for Extreme Magicka Recovery.

The earlier class-route proof optimized all six active-bar slots only across equipped
class lines. ESO does not require every active-bar slot to contain a class ability.
This audit therefore recomputes the legal six-slot frontier while allowing Alliance
War Support and Mages Guild abilities to compete for bar space.

It deliberately treats the previously proven Torc named-gear result as an input
checkpoint and reuses canonical passive math, same-build Max Magicka, Champion Point,
class-route, skill-universe, armor, Mundus, jewelry, provisioning, and racial owners.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_MAGICKA_RECOVERY, BaseCharacterCalculator, ResourceInputs
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.passive_math import (
    arcanist_wellspring_recovery,
    light_armor_magicka_recovery_percent,
    mages_guild_magicka_controller_percent,
    support_magicka_aid_recovery_percent,
    warden_flourish_recovery_percent,
)
from services.extreme_divines_mundus_objective_service import ExtremeDivinesMundusObjectiveService
from services.extreme_recovery_class_route_frontier_service import ExtremeRecoveryClassRouteFrontierService
from services.extreme_recovery_jewelry_projection_service import ExtremeRecoveryJewelryProjectionService
from services.extreme_recovery_provisioning_projection_service import ExtremeRecoveryProvisioningProjectionService
from services.extreme_skill_universe_service import ExtremeSkillUniverseService
from tools.audit_extreme_magicka_recovery_same_build_enlivening import (
    _best_racial_recovery_witness,
    _build_max_magicka_witness,
    _recovery_cp_loadout,
    exact_enlivening_value,
)

OBJECTIVE = "magicka_recovery"
EXPECTED_ROUTE_IDS = frozenset({"animal_companions", "curative_runeforms", "shadow"})


@dataclass(frozen=True)
class LineCapacity:
    line_id: str
    normal: int
    ultimate: int

    @property
    def total(self) -> int:
        return min(5, self.normal) + min(1, self.ultimate)


@dataclass(frozen=True)
class ActiveBarCandidate:
    base_class: str
    equipped_skill_lines: tuple[str, ...]
    is_pure_class: bool
    animal_slots: int
    soldier_slots: int
    support_slots: int
    mages_slots: int
    max_magicka: float
    enlivening: float
    cp_total: float
    pre_percent_total: float
    total_percent: float
    final_value: float
    mastery_projected_delta: float


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--torc-structural", type=float, default=1032.0)
    parser.add_argument("--torc-special", type=float, default=450.0)
    return parser


def _line_id(value: object) -> str:
    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _family_key(row) -> tuple[int, str]:
    return (int(row.base_ability_id or row.skill_id), _line_id(row.skill_line))


def _capacity(universe: ExtremeSkillUniverseService, line_id: str) -> LineCapacity:
    normal: set[tuple[int, str]] = set()
    ultimate: set[tuple[int, str]] = set()
    wanted = _line_id(line_id)
    for row in universe.actives():
        if _line_id(row.skill_line) != wanted or row.is_crafted or row.max_rank_ability_id is None:
            continue
        target = ultimate if "ultimate" in str(row.skill_type or "").casefold() else normal
        target.add(_family_key(row))
    return LineCapacity(wanted, len(normal), len(ultimate))


def _same_build_max_magicka(base_witness, mages_slots: int) -> float:
    trace = BaseCharacterCalculator().max_magicka(
        ResourceInputs(
            attribute_points=64,
            item_flat=float(base_witness.armor_glyph_flat),
            food_flat=float(base_witness.provisioning_flat),
            champion_flat=float(base_witness.arcane_supremacy_flat),
            race_flat=float(base_witness.race_flat),
            skill_percent=mages_guild_magicka_controller_percent(mages_slots),
            other_percent=float(base_witness.undaunted_percent + base_witness.provisioning_percent),
        )
    )
    return float(trace.raw_value)


def _max_line_slots(capacity: LineCapacity, *, ultimate_claimed: bool) -> int:
    return min(5, capacity.normal) + (0 if ultimate_claimed else min(1, capacity.ultimate))


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    unresolved: list[str] = []

    jewelry = ExtremeRecoveryJewelryProjectionService(
        JewelryGlyphEffectRepository(database), JewelryTraitRepository(database)
    ).build(OBJECTIVE)
    unresolved.extend(jewelry.unresolved)
    jewelry_flat = float(jewelry.three_slot_infused_flat or 0.0)

    provisioning = ExtremeRecoveryProvisioningProjectionService.build(database, objective_key=OBJECTIVE)
    unresolved.extend(provisioning.unresolved)
    drink = provisioning.drink
    if drink is None:
        unresolved.append("No reviewed Magicka Recovery provisioning winner")
    drink_flat = 0.0 if drink is None else float(drink.delta)

    atronach = ExtremeDivinesMundusObjectiveService.candidate_for_name(
        MundusRepository(database, initialize=False),
        "The Atronach",
        OBJECTIVE,
        armor_divines_count=7,
    )
    atronach_flat = float(atronach.projected_delta or 0.0)
    if atronach.projected_delta is None:
        unresolved.extend(atronach.mundus.unresolved)

    race_row, race_unresolved, _ = _best_racial_recovery_witness(database)
    unresolved.extend(f"racial Recovery unresolved: {item}" for item in race_unresolved)
    race_flat = 0.0 if race_row is None else float(race_row[0])
    if race_row is None:
        unresolved.append("No positive racial Magicka Recovery witness")

    structural_cp, structural_cp_unresolved = _recovery_cp_loadout(database, enlivening_value=150.0)
    unresolved.extend(structural_cp_unresolved)
    base_witness = None
    if drink is not None:
        base_witness, witness_unresolved, arcane_legal = _build_max_magicka_witness(
            database,
            recovery_cp_loadout=structural_cp,
            provisioning_name=drink.name,
        )
        unresolved.extend(witness_unresolved)
        if not arcane_legal:
            unresolved.append("Arcane Supremacy is not compatible with Recovery CP loadout")
    if base_witness is None:
        unresolved.append("Same-build Max Magicka witness unavailable")

    fixed_without_cp = (
        float(BASE_MAGICKA_RECOVERY)
        + jewelry_flat
        + drink_flat
        + atronach_flat
        + race_flat
        + float(args.torc_structural)
        + float(args.torc_special)
    )

    universe = ExtremeSkillUniverseService(database)
    support_capacity = _capacity(universe, "Support")
    mages_capacity = _capacity(universe, "Mages Guild")
    animal_capacity = _capacity(universe, "Animal Companions")
    soldier_capacity = _capacity(universe, "Soldier of Apocrypha")

    if support_capacity.total < 5:
        unresolved.append(
            f"Support line exposes only {support_capacity.total} distinct reviewed bar slots; five-slot Magicka Aid witness unavailable"
        )

    route_service = ExtremeRecoveryClassRouteFrontierService(database)
    rows: list[ActiveBarCandidate] = []

    # Enumerate counts first; exact skill identities are unnecessary once the
    # canonical universe proves enough distinct normal/Ultimate families exist.
    for mages_slots in range(0, min(6, mages_capacity.total) + 1):
        max_magicka = _same_build_max_magicka(base_witness, mages_slots) if base_witness else 0.0
        enlivening = exact_enlivening_value(max_magicka)
        cp, cp_unresolved = _recovery_cp_loadout(database, enlivening_value=enlivening)
        unresolved.extend(cp_unresolved)
        cp_total = float(cp.total_flat_ceiling)
        reference = fixed_without_cp + cp_total
        frontier = route_service.frontier(OBJECTIVE, reference_value=reference)

        for route in frontier.candidates:
            line_ids = frozenset(_line_id(line) for line in route.equipped_skill_lines)
            has_animal = "animal_companions" in line_ids
            has_soldier = "soldier_of_apocrypha" in line_ids

            for animal_slots in range(0, min(6, animal_capacity.total if has_animal else 0) + 1):
                for soldier_slots in range(0, min(6 - animal_slots, soldier_capacity.total if has_soldier else 0) + 1):
                    remaining = 6 - animal_slots - soldier_slots - mages_slots
                    if remaining < 0:
                        continue
                    support_slots = remaining
                    if support_slots > support_capacity.total:
                        continue

                    # At most one Ultimate may appear across all counted categories.
                    # If a category count exceeds its normal capacity it must consume
                    # the Ultimate slot. Reject states that require two such claims.
                    ultimate_claims = sum(
                        int(count > capacity.normal)
                        for count, capacity in (
                            (animal_slots, animal_capacity),
                            (soldier_slots, soldier_capacity),
                            (support_slots, support_capacity),
                            (mages_slots, mages_capacity),
                        )
                        if count > 0
                    )
                    if ultimate_claims > 1:
                        continue
                    if any(
                        count > capacity.total
                        for count, capacity in (
                            (animal_slots, animal_capacity),
                            (soldier_slots, soldier_capacity),
                            (support_slots, support_capacity),
                            (mages_slots, mages_capacity),
                        )
                    ):
                        continue

                    class_flat = float(route.static_flat)
                    class_percent = float(route.static_percent)
                    class_flat += arcanist_wellspring_recovery(soldier_slots)
                    class_percent += warden_flourish_recovery_percent(animal_slots)
                    support_percent = support_magicka_aid_recovery_percent(support_slots)
                    light_percent = light_armor_magicka_recovery_percent(7)

                    # Class Mastery is already projected by the canonical route owner.
                    # For current reviewed Recovery masteries this is a flat projected
                    # runtime ceiling; retain it as additive for candidate comparison.
                    mastery = float(route.mastery_projected_delta)
                    pre_percent = reference + class_flat + mastery
                    total_percent = light_percent + class_percent + support_percent
                    final_value = pre_percent * (1.0 + total_percent)
                    rows.append(
                        ActiveBarCandidate(
                            base_class=route.base_class,
                            equipped_skill_lines=route.equipped_skill_lines,
                            is_pure_class=route.is_pure_class,
                            animal_slots=animal_slots,
                            soldier_slots=soldier_slots,
                            support_slots=support_slots,
                            mages_slots=mages_slots,
                            max_magicka=max_magicka,
                            enlivening=enlivening,
                            cp_total=cp_total,
                            pre_percent_total=pre_percent,
                            total_percent=total_percent,
                            final_value=final_value,
                            mastery_projected_delta=mastery,
                        )
                    )

    ranked = tuple(sorted(rows, key=lambda row: (-row.final_value, row.base_class, row.equipped_skill_lines)))
    winner = ranked[0] if ranked else None
    runner_up = ranked[1] if len(ranked) > 1 else None
    winner_ids = frozenset(_line_id(line) for line in winner.equipped_skill_lines) if winner else frozenset()
    winner_expected_route = bool(winner and winner_ids == EXPECTED_ROUTE_IDS)
    winner_uses_five_support = bool(winner and winner.support_slots == 5 and winner.animal_slots == 1)
    support_capacity_proven = support_capacity.total >= 5
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        winner is not None
        and winner_expected_route
        and winner_uses_five_support
        and support_capacity_proven
        and not unique_unresolved
    )

    print("EXTREME MAGICKA RECOVERY COMBINED ACTIVE-BAR FRONTIER")
    print(f"database={database}")
    print(f"torc_structural_checkpoint={args.torc_structural:.3f}")
    print(f"torc_special_checkpoint={args.torc_special:.3f}")
    print(f"support_capacity_normal={support_capacity.normal} ultimate={support_capacity.ultimate} total={support_capacity.total}")
    print(f"mages_capacity_normal={mages_capacity.normal} ultimate={mages_capacity.ultimate} total={mages_capacity.total}")
    print(f"animal_capacity_normal={animal_capacity.normal} ultimate={animal_capacity.ultimate} total={animal_capacity.total}")
    print(f"soldier_capacity_normal={soldier_capacity.normal} ultimate={soldier_capacity.ultimate} total={soldier_capacity.total}")
    print(f"fixed_without_cp={fixed_without_cp:.3f}")
    print()
    print("TOP ACTIVE-BAR CANDIDATES")
    for index, row in enumerate(ranked[:12], start=1):
        print(
            f"rank={index} base_class={row.base_class!r} lines={tuple(_line_id(x) for x in row.equipped_skill_lines)!r} "
            f"animal={row.animal_slots} soldier={row.soldier_slots} support={row.support_slots} mages={row.mages_slots} "
            f"max_magicka={row.max_magicka:.3f} enlivening={row.enlivening:.3f} cp={row.cp_total:.3f} "
            f"pre_percent={row.pre_percent_total:.3f} total_percent={row.total_percent * 100.0:.3f} "
            f"mastery={row.mastery_projected_delta:.3f} final={row.final_value:.3f}"
        )
    print()
    print("PROOF GATES")
    print(f"support_five_slot_witness_available={support_capacity_proven}")
    print(f"winner_expected_class_route={winner_expected_route}")
    print(f"winner_one_animal_five_support={winner_uses_five_support}")
    print(f"winner_mages_slots={winner.mages_slots if winner else -1}")
    print(f"winner_final={winner.final_value if winner else 0.0:.3f}")
    print(f"runner_up_final={runner_up.final_value if runner_up else 0.0:.3f}")
    print(f"minimum_top_margin={(winner.final_value - runner_up.final_value) if winner and runner_up else 0.0:.3f}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"combined_active_bar_frontier_closed={closed}")
    if closed:
        print("NEXT_STEP=recompose contextual Recovery percentages and final score using the corrected five-Support-slot winner")
    else:
        print("NEXT_STEP=close only the reported combined active-bar blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
