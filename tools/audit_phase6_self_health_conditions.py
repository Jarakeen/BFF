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

from minmax.skill_component_condition import SkillComponentConditionType
from minmax.skill_component_condition_repository import SkillComponentConditionRepository
from tools.audit_phase6_component_gaps import load_phase6_gap_matrix

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
_SELF_HEALTH_RE = re.compile(
    r"\b(?:your|the\s+caster(?:'s)?|caster(?:'s)?)\s+health\s+(?:drops?|falls?|is)\s+"
    r"(?:below|under|less\s+than)\s+\d+(?:\.\d+)?\s*%\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SelfHealthConditionAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    promoted: bool
    threshold: float | None
    fragment: str


def load_self_health_condition_audit(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[SelfHealthConditionAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentConditionRepository(path)
    rows: list[SelfHealthConditionAuditRow] = []

    for gap in load_phase6_gap_matrix(path, limit=limit):
        fragment = " ".join(str(gap.fragment or "").split())
        if not _SELF_HEALTH_RE.search(fragment):
            continue

        conditions = repository.resolve(gap.skill_rank_id, gap.coefficient_number)
        matched = next(
            (
                condition
                for condition in conditions
                if condition.condition_type is SkillComponentConditionType.SELF_HEALTH_BELOW_PERCENT
            ),
            None,
        )
        rows.append(
            SelfHealthConditionAuditRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                promoted=matched is not None,
                threshold=None if matched is None else matched.threshold,
                fragment=fragment,
            )
        )

    return tuple(rows)


def summarize(rows: tuple[SelfHealthConditionAuditRow, ...]) -> dict[str, object]:
    promoted = [row for row in rows if row.promoted]
    return {
        "candidates": len(rows),
        "promoted": len(promoted),
        "unresolved": len(rows) - len(promoted),
        "thresholds": Counter(row.threshold for row in promoted),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit explicit Phase 6 self-health threshold conditions against the real coefficient corpus."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_self_health_condition_audit(args.database, limit=args.limit)
    summary = summarize(rows)
    thresholds: Counter[float] = summary["thresholds"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 SELF HEALTH CONDITIONS")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {summary['candidates']}")
    print(f"Canonically promoted:  {summary['promoted']}")
    print(f"Still unresolved:      {summary['unresolved']}")

    if thresholds:
        print("\nTHRESHOLDS")
        for threshold, count in thresholds.most_common():
            print(f"  {threshold * 100:5.1f}%                     {count}")

    print("\nNOTE: Phase 6 records the threshold rule; current Health evaluation remains a later-phase concern.")

    ordered = sorted(rows, key=lambda row: (not row.promoted, row.skill_rank_id, row.coefficient_number))
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={'PROMOTED' if row.promoted else 'UNRESOLVED'}")
        if row.threshold is not None:
            print(f"threshold={row.threshold * 100:.1f}%")
        print(f"fragment={row.fragment}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
