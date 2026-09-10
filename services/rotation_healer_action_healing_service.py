from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from minmax.build_calculation_context import BuildCalculationContext
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import HealTemporalScope, SkillEffectKind
from models.build_model import PlayerBuild
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


@dataclass(frozen=True)
class RotationHealerResolvedHealEvent:
    """One verified direct healing component at a scheduled event time.

    ``modeled_heal`` is the canonical modeled actual-effect value for the
    component before target-specific received-heal consequences such as missing
    Health, overheal, recipient count, encounter demand, or runtime critical
    outcomes are applied.
    """

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
    """Verified delayed-heal component awaiting a source-backed delay.

    The action timestamp is the activation time, not the heal time. A separate
    delayed-runtime resolver must prove the offset before the component may become
    a timed healing event. This prevents delayed blooms from being counted as
    direct cast-time healing.
    """

    time_seconds: float
    sequence: int
    source_name: str
    coefficient_number: int
    modeled_heal: float


@dataclass(frozen=True)
class RotationHealerActionHealingProjection:
    direct_events: tuple[RotationHealerResolvedHealEvent, ...]
    periodic_seeds: tuple[RotationHealerPeriodicHealSeed, ...]
    unresolved: tuple[str, ...]
    delayed_seeds: tuple[RotationHealerDelayedHealSeed, ...] = ()


class RotationHealerActionHealingService:
    """Project scheduled healer skill actions into canonical healing consequences.

    Direct heals may attach to cast time. Periodic heals become recurring-runtime
    seeds. Delayed heals become delayed-runtime seeds. Channel-tick healing remains
    an explicit blocker until its distinct event timing is modeled.

    A legacy single ``context`` remains the default for backward compatibility.
    Callers evaluating a real dual-bar build may additionally supply
    ``contexts_by_bar``. When supplied, skill/Ultimate actions with an explicit
    front/back bar are evaluated against that exact bar's static context. Missing
    mapped bar state fails closed for that action rather than borrowing the default
    context and silently applying the wrong bar stats.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        tooltip_service: SavedBuildSkillTooltipService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.tooltip_service = tooltip_service or SavedBuildSkillTooltipService(
            self.database_path,
            component_repository=RotationHealerU50SkillComponentRepository(
                self.database_path
            ),
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
            actual_by_number = {
                int(trace.coefficient_number): float(trace.output_value)
                for trace in result.component_actual_effect_trace
            }

            for trace in result.components:
                number = int(trace.coefficient_number)
                classification = classifications.get(number)
                if classification is None:
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
            item.coefficient_number,
        )
        return RotationHealerActionHealingProjection(
            direct_events=tuple(sorted(direct_events, key=sort_key)),
            periodic_seeds=tuple(sorted(periodic_seeds, key=sort_key)),
            unresolved=self._dedupe(tuple(unresolved)),
            delayed_seeds=tuple(sorted(delayed_seeds, key=sort_key)),
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
