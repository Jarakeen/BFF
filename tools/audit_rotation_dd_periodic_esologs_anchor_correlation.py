from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_anchor_correlation_service import (
    RotationDDPeriodicEsoLogsAnchorCorrelationService,
)


def _common(values: tuple[float, ...], *, limit: int = 8) -> str:
    if not values:
        return "none"
    rounded = Counter(round(float(value), 3) for value in values)
    return ", ".join(
        f"{value:g}s x{count}" if count > 1 else f"{value:g}s"
        for value, count in rounded.most_common(limit)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Correlate one canonical DD skill cast with observational impact and "
            "periodic ESO Logs ability IDs. Evidence only; never promotes semantics."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--impact-id", required=True, type=int)
    parser.add_argument("--periodic-id", required=True, type=int)
    parser.add_argument("--active-window", required=True, type=float)
    parser.add_argument("--logs-db", required=True, type=Path)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--report")
    parser.add_argument("--fight", type=int)
    parser.add_argument("--source", type=int)
    args = parser.parse_args(argv)

    if not args.database.is_file():
        print(f"Canonical database file not found: {args.database}")
        return 1
    if not args.logs_db.is_file():
        print(f"ESO Logs database file not found: {args.logs_db}")
        return 2

    report = RotationDDPeriodicEsoLogsAnchorCorrelationService(
        canonical_database_path=args.database,
        logs_database_path=args.logs_db,
    ).inspect(
        args.skill,
        impact_ability_id=args.impact_id,
        periodic_ability_id=args.periodic_id,
        active_window_seconds=args.active_window,
        report_code=args.report,
        fight_id=args.fight,
        source_id=args.source,
    )

    print()
    print("==============================================")
    print(" DD PERIODIC ESO LOGS ANCHOR CORRELATION")
    print("==============================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print(f"Impact evidence ID:   {report.impact_ability_id}")
    print(f"Periodic evidence ID: {report.periodic_ability_id}")
    print(f"Cast anchors: {report.cast_count}")
    print(f"Casts with impact evidence: {report.impact_observation_count}")
    print(f"Casts with periodic evidence after impact: {report.periodic_observation_count}")
    print(f"Cast-track-linked impacts: {report.cast_track_linked_impact_count}")
    print(f"Cast-track-linked periodic events: {report.cast_track_linked_periodic_count}")
    print(
        "Median cast -> impact: "
        + (
            f"{report.median_cast_to_impact_seconds:g}s"
            if report.median_cast_to_impact_seconds is not None
            else "unresolved"
        )
    )
    print(
        "Median impact -> first periodic occurrence: "
        + (
            f"{report.median_impact_to_first_periodic_seconds:g}s"
            if report.median_impact_to_first_periodic_seconds is not None
            else "unresolved"
        )
    )
    print("Common cast -> impact offsets: " + _common(report.cast_to_impact_seconds))
    print(
        "Common impact -> first periodic offsets: "
        + _common(report.impact_to_first_periodic_seconds)
    )
    print("Common periodic intervals: " + _common(report.periodic_intervals_seconds))

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — numeric IDs remain evidence handles; this tool "
        "does not promote an activation anchor or first-tick semantic automatically."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
