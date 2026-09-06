from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from engine.config import DEFAULT_DATABASE
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_sustain import BuildSustainRun, NamedBuildAction, evaluate_named_build_sustain
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.race_repository import RaceRepository
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationActionKind, RotationPlan
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class RotationSustainProjection:
    """Phase 13 view of one Phase 4 resource evaluation."""

    resource: ResourceType
    run: BuildSustainRun
    series: tuple[tuple[float, float], ...]
    unresolved: tuple[str, ...]


class RotationSustainService:
    """Evaluate a generated rotation through the existing Phase 4 sustain engine.

    The service owns only the bridge from ``RotationPlan`` scheduled skill actions
    into Phase 4 ``NamedBuildAction`` inputs. Cost resolution, build modifiers,
    recovery timing, and resource-state math remain authoritative in Phase 4.
    """

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        sustain_evaluator: Callable[..., BuildSustainRun] = evaluate_named_build_sustain,
    ) -> None:
        self.database_path = Path(database_path)
        self.sustain_evaluator = sustain_evaluator

    def evaluate(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
        resource: ResourceType = ResourceType.MAGICKA,
    ) -> RotationSustainProjection:
        self._validate_identity(build, plan)

        named_actions = self.named_actions(plan)
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
        """Project only resource-cost-bearing named ability actions.

        Light attacks, waits, bar swaps, and potions are intentionally excluded.
        Heavy-attack restoration and potion restoration/cooldown semantics remain
        later Phase 13 temporal work rather than being fabricated here.
        """

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
        """Return graph-ready resource state including the initial state."""

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

    @staticmethod
    def _progression(build: PlayerBuild) -> tuple[CharacterProgression, tuple[str, ...]]:
        """Build the same bounded progression input proven by the Phase 4 audit.

        Character-owned skill-line persistence is not yet authoritative in every
        downstream page. Until Phase 1 adoption is complete, infer only armor lines
        visibly equipped by this build and report that assumption explicitly.
        """

        armor_lines = {
            f"{str(entry.get('Weight', '') or '').strip().title()} Armor"
            for entry in build.Armor.values()
            if str(entry.get("Weight", "") or "").strip().casefold()
            in {"light", "medium", "heavy"}
        }
        progression = CharacterProgression(
            attributes=AttributeAllocation(
                health=build.AttributeHealth,
                magicka=build.AttributeMagicka,
                stamina=build.AttributeStamina,
            ),
            owned_skill_lines=tuple(sorted(armor_lines)),
        )
        unresolved = (
            "rotation sustain currently infers equipped armor skill-line ownership; "
            "canonical character-owned progression adoption is still incomplete",
        )
        return progression, unresolved

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
