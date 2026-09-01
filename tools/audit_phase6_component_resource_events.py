from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_resource_event_repository import SkillComponentResourceEventRepository
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ResourceEventAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    resource_type: str
    evidence: str


def load_component_resource_events(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ResourceEventAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentResourceEventRepository(path)
    rows: list[ResourceEventAuditRow] = []

    for slot in load_slot_audit(path, limit=limit):
        if not is_active_coefficient(slot):
            continue
        for event in repository.resolve(slot.skill_rank_id, slot.coefficient_number):
            rows.append(
                ResourceEventAuditRow(
                    skill_rank_id=slot.skill_rank_id,
                    coefficient_number=slot.coefficient_number,
                    ability_id=slot.ability_id,
                    ability_name=slot.name,
                    resource_type=event.resource_type.value,
                    evidence=event.evidence,
                )
            )
    return tuple(rows)


def summarize(rows: tuple[ResourceEventAuditRow, ...]) -> Counter[str]:
    return Counter(row.resource_type for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit explicit Phase 6 component resource gains.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_component_resource_events(args.database, limit=args.limit)
    print("\n========================================")
    print(" PHASE 6 COMPONENT RESOURCE EVENTS")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Resource events:       {len(rows)}")
    print(f"Unique components:     {len({(row.skill_rank_id, row.coefficient_number) for row in rows})}")
    print(f"Unique abilities:      {len({row.ability_id for row in rows})}")
    print("\nRESOURCE TYPES")
    for resource, count in summarize(rows).most_common():
        print(f"  {resource:28} {count}")
    print("\nNOTE: explicit coefficient-local gains only; cadence and sustain-rate math are not inferred.")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"resource={row.resource_type}")
        print(f"evidence={row.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
