from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_stat_scaling_repository import SkillComponentStatScalingRepository

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
TARGETS = ((5578, 1), (5579, 1))


@dataclass(frozen=True)
class StatScalingAuditRow:
    skill_rank_id: int
    coefficient_number: int
    promoted: bool
    stat: str | None
    scaling_driver: str | None
    maximum_bonus: float | None


def load_stat_scaling_audit(database_path: str | Path) -> tuple[StatScalingAuditRow, ...]:
    repository = SkillComponentStatScalingRepository(database_path)
    rows: list[StatScalingAuditRow] = []
    for rank, coef in TARGETS:
        resolved = repository.resolve(rank, coef)
        item = resolved[0] if resolved else None
        rows.append(
            StatScalingAuditRow(
                skill_rank_id=rank,
                coefficient_number=coef,
                promoted=item is not None,
                stat=item.stat.value if item else None,
                scaling_driver=item.scaling_driver.value if item else None,
                maximum_bonus=item.maximum_bonus if item else None,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[StatScalingAuditRow, ...]) -> dict[str, object]:
    promoted = [row for row in rows if row.promoted]
    return {
        "candidates": len(rows),
        "promoted": len(promoted),
        "unresolved": len(rows) - len(promoted),
        "stats": Counter(row.stat for row in promoted if row.stat),
        "drivers": Counter(row.scaling_driver for row in promoted if row.scaling_driver),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit canonical Phase 6 dynamic stat-scaling rules.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    rows = load_stat_scaling_audit(args.database)
    summary = summarize(rows)

    print("\n========================================")
    print(" PHASE 6 COMPONENT STAT SCALING")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {summary['candidates']}")
    print(f"Canonically promoted:  {summary['promoted']}")
    print(f"Still unresolved:      {summary['unresolved']}")
    print("\nNOTE: current combat-state evaluation remains Phase 8.")

    for row in rows:
        print("\n----------------------------------------")
        print(f"rank={row.skill_rank_id} coef={row.coefficient_number}")
        print(f"status={'PROMOTED' if row.promoted else 'UNRESOLVED'}")
        if row.promoted:
            print(f"stat={row.stat}")
            print(f"scaling_driver={row.scaling_driver}")
            print(f"maximum_bonus={row.maximum_bonus:g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
