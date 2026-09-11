from __future__ import annotations

from pathlib import Path

from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import SkillEffectKind
from models.build_model import PlayerBuild
from services.rotation_healer_action_healing_service import RotationHealerPeriodicHealSeed
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicMagnitudeResolution,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationRuntimeBuildContextResolver,
)


class RotationHealerPeriodicTickMagnitudeService:
    """Re-evaluate one verified periodic-heal component at one exact tick instant.

    This service owns no timing policy. ``RotationHealerPeriodicRuntimeService``
    decides whether a component snapshots at cast or recalculates per tick. When the
    reviewed policy chooses per-tick recalculation, this service rebuilds the exact
    runtime calculation context and routes the same canonical skill/component through
    existing saved-build tooltip and healing modifier math.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        tooltip_service: SavedBuildSkillTooltipService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.tooltip_service = tooltip_service or SavedBuildSkillTooltipService(
            self.database_path
        )

    def resolve(
        self,
        *,
        build: PlayerBuild,
        seed: RotationHealerPeriodicHealSeed,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver,
        time_seconds: float,
        sequence: int,
    ) -> RotationHealerPeriodicMagnitudeResolution:
        runtime_context = runtime_build_context_resolver(
            float(time_seconds),
            int(sequence),
        )
        if not runtime_context.resolved or runtime_context.context is None:
            return self._unresolved(
                *(runtime_context.unresolved or ("exact runtime build context is unresolved",))
            )

        resolution = self.tooltip_service.coefficients.resolve_name(seed.source_name)
        if resolution.rank is None:
            return self._unresolved(
                *(resolution.unresolved or ("canonical skill rank is unresolved",))
            )

        result = self.tooltip_service.evaluate_entity_id(
            build=build,
            context=runtime_context.context,
            entity_id=resolution.rank.entity_id,
        )
        if result.unresolved:
            return self._unresolved(*result.unresolved)
        if result.skill is None:
            return self._unresolved("canonical heal evaluation returned no resolved skill")

        number = int(seed.coefficient_number)
        classifications = {
            int(component.coefficient_number): component
            for component in self.tooltip_service.components.get_for_skill_rank(
                result.skill.skill_rank_id
            )
        }
        classification = classifications.get(number)
        if classification is None:
            return self._unresolved("canonical component classification unavailable")
        if classification.effect_kind is not SkillEffectKind.HEAL:
            return self._unresolved("component is not canonically classified as healing")
        if classification.is_dot is not True:
            return self._unresolved("component is not canonically classified as periodic healing")

        actual_by_number = {
            int(trace.coefficient_number): float(trace.output_value)
            for trace in result.component_actual_effect_trace
        }
        if number in actual_by_number:
            return RotationHealerPeriodicMagnitudeResolution(
                modeled_heal=actual_by_number[number]
            )

        component_by_number = {
            int(trace.coefficient_number): float(trace.final_value)
            for trace in result.components
        }
        if number not in component_by_number:
            return self._unresolved("canonical periodic healing component value is unavailable")

        return RotationHealerPeriodicMagnitudeResolution(
            modeled_heal=component_by_number[number]
        )

    @staticmethod
    def _unresolved(*messages: str) -> RotationHealerPeriodicMagnitudeResolution:
        return RotationHealerPeriodicMagnitudeResolution(
            modeled_heal=None,
            unresolved=tuple(
                dict.fromkeys(
                    str(message).strip()
                    for message in messages
                    if str(message).strip()
                )
            ),
        )


__all__ = ["RotationHealerPeriodicTickMagnitudeService"]
