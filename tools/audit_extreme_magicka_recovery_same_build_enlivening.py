from __future__ import annotations

"""Prove a three-Infused same-build Enlivening witness for Extreme Magicka Recovery.

This audit intentionally reuses canonical Max Magicka, Recovery, provisioning,
Champion Point, Mundus, class-route, and skill-slot owners. It first constructs a
Recovery lower bound that does not depend on Enlivening Overflow. If that lower
bound already locks the high-reference class route, it then builds one conservative
same-build Max Magicka witness, scores Enlivening exactly, and recomposes the legal
Recovery Champion Point loadout.

The witness does not need to reach Enlivening Overflow's 150-point cap. A legal
below-cap value is sufficient when the class route is already globally locked and
the exact CP loadout remains legal at that value.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import (
    BASE_MAGICKA_RECOVERY,
    BaseCharacterCalculator,
    ResourceInputs,
)
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.conditional_recovery import (
    ENLIVENING_OVERFLOW_MAX_BONUS,
    ENLIVENING_OVERFLOW_MAX_MAGICKA_PERCENT,
)
from minmax.effects import EffectOperation
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.passive_math import undaunted_mettle_resource_percent
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId
from services.champion_point_loadout_service import (
    CHAMPION_POINT_SLOTS_PER_DISCIPLINE,
    ChampionPointLoadoutCandidate,
    ChampionPointLoadoutService,
)
from services.extreme_champion_point_objective_service import ExtremeChampionPointObjectiveService
from services.extreme_divines_mundus_objective_service import ExtremeDivinesMundusObjectiveService
from services.extreme_passive_projection_service import ExtremePassiveProjectionService
from services.extreme_recovery_champion_point_branch_service import (
    ExtremeRecoveryChampionPointBranchService,
)
from services.extreme_recovery_class_route_frontier_service import (
    ExtremeRecoveryClassRouteCandidate,
    ExtremeRecoveryClassRouteFrontierService,
)
from services.extreme_recovery_jewelry_projection_service import (
    ExtremeRecoveryJewelryProjectionService,
)
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)
from services.extreme_skill_universe_service import ExtremeSkillDomain, ExtremeSkillUniverseService
from tools.audit_extreme_health_recovery_final_record import (
    _armor_magicka_glyph_flat,
    _provisioning_magicka,
)

OBJECTIVE = "magicka_recovery"
EXPECTED_HIGH_REFERENCE_LINES = frozenset(
    {"animal_companions", "curative_runeforms", "shadow"}
)


@dataclass(frozen=True)
class MaxMagickaWitness:
    race_name: str
    race_flat: float
    armor_glyph_flat: float
    provisioning_name: str
    provisioning_flat: float
    provisioning_percent: float
    arcane_supremacy_flat: float
    mages_guild_slots: int
    mages_guild_percent: float
    undaunted_percent: float
    raw_max_magicka: float
    displayed_max_magicka: int


@dataclass(frozen=True)
class RouteLockProof:
    winner: ExtremeRecoveryClassRouteCandidate | None
    winner_slope: float | None
    minimum_margin: float | None
    globally_locked_above_reference: bool


def exact_enlivening_value(max_magicka: float) -> float:
    return min(
        float(ENLIVENING_OVERFLOW_MAX_BONUS),
        max(0.0, float(max_magicka)) * float(ENLIVENING_OVERFLOW_MAX_MAGICKA_PERCENT),
    )


def _line_id(value: object) -> str:
    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def route_line_ids(row: ExtremeRecoveryClassRouteCandidate | None) -> frozenset[str]:
    if row is None:
        return frozenset()
    return frozenset(_line_id(line) for line in row.equipped_skill_lines)


def _candidate_identity(row: ExtremeRecoveryClassRouteCandidate) -> tuple:
    return (
        row.base_class,
        row.equipped_skill_lines,
        row.is_pure_class,
        row.slot_counts,
    )


def prove_route_lock(
    service: ExtremeRecoveryClassRouteFrontierService,
    *,
    reference_value: float,
) -> RouteLockProof:
    base = service.frontier(OBJECTIVE, reference_value=reference_value)
    next_point = service.frontier(OBJECTIVE, reference_value=reference_value + 1.0)
    winner = base.best_reviewed_candidate
    if winner is None:
        return RouteLockProof(None, None, None, False)

    next_by_identity = {_candidate_identity(row): row for row in next_point.candidates}
    winner_next = next_by_identity.get(_candidate_identity(winner))
    if winner_next is None:
        return RouteLockProof(winner, None, None, False)

    winner_slope = float(winner_next.projected_delta) - float(winner.projected_delta)
    minimum_margin = float("inf")
    locked = not winner.runtime_obligations

    for challenger in base.candidates:
        if _candidate_identity(challenger) == _candidate_identity(winner):
            continue
        challenger_next = next_by_identity.get(_candidate_identity(challenger))
        if challenger_next is None:
            locked = False
            continue
        margin = float(winner.projected_delta) - float(challenger.projected_delta)
        challenger_slope = (
            float(challenger_next.projected_delta) - float(challenger.projected_delta)
        )
        minimum_margin = min(minimum_margin, margin)
        if margin < -1e-9 or winner_slope + 1e-9 < challenger_slope:
            locked = False

    if minimum_margin == float("inf"):
        minimum_margin = 0.0
    return RouteLockProof(winner, winner_slope, minimum_margin, locked)


def _recovery_cp_loadout(
    database: Path,
    *,
    enlivening_value: float,
):
    repository = ChampionPointStaticRepository(database)
    candidates: list[ChampionPointLoadoutCandidate] = []
    unresolved: list[str] = []

    for record in repository.slottable_records():
        projected = ExtremeChampionPointObjectiveService.candidate_for_record(
            repository,
            record,
            OBJECTIVE,
        )
        if projected.reviewed_delta is not None:
            delta = float(projected.reviewed_delta)
            if delta > 0.0:
                candidates.append(
                    ChampionPointLoadoutCandidate(
                        name=record.name,
                        discipline_index=record.discipline_index,
                        flat_ceiling=delta,
                        condition=None,
                    )
                )
            continue

        if not ExtremeRecoveryChampionPointBranchService.mentions_objective_recovery(
            record.description,
            OBJECTIVE,
        ):
            continue
        branch = ExtremeRecoveryChampionPointBranchService.classify(record, OBJECTIVE)
        if not branch.complete or branch.flat_ceiling is None:
            unresolved.extend(f"{record.name}: {item}" for item in branch.unresolved)
            continue

        value = float(branch.flat_ceiling)
        condition = branch.condition
        if record.name.casefold() == "enlivening overflow":
            value = min(value, max(0.0, float(enlivening_value)))
            if value < float(ENLIVENING_OVERFLOW_MAX_BONUS) - 1e-9:
                condition = "overheal target"
        if value <= 0.0:
            continue

        candidates.append(
            ChampionPointLoadoutCandidate(
                name=record.name,
                discipline_index=record.discipline_index,
                flat_ceiling=value,
                condition=condition,
            )
        )

    loadout = ChampionPointLoadoutService.build(tuple(candidates))
    unresolved.extend(loadout.unresolved)
    return loadout, tuple(dict.fromkeys(unresolved))


def _best_racial_recovery_witness(database: Path):
    rows = []
    unresolved = []
    for passive in ExtremeSkillUniverseService(database).all_player_skills():
        if not passive.is_passive or passive.domain is not ExtremeSkillDomain.RACIAL:
            continue
        projection = ExtremePassiveProjectionService.project(passive)
        relevant = tuple(
            row for row in projection.contributions if row.objective_key == OBJECTIVE
        )
        if relevant:
            flat = sum(float(row.flat) for row in relevant)
            percent = sum(float(row.percent_of_reference) for row in relevant)
            if flat > 0.0 or percent > 0.0:
                rows.append((flat, percent, passive))
            continue
        text = f"{passive.name} {passive.description}".casefold()
        if "magicka recovery" in text or (
            "magicka" in text and "recovery" in text and "stamina" in text
        ):
            unresolved.append(passive.name)
    rows.sort(key=lambda item: (-item[0], -item[1], item[2].skill_line.casefold()))
    return (rows[0] if rows else None), tuple(dict.fromkeys(unresolved)), tuple(rows)


def _arcane_supremacy(database: Path) -> tuple[float, int | None, bool, tuple[str, ...]]:
    repository = ChampionPointStaticRepository(database)
    record = repository.get("Arcane Supremacy")
    if record is None:
        return 0.0, None, False, ("Arcane Supremacy canonical record missing",)
    effects, unresolved = repository.resolve(record.name, record.max_points)
    flat = sum(
        float(effect.value)
        for effect in effects
        if effect.stat is StatId.MAX_MAGICKA and effect.operation is EffectOperation.ADD
    )
    if flat <= 0.0:
        unresolved.append("Arcane Supremacy canonical Max Magicka value unresolved")
    return flat, record.discipline_index, record.is_slottable, tuple(dict.fromkeys(unresolved))


def _mundus_ordinary_recovery(database: Path) -> tuple[float, tuple[str, ...]]:
    row = ExtremeDivinesMundusObjectiveService.candidate_for_name(
        MundusRepository(database),
        "The Atronach",
        OBJECTIVE,
        armor_divines_count=0,
        shield_divines=False,
    )
    if row.projected_delta is None:
        return 0.0, tuple(row.mundus.unresolved)
    return float(row.projected_delta), tuple(row.mundus.unresolved)


def _build_max_magicka_witness(
    database: Path,
    *,
    recovery_cp_loadout,
    provisioning_name: str,
) -> tuple[MaxMagickaWitness | None, tuple[str, ...], bool]:
    unresolved: list[str] = []

    race_row, race_unresolved, _ = _best_racial_recovery_witness(database)
    unresolved.extend(f"racial Recovery unresolved: {name}" for name in race_unresolved)
    if race_row is None:
        unresolved.append("No positive racial Magicka Recovery witness resolved")
        return None, tuple(dict.fromkeys(unresolved)), False

    race_name = race_row[2].skill_line.removesuffix(" Skills")
    race_flat = float(
        RaceRepository(database).get_stat_map_by_name(race_name).get("max_magicka", 0.0)
    )

    armor_glyph_flat = _armor_magicka_glyph_flat(database)
    if armor_glyph_flat is None:
        unresolved.append("Canonical seven-piece Max Magicka armor glyph value unresolved")
        armor_glyph_flat = 0.0

    food_flat, food_percent, food_unresolved = _provisioning_magicka(
        database,
        provisioning_name,
    )
    unresolved.extend(food_unresolved)

    arcane_flat, arcane_discipline, arcane_slottable, arcane_unresolved = _arcane_supremacy(
        database
    )
    unresolved.extend(arcane_unresolved)

    recovery_counts = dict(recovery_cp_loadout.discipline_slot_counts)
    recovery_count_same_discipline = recovery_counts.get(arcane_discipline, 0)
    arcane_slot_legal = bool(
        arcane_slottable
        and arcane_discipline is not None
        and recovery_count_same_discipline + 1 <= CHAMPION_POINT_SLOTS_PER_DISCIPLINE
    )
    if not arcane_slot_legal:
        unresolved.append("Arcane Supremacy cannot coexist with the selected Recovery CP loadout")

    # The locked high-reference Recovery route consumes all six active-bar slots.
    # Magicka Controller therefore contributes exactly zero in this same-build
    # witness. Zero is a resolved legal state, not an unresolved mechanic.
    mages_guild_slots = 0
    mages_guild_percent = 0.0

    # One armor weight is deliberately conservative for Max Magicka and remains
    # compatible with a seven-light Recovery witness. More armor types would only
    # increase Undaunted Mettle, so they are unnecessary for this existence proof.
    undaunted_percent = undaunted_mettle_resource_percent(1)

    trace = BaseCharacterCalculator().max_magicka(
        ResourceInputs(
            attribute_points=64,
            item_flat=float(armor_glyph_flat),
            food_flat=float(food_flat),
            champion_flat=float(arcane_flat if arcane_slot_legal else 0.0),
            race_flat=float(race_flat),
            skill_percent=mages_guild_percent,
            other_percent=float(undaunted_percent + food_percent),
        )
    )
    witness = MaxMagickaWitness(
        race_name=race_name,
        race_flat=race_flat,
        armor_glyph_flat=float(armor_glyph_flat),
        provisioning_name=provisioning_name,
        provisioning_flat=food_flat,
        provisioning_percent=food_percent,
        arcane_supremacy_flat=float(arcane_flat if arcane_slot_legal else 0.0),
        mages_guild_slots=mages_guild_slots,
        mages_guild_percent=mages_guild_percent,
        undaunted_percent=undaunted_percent,
        raw_max_magicka=float(trace.raw_value),
        displayed_max_magicka=int(trace.final_value),
    )
    return witness, tuple(dict.fromkeys(unresolved)), arcane_slot_legal


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

    provisioning = ExtremeRecoveryProvisioningProjectionService.build(
        database,
        objective_key=OBJECTIVE,
    )
    unresolved.extend(provisioning.unresolved)
    drink = provisioning.drink
    if drink is None:
        unresolved.append("No reviewed Magicka Recovery drink winner resolved")
    drink_recovery = float(drink.delta) if drink else 0.0

    ordinary_atronach, mundus_unresolved = _mundus_ordinary_recovery(database)
    unresolved.extend(mundus_unresolved)

    cp_without_enlivening, cp_without_unresolved = _recovery_cp_loadout(
        database,
        enlivening_value=0.0,
    )
    unresolved.extend(cp_without_unresolved)
    non_enlivening_cp = float(cp_without_enlivening.total_flat_ceiling)

    preclass_floor_without_enlivening = (
        float(BASE_MAGICKA_RECOVERY)
        + three_infused
        + drink_recovery
        + ordinary_atronach
        + non_enlivening_cp
    )

    route_service = ExtremeRecoveryClassRouteFrontierService(database)
    route_lock = prove_route_lock(
        route_service,
        reference_value=preclass_floor_without_enlivening,
    )
    winner = route_lock.winner
    expected_route = route_line_ids(winner) == EXPECTED_HIGH_REFERENCE_LINES

    # Use the capped Recovery loadout only for structural CP-slot legality. The
    # exact Enlivening numeric value is recomputed from the same-build witness.
    structural_cp, structural_cp_unresolved = _recovery_cp_loadout(
        database,
        enlivening_value=float(ENLIVENING_OVERFLOW_MAX_BONUS),
    )
    unresolved.extend(structural_cp_unresolved)

    witness = None
    arcane_slot_legal = False
    if winner is not None and drink is not None:
        witness, witness_unresolved, arcane_slot_legal = _build_max_magicka_witness(
            database,
            recovery_cp_loadout=structural_cp,
            provisioning_name=drink.name,
        )
        unresolved.extend(witness_unresolved)

    same_build_max_magicka = float(witness.raw_max_magicka) if witness else 0.0
    enlivening_exact = exact_enlivening_value(same_build_max_magicka)
    cap_requirement = float(ENLIVENING_OVERFLOW_MAX_BONUS) / float(
        ENLIVENING_OVERFLOW_MAX_MAGICKA_PERCENT
    )
    cap_reached = same_build_max_magicka + 1e-9 >= cap_requirement
    enlivening_exact_scored = bool(
        witness is not None
        and enlivening_exact > 0.0
        and enlivening_exact <= float(ENLIVENING_OVERFLOW_MAX_BONUS) + 1e-9
    )

    exact_cp, exact_cp_unresolved = _recovery_cp_loadout(
        database,
        enlivening_value=enlivening_exact,
    )
    unresolved.extend(exact_cp_unresolved)
    exact_cp_total = float(exact_cp.total_flat_ceiling)
    exact_enlivening_rows = tuple(
        row for row in exact_cp.selected if row.name.casefold() == "enlivening overflow"
    )
    exact_enlivening_composed = bool(
        len(exact_enlivening_rows) == 1
        and abs(exact_enlivening_rows[0].flat_ceiling - enlivening_exact) <= 1e-9
    )

    preclass_floor_exact_cp = (
        float(BASE_MAGICKA_RECOVERY)
        + three_infused
        + drink_recovery
        + ordinary_atronach
        + exact_cp_total
    )
    exact_route_lock = prove_route_lock(
        route_service,
        reference_value=preclass_floor_exact_cp,
    )
    exact_winner = exact_route_lock.winner
    exact_expected_route = route_line_ids(exact_winner) == EXPECTED_HIGH_REFERENCE_LINES

    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        jewelry.denominator_proven
        and provisioning.comparison_proven
        and cp_without_enlivening.denominator_proven
        and structural_cp.denominator_proven
        and exact_cp.denominator_proven
        and expected_route
        and route_lock.globally_locked_above_reference
        and witness is not None
        and arcane_slot_legal
        and enlivening_exact_scored
        and exact_enlivening_composed
        and exact_expected_route
        and exact_route_lock.globally_locked_above_reference
        and not unique_unresolved
    )

    print("EXTREME MAGICKA RECOVERY SAME-BUILD ENLIVENING WITNESS")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    print("PRE-CLASS LOWER BOUND WITHOUT ENLIVENING")
    print(f"base_magicka_recovery={BASE_MAGICKA_RECOVERY:.3f}")
    print(f"three_infused_jewelry={three_infused:.3f}")
    print(f"provisioning={drink.name if drink else '<unresolved>'!r} delta={drink_recovery:.3f}")
    print(f"ordinary_atronach={ordinary_atronach:.3f}")
    print(f"legal_non_enlivening_cp={non_enlivening_cp:.3f}")
    print(f"preclass_floor_without_enlivening={preclass_floor_without_enlivening:.3f}")
    if winner is not None:
        print(f"lower_bound_route={winner.equipped_skill_lines!r}")
        print(f"lower_bound_route_ids={tuple(sorted(route_line_ids(winner)))!r}")
        print(f"lower_bound_route_slot_counts={winner.slot_counts!r}")
        print(f"lower_bound_route_delta={winner.projected_delta:.3f}")
        print(f"lower_bound_route_slope={float(route_lock.winner_slope or 0.0):.6f}")
        print(f"lower_bound_minimum_margin={float(route_lock.minimum_margin or 0.0):.3f}")
    print(f"route_globally_locked_above_lower_bound={route_lock.globally_locked_above_reference}")
    print()
    print("SAME-BUILD MAX MAGICKA WITNESS")
    if witness is not None:
        print(f"race={witness.race_name!r} max_magicka_flat={witness.race_flat:.3f}")
        print(f"seven_armor_magicka_glyphs={witness.armor_glyph_flat:.3f}")
        print(f"provisioning_max_magicka_flat={witness.provisioning_flat:.3f}")
        print(f"provisioning_max_magicka_percent={witness.provisioning_percent * 100.0:.3f}")
        print(f"arcane_supremacy_flat={witness.arcane_supremacy_flat:.3f}")
        print(f"mages_guild_slots={witness.mages_guild_slots}")
        print(f"magicka_controller_percent={witness.mages_guild_percent * 100.0:.3f}")
        print(f"undaunted_mettle_percent={witness.undaunted_percent * 100.0:.3f}")
        print(f"same_build_max_magicka_raw={witness.raw_max_magicka:.3f}")
        print(f"same_build_max_magicka_display={witness.displayed_max_magicka}")
    print(f"arcane_supremacy_slot_compatible={arcane_slot_legal}")
    print(f"enlivening_cap_requirement={cap_requirement:.3f}")
    print(f"enlivening_exact_value={enlivening_exact:.3f}")
    print(f"enlivening_cap_reached={cap_reached}")
    print(f"enlivening_exact_scored={enlivening_exact_scored}")
    print()
    print("EXACT CP / CLASS COMPOSITION")
    print(f"exact_legal_cp_total={exact_cp_total:.3f}")
    for row in exact_cp.selected:
        print(
            f"  selected_cp={row.name!r} discipline={row.discipline_index} "
            f"delta={row.flat_ceiling:.3f} condition={row.condition or '<none>'}"
        )
    print(f"exact_enlivening_composed={exact_enlivening_composed}")
    print(f"preclass_floor_with_exact_cp={preclass_floor_exact_cp:.3f}")
    if exact_winner is not None:
        print(f"exact_floor_route={exact_winner.equipped_skill_lines!r}")
        print(f"exact_floor_route_ids={tuple(sorted(route_line_ids(exact_winner)))!r}")
        print(f"exact_floor_route_delta={exact_winner.projected_delta:.3f}")
        print(f"exact_floor_route_slope={float(exact_route_lock.winner_slope or 0.0):.6f}")
    print(f"exact_route_globally_locked={exact_route_lock.globally_locked_above_reference}")
    print()
    print("PROOF GATES")
    print(f"three_infused_jewelry_denominator_proven={jewelry.denominator_proven}")
    print(f"provisioning_denominator_proven={provisioning.comparison_proven}")
    print(f"non_enlivening_cp_legality_proven={cp_without_enlivening.denominator_proven}")
    print(
        "high_reference_route_locked_without_enlivening="
        f"{expected_route and route_lock.globally_locked_above_reference}"
    )
    print(f"same_build_max_magicka_witness_proven={witness is not None}")
    print(f"arcane_supremacy_slot_compatible={arcane_slot_legal}")
    print(f"enlivening_exact_score_proven={enlivening_exact_scored}")
    print(f"exact_cp_legality_proven={exact_cp.denominator_proven}")
    print(f"exact_enlivening_composed={exact_enlivening_composed}")
    print(
        "exact_high_reference_route_locked="
        f"{exact_expected_route and exact_route_lock.globally_locked_above_reference}"
    )
    print(f"unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"magicka_recovery_same_build_enlivening_closed={closed}")
    if closed:
        print(
            "NEXT_STEP=compose armor/Mundus and ordinary named-gear Recovery frontiers "
            "onto the locked high-reference class route"
        )
    else:
        print("NEXT_STEP=close only the reported same-build Enlivening blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
