from __future__ import annotations

"""Canonical scoring with one named gear witness and one reviewed armor state fixed.

This layer composes the already-proven named-set realization with one reviewed
seven-piece armor weight/static-trait state. It performs no armor math itself.
The combined ``PlayerBuild`` is re-scored through the same canonical
``ExtremeOptimizationService`` so Divines, armor-weight passives, base armor, and
other shared mechanics are resolved in one build state.
"""

from typing import Any

from minmax.character_progression import CharacterProgression
from minmax.combat_effect_semantics import GameUpdate
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_armor_weight_trait_state_service import (
    ExtremeArmorWeightTraitState,
    ExtremeArmorWeightTraitStateService,
)
from services.extreme_named_gear_canonical_stat_evaluator import (
    ExtremeNamedGearCanonicalStatEvaluator,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


class ExtremeNamedGearArmorCanonicalStatEvaluator:
    """Add one reviewed armor state beneath the finite Mundus/food/potion axes."""

    def __init__(
        self,
        *,
        evaluator: ExtremeNamedGearCanonicalStatEvaluator,
        armor_state: ExtremeArmorWeightTraitState,
    ) -> None:
        self.evaluator = evaluator
        self.armor_state = armor_state
        self.optimizer = evaluator.optimizer
        self.progression_service = evaluator.progression_service

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
                "Extreme armor state objective mismatch: "
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
        build = ExtremeArmorWeightTraitStateService.materialize(build, self.armor_state)

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
        armor_identity = ",".join(
            f"{slot}:{weight}:{trait or 'None'}"
            for slot, weight, trait in self.armor_state.identity
        )
        build_id = (
            f"extreme-named-gear-armor:{candidate.identity}:"
            f"{armor_identity}:{mundus}:{food}:{potion}"
        )

        if normalized_buffs:
            context = self.optimizer.context_factory.build(
                character_id="extreme-named-gear-armor",
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
                character_id="extreme-named-gear-armor",
                build_id=build_id,
                objective=objective,
                active_bar=candidate.active_bar,
            )

        output = dict(payload)
        output["build"] = build.to_dict()
        output["armor_weight_trait_state"] = self.armor_state.identity
        output["armor_light_pieces"] = self.armor_state.light_pieces
        output["armor_medium_pieces"] = self.armor_state.medium_pieces
        output["armor_heavy_pieces"] = self.armor_state.heavy_pieces
        output["armor_divines_count"] = self.armor_state.divines_count
        output["armor_reviewed_direct_delta"] = self.armor_state.direct_delta

        unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (*base_unresolved, *armor_unresolved)
                if str(item)
            )
        )
        return float(value), output, unresolved
