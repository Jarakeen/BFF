from __future__ import annotations

"""Compare Oakensoul Ring against the legal Torc Recovery incumbent.

The Extreme class-slot frontier already models one six-slot active bar. Oakensoul's
``one_bar_only`` search-state rule removes the backup weapon bar; it does not reduce
the five abilities + ultimate available on the active bar. The audit therefore keeps
the proven six-slot class multiplier and compares exact physical one-Mythic gear
witnesses, including a future-common Major Intellect potion context because additive
Recovery percentages can change close rankings.
"""

import argparse
from pathlib import Path
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
from services.extreme_subclass_slot_allocation_service import ExtremeSubclassSlotAllocationService
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

TORC_NAME = "Torc of Tonal Constancy"
OAK_NAME = "Oakensoul Ring"
PIECES = 1
MAJOR_INTELLECT_PERCENT = 0.30


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _score(*, shared: float, structural: float, flat_special: float = 0.0, extra_percent: float = 0.0, common_percent: float = 0.0) -> float:
    return (float(shared) + float(structural) + float(flat_special)) * (
        RECOVERY_MULTIPLIER + float(extra_percent) + float(common_percent)
    )


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

    by_name = {
        row.set_name.casefold(): row
        for row in triage
        if int(row.piece_count) == PIECES
    }
    torc = by_name.get(TORC_NAME.casefold())
    oak = by_name.get(OAK_NAME.casefold())
    if torc is None:
        unresolved.append("Torc triage row missing")
    if oak is None:
        unresolved.append("Oakensoul triage row missing")

    torc_flat = 0.0
    torc_structural = 0.0
    torc_realization = None
    if torc is not None:
        unresolved.extend(torc.unresolved)
        evidence = recovery_by.get((int(torc.set_id), PIECES))
        if evidence is None:
            unresolved.append("Torc Recovery evidence missing")
        else:
            upper = direct_flat_upper_bound(torc, evidence)
            unresolved.extend(upper.pending_nonflat)
            branch = aggregate_recovery_semantic_branch(evidence)
            if branch is None or branch.flat_ceiling is None:
                unresolved.append("Torc conditional flat Recovery unresolved")
            else:
                torc_flat = min(float(upper.total_special_ceiling), float(branch.flat_ceiling))
            constrained, messages = _constrained_effective_recovery_search(
                challenger=torc,
                topology=topology,
                breakpoints=breakpoints,
                eligibility=filtered.catalog,
                merged=merged,
                pair_scores=pair_scores,
            )
            unresolved.extend(messages)
            if constrained is None or not constrained.winner_found:
                unresolved.append("no legal Torc physical witness")
            else:
                torc_realization = constrained.realizations[0]
                torc_structural = float(constrained.best_exact_flat_delta or 0.0)

    oak_percent = 0.0
    oak_rule = ""
    oak_condition = ""
    oak_structural = 0.0
    oak_realization = None
    if oak is not None:
        unresolved.extend(oak.unresolved)
        evidence = recovery_by.get((int(oak.set_id), PIECES))
        if evidence is None:
            unresolved.append("Oakensoul Recovery evidence missing")
        else:
            branch = aggregate_recovery_semantic_branch(evidence)
            if (
                branch is None
                or branch.percent_ceiling is None
                or branch.search_state_rule != "one_bar_only"
            ):
                unresolved.append("Oakensoul one-bar Minor Intellect branch unresolved")
            else:
                oak_percent = float(branch.percent_ceiling) / 100.0
                oak_rule = str(branch.search_state_rule or "")
                oak_condition = str(branch.condition or "")
            constrained, messages = _constrained_effective_recovery_search(
                challenger=oak,
                topology=topology,
                breakpoints=breakpoints,
                eligibility=filtered.catalog,
                merged=merged,
                pair_scores=pair_scores,
            )
            unresolved.extend(messages)
            if constrained is None or not constrained.winner_found:
                unresolved.append("no legal Oakensoul physical witness")
            else:
                oak_realization = constrained.realizations[0]
                oak_structural = float(constrained.best_exact_flat_delta or 0.0)

    # The reviewed slot service explicitly optimizes one six-slot active bar.
    active_bar_slots = int(ExtremeSubclassSlotAllocationService.ACTIVE_BAR_SLOTS)
    if active_bar_slots != 6:
        unresolved.append(f"unexpected reviewed active-bar slot count: {active_bar_slots}")

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

    shared = (
        float(BASE_MAGICKA_RECOVERY)
        + three_infused
        + drink
        + atronach_delta
        + float(cp.total_flat_ceiling)
        + race_flat
    )

    torc_named = _score(shared=shared, structural=torc_structural, flat_special=torc_flat)
    oak_named = _score(shared=shared, structural=oak_structural, extra_percent=oak_percent)
    torc_potion = _score(
        shared=shared,
        structural=torc_structural,
        flat_special=torc_flat,
        common_percent=MAJOR_INTELLECT_PERCENT,
    )
    oak_potion = _score(
        shared=shared,
        structural=oak_structural,
        extra_percent=oak_percent,
        common_percent=MAJOR_INTELLECT_PERCENT,
    )

    named_lead = torc_named - oak_named
    potion_lead = torc_potion - oak_potion
    torc_wins_both = named_lead > 1e-9 and potion_lead > 1e-9
    unique_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
    closed = bool(
        not unique_unresolved
        and torc_realization is not None
        and oak_realization is not None
        and oak_rule == "one_bar_only"
        and active_bar_slots == 6
    )

    print("EXTREME MAGICKA RECOVERY OAKENSOUL VS LEGAL TORC")
    print(f"database={database}")
    print(f"shared_flat_floor={shared:.3f}")
    print(f"reviewed_active_bar_slots={active_bar_slots}")
    print("oakensoul_one_bar_reduces_active_bar_slots=False")
    print(f"oakensoul_search_state_rule={oak_rule}")
    print(f"oakensoul_condition={oak_condition}")
    print(f"oakensoul_minor_intellect_percent={oak_percent * 100.0:.3f}")
    print(f"torc_special_flat={torc_flat:.3f}")
    print(f"torc_physical_structural={torc_structural:.3f}")
    print(f"oakensoul_physical_structural={oak_structural:.3f}")
    print(f"torc_named_gear_final={torc_named:.3f}")
    print(f"oakensoul_named_gear_final={oak_named:.3f}")
    print(f"torc_named_gear_lead={named_lead:.3f}")
    print(f"common_major_intellect_percent={MAJOR_INTELLECT_PERCENT * 100.0:.3f}")
    print(f"torc_potion_active_final={torc_potion:.3f}")
    print(f"oakensoul_potion_active_final={oak_potion:.3f}")
    print(f"torc_potion_active_lead={potion_lead:.3f}")
    print(f"torc_beats_oakensoul_in_both_contexts={torc_wins_both}")
    if torc_realization is not None:
        print(f"torc_witness_sets={tuple(zip(torc_realization.set_names, torc_realization.counts))!r}")
    if oak_realization is not None:
        print(f"oakensoul_witness_sets={tuple(zip(oak_realization.set_names, oak_realization.counts))!r}")
        print("oakensoul_assignments=" + repr(tuple((row.slot, row.set_name, row.weapon_type) for row in oak_realization.assignments)))

    print("\nPROOF GATES")
    print(f"ordinary_denominator_prerequisite_proven={ordinary_search.ordinary_denominator_proven}")
    print(f"torc_physical_witness={torc_realization is not None}")
    print(f"oakensoul_physical_witness={oak_realization is not None}")
    print(f"one_bar_semantics_proven={oak_rule == 'one_bar_only' and active_bar_slots == 6}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"oakensoul_torc_comparison_closed={closed}")
    if closed and torc_wins_both:
        print("NEXT_STEP=remove Oakensoul; legal Torc closes the named-gear Recovery frontier")
    elif closed:
        print("NEXT_STEP=promote Oakensoul or split the incumbent by future buff context")
    else:
        print("NEXT_STEP=close only the reported Oakensoul blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
