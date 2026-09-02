from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_source_alignment_issue_repository import (
    SkillComponentSourceAlignmentIssueRepository,
)
from tools.audit_phase6_closeout import load_phase6_closeout, summarize

DEFAULT_DATABASE = ROOT / "data" / "eso.db"

_ALLOWED_RESIDUAL_STATUSES = {
    "CLASSIFICATION_CLEANUP",
    "PHASE7_BOUNDARY",
    "OWNERSHIP_NEGATIVE",
}


def evaluate_phase6_closeout(database_path: str | Path) -> tuple[bool, dict[str, object]]:
    rows = load_phase6_closeout(database_path)
    summary = summarize(rows)
    statuses: Counter[str] = summary["statuses"]  # type: ignore[assignment]

    source_issue_repository = SkillComponentSourceAlignmentIssueRepository(database_path)
    source_rows = [row for row in rows if row.closeout_status == "SOURCE_EVIDENCE_BLOCKED"]
    unsupported_source_rows = [
        row
        for row in source_rows
        if source_issue_repository.resolve(row.skill_rank_id, row.coefficient_number)
    ]
    unsupported_keys = {
        (row.skill_rank_id, row.coefficient_number) for row in unsupported_source_rows
    }
    unresolved_source_rows = [
        row
        for row in source_rows
        if (row.skill_rank_id, row.coefficient_number) not in unsupported_keys
    ]

    unexpected = {
        name: count
        for name, count in statuses.items()
        if count and name not in _ALLOWED_RESIDUAL_STATUSES and name != "SOURCE_EVIDENCE_BLOCKED"
    }
    if unresolved_source_rows:
        unexpected["SOURCE_EVIDENCE_BLOCKED"] = len(unresolved_source_rows)

    parser_rows = sum(1 for row in rows if row.disposition == "parser_coverage")
    needs_review = int(summary["needs_review"])

    passed = not unexpected and parser_rows == 0 and needs_review == 0
    details: dict[str, object] = {
        "rows": len(rows),
        "statuses": statuses,
        "needs_review": needs_review,
        "parser_rows": parser_rows,
        "source_blocked": len(source_rows),
        "unsupported_source_alignment": len(unsupported_source_rows),
        "unresolved_source_blocked": len(unresolved_source_rows),
        "unexpected": unexpected,
    }
    return passed, details


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail unless all remaining Phase 6 gap rows are proven cleanup, Phase 7 boundaries, "
            "known ownership negatives, or explicitly classified unsupported source alignment."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    passed, details = evaluate_phase6_closeout(args.database)
    statuses: Counter[str] = details["statuses"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 CLOSEOUT GATE")
    print("========================================")
    print(f"Database:                     {args.database}")
    print(f"Residual audit rows:          {details['rows']}")
    print(f"Needs Phase 6 review:         {details['needs_review']}")
    print(f"Parser-coverage rows:         {details['parser_rows']}")
    print(f"Source-evidence blocked:      {details['source_blocked']}")
    print(f"Unsupported source alignment: {details['unsupported_source_alignment']}")
    print(f"Unresolved source blocks:     {details['unresolved_source_blocked']}")

    print("\nALLOWED RESIDUAL STATUS")
    for name in sorted(_ALLOWED_RESIDUAL_STATUSES):
        print(f"  {name:28} {statuses.get(name, 0)}")
    print(f"  {'UNSUPPORTED_SOURCE_ALIGNMENT':28} {details['unsupported_source_alignment']}")

    unexpected: dict[str, int] = details["unexpected"]  # type: ignore[assignment]
    if unexpected:
        print("\nUNEXPECTED STATUS")
        for name, count in sorted(unexpected.items()):
            print(f"  {name:28} {count}")

    if passed:
        print("\nRESULT: PASS")
        print(
            "Phase 6 has no remaining semantic-review, parser-coverage, or unexplained source blockers. "
            "Any retained source-alignment anomaly is explicitly unsupported rather than guessed."
        )
        return 0

    print("\nRESULT: FAIL")
    print("Phase 6 still has unresolved closeout blockers; inspect tools/audit_phase6_closeout.py output.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
