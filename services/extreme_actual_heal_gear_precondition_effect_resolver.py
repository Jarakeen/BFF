from __future__ import annotations

"""Resolve reviewed H1 gear effects behind explicit setup or scenario witnesses."""

import re

from minmax.effect_kinds import EffectKind
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.eso_markup import normalize_eso_markup
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


BLESSING_OF_HIGH_ISLE_CONDITION = "recently_healed_in_combat"
BURNING_SPELLWEAVE_POWER_CONDITION = "burning_spellweave_power_active"
ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION = "wearer_health_above_50_percent"
TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION = "wearer_in_combat_below_50_percent_health"
PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION = "pearlescent_ward_full_group_alive"
CORAL_RIPTIDE_MAX_POWER_CONDITION = "wearer_stamina_at_or_below_50_percent"
ARMOR_OF_TRUTH_POWER_CONDITION = "armor_of_truth_power_active"
ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION = "armor_of_the_veiled_heritance_power_active"
WARRIORS_FURY_FULL_STACKS_CONDITION = "warriors_fury_full_stacks"
STYGIAN_POWER_CONDITION = "stygian_power_active"
SEVENTH_LEGION_BRUTE_POWER_CONDITION = "seventh_legion_brute_power_active"
SOULSHINE_POWER_CONDITION = "soulshine_power_active"
POWERFUL_ASSAULT_POWER_CONDITION = "powerful_assault_power_active"
CAMONNA_TONG_MAX_POWER_CONDITION = "camonna_tong_max_power_active"
RAVAGER_FULL_STACKS_CONDITION = "ravager_full_stacks"
TRACKERS_LASH_FULL_STACKS_CONDITION = "trackers_lash_full_stacks"
PELINALS_WRATH_FULL_STACKS_CONDITION = "pelinals_wrath_full_stacks"
LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION = "light_speaker_restoration_scope_active"
INNATE_AXIOM_CLASS_SCOPE_CONDITION = "innate_axiom_class_scope_active"
RED_EAGLES_FURY_WEAPON_SCOPE_CONDITION = "red_eagles_fury_weapon_scope_active"


