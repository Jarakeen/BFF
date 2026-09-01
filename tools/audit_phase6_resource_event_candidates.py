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
from tools.audit_phase6_component_gaps import load_phase6_gap_matrix

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ResourceEventCandidateAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    promoted: bool
    resources: tuple[str, ...]
    phase3_reasons: tuple[str, ...]
    fragment: str


def load_resource_event_candidates(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ResourceEventCandidateAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentResourceEventRepository(path)
    rows: list[ResourceEventCandidateAuditRow] = []

    for gap in load_phase6_gap_matrix(path, limit=limit):
        if "resource_event_candidate" not in gap.signals:
            continue
        events = repository.resolve(gap.skill_rank_id, gap.coefficient_number)
        rows.append(
            ResourceEventCandidateAuditRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                promoted=bool(events),
                resources=tuple(event.resource_type.value for event in events),
                phase3_reasons=gap.phase3_reasons,
                fragment=gap.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[ResourceEventCandidateAuditRow, ...]) -> dict[str, object]:
    promoted = sum(row.promoted for row in rows)
    return {
        "candidates": len(rows),
        "promoted": promoted,
        "unresolved": len(rows) - promoted,
        "resources": Counter(resource for row in rows for resource in row.resources),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Phase 6 resource-event triage candidates with canonical component resource events."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_resource_event_candidates(args.database, limit=args.limit)
    summary = summarize(rows)
    resources: Counter[str] = summary["resources"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 RESOURCE EVENT CANDIDATES")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Candidates:            {summary['candidates']}")
    print(f"Canonically promoted:  {summary['promoted']}")
    print(f"Still unresolved:      {summary['unresolved']}")

    if resources:
        print("\nPROMOTED RESOURCE TYPES")
        for resource, count in resources.most_common():
            print(f"  {resource:28} {count}")

    print("\nNOTE: unresolved candidates remain evidence only; this audit never promotes mechanics.")

    unresolved = [row for row in rows if not row.promoted]
    promoted = [row for row in rows if row.promoted]
    display_rows = unresolved + promoted
    for row in display_rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"status={'PROMOTED' if row.promoted else 'UNRESOLVED'}")
        if row.resources:
            print(f"resources={','.join(row.resources)}")
        if row.phase3_reasons:
            print(f"phase3_gap={','.join(row.phase3_reasons)}")
        if row.fragment:
            print(f"fragment={' '.join(row.fragment.split())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
