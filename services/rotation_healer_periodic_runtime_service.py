from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Protocol

from minmax.runtime_event import PeriodicRuntimeSchedule, schedule_periodic_runtime_events
from services.rotation_healer_action_healing_service import (
    RotationHealerPeriodicHealSeed,
    RotationHealerResolvedHealEvent,
)


class RotationHealerPeriodicRefreshPolicy(str, Enum):
    RESTART = "restart"


class RotationHealerPeriodicMagnitudePolicy(str, Enum):
    """When one periodic-heal occurrence resolves its magnitude inputs."""

    SNAPSHOT_AT_CAST = "snapshot_at_cast"
    RECALCULATE_EACH_TICK = "recalculate_each_tick"


@dataclass(frozen=True)
class RotationHealerPeriodicMagnitudeResolution:
    """Resolved magnitude for one exact periodic-heal occurrence."""

    modeled_heal: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.modeled_heal is not None and not self.unresolved


class RotationHealerPeriodicMagnitudeResolver(Protocol):
    def __call__(
        self,
        seed: RotationHealerPeriodicHealSeed,
        time_seconds: float,
        sequence: int,
    ) -> RotationHealerPeriodicMagnitudeResolution: ...


@dataclass(frozen=True)
class RotationHealerPeriodicRuntimeEvidence:
    """Explicit runtime timing and optional magnitude-timing evidence for one HoT component."""

    source_name: str
    coefficient_number: int
    duration_seconds: float
    tick_interval_seconds: float
    first_tick_offset_seconds: float
    tick_on_expiry_boundary: bool
    refresh_policy: RotationHealerPeriodicRefreshPolicy | None = None
    magnitude_policy: RotationHealerPeriodicMagnitudePolicy | None = None

    def __post_init__(self) -> None:
        source_name = str(self.source_name or "").strip()
        if not source_name:
            raise ValueError("periodic heal runtime evidence requires source_name")
        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))

        for field_name in (
            "duration_seconds",
            "tick_interval_seconds",
            "first_tick_offset_seconds",
        ):
            value = float(getattr(self, field_name))
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, value)

        if self.duration_seconds <= 0 or self.tick_interval_seconds <= 0:
            raise ValueError("periodic heal duration and tick interval must be positive")
        if self.first_tick_offset_seconds > self.duration_seconds:
            raise ValueError("first periodic heal tick cannot occur after duration")
        if self.refresh_policy is not None and not isinstance(
            self.refresh_policy, RotationHealerPeriodicRefreshPolicy
        ):
            object.__setattr__(
                self,
                "refresh_policy",
                RotationHealerPeriodicRefreshPolicy(str(self.refresh_policy)),
            )
        if self.magnitude_policy is not None and not isinstance(
            self.magnitude_policy, RotationHealerPeriodicMagnitudePolicy
        ):
            object.__setattr__(
                self,
                "magnitude_policy",
                RotationHealerPeriodicMagnitudePolicy(str(self.magnitude_policy)),
            )


@dataclass(frozen=True)
class RotationHealerPeriodicRuntimeProjection:
    events: tuple[RotationHealerResolvedHealEvent, ...]
    unresolved: tuple[str, ...]


