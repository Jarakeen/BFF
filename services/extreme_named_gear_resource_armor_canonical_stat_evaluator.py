from __future__ import annotations

"""Canonical scoring with named gear, resource armor, reviewed jewelry, bars, CP, and runtime.

This layer composes a proven named-set realization with one proof-reduced
Light/Medium/Heavy + Divines/Infused + armor-glyph state for max
Health/Magicka/Stamina and, when supplied, one reviewed static resource-jewelry
trait state. It owns no stat arithmetic: the completed ``PlayerBuild`` is re-scored
through the canonical calculation stack so armor, jewelry, Mundus, set effects,
food, potions, Champion Points, class/race state, active-bar state, reviewed runtime
state, and passive progression meet in one context.
"""

from typing import Any

from minmax.character_progression import CharacterProgression
from minmax.combat_effect_semantics import GameUpdate
from minmax.combat_state import CombatState
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from models.build_model import PlayerBuild
from services.class_mastery_repository import ClassMasteryRepository
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
    ExtremeArmorResourceWeightTraitGlyphStateService,
)
from services.extreme_hypothetical_racial_progression_service import (
    ExtremeHypotheticalRacialProgressionService,
)
from services.extreme_hypothetical_resource_active_bar_passive_progression_service import (
    ExtremeHypotheticalResourceActiveBarPassiveProgressionService,
)
from services.extreme_hypothetical_resource_armor_passive_progression_service import (
    ExtremeHypotheticalResourceArmorPassiveProgressionService,
)
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitState,
    ExtremeJewelryResourceStaticTraitStateService,
)
from services.extreme_named_gear_canonical_stat_evaluator import (
    ExtremeNamedGearCanonicalStatEvaluator,
)
from services.extreme_resource_active_bar_state_service import (
    ExtremeResourceActiveBarStateService,
)
from services.extreme_resource_candidate_runtime_condition_service import (
    ExtremeResourceCandidateRuntimeConditionService,
)
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)
from services.extreme_resource_max_health_runtime_context_service import (
    ExtremeResourceMaxHealthRuntimeContextService,
)
from services.extreme_resource_max_health_runtime_state_service import (
    ExtremeResourceMaxHealthRuntimeStateService,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


class ExtremeNamedGearResourceArmorCanonicalStatEvaluator:
    """Add resource armor, reviewed passives/bar/CP/runtime, jewelry, Mettle, and race."""

    def __init__(
        self,
        *,
        evaluator: ExtremeNamedGearCanonicalStatEvaluator,
        armor_state: ExtremeArmorResourceWeightTraitGlyphState,
        jewelry_state: ExtremeJewelryResourceStaticTraitState | None = None,
        undaunted_progression_service: ExtremeHypotheticalUndauntedProgressionService | None = None,
        resource_armor_progression_service: ExtremeHypotheticalResourceArmorPassiveProgressionService | None = None,
        active_bar_progression_service: ExtremeHypotheticalResourceActiveBarPassiveProgressionService | None = None,
        active_bar_state_service: ExtremeResourceActiveBarStateService | None = None,
        champion_point_state_service: ExtremeResourceChampionPointStateService | None = None,
        candidate_runtime_condition_service: ExtremeResourceCandidateRuntimeConditionService | None = None,
        max_health_runtime_state_service: ExtremeResourceMaxHealthRuntimeStateService | None = None,
        max_health_runtime_context_service: ExtremeResourceMaxHealthRuntimeContextService | None = None,
        racial_progression_service: ExtremeHypotheticalRacialProgressionService | None = None,
        context_factory: Phase5BuildCalculationContextFactory | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.armor_state = armor_state
        self.jewelry_state = jewelry_state
        self.optimizer = evaluator.optimizer
        self.class_progression_service = evaluator.progression_service

        if jewelry_state is not None and jewelry_state.objective_key != armor_state.objective_key:
            raise ValueError(
                "Extreme jewelry/armor objective mismatch: "
                f"jewelry={jewelry_state.objective_key!r}, armor={armor_state.objective_key!r}"
            )

        database_path = getattr(self.optimizer, "database_path", None)
        if undaunted_progression_service is None and database_path is not None:
            undaunted_progression_service = ExtremeHypotheticalUndauntedProgressionService(
                database_path,
                class_progression_service=self.class_progression_service,
            )
        self.undaunted_progression_service = undaunted_progression_service

        if resource_armor_progression_service is None and database_path is not None:
            resource_armor_progression_service = ExtremeHypotheticalResourceArmorPassiveProgressionService(
                database_path,
                objective_key=armor_state.objective_key,
                progression_service=undaunted_progression_service,
            )
        self.resource_armor_progression_service = resource_armor_progression_service

        if active_bar_progression_service is None and database_path is not None:
            active_bar_progression_service = ExtremeHypotheticalResourceActiveBarPassiveProgressionService(
                database_path,
                objective_key=armor_state.objective_key,
                progression_service=resource_armor_progression_service,
            )
        self.active_bar_progression_service = active_bar_progression_service
        self.progression_service = (
            active_bar_progression_service
            or resource_armor_progression_service
            or undaunted_progression_service
            or self.class_progression_service
        )

        if active_bar_state_service is None and database_path is not None:
            active_bar_state_service = ExtremeResourceActiveBarStateService(database_path)
        self.active_bar_state_service = active_bar_state_service

        if champion_point_state_service is None and database_path is not None:
            champion_point_state_service = ExtremeResourceChampionPointStateService(database_path)
        self.champion_point_state_service = champion_point_state_service

        if candidate_runtime_condition_service is None and database_path is not None:
            candidate_runtime_condition_service = ExtremeResourceCandidateRuntimeConditionService(
                database_path
            )
        self.candidate_runtime_condition_service = candidate_runtime_condition_service

        if (
            armor_state.objective_key == "max_health"
            and max_health_runtime_state_service is None
            and database_path is not None
        ):
            max_health_runtime_state_service = ExtremeResourceMaxHealthRuntimeStateService(
                database_path
            )
        self.max_health_runtime_state_service = max_health_runtime_state_service

        if (
            armor_state.objective_key == "max_health"
            and max_health_runtime_context_service is None
            and database_path is not None
        ):
            max_health_runtime_context_service = ExtremeResourceMaxHealthRuntimeContextService(
                mastery_repository=ClassMasteryRepository(database_path)
            )
        self.max_health_runtime_context_service = max_health_runtime_context_service

        if racial_progression_service is None and database_path is not None:
            racial_progression_service = ExtremeHypotheticalRacialProgressionService(database_path)
        self.racial_progression_service = racial_progression_service

        if context_factory is None:
            race_repository = getattr(self.optimizer, "race_repository", None)
            gear_set_repository = getattr(self.optimizer, "gear_set_repository", None)
            if race_repository is not None and gear_set_repository is not None:
                champion_point_repository = (
                    getattr(self.champion_point_state_service, "repository", None)
                    if self.champion_point_state_service is not None
                    else None
                )
                context_factory = ExtremeResourceConditionedPhase5ContextFactory(
                    race_repository=race_repository,
                    gear_set_repository=gear_set_repository,
                    mundus_repository=getattr(self.optimizer, "mundus_repository", None),
                    champion_point_repository=champion_point_repository,
                    provisioning_repository=getattr(self.optimizer, "provisioning_repository", None),
                )
        self.context_factory = context_factory

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
        if self.jewelry_state is not None and key != self.jewelry_state.objective_key:
            raise ValueError(
                "Extreme resource jewelry state objective mismatch: "
                f"state={self.jewelry_state.objective_key!r}, requested={key!r}"
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
        if self.jewelry_state is not None:
            build = ExtremeJewelryResourceStaticTraitStateService.materialize(
                build,
                self.jewelry_state,
            )

        bar_catalog = None
        bar_state = None
        if self.active_bar_state_service is not None:
            bar_catalog = self.active_bar_state_service.build(key, candidate.class_route)
            if not bar_catalog.states:
                raise ValueError("Extreme resource active-bar search produced no witness state")
            bar_state = bar_catalog.states[0]
            build = self.active_bar_state_service.materialize(
                build,
                bar_state,
                active_bar=candidate.active_bar,
            )

        runtime_catalog = None
        runtime_state = None
        if key == "max_health" and self.max_health_runtime_state_service is not None:
            runtime_catalog = self.max_health_runtime_state_service.build(candidate.class_route)
            if not runtime_catalog.states:
                raise ValueError("Extreme Max Health runtime search produced no witness state")
            runtime_state = runtime_catalog.states[0]
            build = self.max_health_runtime_state_service.materialize(build, runtime_state)

        champion_point_state = None
        if self.champion_point_state_service is not None:
            champion_point_state = self.champion_point_state_service.build(key)
            build = self.champion_point_state_service.materialize_build(
                build,
                champion_point_state,
            )

        runtime_condition_projection = None
        gear_condition_context: frozenset[str] | None = None
        if self.candidate_runtime_condition_service is not None:
            runtime_condition_projection = self.candidate_runtime_condition_service.build(
                key,
                build=build,
                active_bar=candidate.active_bar,
                food=food,
                route=candidate.class_route,
            )
            build = runtime_condition_projection.build
            gear_condition_context = runtime_condition_projection.condition_context

        progression = CharacterProgression(
            attributes=candidate.attributes,
            passive_ranks={},
            passive_cp_points={},
        )
        progression = self.progression_service.normalize(progression, candidate.class_route)
        if self.racial_progression_service is not None:
            progression = self.racial_progression_service.normalize(
                progression,
                candidate.race,
            )
        if self.champion_point_state_service is not None and champion_point_state is not None:
            progression = self.champion_point_state_service.materialize_progression(
                progression,
                champion_point_state,
            )

        normalized_buffs = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in active_buffs
                if str(value or "").strip()
            )
        )
        combat_state = (
            CombatState(active_buffs=normalized_buffs, game_update=GameUpdate.U50)
            if normalized_buffs
            else None
        )
        objective = self.optimizer.objective(key)
        armor_identity = repr(self.armor_state.identity)
        jewelry_identity = repr(self.jewelry_state.identity) if self.jewelry_state is not None else "none"
        bar_identity = repr(bar_state.identity) if bar_state is not None else "none"
        runtime_identity = repr(runtime_state.identity) if runtime_state is not None else "none"
        cp_identity = repr(champion_point_state.identity) if champion_point_state is not None else "none"
        condition_identity = (
            repr(runtime_condition_projection.state.identity)
            if runtime_condition_projection is not None
            else "none"
        )
        build_id = (
            f"extreme-named-gear-resource-armor-jewelry-bar-cp-runtime:{candidate.identity}:"
            f"{armor_identity}:{jewelry_identity}:{bar_identity}:{cp_identity}:{runtime_identity}:"
            f"{condition_identity}:{mundus}:{food}:{potion}"
        )
        character_id = "extreme-named-gear-resource-armor-jewelry-bar-cp-runtime"

        runtime_factory = self.context_factory or getattr(self.optimizer, "context_factory", None)
        if (
            key == "max_health"
            and runtime_state is not None
            and self.max_health_runtime_context_service is not None
            and runtime_factory is not None
        ):
            context = self.max_health_runtime_context_service.resolve(
                factory=runtime_factory,
                build=build,
                progression=progression,
                state=runtime_state,
                character_id=character_id,
                build_id=build_id,
                active_bar=candidate.active_bar,
                combat_state=combat_state,
                gear_condition_context=gear_condition_context,
            )
            value = self.optimizer._objective_value(context, objective)
            gear_unresolved = tuple(context.unresolved_gear_effects)
        elif self.context_factory is not None:
            kwargs: dict[str, Any] = {}
            if combat_state is not None:
                kwargs["combat_state"] = combat_state
            if (
                gear_condition_context is not None
                and hasattr(self.context_factory, "gear_inputs_with_condition")
            ):
                kwargs["gear_condition_context"] = gear_condition_context
            context = self.context_factory.build(
                character_id=character_id,
                build_id=build_id,
                build=build,
                progression=progression,
                active_bar=candidate.active_bar,
                **kwargs,
            )
            value = self.optimizer._objective_value(context, objective)
            gear_unresolved = tuple(context.unresolved_gear_effects)
        elif combat_state is not None:
            context = self.optimizer.context_factory.build(
                character_id=character_id,
                build_id=build_id,
                build=build,
                progression=progression,
                active_bar=candidate.active_bar,
                combat_state=combat_state,
            )
            value = self.optimizer._objective_value(context, objective)
            gear_unresolved = tuple(context.unresolved_gear_effects)
        else:
            value, gear_unresolved = self.optimizer._evaluate(
                build,
                progression=progression,
                character_id=character_id,
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
        output["armor_reviewed_glyph_delta"] = self.armor_state.trait_glyph_state.direct_glyph_delta
        output["armor_weights"] = self.armor_state.weight_state.identity
        if self.jewelry_state is not None:
            output["jewelry_resource_static_trait_state"] = self.jewelry_state.identity
            output["jewelry_reviewed_static_trait_delta"] = self.jewelry_state.direct_delta
        if bar_state is not None:
            output["resource_active_bar_state"] = bar_state.identity
            output["resource_active_bar_skills"] = bar_state.skills
            output["resource_active_bar_shadow_slots"] = bar_state.shadow_slots
            output["resource_active_bar_siphoning_slots"] = bar_state.siphoning_slots
            output["resource_active_bar_mages_guild_slots"] = bar_state.mages_guild_slots
            output["resource_active_bar_reviewed_percent_bonus"] = bar_state.reviewed_percent_bonus
            output["resource_active_bar_denominator_proven"] = bool(
                bar_catalog is not None and bar_catalog.denominator_proven
            )
            output["resource_active_skills_reviewed"] = (
                bar_catalog.active_skills_reviewed if bar_catalog is not None else 0
            )
        if champion_point_state is not None:
            output["resource_champion_point_state"] = champion_point_state.identity
            output["resource_champion_point_non_slottable"] = champion_point_state.non_slottable_allocations
            output["resource_champion_point_slottable"] = champion_point_state.slottable_allocations
            output["resource_champion_point_reviewed_delta"] = champion_point_state.reviewed_delta
            output["resource_champion_point_denominator_proven"] = champion_point_state.denominator_proven
        if runtime_state is not None:
            output["resource_max_health_runtime_state"] = runtime_state.identity
            output["resource_max_health_runtime_label"] = runtime_state.label
            output["resource_max_health_runtime_permanent_pet_active"] = runtime_state.permanent_pet_active
            output["resource_max_health_runtime_nothing_wasted_stacks"] = runtime_state.nothing_wasted_stacks
            output["resource_max_health_runtime_class_mastery_ability_ids"] = runtime_state.class_mastery_ability_ids
            output["resource_max_health_runtime_reviewed_percent_bonus"] = runtime_state.reviewed_percent_bonus
            output["resource_max_health_runtime_conditions"] = runtime_state.conditions
            output["resource_max_health_runtime_denominator_proven"] = bool(
                runtime_catalog is not None and runtime_catalog.denominator_proven
            )
        if runtime_condition_projection is not None:
            output["resource_runtime_condition_state"] = runtime_condition_projection.state.identity
            output["resource_runtime_required_conditions"] = runtime_condition_projection.required_conditions
            output["resource_runtime_active_conditions"] = runtime_condition_projection.active_conditions
            output["resource_runtime_condition_evidence"] = runtime_condition_projection.state.evidence
            output["resource_runtime_condition_denominator_proven"] = runtime_condition_projection.denominator_proven
            if runtime_condition_projection.skill_witnesses is not None:
                output["resource_runtime_skill_witnesses"] = runtime_condition_projection.skill_witnesses.witnesses
                output["resource_runtime_displaced_skills"] = runtime_condition_projection.skill_witnesses.displaced_skills
        output["undaunted_mettle_rank"] = progression.passive_rank("Undaunted Mettle")
        output["undaunted_mettle_progression_applied"] = bool(
            progression.owns_skill_line("Undaunted")
            and progression.passive_rank("Undaunted Mettle")
        )
        output["juggernaut_rank"] = progression.passive_rank("Juggernaut")
        output["juggernaut_progression_applied"] = bool(
            progression.owns_skill_line("Heavy Armor")
            and progression.passive_rank("Juggernaut")
        )
        output["magicka_controller_rank"] = progression.passive_rank("Magicka Controller")
        output["magicka_controller_progression_applied"] = bool(
            progression.owns_skill_line("Mages Guild")
            and progression.passive_rank("Magicka Controller")
        )
        output["racial_progression_applied"] = bool(
            self.racial_progression_service is not None
        )

        bar_unresolved = tuple(bar_catalog.unresolved) if bar_catalog is not None else ()
        cp_unresolved = tuple(champion_point_state.unresolved) if champion_point_state is not None else ()
        runtime_unresolved = tuple(runtime_catalog.unresolved) if runtime_catalog is not None else ()
        condition_unresolved = (
            tuple(runtime_condition_projection.state.unresolved_conditions)
            + tuple(runtime_condition_projection.unresolved)
            if runtime_condition_projection is not None
            else ()
        )
        if (
            runtime_condition_projection is not None
            and runtime_condition_projection.required_conditions
            and gear_condition_context is not None
            and not (
                self.context_factory is not None
                and hasattr(self.context_factory, "gear_inputs_with_condition")
            )
            and not (
                key == "max_health"
                and runtime_factory is not None
                and hasattr(runtime_factory, "gear_inputs_with_condition")
            )
        ):
            condition_unresolved = (
                *condition_unresolved,
                "Extreme runtime conditions are proven but no conditioned canonical context factory is available",
            )
        unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (
                    *base_unresolved,
                    *bar_unresolved,
                    *cp_unresolved,
                    *runtime_unresolved,
                    *condition_unresolved,
                    *gear_unresolved,
                )
                if str(item)
            )
        )
        return float(value), output, unresolved
