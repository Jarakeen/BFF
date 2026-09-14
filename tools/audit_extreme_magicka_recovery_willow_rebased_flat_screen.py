from __future__ import annotations

"""Rebase direct-flat named-gear dominance on the legal Willow's Path witness.

The earlier direct-flat screen compared challenger pre-percent Recovery against the
closed ordinary named-gear incumbent. Willow's Path proved a stronger legal build
because its 18% Recovery bonus belongs at the percent layer. This audit reconstructs
that Willow witness from canonical data, converts every surviving flat challenger's
proof-safe pre-percent upper bound into final Recovery using the locked ordinary
1.81 multiplier, and prunes any branch that still cannot reach Willow's legal final
Recovery lower bound.

Only the already-proven special/non-flat named-gear queue is reconsidered here.
Ordinary named gear remains closed and is never regenerated from the full Recovery
evidence universe. Percentage, named-buff, formula, and search-state mechanics remain
separate obligations.
"""

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
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import (
    _NONFLAT_KINDS,
    aggregate_recovery_semantic_branch,
    distinct_set_capacity_upper_bound,
)
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def prepercent_threshold(*, shared_flat: float, incumbent_final: float, multiplier: float) -> float:
    return max(0.0, float(incumbent_final) / float(multiplier) - float(shared_flat))


