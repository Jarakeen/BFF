from __future__ import annotations

"""Canonical scoring with one named gear witness and one full resource armor state.

This layer composes a proven named-set realization with one proof-reduced
Light/Medium/Heavy + Divines/Infused + armor-glyph state for max
Health/Magicka/Stamina. It owns no stat arithmetic: the completed ``PlayerBuild``
is re-scored through the existing ``ExtremeOptimizationService`` so armor weight,
glyph slot scaling, Infused, Divines/Mundus, set effects, food, potions, class/race
state, and reviewed passive progression meet in one canonical context.

For the max-resource path, reviewed max-rank Undaunted Mettle progression is
applied through ``ExtremeHypotheticalUndauntedProgressionService`` when a canonical
database path is available. The +2/+4/+6% resource effect remains owned entirely by
the shared ``UndauntedPassiveInputResolver``.
"""

from typing import Any

from minmax.character_progression import CharacterProgression
from minmax.combat_effect_semantics import GameUpdate
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
    ExtremeArmorResourceWeightTraitGlyphStateService,
)
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)
from services.extreme_named_gear_canonical_stat_evaluator import (
    ExtremeNamedGearCanonicalStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


class ExtremeNamedGearResourceArmorCanonicalStatEvaluator:
    """Add one combined resource armor state plus reviewed Mettle progression."""

    def __init__(
        self,
        *,
        evaluator: ExtremeNamedGearCanonicalStatEvaluator,
        armor_state: ExtremeArmorResourceWeightTraitGlyphState,
        undaunted_progression_service: ExtremeHypotheticalUndauntedProgressionService | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.armor_state = armor_state
        self.optimizer = evaluator.optimizer
        self.class_progression_service = evaluator.progression_service

        if undaunted_progression_service is None:
            database_path = getattr(self.optimizer, "database_path", None)
            if database_path is not None:
                undaunted_progression_service = ExtremeHypotheticalUndauntedProgressionService(
                    database_path,
                    class_progression_service=self.class_progression_service,
                )
        self.undaunted_progression_service = undaunted_progression_service
        self.progression_service = (
            undaunted_progression_service or self.class_progression_service
        )

    def evaluate_candidate(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
        *,
        mundus: str = "",
        food: str = "",
        potion: str = "",
        active_buffs: tuple[str, ...] = (),
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        key = str(objective_key or "").strip().casefold()
        if key != self.armor_state.objective_key:
            raise ValueError(
                "Extreme resource armor state objective mismatch: "
                f"state={self.armor_state.objective_key!r}, requested={key!r}"
            )

        _, payload, base_unresolved = self.evaluator.evaluate_candidate(
            key,
            candidate,
            mundus=mundus,
            food=food,
            potion=potion,
            active_buffs=active_buffs,
        )
        build = PlayerBuild.from_dict(payload["build"])
        build = ExtremeArmorResourceWeightTraitGlyphStateService.materialize(
            build,
            self.armor_state,
        )

        progression = CharacterProgression(
            attributes=candidate.attributes,
            passive_ranks={},
            passive_cp_points={},
        )
        progression = self.progression_service.normalize(progression, candidate.class_route)
        normalized_buffs = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in active_buffs
                if str(value or "").strip()
            )
        )
        objective = self.optimizer.objective(key)
        armor_identity = repr(self.armor_state.identity)
        build_id = (
            f"extreme-named-gear-resource-armor:{candidate.identity}:"
            f"{armor_identity}:{mundus}:{food}:{potion}"
        )

        if normalized_buffs:
            context = self.optimizer.context_factory.build(
                character_id="extreme-named-gear-resource-armor",
                build_id=build_id,
                build=build,
                progression=progression,
                active_bar=candidate.active_bar,
                combat_state=CombatState(
                    active_buffs=normalized_buffs,
                    game_update=GameUpdate.U50,
                ),
            )
            value = self.optimizer._objective_value(context, objective)
            armor_unresolved = tuple(context.unresolved_gear_effects)
        else:
            value, armor_unresolved = self.optimizer._evaluate(
                build,
                progression=progression,
                character_id="extreme-named-gear-resource-armor",
                build_id=build_id,
                objective=objective,
                active_bar=candidate.active_bar,
            )

        output = dict(payload)
        output["build"] = build.to_dict()
        output["armor_resource_weight_trait_glyph_state"] = self.armor_state.identity
        output["armor_type_count"] = self.armor_state.armor_type_count
        output["armor_divines_count"] = self.armor_state.divines_count
        output["armor_infused_count"] = self.armor_state.infused_count
        output["armor_reviewed_glyph_delta"] = (
            self.armor_state.trait_glyph_state.direct_glyph_delta
        )
        output["armor_weights"] = self.armor_state.weight_state.identity
        output["undaunted_mettle_rank"] = progression.passive_rank("Undaunted Mettle")
        output["undaunted_mettle_progression_applied"] = bool(
            progression.owns_skill_line("Undaunted")
            and progression.passive_rank("Undaunted Mettle")
        )

        unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (*base_unresolved, *armor_unresolved)
                if str(item)
            )
        )
        return float(value), output, unresolved
