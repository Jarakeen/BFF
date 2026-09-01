from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_conditional_consequence_repository import (
    SkillComponentConditionalConsequenceRepository,
)
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ConditionalConsequenceAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    consequence_type: str
    threshold: float
    maximum_bonus_fraction: float | None
    evidence: str


def load_conditional_consequences(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ConditionalConsequenceAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentConditionalConsequenceRepository(path)
    rows: list[ConditionalConsequenceAuditRow] = []

    for slot in load_slot_audit(path, limit=limit):
        if not is_active_coefficient(slot):
            continue
        for consequence in repository.resolve(slot.skill_rank_id, slot.coefficient_number):
            rows.append(
                ConditionalConsequenceAuditRow(
                    skill_rank_id=slot.skill_rank_id,
                    coefficient_number=slot.coefficient_number,
                    ability_id=slot.ability_id,
                    ability_name=slot.name,
                    consequence_type=consequence.consequence_type.value,
                    threshold=consequence.condition.threshold,
                    maximum_bonus_fraction=consequence.maximum_bonus_fraction,
                    evidence=consequence.evidence,
                )
            )
    return tuple(rows)


def summarize(rows: tuple[ConditionalConsequenceAuditRow, ...]) -> Counter[str]:
    return Counter(row.consequence_type for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit canonical Phase 6 conditional component consequences.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_conditional_consequences(args.database, limit=args.limit)
    print("\n========================================")
    print(" PHASE 6 CONDITIONAL CONSEQUENCES")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Consequences:          {len(rows)}")
    print(f"Unique components:     {len({(row.skill_rank_id, row.coefficient_number) for row in rows})}")
    print(f"Unique abilities:      {len({row.ability_id for row in rows})}")

    print("\nCONSEQUENCE TYPES")
    for name, count in summarize(rows).most_common():
        print(f"  {name:28} {count}")

    print("\nNOTE: Phase 6 records the relationship only; timing and combat-state evaluation remain later-phase work.")
    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"consequence={row.consequence_type}")
        print(f"threshold={row.threshold * 100:.1f}%")
        if row.maximum_bonus_fraction is not None:
            print(f"maximum_bonus={row.maximum_bonus_fraction * 100:.1f}%")
        print(f"evidence={row.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
