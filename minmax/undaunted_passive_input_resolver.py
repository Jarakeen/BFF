from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .gear_stat_inputs import GearCalculationInputs
from .passive_math import undaunted_mettle_resource_percent


class UndauntedPassiveInputResolver:
    """Apply verified standing Undaunted passives to shared inputs.

    Only Undaunted Mettle belongs here today. Undaunted Command is triggered
    by synergy activation and therefore remains outside standing character
    state.
    """

    @staticmethod
    def _equipped_armor_type_count(build: PlayerBuild) -> int:
        weights = {
            str(entry.get("Weight", "") or "").strip().casefold()
            for entry in build.Armor.values()
        }
        return len(weights.intersection({"light", "medium", "heavy"}))

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        undaunted_passives_owned: bool = False,
    ) -> GearCalculationInputs:
        if not undaunted_passives_owned:
            return result

        armor_type_count = self._equipped_armor_type_count(build)
        resource_percent = undaunted_mettle_resource_percent(armor_type_count)
        if not resource_percent:
            return result

        source = PercentContribution("Undaunted: Undaunted Mettle", resource_percent)
        return replace(
            result,
            health=replace(
                result.health,
                skill_percent_contributions=result.health.skill_percent_contributions + (source,),
            ),
            magicka=replace(
                result.magicka,
                skill_percent_contributions=result.magicka.skill_percent_contributions + (source,),
            ),
            stamina=replace(
                result.stamina,
                skill_percent_contributions=result.stamina.skill_percent_contributions + (source,),
            ),
            applied_effect_count=result.applied_effect_count + 3,
        )
