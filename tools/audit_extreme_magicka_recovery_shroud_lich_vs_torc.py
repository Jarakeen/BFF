from __future__ import annotations

"""Compare exact Shroud of the Lich Recovery against the current Torc incumbent."""

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

SHROUD_NAME = "Shroud of the Lich"
SHROUD_PIECES = 5
TORC_NAME = "Torc of Tonal Constancy"
TORC_PIECES = 1


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
    pair_scores, merged = build_pair_scores(
        recovery, max_magicka, max_magicka_to_recovery=conversion
    )

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

    def resolve_target(name: str, pieces: int):
        rows = tuple(
            row for row in triage
            if row.set_name.casefold() == name.casefold() and int(row.piece_count) == pieces
        )
        if len(rows) != 1:
            unresolved.append(f"expected one {name} {pieces}pc triage row, found {len(rows)}")
            return None, None, None, 0.0, 0.0, "", None
        target = rows[0]
        unresolved.extend(target.unresolved)
        evidence = recovery_by.get((int(target.set_id), pieces))
        if evidence is None:
            unresolved.append(f"{name} canonical Recovery evidence missing")
            return target, None, None, 0.0, 0.0, "", None

        upper = direct_flat_upper_bound(target, evidence)
        unresolved.extend(upper.pending_nonflat)
        generic = float(upper.total_special_ceiling)
        branch = aggregate_recovery_semantic_branch(evidence)
        exact = generic
        condition = ""
        if branch is None or branch.flat_ceiling is None:
            unresolved.append(f"{name} exact conditional Recovery branch unresolved")
        else:
            exact = min(generic, float(branch.flat_ceiling))
            condition = str(branch.condition or "")

        constrained, messages = _constrained_effective_recovery_search(
            challenger=target,
            topology=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            merged=merged,
            pair_scores=pair_scores,
        )
        unresolved.extend(messages)
        realization = None
        structural = 0.0
        if constrained is None or not constrained.winner_found:
            unresolved.append(f"no physically realizable seven-Light {name} witness")
        else:
            realization = constrained.realizations[0]
            structural = float(constrained.best_exact_flat_delta or 0.0)
        return target, evidence, branch, generic, exact, condition, (realization, structural)

    shroud = resolve_target(SHROUD_NAME, SHROUD_PIECES)
    torc = resolve_target(TORC_NAME, TORC_PIECES)

    shroud_generic = float(shroud[3])
    shroud_exact = float(shroud[4])
    shroud_condition = str(shroud[5])
    shroud_realization, shroud_structural = shroud[6] if shroud[6] is not None else (None, 0.0)

    torc_exact = float(torc[4])
    torc_condition = str(torc[5])
    torc_realization, torc_structural = torc[6] if torc[6] is not None else (None, 0.0)

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
        + float(cp.total_flat_ceiling)
        + race_flat
    )

    torc_final = final_score(
        shared_flat=shared_flat,
        structural=torc_structural,
        special=torc_exact,
    )
    shroud_generic_final = final_score(
        shared_flat=shared_flat,
        structural=shroud_structural,
        special=shroud_generic,
    )
    shroud_final = final_score(
        shared_flat=shared_flat,
        structural=shroud_structural,
        special=shroud_exact,
    )
    lead_over_torc = shroud_final - torc_final
    shroud_wins = shroud_realization is not None and torc_realization is not None and lead_over_torc > 1e-9

    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        not unique_unresolved
        and ordinary_search.ordinary_denominator_proven
        and shroud_realization is not None
        and torc_realization is not None
    )

    print("EXTREME MAGICKA RECOVERY SHROUD OF THE LICH VS TORC")
    print(f"database={database}")
    print(f"shared_flat_floor={shared_flat:.3f}")
    print(f"torc_condition={torc_condition}")
    print(f"torc_special_flat_ceiling={torc_exact:.3f}")
    print(f"torc_physical_structural={torc_structural:.3f}")
    print(f"torc_final={torc_final:.3f}")
    print(f"shroud_condition={shroud_condition}")
    print(f"shroud_generic_special_ceiling={shroud_generic:.3f}")
    print(f"shroud_exact_special_flat_ceiling={shroud_exact:.3f}")
    print(f"shroud_physical_structural={shroud_structural:.3f}")
    print(f"shroud_generic_final_control={shroud_generic_final:.3f}")
    print(f"shroud_final={shroud_final:.3f}")
    print(f"lead_over_torc={lead_over_torc:.3f}")
    print(f"shroud_beats_torc={shroud_wins}")
    if shroud_realization is not None:
        print(f"shroud_witness_sets={tuple(zip(shroud_realization.set_names, shroud_realization.counts))!r}")
        print("shroud_assignments=" + repr(tuple((row.slot, row.set_name, row.weapon_type) for row in shroud_realization.assignments)))
    if torc_realization is not None:
        print(f"torc_witness_sets={tuple(zip(torc_realization.set_names, torc_realization.counts))!r}")

    print()
    print("PROOF GATES")
    print(f"ordinary_denominator_prerequisite_proven={ordinary_search.ordinary_denominator_proven}")
    print(f"shroud_physical_witness={shroud_realization is not None}")
    print(f"torc_physical_witness={torc_realization is not None}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"shroud_torc_comparison_closed={closed}")
    if closed and shroud_wins:
        print("NEXT_STEP=promote Shroud of the Lich above Torc as the named-gear incumbent")
    elif closed:
        print("NEXT_STEP=remove Shroud of the Lich; Torc remains the named-gear incumbent")
    else:
        print("NEXT_STEP=close only the reported Shroud/Torc blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
