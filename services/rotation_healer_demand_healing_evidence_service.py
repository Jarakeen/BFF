from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandWindow
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerResolvedHealEvent,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeProjection,
)


@dataclass(frozen=True)
class RotationHealerDemandHealingEvidence:
    """Timed modeled-heal evidence observed inside one healing demand window.

    This is deliberately evidence, not a pass/fail healing verdict. Encounter
    demand windows currently describe *when* healing matters, not verified HPS or
    received-heal thresholds. Direct and canonically scheduled periodic healing
    can therefore be reported without pretending either proves survival.
    """

    demand: RotationDemandWindow
    direct_events: tuple[RotationHealerResolvedHealEvent, ...]
    periodic_events: tuple[RotationHealerResolvedHealEvent, ...]
    modeled_direct_healing: float
    modeled_periodic_healing: float
    unresolved: tuple[str, ...]

    @property
    def modeled_total_healing(self) -> float:
        return self.modeled_direct_healing + self.modeled_periodic_healing

    @property
    def has_timed_direct_heal(self) -> bool:
        return bool(self.direct_events)

    @property
    def has_timed_periodic_heal(self) -> bool:
        return bool(self.periodic_events)


class RotationHealerDemandHealingEvidenceService:
    """Place canonical healer consequences inside explicit encounter windows."""

    def assess(
        self,
        *,
        demand: RotationDemandWindow,
        projection: RotationHealerActionHealingProjection,
        periodic_projection: RotationHealerPeriodicRuntimeProjection | None = None,
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

        return RotationHealerDemandHealingEvidence(
            demand=demand,
            direct_events=direct_events,
            periodic_events=periodic_events,
            modeled_direct_healing=sum(event.modeled_heal for event in direct_events),
            modeled_periodic_healing=sum(event.modeled_heal for event in periodic_events),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
