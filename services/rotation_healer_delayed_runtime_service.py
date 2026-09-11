from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Protocol

from services.rotation_healer_action_healing_service import (
    RotationHealerDelayedHealSeed,
    RotationHealerResolvedHealEvent,
)


_AFTER_SECONDS_RE = re.compile(
    r"\bafter\s+(?P<delay>\d+(?:\.\d+)?)\s+seconds?\b",
    re.IGNORECASE,
)


class RotationHealerDelayedMagnitudePolicy(str, Enum):
    """When a delayed-heal consequence resolves its magnitude inputs."""

    SNAPSHOT_AT_CAST = "snapshot_at_cast"
    RECALCULATE_AT_LANDING = "recalculate_at_landing"


@dataclass(frozen=True)
class RotationHealerDelayedMagnitudeResolution:
    """Resolved magnitude for one exact delayed-heal landing."""

    modeled_heal: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.modeled_heal is not None and not self.unresolved


class RotationHealerDelayedMagnitudeResolver(Protocol):
    def __call__(
        self,
        seed: RotationHealerDelayedHealSeed,
        time_seconds: float,
        sequence: int,
    ) -> RotationHealerDelayedMagnitudeResolution: ...


@dataclass(frozen=True)
class RotationHealerDelayedRuntimeEvidence:
    source_name: str
    coefficient_number: int
    delay_seconds: float
    provenance: tuple[str, ...] = ()
    magnitude_policy: RotationHealerDelayedMagnitudePolicy | None = None

    def __post_init__(self) -> None:
        name = str(self.source_name or "").strip()
        if not name:
            raise ValueError("delayed healer runtime evidence requires source_name")
        object.__setattr__(self, "source_name", name)
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))
        delay = float(self.delay_seconds)
        if not math.isfinite(delay) or delay < 0:
            raise ValueError("delayed healer runtime delay must be finite and non-negative")
        object.__setattr__(self, "delay_seconds", delay)
        provenance = tuple(
            dict.fromkeys(str(item).strip() for item in self.provenance if str(item).strip())
        )
        object.__setattr__(self, "provenance", provenance)
        if self.magnitude_policy is not None and not isinstance(
            self.magnitude_policy,
            RotationHealerDelayedMagnitudePolicy,
        ):
            object.__setattr__(
                self,
                "magnitude_policy",
                RotationHealerDelayedMagnitudePolicy(str(self.magnitude_policy)),
            )
        if self.magnitude_policy is not None and not provenance:
            raise ValueError(
                "reviewed delayed-heal magnitude policy requires provenance"
            )


@dataclass(frozen=True)
class RotationHealerDelayedRuntimeProjection:
    events: tuple[RotationHealerResolvedHealEvent, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerDelayedRuntimeService:
    """Schedule delayed healer consequences only from explicit runtime evidence.

    Timing and magnitude timing are separate evidence classes. Existing callers that
    only request verified landing timing preserve the cast-resolved seed magnitude.
    A caller that supplies ``runtime_magnitude_resolver`` is explicitly asking for
    time-varying delayed magnitude evaluation; in that mode each component must also
    have a reviewed ``magnitude_policy``. Unknown cast-snapshot-vs-landing semantics
    fail closed rather than being inferred merely because the heal is delayed.

    This service intentionally models one delayed consequence per activation.
    Reapplication topology such as Budding Seeds' second-activation bloom remains
    a separate concern because a second button press may terminate or transform
    the original pending/periodic state rather than create another ordinary copy.
    """

    def project(
        self,
        *,
        seeds: tuple[RotationHealerDelayedHealSeed, ...],
        evidence: tuple[RotationHealerDelayedRuntimeEvidence, ...],
        horizon_seconds: float,
        runtime_magnitude_resolver: RotationHealerDelayedMagnitudeResolver | None = None,
    ) -> RotationHealerDelayedRuntimeProjection:
        horizon = float(horizon_seconds)
        if not math.isfinite(horizon) or horizon < 0:
            raise ValueError("delayed healer horizon must be finite and non-negative")

        evidence_by_key = {
            (item.source_name.casefold(), item.coefficient_number): item
            for item in evidence
        }
        events: list[RotationHealerResolvedHealEvent] = []
        unresolved: list[str] = []

        for seed in seeds:
            key = (seed.source_name.casefold(), int(seed.coefficient_number))
            runtime = evidence_by_key.get(key)
            if runtime is None:
                unresolved.append(
                    f"{seed.source_name} coefficient {seed.coefficient_number}: "
                    "delayed healing runtime evidence unavailable"
                )
                continue
            if runtime_magnitude_resolver is not None and runtime.magnitude_policy is None:
                unresolved.append(
                    f"{seed.source_name} coefficient {seed.coefficient_number}: "
                    "delayed healing magnitude snapshot/recalculation policy is not canonically verified"
                )
                continue

            event_time = float(seed.time_seconds) + runtime.delay_seconds
            if event_time > horizon:
                continue

            modeled_heal = float(seed.modeled_heal)
            if (
                runtime_magnitude_resolver is not None
                and runtime.magnitude_policy
                is RotationHealerDelayedMagnitudePolicy.RECALCULATE_AT_LANDING
            ):
                magnitude = runtime_magnitude_resolver(
                    seed,
                    float(event_time),
                    int(seed.sequence),
                )
                if not magnitude.resolved or magnitude.modeled_heal is None:
                    messages = magnitude.unresolved or (
                        "delayed healing landing magnitude is unresolved",
                    )
                    unresolved.extend(
                        f"{seed.source_name} coefficient {seed.coefficient_number} "
                        f"at {event_time:g}s: {message}"
                        for message in messages
                    )
                    continue
                modeled_heal = float(magnitude.modeled_heal)

            events.append(
                RotationHealerResolvedHealEvent(
                    time_seconds=event_time,
                    sequence=int(seed.sequence),
                    source_name=seed.source_name,
                    coefficient_number=int(seed.coefficient_number),
                    modeled_heal=modeled_heal,
                )
            )

        return RotationHealerDelayedRuntimeProjection(
            events=tuple(
                sorted(
                    events,
                    key=lambda item: (
                        item.time_seconds,
                        item.sequence,
                        item.source_name.casefold(),
                        item.coefficient_number,
                    ),
                )
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


def extract_delayed_heal_runtime_evidence(
    *,
    source_name: str,
    coefficient_number: int,
    component_fragment: str,
) -> RotationHealerDelayedRuntimeEvidence | None:
    """Extract explicit landing timing only; magnitude semantics need review evidence."""

    text = " ".join(str(component_fragment or "").split())
    match = _AFTER_SECONDS_RE.search(text)
    if match is None:
        return None
    return RotationHealerDelayedRuntimeEvidence(
        source_name=source_name,
        coefficient_number=coefficient_number,
        delay_seconds=float(match.group("delay")),
        provenance=(f"coefficient-local wording: {match.group(0)}",),
    )


__all__ = [
    "RotationHealerDelayedMagnitudePolicy",
    "RotationHealerDelayedMagnitudeResolution",
    "RotationHealerDelayedMagnitudeResolver",
    "RotationHealerDelayedRuntimeEvidence",
    "RotationHealerDelayedRuntimeProjection",
    "RotationHealerDelayedRuntimeService",
    "extract_delayed_heal_runtime_evidence",
]
