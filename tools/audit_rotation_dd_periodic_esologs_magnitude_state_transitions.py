from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionService,
)


def audit(
    *,
    skill: str,
    database: Path,
    logs_db: Path,
    periodic_id: int,
    max_transitions: int,
) -> int:
    if not database.is_file():
        print(f"Canonical ESO database not found: {database}")
        return 1
    if not logs_db.is_file():
        print(f"ESO Logs database not found or is not a file: {logs_db}")
        return 2

    report = RotationDDPeriodicEsoLogsMagnitudeStateTransitionService(
        canonical_database_path=database,
        logs_database_path=logs_db,
    ).inspect(skill, periodic_ability_id=periodic_id)

    print()
    print("====================================================")
    print(" DD PERIODIC ESO LOGS MAGNITUDE STATE TRANSITIONS")
    print("====================================================")
    print(f"Skill: {report.skill_entity_id or skill}")
    print(f"Periodic evidence ID: {report.periodic_ability_id}")
    print(f"Amount-change transitions: {len(report.transitions)}")
    print(f"With observed source/target state changes: {report.transitions_with_state_change}")
    print(f"Without observed source/target state changes: {report.transitions_without_state_change}")

    ranked = sorted(
        report.transitions,
        key=lambda item: (not item.has_observed_state_change, item.report_code, item.fight_id, item.cast_track_id, item.to_timestamp_ms),
    )
    for index, item in enumerate(ranked[: max(0, int(max_transitions))], start=1):
        delta_ms = item.to_timestamp_ms - item.from_timestamp_ms
        print()
        print(
            f"  [{index}] report={item.report_code} fight={item.fight_id} "
            f"source={item.source_id} target={item.target_id} track={item.cast_track_id} "
            f"hit_type={item.hit_type}"
        )
        print(
            f"      amount: {item.from_amount:g} -> {item.to_amount:g} "
            f"over {delta_ms / 1000.0:.3f}s"
        )
        if not item.state_events:
            print("      observed state events between ticks: none")
            continue
        print("      observed state events between ticks:")
        for event in item.state_events:
            label = event.ability_name or (
                f"ability_id_{event.ability_game_id}"
                if event.ability_game_id is not None
                else "unidentified_ability"
            )
            print(
                f"        - {event.event_type} {label} "
                f"(id={event.ability_game_id}, source={event.source_id}, "
                f"target={event.target_id}, event_index={event.event_index})"
            )

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for item in report.unresolved:
            print(f"  - {item}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — an amount change following an observed buff/debuff "
        "transition can strengthen dynamic-at-tick evidence, but this tool never promotes "
        "magnitude policy automatically. Numeric IDs remain evidence handles only."
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Correlate same-cast DD periodic amount changes with observed source/target "
            "buff and debuff transitions."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--periodic-id", type=int, required=True)
    parser.add_argument("--max-transitions", type=int, default=20)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return audit(
        skill=args.skill,
        database=args.database,
        logs_db=args.logs_db,
        periodic_id=args.periodic_id,
        max_transitions=args.max_transitions,
    )


if __name__ == "__main__":
    raise SystemExit(main())
