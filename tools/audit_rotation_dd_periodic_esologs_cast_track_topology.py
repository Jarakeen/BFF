from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_cast_track_topology_service import (
    RotationDDPeriodicEsoLogsCastTrackTopologyService,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List exact same-cast-track ESO Logs components after a canonical DD skill cast."
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--active-window", required=True, type=float)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", required=True, type=Path)
    parser.add_argument("--report", dest="report_code")
    parser.add_argument("--fight", dest="fight_id", type=int)
    parser.add_argument("--source", dest="source_id", type=int)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsCastTrackTopologyService(
        canonical_database_path=args.database,
        logs_database_path=args.logs_db,
    ).inspect(
        args.skill,
        active_window_seconds=args.active_window,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
    )

    print("\n================================================")
    print(" DD PERIODIC ESO LOGS CAST TRACK TOPOLOGY")
    print("================================================")
    print(f"Skill: {report.skill_entity_id or '(unresolved)'}")
    print(f"Cast anchors: {report.cast_count}")
    print(f"Observed window: {report.active_window_seconds:g}s")
    print(f"Same-track component groups: {len(report.components)}")

    for index, component in enumerate(report.components, start=1):
        ability = str(component.ability_game_id) if component.ability_game_id is not None else "none"
        name = component.ability_name or "(name unavailable)"
        median_first = (
            f"{component.median_first_offset_seconds:g}s"
            if component.median_first_offset_seconds is not None
            else "unresolved"
        )
        print(f"\n  [{index}] ability_id={ability}  event={component.event_type}")
        print(f"      name: {name}")
        print(f"      cast tracks observed: {component.cast_track_count}")
        print(f"      events: {component.event_count}")
        print(f"      median first offset: {median_first}")

    if report.unresolved:
        print("\nUnresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print(
        "\nResult: OBSERVATIONAL ONLY — same-track event order can reveal activation topology, "
        "but it never promotes numeric IDs or executable runtime semantics automatically."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
