from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_missing_health_healing_repository import (
    SkillComponentMissingHealthHealingRepository,
)
from tools.audit_phase6_heal_shield_unresolved_taxonomy import (
    load_unresolved_heal_shield_taxonomy,
)

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class MissingHealthHealingAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    status: str
    fraction: float | None
    fragment: str


def load_missing_health_healing_audit(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[MissingHealthHealingAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentMissingHealthHealingRepository(path)
    rows: list[MissingHealthHealingAuditRow] = []

    for candidate in load_unresolved_heal_shield_taxonomy(path, limit=limit):
        if candidate.category != "missing_health_healing":
            continue
        healing = repository.resolve(candidate.skill_rank_id, candidate.coefficient_number)
        fraction = healing[0].fraction if healing else None
        rows.append(
            MissingHealthHealingAuditRow(
                skill_rank_id=candidate.skill_rank_id,
                coefficient_number=candidate.coefficient_number,
                ability_id=candidate.ability_id,
                ability_name=candidate.ability_name,
                status="PROMOTED" if healing else "UNRESOLVED",
                fraction=fraction,
                fragment=candidate.fragment,
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Phase 6 healing derived from a percentage of missing Health."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_missing_health_healing_audit(args.database, limit=args.limit)
    promoted = sum(row.status == "PROMOTED" for row in rows)

    print("\n========================================")
    print(" PHASE 6 MISSING-HEALTH HEALING")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {len(rows)}")
    print(f"Canonically promoted:  {promoted}")
    print(f"Still unresolved:      {len(rows) - promoted}")
    print("\nNOTE: Phase 6 records the amount relationship only; cadence remains later-phase work.")

    ordered = sorted(rows, key=lambda row: (row.status != "UNRESOLVED", row.skill_rank_id))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={row.status}")
        if row.fraction is not None:
            print(f"fraction={row.fraction * 100:.1f}%")
        print(f"fragment={' '.join(row.fragment.split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
