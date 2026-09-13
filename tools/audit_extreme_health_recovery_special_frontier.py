from __future__ import annotations

"""Classify the Health Recovery named-gear special denominator without scoring it."""

import argparse
from collections import Counter
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
)

OBJECTIVE = "health_recovery"
_UNRESOLVED_ROW = re.compile(
    r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$",
    re.DOTALL,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)

    rows: list[tuple[str, int, str]] = []
    parse_unresolved: list[str] = []
    for item in relevance.unresolved:
        match = _UNRESOLVED_ROW.match(str(item))
        if match is None:
            parse_unresolved.append(str(item))
            continue
        rows.append(
            (
                match.group("name"),
                int(match.group("count")),
                match.group("description"),
            )
        )

    catalog = ExtremeGearSetRecoverySpecialBranchService.build(
        tuple(rows),
        objective_key=OBJECTIVE,
    )
    unresolved = tuple(dict.fromkeys((*parse_unresolved, *catalog.unresolved)))
    kinds = Counter(row.kind.value for row in catalog.branches)
    semantic_denominator_proven = bool(
        relevance.breakpoints_reviewed
        and not unresolved
        and len(rows) == len(catalog.branches)
    )

    print("EXTREME HEALTH RECOVERY SPECIAL FRONTIER")
    print(f"database={database}")
    print("mode=description_driven_semantic_classification_not_scoring")
    print(f"base_relevance_denominator_proven={relevance.denominator_proven}")
    print(f"relevance_unresolved_rows={len(relevance.unresolved)}")
    print(f"parsed_recovery_rows={len(rows)}")
    print(f"classified_branches={len(catalog.branches)}")
    print(f"positive_challengers={len(catalog.positive_challengers)}")
    print(f"reviewed_non_challengers={len(catalog.reviewed_non_challengers)}")
    print(f"semantic_denominator_proven={semantic_denominator_proven}")
    print(f"denominator_classified={not unresolved and len(rows) == len(catalog.branches)}")
    print("branch_kinds=" + ", ".join(f"{key}:{value}" for key, value in sorted(kinds.items())))
    print()

    print("POSITIVE SELF CHALLENGERS")
    for row in catalog.positive_challengers:
        print(
            f"  {row.set_name} {row.piece_count}pc kind={row.kind.value} "
            f"flat_ceiling={row.flat_ceiling!r} percent_ceiling={row.percent_ceiling!r} "
            f"condition={row.condition or '<none>'} rule={row.search_state_rule or '<none>'}"
        )

    print()
    print("REVIEWED NON-CHALLENGERS / SEARCH OBLIGATIONS")
    for row in catalog.reviewed_non_challengers:
        print(
            f"  {row.set_name} {row.piece_count}pc kind={row.kind.value} "
            f"rule={row.search_state_rule or '<none>'}"
        )

    print()
    print(f"unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")

    if unresolved or not semantic_denominator_proven:
        print("NEXT_STEP=close the remaining recovery semantic grammars before any record scoring")
        return 2
    print(
        "NEXT_STEP=build the constructive Health Recovery component ledger and canonical "
        "ordinary incumbent using only the classified positive challenger frontier"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
