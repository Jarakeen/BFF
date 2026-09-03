from __future__ import annotations

"""Validate or persist human-reviewed single-source inferred boss mechanics.

The review manifest remains the authority for acceptance. Accepted mechanics are
converted into ``reviewed_single_source`` canonical plans, grouped by encounter,
and passed through the existing strict schema-v3 persistence writer. Rejected or
pending decisions are never written.
"""

import argparse
from collections import defaultdict
from pathlib import Path
import sqlite3
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_inferred_mechanic_decisions import load_decisions
from services.boss_inferred_mechanic_review import audit_inferred_boss_mechanics
from services.encounter_persistence_plan import EncounterPersistencePlan
from services.encounter_persistence_writer import (
    EncounterWriteResult,
    persist_encounter_plans,
    validate_persistence_target,
)
from services.reviewed_single_source_mechanic_persistence import (
    REVIEW_STATUS,
    build_reviewed_single_source_plans,
)


def group_plans_by_encounter(
    plans: Iterable[EncounterPersistencePlan],
) -> tuple[tuple[str, tuple[EncounterPersistencePlan, ...]], ...]:
    grouped: dict[str, list[EncounterPersistencePlan]] = defaultdict(list)
    for plan in plans:
        grouped[plan.fact.encounter_id].append(plan)
    return tuple(
        (encounter_id, tuple(grouped[encounter_id]))
        for encounter_id in sorted(grouped)
    )


def _sum_results(results: Iterable[EncounterWriteResult]) -> EncounterWriteResult:
    rows = tuple(results)
    return EncounterWriteResult(
        facts_inserted=sum(row.facts_inserted for row in rows),
        facts_existing=sum(row.facts_existing for row in rows),
        evidence_inserted=sum(row.evidence_inserted for row in rows),
        evidence_existing=sum(row.evidence_existing for row in rows),
    )


def _build_plans(source_dir: Path, manifest: Path) -> list[EncounterPersistencePlan]:
    source_audit = audit_inferred_boss_mechanics(source_dir)
    if source_audit.failures:
        raise RuntimeError("boss source audit failed: " + source_audit.failures[0])
    decisions = load_decisions(manifest)
    pending = [decision for decision in decisions if decision.status == "pending"]
    if pending:
        first = pending[0]
        raise RuntimeError(
            "review manifest still contains pending decisions: "
            f"{first.encounter_id} :: {first.mechanic_name}"
        )
    plans = build_reviewed_single_source_plans(source_audit.rows, decisions)
    bad_status = [plan for plan in plans if plan.fact.review_status != REVIEW_STATUS]
    if bad_status:
        raise RuntimeError("reviewed single-source planner returned an unexpected review status")
    return plans


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate or persist accepted reviewed single-source boss mechanics."
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
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "data" / "eso.db",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write canonical fact/evidence rows. Without this flag the command is validation-only.",
    )
    args = parser.parse_args()

    try:
        plans = _build_plans(args.source_dir, args.manifest)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"BLOCKED: {exc}")
        print("No canonical facts or evidence rows were changed.")
        return 2

    groups = group_plans_by_encounter(plans)
    evidence_count = sum(len(plan.evidence) for plan in plans)

    print("=" * 72)
    print(" REVIEWED SINGLE-SOURCE MECHANIC WRITER")
    print("=" * 72)
    print(f"Mode:                         {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Database:                     {args.database}")
    print(f"Accepted persistence plans:   {len(plans)}")
    print(f"Target encounters:            {len(groups)}")
    print(f"Planned evidence rows:        {evidence_count}")
    print(f"Review status:                {REVIEW_STATUS}")

    if not args.database.exists():
        print("\nRESULT: BLOCKED")
        print("Database file does not exist. No SQLite rows were changed.")
        return 2

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        try:
            # Validate every encounter group before any writes. The underlying
            # writer deliberately accepts one encounter per controlled batch.
            for _, encounter_plans in groups:
                validate_persistence_target(connection, encounter_plans)
        except RuntimeError as exc:
            print(f"\nRESULT: BLOCKED\n{exc}")
            print("No SQLite rows were changed.")
            return 2

        print("\nTarget validation: PASS")
        if not args.apply:
            print("RESULT: PASS")
            print("Dry run only. No canonical facts or evidence rows were changed.")
            return 0

        results: list[EncounterWriteResult] = []
        try:
            connection.execute("BEGIN IMMEDIATE")
            # Revalidate while holding the write transaction, then persist each
            # encounter through the existing one-encounter writer boundary.
            for _, encounter_plans in groups:
                validate_persistence_target(connection, encounter_plans)
            for _, encounter_plans in groups:
                results.append(persist_encounter_plans(connection, encounter_plans))
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        total = _sum_results(results)
        print("\nRESULT: PASS")
        print(f"Canonical facts inserted:     {total.facts_inserted}")
        print(f"Canonical facts existing:     {total.facts_existing}")
        print(f"Evidence rows inserted:       {total.evidence_inserted}")
        print(f"Evidence rows existing:       {total.evidence_existing}")
        print("Rejected review decisions were not persisted.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
