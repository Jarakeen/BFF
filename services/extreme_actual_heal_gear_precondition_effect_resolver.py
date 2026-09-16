from __future__ import annotations

"""Resolve reviewed H1 gear effects behind explicit setup or scenario witnesses."""

import re

from minmax.effect_kinds import EffectKind
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.eso_markup import normalize_eso_markup
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


BLESSING_OF_HIGH_ISLE_CONDITION = "recently_healed_in_combat"
ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION = "wearer_health_above_50_percent"
TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION = "wearer_in_combat_below_50_percent_health"
PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION = "pearlescent_ward_full_group_alive"
ARMOR_OF_TRUTH_POWER_CONDITION = "armor_of_truth_power_active"
ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION = "armor_of_the_veiled_heritance_power_active"
WARRIORS_FURY_FULL_STACKS_CONDITION = "warriors_fury_full_stacks"
STYGIAN_POWER_CONDITION = "stygian_power_active"
SEVENTH_LEGION_BRUTE_POWER_CONDITION = "seventh_legion_brute_power_active"


class ExtremeActualHealGearPreconditionEffectResolver:
    """Map exact reviewed self-stat effects behind H1-owned conditions."""

    _BLESSING_OF_HIGH_ISLE = re.compile(
        r"^\(5 items\)\s*When you are healed while in combat,\s*"
        r"increase your Weapon and Spell Damage by\s+"
        r"(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)\s+for\s+5 seconds\.?$",
        re.IGNORECASE,
    )
    _ANCIENT_DRAGONGUARD = re.compile(
        r"^\(5 items\)\s*Adds\s+"
        r"(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)\s+Weapon and Spell Damage "
        r"while your Health is above 50%\.\s*Adds\s+\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s+"
        r"Physical and Spell Resistance while your Health is 50% or less\.?$",
        re.IGNORECASE,
    )
    _TITANBORN_STRENGTH = re.compile(
        r"^\(5 items\)\s*Adds\s+(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s+"
        r"Weapon and Spell Damage and\s+\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s+Offensive Penetration\.\s*"
        r"While in combat, this bonus doubles when you are under 75% Health and quadruples "
        r"when you are under 50% Health\.?$",
        re.IGNORECASE,
    )
    _PEARLESCENT_WARD = re.compile(
        r"^\(5 items\)\s*Grants you and up to 11 other group members Pearlescent Ward\.\s*"
        r"This bonus persists through death\.\s*Pearlescent Ward increases Weapon and Spell Damage "
        r"by up to\s*(?P<max>\d[\d,]*)\s*based on the number of group members that are alive\.\s*"
        r"(?:Current\s+\d[\d,]*\s+Weapon and Spell Damage\.\s*)?"
        r"Pearlescent Ward increases damage reduction from non-player enemies.*$",
        re.IGNORECASE,
    )
    _ARMOR_OF_TRUTH = re.compile(
        r"^\(5 items\)\s*When you deal damage to an enemy who is Off Balance, your Weapon and Spell Damage are increased by\s*"
        r"(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*for\s*10 seconds\.?$",
        re.IGNORECASE,
    )
    _ARMOR_OF_THE_VEILED_HERITANCE = re.compile(
        r"^\(5 items\)\s*When you interrupt an enemy, you gain\s*"
        r"(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*Weapon and Spell Damage for\s*15 seconds\.\s*"
        r"Your Bash attacks deal\s*\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*more damage\.?$",
        re.IGNORECASE,
    )
    _WARRIORS_FURY = re.compile(
        r"^\(5 items\)\s*When you take damage, your Weapon and Spell Damage is increased by\s*"
        r"(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*for\s*5 seconds, stacking up to\s*20 times\.\s*"
        r"This effect can occur once every half second\.\s*Upon reaching 20 stacks, the duration is doubled but can no longer be refreshed\.?$",
        re.IGNORECASE,
    )
    _STYGIAN = re.compile(
        r"^\(5 items\)\s*When you leave Sneak or invisibility while in combat, your Weapon and Spell Damage is increased by\s*"
        r"(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*for\s*15 seconds\.?$",
        re.IGNORECASE,
    )
    _SEVENTH_LEGION_BRUTE = re.compile(
        r"^\(5 items\)\s*When you cast an ability that grants Major or Minor Resolve while in combat, you gain\s*"
        r"(?:(?P<min>\d[\d,]*)\s*-\s*)?(?P<max>\d[\d,]*)\s*Weapon and Spell Damage and\s*"
        r"\d[\d,]*(?:\s*-\s*\d[\d,]*)?\s*Health Recovery for\s*15 seconds\.\s*"
        r"This effect can occur every\s*15 seconds\.?$",
        re.IGNORECASE,
    )

    def resolve(
        self,
        bonus: GearSetBonus,
        *,
        use_max_value: bool = True,
        source: str | None = None,
    ) -> list[Effect]:
        description = normalize_eso_markup(str(bonus.description or "")).text.strip()
        if not description:
            return []
        normalized = " ".join(description.split())

        match = self._BLESSING_OF_HIGH_ISLE.fullmatch(normalized)
        condition = BLESSING_OF_HIGH_ISLE_CONDITION
        multiplier = 1.0
        if match is None:
            match = self._ANCIENT_DRAGONGUARD.fullmatch(normalized)
            condition = ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION
            multiplier = 1.0
        if match is None:
            match = self._TITANBORN_STRENGTH.fullmatch(normalized)
            condition = TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION
            multiplier = 4.0
        if match is None:
            match = self._PEARLESCENT_WARD.fullmatch(normalized)
            condition = PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION
            multiplier = 1.0
        if match is None:
            match = self._ARMOR_OF_TRUTH.fullmatch(normalized)
            condition = ARMOR_OF_TRUTH_POWER_CONDITION
            multiplier = 1.0
        if match is None:
            match = self._ARMOR_OF_THE_VEILED_HERITANCE.fullmatch(normalized)
            condition = ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION
            multiplier = 1.0
        if match is None:
            match = self._WARRIORS_FURY.fullmatch(normalized)
            condition = WARRIORS_FURY_FULL_STACKS_CONDITION
            multiplier = 20.0
        if match is None:
            match = self._STYGIAN.fullmatch(normalized)
            condition = STYGIAN_POWER_CONDITION
            multiplier = 1.0
        if match is None:
            match = self._SEVENTH_LEGION_BRUTE.fullmatch(normalized)
            condition = SEVENTH_LEGION_BRUTE_POWER_CONDITION
            multiplier = 1.0
        if match is None:
            return []

        key = "max" if use_max_value or not match.groupdict().get("min") else "min"
        raw_value = match.group(key) or match.group("max")
        value = float(raw_value.replace(",", "")) * multiplier
        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"
        return [
            Effect(
                operation=EffectOperation.ADD,
                value=value,
                source=source_text,
                stat=stat,
                kind=EffectKind.STAT,
                unit=EffectUnit.FLAT,
                condition=condition,
            )
            for stat in (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE)
        ]


__all__ = [
    "ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION",
    "ARMOR_OF_THE_VEILED_HERITANCE_POWER_CONDITION",
    "ARMOR_OF_TRUTH_POWER_CONDITION",
    "BLESSING_OF_HIGH_ISLE_CONDITION",
    "PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION",
    "SEVENTH_LEGION_BRUTE_POWER_CONDITION",
    "STYGIAN_POWER_CONDITION",
    "TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION",
    "WARRIORS_FURY_FULL_STACKS_CONDITION",
    "ExtremeActualHealGearPreconditionEffectResolver",
]
