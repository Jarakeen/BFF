from __future__ import annotations

"""Audit reviewed Xalvakka add activity-boundary semantics against runtime evidence."""

import argparse
from pathlib import Path
import sqlite3
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_tank_encounter_add_activity_service import (
    RotationTankEncounterAddActivityService,
)
from tools.audit_phase13_xalvakka_add_earliest_event_signal import observe

_DEFAULT_DATABASE = ROOT / "research" / "xalvakka_esologs_runtime.db"


def audit(database: Path) -> tuple[str, ...]:
    plan = RotationTankEncounterAddActivityService().reviewed_for("xalvakka")
    if plan is None:
        return ("UNRESOLVED: no reviewed Xalvakka add activity plan",)

    observations = observe(database)
    lines = [
        "PHASE 13 XALVAKKA ADD ACTIVITY BOUNDARY AUDIT",
        f"DATABASE: {database}",
        f"OBSERVATIONS: {len(observations)}",
    ]
    for actor in plan.actors:
        rows = tuple(row for row in observations if row.actor_name.casefold() == actor.actor_name.casefold())
        leads = tuple(
            (row.first_friendly_damage_ms - row.first_source_ms) / 1000.0
            for row in rows
            if row.first_source_ms is not None and row.first_friendly_damage_ms is not None
        )
        lines.append(
            f"ACTOR: {actor.actor_name} instances={len(rows)} boundary={actor.activity_boundary} "
            f"fully_observed_source_boundary={actor.fully_observed_source_boundary}"
        )
        if leads:
            lines.append(
                f"SOURCE_TO_FIRST_DAMAGE: samples={len(leads)} median={statistics.median(leads):.3f}s "
                f"min={min(leads):.3f}s max={max(leads):.3f}s"
            )
        else:
            lines.append("SOURCE_TO_FIRST_DAMAGE: unavailable")

    lines.append(
        "INTERPRETATION=reviewed boundary is observed add activity entry; lead variance prevents promotion to exact spawn or exact taunt-required timing"
    )
    return tuple(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DATABASE)
    args = parser.parse_args()
    if not args.db.exists():
        print(f"AUDIT ERROR: database does not exist: {args.db}")
        return 2
    try:
        lines = audit(args.db)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
