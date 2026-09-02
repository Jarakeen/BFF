from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_resource_restore_display_repository import (
    SkillComponentResourceRestoreDisplayRepository,
)

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
TARGETS = (
    (5636, 2, "Constitution"),
    (5637, 2, "Constitution"),
    (6568, 1, "Undaunted Command"),
    (6568, 2, "Undaunted Command"),
    (6568, 3, "Undaunted Command"),
    (6569, 1, "Undaunted Command"),
    (6569, 2, "Undaunted Command"),
    (6569, 3, "Undaunted Command"),
)


@dataclass(frozen=True)
class AuditRow:
    skill_rank_id: int
    coefficient_number: int
    name: str
    promoted: bool
    summary: str


def load_rows(database_path: str | Path) -> tuple[AuditRow, ...]:
    repo = SkillComponentResourceRestoreDisplayRepository(database_path)
    rows: list[AuditRow] = []
    for rank, coef, name in TARGETS:
        resolved = repo.resolve(rank, coef)
        if not resolved:
            rows.append(AuditRow(rank, coef, name, False, "-"))
            continue
        item = resolved[0]
        resources = ",".join(resource.value for resource in item.resources)
        if item.amount_fraction is not None:
            amount = f"fraction={item.amount_fraction:.4g}"
        else:
            amount = f"amount_per_unit={item.amount_per_unit:.4g}; driver={item.driver.value if item.driver else '-'}"
        rows.append(
            AuditRow(
                rank,
                coef,
                name,
                True,
                f"resources={resources}; basis={item.basis.value}; {amount}",
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 6 current resource-restore display semantics.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    rows = load_rows(args.database)
    counts = Counter("PROMOTED" if row.promoted else "UNRESOLVED" for row in rows)
    print("\n========================================")
    print(" PHASE 6 RESOURCE RESTORE DISPLAYS")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {len(rows)}")
    print(f"Canonically promoted:  {counts['PROMOTED']}")
    print(f"Still unresolved:      {counts['UNRESOLVED']}")

    for row in rows:
        print("\n----------------------------------------")
        print(f"rank={row.skill_rank_id} coef={row.coefficient_number} name={row.name}")
        print(f"status={'PROMOTED' if row.promoted else 'UNRESOLVED'}")
        if row.promoted:
            print(row.summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
