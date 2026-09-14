from __future__ import annotations

"""Upper-bound dominance proof for Bastion of the Draoife in Extreme Magicka Recovery.

The reviewed five-piece mechanic grants 106 Magicka Recovery per Inflection stack,
up to three stacks.  The shared Recovery semantic classifier owns the stack ceiling;
this audit does not duplicate the arithmetic.  Bastion's lower-piece bonuses do not
raise Magicka Recovery or Max Magicka, so the challenger reserves five of the 12
active-snapshot set units and receives only its full reviewed stack ceiling on top of
the existing distinct-set ordinary coexistence upper bound.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranchKind,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import (
    distinct_set_capacity_upper_bound,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    _EffectiveRecoveryOrdinarySearch,
    build_pair_scores,
)

TARGET_NAME = "Bastion of the Draoife"
TARGET_PIECES = 5
REVIEWED_TOOLTIP = (
    "Blocking an attack grants you a stack of Inflection for 10 seconds, up to 3 stacks max. "
    "You can gain up to 1 stack every 0.5 seconds. Increase your Magicka and Stamina Recovery "
    "by 106 per stack of Inflection."
)
INCUMBENT = 1332.0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def bastion_optimistic_total(*, structural_upper: float, stack_ceiling: float) -> float:
    return float(structural_upper) + float(stack_ceiling)


def main() -> int:
    database = Path(_parser().parse_args().database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    max_magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)

    pair_scores, merged = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=0.0051,
    )
    ordinary_search = _EffectiveRecoveryOrdinarySearch(
        breakpoints=breakpoints,
        eligibility=None,
        relevance=merged,
        pair_scores=pair_scores,
    ) if False else None

    target_rows = tuple(
        row
        for row in recovery.evidence
        if row.set_name.casefold() == TARGET_NAME.casefold() and int(row.piece_count) == TARGET_PIECES
    )
    unresolved: list[str] = []
    if len(target_rows) != 1:
        unresolved.append(f"expected one {TARGET_NAME} Recovery 5pc row, found {len(target_rows)}")

    branch = ExtremeGearSetRecoverySpecialBranchService.classify(
        set_name=TARGET_NAME,
        piece_count=TARGET_PIECES,
        description=REVIEWED_TOOLTIP,
        objective_key=OBJECTIVE,
    )
    if branch is None or branch.kind is not ExtremeRecoverySpecialBranchKind.STACKED_FLAT:
        unresolved.append("reviewed Bastion tooltip did not resolve to stacked-flat Recovery")
    elif branch.flat_ceiling is None:
        unresolved.append("reviewed Bastion stack ceiling is unresolved")

    set_id = int(target_rows[0].set_id) if target_rows else -1
    structural_upper = (
        distinct_set_capacity_upper_bound(
            type("Challenger", (), {"set_id": set_id, "piece_count": TARGET_PIECES})(),
            pair_scores,
        )
        if set_id >= 0
        else None
    )
    if structural_upper is None:
        unresolved.append("no compatible distinct-set capacity upper bound")

    stack_ceiling = float(branch.flat_ceiling or 0.0) if branch is not None else 0.0
    optimistic_total = (
        bastion_optimistic_total(
            structural_upper=float(structural_upper),
            stack_ceiling=stack_ceiling,
        )
        if structural_upper is not None and not unresolved
        else None
    )
    dominated = optimistic_total is not None and optimistic_total < INCUMBENT - 1e-9
    closed = bool(not unresolved and dominated)

    print("EXTREME MAGICKA RECOVERY BASTION DOMINANCE")
    print(f"database={database}")
    print(f"ordinary_incumbent_prepercent_recovery={INCUMBENT:.3f}")
    print(f"reviewed_stack_ceiling={stack_ceiling:.3f}")
    print(f"ordinary_capacity_upper={float(structural_upper or 0.0):.3f}")
    print(f"optimistic_total={float(optimistic_total or 0.0):.3f}")
    print(f"margin_to_incumbent={(INCUMBENT - float(optimistic_total)) if optimistic_total is not None else 0.0:.3f}")
    print(f"dominated={dominated}")
    print()
    print("PROOF GATES")
    print(f"stack_semantics_resolved={branch is not None and branch.kind is ExtremeRecoverySpecialBranchKind.STACKED_FLAT and branch.flat_ceiling is not None}")
    print(f"audit_unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")
    print(f"bastion_branch_closed={closed}")
    print("NEXT_STEP=remove Bastion from the special named-gear queue" if closed else "NEXT_STEP=close only the reported Bastion blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
