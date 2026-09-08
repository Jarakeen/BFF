from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.build_calculation_context import BuildCalculationContext
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import SkillEffectKind
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class RotationHealerResolvedHealEvent:
    """One verified non-periodic healing component at a scheduled cast time.

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
    """Verified periodic-heal component awaiting canonical runtime timing.

    A coefficient proves the per-component modeled value, not how many ticks
    occur, when the first tick lands, refresh/overwrite behavior, target lifetime,
    or encounter-effective coverage. Those semantics belong to a later runtime
    scheduler and must not be guessed here.
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


class RotationHealerActionHealingService:
    """Project scheduled healer skill actions into canonical healing consequences.

    This is the healer-side equivalent of the DD action consequence boundary.
    It preserves exact rotation timestamps and canonical saved-build heal math,
    while deliberately refusing to call one-application potency "HPS" or
    "coverage". Direct healing components can be attached to their cast time.
    Periodic healing components are preserved as seeds until duration, cadence,
    refresh behavior, and recipient/target semantics are explicitly resolved.
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

    def project(
        self,
        *,
        plan: RotationPlan,
        build: PlayerBuild,
        context: BuildCalculationContext,
    ) -> RotationHealerActionHealingProjection:
        direct_events: list[RotationHealerResolvedHealEvent] = []
        periodic_seeds: list[RotationHealerPeriodicHealSeed] = []
        unresolved: list[str] = []

        for action in plan.actions:
            if action.kind not in {
                RotationActionKind.SKILL,
                RotationActionKind.ULTIMATE,
            }:
                continue
            if not action.name:
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
                context=context,
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
                if classification.is_dot is None:
                    unresolved.append(
                        f"{action.name} coefficient {number} at {action.time_seconds:g}s: "
                        "direct-versus-periodic heal identity unavailable"
                    )
                    continue

                value = actual_by_number.get(number, float(trace.final_value))
                if classification.is_dot:
                    periodic_seeds.append(
                        RotationHealerPeriodicHealSeed(
                            time_seconds=float(action.time_seconds),
                            sequence=int(action.sequence),
                            source_name=action.name,
                            coefficient_number=number,
                            modeled_heal=value,
                        )
                    )
                else:
                    direct_events.append(
                        RotationHealerResolvedHealEvent(
                            time_seconds=float(action.time_seconds),
                            sequence=int(action.sequence),
                            source_name=action.name,
                            coefficient_number=number,
                            modeled_heal=value,
                        )
                    )

        direct = tuple(
            sorted(
                direct_events,
                key=lambda item: (
                    item.time_seconds,
                    item.sequence,
                    item.source_name.casefold(),
                    item.coefficient_number,
                ),
            )
        )
        periodic = tuple(
            sorted(
                periodic_seeds,
                key=lambda item: (
                    item.time_seconds,
                    item.sequence,
                    item.source_name.casefold(),
                    item.coefficient_number,
                ),
            )
        )
        return RotationHealerActionHealingProjection(
            direct_events=direct,
            periodic_seeds=periodic,
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(str(value).strip() for value in values if str(value).strip())
        )
