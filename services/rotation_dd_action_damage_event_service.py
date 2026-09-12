from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from minmax.build_calculation_context import BuildCalculationContext
from minmax.dd_damage import DDDamageEvent
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
from minmax.skill_tooltip_calculator import SkillTooltipCalculator


RotationDDActionContextResolver = Callable[[float, int], BuildCalculationContext]


@dataclass(frozen=True)
class RotationDDResolvedDamageEvent:
    time_seconds: float
    sequence: int
    source_name: str
    coefficient_number: int
    event: DDDamageEvent


@dataclass(frozen=True)
class RotationDDDotComponentSeed:
    """Verified DoT component awaiting explicit runtime timing evidence."""

    cast_time_seconds: float
    sequence: int
    source_name: str
    coefficient_number: int
    event: DDDamageEvent


@dataclass(frozen=True)
class RotationDDActionDamageProjection:
    events: tuple[RotationDDResolvedDamageEvent, ...]
    unresolved: tuple[str, ...]
    dot_components: tuple[RotationDDDotComponentSeed, ...] = ()


class RotationDDActionDamageEventService:
    """Project verified skill/Ultimate damage components from scheduled actions.

    Direct damage attaches to the scheduled cast timestamp. A caller may provide an
    exact-time context resolver so tooltip/coefficient evaluation uses the canonical
    bar active at each action's ``(time_seconds, sequence)``. Without one, the legacy
    single-context path remains available for focused/static callers.

    Verified DoT components are preserved as seeds but are not expanded into ticks
    here. Tick cadence, duration, refresh/overwrite behavior, horizon clipping, and
    later-tick stat semantics need explicit runtime evidence before a DoT becomes
    fully time-resolved damage.

    Light/heavy attacks are recognized as damage-bearing rotation actions, but this
    service does not yet own canonical weapon-attack magnitude formulas. Their
    presence is therefore explicit unresolved damage evidence rather than silently
    disappearing from a supposedly complete DD projection.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | None = None,
        component_repository: SkillComponentRepository | None = None,
        calculator: SkillTooltipCalculator | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(
            self.database_path
        )
        self.components = component_repository or SkillComponentRepository(
            self.database_path
        )
        self.calculator = calculator or SkillTooltipCalculator(self.coefficients)

    def project(
        self,
        *,
        plan: RotationPlan,
        context: BuildCalculationContext,
        context_resolver: RotationDDActionContextResolver | None = None,
    ) -> RotationDDActionDamageProjection:
        events: list[RotationDDResolvedDamageEvent] = []
        dot_components: list[RotationDDDotComponentSeed] = []
        unresolved: list[str] = []

        for action in plan.actions:
            if action.kind in {
                RotationActionKind.LIGHT_ATTACK,
                RotationActionKind.HEAVY_ATTACK,
            }:
                label = (
                    "light attack"
                    if action.kind is RotationActionKind.LIGHT_ATTACK
                    else "heavy attack"
                )
                unresolved.append(
                    f"{label} at {action.time_seconds:g}s: canonical weapon-attack damage projection unavailable"
                )
                continue

            if action.kind not in {
                RotationActionKind.SKILL,
                RotationActionKind.ULTIMATE,
            }:
                continue
            if not action.name:
                continue

            action_context = context
            if context_resolver is not None:
                try:
                    action_context = context_resolver(
                        float(action.time_seconds),
                        int(action.sequence),
                    )
                except (LookupError, ValueError) as exc:
                    unresolved.append(
                        f"{action.name} at {action.time_seconds:g}s: active-bar damage context unavailable: {exc}"
                    )
                    continue

            resolution = self.coefficients.resolve_name(action.name)
            if resolution.rank is None:
                unresolved.extend(
                    f"{action.name} at {action.time_seconds:g}s: {item}"
                    for item in resolution.unresolved
                )
                if not resolution.unresolved:
                    unresolved.append(
                        f"{action.name} at {action.time_seconds:g}s: skill rank unresolved"
                    )
                continue

            result = self.calculator.evaluate_name(action.name, action_context)
            if result.unresolved:
                unresolved.extend(
                    f"{action.name} at {action.time_seconds:g}s: {item}"
                    for item in result.unresolved
                )

            classifications = {
                int(component.coefficient_number): component
                for component in self.components.get_for_skill_rank(
                    resolution.rank.skill_rank_id
                )
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
                if classification.effect_kind is not SkillEffectKind.DAMAGE:
                    continue
                if not classification.is_complete_damage_identity:
                    unresolved.append(
                        f"{action.name} coefficient {number} at {action.time_seconds:g}s: "
                        "damage identity is incomplete"
                    )
                    continue

                event = DDDamageEvent(
                    base_value=float(trace.final_value),
                    scaling_coefficient=0.0,
                    damage_type=classification.damage_type,
                    can_crit=bool(classification.can_crit),
                    is_dot=bool(classification.is_dot),
                    is_aoe=bool(classification.is_aoe),
                )
                if classification.is_dot:
                    dot_components.append(
                        RotationDDDotComponentSeed(
                            cast_time_seconds=float(action.time_seconds),
                            sequence=int(action.sequence),
                            source_name=action.name,
                            coefficient_number=number,
                            event=event,
                        )
                    )
                    continue

                events.append(
                    RotationDDResolvedDamageEvent(
                        time_seconds=float(action.time_seconds),
                        sequence=int(action.sequence),
                        source_name=action.name,
                        coefficient_number=number,
                        event=event,
                    )
                )

        ordered = tuple(
            sorted(
                events,
                key=lambda item: (
                    item.time_seconds,
                    item.sequence,
                    item.source_name.casefold(),
                    item.coefficient_number,
                ),
            )
        )
        ordered_dots = tuple(
            sorted(
                dot_components,
                key=lambda item: (
                    item.cast_time_seconds,
                    item.sequence,
                    item.source_name.casefold(),
                    item.coefficient_number,
                ),
            )
        )
        return RotationDDActionDamageProjection(
            events=ordered,
            unresolved=self._dedupe(tuple(unresolved)),
            dot_components=ordered_dots,
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return tuple(result)


__all__ = [
    "RotationDDActionContextResolver",
    "RotationDDActionDamageEventService",
    "RotationDDActionDamageProjection",
    "RotationDDDotComponentSeed",
    "RotationDDResolvedDamageEvent",
]
