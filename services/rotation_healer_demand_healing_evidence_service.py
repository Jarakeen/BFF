from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandWindow
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerResolvedHealEvent,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeProjection,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeProjection,
)


@dataclass(frozen=True)
class RotationHealerDemandHealingEvidence:
    """Timed modeled-heal evidence observed inside one healing demand window."""

    demand: RotationDemandWindow
    direct_events: tuple[RotationHealerResolvedHealEvent, ...]
    periodic_events: tuple[RotationHealerResolvedHealEvent, ...]
    delayed_events: tuple[RotationHealerResolvedHealEvent, ...]
    modeled_direct_healing: float
    modeled_periodic_healing: float
    modeled_delayed_healing: float
    unresolved: tuple[str, ...]

    @property
    def modeled_total_healing(self) -> float:
        return (
            self.modeled_direct_healing
            + self.modeled_periodic_healing
            + self.modeled_delayed_healing
        )

    @property
    def has_timed_direct_heal(self) -> bool:
        return bool(self.direct_events)

    @property
    def has_timed_periodic_heal(self) -> bool:
        return bool(self.periodic_events)

    @property
    def has_timed_delayed_heal(self) -> bool:
        return bool(self.delayed_events)


class RotationHealerDemandHealingEvidenceService:
    """Place canonical healer consequences inside explicit encounter windows."""

    def assess(
        self,
        *,
        demand: RotationDemandWindow,
        projection: RotationHealerActionHealingProjection,
        periodic_projection: RotationHealerPeriodicRuntimeProjection | None = None,
        delayed_projection: RotationHealerDelayedRuntimeProjection | None = None,
    ) -> RotationHealerDemandHealingEvidence:
        if demand.kind is not RotationDemandKind.HEALING:
            raise ValueError(
                "healer demand healing evidence requires a healing demand window"
            )

        direct_events = tuple(
            event
            for event in projection.direct_events
            if demand.start_seconds <= event.time_seconds <= demand.end_seconds
        )
        unresolved = list(projection.unresolved)

        for seed in projection.external_conditional_seeds:
            effect_start = float(seed.time_seconds)
            effect_end = effect_start + float(seed.duration_seconds)
            overlaps = (
                effect_start <= demand.end_seconds
                and effect_end >= demand.start_seconds
            )
            if not overlaps:
                continue
            unresolved.append(
                f"{seed.source_name} at {seed.time_seconds:g}s: reviewed external healing "
                f"condition {seed.trigger_condition} is not yet modeled for demand coverage"
            )

        periodic_events: tuple[RotationHealerResolvedHealEvent, ...] = ()
        periodic_in_or_before_window = tuple(
            seed
            for seed in projection.periodic_seeds
            if seed.time_seconds <= demand.end_seconds
        )
        if periodic_in_or_before_window:
            if periodic_projection is None:
                labels = ", ".join(
                    sorted({seed.source_name for seed in periodic_in_or_before_window})
                )
                unresolved.append(
                    f"{demand.name}: periodic healing runtime is unresolved for demand coverage"
                    + (f" ({labels})" if labels else "")
                )
            else:
                unresolved.extend(periodic_projection.unresolved)
                periodic_events = tuple(
                    event
                    for event in periodic_projection.events
                    if demand.start_seconds <= event.time_seconds <= demand.end_seconds
                )
        elif periodic_projection is not None:
            unresolved.extend(periodic_projection.unresolved)
            periodic_events = tuple(
                event
                for event in periodic_projection.events
                if demand.start_seconds <= event.time_seconds <= demand.end_seconds
            )

        delayed_events: tuple[RotationHealerResolvedHealEvent, ...] = ()
        delayed_in_or_before_window = tuple(
            seed
            for seed in projection.delayed_seeds
            if seed.time_seconds <= demand.end_seconds
        )
        if delayed_in_or_before_window:
            if delayed_projection is None:
                labels = ", ".join(
                    sorted({seed.source_name for seed in delayed_in_or_before_window})
                )
                unresolved.append(
                    f"{demand.name}: delayed healing runtime is unresolved for demand coverage"
                    + (f" ({labels})" if labels else "")
                )
            else:
                unresolved.extend(delayed_projection.unresolved)
                delayed_events = tuple(
                    event
                    for event in delayed_projection.events
                    if demand.start_seconds <= event.time_seconds <= demand.end_seconds
                )
        elif delayed_projection is not None:
            unresolved.extend(delayed_projection.unresolved)
            delayed_events = tuple(
                event
                for event in delayed_projection.events
                if demand.start_seconds <= event.time_seconds <= demand.end_seconds
            )

        return RotationHealerDemandHealingEvidence(
            demand=demand,
            direct_events=direct_events,
            periodic_events=periodic_events,
            delayed_events=delayed_events,
            modeled_direct_healing=sum(event.modeled_heal for event in direct_events),
            modeled_periodic_healing=sum(event.modeled_heal for event in periodic_events),
            modeled_delayed_healing=sum(event.modeled_heal for event in delayed_events),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
