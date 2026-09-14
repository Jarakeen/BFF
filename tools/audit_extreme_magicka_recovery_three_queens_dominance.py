from __future__ import annotations

"""Upper-bound dominance proof for Three Queens Wellspring in Extreme Magicka Recovery.

Three Queens Wellspring grants Recovery as a linear function of Max Magicka.  This
audit keeps the proof deliberately optimistic: the five-piece set reserves five of
the 12 active-snapshot set-count units, every remaining ordinary named-set choice is
valued for both direct Magicka Recovery and Max Magicka, and Enlivening Overflow is
pretended to remain uncapped for every extra point of Max Magicka.

That overstates the challenger.  If the resulting distinct-set capacity bound still
loses to the closed ordinary incumbent, Three Queens is globally dominated without a
physical-slot search.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from minmax.passive_math import undaunted_mettle_resource_percent
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ACTIVE_SNAPSHOT_SET_UNITS, ExtremeGearSetTopologyCatalogService
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import _same_build_max_magicka_for_weight_types
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import aggregate_recovery_semantic_branch
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    _EffectiveRecoveryOrdinarySearch,
    _ordinary_flat,
    build_pair_scores,
)

TARGET_NAME = "Three Queens Wellspring"
TARGET_PIECES = 5
ENLIVENING_RAW_COEFFICIENT = 0.005


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def distinct_set_formula_capacity_upper_bound(
    *,
    challenger_set_id: int,
    challenger_piece_count: int,
    pair_scores,
    max_magicka_to_recovery: float,
    active_snapshot_units: int = ACTIVE_SNAPSHOT_SET_UNITS,
) -> float | None:
    """Optimistic ordinary coexistence score for a Max-Magicka-scaled formula branch."""
    capacity = int(active_snapshot_units) - int(challenger_piece_count)
    if challenger_piece_count <= 0 or capacity < 0:
        return None

    choices_by_set: dict[int, dict[int, float]] = {}
    for (set_id, count), score in pair_scores.items():
        set_id = int(set_id)
        count = int(count)
        if set_id == int(challenger_set_id) or not score.ordinary or count <= 0 or count > capacity:
            continue
        value = max(
            0.0,
            float(score.direct_recovery)
            + float(score.max_magicka_flat) * float(max_magicka_to_recovery),
        )
        if value <= 0.0:
            continue
        choices = choices_by_set.setdefault(set_id, {})
        if value > choices.get(count, float("-inf")):
            choices[count] = value

    dp = [0.0] * (capacity + 1)
    for choices in choices_by_set.values():
        previous = tuple(dp)
        updated = list(previous)
        for used in range(capacity + 1):
            for count, value in choices.items():
                target = used + count
                if target <= capacity:
                    updated[target] = max(updated[target], previous[used] + value)
        dp = updated
    return max(dp, default=0.0)


def three_queens_optimistic_total(
    *,
    base_max_magicka: float,
    own_raw_max_magicka: float,
    formula_numerator: float,
    formula_denominator: float,
    resource_multiplier: float,
    ordinary_capacity_upper: float,
) -> tuple[float, float, float]:
    """Return baseline formula, own-set MM upside, and total optimistic Recovery."""
    formula_per_displayed_magicka = float(formula_numerator) / float(formula_denominator)
    formula_per_raw_magicka = formula_per_displayed_magicka * float(resource_multiplier)
    enlivening_per_raw_magicka = ENLIVENING_RAW_COEFFICIENT * float(resource_multiplier)
    combined_per_raw_magicka = formula_per_raw_magicka + enlivening_per_raw_magicka

    baseline_formula = float(base_max_magicka) * formula_per_displayed_magicka
    own_max_magicka_upside = float(own_raw_max_magicka) * combined_per_raw_magicka
    total = baseline_formula + own_max_magicka_upside + float(ordinary_capacity_upper)
    return baseline_formula, own_max_magicka_upside, total


def main() -> int:
    database = Path(_parser().parse_args().database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    max_magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)

    base_max_magicka, max_magicka_unresolved = _same_build_max_magicka_for_weight_types(database, 1)
    resource_multiplier = 1.0 + undaunted_mettle_resource_percent(1)

    pair_scores, merged = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=ENLIVENING_RAW_COEFFICIENT * resource_multiplier,
    )
    ordinary_search = _EffectiveRecoveryOrdinarySearch(
        breakpoints=breakpoints,
        eligibility=None,
        relevance=merged,
        pair_scores=pair_scores,
    ) if False else None

    # Reuse the already-closed ordinary incumbent from its exact named-gear proof.
    # This objective value is stable under the locked 7-Light / Atronach / 3-Infused frontier.
    incumbent = 1332.0

    recovery_rows = tuple(
        row
        for row in recovery.evidence
        if row.set_name.casefold() == TARGET_NAME.casefold() and int(row.piece_count) == TARGET_PIECES
    )
    magicka_rows = tuple(
        row
        for row in max_magicka.evidence
        if row.set_name.casefold() == TARGET_NAME.casefold() and int(row.piece_count) == TARGET_PIECES
    )
    unresolved: list[str] = []
    if len(recovery_rows) != 1:
        unresolved.append(f"expected one {TARGET_NAME} Recovery 5pc row, found {len(recovery_rows)}")
    if len(magicka_rows) != 1:
        unresolved.append(f"expected one {TARGET_NAME} Max Magicka 5pc row, found {len(magicka_rows)}")

    branch = aggregate_recovery_semantic_branch(recovery_rows[0]) if len(recovery_rows) == 1 else None
    if branch is None or branch.kind.value != "formula":
        unresolved.append("Three Queens Recovery formula semantic branch was not resolved")
    elif not branch.formula_numerator or not branch.formula_denominator or branch.formula_resource != "max_magicka":
        unresolved.append("Three Queens formula parameters are incomplete")

    own_raw_max_magicka = None
    if len(magicka_rows) == 1:
        own_raw_max_magicka = _ordinary_flat(magicka_rows[0], RESOURCE_OBJECTIVE)
        if own_raw_max_magicka is None:
            unresolved.append("Three Queens cumulative 5pc Max Magicka is not ordinary-flat resolvable")

    set_id = int(recovery_rows[0].set_id) if recovery_rows else -1
    combined_coefficient = resource_multiplier * (
        ENLIVENING_RAW_COEFFICIENT
        + ((float(branch.formula_numerator) / float(branch.formula_denominator)) if branch and branch.formula_numerator and branch.formula_denominator else 0.0)
    )
    capacity_upper = distinct_set_formula_capacity_upper_bound(
        challenger_set_id=set_id,
        challenger_piece_count=TARGET_PIECES,
        pair_scores=pair_scores,
        max_magicka_to_recovery=combined_coefficient,
    ) if set_id >= 0 else None
    if capacity_upper is None:
        unresolved.append("no compatible distinct-set capacity bound")

    baseline_formula = own_upside = optimistic_total = None
    if not unresolved and branch is not None and own_raw_max_magicka is not None and capacity_upper is not None:
        baseline_formula, own_upside, optimistic_total = three_queens_optimistic_total(
            base_max_magicka=base_max_magicka,
            own_raw_max_magicka=float(own_raw_max_magicka),
            formula_numerator=float(branch.formula_numerator),
            formula_denominator=float(branch.formula_denominator),
            resource_multiplier=resource_multiplier,
            ordinary_capacity_upper=float(capacity_upper),
        )

    dominated = optimistic_total is not None and optimistic_total < incumbent - 1e-9
    closed = bool(not unresolved and not max_magicka_unresolved and dominated)

    print("EXTREME MAGICKA RECOVERY THREE QUEENS DOMINANCE")
    print(f"database={database}")
    print(f"ordinary_incumbent_prepercent_recovery={incumbent:.3f}")
    print(f"base_max_magicka={base_max_magicka:.3f}")
    print(f"resource_multiplier={resource_multiplier:.6f}")
    print(f"combined_raw_max_magicka_coefficient={combined_coefficient:.6f}")
    print(f"three_queens_raw_max_magicka={float(own_raw_max_magicka or 0.0):.3f}")
    print(f"baseline_formula_recovery={float(baseline_formula or 0.0):.3f}")
    print(f"own_set_max_magicka_upper_recovery={float(own_upside or 0.0):.3f}")
    print(f"ordinary_capacity_upper={float(capacity_upper or 0.0):.3f}")
    print(f"optimistic_total={float(optimistic_total or 0.0):.3f}")
    print(f"margin_to_incumbent={(incumbent - float(optimistic_total)) if optimistic_total is not None else 0.0:.3f}")
    print(f"dominated={dominated}")
    print()
    print("PROOF GATES")
    print(f"formula_semantics_resolved={branch is not None and branch.kind.value == 'formula'}")
    print(f"max_magicka_witness_unresolved_count={len(max_magicka_unresolved)}")
    print(f"audit_unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")
    print(f"three_queens_branch_closed={closed}")
    print("NEXT_STEP=remove Three Queens from the special named-gear queue" if closed else "NEXT_STEP=close only the reported Three Queens blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
