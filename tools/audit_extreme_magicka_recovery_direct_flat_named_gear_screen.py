from __future__ import annotations

"""Screen direct-flat Magicka Recovery named gear without physical brute force.

This pass is deliberately an optimistic upper-bound screen. It reuses the closed
ordinary Recovery frontier, classifies direct-flat special challengers, and for
each one reserves the challenger's active-snapshot set units, then solves a tiny
distinct-set capacity knapsack over the remaining ordinary named-set breakpoints.

The knapsack enforces only two facts that any legal loadout must obey: one breakpoint
per set identity, and no more than the remaining active-snapshot set-count units.
It deliberately ignores armor/jewelry/weapon slot compatibility, exact count-topology
shape, and all other physical conflicts. Those omissions can only increase the
ordinary coexistence score, so the result remains a proof-safe upper bound while
avoiding the previous absurdity of reusing the same best set identity repeatedly.

A challenger below the incumbent under this generous bound is globally dominated.
A challenger at or above the incumbent is carried forward for exact follow-up. This
screen performs no constrained physical brute force.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import (
    ACTIVE_SNAPSHOT_SET_UNITS,
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import (
    _same_build_max_magicka_for_weight_types,
)
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_dominance import (
    direct_flat_upper_bound,
    dominance_row,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    RECOVERY_MULTIPLIER,
    _EffectiveRecoveryOrdinarySearch,
    build_pair_scores,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import exact_enlivening_value
from tools.audit_extreme_magicka_recovery_special_named_gear_triage import _triage_pair


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def distinct_set_capacity_upper_bound(
    challenger,
    pair_scores,
    *,
    active_snapshot_units: int = ACTIVE_SNAPSHOT_SET_UNITS,
) -> float | None:
    """Optimistic ordinary score with the challenger reserving its set-count units.

    Each ordinary set identity may contribute at most one breakpoint. The search
    ignores physical slot legality and does not require every remaining unit to be
    consumed, so its maximum is at least as large as any legal ordinary coexistence
    score for the same challenger.
    """
    required = int(challenger.piece_count)
    capacity = int(active_snapshot_units) - required
    if required <= 0 or capacity < 0:
        return None

    challenger_id = int(challenger.set_id)
    choices_by_set: dict[int, dict[int, float]] = {}
    for (set_id, count), score in pair_scores.items():
        set_id = int(set_id)
        count = int(count)
        if set_id == challenger_id or not score.ordinary or count <= 0 or count > capacity:
            continue
        value = max(0.0, float(score.optimistic_effective_recovery))
        if value <= 0.0:
            continue
        choices = choices_by_set.setdefault(set_id, {})
        if value > choices.get(count, float("-inf")):
            choices[count] = value

    # Multiple-choice 0/1 knapsack: skip a set or choose exactly one of its
    # ordinary breakpoints. Physical eligibility is intentionally ignored.
    dp = [0.0] * (capacity + 1)
    for choices in choices_by_set.values():
        previous = tuple(dp)
        updated = list(previous)
        for used in range(capacity + 1):
            base = previous[used]
            for count, value in choices.items():
                target = used + count
                if target <= capacity:
                    updated[target] = max(updated[target], base + value)
        dp = updated
    return max(dp, default=0.0)


def main() -> int:
    database = Path(_parser().parse_args().database)
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
    base_enlivening = exact_enlivening_value(base_max_magicka)
    remaining_headroom = max(0.0, 150.0 - base_enlivening)
    pair_scores, merged = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=0.0051,
    )
    ordinary_search = _EffectiveRecoveryOrdinarySearch(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged,
        pair_scores=pair_scores,
    ).search(topology)
    incumbent = max(
        (
            float(row.best_exact_flat_delta)
            for row in ordinary_search.topologies
            if row.winner_found and row.best_exact_flat_delta is not None
        ),
        default=0.0,
    )

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
    unresolved_triage = tuple(row for row in triage if row.unresolved)
    direct = tuple(row for row in triage if row.direct_recovery_challenger)

    rows = []
    pending = []
    for challenger in direct:
        evidence = recovery_by.get((int(challenger.set_id), int(challenger.piece_count)))
        if evidence is None:
            pending.append((challenger, ("missing canonical Recovery evidence",)))
            continue
        upper = direct_flat_upper_bound(challenger, evidence)
        if upper.pending_nonflat:
            pending.append((challenger, upper.pending_nonflat))
            continue
        structural = distinct_set_capacity_upper_bound(challenger, pair_scores)
        rows.append(
            dominance_row(
                challenger=challenger,
                structural_score=structural,
                special_ceiling=upper.total_special_ceiling,
                incumbent=incumbent,
                bound_kind="distinct_set_capacity_upper",
            )
        )

    rows.sort(
        key=lambda row: (
            -(row.optimistic_total if row.optimistic_total is not None else float("-inf")),
            row.piece_count,
            row.set_id,
        )
    )
    dominated = tuple(row for row in rows if row.dominated)
    survivors = tuple(row for row in rows if not row.dominated)
    screen_closed = bool(
        filtered.denominator_proven
        and ordinary_search.ordinary_denominator_proven
        and not unresolved_triage
        and not max_magicka_unresolved
        and rows
    )

    print("EXTREME MAGICKA RECOVERY DIRECT-FLAT NAMED-GEAR SCREEN")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"ordinary_incumbent_prepercent_recovery={incumbent:.3f}")
    print(f"ordinary_incumbent_final_recovery_gain={incumbent * RECOVERY_MULTIPLIER:.3f}")
    print(f"direct_recovery_challengers={len(direct)}")
    print(f"flat_upper_bound_candidates={len(rows)}")
    print(f"nonflat_or_search_state_pending={len(pending)}")
    print()
    print("DISTINCT-SET CAPACITY UPPER BOUNDS")
    for row in rows:
        if row.optimistic_total is None or row.margin is None:
            print(
                f"set={row.set_name!r} pieces={row.piece_count} compatible_capacity=False dominated=True"
            )
            continue
        print(
            f"set={row.set_name!r} pieces={row.piece_count} "
            f"structural_upper={row.structural_ordinary_score:.3f} "
            f"special_flat_upper_bound={row.special_flat_upper_bound:.3f} "
            f"optimistic_total={row.optimistic_total:.3f} margin_to_incumbent={row.margin:.3f} "
            f"dominated={row.dominated}"
        )
    print()
    print("SURVIVORS FOR EXACT FOLLOW-UP")
    for row in survivors:
        print(
            f"survivor: set={row.set_name!r} pieces={row.piece_count} "
            f"optimistic_total={row.optimistic_total:.3f} margin_to_incumbent={row.margin:.3f}"
        )
    for challenger, reasons in pending:
        print(
            f"pending_nonflat: set={challenger.set_name!r} pieces={challenger.piece_count} reasons={reasons!r}"
        )
    print()
    print("PROOF GATES")
    print(f"light_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_denominator_prerequisite_proven={ordinary_search.ordinary_denominator_proven}")
    print(f"triage_unresolved_count={len(unresolved_triage)}")
    print(f"max_magicka_witness_unresolved_count={len(max_magicka_unresolved)}")
    print(f"flat_candidates_dominated_by_capacity_bound={len(dominated)}")
    print(f"flat_candidates_surviving_capacity_bound={len(survivors)}")
    print(f"direct_flat_screen_closed={screen_closed}")
    if screen_closed:
        print("NEXT_STEP=exactly resolve only capacity-bound flat survivors plus pending non-flat/search-state branches")
    else:
        print("NEXT_STEP=close only the reported screen prerequisites")
    return 0 if screen_closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
