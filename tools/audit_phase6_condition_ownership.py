from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_condition_repository import SkillComponentConditionRepository
from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ConditionOwnershipRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    effect_kind: str | None
    owns_condition: bool
    thresholds: tuple[float, ...]
    fragment: str


def load_condition_ownership(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ConditionOwnershipRow, ...]:
    path = Path(database_path)
    repository = SkillComponentConditionRepository(path)
    slots = tuple(slot for slot in load_slot_audit(path, limit=limit) if is_active_coefficient(slot))

    conditioned_abilities: set[int] = set()
    condition_cache: dict[tuple[int, int], tuple[object, ...]] = {}
    for slot in slots:
        conditions = repository.resolve(slot.skill_rank_id, slot.coefficient_number)
        condition_cache[(slot.skill_rank_id, slot.coefficient_number)] = conditions
        if conditions:
            conditioned_abilities.add(slot.ability_id)

    rows: list[ConditionOwnershipRow] = []
    for slot in slots:
        if slot.ability_id not in conditioned_abilities:
            continue
        evidence = extract_component_text_evidence(slot.coef_description, slot.coefficient_number)
        conditions = condition_cache[(slot.skill_rank_id, slot.coefficient_number)]
        rows.append(
            ConditionOwnershipRow(
                skill_rank_id=slot.skill_rank_id,
                coefficient_number=slot.coefficient_number,
                ability_id=slot.ability_id,
                ability_name=slot.name,
                effect_kind=evidence.effect_kind,
                owns_condition=bool(conditions),
                thresholds=tuple(float(condition.threshold) for condition in conditions),
                fragment=evidence.fragment,
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit which coefficient currently owns each Phase 6 health-threshold condition."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=20, help="Maximum conditioned abilities to print.")
    args = parser.parse_args()

    rows = load_condition_ownership(args.database, limit=args.limit)
    grouped: dict[tuple[int, int, str], list[ConditionOwnershipRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.skill_rank_id, row.ability_id, row.ability_name)].append(row)

    print("\n========================================")
    print(" PHASE 6 CONDITION OWNERSHIP")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Conditioned abilities: {len(grouped)}")
    print("\nNOTE: this is read-only evidence. It exposes coefficient ownership for review.")

    for index, ((rank_id, ability_id, name), ability_rows) in enumerate(grouped.items()):
        if index >= max(0, args.samples):
            break
        print("\n----------------------------------------")
        print(f"rank={rank_id} ability={ability_id} name={name}")
        for row in sorted(ability_rows, key=lambda item: item.coefficient_number):
            marker = "OWNER" if row.owns_condition else "     "
            thresholds = ",".join(f"{value * 100:.1f}%" for value in row.thresholds) or "-"
            fragment = " ".join(row.fragment.split())
            print(
                f"  {marker} coef={row.coefficient_number} kind={row.effect_kind or 'unknown'} "
                f"threshold={thresholds}"
            )
            print(f"        fragment={fragment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
