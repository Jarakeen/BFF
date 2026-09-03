from __future__ import annotations

"""Validate or persist corroborated encounter phase/transition evidence.

This is deliberately narrower than the general canonical fact writer. It scans
review packets, keeps only timeline-shaped fact types, promotes corroborated
facts only, and leaves single-source/conflicting facts untouched for review.
"""

import argparse
from collections import defaultdict
from pathlib import Path
import sqlite3
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_evidence_packet import load_encounter_evidence_packet
from services.encounter_persistence_plan import build_persistence_plan
from services.encounter_persistence_writer import (
    EncounterWriteResult,
    persist_encounter_plans,
    validate_persistence_target,
)
from services.encounter_promotion import build_encounter_promotion_preview


TIMELINE_FACT_TYPES = {"phase", "transition"}


def _packet_paths(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise FileNotFoundError(f"Encounter evidence path does not exist: {root}")
    return sorted(path for path in root.glob("*.json") if path.is_file())


def _timeline_facts(rows):
    return [
        fact
        for fact in reconcile_encounter_evidence(rows)
        if fact.fact_type.strip().casefold() in TIMELINE_FACT_TYPES
    ]


def _sum_results(results: list[EncounterWriteResult]) -> EncounterWriteResult:
    return EncounterWriteResult(
        facts_inserted=sum(row.facts_inserted for row in results),
        facts_existing=sum(row.facts_existing for row in results),
        evidence_inserted=sum(row.evidence_inserted for row in results),
        evidence_existing=sum(row.evidence_existing for row in results),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate or apply corroborated encounter timeline facts"
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path("data/encounter_evidence"),
        help="Evidence packet directory or one packet JSON file.",
    )
    parser.add_argument("--database", type=Path, default=Path("data/eso.db"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write eligible canonical phase/transition facts. Default is dry-run.",
    )
    args = parser.parse_args()

    try:
        packet_paths = _packet_paths(args.evidence_root)
    except FileNotFoundError as exc:
        print(f"BLOCKED: {exc}")
        return 2

    facts = []
    for path in packet_paths:
        _payload, rows = load_encounter_evidence_packet(path)
        facts.extend(_timeline_facts(rows))

    candidates = build_encounter_promotion_preview(facts)
    plans = build_persistence_plan(candidates)

    eligible = sum(1 for row in candidates if row.promotion_status == "eligible")
    review_required = sum(1 for row in candidates if row.promotion_status == "review_required")
    blocked = sum(1 for row in candidates if row.promotion_status == "blocked")

    print("=" * 76)
    print(" ENCOUNTER TIMELINE CANONICAL PROMOTION")
    print("=" * 76)
    print(f"mode:                  {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"database:              {args.database}")
    print(f"evidence root:         {args.evidence_root}")
    print(f"evidence packets:      {len(packet_paths)}")
    print(f"timeline facts:        {len(facts)}")
    print(f"eligible corroborated: {eligible}")
    print(f"review required:       {review_required}")
    print(f"blocked conflicts:     {blocked}")
    print(f"planned canonical:     {len(plans)}")
    print(f"planned evidence rows: {sum(len(plan.evidence) for plan in plans)}")

    if not args.database.exists():
        print("\nBLOCKED: database file does not exist.")
        return 2

    grouped = defaultdict(list)
    for plan in plans:
        grouped[plan.fact.encounter_id].append(plan)

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        try:
            for encounter_id in sorted(grouped):
                validate_persistence_target(connection, grouped[encounter_id])
        except RuntimeError as exc:
            print(f"\nBLOCKED: {exc}")
            print("No SQLite rows were changed.")
            return 2

        print("\nTarget validation: PASS")
        for encounter_id in sorted(grouped):
            print(f"  {encounter_id}: {len(grouped[encounter_id])} canonical timeline fact(s)")

        if not args.apply:
            print("\nDRY RUN complete. No SQLite rows were changed.")
            return 0

        try:
            connection.execute("BEGIN IMMEDIATE")
            results = [
                persist_encounter_plans(connection, grouped[encounter_id])
                for encounter_id in sorted(grouped)
            ]
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        result = _sum_results(results)
        print("\nAPPLY complete.")
        print(f"canonical facts inserted: {result.facts_inserted}")
        print(f"canonical facts existing: {result.facts_existing}")
        print(f"evidence rows inserted:   {result.evidence_inserted}")
        print(f"evidence rows existing:   {result.evidence_existing}")
        print(f"review-required untouched:{review_required}")
        print(f"conflicting untouched:    {blocked}")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
