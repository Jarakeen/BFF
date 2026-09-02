from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_trigger_relationship_repository import (
    SkillComponentTriggerRelationshipRepository,
)
from tools.audit_phase6_remaining_semantics import load_remaining_phase6_semantics

DEFAULT_DATABASE = ROOT / "data" / "eso.db"

_TRIGGER_CUE_RE = re.compile(
    r"\b(?:when\s+triggered|light\s+attacks?|heavy\s+attacks?|stun\s+lasts\s+the\s+full\s+duration|"
    r"after\s+the\s+stun\s+ends|(?:when|after)\s+the\s+(?:effect|shield)\s+ends|"
    r"each\s+time\s+(?:they|the\s+target)\s+take(?:s)?\s+damage|"
    r"if\s+the\s+enemy\s+dies|damage\s+over\s+time\s+effects?\s+end)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TriggerAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_name: str
    status: str
    trigger_type: str | None
    fragment: str


def load_trigger_audit(database_path: str | Path) -> tuple[TriggerAuditRow, ...]:
    repo = SkillComponentTriggerRelationshipRepository(database_path)
    rows: list[TriggerAuditRow] = []
    for item in load_remaining_phase6_semantics(database_path):
        if item.is_covered:
            continue
        gap = item.gap
        fragment = " ".join(str(gap.fragment or "").split())
        if not fragment or _TRIGGER_CUE_RE.search(fragment) is None:
            continue
        resolved = repo.resolve(gap.skill_rank_id, gap.coefficient_number)
        rows.append(
            TriggerAuditRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_name=gap.name,
                status="PROMOTED" if resolved else "UNRESOLVED",
                trigger_type=resolved[0].trigger_type.value if resolved else None,
                fragment=fragment,
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit explicit Phase 6 component trigger relationships.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--samples", type=int, default=120)
    args = parser.parse_args()

    rows = load_trigger_audit(args.database)
    status = Counter(row.status for row in rows)
    types = Counter(row.trigger_type for row in rows if row.trigger_type)

    print("\n========================================")
    print(" PHASE 6 COMPONENT TRIGGERS")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {len(rows)}")
    print(f"Canonically promoted:  {status['PROMOTED']}")
    print(f"Still unresolved:      {status['UNRESOLVED']}")
    print("\nTRIGGER TYPES")
    for name, count in types.most_common():
        print(f"  {name:32} {count}")
    print("\nNOTE: Phase 6 records event identity only; Phase 7 owns runtime timing and trigger evaluation.")

    for row in sorted(rows, key=lambda r: (r.status, r.ability_name, r.skill_rank_id, r.coefficient_number))[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(f"rank={row.skill_rank_id} coef={row.coefficient_number} name={row.ability_name}")
        print(f"status={row.status}")
        print(f"trigger_type={row.trigger_type or '-'}")
        print(f"fragment={row.fragment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
