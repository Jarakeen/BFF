from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from minmax.build_calculation_context import BuildCalculationContext
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import HealTemporalScope, SkillEffectKind
from models.build_model import PlayerBuild
from services.rotation_healer_caster_healing_relevance_service import (
    RotationHealerCasterHealingRelevance,
    RotationHealerCasterHealingRelevanceService,
)
from services.rotation_healer_external_conditional_healing_service import (
    RotationHealerExternalConditionalHealingService,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


@dataclass(frozen=True)
class RotationHealerResolvedHealEvent:
    """One verified direct healing component at a scheduled event time."""

    time_seconds: float
    sequence: int
    source_name: str
    coefficient_number: int
    modeled_heal: float


@dataclass(frozen=True)
class RotationHealerPeriodicHealSeed:
    """Verified periodic-heal component awaiting canonical runtime timing."""

    time_seconds: float
    sequence: int
    source_name: str
    coefficient_number: int
    modeled_heal: float


@dataclass(frozen=True)
class RotationHealerDelayedHealSeed:
    """Verified delayed-heal component awaiting a source-backed delay."""

    time_seconds: float
    sequence: int
    source_name: str
    coefficient_number: int
    modeled_heal: float


@dataclass(frozen=True)
class RotationHealerExternalConditionalHealSeed:
    """Reviewed externally-triggered healing evidence anchored to an action time.

    The seed carries source-backed effect duration and magnitude semantics but is
    not itself a timed heal event. Runtime trigger cadence/ownership must be
    separately modeled before this evidence may contribute numeric healing.
    """

    time_seconds: float
    sequence: int
    source_name: str
    skill_id: str
    effect_name: str
    duration_seconds: float
    reviewed_magnitude: float
    magnitude_unit: str
    trigger_condition: str
    provenance: tuple[str, ...]
    game_version: str


@dataclass(frozen=True)
class RotationHealerActionHealingProjection:
    direct_events: tuple[RotationHealerResolvedHealEvent, ...]
    periodic_seeds: tuple[RotationHealerPeriodicHealSeed, ...]
    unresolved: tuple[str, ...]
    delayed_seeds: tuple[RotationHealerDelayedHealSeed, ...] = ()
    external_conditional_seeds: tuple[RotationHealerExternalConditionalHealSeed, ...] = ()


class RotationHealerActionHealingService:
    """Project scheduled healer skill actions into canonical healing consequences."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        tooltip_service: SavedBuildSkillTooltipService | None = None,
        caster_healing_relevance_service: RotationHealerCasterHealingRelevanceService
        | None = None,
        external_conditional_healing_service: RotationHealerExternalConditionalHealingService
        | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.tooltip_service = tooltip_service or SavedBuildSkillTooltipService(
            self.database_path,
            component_repository=RotationHealerU50SkillComponentRepository(
                self.database_path
            ),
        )
        self.caster_healing_relevance_service = (
            caster_healing_relevance_service
            or RotationHealerCasterHealingRelevanceService()
        )
        self.external_conditional_healing_service = (
            external_conditional_healing_service
            or RotationHealerExternalConditionalHealingService()
        )

    def project(
        self,
        *,
        plan: RotationPlan,
        build: PlayerBuild,
        context: BuildCalculationContext,
        contexts_by_bar: Mapping[str, BuildCalculationContext] | None = None,
    ) -> RotationHealerActionHealingProjection:
        direct_events: list[RotationHealerResolvedHealEvent] = []
        periodic_seeds: list[RotationHealerPeriodicHealSeed] = []
        delayed_seeds: list[RotationHealerDelayedHealSeed] = []
        external_conditional_seeds: list[RotationHealerExternalConditionalHealSeed] = []
        unresolved: list[str] = []
        bar_contexts = self._normalize_bar_contexts(contexts_by_bar)

        for action in plan.actions:
            if action.kind not in {
                RotationActionKind.SKILL,
                RotationActionKind.ULTIMATE,
            }:
                continue
            if not action.name:
                continue

            action_context = context
            if bar_contexts is not None and action.bar is not None:
                bar = str(action.bar or "").strip().casefold()
                if bar in {"front", "back"}:
                    action_context = bar_contexts.get(bar)
                    if action_context is None:
                        unresolved.append(
                            f"{action.name} at {action.time_seconds:g}s: "
                            f"static build context unavailable for {bar} bar"
                        )
                        continue

            resolution = self.tooltip_service.coefficients.resolve_name(action.name)
            if resolution.rank is None:
                messages = resolution.unresolved or ("skill rank unresolved",)
                unresolved.extend(
                    f"{action.name} at {action.time_seconds:g}s: {message}"
                    for message in messages
                )
                continue

            skill_id = str(resolution.rank.entity_id or "").strip().casefold()
            skill_relevance = self.caster_healing_relevance_service.resolve(skill_id)
            if skill_relevance is not None:
                if (
                    skill_relevance.relevance
                    is RotationHealerCasterHealingRelevance.NO_CASTER_HEALING
                ):
                    continue
                if (
                    skill_relevance.relevance
                    is RotationHealerCasterHealingRelevance.EXTERNAL_CONDITIONAL_HEALING
                ):
                    evidence = self.external_conditional_healing_service.resolve(skill_id)
                    if evidence is None:
                        unresolved.append(
                            f"{action.name} at {action.time_seconds:g}s: "
                            "reviewed external-conditional healing evidence is unavailable"
                        )
                    else:
                        external_conditional_seeds.append(
                            RotationHealerExternalConditionalHealSeed(
                                time_seconds=float(action.time_seconds),
                                sequence=int(action.sequence),
                                source_name=action.name,
                                skill_id=evidence.skill_id,
                                effect_name=evidence.effect_name,
                                duration_seconds=float(evidence.duration_seconds),
                                reviewed_magnitude=float(evidence.reviewed_magnitude),
                                magnitude_unit=evidence.magnitude_unit,
                                trigger_condition=evidence.trigger_condition,
                                provenance=tuple(evidence.provenance),
                                game_version=evidence.game_version,
                            )
                        )
                        unresolved.append(
                            f"{action.name} at {action.time_seconds:g}s: "
                            "reviewed healing consequence is externally triggered and is not "
                            "modeled by caster action healing projection"
                        )
                    continue

            result = self.tooltip_service.evaluate_entity_id(
                build=build,
                context=action_context,
                entity_id=resolution.rank.entity_id,
            )
            if result.unresolved:
                unresolved.extend(
                    f"{action.name} at {action.time_seconds:g}s: {message}"
                    for message in result.unresolved
                )
            if result.skill is None:
                if not result.unresolved:
                    unresolved.append(
                        f"{action.name} at {action.time_seconds:g}s: "
                        "canonical heal evaluation returned no resolved skill"
                    )
                continue

            classifications = {
                int(component.coefficient_number): component
                for component in self.tooltip_service.components.get_for_skill_rank(
                    result.skill.skill_rank_id
                )
            }
            intentional_exclusion = getattr(
                self.tooltip_service.components,
                "is_intentionally_excluded_caster_healing_component",
                None,
            )
            actual_by_number = {
                int(trace.coefficient_number): float(trace.output_value)
                for trace in result.component_actual_effect_trace
            }

            for trace in result.components:
                number = int(trace.coefficient_number)
                classification = classifications.get(number)
                if classification is None:
                    if callable(intentional_exclusion) and intentional_exclusion(
                        skill_rank_id=result.skill.skill_rank_id,
                        coefficient_number=number,
                    ):
                        continue
                    unresolved.append(
                        f"{action.name} coefficient {number} at {action.time_seconds:g}s: "
                        "canonical component classification unavailable"
                    )
                    continue
                if classification.effect_kind is SkillEffectKind.UNKNOWN:
                    unresolved.append(
                        f"{action.name} coefficient {number} at {action.time_seconds:g}s: "
                        "effect kind unresolved"
                    )
                    continue
                if classification.effect_kind is not SkillEffectKind.HEAL:
                    continue

                temporal = classification.heal_temporal_scope
                if temporal is HealTemporalScope.CHANNEL_TICK:
                    unresolved.append(
                        f"{action.name} coefficient {number} at {action.time_seconds:g}s: "
                        "channel-tick heal runtime timing is not yet modeled"
                    )
                    continue

                value = actual_by_number.get(number, float(trace.final_value))
                if temporal is HealTemporalScope.DELAYED:
                    delayed_seeds.append(
                        RotationHealerDelayedHealSeed(
                            time_seconds=float(action.time_seconds),
                            sequence=int(action.sequence),
                            source_name=action.name,
                            coefficient_number=number,
                            modeled_heal=value,
                        )
                    )
                    continue

                if temporal is HealTemporalScope.PERIODIC or (
                    temporal is None and classification.is_dot is True
                ):
                    periodic_seeds.append(
                        RotationHealerPeriodicHealSeed(
                            time_seconds=float(action.time_seconds),
                            sequence=int(action.sequence),
                            source_name=action.name,
                            coefficient_number=number,
                            modeled_heal=value,
                        )
                    )
                    continue

                if temporal is HealTemporalScope.DIRECT or (
                    temporal is None and classification.is_dot is False
                ):
                    direct_events.append(
                        RotationHealerResolvedHealEvent(
                            time_seconds=float(action.time_seconds),
                            sequence=int(action.sequence),
                            source_name=action.name,
                            coefficient_number=number,
                            modeled_heal=value,
                        )
                    )
                    continue

                unresolved.append(
                    f"{action.name} coefficient {number} at {action.time_seconds:g}s: "
                    "direct-versus-periodic heal identity unavailable"
                )

        sort_key = lambda item: (
            item.time_seconds,
            item.sequence,
            item.source_name.casefold(),
        )
        component_sort_key = lambda item: sort_key(item) + (item.coefficient_number,)
        return RotationHealerActionHealingProjection(
            direct_events=tuple(sorted(direct_events, key=component_sort_key)),
            periodic_seeds=tuple(sorted(periodic_seeds, key=component_sort_key)),
            unresolved=self._dedupe(tuple(unresolved)),
            delayed_seeds=tuple(sorted(delayed_seeds, key=component_sort_key)),
            external_conditional_seeds=tuple(
                sorted(external_conditional_seeds, key=sort_key)
            ),
        )

    @staticmethod
    def _normalize_bar_contexts(
        contexts_by_bar: Mapping[str, BuildCalculationContext] | None,
    ) -> dict[str, BuildCalculationContext] | None:
        if contexts_by_bar is None:
            return None
        result: dict[str, BuildCalculationContext] = {}
        for raw_bar, context in contexts_by_bar.items():
            bar = str(raw_bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("healer action build-context key must be front or back")
            if bar in result:
                raise ValueError(f"duplicate healer action build-context bar: {bar}")
            result[bar] = context
        return result

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(str(value).strip() for value in values if str(value).strip())
        )
