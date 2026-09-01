from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_condition_repository import SkillComponentConditionRepository
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


def load_component_conditions(database_path: str | Path, *, limit: int | None = None):
    repository = SkillComponentConditionRepository(database_path)
    rows = []
    for slot in load_slot_audit(database_path, limit=limit):
        if not is_active_coefficient(slot):
            continue
        for condition in repository.resolve(slot.skill_rank_id, slot.coefficient_number):
            rows.append((
                slot.skill_rank_id,
                slot.coefficient_number,
                slot.ability_id,
                slot.name,
                condition.condition_type.value,
                condition.threshold,
                condition.evidence,
            ))
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 6 coefficient-local component conditions.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_component_conditions(args.database, limit=args.limit)
    threshold_counts = Counter(row[5] for row in rows)
    print("\n========================================")
    print(" PHASE 6 COMPONENT CONDITIONS")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Conditions:            {len(rows)}")
    print(f"Unique components:     {len({(row[0], row[1]) for row in rows})}")
    print(f"Unique abilities:      {len({row[2] for row in rows})}")
    print("\nTARGET HEALTH THRESHOLDS")
    for threshold, count in sorted(threshold_counts.items()):
        print(f"  {threshold * 100:6.1f}%                    {count}")
    print("\nNOTE: explicit coefficient-local wording only; Phase 6 does not evaluate combat state.")
    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(f"rank={row[0]} coef={row[1]} ability={row[2]} name={row[3]}")
        print(f"condition={row[4]}")
        print(f"threshold={row[5] * 100:.1f}%")
        print(f"evidence={row[6]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
