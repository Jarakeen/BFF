from __future__ import annotations

"""Audit reviewed report-scoped Xalvakka Tank lane assignment evidence."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_tank_observed_lane_assignment_service import (
    RotationTankObservedLaneAssignmentService,
)


def audit() -> tuple[str, ...]:
    assignment = RotationTankObservedLaneAssignmentService().reviewed_for(
        encounter_id="xalvakka",
        report_code="XVMgLdq6GpQ7bhKN",
    )
    if assignment is None:
        return ("STATUS=MISSING_REVIEWED_ASSIGNMENT",)

    lines = [
        "PHASE 13 XALVAKKA OBSERVED TANK LANE ASSIGNMENT AUDIT",
        f"EVIDENCE_SCOPE={assignment.evidence_scope}",
        f"REPORT={assignment.report_code}",
        "FIGHTS=" + ",".join(str(value) for value in assignment.fights),
        f"TAUNT_STATE_EFFECT_ID={assignment.taunt_state_effect_id}",
    ]
    for lane in assignment.lanes:
        lines.append(
            "LANE: "
            f"lane_id={lane.lane_id} source_id={lane.source_id} "
            f"character={lane.character_name} account={lane.account_name} "
            f"role={lane.eso_logs_role} role_fights={lane.role_fights} "
            f"boss_taunt_events={lane.boss_taunt_events} boss_fights={lane.boss_fights} "
            f"add_taunt_events={lane.add_taunt_events} add_instances={lane.add_instances}"
        )
    lines.extend(
        (
            "STATUS=REVIEWED_REPORT_SCOPED_LANE_ASSIGNMENT",
            "GENERIC_MT_OT_PROMOTION=BLOCKED",
            "INTERPRETATION=Dualtalons matches boss_holder and Fulcinator matches add_handler in the reviewed report; character/account/class/source identity is not promoted to universal Main Tank or Off Tank truth",
        )
    )
    return tuple(lines)


def main() -> int:
    for line in audit():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
