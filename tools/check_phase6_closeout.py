from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

    unexpected = {
        name: count
        for name, count in statuses.items()
        if count and name not in _ALLOWED_RESIDUAL_STATUSES
    }
    parser_rows = sum(
        1
        for row in rows
        if row.disposition == "parser_coverage"
    )
    source_blocked = statuses.get("SOURCE_EVIDENCE_BLOCKED", 0)
    needs_review = int(summary["needs_review"])

    passed = not unexpected and parser_rows == 0 and source_blocked == 0 and needs_review == 0
    details: dict[str, object] = {
        "rows": len(rows),
        "statuses": statuses,
        "needs_review": needs_review,
        "parser_rows": parser_rows,
        "source_blocked": source_blocked,
        "unexpected": unexpected,
    }
    return passed, details


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail unless all remaining Phase 6 gap rows are proven classification cleanup, "
            "Phase 7 boundaries, or known ownership negatives."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    passed, details = evaluate_phase6_closeout(args.database)
    statuses: Counter[str] = details["statuses"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 CLOSEOUT GATE")
    print("========================================")
    print(f"Database:                 {args.database}")
    print(f"Residual audit rows:      {details['rows']}")
    print(f"Needs Phase 6 review:     {details['needs_review']}")
    print(f"Parser-coverage rows:     {details['parser_rows']}")
    print(f"Source-evidence blocked:  {details['source_blocked']}")

    print("\nALLOWED RESIDUAL STATUS")
    for name in sorted(_ALLOWED_RESIDUAL_STATUSES):
        print(f"  {name:28} {statuses.get(name, 0)}")

    unexpected: dict[str, int] = details["unexpected"]  # type: ignore[assignment]
    if unexpected:
        print("\nUNEXPECTED STATUS")
        for name, count in sorted(unexpected.items()):
            print(f"  {name:28} {count}")

    if passed:
        print("\nRESULT: PASS")
        print("Phase 6 has no remaining semantic-review, parser-coverage, or source-evidence blockers.")
        return 0

    print("\nRESULT: FAIL")
    print("Phase 6 still has unresolved closeout blockers; inspect tools/audit_phase6_closeout.py output.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