def canonical_special_triage_pairs(special_or_nonflat_pairs) -> tuple[tuple[int, str, int], ...]:
    """Preserve the closed ordinary-search special queue as canonical triage triples."""
    rows: list[tuple[int, str, int]] = []
    for pair in special_or_nonflat_pairs:
        if len(pair) != 3:
            raise ValueError(f"special named-gear queue pair must have 3 fields, got {pair!r}")
        set_id, set_name, piece_count = pair
        rows.append((int(set_id), str(set_name), int(piece_count)))
    return tuple(rows)


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
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
    conversion = 0.005 * (1.0 + undaunted_mettle_resource_percent(1))
    pair_scores, merged = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=conversion,
    )
    ordinary_search = _EffectiveRecoveryOrdinarySearch(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged,
        pair_scores=pair_scores,
    ).search(topology)

    recovery_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    magicka_by = {(int(row.set_id), int(row.piece_count)): row for row in max_magicka.evidence}

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
            unresolved.append("Willow's Path percentage Recovery semantics unresolved")
        else:
            willow_percent = float(branch.percent_ceiling) / 100.0
        willow_own_flat = mapped_positive_recovery_flat(willow)
        constrained, messages = _constrained_effective_recovery_search(
            challenger=SimpleNamespace(set_id=willow_id, set_name=WILLOW_NAME, piece_count=WILLOW_PIECES),
            topology=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            merged=merged,
            pair_scores=pair_scores,
        )
        unresolved.extend(messages)
        if constrained is None or not constrained.winner_found:
            unresolved.append("no physical Willow's Path witness for rebase")
        else:
            willow_realization = constrained.realizations[0]
            direct, magicka = companion_pair_totals(
                willow_realization,
                pair_scores,
                excluded_set_id=willow_id,
            )
            own_score = pair_scores.get((willow_id, WILLOW_PIECES))
            own_magicka = float(own_score.max_magicka_flat) if own_score is not None else 0.0
            extra_enlivening = min(
                remaining_headroom,
                max(0.0, magicka + own_magicka) * conversion,
            )
            willow_structural = float(direct) + float(extra_enlivening)

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
    race_flat = float(race_row[0]) if race_row is not None else 0.0
    if race_row is None:
        unresolved.append("no positive racial Magicka Recovery witness")

    shared_flat = (
        float(BASE_MAGICKA_RECOVERY)
        + three_infused
        + drink
        + atronach_delta
        + cp_total
        + race_flat
    )
    willow_final = compose_final(
        shared_flat=shared_flat,
        gear_flat=willow_structural + willow_own_flat,
        multiplier=RECOVERY_MULTIPLIER + willow_percent,
    )
    threshold = prepercent_threshold(
        shared_flat=shared_flat,
        incumbent_final=willow_final,
        multiplier=RECOVERY_MULTIPLIER,
    )

    max_magicka_service = ExtremeMaxResourceSpecialNamedGearBranchService(max_magicka)
    triage_pairs = canonical_special_triage_pairs(ordinary_search.special_or_nonflat_pairs)
    triage = tuple(
        _triage_pair(
            pair,
            recovery_by=recovery_by,
            magicka_by=magicka_by,
            max_magicka_service=max_magicka_service,
            remaining_enlivening_headroom=remaining_headroom,
        )
        for pair in triage_pairs
    )
    unresolved_triage = tuple(row for row in triage if row.unresolved)
    direct = tuple(row for row in triage if row.direct_recovery_challenger and not row.unresolved)

    rows: list[tuple[str, int, float, float, bool]] = []
    pending: list[str] = []
    for challenger in direct:
        evidence = recovery_by.get((int(challenger.set_id), int(challenger.piece_count)))
        if evidence is None:
            continue
        upper = direct_flat_upper_bound(challenger, evidence)
        reasons = list(upper.pending_nonflat)
        special_ceiling = float(upper.total_special_ceiling)
        aggregate = aggregate_recovery_semantic_branch(evidence)
        if aggregate is not None:
            if aggregate.kind in _NONFLAT_KINDS or aggregate.percent_ceiling is not None or aggregate.search_state_rule:
                reasons.append(aggregate.kind.value)
            elif aggregate.can_raise_self and aggregate.flat_ceiling is not None:
                special_ceiling = max(
                    special_ceiling,
                    float(upper.mapped_flat)
                    + max(0.0, float(aggregate.flat_ceiling))
                    + float(upper.max_magicka_recovery_ceiling),
                )
        if reasons:
            pending.append(challenger.set_name)
            continue
        structural = distinct_set_capacity_upper_bound(challenger, pair_scores)
        if structural is None:
            continue
        optimistic_prepercent = float(structural) + special_ceiling
        optimistic_final = (shared_flat + optimistic_prepercent) * RECOVERY_MULTIPLIER
        dominated = optimistic_final < willow_final - 1e-9
        rows.append(
            (
                str(challenger.set_name),
                int(challenger.piece_count),
                optimistic_prepercent,
                optimistic_final,
                dominated,
            )
        )

    rows.sort(key=lambda row: (-row[2], row[0].casefold()))
    dominated_rows = tuple(row for row in rows if row[4])
    survivors = tuple(row for row in rows if not row[4])
    unique_unresolved = tuple(dict.fromkeys((*unresolved, *(item for row in unresolved_triage for item in row.unresolved))))
    closed = bool(
        not unique_unresolved
        and willow_realization is not None
        and filtered.denominator_proven
        and ordinary_search.ordinary_denominator_proven
    )

    print("EXTREME MAGICKA RECOVERY WILLOW-REBASED FLAT SCREEN")
    print(f"database={database}")
    print(f"shared_flat_floor={shared_flat:.3f}")
    print(f"willow_constructive_final={willow_final:.3f}")
    print(f"ordinary_flat_multiplier={RECOVERY_MULTIPLIER:.6f}")
    print(f"flat_prepercent_tie_threshold={threshold:.3f}")
    print(f"special_queue_pair_count={len(triage_pairs)}")
    print(f"direct_recovery_challengers={len(direct)}")
    print()
    print("FLAT CHALLENGER FINAL UPPER BOUNDS")
    for name, pieces, prepercent, final_upper, dominated in rows:
        print(
            f"set={name!r} pieces={pieces} optimistic_prepercent={prepercent:.3f} "
            f"optimistic_final_upper={final_upper:.3f} margin_to_willow={willow_final-final_upper:.3f} "
            f"dominated={dominated}"
        )
    print()
    print("REBASED SURVIVORS")
    for name, pieces, prepercent, final_upper, _dominated in survivors:
        print(f"survivor: set={name!r} pieces={pieces} optimistic_prepercent={prepercent:.3f} optimistic_final_upper={final_upper:.3f}")
    print()
    print("PROOF GATES")
    print(f"willow_physical_witness={willow_realization is not None}")
    print(f"ordinary_denominator_prerequisite_proven={ordinary_search.ordinary_denominator_proven}")
    print(f"triage_unresolved_count={len(unresolved_triage)}")
    print(f"rebased_flat_dominated_count={len(dominated_rows)}")
    print(f"rebased_flat_survivor_count={len(survivors)}")
    print(f"pending_nonflat_count={len(set(pending))}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"willow_rebased_flat_screen_closed={closed}")
    print("NEXT_STEP=exactly resolve only the Willow-rebased flat survivors and remaining special branches")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
