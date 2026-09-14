from __future__ import annotations

"""Project reviewed add-activity boundaries onto bound Tank responsibilities.

These triggers are contextual planning evidence. They tell Rotation Generate that a
reviewed Tank responsibility becomes relevant when an observed NPC activity signal is
present. They do not claim exact spawn time, exact taunt-required time, or a fixed
wall-clock schedule.
"""

from dataclasses import dataclass

from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterBoundResponsibility,
)
from services.rotation_tank_encounter_add_activity_service import (
    RotationTankEncounterAddActivityService,
)


def _identity(value: object) -> str:
    return "_".join(
        str(value or "").strip().casefold().replace("-", " ").replace("_", " ").split()
    )


@dataclass(frozen=True)
class RotationTankEncounterAddActivityTrigger:
    encounter_id: str
    lane_id: str
    member_id: str
    responsibility_id: str
    action_type: str
    actor_name: str
    activity_boundary: str
    required_capability_type: str | None = None
    source: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "encounter_id",
            "lane_id",
            "member_id",
            "responsibility_id",
            "action_type",
            "actor_name",
            "activity_boundary",
            "source",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"Tank add activity trigger {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        if self.required_capability_type is not None:
            value = str(self.required_capability_type or "").strip().casefold()
            if not value:
                raise ValueError(
                    "Tank add activity trigger required_capability_type must be non-empty when supplied"
                )
            object.__setattr__(self, "required_capability_type", value)


class RotationTankEncounterAddActivityTriggerService:
    """Join reviewed add activity semantics to already-bound Tank responsibilities."""

    def __init__(
        self,
        activity_service: RotationTankEncounterAddActivityService | object | None = None,
    ) -> None:
        self.activity_service = activity_service or RotationTankEncounterAddActivityService()

    def for_responsibilities(
        self,
        *,
        encounter_id: str,
        responsibilities: tuple[RaidTankEncounterBoundResponsibility, ...],
    ) -> tuple[RotationTankEncounterAddActivityTrigger, ...]:
        resolved_encounter = str(encounter_id or "").strip()
        if not resolved_encounter:
            raise ValueError("Tank add activity trigger projection requires encounter_id")
        rows = tuple(responsibilities)
        if not rows:
            return ()

        plan = self.activity_service.reviewed_for(resolved_encounter)
        if plan is None:
            return ()

        triggers: list[RotationTankEncounterAddActivityTrigger] = []
        seen: set[tuple[str, str, str]] = set()
        for bound in rows:
            if bound.encounter_id.casefold() != resolved_encounter.casefold():
                raise ValueError(
                    "Tank add activity responsibility encounter does not match trigger projection"
                )
            responsibility = bound.responsibility
            target_key = _identity(responsibility.target_key)
            if target_key == "encounter_adds":
                actors = plan.actors
            else:
                actors = tuple(
                    actor
                    for actor in plan.actors
                    if _identity(actor.actor_name) == target_key
                )
            for actor in actors:
                if not actor.fully_observed_source_boundary:
                    continue
                key = (
                    bound.member_id.casefold(),
                    responsibility.responsibility_id.casefold(),
                    actor.actor_name.casefold(),
                )
                if key in seen:
                    continue
                seen.add(key)
                triggers.append(
                    RotationTankEncounterAddActivityTrigger(
                        encounter_id=resolved_encounter,
                        lane_id=bound.lane_id,
                        member_id=bound.member_id,
                        responsibility_id=responsibility.responsibility_id,
                        action_type=responsibility.action_type,
                        actor_name=actor.actor_name,
                        activity_boundary=actor.activity_boundary,
                        required_capability_type=responsibility.required_capability_type,
                        source=(
                            f"{responsibility.source} Observed activity boundary: "
                            f"{actor.interpretation}"
                        ),
                    )
                )
        return tuple(triggers)


__all__ = [
    "RotationTankEncounterAddActivityTrigger",
    "RotationTankEncounterAddActivityTriggerService",
]
