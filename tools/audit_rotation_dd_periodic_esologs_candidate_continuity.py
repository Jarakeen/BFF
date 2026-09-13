from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_candidate_continuity_service import (
    RotationDDPeriodicEsoLogsCandidateContinuityService,
)


def _fmt(value: float | None) -> str:
    return "unresolved" if value is None else f"{value:.3f}s"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure occurrence continuity and inter-occurrence gaps for long-lived, "
            "same-source, same-cast-track DD periodic evidence candidates."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--candidate-id", dest="candidate_ids", type=int, action="append", required=True)
    parser.add_argument("--active-window", type=float, required=True)
    parser.add_argument("--cluster-tolerance-ms", type=float, default=50.0)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", type=Path, required=True)
    parser.add_argument("--report", dest="report_code")
    parser.add_argument("--fight", dest="fight_id", type=int)
    parser.add_argument("--source", dest="source_id", type=int)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsCandidateContinuityService(
        canonical_database_path=args.database,
        logs_database_path=args.logs_db,
    ).inspect(
        args.skill,
        candidate_ability_ids=tuple(args.candidate_ids),
        active_window_seconds=args.active_window,
        cluster_tolerance_seconds=args.cluster_tolerance_ms / 1000.0,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
    )

    print()
    print("==================================================")
    print(" DD PERIODIC ESO LOGS CANDIDATE CONTINUITY")
    print("==================================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print("Candidate evidence IDs: " + ", ".join(str(value) for value in report.candidate_ability_ids))
    print(f"Reviewed active window: {report.active_window_seconds:g}s")
    print(f"Cast anchors: {report.cast_count}")
    print(f"Occurrence cluster tolerance: {report.cluster_tolerance_seconds * 1000.0:g}ms")
    print("Ownership rule: same source + same cast track; censored at recast, reviewed window end, or fight end")

    for summary in report.summaries:
        print()
        print(f"Candidate {summary.candidate_ability_id}")
        print(f"  Censored casts with candidate stream: {summary.linked_cast_count}")
        for item in summary.thresholds:
            print(
                f"  Reaches {item.threshold_seconds:>2.0f}s: casts={item.qualifying_cast_count:<4} "
                f"median_occurrences={item.median_occurrence_count if item.median_occurrence_count is not None else 'unresolved'} "
                f"first={_fmt(item.median_first_offset_seconds)} "
                f"last={_fmt(item.median_last_offset_seconds)} "
                f"median_gap={_fmt(item.median_gap_seconds)} "
                f"median_max_gap={_fmt(item.median_max_gap_seconds)} "
                f"max_gap={_fmt(item.maximum_gap_seconds)}"
            )

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — long-lived streams are selected by their last observed "
        "candidate event. Near-simultaneous AoE fan-out is clustered before gap measurement. "
        "Gap statistics do not establish uninterrupted uptime or executable cadence."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
