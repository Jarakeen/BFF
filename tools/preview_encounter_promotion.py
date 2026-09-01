from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import (
    PROMOTION_BLOCKED,
    PROMOTION_ELIGIBLE,
    PROMOTION_REVIEW_REQUIRED,
    build_encounter_promotion_preview,
)
from tools.reconcile_encounter_evidence import _display_value, _load_packet


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Preview which reconciled encounter facts are eligible for canonical promotion"
    )
    ap.add_argument("packet", type=Path)
    ap.add_argument(
        "--status",
        choices=(PROMOTION_ELIGIBLE, PROMOTION_REVIEW_REQUIRED, PROMOTION_BLOCKED),
        help="Show only candidates with this promotion status.",
    )
    args = ap.parse_args()

    payload, evidence = _load_packet(args.packet)
    reconciled = reconcile_encounter_evidence(evidence)
    all_candidates = build_encounter_promotion_preview(reconciled)
    candidates = all_candidates
    if args.status:
        candidates = [c for c in candidates if c.promotion_status == args.status]

    print("=" * 76)
    print(" ENCOUNTER CANONICAL PROMOTION PREVIEW - READ ONLY")
    print("=" * 76)
    print(f"packet:          {args.packet}")
    print(f"content:         {payload.get('content_id', '(unknown)')}")
    print(f"encounter:       {payload.get('encounter_name', payload.get('encounter_id', '(unknown)'))}")
    print(f"reconciled facts:{len(reconciled):>6}")

    for status in (PROMOTION_ELIGIBLE, PROMOTION_REVIEW_REQUIRED, PROMOTION_BLOCKED):
        count = sum(1 for c in all_candidates if c.promotion_status == status)
        print(f"{status + ':':17} {count}")

    if not candidates:
        print("\nNo facts match the requested filter.")
    else:
        for candidate in candidates:
            fact = candidate.fact
            print()
            print(
                f"[{candidate.promotion_status.upper()}] "
                f"{fact.fact_type}:{fact.fact_key} "
                f"reconciliation={fact.status}"
            )
            if fact.value is not None:
                print(f"  value: {_display_value(fact.value)}")
            else:
                print("  value: unresolved because sources conflict")
            print(f"  reason: {candidate.reason}")
            print(f"  evidence sources: {fact.distinct_sources}")

    print("\nPreview only. No canonical encounter rows or source JSON files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
