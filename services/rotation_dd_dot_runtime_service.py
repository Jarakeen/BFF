from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from minmax.dd_damage import DDDamageEvent
from services.rotation_dd_action_damage_event_service import (
    RotationDDDotComponentSeed,
    RotationDDResolvedDamageEvent,
)


class RotationDDDotRefreshPolicy(str, Enum):
    RESTART = "restart"


@dataclass(frozen=True)
class RotationDDDotRuntimeEvidence:
    source_name: str
    coefficient_number: int
    duration_seconds: float
    tick_interval_seconds: float
    first_tick_offset_seconds: float
    refresh_policy: RotationDDDotRefreshPolicy = RotationDDDotRefreshPolicy.RESTART
    tick_on_expiry_boundary: bool = True

    def __post_init__(self) -> None:
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
            raise ValueError("DoT duration and tick interval must be positive")
        if self.first_tick_offset_seconds > self.duration_seconds:
            raise ValueError("first DoT tick cannot occur after duration")


@dataclass(frozen=True)
class RotationDDDotRuntimeProjection:
    events: tuple[RotationDDResolvedDamageEvent, ...]
    unresolved: tuple[str, ...]


class RotationDDDotRuntimeService:
    """Expand verified DoT seeds only from explicit runtime timing evidence."""

    def project(
        self,
        *,
        seeds: tuple[RotationDDDotComponentSeed, ...],
        evidence: tuple[RotationDDDotRuntimeEvidence, ...],
        horizon_seconds: float,
    ) -> RotationDDDotRuntimeProjection:
        horizon = float(horizon_seconds)
        if not math.isfinite(horizon) or horizon < 0:
            raise ValueError("DoT horizon must be finite and non-negative")

        evidence_by_key = {
            (item.source_name.casefold(), int(item.coefficient_number)): item
            for item in evidence
        }
        unresolved: list[str] = []
        events: list[RotationDDResolvedDamageEvent] = []

        grouped: dict[tuple[str, int], list[RotationDDDotComponentSeed]] = {}
        for seed in seeds:
            grouped.setdefault(
                (seed.source_name.casefold(), int(seed.coefficient_number)), []
            ).append(seed)

        for key, group in grouped.items():
            runtime = evidence_by_key.get(key)
            if runtime is None:
                label = group[0]
                unresolved.append(
                    f"{label.source_name} coefficient {label.coefficient_number}: "
                    "DoT runtime evidence unavailable"
                )
                continue

            ordered = sorted(group, key=lambda item: (item.cast_time_seconds, item.sequence))
            for index, seed in enumerate(ordered):
                natural_end = seed.cast_time_seconds + runtime.duration_seconds
                next_cast = (
                    ordered[index + 1].cast_time_seconds
                    if index + 1 < len(ordered)
                    else math.inf
                )
                active_end = min(natural_end, next_cast, horizon)
                tick_time = seed.cast_time_seconds + runtime.first_tick_offset_seconds
                tick_index = 0
                while tick_time <= active_end:
                    if (
                        not runtime.tick_on_expiry_boundary
                        and math.isclose(tick_time, natural_end, abs_tol=1e-9)
                    ):
                        break
                    if tick_time >= next_cast:
                        break
                    events.append(
                        RotationDDResolvedDamageEvent(
                            time_seconds=tick_time,
                            sequence=seed.sequence * 1000 + tick_index,
                            source_name=seed.source_name,
                            coefficient_number=seed.coefficient_number,
                            event=DDDamageEvent(
                                base_value=seed.event.base_value,
                                scaling_coefficient=seed.event.scaling_coefficient,
                                damage_type=seed.event.damage_type,
                                can_crit=seed.event.can_crit,
                                is_dot=True,
                                is_aoe=seed.event.is_aoe,
                            ),
                        )
                    )
                    tick_index += 1
                    tick_time = (
                        seed.cast_time_seconds
                        + runtime.first_tick_offset_seconds
                        + tick_index * runtime.tick_interval_seconds
                    )

        return RotationDDDotRuntimeProjection(
            events=tuple(sorted(events, key=lambda item: (item.time_seconds, item.sequence))),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
