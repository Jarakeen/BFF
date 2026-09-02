from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_current_bonus_repository import SkillComponentCurrentBonusRepository
from tools.audit_phase6_component_gaps import load_phase6_gap_matrix

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class CurrentBonusAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_name: str
    status: str
    kind: str
    detail: str
    fragment: str


def load_current_bonus_semantics(database_path: str | Path) -> tuple[CurrentBonusAuditRow, ...]:
    repo = SkillComponentCurrentBonusRepository(database_path)
    rows: list[CurrentBonusAuditRow] = []
    for gap in load_phase6_gap_matrix(database_path):
        if gap.disposition != "parser_coverage" or "current bonus" not in gap.fragment.casefold():
            continue
        resolved = repo.resolve(gap.skill_rank_id, gap.coefficient_number)
        if resolved:
            item = resolved[0]
            detail = (
                f"stats={','.join(stat.value for stat in item.stats)}; "
                f"driver={item.driver.value}; mode={item.mode.value}; amount_per_unit={item.amount_per_unit:g}"
            )
            status = "PROMOTED_STAT_TOTAL"
            kind = "stat_total"
        else:
            lower = gap.fragment.casefold()
            if "health" in lower or "stamina" in lower or "magicka" in lower:
                status = "RESOURCE_DISPLAY_REVIEW"
                kind = "resource_restore"
                detail = "current resource-restore display belongs to resource/trigger semantics"
            else:
                status = "UNRESOLVED"
                kind = "unknown"
                detail = "current bonus source not resolved by stat-total semantics"
        rows.append(CurrentBonusAuditRow(
            gap.skill_rank_id,
            gap.coefficient_number,
            gap.name,
            status,
            kind,
            detail,
            " ".join(gap.fragment.split()),
        ))
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 6 Current bonus coefficient semantics.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()

    rows = load_current_bonus_semantics(args.database)
    counts = Counter(row.status for row in rows)
    print("\n========================================")
    print(" PHASE 6 CURRENT BONUS SEMANTICS")
    print("========================================")
    print(f"Database: {args.database}")
    print(f"Rows:     {len(rows)}")
    print("\nSTATUS")
    for key, value in counts.most_common():
        print(f"  {key:28} {value}")
    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(f"rank={row.skill_rank_id} coef={row.coefficient_number} name={row.ability_name}")
        print(f"status={row.status}")
        print(f"kind={row.kind}")
        print(row.detail)
        print(f"fragment={row.fragment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
