from __future__ import annotations

"""Dominance proof for Apocryphal Inspiration in Extreme Magicka Recovery.

Apocryphal Inspiration's relevant 5pc branch grants Major Intellect. The Extreme
Magicka Recovery blueprint already owns a self-usable Restore Magicka potion that
grants that same named buff. Named buffs do not stack with themselves, so the set
has zero marginal percentage value in the potion-active optimum.

The challenger is still granted the optimistic five-piece distinct-set ordinary
capacity bound. If that bound loses to the proven Torc of Tonal Constancy incumbent
under the same future Major Intellect multiplier, the branch is globally dominated
without needing a physical-slot realization.
"""

import argparse
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_blueprint_service import _POTION_PROFILE
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import (
    aggregate_recovery_semantic_branch,
    distinct_set_capacity_upper_bound,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    RECOVERY_MULTIPLIER,
    build_pair_scores,
)

TARGET_NAME = "Apocryphal Inspiration"
TARGET_PIECES = 5
EXPECTED_BUFF = "Major Intellect"
EXPECTED_PERCENT = 30.0
TORC_STRUCTURAL = 1203.0
TORC_SPECIAL = 450.0
SHARED_FLAT_FLOOR = 3702.294


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def score(*, shared_flat: float, gear_flat: float, percent: float) -> float:
    return (float(shared_flat) + float(gear_flat)) * float(percent)


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    max_magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)
    pair_scores, _ = build_pair_scores(recovery, max_magicka, max_magicka_to_recovery=0.0051)

    target_rows = tuple(
        row for row in recovery.evidence
        if row.set_name.casefold() == TARGET_NAME.casefold() and int(row.piece_count) == TARGET_PIECES
    )
    branch = None
    target_set_id = -1
    if len(target_rows) != 1:
        unresolved.append(f"expected one {TARGET_NAME} Recovery 5pc row, found {len(target_rows)}")
    else:
        target_set_id = int(target_rows[0].set_id)
        branch = aggregate_recovery_semantic_branch(target_rows[0])
        if branch is None:
            unresolved.append("Apocryphal Inspiration Recovery branch unresolved")
        else:
            if branch.kind.value != "named_buff":
                unresolved.append(f"expected named_buff branch, found {branch.kind.value!r}")
            if branch.percent_ceiling is None or abs(float(branch.percent_ceiling) - EXPECTED_PERCENT) > 1e-9:
                unresolved.append(f"expected {EXPECTED_PERCENT:.0f}% Major Intellect ceiling")

    potion_profile = _POTION_PROFILE.get(OBJECTIVE)
    potion_name = potion_profile[0] if potion_profile else None
    potion_buff = potion_profile[1] if potion_profile else None
    if potion_buff != EXPECTED_BUFF:
        unresolved.append(f"Restore Magicka potion Major Intellect source unresolved: {potion_profile!r}")

    capacity = None
    if target_set_id >= 0:
        capacity = distinct_set_capacity_upper_bound(
            SimpleNamespace(set_id=target_set_id, piece_count=TARGET_PIECES),
            pair_scores,
        )
    if capacity is None:
        unresolved.append("no compatible five-piece distinct-set capacity bound")

    common_major_intellect = EXPECTED_PERCENT / 100.0
    common_multiplier = RECOVERY_MULTIPLIER + common_major_intellect
    torc_prepercent = SHARED_FLAT_FLOOR + TORC_STRUCTURAL + TORC_SPECIAL
    challenger_prepercent = SHARED_FLAT_FLOOR + float(capacity or 0.0)
    torc_final = torc_prepercent * common_multiplier
    challenger_final = challenger_prepercent * common_multiplier
    margin = torc_final - challenger_final
    dominated = capacity is not None and margin > 1e-9
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(not unique_unresolved and dominated)

    print("EXTREME MAGICKA RECOVERY APOCRYPHAL INSPIRATION DOMINANCE")
    print(f"database={database}")
    print(f"potion_name={potion_name!r}")
    print(f"potion_named_buff={potion_buff!r}")
    print(f"set_named_buff={EXPECTED_BUFF!r}")
    print(f"set_percent_ceiling={float(branch.percent_ceiling if branch and branch.percent_ceiling is not None else 0.0):.3f}")
    print("named_buff_stacks_with_itself=False")
    print("apocryphal_marginal_percent_with_potion=0.000")
    print(f"apocryphal_ordinary_capacity_upper={float(capacity or 0.0):.3f}")
    print(f"common_major_intellect_percent={common_major_intellect:.3f}")
    print(f"common_multiplier={common_multiplier:.3f}")
    print(f"torc_prepercent={torc_prepercent:.3f}")
    print(f"apocryphal_optimistic_prepercent={challenger_prepercent:.3f}")
    print(f"torc_with_major_intellect={torc_final:.3f}")
    print(f"apocryphal_upper_with_major_intellect={challenger_final:.3f}")
    print(f"margin_to_torc={margin:.3f}")
    print(f"dominated={dominated}")
    print()
    print("PROOF GATES")
    print(f"major_intellect_potion_source_proven={potion_buff == EXPECTED_BUFF}")
    print(f"apocryphal_named_buff_semantics_proven={branch is not None and branch.kind.value == 'named_buff'}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"apocryphal_branch_closed={closed}")
    print("NEXT_STEP=remove Apocryphal Inspiration; Oakensoul remains the final named-gear search-state branch" if closed else "NEXT_STEP=close only the reported Apocryphal Inspiration blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
