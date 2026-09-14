from __future__ import annotations

"""Project reviewed Tank runtime context into Raid Plan triggered responsibilities.

This bridge deliberately stops at planning intent. Reviewed actor-activity evidence can
activate a responsibility, but it cannot manufacture a wall-clock RotationAction. Cues
that require additional encounter context remain unresolved until that context is supplied
by a stronger planning/runtime layer.
"""

from dataclasses import dataclass, replace

from models.raid_plan import RaidPlan, RaidPlanTriggeredResponsibility
from services.rotation_tank_encounter_add_activity_trigger_service import (
    RotationTankEncounterAddActivityTrigger,
)
from services.rotation_tank_encounter_priority_context_service import (
    RotationTankEncounterPriorityCue,
)


def _key(value: object) -> str:
    return "_".join(
        str(value or "").strip().casefold().replace("-", " ").replace("_", " ").split()
    )


@dataclass(frozen=True)
class RaidPlanTankTriggeredResponsibilityProjection:
    responsibilities: tuple[RaidPlanTriggeredResponsibility, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


@dataclass(frozen=True)
class RaidPlanTankTriggeredResponsibilityApplication:
    """One immutable Raid Plan update plus any fail-closed projection conflicts."""

    plan: RaidPlan
    applied: tuple[RaidPlanTriggeredResponsibility, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class RaidPlanTankTriggeredResponsibilityService:
    """Convert sufficiently reviewed Tank add context into seat-owned plan intent."""

    def project(
        self,
        *,
        seat_id: str,
        add_activity_triggers: tuple[RotationTankEncounterAddActivityTrigger, ...],
        priority_context: tuple[RotationTankEncounterPriorityCue, ...],
    ) -> RaidPlanTankTriggeredResponsibilityProjection:
        resolved_seat = str(seat_id or "").strip()
        if not resolved_seat:
            raise ValueError("Tank triggered responsibility projection requires seat_id")

        triggers = tuple(add_activity_triggers)
        cues = tuple(priority_context)
        cue_by_key: dict[tuple[str, str, str, str], RotationTankEncounterPriorityCue] = {}
        for cue in cues:
            if cue.hard_policy:
                raise ValueError(
                    "Tank priority context must remain soft before Raid Plan projection"
                )
            if not cue.actor_name:
                continue
            key = (
                cue.encounter_id.casefold(),
                cue.member_id.casefold(),
                cue.responsibility_id.casefold(),
                cue.actor_name.casefold(),
            )
            if key in cue_by_key:
                raise ValueError(
                    "duplicate Tank priority context for encounter/member/responsibility/actor"
                )
            cue_by_key[key] = cue

        responsibilities: list[RaidPlanTriggeredResponsibility] = []
        unresolved: list[str] = []
        seen_ids: set[str] = set()

        for trigger in triggers:
            cue = cue_by_key.get(
                (
                    trigger.encounter_id.casefold(),
                    trigger.member_id.casefold(),
                    trigger.responsibility_id.casefold(),
                    trigger.actor_name.casefold(),
                )
            )
            if cue is None:
                unresolved.append(
                    f"{trigger.actor_name}: reviewed add activity has no matching Tank priority context"
                )
                continue

            cue_trigger = _key(cue.trigger)
            if cue_trigger == "reviewed_add_activity_and_encounter_context":
                unresolved.append(
                    f"{trigger.actor_name}: Tank responsibility requires additional encounter context before it can become triggered plan intent"
                )
                continue
            if cue_trigger != "reviewed_add_activity":
                unresolved.append(
                    f"{trigger.actor_name}: unsupported Tank priority trigger {cue.trigger!r}"
                )
                continue

            responsibility_id = (
                f"{_key(trigger.encounter_id)}:{_key(trigger.responsibility_id)}:"
                f"{_key(trigger.actor_name)}"
            )
            identity = responsibility_id.casefold()
            if identity in seen_ids:
                continue
            seen_ids.add(identity)

            responsibilities.append(
                RaidPlanTriggeredResponsibility(
                    responsibility_id=responsibility_id,
                    seat_id=resolved_seat,
                    encounter_id=trigger.encounter_id,
                    trigger_key=f"encounter_actor_active:{_key(trigger.actor_name)}",
                    directive=cue.directive,
                    target_key=trigger.actor_name,
                    required_capability_type=trigger.required_capability_type,
                    source=(
                        f"{trigger.source} Priority context: {cue.interpretation}"
                    ),
                )
            )

        return RaidPlanTankTriggeredResponsibilityProjection(
            responsibilities=tuple(responsibilities),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def apply_to_plan(
        self,
        *,
        plan: RaidPlan,
        seat_id: str,
        add_activity_triggers: tuple[RotationTankEncounterAddActivityTrigger, ...],
        priority_context: tuple[RotationTankEncounterPriorityCue, ...],
    ) -> RaidPlanTankTriggeredResponsibilityApplication:
        """Apply reviewed Tank runtime intent without overwriting raid-lead decisions.

        Existing identical responsibility rows are idempotent. A responsibility identity
        already present with different intent remains untouched and is reported unresolved;
        projection is not authority to rewrite an existing Raid Plan decision.
        """

        if not isinstance(plan, RaidPlan):
            raise TypeError("Tank triggered responsibility application requires RaidPlan")
        resolved_seat = str(seat_id or "").strip()
        if not resolved_seat:
            raise ValueError("Tank triggered responsibility application requires seat_id")
        if plan.member(resolved_seat) is None:
            raise ValueError(
                f"Tank triggered responsibility application references unknown Raid Plan seat {resolved_seat!r}"
            )

        projection = self.project(
            seat_id=resolved_seat,
            add_activity_triggers=add_activity_triggers,
            priority_context=priority_context,
        )
        existing_by_id = {
            row.responsibility_id.casefold(): row
            for row in plan.triggered_responsibilities
        }
        merged = list(plan.triggered_responsibilities)
        applied: list[RaidPlanTriggeredResponsibility] = []
        unresolved = list(projection.unresolved)

        for row in projection.responsibilities:
            existing = existing_by_id.get(row.responsibility_id.casefold())
            if existing is None:
                merged.append(row)
                existing_by_id[row.responsibility_id.casefold()] = row
                applied.append(row)
                continue
            if existing == row:
                applied.append(existing)
                continue
            unresolved.append(
                f"{row.responsibility_id}: Raid Plan already contains different triggered responsibility intent; existing plan decision preserved"
            )

        updated = replace(plan, triggered_responsibilities=tuple(merged))
        return RaidPlanTankTriggeredResponsibilityApplication(
            plan=updated,
            applied=tuple(applied),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RaidPlanTankTriggeredResponsibilityApplication",
    "RaidPlanTankTriggeredResponsibilityProjection",
    "RaidPlanTankTriggeredResponsibilityService",
]
