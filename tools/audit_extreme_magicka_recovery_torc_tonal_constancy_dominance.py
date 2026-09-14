from __future__ import annotations

"""Exact physical Torc of Tonal Constancy comparison against the legal Willow witness."""

import argparse
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_MAGICKA_RECOVERY
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.passive_math import undaunted_mettle_resource_percent
from services.extreme_armor_weight_filtered_slot_eligibility_service import ExtremeArmorWeightFilteredSlotEligibilityService
from services.extreme_divines_mundus_objective_service import ExtremeDivinesMundusObjectiveService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_special_named_gear_branch_service import ExtremeMaxResourceSpecialNamedGearBranchService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_recovery_jewelry_projection_service import ExtremeRecoveryJewelryProjectionService
from services.extreme_recovery_provisioning_projection_service import ExtremeRecoveryProvisioningProjectionService
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import _same_build_max_magicka_for_weight_types
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_dominance import direct_flat_upper_bound
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import aggregate_recovery_semantic_branch
from tools.audit_extreme_magicka_recovery_max_magicka_only_named_gear_dominance import _constrained_effective_recovery_search
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    RECOVERY_MULTIPLIER,
    _EffectiveRecoveryOrdinarySearch,
    build_pair_scores,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import (
    _best_racial_recovery_witness,
    _recovery_cp_loadout,
    exact_enlivening_value,
)
from tools.audit_extreme_magicka_recovery_special_named_gear_triage import _triage_pair
from tools.audit_extreme_magicka_recovery_willows_path_frontier import (
    TARGET_NAME as WILLOW_NAME,
    TARGET_PIECES as WILLOW_PIECES,
    companion_pair_totals,
    compose_final,
    mapped_positive_recovery_flat,
)

