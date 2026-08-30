from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .block_stats import BlockCostModifier
from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs, GearStatInputResolver
from .passive_math import (
    light_armor_critical_rating,
    light_armor_magicka_recovery_percent,
    light_armor_penetration,
    light_armor_spell_resistance,
    medium_armor_crit_damage_healing_percent,
    medium_armor_stamina_recovery_percent,
    medium_armor_weapon_spell_damage_percent,
)


class ArmorPassiveInputResolver:
    """Apply verified standing armor passives to shared inputs.

    Ownership is explicit. Equipped armor weight alone does not prove the
    character has purchased/maxed the passive ranks.
    """

    @staticmethod
    def _armor_counts(build: PlayerBuild) -> tuple[int, int, int]:
        light = medium = heavy = 0
        for entry in build.Armor.values():
            weight = str(entry.get("Weight", "") or "").strip().casefold()
            if weight == "light":
                light += 1
            elif weight == "medium":
                medium += 1
            elif weight == "heavy":
                heavy += 1
        return light, medium, heavy

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        light_armor_passives_owned: bool = False,
        medium_armor_passives_owned: bool = False,
        heavy_armor_passives_owned: bool = False,
    ) -> GearCalculationInputs:
        light_count, medium_count, heavy_count = self._armor_counts(build)
        applied = result.applied_effect_count

        if light_armor_passives_owned and light_count:
            block_cost = replace(
                result.core.block_cost,
                sequential_modifiers=result.core.block_cost.sequential_modifiers
                + (BlockCostModifier("Light Armor: Block Cost Penalty", 0.03 * light_count),),
            )
            result = replace(result, core=replace(result.core, block_cost=block_cost))
            applied += 1

            magicka_recovery = light_armor_magicka_recovery_percent(light_count)
            if magicka_recovery:
                source = PercentContribution("Light Armor: Evocation", magicka_recovery)
                result = replace(
                    result,
                    magicka_recovery=replace(
                        result.magicka_recovery,
                        skill_percent_contributions=result.magicka_recovery.skill_percent_contributions + (source,),
                    ),
                )
                applied += 1

            penetration = light_armor_penetration(light_count)
            if penetration:
                contribution = StatContribution("Light Armor: Concentration", penetration)
                core = replace(
                    result.core,
                    physical_penetration=replace(
                        result.core.physical_penetration,
                        flat=result.core.physical_penetration.flat + (contribution,),
                    ),
                    spell_penetration=replace(
                        result.core.spell_penetration,
                        flat=result.core.spell_penetration.flat + (contribution,),
                    ),
                )
                result = replace(result, core=core)
                applied += 2

            spell_resistance = light_armor_spell_resistance(light_count)
            if spell_resistance:
                contribution = StatContribution("Light Armor: Spell Warding", spell_resistance)
                result = replace(
                    result,
                    core=replace(
                        result.core,
                        spell_resistance=replace(
                            result.core.spell_resistance,
                            flat=result.core.spell_resistance.flat + (contribution,),
                        ),
                    ),
                )
                applied += 1

            critical_rating = light_armor_critical_rating(light_count)
            if critical_rating:
                critical_ratio = GearStatInputResolver.critical_rating_to_ratio(critical_rating)
                contribution = StatContribution("Light Armor: Prodigy", critical_ratio)
                result = replace(
                    result,
                    core=replace(
                        result.core,
                        weapon_critical=replace(
                            result.core.weapon_critical,
                            flat=result.core.weapon_critical.flat + (contribution,),
                        ),
                        spell_critical=replace(
                            result.core.spell_critical,
                            flat=result.core.spell_critical.flat + (contribution,),
                        ),
                    ),
                )
                applied += 2

        if medium_armor_passives_owned and medium_count:
            block_cost = replace(
                result.core.block_cost,
                sequential_modifiers=result.core.block_cost.sequential_modifiers
                + (BlockCostModifier("Medium Armor: Block Cost Bonus", -0.03 * medium_count),),
            )
            result = replace(result, core=replace(result.core, block_cost=block_cost))
            applied += 1

            stamina_recovery = medium_armor_stamina_recovery_percent(medium_count)
            if stamina_recovery:
                source = PercentContribution("Medium Armor: Wind Walker", stamina_recovery)
                result = replace(
                    result,
                    stamina_recovery=replace(
                        result.stamina_recovery,
                        skill_percent_contributions=result.stamina_recovery.skill_percent_contributions + (source,),
                    ),
                )
                applied += 1

            weapon_spell_damage = medium_armor_weapon_spell_damage_percent(medium_count)
            if weapon_spell_damage:
                contribution = StatContribution("Medium Armor: Agility", weapon_spell_damage)
                result = replace(
                    result,
                    core=replace(
                        result.core,
                        weapon_damage=replace(
                            result.core.weapon_damage,
                            percent=result.core.weapon_damage.percent + (contribution,),
                        ),
                        spell_damage=replace(
                            result.core.spell_damage,
                            percent=result.core.spell_damage.percent + (contribution,),
                        ),
                    ),
                )
                applied += 2

            critical = medium_armor_crit_damage_healing_percent(medium_count)
            if critical:
                damage_contribution = StatContribution("Medium Armor: Dexterity (Critical Damage)", critical)
                healing_contribution = StatContribution("Medium Armor: Dexterity (Critical Healing)", critical)
                result = replace(
                    result,
                    core=replace(
                        result.core,
                        critical_damage=replace(
                            result.core.critical_damage,
                            additive_after_percent=result.core.critical_damage.additive_after_percent + (damage_contribution,),
                        ),
                        critical_healing=replace(
                            result.core.critical_healing,
                            additive_after_percent=result.core.critical_healing.additive_after_percent + (healing_contribution,),
                        ),
                    ),
                )
                applied += 2

        if heavy_armor_passives_owned and heavy_count:
            mitigation = replace(
                result.core.block_mitigation,
                direct_points=result.core.block_mitigation.direct_points
                + (("Heavy Armor: Block Mitigation Bonus", 0.01 * heavy_count),),
            )
            result = replace(result, core=replace(result.core, block_mitigation=mitigation))
            applied += 1

        return replace(
            result,
            applied_effect_count=applied,
        )
