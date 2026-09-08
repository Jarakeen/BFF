from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from minmax.gear_set_effect_service import GearSetEffectService
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_blueprint_service import (
    ExtremeBlueprintResult,
    ExtremeBlueprintService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_optimization_service import ExtremeObjective


class ExtremeCompleteBlueprintService(ExtremeBlueprintService):
    """Completion layer for from-scratch Extreme objectives.

    This service deliberately reuses the canonical blueprint/context pipeline.
    Objective-specific support belongs here only when the same reviewed ESO
    mechanic changes the final whole-build value and the base blueprint has not
    yet wired that mechanic for the objective.
    """

    _WEAPON_SPELL_DAMAGE_OBJECTIVES = frozenset({"weapon_damage", "spell_damage"})

    def __init__(
        self,
        *,
        database_path: Path | None = None,
        builds_path: Path | None = None,
    ) -> None:
        super().__init__(database_path=database_path, builds_path=builds_path)
        self.extreme = ExtremeCompleteOptimizationService(
            database_path=self.database_path,
            builds_path=builds_path,
        )
        self.set_effects = GearSetEffectService(self.extreme.gear_set_repository)

    def _resting_progression(self, objective: ExtremeObjective):
        if objective.key == "weapon_damage":
            # Medium Armor static passives used by the reviewed Spell Damage
            # package raise Weapon Damage too. Reuse the same progression proof
            # instead of maintaining a second passive list.
            spell_objective = self.extreme.objective("spell_damage")
            return super()._resting_progression(spell_objective)
        return super()._resting_progression(objective)

    def _apply_resting_profile(
        self,
        build: PlayerBuild,
        objective: ExtremeObjective,
        *,
        active_bar: str,
    ):
        if objective.key != "weapon_damage":
            return super()._apply_resting_profile(
                build,
                objective,
                active_bar=active_bar,
            )

        # Expert Mage, Twin Blade and Blunt swords, and Medium Armor Agility are
        # Weapon/Spell Damage mechanics. The reviewed Spell Damage profile is
        # therefore a valid whole-build candidate for Weapon Damage as well.
        spell_objective = self.extreme.objective("spell_damage")
        candidate, label, contenders = super()._apply_resting_profile(
            build,
            spell_objective,
            active_bar=active_bar,
        )
        for field_name in ("Necklace", "Ring1", "Ring2"):
            getattr(candidate, field_name).Enchant = "Weapon Damage"
        return candidate, label, contenders

    def _blank_build(self, objective: ExtremeObjective) -> PlayerBuild:
        build = super()._blank_build(objective)
        if objective.key == "weapon_damage":
            for entry in build.Armor.values():
                entry["Enchant"] = "Max Stamina"
            for field_name in ("Necklace", "Ring1", "Ring2"):
                getattr(build, field_name).Enchant = "Weapon Damage"
        return build

    def _set_static_score(self, name: str, objective: ExtremeObjective) -> float:
        if objective.key != "critical_healing":
            return super()._set_static_score(name, objective)

        gear_set = self.extreme.gear_set_repository.get_set(name)
        if gear_set is None:
            return 0.0
        effects = self.set_effects.resolve_effects(gear_set.id, 5)
        return sum(
            float(effect.value)
            for effect in effects
            if effect.stat == StatId.CRITICAL_HEALING
        )

    def _evaluate_snapshot(
        self,
        build: PlayerBuild,
        *,
        progression,
        character_id: str,
        build_id: str,
        objective: ExtremeObjective,
        active_bar: str,
        potion_buff: str = "",
    ):
        value, unresolved = super()._evaluate_snapshot(
            build,
            progression=progression,
            character_id=character_id,
            build_id=build_id,
            objective=objective,
            active_bar=active_bar,
            potion_buff=potion_buff,
        )
        if objective.key != "weapon_damage":
            return value, unresolved

        extra_percent = self._named_percent_for_stat(
            potion_buff,
            StatId.WEAPON_DAMAGE,
        )
        value += self._resting_spell_damage_bonus(
            build,
            active_bar=active_bar,
            extra_percent=extra_percent,
        )
        return value, unresolved

    def optimize_from_scratch(
        self,
        objective_key: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> ExtremeBlueprintResult:
        result = super().optimize_from_scratch(
            objective_key,
            active_bar=active_bar,
            max_passes=max_passes,
        )
        if result.objective.key != "weapon_damage":
            return result

        corrected_notes = tuple(
            (
                "Weapon Damage currently resolves to the reviewed Sorcerer Weapon/Spell Damage standing package: Expert Mage on the active bar, dual swords, and Medium Armor Agility."
                if note.startswith("No proven class-specific standing winner is modeled")
                else note
            )
            for note in result.notes
        )
        return replace(result, notes=corrected_notes)
