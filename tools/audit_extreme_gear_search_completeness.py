from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_search_completeness_audit_service import (
    ExtremeGearSearchCompletenessAuditService,
)
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


def _label_set_ids(ids: tuple[int, ...], names: dict[int, str]) -> tuple[str, ...]:
    return tuple(f"{set_id} :: {names.get(set_id, '<unknown>')}" for set_id in ids)


def _label_breakpoints(
    rows: tuple[tuple[int, int], ...],
    names: dict[int, str],
) -> tuple[str, ...]:
    return tuple(
        f"{set_id} :: {names.get(set_id, '<unknown>')} :: {piece_count}-piece"
        for set_id, piece_count in rows
    )


def _print_rows(title: str, rows: tuple[str, ...]) -> None:
    print(f"{title}: {len(rows)}")
    for row in rows:
        print(f"  - {row}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the canonical named-gear denominator used by Extreme max-resource search. "
            "This command is read-only and cross-checks topology, set-bonus breakpoints, "
            "slot eligibility, and objective relevance."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--objective",
        choices=_OBJECTIVES,
        action="append",
        help="Limit the audit to one or more max-resource objectives. Defaults to all three.",
    )
    args = parser.parse_args()

    objectives = tuple(args.objective or _OBJECTIVES)
    repository = GearSetRepository(args.database)
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    eligibility = ExtremeNamedGearSetSlotEligibilityService(args.database).build()
    names = {int(row.set_id): row.name for row in topology.sets}

    print("EXTREME GEAR SEARCH COMPLETENESS AUDIT")
    print(f"Database: {args.database}")
    print("Mode: READ ONLY")
    print(
        "Boundary: every canonical named set must survive the same topology, breakpoint, "
        "slot-eligibility, and objective-relevance accounting denominator."
    )

    exit_code = 0
    for objective in objectives:
        relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
            objective,
            breakpoints,
        )
        audit = ExtremeGearSearchCompletenessAuditService.build(
            topology=topology,
            breakpoints=breakpoints,
            eligibility=eligibility,
            relevance=relevance,
        )

        print()
        print(objective.upper())
        print(f"Canonical sets reviewed: {audit.canonical_sets_reviewed}")
        print(f"Mechanically relevant breakpoints: {audit.mechanically_relevant_breakpoints}")
        print(f"Relevance breakpoints reviewed: {audit.relevance_breakpoints_reviewed}")
        print(f"Named-gear denominator proven: {'yes' if audit.denominator_proven else 'no'}")
        _print_rows(
            "Missing from breakpoint catalog",
            _label_set_ids(audit.missing_from_breakpoints, names),
        )
        _print_rows(
            "Missing from slot eligibility",
            _label_set_ids(audit.missing_from_slot_eligibility, names),
        )
        _print_rows(
            "Extra breakpoint sets",
            _label_set_ids(audit.extra_breakpoint_sets, names),
        )
        _print_rows(
            "Extra slot eligibility sets",
            _label_set_ids(audit.extra_slot_eligibility_sets, names),
        )
        _print_rows(
            "Missing relevance breakpoints",
            _label_breakpoints(audit.missing_relevance_breakpoints, names),
        )
        _print_rows(
            "Extra relevance breakpoints",
            _label_breakpoints(audit.extra_relevance_breakpoints, names),
        )
        _print_rows(
            "Candidate sets without slot evidence",
            _label_set_ids(audit.candidate_sets_without_slot_evidence, names),
        )
        _print_rows("Unresolved", audit.unresolved)

        if not audit.denominator_proven:
            exit_code = 2

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
