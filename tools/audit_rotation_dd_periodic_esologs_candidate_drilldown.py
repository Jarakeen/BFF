from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_candidate_drilldown_service import (
    RotationDDPeriodicEsoLogsCandidateDrilldownService,
)


def _common(values: tuple[float, ...], *, limit: int = 12) -> str:
    if not values:
        return "none"
    counts = Counter(round(float(value), 3) for value in values)
    return ", ".join(
        f"{value:g}s" + (f" x{count}" if count > 1 else "")
        for value, count in counts.most_common(limit)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Drill into one observational ESO Logs secondary-effect candidate without promoting mechanics."
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--candidate-id", required=True, type=int)
    parser.add_argument("--active-window", required=True, type=float)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", required=True, type=Path)
    parser.add_argument("--report", dest="report_code")
    parser.add_argument("--fight", dest="fight_id", type=int)
    parser.add_argument("--source", dest="source_id", type=int)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsCandidateDrilldownService(
        canonical_database_path=args.database,
        logs_database_path=args.logs_db,
    ).inspect(
        args.skill,
        candidate_ability_id=args.candidate_id,
        active_window_seconds=args.active_window,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
    )

    print("\n================================================")
    print(" DD PERIODIC ESO LOGS CANDIDATE DRILLDOWN")
    print("================================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print(f"Candidate ability id: {report.candidate_ability_id}")
    print(f"Reviewed active window: {report.active_window_seconds:g}s")
    print(f"Cast anchors: {report.cast_count}")
    print(f"Same-track casts with candidate: {report.linked_cast_count}")
    print(f"Candidate events: {report.event_count}")
    print(f"Same-track candidate events: {report.linked_event_count}")
    print("Observed names: " + (" | ".join(report.ability_names) or "none"))
    print("Event types: " + (", ".join(f"{kind}={count}" for kind, count in report.event_types) or "none"))
    print("Distinct targets: " + (str(report.target_count) if report.target_count is not None else "unavailable"))
    print("Median first offset: " + (f"{report.median_first_offset_seconds:g}s" if report.median_first_offset_seconds is not None else "unresolved"))
    print("Median last offset: " + (f"{report.median_last_offset_seconds:g}s" if report.median_last_offset_seconds is not None else "unresolved"))
    print(f"Events within ±0.25s of active-window end: {report.near_active_end_count}")
    print("Common first offsets: " + _common(report.first_offsets_seconds))
    print("Common last offsets: " + _common(report.last_offsets_seconds))
    print("Common same-track intervals: " + _common(report.within_cast_intervals_seconds))
    if report.unresolved:
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")
    print("\nResult: OBSERVATIONAL ONLY — this drilldown distinguishes candidate behavior; it never promotes executable semantics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