class RotationHealerPeriodicRuntimeService:
    """Expand periodic-heal seeds only from explicit runtime evidence.

    Timing and magnitude timing are separate evidence classes. Existing callers that
    only request canonical tick timing preserve the cast-resolved ``seed.modeled_heal``
    value. A caller that supplies ``runtime_magnitude_resolver`` is explicitly asking
    for time-varying magnitude evaluation; in that mode each component must also have
    a reviewed ``magnitude_policy``. Unknown snapshot-vs-recalculation semantics fail
    closed rather than being inferred from the fact that an effect is periodic.

    Healer-specific logic owns duration evidence and refresh legality. Actual cadence
    expansion is delegated to the shared Phase 7 periodic runtime scheduler so DD,
    healing, proc, and other recurring consequences do not grow separate clock
    arithmetic.
    """

    def project(
        self,
        *,
        seeds: tuple[RotationHealerPeriodicHealSeed, ...],
        evidence: tuple[RotationHealerPeriodicRuntimeEvidence, ...],
        horizon_seconds: float,
        runtime_magnitude_resolver: RotationHealerPeriodicMagnitudeResolver | None = None,
    ) -> RotationHealerPeriodicRuntimeProjection:
        horizon = float(horizon_seconds)
        if not math.isfinite(horizon) or horizon < 0:
            raise ValueError("periodic heal horizon must be finite and non-negative")

        evidence_by_key = {
            (item.source_name.casefold(), int(item.coefficient_number)): item
            for item in evidence
        }
        grouped: dict[tuple[str, int], list[RotationHealerPeriodicHealSeed]] = {}
        for seed in seeds:
            grouped.setdefault(
                (seed.source_name.casefold(), int(seed.coefficient_number)), []
            ).append(seed)

        events: list[RotationHealerResolvedHealEvent] = []
        unresolved: list[str] = []

        for key, group in grouped.items():
            runtime = evidence_by_key.get(key)
            label = group[0]
            if runtime is None:
                unresolved.append(
                    f"{label.source_name} coefficient {label.coefficient_number}: "
                    "periodic healing runtime evidence unavailable"
                )
                continue

            if runtime_magnitude_resolver is not None and runtime.magnitude_policy is None:
                unresolved.append(
                    f"{label.source_name} coefficient {label.coefficient_number}: "
                    "periodic healing magnitude snapshot/recalculation policy is not canonically verified"
                )
                continue

            ordered = sorted(group, key=lambda item: (item.time_seconds, item.sequence))
            if len(ordered) > 1 and runtime.refresh_policy is None:
                unresolved.append(
                    f"{label.source_name} coefficient {label.coefficient_number}: "
                    "periodic healing refresh behavior is not canonically verified"
                )
                continue

            for index, seed in enumerate(ordered):
                natural_end = seed.time_seconds + runtime.duration_seconds
                next_cast = (
                    ordered[index + 1].time_seconds
                    if index + 1 < len(ordered)
                    else math.inf
                )
                active_end = min(natural_end, horizon)
                if runtime.refresh_policy is RotationHealerPeriodicRefreshPolicy.RESTART:
                    active_end = min(active_end, next_cast)

                first_tick = seed.time_seconds + runtime.first_tick_offset_seconds
                if first_tick > active_end:
                    continue

                scheduled = schedule_periodic_runtime_events(
                    PeriodicRuntimeSchedule(
                        trigger="periodic_heal_tick",
                        source=seed.source_name,
                        interval_seconds=runtime.tick_interval_seconds,
                        start_time_seconds=first_tick,
                        end_time_seconds=active_end,
                    ),
                    starting_sequence=seed.sequence * 1000,
                )

                for event in scheduled:
                    at_natural_expiry = math.isclose(
                        event.time_seconds,
                        natural_end,
                        rel_tol=0.0,
                        abs_tol=1e-9,
                    )
                    if not runtime.tick_on_expiry_boundary and at_natural_expiry:
                        continue

                    at_or_after_restart = (
                        runtime.refresh_policy is RotationHealerPeriodicRefreshPolicy.RESTART
                        and math.isfinite(next_cast)
                        and (
                            event.time_seconds > next_cast
                            or math.isclose(
                                event.time_seconds,
                                next_cast,
                                rel_tol=0.0,
                                abs_tol=1e-9,
                            )
                        )
                    )
                    if at_or_after_restart:
                        continue

                    modeled_heal = seed.modeled_heal
                    if (
                        runtime_magnitude_resolver is not None
                        and runtime.magnitude_policy
                        is RotationHealerPeriodicMagnitudePolicy.RECALCULATE_EACH_TICK
                    ):
                        magnitude = runtime_magnitude_resolver(
                            seed,
                            float(event.time_seconds),
                            int(event.sequence),
                        )
                        if not magnitude.resolved or magnitude.modeled_heal is None:
                            messages = magnitude.unresolved or (
                                "periodic healing tick magnitude is unresolved",
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
                            time_seconds=event.time_seconds,
                            sequence=event.sequence,
                            source_name=seed.source_name,
                            coefficient_number=seed.coefficient_number,
                            modeled_heal=modeled_heal,
                        )
                    )

        return RotationHealerPeriodicRuntimeProjection(
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
    "RotationHealerPeriodicMagnitudePolicy",
    "RotationHealerPeriodicMagnitudeResolution",
    "RotationHealerPeriodicMagnitudeResolver",
    "RotationHealerPeriodicRefreshPolicy",
    "RotationHealerPeriodicRuntimeEvidence",
    "RotationHealerPeriodicRuntimeProjection",
    "RotationHealerPeriodicRuntimeService",
]
