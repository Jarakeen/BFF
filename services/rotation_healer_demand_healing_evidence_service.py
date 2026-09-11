from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandWindow
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerResolvedHealEvent,
)
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelRuntimeProjection,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeProjection,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeProjection,
)
from services.rotation_healer_external_conditional_healing_service import (
    RotationHealerExternalConditionalHealingService,
)


@dataclass(frozen=True)
class RotationHealerExternalConditionalDemandAssumption:
    """Explicit strategy input for sustained attackers during a demand window."""

    effect_name: str
    active_attacker_count: int

    def __post_init__(self) -> None:
        effect_name = str(self.effect_name or "").strip().casefold()
        if not effect_name:
            raise ValueError("external conditional effect name is required")
        object.__setattr__(self, "effect_name", effect_name)
        count = int(self.active_attacker_count)
        if count <= 0:
            raise ValueError("active attacker count must be positive")
        object.__setattr__(self, "active_attacker_count", count)


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
    modeled_external_conditional_healing: float = 0.0
    channel_events: tuple[RotationHealerResolvedHealEvent, ...] = ()
    modeled_channel_healing: float = 0.0

    @property
    def modeled_total_healing(self) -> float:
        return (
            self.modeled_direct_healing
            + self.modeled_periodic_healing
            + self.modeled_delayed_healing
            + self.modeled_channel_healing
            + self.modeled_external_conditional_healing
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

    @property
    def has_timed_channel_heal(self) -> bool:
        return bool(self.channel_events)


class RotationHealerDemandHealingEvidenceService:
    """Place canonical healer consequences inside explicit encounter windows."""

    def __init__(
        self,
        *,
        external_conditional_healing_service: RotationHealerExternalConditionalHealingService
        | None = None,
    ) -> None:
        self.external_conditional_healing_service = (
            external_conditional_healing_service
            or RotationHealerExternalConditionalHealingService()
        )

    def assess(
        self,
        *,
        demand: RotationDemandWindow,
        projection: RotationHealerActionHealingProjection,
        periodic_projection: RotationHealerPeriodicRuntimeProjection | None = None,
        delayed_projection: RotationHealerDelayedRuntimeProjection | None = None,
        channel_projection: RotationHealerChannelRuntimeProjection | None = None,
        external_conditional_assumptions: tuple[
            RotationHealerExternalConditionalDemandAssumption, ...
        ] = (),
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
        assumptions_by_effect: dict[
            str, RotationHealerExternalConditionalDemandAssumption
        ] = {}
        for assumption in external_conditional_assumptions:
            if assumption.effect_name in assumptions_by_effect:
                raise ValueError(
                    f"duplicate external conditional demand assumption: {assumption.effect_name}"
                )
            if assumption.active_attacker_count > demand.target_count:
                raise ValueError(
                    f"{assumption.effect_name}: active attacker count cannot exceed "
                    f"demand target count {demand.target_count}"
                )
            assumptions_by_effect[assumption.effect_name] = assumption
        modeled_external_conditional_healing = 0.0

        for seed in projection.external_conditional_seeds:
            effect_start = float(seed.time_seconds)
            effect_end = effect_start + float(seed.duration_seconds)
            overlap_seconds = max(
                0.0,
                min(effect_end, demand.end_seconds)
                - max(effect_start, demand.start_seconds),
            )
            if overlap_seconds <= 0:
                continue
            assumption = assumptions_by_effect.get(seed.effect_name.casefold())
            if assumption is None:
                unresolved.append(
                    f"{seed.source_name} at {seed.time_seconds:g}s: reviewed external healing "
                    f"condition {seed.trigger_condition} requires an explicit active-attacker "
                    "count for demand coverage"
                )
                continue
            canonical = self.external_conditional_healing_service.resolve(
                seed.skill_id,
                game_version=seed.game_version,
            )
            if (
                canonical is None
                or canonical.effect_name != seed.effect_name
                or canonical.magnitude_unit != "health_per_trigger"
                or canonical.trigger_actor != "damaging_actor"
                or canonical.heal_recipient != "trigger_actor"
                or canonical.maximum_trigger_rate_per_actor_per_second <= 0
            ):
                unresolved.append(
                    f"{seed.source_name} at {seed.time_seconds:g}s: reviewed external healing "
                    "runtime contract is unavailable for demand coverage"
                )
                continue
            modeled_external_conditional_healing += (
                float(seed.reviewed_magnitude)
                * float(canonical.maximum_trigger_rate_per_actor_per_second)
                * float(assumption.active_attacker_count)
                * overlap_seconds
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

        channel_events: tuple[RotationHealerResolvedHealEvent, ...] = ()
        channel_in_or_before_window = tuple(
            seed
            for seed in projection.channel_seeds
            if seed.time_seconds <= demand.end_seconds
        )
        if channel_in_or_before_window:
            if channel_projection is None:
                labels = ", ".join(
                    sorted({seed.source_name for seed in channel_in_or_before_window})
                )
                unresolved.append(
                    f"{demand.name}: channel healing runtime is unresolved for demand coverage"
                    + (f" ({labels})" if labels else "")
                )
            else:
                unresolved.extend(channel_projection.unresolved)
                channel_events = tuple(
                    event
                    for event in channel_projection.events
                    if demand.start_seconds <= event.time_seconds <= demand.end_seconds
                )
        elif channel_projection is not None:
            unresolved.extend(channel_projection.unresolved)
            channel_events = tuple(
                event
                for event in channel_projection.events
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
            modeled_external_conditional_healing=modeled_external_conditional_healing,
            channel_events=channel_events,
            modeled_channel_healing=sum(event.modeled_heal for event in channel_events),
        )
