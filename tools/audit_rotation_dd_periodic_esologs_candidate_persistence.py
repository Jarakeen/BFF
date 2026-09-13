from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_candidate_persistence_service import (
    RotationDDPeriodicEsoLogsCandidatePersistenceService,
)


def _pct(count: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(100.0 * count / total):.1f}%"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure last-observed same-source same-cast-track persistence for DD periodic "
            "candidate IDs using recast-censored ownership windows."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--candidate-id", dest="candidate_ids", type=int, action="append", required=True)
    parser.add_argument("--active-window", type=float, required=True)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", type=Path, required=True)
    parser.add_argument("--report", dest="report_code")
    parser.add_argument("--fight", dest="fight_id", type=int)
    parser.add_argument("--source", dest="source_id", type=int)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsCandidatePersistenceService(
        canonical_database_path=args.database,
        logs_database_path=args.logs_db,
    ).inspect(
        args.skill,
        candidate_ability_ids=tuple(args.candidate_ids),
        active_window_seconds=args.active_window,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
    )

    print()
    print("===================================================")
    print(" DD PERIODIC ESO LOGS CANDIDATE CAST PERSISTENCE")
    print("===================================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print("Candidate evidence IDs: " + ", ".join(str(value) for value in report.candidate_ability_ids))
    print(f"Reviewed active window: {report.active_window_seconds:g}s")
    print(f"Cast anchors: {report.cast_count}")
    print("Ownership rule: same source + same cast track; censored at next same-source cast")

    for summary in report.summaries:
        print()
        print(f"Candidate {summary.candidate_ability_id}")
        total = summary.linked_cast_count
        print(f"  Censored casts with candidate: {total}")
        if total:
            print(
                "  Last-observed offset min/median/max: "
                f"{summary.minimum_last_offset_seconds:.3f}s / "
                f"{summary.median_last_offset_seconds:.3f}s / "
                f"{summary.maximum_last_offset_seconds:.3f}s"
            )
        else:
            print("  Last-observed offset min/median/max: unresolved")
        for threshold, count in (
            (2, summary.observed_at_or_after_2s),
            (5, summary.observed_at_or_after_5s),
            (10, summary.observed_at_or_after_10s),
            (15, summary.observed_at_or_after_15s),
            (19, summary.observed_at_or_after_19s),
        ):
            print(
                f"  Casts with an observation at/after {threshold:>2}s: "
                f"{count:<5} ({_pct(count, total)})"
            )

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — threshold counts mean a candidate event was observed "
        "at or after that offset on the original cast track. They do not prove uninterrupted "
        "uptime, cadence, or executable duration semantics."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
