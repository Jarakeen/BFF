from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_source_window_exclusivity_service import (
    RotationDDPeriodicEsoLogsSourceWindowExclusivityService,
)


def _rate(value: float | None) -> str:
    return "unresolved" if value is None else f"{value:.3f}/min"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare one observational periodic candidate inside and outside a reviewed "
            "skill active window without promoting identity or mechanics."
        )
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

    report = RotationDDPeriodicEsoLogsSourceWindowExclusivityService(
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

    print("\n====================================================")
    print(" DD PERIODIC ESO LOGS SOURCE WINDOW EXCLUSIVITY")
    print("====================================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print(f"Candidate ability id: {report.candidate_ability_id}")
    print(f"Assumed active window: {report.active_window_seconds:g}s")
    print(f"Cast anchors: {report.cast_count}")
    print(f"Caster source/fight groups: {report.caster_source_groups}")
    print(f"Merged active exposure: {report.active_exposure_seconds:.3f}s")
    print(f"Inactive exposure on same caster groups: {report.inactive_exposure_seconds:.3f}s")
    print(f"Candidate events inside windows: {report.candidate_events_inside_windows}")
    print(f"Candidate events outside windows: {report.candidate_events_outside_windows}")
    print(f"Inside event rate: {_rate(report.inside_rate_per_minute)}")
    print(f"Outside event rate: {_rate(report.outside_rate_per_minute)}")
    ratio = report.inside_outside_rate_ratio
    print("Inside/outside rate ratio: " + ("unresolved" if ratio is None else f"{ratio:.3f}x"))
    print(f"Non-caster source/fight groups emitting candidate: {report.noncaster_source_groups_with_candidate}")
    print(f"Candidate events on non-caster groups: {report.noncaster_candidate_events}")
    if report.unresolved:
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")
    print(
        "\nResult: OBSERVATIONAL ONLY — concentration inside an assumed active window can "
        "strengthen candidate association, but it does not establish canonical identity, "
        "current duration, or executable runtime semantics."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
