from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_candidate_segment_service import (
    RotationDDPeriodicEsoLogsCandidateSegmentService,
)


def _pct(count: int, total: int) -> str:
    return "0.0%" if total <= 0 else f"{100.0 * count / total:.1f}%"


def _fmt(value: float | None) -> str:
    return "unresolved" if value is None else f"{value:.3f}s"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Observe burst/segment structure within censored DD periodic candidate cast-track streams.")
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

    report = RotationDDPeriodicEsoLogsCandidateSegmentService(
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
    print("==================================================")
    print(" DD PERIODIC ESO LOGS CANDIDATE SEGMENT STRUCTURE")
    print("==================================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print("Candidate evidence IDs: " + ", ".join(str(value) for value in report.candidate_ability_ids))
    print(f"Reviewed active window: {report.active_window_seconds:g}s")
    print(f"Cast anchors: {report.cast_count}")
    print(f"Occurrence cluster tolerance: {report.cluster_tolerance_seconds * 1000:.0f}ms")
    print(f"New segment after gap: > {report.segment_gap_seconds:g}s")
    print("Ownership rule: same source + same cast track; censored at recast, reviewed window end, or fight end")

    for summary in report.summaries:
        print()
        print(f"Candidate {summary.candidate_ability_id}")
        print(f"  Censored casts with candidate stream: {summary.linked_cast_count}")
        print(f"  Multi-segment casts: {summary.multi_segment_cast_count} ({_pct(summary.multi_segment_cast_count, summary.linked_cast_count)})")
        print(f"  Segments/cast median/max: {summary.median_segments_per_cast if summary.median_segments_per_cast is not None else 'unresolved'} / {summary.maximum_segments_per_cast if summary.maximum_segments_per_cast is not None else 'unresolved'}")
        print(f"  Median segment duration: {_fmt(summary.median_segment_duration_seconds)}")
        print(f"  Median occurrences/segment: {summary.median_occurrences_per_segment if summary.median_occurrences_per_segment is not None else 'unresolved'}")
        print(f"  Inter-segment gap median/max: {_fmt(summary.median_inter_segment_gap_seconds)} / {_fmt(summary.maximum_inter_segment_gap_seconds)}")
        print(f"  Later segment starts >=  5s: {summary.resumed_at_or_after_5s} ({_pct(summary.resumed_at_or_after_5s, summary.linked_cast_count)})")
        print(f"  Later segment starts >= 10s: {summary.resumed_at_or_after_10s} ({_pct(summary.resumed_at_or_after_10s, summary.linked_cast_count)})")
        print(f"  Later segment starts >= 15s: {summary.resumed_at_or_after_15s} ({_pct(summary.resumed_at_or_after_15s, summary.linked_cast_count)})")

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print("Result: OBSERVATIONAL ONLY — segmentation describes clustered event structure on the original cast track. It does not establish a gameplay condition, cadence, duration, or executable runtime rule.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
