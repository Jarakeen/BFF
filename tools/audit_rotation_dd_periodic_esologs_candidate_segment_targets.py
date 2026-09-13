from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_candidate_segment_target_service import (
    RotationDDPeriodicEsoLogsCandidateSegmentTargetService,
)


def _pct(count: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{100.0 * count / total:.1f}%"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Observe whether later same-track DD periodic candidate segments revisit "
            "previous targets or introduce new targets."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--candidate-id", dest="candidate_ids", type=int, action="append", required=True)
    parser.add_argument("--active-window", type=float, required=True)
    parser.add_argument("--cluster-tolerance", type=float, default=0.05)
    parser.add_argument("--segment-gap", type=float, default=2.0)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", type=Path, required=True)
    parser.add_argument("--report", dest="report_code")
    parser.add_argument("--fight", dest="fight_id", type=int)
    parser.add_argument("--source", dest="source_id", type=int)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsCandidateSegmentTargetService(
        canonical_database_path=args.database,
        logs_database_path=args.logs_db,
    ).inspect(
        args.skill,
        candidate_ability_ids=tuple(args.candidate_ids),
        active_window_seconds=args.active_window,
        cluster_tolerance_seconds=args.cluster_tolerance,
        segment_gap_seconds=args.segment_gap,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
    )

    print()
    print("========================================================")
    print(" DD PERIODIC ESO LOGS CANDIDATE SEGMENT TARGET TOPOLOGY")
    print("========================================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print("Candidate evidence IDs: " + ", ".join(str(value) for value in report.candidate_ability_ids))
    print(f"Reviewed active window: {report.active_window_seconds:g}s")
    print(f"Cast anchors: {report.cast_count}")
    print(f"Occurrence cluster tolerance: {report.cluster_tolerance_seconds * 1000:g}ms")
    print(f"New segment after gap: > {report.segment_gap_seconds:g}s")
    print("Later target relation compares each segment with all targets seen earlier on the same cast track.")

    for summary in report.summaries:
        print()
        print(f"Candidate {summary.candidate_ability_id}")
        print(f"  Censored casts with candidate stream: {summary.linked_cast_count}")
        print(
            f"  Multi-segment casts: {summary.multi_segment_cast_count} "
            f"({_pct(summary.multi_segment_cast_count, summary.linked_cast_count)})"
        )
        print(f"  Later segments observed: {summary.later_segment_count}")
        print(
            "  Later segment target relation: "
            f"repeat-only={summary.repeat_only_later_segment_count}  "
            f"new-only={summary.new_only_later_segment_count}  "
            f"mixed={summary.mixed_later_segment_count}  "
            f"unknown={summary.unknown_target_later_segment_count}"
        )
        first = "unresolved" if summary.median_targets_first_segment is None else f"{summary.median_targets_first_segment:.1f}"
        later = "unresolved" if summary.median_targets_later_segment is None else f"{summary.median_targets_later_segment:.1f}"
        print(f"  Median distinct targets first/later segment: {first} / {later}")
        for threshold, repeat_count, new_count in (
            (5, summary.repeat_or_mixed_start_at_or_after_5s, summary.new_only_start_at_or_after_5s),
            (10, summary.repeat_or_mixed_start_at_or_after_10s, summary.new_only_start_at_or_after_10s),
            (15, summary.repeat_or_mixed_start_at_or_after_15s, summary.new_only_start_at_or_after_15s),
        ):
            print(
                f"  Later segment starts >= {threshold:>2}s: "
                f"revisits-prior-target={repeat_count:<4} new-target-only={new_count:<4}"
            )

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — target reuse can distinguish later re-engagement "
        "from newly affected targets, but it does not identify the gameplay condition "
        "or promote executable runtime semantics."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
