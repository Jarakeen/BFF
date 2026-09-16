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
    "BLESSING_OF_HIGH_ISLE_CONDITION",
    "PEARLESCENT_WARD_FULL_GROUP_ALIVE_CONDITION",
    "TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION",
    "ExtremeActualHealGearPreconditionEffectResolver",
]
