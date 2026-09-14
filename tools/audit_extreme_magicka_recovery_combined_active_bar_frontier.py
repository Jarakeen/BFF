from __future__ import annotations

"""Audit the combined class / Support / Mages Guild active-bar frontier for Extreme Magicka Recovery.

The earlier class-route proof optimized all six active-bar positions only across equipped
class lines. ESO does not require every active-bar position to contain a class ability,
but the bar topology is also not six interchangeable skill slots: it is five normal
ability slots plus one Ultimate slot. This audit therefore recomputes the legal frontier
while allowing Alliance War Support and Mages Guild abilities to compete for the five
normal slots and admitting an objective-relevant sixth counted ability only when a
canonical Ultimate from that same counted line exists.

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
NORMAL_BAR_SLOTS = 5
ULTIMATE_BAR_SLOTS = 1


@dataclass(frozen=True)
class LineCapacity:
    line_id: str
    normal: int
    ultimate: int

    @property
    def total(self) -> int:
        return min(NORMAL_BAR_SLOTS, self.normal) + min(ULTIMATE_BAR_SLOTS, self.ultimate)


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


def _bar_shape_legal(
    counted: tuple[tuple[int, LineCapacity], ...],
) -> bool:
    """Return whether counted objective skills fit 5 normal slots + 1 Ultimate.

    Uncounted filler skills are allowed. A counted category may consume the Ultimate
    slot only when its canonical line actually exposes an Ultimate family. This is an
    existence proof over slot *types*, not merely a six-position cardinality check.
    """

    rows = tuple((max(0, int(count)), capacity) for count, capacity in counted)
    total = sum(count for count, _ in rows)
    if total > NORMAL_BAR_SLOTS + ULTIMATE_BAR_SLOTS:
        return False
    if any(count > capacity.total for count, capacity in rows):
        return False

    # Try an all-normal realization first. This is sufficient whenever every
    # counted category fits its normal family supply and at most five are counted.
    if total <= NORMAL_BAR_SLOTS and all(count <= capacity.normal for count, capacity in rows):
        return True

    # Otherwise exactly one counted category must own the single Ultimate slot.
    for index, (count, capacity) in enumerate(rows):
        if count <= 0 or capacity.ultimate <= 0:
            continue
        normal_required = 0
        legal = True
        for other_index, (other_count, other_capacity) in enumerate(rows):
            required = other_count - 1 if other_index == index else other_count
            if required < 0 or required > other_capacity.normal:
                legal = False
                break
            normal_required += required
        if legal and normal_required <= NORMAL_BAR_SLOTS:
            return True
    return False


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

    if support_capacity.normal < 4:
        unresolved.append(
            f"Support line exposes only {support_capacity.normal} distinct reviewed normal slots; four-slot Magicka Aid witness unavailable"
        )

    six_normal_rejected = not _bar_shape_legal(
        (
            (1, animal_capacity),
            (0, soldier_capacity),
            (5, support_capacity),
            (0, mages_capacity),
        )
    )
    one_animal_four_support_legal = _bar_shape_legal(
        (
            (1, animal_capacity),
            (0, soldier_capacity),
            (4, support_capacity),
            (0, mages_capacity),
        )
    )
    if not six_normal_rejected:
        unresolved.append("Six-normal-skill state was not rejected by active-bar topology")
    if not one_animal_four_support_legal:
        unresolved.append("One-Animal/four-Support normal-slot witness is not physically legal")

    route_service = ExtremeRecoveryClassRouteFrontierService(database)
    rows: list[ActiveBarCandidate] = []

    # Enumerate all objective-relevant counted skills. Any unused normal or Ultimate
    # position may hold an irrelevant filler skill; objective score never assumes that
    # filler contributes Recovery.
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
            animal_limit = min(6, animal_capacity.total if has_animal else 0)
            soldier_limit = min(6, soldier_capacity.total if has_soldier else 0)

            for animal_slots in range(0, animal_limit + 1):
                for soldier_slots in range(0, soldier_limit + 1):
                    for support_slots in range(0, min(6, support_capacity.total) + 1):
                        counted = (
                            (animal_slots, animal_capacity),
                            (soldier_slots, soldier_capacity),
                            (support_slots, support_capacity),
                            (mages_slots, mages_capacity),
                        )
                        if not _bar_shape_legal(counted):
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

    # Base-class identity can tie for a subclassed route with no pure-class Mastery.
    # Report the next distinct objective state rather than treating that harmless
    # identity tie as a zero proof margin.
    distinct_rows: list[ActiveBarCandidate] = []
    seen_states: set[tuple[object, ...]] = set()
    for row in ranked:
        state = (
            tuple(_line_id(line) for line in row.equipped_skill_lines),
            row.is_pure_class,
            row.animal_slots,
            row.soldier_slots,
            row.support_slots,
            row.mages_slots,
            round(row.max_magicka, 9),
            round(row.pre_percent_total, 9),
            round(row.total_percent, 9),
            round(row.mastery_projected_delta, 9),
        )
        if state in seen_states:
            continue
        seen_states.add(state)
        distinct_rows.append(row)
    runner_up = distinct_rows[1] if len(distinct_rows) > 1 else None

    winner_ids = frozenset(_line_id(line) for line in winner.equipped_skill_lines) if winner else frozenset()
    winner_expected_route = bool(winner and winner_ids == EXPECTED_ROUTE_IDS)
    winner_uses_four_support = bool(winner and winner.support_slots == 4 and winner.animal_slots == 1)
    support_capacity_proven = support_capacity.normal >= 4
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        winner is not None
        and winner_expected_route
        and winner_uses_four_support
        and support_capacity_proven
        and six_normal_rejected
        and one_animal_four_support_legal
        and not unique_unresolved
    )

    print("EXTREME MAGICKA RECOVERY COMBINED ACTIVE-BAR FRONTIER")
    print(f"database={database}")
    print(f"torc_structural_checkpoint={args.torc_structural:.3f}")
    print(f"torc_special_checkpoint={args.torc_special:.3f}")
    print(f"normal_bar_slots={NORMAL_BAR_SLOTS} ultimate_bar_slots={ULTIMATE_BAR_SLOTS}")
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
    print(f"five_normal_plus_one_ultimate_topology=True")
    print(f"six_normal_state_rejected={six_normal_rejected}")
    print(f"one_animal_four_support_legal={one_animal_four_support_legal}")
    print(f"support_four_slot_witness_available={support_capacity_proven}")
    print(f"winner_expected_class_route={winner_expected_route}")
    print(f"winner_one_animal_four_support={winner_uses_four_support}")
    print(f"winner_mages_slots={winner.mages_slots if winner else -1}")
    print(f"winner_final={winner.final_value if winner else 0.0:.3f}")
    print(f"runner_up_distinct_final={runner_up.final_value if runner_up else 0.0:.3f}")
    print(f"minimum_distinct_margin={(winner.final_value - runner_up.final_value) if winner and runner_up else 0.0:.3f}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"combined_active_bar_frontier_closed={closed}")
    if closed:
        print("NEXT_STEP=add legal named-buff skill sources and contextual Recovery states to the corrected five-normal-slot winner")
    else:
        print("NEXT_STEP=close only the reported combined active-bar blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
