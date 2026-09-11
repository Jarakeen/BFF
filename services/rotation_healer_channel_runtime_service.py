from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Protocol

from minmax.runtime_event import PeriodicRuntimeSchedule, schedule_periodic_runtime_events
from services.rotation_healer_action_healing_service import (
    RotationHealerChannelHealSeed,
    RotationHealerResolvedHealEvent,
)


class RotationHealerChannelMagnitudePolicy(str, Enum):
    """When a channel-heal tick resolves its magnitude inputs."""

    SNAPSHOT_AT_CAST = "snapshot_at_cast"
    RECALCULATE_EACH_TICK = "recalculate_each_tick"


@dataclass(frozen=True)
class RotationHealerChannelMagnitudeResolution:
    modeled_heal: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.modeled_heal is not None and not self.unresolved


class RotationHealerChannelMagnitudeResolver(Protocol):
    def __call__(
        self,
        seed: RotationHealerChannelHealSeed,
        time_seconds: float,
        sequence: int,
    ) -> RotationHealerChannelMagnitudeResolution: ...


@dataclass(frozen=True)
class RotationHealerChannelRuntimeEvidence:
    """Reviewed runtime evidence for one channel-heal component.

    Channel duration and tick cadence are separate semantic facts. Callers should
    source ``channel_duration_seconds`` from canonical channel-time evidence when
    available; this service does not infer duration from generic occupancy.
    """

    source_name: str
    coefficient_number: int
    channel_duration_seconds: float
    tick_interval_seconds: float
    first_tick_offset_seconds: float
    tick_on_channel_end_boundary: bool
    magnitude_policy: RotationHealerChannelMagnitudePolicy | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = str(self.source_name or "").strip()
        if not name:
            raise ValueError("channel healer runtime evidence requires source_name")
        object.__setattr__(self, "source_name", name)
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))

        for field_name in (
            "channel_duration_seconds",
            "tick_interval_seconds",
            "first_tick_offset_seconds",
        ):
            value = float(getattr(self, field_name))
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, value)

        if self.channel_duration_seconds <= 0 or self.tick_interval_seconds <= 0:
            raise ValueError("channel duration and tick interval must be positive")
        if self.first_tick_offset_seconds > self.channel_duration_seconds:
            raise ValueError("first channel-heal tick cannot occur after channel duration")
        if self.magnitude_policy is not None and not isinstance(
            self.magnitude_policy, RotationHealerChannelMagnitudePolicy
        ):
            object.__setattr__(
                self,
                "magnitude_policy",
                RotationHealerChannelMagnitudePolicy(str(self.magnitude_policy)),
            )

        provenance = tuple(
            dict.fromkeys(
                str(item).strip() for item in self.provenance if str(item).strip()
            )
        )
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True)
class RotationHealerChannelRuntimeProjection:
    events: tuple[RotationHealerResolvedHealEvent, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerChannelRuntimeService:
    """Expand reviewed channel-heal seeds into exact tick events.

    The service owns only channel tick scheduling. It does not infer cadence from
    channel duration, does not infer duration from generic action occupancy, and does
    not guess snapshot-vs-recalculation magnitude semantics.
    """

    def project(
        self,
        *,
        seeds: tuple[RotationHealerChannelHealSeed, ...],
        evidence: tuple[RotationHealerChannelRuntimeEvidence, ...],
        horizon_seconds: float,
        runtime_magnitude_resolver: RotationHealerChannelMagnitudeResolver | None = None,
    ) -> RotationHealerChannelRuntimeProjection:
        horizon = float(horizon_seconds)
        if not math.isfinite(horizon) or horizon < 0:
            raise ValueError("channel healer horizon must be finite and non-negative")

        evidence_by_key = {
            (item.source_name.casefold(), int(item.coefficient_number)): item
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
                    "channel healing runtime evidence unavailable"
                )
                continue

            if runtime_magnitude_resolver is not None and runtime.magnitude_policy is None:
                unresolved.append(
                    f"{seed.source_name} coefficient {seed.coefficient_number}: "
                    "channel healing magnitude snapshot/recalculation policy is not canonically verified"
                )
                continue

            natural_end = float(seed.time_seconds) + runtime.channel_duration_seconds
            active_end = min(natural_end, horizon)
            first_tick = float(seed.time_seconds) + runtime.first_tick_offset_seconds
            if first_tick > active_end:
                continue

            scheduled = schedule_periodic_runtime_events(
                PeriodicRuntimeSchedule(
                    trigger="channel_heal_tick",
                    source=seed.source_name,
                    interval_seconds=runtime.tick_interval_seconds,
                    start_time_seconds=first_tick,
                    end_time_seconds=active_end,
                ),
                starting_sequence=int(seed.sequence) * 1000,
            )

            for event in scheduled:
                at_channel_end = math.isclose(
                    event.time_seconds,
                    natural_end,
                    rel_tol=0.0,
                    abs_tol=1e-9,
                )
                if not runtime.tick_on_channel_end_boundary and at_channel_end:
                    continue

                modeled_heal = float(seed.modeled_heal)
                if (
                    runtime_magnitude_resolver is not None
                    and runtime.magnitude_policy
                    is RotationHealerChannelMagnitudePolicy.RECALCULATE_EACH_TICK
                ):
                    magnitude = runtime_magnitude_resolver(
                        seed,
                        float(event.time_seconds),
                        int(event.sequence),
                    )
                    if not magnitude.resolved or magnitude.modeled_heal is None:
                        messages = magnitude.unresolved or (
                            "channel healing tick magnitude is unresolved",
                        )
                        unresolved.extend(
                            f"{seed.source_name} coefficient {seed.coefficient_number} "
                            f"at {event.time_seconds:g}s: {message}"
                            for message in messages
                        )
                        continue
                    modeled_heal = float(magnitude.modeled_heal)

                events.append(
                    RotationHealerResolvedHealEvent(
                        time_seconds=float(event.time_seconds),
                        sequence=int(event.sequence),
                        source_name=seed.source_name,
                        coefficient_number=int(seed.coefficient_number),
                        modeled_heal=modeled_heal,
                    )
                )

        return RotationHealerChannelRuntimeProjection(
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


__all__ = [
    "RotationHealerChannelMagnitudePolicy",
    "RotationHealerChannelMagnitudeResolution",
    "RotationHealerChannelMagnitudeResolver",
    "RotationHealerChannelRuntimeEvidence",
    "RotationHealerChannelRuntimeProjection",
    "RotationHealerChannelRuntimeService",
]
