from __future__ import annotations

"""Project Raid Plan runtime-triggered responsibilities into Rotation execution intent.

This boundary deliberately does not schedule actions. A runtime-triggered intent records
what should happen when a reviewed condition becomes true, while the ordinary RotationPlan
continues to own only concrete clock-timed actions. A later runtime-condition resolver may
materialize one of these intents after authoritative trigger evidence exists.
"""

from dataclasses import dataclass

from models.raid_plan import RaidPlanTriggeredResponsibility


def _clean(value: object) -> str:
    return str(value or "").strip()


def _optional(value: object) -> str | None:
    text = _clean(value)
    return text or None


@dataclass(frozen=True)
class RotationRuntimeTriggeredIntent:
    """One pending execution instruction whose trigger has no clock time yet."""

    intent_id: str
    trigger_key: str
    directive: str
    source_plan_id: str
    source_seat_id: str
    encounter_id: str
    target_key: str | None = None
    required_capability_type: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "intent_id",
            "trigger_key",
            "directive",
            "source_plan_id",
            "source_seat_id",
            "encounter_id",
        ):
            value = _clean(getattr(self, field_name))
            if not value:
                raise ValueError(f"runtime-triggered intent {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        object.__setattr__(self, "target_key", _optional(self.target_key))
        capability = _optional(self.required_capability_type)
        object.__setattr__(
            self,
            "required_capability_type",
            capability.casefold() if capability is not None else None,
        )
        object.__setattr__(self, "source", _optional(self.source))


class RotationRuntimeTriggeredIntentService:
    """Convert already-bound Raid Plan responsibilities into pending Rotation intent."""

    def project(
        self,
        *,
        plan_id: str,
        seat_id: str,
        responsibilities: tuple[RaidPlanTriggeredResponsibility, ...],
    ) -> tuple[RotationRuntimeTriggeredIntent, ...]:
        resolved_plan = _clean(plan_id)
        resolved_seat = _clean(seat_id)
        if not resolved_plan:
            raise ValueError("runtime-triggered intent projection requires plan_id")
        if not resolved_seat:
            raise ValueError("runtime-triggered intent projection requires seat_id")

        intents: list[RotationRuntimeTriggeredIntent] = []
        seen: set[str] = set()
        for responsibility in tuple(responsibilities):
            if responsibility.seat_id.casefold() != resolved_seat.casefold():
                raise ValueError(
                    "runtime-triggered responsibility does not belong to the bound Raid Plan seat"
                )
            identity = responsibility.responsibility_id.casefold()
            if identity in seen:
                continue
            seen.add(identity)
            intents.append(
                RotationRuntimeTriggeredIntent(
                    intent_id=responsibility.responsibility_id,
                    trigger_key=responsibility.trigger_key,
                    directive=responsibility.directive,
                    source_plan_id=resolved_plan,
                    source_seat_id=resolved_seat,
                    encounter_id=responsibility.encounter_id,
                    target_key=responsibility.target_key,
                    required_capability_type=responsibility.required_capability_type,
                    source=responsibility.source,
                )
            )
        return tuple(intents)


__all__ = [
    "RotationRuntimeTriggeredIntent",
    "RotationRuntimeTriggeredIntentService",
]