TARGET_NAME = "Torc of Tonal Constancy"
TARGET_PIECES = 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def final_score(*, shared_flat: float, structural: float, special: float) -> float:
    return (float(shared_flat) + float(structural) + float(special)) * RECOVERY_MULTIPLIER


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    raw_eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw_eligibility, required_armor_weight="Light"
    )
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    max_magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)

    base_max_magicka, mm_unresolved = _same_build_max_magicka_for_weight_types(database, 1)
    unresolved.extend(mm_unresolved)
    base_enlivening = exact_enlivening_value(base_max_magicka)
    remaining_headroom = max(0.0, 150.0 - base_enlivening)
    conversion = 0.005 * (1.0 + undaunted_mettle_resource_percent(1))
    pair_scores, merged = build_pair_scores(recovery, max_magicka, max_magicka_to_recovery=conversion)

    ordinary_search = _EffectiveRecoveryOrdinarySearch(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged,
        pair_scores=pair_scores,
    ).search(topology)
    unresolved.extend(ordinary_search.unresolved)

    recovery_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    magicka_by = {(int(row.set_id), int(row.piece_count)): row for row in max_magicka.evidence}
    max_magicka_service = ExtremeMaxResourceSpecialNamedGearBranchService(max_magicka)
    triage = tuple(
        _triage_pair(
            pair,
            recovery_by=recovery_by,
            magicka_by=magicka_by,
            max_magicka_service=max_magicka_service,
            remaining_enlivening_headroom=remaining_headroom,
        )
        for pair in ordinary_search.special_or_nonflat_pairs
    )
    target_rows = tuple(
        row for row in triage
        if row.set_name.casefold() == TARGET_NAME.casefold() and int(row.piece_count) == TARGET_PIECES
    )

    special_ceiling = 0.0
    target_realization = None
    target_structural = 0.0
    target_condition = ""
    if len(target_rows) != 1:
        unresolved.append(f"expected one {TARGET_NAME} {TARGET_PIECES}pc triage row, found {len(target_rows)}")
    else:
        target = target_rows[0]
        unresolved.extend(target.unresolved)
        target_evidence = recovery_by.get((int(target.set_id), TARGET_PIECES))
        if target_evidence is None:
            unresolved.append("Torc canonical Recovery evidence missing")
        else:
            upper = direct_flat_upper_bound(target, target_evidence)
            unresolved.extend(upper.pending_nonflat)
            special_ceiling = float(upper.total_special_ceiling)
            branches = tuple(aggregate_recovery_semantic_branch(target_evidence) for _ in (0,))
            branch = branches[0]
            if branch is None or branch.flat_ceiling is None:
                unresolved.append("Torc conditional Magicka Recovery branch unresolved")
            else:
                target_condition = str(branch.condition or "")
                special_ceiling = min(special_ceiling, float(branch.flat_ceiling))
            constrained, messages = _constrained_effective_recovery_search(
                challenger=target,
                topology=topology,
                breakpoints=breakpoints,
                eligibility=filtered.catalog,
                merged=merged,
                pair_scores=pair_scores,
            )
            unresolved.extend(messages)
            if constrained is None or not constrained.winner_found:
                unresolved.append("no physically realizable seven-Light Torc witness")
            else:
                target_realization = constrained.realizations[0]
                target_structural = float(constrained.best_exact_flat_delta or 0.0)

    willow_rows = tuple(
        row for row in recovery.evidence
        if row.set_name.casefold() == WILLOW_NAME.casefold() and int(row.piece_count) == WILLOW_PIECES
    )
    willow_realization = None
    willow_percent = 0.0
    willow_own_flat = 0.0
    willow_structural = 0.0
    if len(willow_rows) != 1:
        unresolved.append(f"expected one {WILLOW_NAME} Recovery 5pc row, found {len(willow_rows)}")
        willow_id = -1
    else:
        willow = willow_rows[0]
        willow_id = int(willow.set_id)
        branch = aggregate_recovery_semantic_branch(willow)
        if branch is None or branch.kind.value != "conditional_percent" or branch.percent_ceiling is None:
            unresolved.append("Willow percentage Recovery semantics unresolved")
        else:
            willow_percent = float(branch.percent_ceiling) / 100.0
        willow_own_flat = mapped_positive_recovery_flat(willow)
        willow_search, messages = _constrained_effective_recovery_search(
            challenger=SimpleNamespace(set_id=willow_id, set_name=WILLOW_NAME, piece_count=WILLOW_PIECES),
            topology=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            merged=merged,
            pair_scores=pair_scores,
        )
        unresolved.extend(messages)
        if willow_search is None or not willow_search.winner_found:
            unresolved.append("no physical Willow witness")
        else:
            willow_realization = willow_search.realizations[0]
            direct, magicka = companion_pair_totals(willow_realization, pair_scores, excluded_set_id=willow_id)
            own_score = pair_scores.get((willow_id, WILLOW_PIECES))
            own_magicka = float(own_score.max_magicka_flat) if own_score is not None else 0.0
            extra_enlivening = min(remaining_headroom, max(0.0, magicka + own_magicka) * conversion)
            willow_structural = float(direct) + float(extra_enlivening)

    jewelry = ExtremeRecoveryJewelryProjectionService(
        JewelryGlyphEffectRepository(database), JewelryTraitRepository(database)
    ).build(OBJECTIVE)
    unresolved.extend(jewelry.unresolved)
    three_infused = float(jewelry.three_slot_infused_flat or 0.0)

    provisioning = ExtremeRecoveryProvisioningProjectionService.build(database, objective_key=OBJECTIVE)
    unresolved.extend(provisioning.unresolved)
    drink = 0.0 if provisioning.drink is None else float(provisioning.drink.delta)
    if provisioning.drink is None:
        unresolved.append("no reviewed Magicka Recovery provisioning winner")

    atronach = ExtremeDivinesMundusObjectiveService.candidate_for_name(
        MundusRepository(database, initialize=False), "The Atronach", OBJECTIVE, armor_divines_count=7
    )
    if atronach.projected_delta is None:
        unresolved.extend(atronach.mundus.unresolved)
        atronach_delta = 0.0
    else:
        atronach_delta = float(atronach.projected_delta)

    cp, cp_unresolved = _recovery_cp_loadout(database, enlivening_value=base_enlivening)
    unresolved.extend(cp_unresolved)
    race_row, race_unresolved, _ = _best_racial_recovery_witness(database)
    unresolved.extend(f"racial Recovery unresolved: {item}" for item in race_unresolved)
    race_flat = 0.0 if race_row is None else float(race_row[0])
    if race_row is None:
        unresolved.append("no positive racial Magicka Recovery witness")

    shared_flat = (
        float(BASE_MAGICKA_RECOVERY)
        + three_infused
        + drink
        + atronach_delta
        + float(cp.total_flat_ceiling)
        + race_flat
    )
    willow_final = compose_final(
        shared_flat=shared_flat,
        gear_flat=willow_structural + willow_own_flat,
        multiplier=RECOVERY_MULTIPLIER + willow_percent,
    )
    torc_final = final_score(shared_flat=shared_flat, structural=target_structural, special=special_ceiling)
    lead_over_willow = torc_final - willow_final
    torc_wins = target_realization is not None and lead_over_willow > 1e-9
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(not unique_unresolved and willow_realization is not None and target_realization is not None)

    print("EXTREME MAGICKA RECOVERY TORC OF TONAL CONSTANCY COMPARISON")
    print(f"database={database}")
    print(f"shared_flat_floor={shared_flat:.3f}")
    print(f"willow_constructive_final={willow_final:.3f}")
    print(f"torc_condition={target_condition}")
    print(f"torc_special_flat_ceiling={special_ceiling:.3f}")
    print(f"torc_physical_structural={target_structural:.3f}")
    print(f"torc_prepercent={target_structural + special_ceiling:.3f}")
    print(f"torc_final={torc_final:.3f}")
    print(f"lead_over_willow={lead_over_willow:.3f}")
    print(f"torc_beats_willow={torc_wins}")
    if target_realization is not None:
        print(f"torc_witness_sets={tuple(zip(target_realization.set_names, target_realization.counts))!r}")
        print("assignments=" + repr(tuple((row.slot, row.set_name, row.weapon_type) for row in target_realization.assignments)))
    print()
    print("PROOF GATES")
    print(f"ordinary_denominator_prerequisite_proven={ordinary_search.ordinary_denominator_proven}")
    print(f"torc_physical_witness={target_realization is not None}")
    print(f"willow_physical_witness={willow_realization is not None}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"torc_comparison_closed={closed}")
    if closed and torc_wins:
        print("NEXT_STEP=promote Torc of Tonal Constancy above Willow and rebase Shroud of the Lich against Torc")
    elif closed:
        print("NEXT_STEP=remove Torc of Tonal Constancy from the survivor queue")
    else:
        print("NEXT_STEP=close only the reported Torc blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
