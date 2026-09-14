from __future__ import annotations

"""Compose reviewed Tank responsibilities into rotation-facing priority context.

This service orders already-reviewed, already-bound encounter responsibilities for a
specific Tank member. It is strategy/context metadata only: priority rows do not create
new hard obligations, timing windows, uptime floors, or cross-lane taunt permissions.

Actor-specific add handling comes from the reviewed add-taunt handling context. This
lets Generate distinguish sustained Iron Atronach ownership from selective/contextual
Daedroth handling without turning single-report behavior into mechanic truth.
"""

from dataclasses import dataclass

from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterBoundResponsibility,
)
from services.rotation_tank_encounter_add_taunt_handling_context_service import (
    RotationTankAddTauntHandlingContext,
    RotationTankEncounterAddTauntHandlingContextService,
)


def _key(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class RotationTankEncounterPriorityCue:
    encounter_id: str
    lane_id: str
    member_id: str
    priority: int
    responsibility_id: str
    target_key: str
    actor_name: str | None
    directive: str
    trigger: str
    hard_policy: bool
    interpretation: str

    def __post_init__(self) -> None:
        for field_name in (
            "encounter_id",
            "lane_id",
            "member_id",
            "responsibility_id",
            "target_key",
            "directive",
            "trigger",
            "interpretation",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"Tank encounter priority cue {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        if self.actor_name is not None:
            actor_name = str(self.actor_name or "").strip()
            if not actor_name:
                raise ValueError("Tank encounter priority cue actor_name must be non-empty when supplied")
            object.__setattr__(self, "actor_name", actor_name)
        if int(self.priority) < 0:
            raise ValueError("Tank encounter priority cue priority must be non-negative")
        if self.hard_policy:
            raise ValueError("Tank encounter priority context cannot create hard policy")


class RotationTankEncounterPriorityContextService:
    """Build soft, rotation-facing priorities from reviewed Tank responsibility context."""

    def __init__(
        self,
        *,
        add_taunt_handling_context_service: (
            RotationTankEncounterAddTauntHandlingContextService | object | None
        ) = None,
    ) -> None:
        self.add_taunt_handling_context_service = (
            add_taunt_handling_context_service
            or RotationTankEncounterAddTauntHandlingContextService()
        )

    def for_responsibilities(
        self,
        *,
        encounter_id: str,
        responsibilities: tuple[RaidTankEncounterBoundResponsibility, ...],
    ) -> tuple[RotationTankEncounterPriorityCue, ...]:
        encounter_id = str(encounter_id or "").strip()
        if not encounter_id:
            raise ValueError("Tank encounter priority context requires encounter_id")
        responsibilities = tuple(responsibilities)
        if any(row.encounter_id.casefold() != encounter_id.casefold() for row in responsibilities):
            raise ValueError("Tank encounter priority responsibility encounter mismatch")

        handling = self.add_taunt_handling_context_service.for_responsibilities(
            encounter_id=encounter_id,
            responsibilities=responsibilities,
        )
        handling_by_responsibility: dict[str, list[RotationTankAddTauntHandlingContext]] = {}
        for row in handling:
            handling_by_responsibility.setdefault(row.responsibility_id, []).append(row)

        cues: list[RotationTankEncounterPriorityCue] = []
        for bound in responsibilities:
            responsibility = bound.responsibility
            responsibility_id = responsibility.responsibility_id
            target_key = responsibility.target_key
            action = _key(responsibility.action_type)
            lane = _key(bound.lane_id)

            if lane == "boss_holder" and action == "maintain_taunt":
                cues.append(
                    self._cue(
                        bound=bound,
                        priority=10,
                        actor_name=None,
                        directive="maintain_primary_boss_ownership",
                        trigger="while_primary_boss_is_targetable",
                        interpretation=(
                            "Protect the reviewed boss-holder responsibility before optional "
                            "cross-lane add work; this ordering does not invent a refresh clock."
                        ),
                    )
                )
                continue

            actor_context = tuple(handling_by_responsibility.get(responsibility_id, ()))
            if actor_context:
                for actor in actor_context:
                    handling_class = _key(actor.handling_class)
                    if handling_class == "strong_taunt_maintenance_target":
                        priority = 20
                        directive = "acquire_and_maintain_owned_add_when_active"
                        trigger = "reviewed_add_activity"
                    elif handling_class == "selective_contextual_taunt_target":
                        priority = 40
                        directive = "contextual_add_pickup_when_required"
                        trigger = "reviewed_add_activity_and_encounter_context"
                    else:
                        continue
                    cues.append(
                        self._cue(
                            bound=bound,
                            priority=priority,
                            actor_name=actor.actor_name,
                            directive=directive,
                            trigger=trigger,
                            interpretation=actor.interpretation,
                        )
                    )
                continue

            if _key(responsibility_id) == "iron_atronach_opening_position":
                cues.append(
                    self._cue(
                        bound=bound,
                        priority=30,
                        actor_name="Iron Atronach",
                        directive="place_away_then_stack",
                        trigger="after_iron_atronach_acquisition",
                        interpretation=(
                            "Apply the reviewed Iron Atronach opening-position responsibility "
                            "after acquisition; positioning is contextual rather than a timed cast."
                        ),
                    )
                )
                continue

            if _key(responsibility_id) == "daedroth_facing":
                cues.append(
                    self._cue(
                        bound=bound,
                        priority=50,
                        actor_name="Daedroth",
                        directive="face_away_from_group_when_owned",
                        trigger="while_daedroth_is_owned",
                        interpretation=(
                            "Apply the reviewed Daedroth facing responsibility only while that "
                            "target is actually being handled."
                        ),
                    )
                )

        return tuple(
            sorted(
                cues,
                key=lambda row: (
                    row.priority,
                    row.lane_id.casefold(),
                    row.responsibility_id.casefold(),
                    (row.actor_name or "").casefold(),
                ),
            )
        )

    @staticmethod
    def _cue(
        *,
        bound: RaidTankEncounterBoundResponsibility,
        priority: int,
        actor_name: str | None,
        directive: str,
        trigger: str,
        interpretation: str,
    ) -> RotationTankEncounterPriorityCue:
        return RotationTankEncounterPriorityCue(
            encounter_id=bound.encounter_id,
            lane_id=bound.lane_id,
            member_id=bound.member_id,
            priority=priority,
            responsibility_id=bound.responsibility.responsibility_id,
            target_key=bound.responsibility.target_key,
            actor_name=actor_name,
            directive=directive,
            trigger=trigger,
            hard_policy=False,
            interpretation=interpretation,
        )


__all__ = [
    "RotationTankEncounterPriorityCue",
    "RotationTankEncounterPriorityContextService",
]
