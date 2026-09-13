from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.rotation_dd_periodic_esologs_single_component_refresh_service import (
    RotationDDPeriodicEsoLogsSingleComponentRefreshService,
)


def _common(values: tuple[float, ...], *, limit: int = 8) -> str:
    if not values:
        return "none"
    counts = Counter(round(value, 3) for value in values)
    return ", ".join(
        f"{value:g}s" + (f" x{count}" if count > 1 else "")
        for value, count in counts.most_common(limit)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect old cast-track periodic events around the first periodic event of the "
            "next cast when no separate impact/trigger component is logged."
        )
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--periodic-id", required=True, type=int)
    parser.add_argument("--active-window", required=True, type=float)
    parser.add_argument("--tolerance-ms", type=float, default=50.0)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--logs-db", required=True, type=Path)
    parser.add_argument("--report", dest="report_code")
    parser.add_argument("--fight", dest="fight_id", type=int)
    parser.add_argument("--source", dest="source_id", type=int)
    args = parser.parse_args(argv)

    report = RotationDDPeriodicEsoLogsSingleComponentRefreshService(
        canonical_database_path=args.database,
        logs_database_path=args.logs_db,
    ).inspect(
        args.skill,
        periodic_ability_id=args.periodic_id,
        active_window_seconds=args.active_window,
        boundary_tolerance_ms=args.tolerance_ms,
        report_code=args.report_code,
        fight_id=args.fight_id,
        source_id=args.source_id,
    )

    print()
    print("========================================================")
    print(" DD PERIODIC ESO LOGS SINGLE-COMPONENT REFRESH EVIDENCE")
    print("========================================================")
    print(f"Skill: {report.skill_entity_id or args.skill}")
    print(f"Periodic evidence ID: {report.periodic_ability_id}")
    print(f"Boundary tolerance: ±{report.boundary_tolerance_ms:g}ms")
    print(f"Consecutive periodic-stream pairs observed: {len(report.observations)}")
    print(f"Old periodic events at new-stream boundary: {report.old_tick_at_boundary_count}")
    print(f"Old periodic events after new-stream boundary: {report.old_tick_after_boundary_count}")
    print(
        "Exact-timestamp old ticks before new-stream event: "
        f"{report.exact_boundary_old_tick_before_new_count}"
    )
    print(
        "Exact-timestamp old ticks after new-stream event:  "
        f"{report.exact_boundary_old_tick_after_new_count}"
    )
    median_last = report.median_last_old_periodic_offset_seconds
    print(
        "Median last old periodic event relative to new-stream boundary: "
        + ("unresolved" if median_last is None else f"{median_last:+.3f}s")
    )
    offsets = tuple(
        item.last_old_periodic_offset_seconds
        for item in report.observations
        if item.last_old_periodic_offset_seconds is not None
    )
    print(f"Common last-old offsets: {_common(offsets)}")

    exact = tuple(item for item in report.observations if item.exact_boundary_old_tick_event_indices)
    if exact:
        print("Exact-timestamp event ordering:")
        for item in exact[:12]:
            print(
                "  - "
                f"report={item.report_code} fight={item.fight_id} source={item.source_id} "
                f"old_track={item.old_cast_track_id} new_track={item.new_cast_track_id} "
                f"new_event_index={item.new_boundary_event_index} "
                f"old_tick_event_indices={','.join(str(v) for v in item.exact_boundary_old_tick_event_indices)}"
            )

    if report.unresolved:
        print("Unresolved evidence:")
        for item in report.unresolved:
            print(f"  - {item}")

    print()
    print(
        "Result: OBSERVATIONAL ONLY — the first periodic event on the new cast track is "
        "used only as an observed replacement boundary. It is not promoted as a canonical "
        "activation anchor or executable refresh policy automatically."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
