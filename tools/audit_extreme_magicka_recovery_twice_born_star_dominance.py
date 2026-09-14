from __future__ import annotations

"""Upper-bound dominance proof for Twice-Born Star in Extreme Magicka Recovery.

Twice-Born Star consumes five active-snapshot set units and permits a second Mundus.
The locked ordinary build already uses The Atronach, so this audit enumerates every
other canonical Mundus and gives the challenger the best direct Magicka Recovery any
second stone can provide. All Max Magicka upside from Twice-Born Star itself and from
the second Mundus is then granted the *entire* remaining Enlivening Overflow headroom.

That deliberately overstates the challenger. If the resulting distinct-set capacity
bound still loses to the closed ordinary incumbent, the branch is globally dominated
without a physical-slot search.
"""

import argparse
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository
from minmax.stat_ids import StatId
from services.extreme_divines_mundus_objective_service import ExtremeDivinesMundusObjectiveService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import _same_build_max_magicka_for_weight_types
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import (
    aggregate_recovery_semantic_branch,
    distinct_set_capacity_upper_bound,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    build_pair_scores,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import exact_enlivening_value

TARGET_NAME = "Twice-Born Star"
TARGET_PIECES = 5
LOCKED_PRIMARY_MUNDUS = "The Atronach"
ORDINARY_INCUMBENT = 1332.0
EXPECTED_SEARCH_STATE_RULE = "allows_two_mundus"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def second_mundus_direct_recovery_ceiling(repository: MundusRepository) -> tuple[float, str | None, tuple[str, ...]]:
    """Return the best direct Magicka Recovery from any non-Atronach Mundus."""
    config = ExtremeDivinesMundusObjectiveService.configuration(armor_divines_count=7)
    best_value = 0.0
    best_name = None
    unresolved: list[str] = []
    for name in repository.list_names():
        if name.casefold() == LOCKED_PRIMARY_MUNDUS.casefold():
            continue
        for record in repository.get_records(name):
            if record.stat_id != StatId.MAGICKA_RECOVERY.value:
                continue
            if not record.supported:
                unresolved.append(f"{name}: Magicka Recovery Mundus record unresolved ({record.notes})")
                continue
            if record.unit != "flat":
                unresolved.append(f"{name}: Magicka Recovery Mundus record uses unsupported unit {record.unit!r}")
                continue
            value = float(record.value) * float(config.multiplier)
            if value > best_value:
                best_value = value
                best_name = name
    return best_value, best_name, tuple(dict.fromkeys(unresolved))


def recovery_search_state_rule(evidence) -> str | None:
    """Resolve the target set mutation through the shared Recovery semantic owner."""
    branch = aggregate_recovery_semantic_branch(evidence)
    if branch is None:
        return None
    return branch.search_state_rule


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    repository = GearSetRepository(database)
    breakpoint_catalog = ExtremeGearSetBonusBreakpointService(repository).build()
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoint_catalog)
    max_magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoint_catalog)

    base_max_magicka, max_magicka_unresolved = _same_build_max_magicka_for_weight_types(database, 1)
    unresolved.extend(max_magicka_unresolved)
    base_enlivening = exact_enlivening_value(base_max_magicka)
    remaining_enlivening_headroom = max(0.0, 150.0 - base_enlivening)

    pair_scores, _ = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=0.0051,
    )

    target_rows = tuple(
        row
        for row in recovery.evidence
        if row.set_name.casefold() == TARGET_NAME.casefold() and int(row.piece_count) == TARGET_PIECES
    )
    resolved_rule = None
    if len(target_rows) != 1:
        unresolved.append(f"expected one {TARGET_NAME} Recovery 5pc row, found {len(target_rows)}")
        target_set_id = -1
    else:
        target_set_id = int(target_rows[0].set_id)
        resolved_rule = recovery_search_state_rule(target_rows[0])
        if resolved_rule != EXPECTED_SEARCH_STATE_RULE:
            unresolved.append(
                f"{TARGET_NAME} 5pc search-state rule unresolved: {resolved_rule!r}"
            )

    challenger = SimpleNamespace(set_id=target_set_id, piece_count=TARGET_PIECES)
    ordinary_capacity_upper = (
        distinct_set_capacity_upper_bound(challenger, pair_scores)
        if target_set_id >= 0
        else None
    )
    if ordinary_capacity_upper is None:
        unresolved.append("no compatible distinct-set capacity bound")

    mundus_repository = MundusRepository(database, initialize=False)
    second_direct, second_name, mundus_unresolved = second_mundus_direct_recovery_ceiling(mundus_repository)
    unresolved.extend(mundus_unresolved)

    # All Twice-Born-Star-owned Max Magicka and all second-Mundus Max Magicka can
    # improve Recovery only through Enlivening. Granting the full remaining headroom
    # is therefore a global absolute ceiling and avoids undercounting cumulative set bonuses.
    special_upper = float(second_direct) + float(remaining_enlivening_headroom)
    optimistic_total = (
        float(ordinary_capacity_upper) + special_upper
        if ordinary_capacity_upper is not None
        else None
    )
    dominated = optimistic_total is not None and optimistic_total < ORDINARY_INCUMBENT - 1e-9
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(not unique_unresolved and dominated)

    print("EXTREME MAGICKA RECOVERY TWICE-BORN STAR DOMINANCE")
    print(f"database={database}")
    print(f"ordinary_incumbent_prepercent_recovery={ORDINARY_INCUMBENT:.3f}")
    print(f"base_max_magicka={base_max_magicka:.3f}")
    print(f"base_enlivening={base_enlivening:.3f}")
    print(f"remaining_enlivening_headroom={remaining_enlivening_headroom:.3f}")
    print(f"best_distinct_second_mundus_direct_recovery={second_direct:.3f}")
    print(f"best_distinct_second_mundus_name={second_name!r}")
    print(f"ordinary_capacity_upper={float(ordinary_capacity_upper or 0.0):.3f}")
    print(f"special_upper={special_upper:.3f}")
    print(f"optimistic_total={float(optimistic_total or 0.0):.3f}")
    print(f"margin_to_incumbent={(ORDINARY_INCUMBENT - float(optimistic_total)) if optimistic_total is not None else 0.0:.3f}")
    print(f"dominated={dominated}")
    print()
    print("PROOF GATES")
    print(f"search_state_rule_resolved={resolved_rule == EXPECTED_SEARCH_STATE_RULE}")
    print(f"max_magicka_witness_unresolved_count={len(max_magicka_unresolved)}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"twice_born_star_branch_closed={closed}")
    print("NEXT_STEP=remove Twice-Born Star from the special named-gear queue" if closed else "NEXT_STEP=close only the reported Twice-Born Star blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
