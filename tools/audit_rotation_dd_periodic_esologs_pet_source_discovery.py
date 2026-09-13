from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_pet_source_discovery_service import (
    RotationDDPeriodicEsoLogsPetSourceDiscoveryService,
)


def _common(values: tuple[float, ...], *, limit: int = 10) -> str:
    if not values:
        return "none"
    counts = Counter(round(float(value), 3) for value in values)
    return ", ".join(
        f"{value:g}s" + (f" x{count}" if count > 1 else "")
        for value, count in counts.most_common(limit)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Discover friendly non-player periodic damage candidates during a reviewed "
            "pet skill window without inferring pet ownership."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", required=True, type=Path)
    parser.add_argument("--report", dest="report_code")
    parser.add_argument("--fight", dest="fight_id", type=int)
    parser.add_argument("--source", dest="source_id", type=int)
    parser.add_argument("--max-candidates", type=int, default=15)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsPetSourceDiscoveryService(
        canonical_database_path=args.database,
        logs_database_path=args.logs_db,
    ).inspect_skill(
        args.skill,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
        max_candidates=args.max_candidates,
    )

    print()
    print("====================================================")
    print(" DD PERIODIC ESO LOGS PET-SOURCE DISCOVERY")
    print("====================================================")
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
    print(f"Candidates: {len(report.candidates)}")

    for index, candidate in enumerate(report.candidates, start=1):
        print()
        print(f"  [{index}] ability_id_{candidate.ability_game_id}")
        if candidate.ability_names:
            print("      ESO Logs names: " + " | ".join(candidate.ability_names))
        print(f"      cast windows observed: {candidate.cast_windows_observed}")
        print(f"      events: {candidate.event_count}")
        print(f"      distinct friendly non-player source actors: {candidate.source_actor_count}")
        print(f"      tick-marked events: {candidate.tick_marked_event_count}")
        print(f"      reviewed cadence matches: {candidate.reviewed_interval_match_count}")
        print(
            "      median first offset: "
            + (
                f"{candidate.median_first_offset_seconds:g}s"
                if candidate.median_first_offset_seconds is not None
                else "unresolved"
            )
        )
        print("      common first offsets: " + _common(candidate.first_offset_samples_seconds))
        print("      common same-source intervals: " + _common(candidate.interval_samples_seconds))

    if report.unresolved:
        print()
        print("Unresolved evidence:")
        for message in report.unresolved:
            print(f"  - {message}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — this path is pet-aware but not owner-aware. "
        "Friendly non-player source candidates are ranked inside reviewed summon windows; "
        "nothing is promoted into executable runtime semantics automatically."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
