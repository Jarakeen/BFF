from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from minmax.build_calculation_context import BuildCalculationContext
from minmax.build_candidate_damage import (
    ModeledDamagePotency,
    measure_modeled_damage_potency,
)
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationPlan
from services.rotation_dd_action_damage_event_service import (
    RotationDDActionDamageProjection,
)
from services.rotation_dd_damage_projection_service import (
    RotationDDDamageInstance,
    RotationDDDamageProjection,
    RotationDDDamageProjectionService,
)


DamageEvaluator = Callable[..., ModeledDamagePotency]


@dataclass(frozen=True)
class RotationDDCanonicalDamageProjection:
    """Canonical direct-action DD projection for one exact rotation horizon.

    ``known_damage`` remains useful for diagnostics, but ``total_damage`` and DPS
    are withheld whenever any required action/event evidence is unresolved. That
    keeps partial direct-damage coverage from masquerading as a complete parse.
    """

    action_projection: RotationDDActionDamageProjection
    damage_projection: RotationDDDamageProjection
    known_damage: float
    total_damage: float | None
    projected_dps: float | None
    unresolved: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.total_damage is not None and not self.unresolved


class RotationDDCanonicalDamageService:
    """Resolve projected direct DD actions through the canonical static DD engine.

    The action projector owns component identity and direct-vs-DoT timing
    boundaries. The canonical DD evaluator owns offensive stats, critical chance,
    penetration, target resistance, and expected single-event damage. The damage
    projection service owns timeline aggregation.

    This service deliberately does not infer DoT ticks, proc events, execute
    scaling, target-health transitions, light/heavy attack damage, or runtime buff
    windows. Missing evidence in any of those required areas remains unresolved.
    """

    def __init__(
        self,
        *,
        damage_evaluator: DamageEvaluator = measure_modeled_damage_potency,
        projection_service: RotationDDDamageProjectionService | None = None,
    ) -> None:
        self.damage_evaluator = damage_evaluator
        self.projection_service = projection_service or RotationDDDamageProjectionService()

    def project(
        self,
        *,
        plan: RotationPlan,
        context: BuildCalculationContext,
        evaluation_context: EvaluationContext,
        action_projection: RotationDDActionDamageProjection,
    ) -> RotationDDCanonicalDamageProjection:
        instances: list[RotationDDDamageInstance] = []
        evaluation_unresolved: list[str] = []

        for projected in action_projection.events:
            measurement = self.damage_evaluator(
                context=context,
                event=projected.event,
                evaluation_context=evaluation_context,
            )
            event_id = (
                f"{projected.sequence}:{projected.coefficient_number}:"
                f"{projected.time_seconds:g}:{projected.source_name.casefold()}"
            )
            unresolved = tuple(
                f"{projected.source_name} coefficient {projected.coefficient_number} "
                f"at {projected.time_seconds:g}s: {item}"
                for item in measurement.unresolved
            )
            if measurement.value is None and not unresolved:
                unresolved = (
                    f"{projected.source_name} coefficient {projected.coefficient_number} "
                    f"at {projected.time_seconds:g}s: canonical damage value unavailable",
                )
            evaluation_unresolved.extend(unresolved)
            instances.append(
                RotationDDDamageInstance(
                    time_seconds=projected.time_seconds,
                    source_name=projected.source_name,
                    expected_damage=(
                        float(measurement.value)
                        if measurement.value is not None and not unresolved
                        else None
                    ),
                    event_id=event_id,
                    unresolved=unresolved,
                )
            )

        damage_projection = self.projection_service.project(
            plan=plan,
            instances=tuple(instances),
        )
        unresolved = self._dedupe(
            tuple(action_projection.unresolved)
            + tuple(evaluation_unresolved)
            + tuple(damage_projection.unresolved)
        )
        total_damage = None if unresolved else damage_projection.total_damage
        projected_dps = (
            None
            if total_damage is None
            else total_damage / float(plan.duration_seconds)
        )
        return RotationDDCanonicalDamageProjection(
            action_projection=action_projection,
            damage_projection=damage_projection,
            known_damage=damage_projection.known_damage,
            total_damage=total_damage,
            projected_dps=projected_dps,
            unresolved=unresolved,
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))
