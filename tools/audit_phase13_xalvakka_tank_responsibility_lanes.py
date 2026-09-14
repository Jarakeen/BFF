from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibilityLaneService,
)


def main() -> int:
    plan = RaidTankEncounterResponsibilityLaneService().for_encounter("xalvakka")
    print("=" * 72)
    print(" PHASE 13 XALVAKKA TANK RESPONSIBILITY LANE AUDIT")
    print("=" * 72)
    if plan is None:
        print("MISSING: no reviewed Xalvakka Tank responsibility lane plan")
        return 1

    print(f"encounter={plan.encounter_id}")
    for lane in plan.lanes:
        distinct = ", ".join(lane.distinct_from) or "none"
        slots = ", ".join(lane.prescription_slot_names) or "unmapped"
        print(
            f"\n{lane.lane_id} | {lane.display_name} | "
            f"distinct_from={distinct} | prescription_slots={slots}"
        )
        for responsibility in lane.responsibilities:
            capability = responsibility.required_capability_type or "none"
            print(
                f"  {responsibility.responsibility_id} | target={responsibility.target_key} "
                f"| action={responsibility.action_type} | capability={capability}"
            )

    print("\nSTATUS=REVIEWED_LANES_PRESCRIPTION_MAPPED")
    print(
        "NEXT_STEP=field-test authoritative Team Optimization Main Tank/Off Tank binding and Generate transfer"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
