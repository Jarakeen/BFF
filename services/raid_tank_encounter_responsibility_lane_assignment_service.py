from __future__ import annotations

"""Validate explicit player assignment to reviewed Tank responsibility lanes.

The reviewed lane plan owns encounter strategy shape. The caller owns the explicit
lane-to-member prescription and canonical capability evidence. This service never
chooses between equally viable Tanks and never derives Main/Off Tank from roster order,
character name, or generic role labels.
"""

from dataclasses import dataclass

from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibilityLane,
    RaidTankEncounterResponsibilityPlan,
)


@dataclass(frozen=True)
class RaidTankEncounterLaneAssignment:
    lane_id: str
    member_id: str

    def __post_init__(self) -> None:
        lane_id = str(self.lane_id or "").strip()
        member_id = str(self.member_id or "").strip()
        if not lane_id:
            raise ValueError("Tank encounter lane assignment lane_id must be non-empty")
        if not member_id:
            raise ValueError("Tank encounter lane assignment member_id must be non-empty")
        object.__setattr__(self, "lane_id", lane_id)
        object.__setattr__(self, "member_id", member_id)


@dataclass(frozen=True)
class RaidTankEncounterLaneAssignmentResolution:
    encounter_id: str
    assignments: tuple[RaidTankEncounterLaneAssignment, ...]
    resolved: bool
    unresolved: tuple[str, ...] = ()


class RaidTankEncounterResponsibilityLaneAssignmentService:
    """Validate an explicit lane prescription against reviewed strategy and capabilities."""

    @staticmethod
    def _required_capabilities(
        lane: RaidTankEncounterResponsibilityLane,
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                row.required_capability_type
                for row in lane.responsibilities
                if row.required_capability_type is not None
            )
        )

    def resolve(
        self,
        *,
        plan: RaidTankEncounterResponsibilityPlan,
        lane_member_ids: dict[str, str],
        member_capabilities: dict[str, tuple[str, ...] | list[str] | set[str]],
    ) -> RaidTankEncounterLaneAssignmentResolution:
        normalized_prescription = {
            str(lane_id or "").strip().casefold(): str(member_id or "").strip()
            for lane_id, member_id in lane_member_ids.items()
        }
        if any(not lane_id or not member_id for lane_id, member_id in normalized_prescription.items()):
            raise ValueError("Tank encounter lane prescription requires non-empty lane/member identities")

        known_lane_ids = {lane.lane_id.casefold() for lane in plan.lanes}
        unknown = tuple(
            sorted(lane_id for lane_id in normalized_prescription if lane_id not in known_lane_ids)
        )
        if unknown:
            raise ValueError(
                "Tank encounter lane prescription references unknown lane(s): "
                + ", ".join(unknown)
            )

        capability_by_member = {
            str(member_id or "").strip(): {
                str(capability or "").strip().casefold()
                for capability in capabilities
                if str(capability or "").strip()
            }
            for member_id, capabilities in member_capabilities.items()
            if str(member_id or "").strip()
        }

        assignments: list[RaidTankEncounterLaneAssignment] = []
        unresolved: list[str] = []
        member_by_lane: dict[str, str] = {}
        for lane in plan.lanes:
            member_id = normalized_prescription.get(lane.lane_id.casefold())
            if not member_id:
                unresolved.append(
                    f"{plan.encounter_id}:{lane.lane_id}: explicit Tank lane assignment is missing"
                )
                continue
            member_by_lane[lane.lane_id] = member_id
            capabilities = capability_by_member.get(member_id)
            if capabilities is None:
                unresolved.append(
                    f"{plan.encounter_id}:{lane.lane_id}: canonical capability evidence is unavailable for {member_id!r}"
                )
                continue
            required = self._required_capabilities(lane)
            missing = tuple(
                capability for capability in required if capability.casefold() not in capabilities
            )
            if missing:
                unresolved.append(
                    f"{plan.encounter_id}:{lane.lane_id}: {member_id!r} lacks required canonical capability evidence: {', '.join(missing)}"
                )
                continue
            assignments.append(
                RaidTankEncounterLaneAssignment(lane_id=lane.lane_id, member_id=member_id)
            )

        for lane in plan.lanes:
            member_id = member_by_lane.get(lane.lane_id)
            if not member_id:
                continue
            for other_id in lane.distinct_from:
                other_member = member_by_lane.get(other_id)
                if other_member and other_member == member_id:
                    pair = tuple(sorted((lane.lane_id, other_id)))
                    unresolved.append(
                        f"{plan.encounter_id}: distinct Tank lanes {pair[0]!r} and {pair[1]!r} cannot both be assigned to {member_id!r}"
                    )

        unresolved = list(dict.fromkeys(unresolved))
        if unresolved:
            return RaidTankEncounterLaneAssignmentResolution(
                encounter_id=plan.encounter_id,
                assignments=tuple(assignments),
                resolved=False,
                unresolved=tuple(unresolved),
            )

        return RaidTankEncounterLaneAssignmentResolution(
            encounter_id=plan.encounter_id,
            assignments=tuple(assignments),
            resolved=True,
        )


__all__ = [
    "RaidTankEncounterLaneAssignment",
    "RaidTankEncounterLaneAssignmentResolution",
    "RaidTankEncounterResponsibilityLaneAssignmentService",
]
