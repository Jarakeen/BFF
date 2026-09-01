from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_secondary_healing_repository import SkillComponentSecondaryHealingRepository
from tools.audit_phase6_heal_shield_unresolved_taxonomy import load_unresolved_taxonomy

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class SecondaryHealingAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    status: str
    fraction: float | None
    fragment: str


def load_secondary_healing_audit(database_path: str | Path) -> tuple[SecondaryHealingAuditRow, ...]:
    repository = SkillComponentSecondaryHealingRepository(database_path)
    rows: list[SecondaryHealingAuditRow] = []
    for candidate in load_unresolved_taxonomy(database_path):
        if candidate.category != "damage_linked_healing":
            continue
        resolved = repository.resolve(candidate.skill_rank_id, candidate.coefficient_number)
        fraction = resolved[0].fraction if resolved else None
        rows.append(
            SecondaryHealingAuditRow(
                skill_rank_id=candidate.skill_rank_id,
                coefficient_number=candidate.coefficient_number,
                ability_id=candidate.ability_id,
                ability_name=candidate.ability_name,
                status="PROMOTED" if resolved else "UNRESOLVED",
                fraction=fraction,
                fragment=candidate.fragment,
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 6 damage-linked secondary healing coverage.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_secondary_healing_audit(args.database)
    promoted = [row for row in rows if row.status == "PROMOTED"]
    unresolved = [row for row in rows if row.status == "UNRESOLVED"]

    print("\n========================================")
    print(" PHASE 6 SECONDARY HEALING")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {len(rows)}")
    print(f"Canonically promoted:  {len(promoted)}")
    print(f"Still unresolved:      {len(unresolved)}")

    fractions = Counter(row.fraction for row in promoted)
    if fractions:
        print("\nHEAL FRACTIONS")
        for fraction, count in sorted(fractions.items(), key=lambda item: (item[0] is None, item[0] or 0)):
            label = "unknown" if fraction is None else f"{fraction * 100:.1f}%"
            print(f"  {label:28} {count}")

    ordered = unresolved + promoted
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
