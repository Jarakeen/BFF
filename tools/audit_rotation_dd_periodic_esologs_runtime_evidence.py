from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_runtime_evidence_service import (
    RotationDDPeriodicEsoLogsRuntimeEvidenceService,
)


def audit_skill(
    *,
    database_path: Path,
    skill: str,
    report_code: str | None = None,
    fight_id: int | None = None,
    source_id: int | None = None,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1

    result = RotationDDPeriodicEsoLogsRuntimeEvidenceService(database_path).inspect_skill(
        skill,
        report_code=report_code,
        fight_id=fight_id,
        source_id=source_id,
    )

    print()
    print("============================================")
    print(" DD PERIODIC ESO LOGS RUNTIME EVIDENCE")
    print("============================================")
    print(f"Skill: {result.skill_entity_id or '(unresolved)'}")
    print(
        "Observed/crosswalk ability IDs: "
        + (", ".join(str(value) for value in result.observed_ability_ids) or "none")
    )
    print(f"Cast observations: {len(result.casts)}")

    for index, cast in enumerate(result.casts, start=1):
        print()
        print(
            f"  [{index}] report={cast.report_code} fight={cast.fight_id} "
            f"source={cast.source_id} cast={cast.cast_timestamp_ms:g}ms "
            f"event={cast.cast_event_type}"
        )
        print(
            "      first tick offset: "
            + (
                f"{cast.first_tick_offset_seconds:g}s"
                if cast.first_tick_offset_seconds is not None
                else "unresolved"
            )
        )
        print(
            "      observed intervals: "
            + (
                ", ".join(f"{value:g}s" for value in cast.tick_intervals_seconds)
                if cast.tick_intervals_seconds
                else "none"
            )
        )
        print(f"      tick-marked damage events: {len(cast.periodic_events)}")
        print(
            f"      isolated from recast: {'yes' if cast.isolated_from_recast else 'no'}"
        )
        if cast.next_cast_timestamp_ms is not None:
            print(f"      next cast: {cast.next_cast_timestamp_ms:g}ms")
            print(
                "      damage events on recast boundary: "
                f"{cast.exact_recast_boundary_event_count}"
            )
        if cast.periodic_events:
            amounts = tuple(
                event.amount for event in cast.periodic_events if event.amount is not None
            )
            if amounts:
                print(
                    "      observed damage amounts: "
                    + ", ".join(f"{value:g}" for value in amounts[:20])
                    + (" ..." if len(amounts) > 20 else "")
                )
        for message in cast.unresolved:
            print(f"      unresolved: {message}")

    if result.unresolved:
        print()
        print("Report-level unresolved evidence:")
        for message in result.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — ESO Logs timing may nominate reviewed runtime "
        "semantics, but this tool never promotes executable first-tick, refresh, or "
        "magnitude-policy claims automatically."
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect imported ESO Logs cast/tick events as observational evidence for "
            "one canonical DD periodic skill identity."
        )
    )
    parser.add_argument("--skill", required=True, help="Canonical skill name or lower_snake identity")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE),
        help="Canonical ESO SQLite database containing imported log_event rows",
    )
    parser.add_argument("--report", dest="report_code", help="Optional ESO Logs report code filter")
    parser.add_argument("--fight", dest="fight_id", type=int, help="Optional fight id filter")
    parser.add_argument("--source", dest="source_id", type=int, help="Optional source actor id filter")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return audit_skill(
        database_path=args.database,
        skill=args.skill,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
