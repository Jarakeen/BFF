from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_resource_event import SkillComponentResourceType
from minmax.skill_component_resource_event_repository import SkillComponentResourceEventRepository
from tools.audit_phase6_heal_shield_unresolved_taxonomy import load_unresolved_taxonomy

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class AmbiguousRestoreResourceAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    status: str
    resource_type: str | None
    amount_basis: str | None
    amount_fraction: float | None
    max_bonus_fraction: float | None
    scaling_driver: str | None
    fragment: str


def load_ambiguous_restore_resource_audit(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[AmbiguousRestoreResourceAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentResourceEventRepository(path)
    rows: list[AmbiguousRestoreResourceAuditRow] = []

    for candidate in load_unresolved_taxonomy(path, limit=limit):
        if candidate.category != "ambiguous_restore_shorthand":
            continue
        events = repository.resolve(candidate.skill_rank_id, candidate.coefficient_number)
        stamina = next(
            (event for event in events if event.resource_type is SkillComponentResourceType.STAMINA),
            None,
        )
        rows.append(
            AmbiguousRestoreResourceAuditRow(
                skill_rank_id=candidate.skill_rank_id,
                coefficient_number=candidate.coefficient_number,
                ability_id=candidate.ability_id,
                ability_name=candidate.ability_name,
                status="PROMOTED" if stamina is not None else "UNRESOLVED",
                resource_type=stamina.resource_type.value if stamina is not None else None,
                amount_basis=stamina.amount_basis.value if stamina is not None else None,
                amount_fraction=stamina.amount_fraction if stamina is not None else None,
                max_bonus_fraction=stamina.max_bonus_fraction if stamina is not None else None,
                scaling_driver=stamina.scaling_driver.value if stamina is not None and stamina.scaling_driver else None,
                fragment=candidate.fragment,
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit ambiguous Current Restore components against Phase 6 resource semantics."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    rows = load_ambiguous_restore_resource_audit(args.database, limit=args.limit)
    promoted = sum(row.status == "PROMOTED" for row in rows)

    print("\n========================================")
    print(" PHASE 6 AMBIGUOUS RESTORE RESOURCE")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {len(rows)}")
    print(f"Canonically promoted:  {promoted}")
    print(f"Still unresolved:      {len(rows) - promoted}")
    print("\nNOTE: Current Restore is treated as a runtime display; Phase 6 records its explicit resource basis and scaling relationship.")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={row.status}")
        if row.resource_type is not None:
            print(f"resource={row.resource_type}")
        if row.amount_basis is not None:
            print(f"amount_basis={row.amount_basis}")
        if row.amount_fraction is not None:
            print(f"base_fraction={row.amount_fraction * 100:.1f}%")
        if row.max_bonus_fraction is not None:
            print(f"max_bonus={row.max_bonus_fraction * 100:.1f}%")
        if row.scaling_driver is not None:
            print(f"scaling_driver={row.scaling_driver}")
        print(f"fragment={' '.join(row.fragment.split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
