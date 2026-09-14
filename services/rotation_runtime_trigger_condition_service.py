from __future__ import annotations

"""Resolve pending Rotation runtime intent against authoritative trigger observations.

This service owns only condition truth. An observed runtime condition may activate an
intent at an exact clock time, but that does not yet identify which skill, bar, action
kind, or refresh strategy should satisfy the intent. Action selection remains a separate
execution-strategy responsibility.
"""

from dataclasses import dataclass
import math

from services.rotation_runtime_triggered_intent_service import RotationRuntimeTriggeredIntent


def _clean(value: object) -> str:
    return str(value or "").strip()


def _optional(value: object) -> str | None:
    text = _clean(value)
    return text or None


@dataclass(frozen=True)
class RotationRuntimeTriggerObservation:
    """Authoritative observation that one runtime trigger became true at an exact time."""

    trigger_key: str
    observed_at_seconds: float
    source: str
    encounter_id: str | None = None
    source_plan_id: str | None = None
    source_seat_id: str | None = None
    authoritative: bool = True

    def __post_init__(self) -> None:
        trigger_key = _clean(self.trigger_key)
        source = _clean(self.source)
        if not trigger_key:
            raise ValueError("runtime trigger observation requires trigger_key")
        if not source:
            raise ValueError("runtime trigger observation requires source")
        observed = float(self.observed_at_seconds)
        if not math.isfinite(observed) or observed < 0.0:
            raise ValueError(
                "runtime trigger observation time must be finite and non-negative"
            )
        object.__setattr__(self, "trigger_key", trigger_key)
        object.__setattr__(self, "observed_at_seconds", observed)
        object.__setattr__(self, "source", source)
        for field_name in ("encounter_id", "source_plan_id", "source_seat_id"):
            object.__setattr__(self, field_name, _optional(getattr(self, field_name)))
        object.__setattr__(self, "authoritative", bool(self.authoritative))


@dataclass(frozen=True)
class RotationRuntimeActivatedIntent:
    """One pending intent whose condition is proven true at an exact runtime time."""

    intent: RotationRuntimeTriggeredIntent
    activated_at_seconds: float
    trigger_source: str

    def __post_init__(self) -> None:
        if not isinstance(self.intent, RotationRuntimeTriggeredIntent):
            raise TypeError("activated runtime intent requires RotationRuntimeTriggeredIntent")
        activated = float(self.activated_at_seconds)
        if not math.isfinite(activated) or activated < 0.0:
            raise ValueError("activated runtime intent time must be finite and non-negative")
        source = _clean(self.trigger_source)
        if not source:
            raise ValueError("activated runtime intent requires trigger_source")
        object.__setattr__(self, "activated_at_seconds", activated)
        object.__setattr__(self, "trigger_source", source)


@dataclass(frozen=True)
class RotationRuntimeTriggerResolution:
    activated: tuple[RotationRuntimeActivatedIntent, ...] = ()
    pending: tuple[RotationRuntimeTriggeredIntent, ...] = ()
    rejected_observations: tuple[str, ...] = ()


class RotationRuntimeTriggerConditionService:
    """Activate exact pending intents only from authoritative matching observations."""

    def resolve(
        self,
        *,
        intents: tuple[RotationRuntimeTriggeredIntent, ...],
        observations: tuple[RotationRuntimeTriggerObservation, ...],
    ) -> RotationRuntimeTriggerResolution:
        pending_intents = tuple(intents)
        observed = tuple(observations)

        observation_by_key: dict[str, RotationRuntimeTriggerObservation] = {}
        rejected: list[str] = []
        for row in observed:
            if not row.authoritative:
                rejected.append(
                    f"{row.trigger_key}: observation is not authoritative runtime evidence"
                )
                continue
            key = row.trigger_key.casefold()
            existing = observation_by_key.get(key)
            if existing is None or row.observed_at_seconds < existing.observed_at_seconds:
                observation_by_key[key] = row

        activated: list[RotationRuntimeActivatedIntent] = []
        still_pending: list[RotationRuntimeTriggeredIntent] = []
        seen_intents: set[str] = set()

        for intent in pending_intents:
            identity = intent.intent_id.casefold()
            if identity in seen_intents:
                continue
            seen_intents.add(identity)

            observation = observation_by_key.get(intent.trigger_key.casefold())
            if observation is None:
                still_pending.append(intent)
                continue

            mismatch = self._scope_mismatch(intent, observation)
            if mismatch is not None:
                rejected.append(mismatch)
                still_pending.append(intent)
                continue

            activated.append(
                RotationRuntimeActivatedIntent(
                    intent=intent,
                    activated_at_seconds=observation.observed_at_seconds,
                    trigger_source=observation.source,
                )
            )

        return RotationRuntimeTriggerResolution(
            activated=tuple(activated),
            pending=tuple(still_pending),
            rejected_observations=tuple(dict.fromkeys(rejected)),
        )

    @staticmethod
    def _scope_mismatch(
        intent: RotationRuntimeTriggeredIntent,
        observation: RotationRuntimeTriggerObservation,
    ) -> str | None:
        checks = (
            ("encounter", observation.encounter_id, intent.encounter_id),
            ("Raid Plan", observation.source_plan_id, intent.source_plan_id),
            ("seat", observation.source_seat_id, intent.source_seat_id),
        )
        for label, observed_value, expected_value in checks:
            if observed_value is None:
                continue
            if observed_value.casefold() != expected_value.casefold():
                return (
                    f"{observation.trigger_key}: authoritative observation {label} scope "
                    "does not match pending runtime intent"
                )
        return None


__all__ = [
    "RotationRuntimeActivatedIntent",
    "RotationRuntimeTriggerConditionService",
    "RotationRuntimeTriggerObservation",
    "RotationRuntimeTriggerResolution",
]
