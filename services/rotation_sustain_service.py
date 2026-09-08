from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from engine.config import DEFAULT_DATABASE
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_calculation_context import BuildCalculationContext
from minmax.build_sustain import BuildSustainRun, NamedBuildAction, evaluate_named_build_sustain
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.race_repository import RaceRepository
from minmax.recovery_timing import DisplayedRecoveryResolver
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceMaximumEvent
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class RotationSustainProjection:
    """Phase 13 view of one Phase 4 resource evaluation."""

    resource: ResourceType
    run: BuildSustainRun
    series: tuple[tuple[float, float], ...]
    unresolved: tuple[str, ...]


class RotationSustainService:
    """Evaluate a generated rotation through the existing Phase 4 sustain engine."""

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        sustain_evaluator: Callable[..., BuildSustainRun] = evaluate_named_build_sustain,
        catalog_path: Path | None = None,
        progression_adapter: MinmaxCharacterProgressionAdapter | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.sustain_evaluator = sustain_evaluator
        resolved_catalog_path = (
            Path(catalog_path)
            if catalog_path is not None
            else self.database_path.with_name("characters.json")
        )
        self.progression_adapter = progression_adapter or MinmaxCharacterProgressionAdapter(
            BuildCatalogService(resolved_catalog_path)
        )

    def evaluate(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
        resource: ResourceType = ResourceType.MAGICKA,
        restoration_events: tuple[ResourceRestorationEvent, ...] = (),
        maximum_events: tuple[ResourceMaximumEvent, ...] = (),
        calculation_context: BuildCalculationContext | None = None,
        displayed_recovery_at: DisplayedRecoveryResolver | None = None,
    ) -> RotationSustainProjection:
        """Evaluate one rotation/resource with caller-verified temporal evidence.

        Canonical callers may provide the already-resolved front-bar static context,
        resource-ceiling events, and a time-aware displayed-recovery resolver. The
        Phase 4 sustain engine remains authoritative for tick cadence, action costs,
        ordering, clipping, waste, and shortfall.
        """

        self._validate_identity(build, plan)

        named_actions = self.named_actions(plan)
        progression_unresolved: tuple[str, ...] = ()
        if calculation_context is None:
            progression, progression_unresolved = self._progression(build)
            factory = BuildCalculationContextFactory(
                race_repository=RaceRepository(self.database_path),
                gear_set_repository=GearSetRepository(self.database_path),
            )
            context = factory.build(
                character_id=self._character_name(build) or "saved-character",
                build_id=self._build_name(build),
                build=build,
                progression=progression,
                active_bar="front",
                fight_duration=plan.duration_seconds,
            )
        else:
            context = calculation_context
            if context.active_bar != "front":
                raise ValueError(
                    "rotation sustain canonical calculation context must represent the front bar"
                )

        run = self.sustain_evaluator(
            build=build,
            context=context,
            resource=resource,
            duration_seconds=plan.duration_seconds,
            actions=named_actions,
            ability_cost_repository=AbilityCostRepository(self.database_path),
            cost_modifier_resolver=BuildActionCostModifierResolver(
                JewelryCostModifierRepository(self.database_path),
                JewelryTraitRepository(self.database_path),
            ),
            restoration_events=tuple(restoration_events),
            maximum_events=tuple(maximum_events),
            displayed_recovery_at=displayed_recovery_at,
        )

        unresolved = self._dedupe(
            tuple(plan.unresolved)
            + tuple(progression_unresolved)
            + tuple(context.unresolved_gear_effects)
            + tuple(run.unresolved)
        )

        return RotationSustainProjection(
            resource=resource,
            run=run,
            series=self.timeline_series(run),
            unresolved=unresolved,
        )

    @staticmethod
    def named_actions(plan: RotationPlan) -> tuple[NamedBuildAction, ...]:
        return tuple(
            NamedBuildAction(
                time_seconds=action.time_seconds,
                skill_name=str(action.name),
            )
            for action in plan.actions
            if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
            and action.name
        )

    @staticmethod
    def timeline_series(run: BuildSustainRun) -> tuple[tuple[float, float], ...]:
        points: list[tuple[float, float]] = [(0.0, float(run.timeline.starting_amount))]
        points.extend(
            (float(event.time_seconds), float(event.after))
            for event in run.timeline.events
        )
        return tuple(points)

    @classmethod
    def _validate_identity(cls, build: PlayerBuild, plan: RotationPlan) -> None:
        if cls._character_name(build).casefold() != plan.character_name.casefold():
            raise ValueError("rotation plan character identity does not match selected build")
        if cls._build_name(build).casefold() != plan.build_name.casefold():
            raise ValueError("rotation plan build identity does not match selected build")

    def _progression(self, build: PlayerBuild) -> tuple[CharacterProgression, tuple[str, ...]]:
        resolved = self.progression_adapter.resolve(build)
        if resolved.resolved and resolved.progression.owned_skill_lines:
            return resolved.progression, tuple(resolved.unresolved)

        armor_lines = {
            f"{str(entry.get('Weight', '') or '').strip().title()} Armor"
            for entry in build.Armor.values()
            if str(entry.get("Weight", "") or "").strip().casefold()
            in {"light", "medium", "heavy"}
        }
        fallback = CharacterProgression(
            attributes=AttributeAllocation(
                health=build.AttributeHealth,
                magicka=build.AttributeMagicka,
                stamina=build.AttributeStamina,
            ),
            owned_skill_lines=tuple(sorted(armor_lines)),
        )

        unresolved = list(resolved.unresolved)
        if resolved.resolved and not resolved.progression.owned_skill_lines:
            unresolved.append(
                "canonical character progression has no owned skill lines; rotation sustain "
                "used equipped-armor inference as a compatibility fallback"
            )
        else:
            unresolved.append(
                "rotation sustain could not use canonical character progression; equipped-armor "
                "skill-line ownership was inferred as a compatibility fallback"
            )
        return fallback, self._dedupe(tuple(unresolved))

    @staticmethod
    def _character_name(build: PlayerBuild) -> str:
        return str(
            getattr(build, "CharacterName", "")
            or build.Name
            or build.Gamertag
            or ""
        ).strip()

    @staticmethod
    def _build_name(build: PlayerBuild) -> str:
        return str(build.BuildName or "Current Build").strip()

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)
