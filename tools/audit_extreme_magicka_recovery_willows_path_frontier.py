from __future__ import annotations

"""Constructively compare Willow's Path against the closed ordinary Recovery incumbent.

Willow's Path is a percentage-Recovery branch, so it cannot be compared to flat gear
by pretending 18% is another flat bonus. This audit composes it at the shared percent
layer. The loose seven-unit coexistence capacity bound remains an upper bound only;
a separate constrained named-gear search requires Willow's Path physically and
externalizes its percentage mechanic so the companion package is an actual legal
seven-Light witness.

The physical witness is rescored with exact remaining Enlivening headroom. We only
need a constructive Willow lower bound that beats the closed ordinary incumbent here,
not the exact global Willow maximum. If the legal witness wins at this conservative
shared floor, later nonnegative flat sources can only widen its lead because Willow's
total Recovery slope is 18 percentage points higher.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_MAGICKA_RECOVERY
from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.passive_math import undaunted_mettle_resource_percent
from minmax.stat_ids import StatId
from services.extreme_armor_weight_filtered_slot_eligibility_service import ExtremeArmorWeightFilteredSlotEligibilityService
from services.extreme_divines_mundus_objective_service import ExtremeDivinesMundusObjectiveService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_recovery_jewelry_projection_service import ExtremeRecoveryJewelryProjectionService
from services.extreme_recovery_provisioning_projection_service import ExtremeRecoveryProvisioningProjectionService
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import _same_build_max_magicka_for_weight_types
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import aggregate_recovery_semantic_branch
from tools.audit_extreme_magicka_recovery_max_magicka_only_named_gear_dominance import _constrained_effective_recovery_search
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    RECOVERY_MULTIPLIER,
    build_pair_scores,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import (
    _best_racial_recovery_witness,
    _recovery_cp_loadout,
    exact_enlivening_value,
)

TARGET_NAME = "Willow's Path"
TARGET_PIECES = 5
ORDINARY_INCUMBENT = 1332.0


@dataclass(frozen=True)
class CapacitySelection:
    optimistic_score: float
    pairs: tuple[tuple[int, int], ...]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def best_distinct_capacity_selection(*, challenger_set_id: int, pair_scores, capacity: int = 7) -> CapacitySelection:
    """Return one exact distinct-set knapsack witness for the loose capacity bound."""
    mutable: dict[int, list[tuple[int, float]]] = {}
    for (set_id, count), score in pair_scores.items():
        set_id = int(set_id)
        count = int(count)
        if set_id == int(challenger_set_id) or not score.ordinary or count <= 0 or count > int(capacity):
            continue
        value = max(0.0, float(score.optimistic_effective_recovery))
        if value <= 0.0:
            continue
        mutable.setdefault(set_id, []).append((count, value))
    choices_by_set = {
        set_id: tuple(sorted(rows, key=lambda row: (row[0], -row[1])))
        for set_id, rows in mutable.items()
    }

    dp: list[tuple[float, tuple[tuple[int, int], ...]]] = [(0.0, ()) for _ in range(capacity + 1)]
    for set_id in sorted(choices_by_set):
        previous = tuple(dp)
        updated = list(previous)
        for used in range(capacity + 1):
            base_score, base_pairs = previous[used]
            for count, value in choices_by_set[set_id]:
                target = used + count
                if target > capacity:
                    continue
                candidate_score = base_score + value
                candidate_pairs = (*base_pairs, (set_id, count))
                current_score, current_pairs = updated[target]
                if candidate_score > current_score + 1e-9 or (
                    abs(candidate_score - current_score) <= 1e-9 and candidate_pairs < current_pairs
                ):
                    updated[target] = (candidate_score, candidate_pairs)
        dp = updated

    score, pairs = max(dp, key=lambda row: (row[0], tuple(-x for pair in row[1] for x in pair)))
    return CapacitySelection(float(score), tuple(pairs))


def mapped_positive_recovery_flat(evidence) -> float:
    return sum(
        float(effect.value)
        for effect in getattr(evidence.candidate, "source_effects", ())
        if effect.stat is StatId.MAGICKA_RECOVERY
        and effect.operation is EffectOperation.ADD
        and float(effect.value) > 0.0
    )


def companion_pair_totals(realization, pair_scores, *, excluded_set_id: int) -> tuple[float, float]:
    recovery = 0.0
    max_magicka = 0.0
    for set_id, count in zip(realization.set_ids, realization.counts):
        if int(set_id) == int(excluded_set_id):
            continue
        score = pair_scores.get((int(set_id), int(count)))
        if score is None or not score.ordinary:
            continue
        recovery += float(score.direct_recovery)
        max_magicka += float(score.max_magicka_flat)
    return recovery, max_magicka


def compose_final(*, shared_flat: float, gear_flat: float, multiplier: float) -> float:
    return (float(shared_flat) + float(gear_flat)) * float(multiplier)


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology_catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    raw_eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database,
        raw_eligibility,
        required_armor_weight="Light",
    )
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    max_magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)

    base_max_magicka, max_magicka_unresolved = _same_build_max_magicka_for_weight_types(database, 1)
    unresolved.extend(max_magicka_unresolved)
    base_enlivening = exact_enlivening_value(base_max_magicka)
    remaining_headroom = max(0.0, 150.0 - base_enlivening)
    undaunted_multiplier = 1.0 + undaunted_mettle_resource_percent(1)
    conversion = 0.005 * undaunted_multiplier

    pair_scores, merged = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=conversion,
    )
    recovery_rows = tuple(
        row for row in recovery.evidence
        if row.set_name.casefold() == TARGET_NAME.casefold() and int(row.piece_count) == TARGET_PIECES
    )
    if len(recovery_rows) != 1:
        unresolved.append(f"expected one {TARGET_NAME} Recovery 5pc row, found {len(recovery_rows)}")
        target = None
        target_id = -1
    else:
        target = recovery_rows[0]
        target_id = int(target.set_id)

    branch = aggregate_recovery_semantic_branch(target) if target is not None else None
    willow_percent = 0.0
    if branch is None or branch.kind.value != "conditional_percent" or branch.percent_ceiling is None:
        unresolved.append("Willow's Path percentage Recovery semantics unresolved")
    else:
        willow_percent = float(branch.percent_ceiling) / 100.0

    own_flat = mapped_positive_recovery_flat(target) if target is not None else 0.0
    loose_selection = best_distinct_capacity_selection(
        challenger_set_id=target_id,
        pair_scores=pair_scores,
        capacity=12 - TARGET_PIECES,
    ) if target_id >= 0 else CapacitySelection(0.0, ())

    constrained = None
    if target_id >= 0:
        challenger = SimpleNamespace(
            set_id=target_id,
            set_name=TARGET_NAME,
            piece_count=TARGET_PIECES,
        )
        constrained, constrained_unresolved = _constrained_effective_recovery_search(
            challenger=challenger,
            topology=topology_catalog,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            merged=merged,
            pair_scores=pair_scores,
        )
        unresolved.extend(constrained_unresolved)

    physical_optimistic = None
    realization = None
    if constrained is not None and constrained.winner_found:
        physical_optimistic = float(constrained.best_exact_flat_delta or 0.0)
        realization = constrained.realizations[0]
    else:
        unresolved.append("no physically realizable seven-Light Willow coexistence witness")

    selected_direct = 0.0
    selected_max_magicka = 0.0
    if realization is not None:
        selected_direct, selected_max_magicka = companion_pair_totals(
            realization,
            pair_scores,
            excluded_set_id=target_id,
        )
    target_score = pair_scores.get((target_id, TARGET_PIECES)) if target_id >= 0 else None
    own_max_magicka = float(target_score.max_magicka_flat) if target_score is not None else 0.0
    exact_extra_enlivening = min(
        remaining_headroom,
        max(0.0, selected_max_magicka + own_max_magicka) * conversion,
    )
    structural_exact = selected_direct + exact_extra_enlivening

    jewelry = ExtremeRecoveryJewelryProjectionService(
        JewelryGlyphEffectRepository(database), JewelryTraitRepository(database)
    ).build(OBJECTIVE)
    unresolved.extend(jewelry.unresolved)
    three_infused = float(jewelry.three_slot_infused_flat or 0.0)

    provisioning = ExtremeRecoveryProvisioningProjectionService.build(database, objective_key=OBJECTIVE)
    unresolved.extend(provisioning.unresolved)
    if provisioning.drink is None:
        unresolved.append("no reviewed Magicka Recovery provisioning winner")
        drink = 0.0
    else:
        drink = float(provisioning.drink.delta)

    atronach = ExtremeDivinesMundusObjectiveService.candidate_for_name(
        MundusRepository(database, initialize=False),
        "The Atronach",
        OBJECTIVE,
        armor_divines_count=7,
    )
    if atronach.projected_delta is None:
        unresolved.extend(atronach.mundus.unresolved)
        atronach_delta = 0.0
    else:
        atronach_delta = float(atronach.projected_delta)

    cp, cp_unresolved = _recovery_cp_loadout(database, enlivening_value=base_enlivening)
    unresolved.extend(cp_unresolved)
    cp_total = float(cp.total_flat_ceiling)

    race_row, race_unresolved, _ = _best_racial_recovery_witness(database)
    unresolved.extend(f"racial Recovery unresolved: {item}" for item in race_unresolved)
    if race_row is None:
        unresolved.append("no positive racial Magicka Recovery witness")
        race_flat = 0.0
    else:
        race_flat = float(race_row[0])

    shared_flat = (
        float(BASE_MAGICKA_RECOVERY)
        + three_infused
        + drink
        + atronach_delta
        + cp_total
        + race_flat
    )
    ordinary_final = compose_final(
        shared_flat=shared_flat,
        gear_flat=ORDINARY_INCUMBENT,
        multiplier=RECOVERY_MULTIPLIER,
    )
    willow_multiplier = RECOVERY_MULTIPLIER + willow_percent
    willow_gear_flat = structural_exact + own_flat
    willow_final = compose_final(
        shared_flat=shared_flat,
        gear_flat=willow_gear_flat,
        multiplier=willow_multiplier,
    )
    margin = willow_final - ordinary_final
    future_flat_slope_advantage = willow_multiplier - RECOVERY_MULTIPLIER
    willow_wins = realization is not None and margin > 1e-9
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        not unique_unresolved
        and branch is not None
        and realization is not None
        and willow_wins
        and future_flat_slope_advantage > 0.0
    )

    names = {int(row.set_id): row.name for row in filtered.catalog.sets}
    print("EXTREME MAGICKA RECOVERY WILLOW'S PATH FRONTIER")
    print(f"database={database}")
    print(f"ordinary_incumbent_prepercent_recovery={ORDINARY_INCUMBENT:.3f}")
    print(f"base_max_magicka={base_max_magicka:.3f}")
    print(f"base_enlivening={base_enlivening:.3f}")
    print(f"remaining_enlivening_headroom={remaining_headroom:.3f}")
    print(f"willow_percent={willow_percent * 100.0:.3f}")
    print(f"willow_own_mapped_flat={own_flat:.3f}")
    print(f"capacity_optimistic_score={loose_selection.optimistic_score:.3f}")
    print(f"capacity_selection={tuple((names.get(set_id, str(set_id)), count) for set_id, count in loose_selection.pairs)!r}")
    print(f"physical_constrained_optimistic_score={float(physical_optimistic or 0.0):.3f}")
    print(f"physical_capacity_witness={realization is not None}")
    if realization is not None:
        print(f"physical_witness_sets={tuple(zip(realization.set_names, realization.counts))!r}")
    print(f"selected_direct_recovery={selected_direct:.3f}")
    print(f"selected_max_magicka_flat={selected_max_magicka:.3f}")
    print(f"exact_extra_enlivening={exact_extra_enlivening:.3f}")
    print(f"structural_exact_prepercent={structural_exact:.3f}")
    print(f"shared_flat_floor={shared_flat:.3f}")
    print(f"ordinary_multiplier={RECOVERY_MULTIPLIER:.6f}")
    print(f"willow_multiplier={willow_multiplier:.6f}")
    print(f"ordinary_final={ordinary_final:.3f}")
    print(f"willow_final={willow_final:.3f}")
    print(f"willow_margin={margin:.3f}")
    print(f"future_flat_slope_advantage={future_flat_slope_advantage:.6f}")
    if realization is not None:
        print("assignments=" + repr(tuple((row.slot, row.set_name, row.weapon_type) for row in realization.assignments)))
    print()
    print("PROOF GATES")
    print(f"percent_semantics_resolved={branch is not None and branch.kind.value == 'conditional_percent'}")
    print(f"physical_capacity_witness={realization is not None}")
    print(f"willow_beats_ordinary_incumbent={willow_wins}")
    print(f"future_nonnegative_flat_lock={willow_wins and future_flat_slope_advantage > 0.0}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"willows_path_branch_closed={closed}")
    print(
        "NEXT_STEP=promote the legal Willow's Path witness as the named-gear incumbent lower bound and rebase surviving flat/special challengers"
        if closed else
        "NEXT_STEP=close only the reported Willow's Path blockers"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