class ExtremeActualHealGearPreconditionEffectResolver:
    """Map exact reviewed self-stat effects behind H1-owned conditions."""

    _BURNING_SPELLWEAVE = re.compile(
        r"^\(5 items\)\s*When you deal damage with a Flame Damage ability,\s*"
        r"you apply the Burning status effect to the enemy and increase your Weapon and Spell Damage by\s*"
        r"(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*for\s*8 seconds\.\s*"
        r"(?:This effect|These effects) can occur once every\s*12 seconds\.?$",
        re.IGNORECASE,
    )
    _BLESSING_OF_HIGH_ISLE = re.compile(r"^\(5 items\)\s*When you are healed while in combat,\s*increase your Weapon and Spell Damage by\s+(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)\s+for\s+5 seconds\.?$", re.IGNORECASE)
    _ANCIENT_DRAGONGUARD = re.compile(r"^\(5 items\)\s*Adds\s+(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)\s+Weapon and Spell Damage while your Health is above 50%\.\s*Adds\s+\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s+Physical and Spell Resistance while your Health is 50% or less\.?$", re.IGNORECASE)
    _TITANBORN_STRENGTH = re.compile(r"^\(5 items\)\s*Adds\s+(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s+Weapon and Spell Damage and\s+\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s+Offensive Penetration\.\s*While in combat, this bonus doubles when you are under 75% Health and quadruples when you are under 50% Health\.?$", re.IGNORECASE)
    _PEARLESCENT_WARD = re.compile(r"^\(5 items\)\s*Grants you and up to 11 other group members Pearlescent Ward\.\s*This bonus persists through death\.\s*Pearlescent Ward increases Weapon and Spell Damage by up to\s*(?P<max>\d[\d,]*)\s*based on the number of group members that are alive\.\s*(?:Current\s+\d[\d,]*\s+Weapon and Spell Damage\.\s*)?Pearlescent Ward increases damage reduction from non-player enemies.*$", re.IGNORECASE)
    _CORAL_RIPTIDE = re.compile(
        r"^\(5 items\)\s*Increases your Weapon and Spell Damage by up to\s*"
        r"(?P<max>\d[\d,]*),?\s*based on your missing Stamina, reaching the maximum at\s*"
        r"50% Stamina\.\s*(?:Current bonus:\s*\d[\d,]*\s*Weapon and Spell Damage\.?\s*)?$",
        re.IGNORECASE,
    )
    _ARMOR_OF_TRUTH = re.compile(r"^\(5 items\)\s*When you deal damage to an enemy who is Off Balance, your Weapon and Spell Damage are increased by\s*(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*for\s*10 seconds\.?$", re.IGNORECASE)
    _ARMOR_OF_THE_VEILED_HERITANCE = re.compile(r"^\(5 items\)\s*When you interrupt an enemy, you gain\s*(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*Weapon and Spell Damage for\s*15 seconds\.\s*Your Bash attacks deal\s*\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*more damage\.?$", re.IGNORECASE)
    _WARRIORS_FURY = re.compile(r"^\(5 items\)\s*When you take damage, your Weapon and Spell Damage is increased by\s*(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*for\s*5 seconds, stacking up to\s*20 times\.\s*This effect can occur once every half second\.\s*Upon reaching 20 stacks, the duration is doubled but can no longer be refreshed\.?$", re.IGNORECASE)
    _STYGIAN = re.compile(r"^\(5 items\)\s*When you leave Sneak or invisibility while in combat, your Weapon and Spell Damage is increased by\s*(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*for\s*15 seconds\.?$", re.IGNORECASE)
    _SEVENTH_LEGION_BRUTE = re.compile(r"^\(5 items\)\s*When you cast an ability that grants Major or Minor Resolve while in combat, you gain\s*(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*Weapon and Spell Damage and\s*\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*Health Recovery for\s*15 seconds\.\s*This effect can occur every\s*15 seconds\.?$", re.IGNORECASE)
    _SOULSHINE = re.compile(r"^\(5 items\)\s*Activating an ability with a cast or channel time grants you\s*(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*Weapon and Spell Damage for\s*5 seconds\.?$", re.IGNORECASE)
    _POWERFUL_ASSAULT = re.compile(r"^\(5 items\)\s*When you cast an Assault ability while in combat, you and up to 5 group members within 12 meters gain\s*(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*Weapon and Spell Damage for\s*15 seconds\.?$", re.IGNORECASE)
    _CAMONNA_TONG = re.compile(r"^\(5 items\)\s*When you kill a monster and gain Experience Points, gain 1 Weapon and Spell Damage for every 50 Experience Points the monster is worth for 30 seconds\.\s*This bonus can stack up to a maximum of\s*(?P<max>\d[\d,]*)\s*Weapon and Spell Damage\.\s*This item set is not affected by Experience Point boosting effects\.?$", re.IGNORECASE)
    _RAVAGER = re.compile(r"^\(5 items\)\s*Each time you attempt to reduce the target's Physical or Spell Resistance, you gain a stack of Ravager for 5 seconds, increasing your Weapon and Spell Damage by\s*(?P<max>\d[\d,]*)\.\s*You can gain a stack every 1 second\.\s*At 4 stacks, the duration doubles but cannot be refreshed\.?$", re.IGNORECASE)
    _TRACKERS_LASH = re.compile(r"^\(5 items\)\s*When your attack is dodged, increase your Weapon and Spell Damage by\s*(?P<max>\d[\d,]*)\s*for\s*7 seconds, stacking up to\s*5 times\.\s*This effect can occur once every\s*0\.5 seconds\.?$", re.IGNORECASE)
    _PELINALS_WRATH = re.compile(r"^\(5 items\)\s*Whenever you kill an enemy you gain a damage shield that absorbs up to\s*\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*damage for\s*10 seconds and a stack of Wrath of Whitestrake for\s*10 seconds\.\s*Each stack of Wrath of Whitestrake grants you\s*(?P<max>\d[\d,]*)\s*Weapon and Spell Damage, but causes you to take\s*\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*Oblivion damage every second, up to\s*10 stacks\.\s*The damage shield scales off the higher of your Weapon or Spell Damage, and the damage scales off your Max Health\.?$", re.IGNORECASE)
    _LIGHT_SPEAKER = re.compile(r"^\(5 items\)\s*Adds\s+(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s+Weapon and Spell Damage to your Restoration Staff abilities\.?$", re.IGNORECASE)
    _INNATE_AXIOM = re.compile(r"^\(5 items\)\s*Adds\s+(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s+Weapon and Spell Damage to your Class abilities\.?$", re.IGNORECASE)
    _RED_EAGLES_FURY = re.compile(
        r"^\(5 items\)\s*Adds\s+(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s+"
        r"Weapon and Spell Damage to your Weapon Skill abilities\.\s*"
        r"Increases the cost of your Weapon Skill abilities by\s*5%\.?$",
        re.IGNORECASE,
    )

    def resolve(self, bonus: GearSetBonus, *, use_max_value: bool = True, source: str | None = None) -> list[Effect]:
        description = normalize_eso_markup(str(bonus.description or "")).text.strip()
        if not description:
            return []
        normalized = " ".join(description.split())
        checks = (
            (self._BURNING_SPELLWEAVE, BURNING_SPELLWEAVE_POWER_CONDITION, 1.0),
            (self._BLESSING_OF_HIGH_ISLE, BLESSING_OF_HIGH_ISLE_CONDITION, 1.0),
            (self._ANCIENT_DRAGONGUARD, ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION, 1.0),
            (self._TITANBORN_STRENGTH, TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION, 4.0),
            (self._PEARLESCENT_WARD, PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION, 1.0),
            (self._CORAL_RIPTIDE, CORAL_RIPTIDE_MAX_POWER_CONDITION, 1.0),
            (self._ARMOR_OF_TRUTH, ARMOR_OF_TRUTH_POWER_CONDITION, 1.0),
            (self._ARMOR_OF_THE_VEILED_HERITANCE, ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION, 1.0),
            (self._WARRIORS_FURY, WARRIORS_FURY_FULL_STACKS_CONDITION, 20.0),
            (self._STYGIAN, STYGIAN_POWER_CONDITION, 1.0),
            (self._SEVENTH_LEGION_BRUTE, SEVENTH_LEGION_BRUTE_POWER_CONDITION, 1.0),
            (self._SOULSHINE, SOULSHINE_POWER_CONDITION, 1.0),
            (self._POWERFUL_ASSAULT, POWERFUL_ASSAULT_POWER_CONDITION, 1.0),
            (self._CAMONNA_TONG, CAMONNA_TONG_MAX_POWER_CONDITION, 1.0),
            (self._RAVAGER, RAVAGER_FULL_STACKS_CONDITION, 4.0),
            (self._TRACKERS_LASH, TRACKERS_LASH_FULL_STACKS_CONDITION, 5.0),
            (self._PELINALS_WRATH, PELINALS_WRATH_FULL_STACKS_CONDITION, 10.0),
            (self._LIGHT_SPEAKER, LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION, 1.0),
            (self._INNATE_AXIOM, INNATE_AXIOM_CLASS_SCOPE_CONDITION, 1.0),
            (self._RED_EAGLES_FURY, RED_EAGLES_FURY_WEAPON_SCOPE_CONDITION, 1.0),
        )
        match = None
        condition = ""
        multiplier = 1.0
        for pattern, candidate_condition, candidate_multiplier in checks:
            match = pattern.fullmatch(normalized)
            if match is not None:
                condition = candidate_condition
                multiplier = candidate_multiplier
                break
        if match is None:
            return []
        key = "max" if use_max_value or not match.groupdict().get("min") else "min"
        raw_value = match.group(key) or match.group("max")
        value = float(raw_value.replace(",", "")) * multiplier
        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"
        return [Effect(operation=EffectOperation.ADD, value=value, source=source_text, stat=stat, kind=EffectKind.STAT, unit=EffectUnit.FLAT, condition=condition) for stat in (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE)]


__all__ = [
    "ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION",
    "ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION",
    "ARMOR_OF_TRUTH_POWER_CONDITION",
    "BLESSING_OF_HIGH_ISLE_CONDITION",
    "BURNING_SPELLWEAVE_POWER_CONDITION",
    "CAMONNA_TONG_MAX_POWER_CONDITION",
    "CORAL_RIPTIDE_MAX_POWER_CONDITION",
    "INNATE_AXIOM_CLASS_SCOPE_CONDITION",
    "LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION",
    "PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION",
    "PELINALS_WRATH_FULL_STACKS_CONDITION",
    "POWERFUL_ASSAULT_POWER_CONDITION",
    "RAVAGER_FULL_STACKS_CONDITION",
    "RED_EAGLES_FURY_WEAPON_SCOPE_CONDITION",
    "SEVENTH_LEGION_BRUTE_POWER_CONDITION",
    "SOULSHINE_POWER_CONDITION",
    "STYGIAN_POWER_CONDITION",
    "TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION",
    "TRACKERS_LASH_FULL_STACKS_CONDITION",
    "WARRIORS_FURY_FULL_STACKS_CONDITION",
    "ExtremeActualHealGearPreconditionEffectResolver",
]
