from __future__ import annotations

"""Canonical structural scoring with one proven named gear realization fixed.

The wrapped structural evaluator remains the authority for race/class/attributes,
Mundus, food, potion identity, and explicit active buffs. We materialize only the
proven named gear witness onto its resulting PlayerBuild and then re-evaluate that
complete state through the same canonical ExtremeOptimizationService.
"""

from typing import Any

from minmax.character_progression import CharacterProgression
from minmax.combat_effect_semantics import GameUpdate
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_named_gear_build_materializer_service import (
    ExtremeNamedGearBuildMaterializerService,
)
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_structural_core_stat_record_service import ExtremeCanonicalStructuralStatEvaluator
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


class ExtremeNamedGearCanonicalStatEvaluator:
    """Add one exact named gear witness beneath existing finite-axis evaluators."""

    def __init__(
        self,
        *,
        evaluator: ExtremeCanonicalStructuralStatEvaluator,
        realization: ExtremeNamedGearSetRealization,
    ) -> None:
        self.evaluator = evaluator
        self.realization = realization
        self.optimizer = evaluator.optimizer
        self.progression_service = evaluator.progression_service

    def evaluate_candidate(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
        *,
        mundus: str = "",
        second_mundus: str = "",
        food: str = "",
        potion: str = "",
        active_buffs: tuple[str, ...] = (),
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        # Let the established structural evaluator materialize every non-gear axis.
        _, payload, base_unresolved = self.evaluator.evaluate_candidate(
            objective_key,
            candidate,
            mundus=mundus,
            food=food,
            potion=potion,
            active_buffs=active_buffs,
        )
        build = PlayerBuild.from_dict(payload["build"])
        build.SecondMundus = str(second_mundus or "").strip()
        build = ExtremeNamedGearBuildMaterializerService.materialize(
            build,
            self.realization,
            active_bar=candidate.active_bar,
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
        objective = self.optimizer.objective(objective_key)
        gear_identity = ",".join(
            f"{set_id}:{count}"
            for set_id, count in zip(self.realization.set_ids, self.realization.counts)
        ) or "none"
        build_id = (
            f"extreme-named-gear:{candidate.identity}:{gear_identity}:"
            f"{mundus}:{second_mundus}:{food}:{potion}"
        )

        if normalized_buffs:
            context = self.optimizer.context_factory.build(
                character_id="extreme-named-gear",
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
            gear_unresolved = tuple(context.unresolved_gear_effects)
        else:
            value, gear_unresolved = self.optimizer._evaluate(
                build,
                progression=progression,
                character_id="extreme-named-gear",
                build_id=build_id,
                objective=objective,
                active_bar=candidate.active_bar,
            )

        output = dict(payload)
        output["build"] = build.to_dict()
        output["mundus"] = build.Mundus
        output["second_mundus"] = build.SecondMundus
        output["gear_topology"] = self.realization.topology_signature
        output["gear_set_ids"] = tuple(self.realization.set_ids)
        output["gear_set_names"] = tuple(self.realization.set_names)
        output["gear_set_counts"] = tuple(self.realization.counts)
        output["gear_weapon_shape"] = self.realization.weapon_shape.value
        output["gear_assignments"] = tuple(
            {
                "slot": row.slot,
                "set_id": row.set_id,
                "set_name": row.set_name,
                "weapon_type": row.weapon_type,
            }
            for row in self.realization.assignments
        )
        unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (*base_unresolved, *gear_unresolved)
                if str(item)
            )
        )
        return float(value), output, unresolved
