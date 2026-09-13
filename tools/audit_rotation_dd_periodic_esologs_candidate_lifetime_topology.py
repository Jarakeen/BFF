from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_candidate_lifetime_topology_service import (
    RotationDDPeriodicEsoLogsCandidateLifetimeTopologyService,
)


def _print_groups(groups) -> None:
    current_candidate = None
    for group in groups:
        if group.candidate_ability_id != current_candidate:
            current_candidate = group.candidate_ability_id
            print()
            print(f"Candidate {current_candidate}")
        median_text = (
            f"{group.median_offset_seconds:.3f}s"
            if group.median_offset_seconds is not None
            else "unresolved"
        )
        latest_text = (
            f"{group.latest_offset_seconds:.3f}s"
            if group.latest_offset_seconds is not None
            else "unresolved"
        )
        print(
            f"  {group.time_band:>6} | {group.source_relation:<12} | "
            f"{group.track_relation:<13} | obs={group.observation_count:<6} "
            f"windows={group.cast_window_count:<5} sources={group.distinct_source_count:<4} "
            f"targets={group.distinct_target_count:<4} tracks={group.distinct_track_count:<5} "
            f"median={median_text:<10} latest={latest_text}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Observe source/target/cast-track topology for numeric DD periodic evidence "
            "candidates across one reviewed cast lifetime."
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

    report = RotationDDPeriodicEsoLogsCandidateLifetimeTopologyService(
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
    print("========================================================")
    print(" DD PERIODIC ESO LOGS CANDIDATE LIFETIME TOPOLOGY")
    print("========================================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print("Candidate evidence IDs: " + ", ".join(str(value) for value in report.candidate_ability_ids))
    print(f"Reviewed active window: {report.active_window_seconds:g}s")
    print(f"Cast anchors: {report.cast_count}")
    print(f"Cast-window observations: {report.observation_count}")
    print(f"Unique candidate events represented: {report.unique_event_count}")
    print(f"Overlapping-window reuse: {report.overlapping_window_reuse_count}")

    print("\nBroad overlapping-window topology")
    _print_groups(report.groups)

    print("\nCensored same-source ownership topology")
    print("  Window rule: cast -> next same-source cast, capped at reviewed active window")
    print(f"  Observations: {report.censored_same_source_observation_count}")
    print(f"  Unique candidate events represented: {report.censored_same_source_unique_event_count}")
    _print_groups(report.censored_same_source_groups)

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — numeric IDs remain evidence handles. The censored "
        "same-source view removes later same-source recasts and other actors from lifetime "
        "ownership evidence, but still does not promote canonical or executable semantics."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
