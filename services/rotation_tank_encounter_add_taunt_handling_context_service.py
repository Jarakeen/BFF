from __future__ import annotations

"""Project reviewed actor-specific add-taunt handling onto exact Tank responsibilities.

This is contextual strategy evidence only. It never creates hard maintenance obligations
or exact timing/uptime floors from single-report behavior.
"""

from dataclasses import dataclass

from services.raid_tank_encounter_responsibility_binding_service import RaidTankEncounterBoundResponsibility
from services.rotation_tank_encounter_add_taunt_handling_service import (
    ReviewedAddTauntHandlingActor,
    RotationTankEncounterAddTauntHandlingService,
)


def _key(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class RotationTankAddTauntHandlingContext:
    encounter_id: str
    lane_id: str
    member_id: str
    responsibility_id: str
    actor_name: str
    handling_class: str
    ranking_context: bool
    interpretation: str


class RotationTankEncounterAddTauntHandlingContextService:
    def __init__(self, handling_service: RotationTankEncounterAddTauntHandlingService | object | None = None) -> None:
        self.handling_service = handling_service or RotationTankEncounterAddTauntHandlingService()

    def for_responsibilities(
        self,
        *,
        encounter_id: str,
        responsibilities: tuple[RaidTankEncounterBoundResponsibility, ...],
    ) -> tuple[RotationTankAddTauntHandlingContext, ...]:
        encounter_id = str(encounter_id or "").strip()
        if not encounter_id:
            raise ValueError("add-taunt handling context requires encounter_id")
        plan = self.handling_service.reviewed_for(encounter_id)
        if plan is None:
            return ()

        actor_by_key = {_key(actor.actor_name): actor for actor in plan.actors}
        result: list[RotationTankAddTauntHandlingContext] = []
        for bound in tuple(responsibilities):
            if bound.encounter_id.casefold() != encounter_id.casefold():
                raise ValueError("add-taunt handling responsibility encounter mismatch")
            target = _key(bound.responsibility.target_key)
            actors: tuple[ReviewedAddTauntHandlingActor, ...]
            if target == "encounter_adds":
                actors = tuple(plan.actors)
            else:
                actor = actor_by_key.get(target)
                actors = () if actor is None else (actor,)
            for actor in actors:
                if not actor.ranking_context:
                    continue
                result.append(
                    RotationTankAddTauntHandlingContext(
                        encounter_id=encounter_id,
                        lane_id=bound.lane_id,
                        member_id=bound.member_id,
                        responsibility_id=bound.responsibility.responsibility_id,
                        actor_name=actor.actor_name,
                        handling_class=actor.handling_class,
                        ranking_context=True,
                        interpretation=actor.interpretation,
                    )
                )
        return tuple(result)


__all__ = [
    "RotationTankAddTauntHandlingContext",
    "RotationTankEncounterAddTauntHandlingContextService",
]
