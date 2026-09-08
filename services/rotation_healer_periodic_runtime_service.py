from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from minmax.runtime_event import PeriodicRuntimeSchedule, schedule_periodic_runtime_events
from services.rotation_healer_action_healing_service import (
    RotationHealerPeriodicHealSeed,
    RotationHealerResolvedHealEvent,
)


class RotationHealerPeriodicRefreshPolicy(str, Enum):
    RESTART = "restart"


@dataclass(frozen=True)
class RotationHealerPeriodicRuntimeEvidence:
    """Explicit runtime timing evidence for one periodic healing component."""

    source_name: str
    coefficient_number: int
    duration_seconds: float
    tick_interval_seconds: float
    first_tick_offset_seconds: float
    tick_on_expiry_boundary: bool
    refresh_policy: RotationHealerPeriodicRefreshPolicy | None = None

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


@dataclass(frozen=True)
class RotationHealerPeriodicRuntimeProjection:
    events: tuple[RotationHealerResolvedHealEvent, ...]
    unresolved: tuple[str, ...]


class RotationHealerPeriodicRuntimeService:
    """Expand periodic-heal seeds only from explicit timing evidence.

    Healer-specific logic owns duration evidence and refresh legality. Actual
    cadence expansion is delegated to the shared Phase 7 periodic runtime
    scheduler so DD, healing, proc, and other recurring consequences do not grow
    separate clock arithmetic.
    """

    def project(
        self,
        *,
        seeds: tuple[RotationHealerPeriodicHealSeed, ...],
        evidence: tuple[RotationHealerPeriodicRuntimeEvidence, ...],
        horizon_seconds: float,
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

                schedule_end = active_end
                if not runtime.tick_on_expiry_boundary and math.isclose(
                    schedule_end, natural_end, abs_tol=1e-9
                ):
                    schedule_end = math.nextafter(schedule_end, -math.inf)
                if (
                    runtime.refresh_policy is RotationHealerPeriodicRefreshPolicy.RESTART
                    and math.isfinite(next_cast)
                    and math.isclose(schedule_end, next_cast, abs_tol=1e-9)
                ):
                    schedule_end = math.nextafter(schedule_end, -math.inf)

                scheduled = schedule_periodic_runtime_events(
                    PeriodicRuntimeSchedule(
                        trigger="periodic_heal_tick",
                        source=seed.source_name,
                        interval_seconds=runtime.tick_interval_seconds,
                        start_time_seconds=first_tick,
                        end_time_seconds=schedule_end,
                    ),
                    starting_sequence=seed.sequence * 1000,
                )
                events.extend(
                    RotationHealerResolvedHealEvent(
                        time_seconds=event.time_seconds,
                        sequence=event.sequence,
                        source_name=seed.source_name,
                        coefficient_number=seed.coefficient_number,
                        modeled_heal=seed.modeled_heal,
                    )
                    for event in scheduled
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
