from __future__ import annotations

"""Canonical scoring with named gear, resource armor, reviewed jewelry, and bars.

This layer composes a proven named-set realization with one proof-reduced
Light/Medium/Heavy + Divines/Infused + armor-glyph state for max
Health/Magicka/Stamina and, when supplied, one reviewed static resource-jewelry
trait state. It owns no stat arithmetic: the completed ``PlayerBuild`` is re-scored
through the canonical calculation stack so armor, jewelry, Mundus, set effects,
food, potions, class/race state, active-bar state, and reviewed passive progression
meet in one context.

For the max-resource path, reviewed max-rank Undaunted Mettle progression,
resource-relevant armor passive progression, reviewed active-bar passive
progression, and the hypothetical race's canonical max-rank racial progression are
applied when a canonical database path is available. Stat math remains owned by
shared canonical resolvers; this evaluator only supplies legal build/progression
evidence.
"""

from typing import Any

from minmax.character_progression import CharacterProgression
from minmax.combat_effect_semantics import GameUpdate
from minmax.combat_state import CombatState
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from models.build_model import PlayerBuild
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
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


class ExtremeNamedGearResourceArmorCanonicalStatEvaluator:
    """Add resource armor, reviewed passives/bar, jewelry, Mettle, and race progression."""

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

        if racial_progression_service is None and database_path is not None:
            racial_progression_service = ExtremeHypotheticalRacialProgressionService(database_path)
        self.racial_progression_service = racial_progression_service

        if context_factory is None:
            race_repository = getattr(self.optimizer, "race_repository", None)
            gear_set_repository = getattr(self.optimizer, "gear_set_repository", None)
            if race_repository is not None and gear_set_repository is not None:
                context_factory = Phase5BuildCalculationContextFactory(
                    race_repository=race_repository,
                    gear_set_repository=gear_set_repository,
                    mundus_repository=getattr(self.optimizer, "mundus_repository", None),
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

        normalized_buffs = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in active_buffs
                if str(value or "").strip()
            )
        )
        objective = self.optimizer.objective(key)
        armor_identity = repr(self.armor_state.identity)
        jewelry_identity = repr(self.jewelry_state.identity) if self.jewelry_state is not None else "none"
        bar_identity = repr(bar_state.identity) if bar_state is not None else "none"
        build_id = (
            f"extreme-named-gear-resource-armor-jewelry-bar:{candidate.identity}:"
            f"{armor_identity}:{jewelry_identity}:{bar_identity}:{mundus}:{food}:{potion}"
        )

        if self.context_factory is not None:
            kwargs: dict[str, Any] = {}
            if normalized_buffs:
                kwargs["combat_state"] = CombatState(
                    active_buffs=normalized_buffs,
                    game_update=GameUpdate.U50,
                )
            context = self.context_factory.build(
                character_id="extreme-named-gear-resource-armor-jewelry-bar",
                build_id=build_id,
                build=build,
                progression=progression,
                active_bar=candidate.active_bar,
                **kwargs,
            )
            value = self.optimizer._objective_value(context, objective)
            gear_unresolved = tuple(context.unresolved_gear_effects)
        elif normalized_buffs:
            context = self.optimizer.context_factory.build(
                character_id="extreme-named-gear-resource-armor-jewelry-bar",
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
                character_id="extreme-named-gear-resource-armor-jewelry-bar",
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
        unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (*base_unresolved, *bar_unresolved, *gear_unresolved)
                if str(item)
            )
        )
        return float(value), output, unresolved
