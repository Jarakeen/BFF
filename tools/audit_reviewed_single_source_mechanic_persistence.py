from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_inferred_mechanic_decisions import load_decisions
from services.boss_inferred_mechanic_review import audit_inferred_boss_mechanics
from services.reviewed_single_source_mechanic_persistence import (
    REVIEW_STATUS,
    build_reviewed_single_source_plans,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit canonical plans for accepted reviewed single-source boss mechanics."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=ROOT / "data" / "eso_info" / "bosses",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "encounter_reviews" / "inferred_boss_mechanics.json",
    )
    args = parser.parse_args()

    source_audit = audit_inferred_boss_mechanics(args.source_dir)
    if source_audit.failures:
        print("RESULT: BLOCKED")
        for failure in source_audit.failures[:10]:
            print(f"  - {failure}")
        return 1

    decisions = load_decisions(args.manifest)
    plans = build_reviewed_single_source_plans(source_audit.rows, decisions)

    accepted = sum(1 for row in decisions if row.status == "accepted")
    rejected = sum(1 for row in decisions if row.status == "rejected")
    pending = sum(1 for row in decisions if row.status == "pending")
    statuses = Counter(plan.fact.review_status for plan in plans)
    encounters = {plan.fact.encounter_id for plan in plans}
    evidence_rows = sum(len(plan.evidence) for plan in plans)
    bad_evidence = [plan.fact.logical_ref for plan in plans if len(plan.evidence) != 1]

    print("=" * 72)
    print(" REVIEWED SINGLE-SOURCE MECHANIC PERSISTENCE AUDIT")
    print("=" * 72)
    print(f"Source mechanics:               {len(source_audit.rows)}")
    print(f"Accepted decisions:             {accepted}")
    print(f"Rejected decisions:             {rejected}")
    print(f"Pending decisions:              {pending}")
    print(f"Persistence plans:              {len(plans)}")
    print(f"Target encounters:              {len(encounters)}")
    print(f"Evidence rows:                  {evidence_rows}")
    print(f"reviewed_single_source plans:   {statuses.get(REVIEW_STATUS, 0)}")
    print(f"Plans with != 1 evidence row:   {len(bad_evidence)}")

    blocked = bool(
        pending
        or len(plans) != accepted
        or statuses != Counter({REVIEW_STATUS: len(plans)})
        or evidence_rows != len(plans)
        or bad_evidence
    )
    print()
    print("RESULT: BLOCKED" if blocked else "RESULT: PASS")
    print("Read-only audit. No canonical facts or evidence rows were changed.")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
