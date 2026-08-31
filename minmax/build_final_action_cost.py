from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild

from .build_action_cost_modifiers import BuildActionCostModifierResolver
from .character_progression import CharacterProgression
from .final_action_cost import FinalActionCost, calculate_final_action_cost
from .resource_cost_modifiers import ActionCostModifierSet
from .resource_costs import BaseActionCost


@dataclass(frozen=True)
class BuildFinalActionCost:
    """Final action cost resolved from one saved build.

    ``final_cost`` is withheld whenever a selected build cost source is
    unresolved. Phase 4 must never silently calculate a partial cost while
    pretending missing modifiers do not exist.
    """

    final_cost: FinalActionCost | None
    modifiers: ActionCostModifierSet
    unresolved: tuple[str, ...] = ()


class BuildFinalActionCostResolver:
    """Bridge saved-build cost sources into the verified final-cost engine."""

    def __init__(self, modifier_resolver: BuildActionCostModifierResolver) -> None:
        self.modifier_resolver = modifier_resolver

    def resolve(
        self,
        build: PlayerBuild,
        base_cost: BaseActionCost,
        *,
        skill_line: str | None = None,
        progression: CharacterProgression | None = None,
    ) -> BuildFinalActionCost:
        resolved_modifiers = self.modifier_resolver.resolve(
            build,
            progression=progression,
        )
        if resolved_modifiers.unresolved:
            return BuildFinalActionCost(
                final_cost=None,
                modifiers=resolved_modifiers.modifiers,
                unresolved=resolved_modifiers.unresolved,
            )

        final_cost = calculate_final_action_cost(
            base_cost,
            resolved_modifiers.modifiers,
            skill_line=skill_line,
        )
        return BuildFinalActionCost(
            final_cost=final_cost,
            modifiers=resolved_modifiers.modifiers,
            unresolved=(),
        )
