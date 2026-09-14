from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterBoundResponsibility,
)
from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibilityLaneService,
)
from services.rotation_tank_encounter_add_activity_trigger_service import (
    RotationTankEncounterAddActivityTriggerService,
)


def audit() -> tuple[str, ...]:
    plan = RaidTankEncounterResponsibilityLaneService().for_encounter("xalvakka")
    if plan is None:
        return ("UNRESOLVED: reviewed Xalvakka Tank responsibility plan is unavailable",)
    lane = plan.lane("add_handler")
    if lane is None:
        return ("UNRESOLVED: reviewed Xalvakka add_handler lane is unavailable",)

    responsibilities = tuple(
        RaidTankEncounterBoundResponsibility(
            encounter_id="xalvakka",
            lane_id=lane.lane_id,
            member_id="reviewed-add-handler",
            responsibility=row,
        )
        for row in lane.responsibilities
    )
    triggers = RotationTankEncounterAddActivityTriggerService().for_responsibilities(
        encounter_id="xalvakka",
        responsibilities=responsibilities,
    )

    lines = [
        "PHASE 13 XALVAKKA TANK ADD ACTIVITY PROJECTION AUDIT",
        f"TRIGGERS={len(triggers)}",
    ]
    for row in triggers:
        capability = row.required_capability_type or "none"
        lines.append(
            f"TRIGGER: lane={row.lane_id} responsibility={row.responsibility_id} "
            f"actor={row.actor_name} boundary={row.activity_boundary} "
            f"action={row.action_type} capability={capability}"
        )

    expected = {
        ("pack_encounter_adds", "Iron Atronach"),
        ("pack_encounter_adds", "Daedroth"),
        ("iron_atronach_opening_position", "Iron Atronach"),
        ("daedroth_facing", "Daedroth"),
    }
    actual = {(row.responsibility_id, row.actor_name) for row in triggers}
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        lines.append(f"UNRESOLVED: trigger projection mismatch missing={missing} extra={extra}")
    else:
        lines.append("STATUS=REVIEWED_ADD_ACTIVITY_TRIGGERS_PROJECTED")
    lines.append(
        "INTERPRETATION=activity triggers are event-bound contextual responsibilities; they are not exact spawn or taunt clocks"
    )
    return tuple(lines)


def main() -> int:
    lines = audit()
    for line in lines:
        print(line)
    return 1 if any(line.startswith("UNRESOLVED:") for line in lines) else 0


if __name__ == "__main__":
    raise SystemExit(main())
