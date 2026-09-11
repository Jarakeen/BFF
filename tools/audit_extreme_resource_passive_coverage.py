from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)


_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


def _print_rows(title: str, rows: tuple[str, ...]) -> None:
    print(f"{title}: {len(rows)}")
    for row in rows:
        print(f"  - {row}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit every canonical player passive for Extreme max Health/Magicka/Stamina coverage. "
            "This is read-only inventory/projection evidence; contextual and unresolved mechanics remain blockers."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--objective",
        choices=_OBJECTIVES,
        action="append",
        help="Limit the audit to one or more resource objectives. Defaults to all three.",
    )
    args = parser.parse_args()

    objectives = tuple(args.objective or _OBJECTIVES)
    service = ExtremeResourcePassiveCoverageAuditService(args.database)

    print("EXTREME MAX-RESOURCE PASSIVE COVERAGE AUDIT")
    print(f"Database: {args.database}")
    print("Mode: READ ONLY")
    print(
        "Boundary: every canonical player passive is classified; contextual/unresolved mechanics are never assigned zero."
    )

    exit_code = 0
    for objective in objectives:
        audit = service.build(objective)
        print()
        print(objective.upper())
        print(f"Passives reviewed: {audit.passives_reviewed}")
        print(f"Inventory denominator proven: {'yes' if audit.denominator_proven else 'no'}")
        print(f"Static projection complete: {'yes' if audit.projection_complete else 'no'}")
        _print_rows("Static relevant", audit.static_relevant)
        _print_rows("Accounted elsewhere", audit.accounted_elsewhere)
        _print_rows("Context required", audit.context_required)
        _print_rows("Unresolved", audit.unresolved)
        print(f"Static irrelevant: {len(audit.static_irrelevant)}")
        if not audit.denominator_proven:
            exit_code = 2

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
