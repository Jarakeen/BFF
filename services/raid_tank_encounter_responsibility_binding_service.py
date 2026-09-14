from __future__ import annotations

"""Bind reviewed encounter Tank lanes to an explicit team prescription.

The lane registry owns which prescription slot names correspond to reviewed encounter
responsibility lanes. The caller supplies exact slot-to-member identities and canonical
capability evidence. This service does not infer Main/Off Tank from roster order, role
labels, build names, or character names.
"""

from dataclasses import dataclass

from services.raid_tank_encounter_responsibility_lane_assignment_service import (
    RaidTankEncounterLaneAssignment,
    RaidTankEncounterResponsibilityLaneAssignmentService,
)
from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibility,
    RaidTankEncounterResponsibilityLaneService,
)


@dataclass(frozen=True)
class RaidTankEncounterBoundResponsibility:
    encounter_id: str
    lane_id: str
    member_id: str
    responsibility: RaidTankEncounterResponsibility


@dataclass(frozen=True)
class RaidTankEncounterResponsibilityBinding:
    encounter_id: str
    assignments: tuple[RaidTankEncounterLaneAssignment, ...]
    responsibilities: tuple[RaidTankEncounterBoundResponsibility, ...]
    resolved: bool
    unresolved: tuple[str, ...] = ()

    def for_member(self, member_id: str) -> tuple[RaidTankEncounterBoundResponsibility, ...]:
        key = str(member_id or "").strip().casefold()
        if not key:
            raise ValueError("Tank responsibility binding member lookup requires member_id")
        return tuple(
            row for row in self.responsibilities if row.member_id.casefold() == key
        )


class RaidTankEncounterResponsibilityBindingService:
    """Resolve reviewed lane/slot mapping into exact member responsibilities."""

    def __init__(
        self,
        *,
        lane_service: RaidTankEncounterResponsibilityLaneService | object | None = None,
        assignment_service: (
            RaidTankEncounterResponsibilityLaneAssignmentService | object | None
        ) = None,
    ) -> None:
        self.lane_service = lane_service or RaidTankEncounterResponsibilityLaneService()
        self.assignment_service = (
            assignment_service or RaidTankEncounterResponsibilityLaneAssignmentService()
        )

    def bind(
        self,
        *,
        encounter_id: str,
        prescription_slot_members: dict[str, str],
        member_capabilities: dict[str, tuple[str, ...] | list[str] | set[str]],
    ) -> RaidTankEncounterResponsibilityBinding:
        resolved_encounter = str(encounter_id or "").strip()
        if not resolved_encounter:
            raise ValueError("Tank responsibility binding requires encounter_id")
        plan = self.lane_service.for_encounter(resolved_encounter)
        if plan is None:
            return RaidTankEncounterResponsibilityBinding(
                encounter_id=resolved_encounter,
                assignments=(),
                responsibilities=(),
                resolved=True,
            )

        slot_members = {
            str(slot or "").strip(): str(member or "").strip()
            for slot, member in prescription_slot_members.items()
            if str(slot or "").strip()
        }
        lane_members: dict[str, str] = {}
        unresolved: list[str] = []
        for lane in plan.lanes:
            if not lane.prescription_slot_names:
                unresolved.append(
                    f"{resolved_encounter}:{lane.lane_id}: reviewed Tank lane has no prescription slot mapping"
                )
                continue
            matches = tuple(
                (slot_name, member_id)
                for slot_name, member_id in slot_members.items()
                if any(
                    reviewed.casefold() == slot_name.casefold()
                    for reviewed in lane.prescription_slot_names
                )
            )
            if len(matches) != 1:
                expected = ", ".join(lane.prescription_slot_names)
                unresolved.append(
                    f"{resolved_encounter}:{lane.lane_id}: expected exactly one authoritative prescription slot from [{expected}], found {len(matches)}"
                )
                continue
            slot_name, member_id = matches[0]
            if not member_id:
                unresolved.append(
                    f"{resolved_encounter}:{lane.lane_id}: prescription slot {slot_name!r} has no exact member"
                )
                continue
            lane_members[lane.lane_id] = member_id

        if unresolved:
            return RaidTankEncounterResponsibilityBinding(
                encounter_id=resolved_encounter,
                assignments=(),
                responsibilities=(),
                resolved=False,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        resolution = self.assignment_service.resolve(
            plan=plan,
            lane_member_ids=lane_members,
            member_capabilities=member_capabilities,
        )
        if not resolution.resolved:
            return RaidTankEncounterResponsibilityBinding(
                encounter_id=resolved_encounter,
                assignments=tuple(resolution.assignments),
                responsibilities=(),
                resolved=False,
                unresolved=tuple(resolution.unresolved),
            )

        responsibilities: list[RaidTankEncounterBoundResponsibility] = []
        for assignment in resolution.assignments:
            lane = plan.lane(assignment.lane_id)
            if lane is None:
                raise ValueError(
                    f"resolved Tank lane assignment references unknown lane {assignment.lane_id!r}"
                )
            responsibilities.extend(
                RaidTankEncounterBoundResponsibility(
                    encounter_id=resolved_encounter,
                    lane_id=lane.lane_id,
                    member_id=assignment.member_id,
                    responsibility=responsibility,
                )
                for responsibility in lane.responsibilities
            )

        return RaidTankEncounterResponsibilityBinding(
            encounter_id=resolved_encounter,
            assignments=tuple(resolution.assignments),
            responsibilities=tuple(responsibilities),
            resolved=True,
        )


__all__ = [
    "RaidTankEncounterBoundResponsibility",
    "RaidTankEncounterResponsibilityBinding",
    "RaidTankEncounterResponsibilityBindingService",
]
