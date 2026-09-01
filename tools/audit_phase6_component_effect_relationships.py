from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_effect_relationship_repository import SkillComponentEffectRelationshipRepository
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient

DEFAULT_DATABASE = ROOT / "data" / "eso.db"

@dataclass(frozen=True)
class ComponentEffectAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    target_effect: str
    source_effect_name: str
    evidence: str

def load_component_effect_relationships(database_path: str | Path, *, limit: int | None = None) -> tuple[ComponentEffectAuditRow, ...]:
    repository = SkillComponentEffectRelationshipRepository(database_path)
    rows: list[ComponentEffectAuditRow] = []
    for slot in load_slot_audit(database_path, limit=limit):
        if not is_active_coefficient(slot):
            continue
        for relationship in repository.resolve(slot.skill_rank_id, slot.coefficient_number):
            rows.append(ComponentEffectAuditRow(
                skill_rank_id=slot.skill_rank_id,
                coefficient_number=slot.coefficient_number,
                ability_id=slot.ability_id,
                ability_name=slot.name,
                target_effect=relationship.target_effect,
                source_effect_name=relationship.source_effect_name,
                evidence=relationship.evidence,
            ))
    return tuple(rows)

def summarize(rows: tuple[ComponentEffectAuditRow, ...]) -> dict[str, object]:
    return {
        "relationships": len(rows),
        "components": len({(row.skill_rank_id, row.coefficient_number) for row in rows}),
        "abilities": len({row.ability_id for row in rows}),
        "effect_counts": Counter(row.source_effect_name for row in rows),
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit explicit Phase 6 component-to-named-effect relationships.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()
    rows = load_component_effect_relationships(args.database, limit=args.limit)
    summary = summarize(rows)
    effect_counts: Counter[str] = summary["effect_counts"]  # type: ignore[assignment]
    print("\n========================================")
    print(" PHASE 6 COMPONENT EFFECT RELATIONSHIPS")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Relationships:         {summary['relationships']}")
    print(f"Unique components:     {summary['components']}")
    print(f"Unique abilities:      {summary['abilities']}")
    print("\nNAMED EFFECT APPLICATIONS")
    for name, count in effect_counts.most_common():
        print(f"  {name:28} {count}")
    print("\nNOTE: only explicit coefficient-local applications of canonical combat effects are counted.")
    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(f"rank={row.skill_rank_id} coef={row.coefficient_number} ability={row.ability_id} name={row.ability_name}")
        print(f"applies={row.source_effect_name} ({row.target_effect})")
        print(f"evidence={row.evidence}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
