from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_secondary_effect_discovery_service import (
    RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService,
)


def _compact_values(values: tuple[float, ...], *, limit: int = 8) -> str:
    if not values:
        return "none"
    rounded = [round(float(value), 3) for value in values]
    counts = Counter(rounded)
    common = counts.most_common(limit)
    return ", ".join(
        f"{value:g}s" + (f" x{count}" if count > 1 else "")
        for value, count in common
    )


def audit_skill(
    *,
    database_path: Path,
    logs_database_path: Path,
    skill: str,
    report_code: str | None = None,
    fight_id: int | None = None,
    source_id: int | None = None,
    max_candidates: int = 12,
) -> int:
    if not database_path.is_file():
        print(f"Canonical database file not found: {database_path}")
        return 1
    if not logs_database_path.is_file():
        print(f"ESO Logs SQLite file not found: {logs_database_path}")
        return 2

    report = RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService(
        canonical_database_path=database_path,
        logs_database_path=logs_database_path,
    ).inspect_skill(
        skill,
        report_code=report_code,
        fight_id=fight_id,
        source_id=source_id,
        max_candidates=max_candidates,
    )

    print()
    print("===============================================")
    print(" DD PERIODIC ESO LOGS SECONDARY EFFECT DISCOVERY")
    print("===============================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print(f"Cast anchors: {report.cast_count}")
    print(
        "Reviewed active window: "
        + (
            f"{report.reviewed_duration_seconds:g}s"
            if report.reviewed_duration_seconds is not None
            else "unresolved"
        )
    )
    print(
        "Reviewed cadence: "
        + (
            f"{report.reviewed_interval_seconds:g}s"
            if report.reviewed_interval_seconds is not None
            else "unresolved"
        )
    )
    print(f"Secondary candidates: {len(report.candidates)}")

    for index, candidate in enumerate(report.candidates, start=1):
        print()
        print(f"  [{index}] {candidate.ability_entity_id}")
        if candidate.ability_names:
            print("      ESO Logs names: " + " | ".join(candidate.ability_names))
        print(
            "      ability ids: "
            + (", ".join(str(value) for value in candidate.ability_game_ids) or "none")
        )
        print(f"      cast windows observed: {candidate.cast_windows_observed}")
        print(
            f"      events/occurrences: {candidate.event_count}/{candidate.occurrence_count}"
        )
        print(f"      tick-marked events: {candidate.tick_marked_event_count}")
        print(
            "      cast-track linked events: "
            f"{candidate.cast_track_linked_event_count}"
        )
        print(
            "      reviewed cadence matches: "
            f"{candidate.reviewed_interval_match_count}"
        )
        print(
            "      median first offset: "
            + (
                f"{candidate.median_first_offset_seconds:g}s"
                if candidate.median_first_offset_seconds is not None
                else "unresolved"
            )
        )
        print(
            "      common first offsets: "
            + _compact_values(candidate.first_offset_samples_seconds)
        )
        print(
            "      common observed intervals: "
            + _compact_values(candidate.interval_samples_seconds)
        )

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: CANDIDATE EVIDENCE ONLY — secondary identities are ranked for review; "
        "nothing here is promoted into executable periodic semantics automatically."
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Discover secondary ESO Logs damage identities that repeatedly occur after "
            "one canonical DD periodic skill cast."
        )
    )
    parser.add_argument("--skill", required=True, help="Canonical skill name or lower_snake identity")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE),
        help="Canonical ESO SQLite database for skill identity/crosswalks",
    )
    parser.add_argument(
        "--logs-db",
        type=Path,
        required=True,
        help="SQLite database containing imported ESO Logs log_event rows",
    )
    parser.add_argument("--report", dest="report_code", help="Optional report code filter")
    parser.add_argument("--fight", dest="fight_id", type=int, help="Optional fight id filter")
    parser.add_argument("--source", dest="source_id", type=int, help="Optional source actor id filter")
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=12,
        help="Maximum ranked secondary identities to print (default: 12)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return audit_skill(
        database_path=args.database,
        logs_database_path=args.logs_db,
        skill=args.skill,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
        max_candidates=args.max_candidates,
    )


if __name__ == "__main__":
    raise SystemExit(main())
