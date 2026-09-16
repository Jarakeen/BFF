from __future__ import annotations

"""Resolve reviewed conditional gear bonuses that modify healing sheet stats.

This resolver is intentionally narrow. It owns only conditional Healing Done /
Critical Healing grammar whose condition can be represented by an existing
canonical condition marker. Triggered windows and unproven runtime states remain
outside this resolver and therefore fail closed elsewhere.
"""

import re

from .effect_kinds import EffectKind
from .effects import Effect, EffectOperation, EffectUnit
from .gear_sets import GearSetBonus
from .stat_ids import StatId


BLIND_PATH_DISTANT_HEAL_CONDITION = "blind_path_target_beyond_15m"


class GearSetHealingConditionResolver:
    """Map reviewed conditional healing modifiers into canonical Effects."""

    _COLOR_MARKUP = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
    _BONUS_PREFIX = re.compile(
        r"^\(\d+\s+(?:perfected\s+)?items?\)\s*",
        re.IGNORECASE,
    )

    def resolve(
        self,
        bonus: GearSetBonus,
        *,
        use_max_value: bool = True,
        source: str | None = None,
    ) -> list[Effect]:
        text = self._clean_description(bonus.description)
        if not text:
            return []
        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"

        match = re.fullmatch(
            r"While you have a food buff active, your Critical Damage and "
            r"Critical Healing is increased by (?P<value>\d+(?:\.\d+)?)%\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            value = float(match.group("value"))
            return [
                self._effect(
                    StatId.CRITICAL_DAMAGE,
                    value,
                    source_text,
                    condition="food_buff_active",
                ),
                self._effect(
                    StatId.CRITICAL_HEALING,
                    value,
                    source_text,
                    condition="food_buff_active",
                ),
            ]

        match = re.fullmatch(
            r"Whenever you successfully Dodge, increase your Critical Damage and "
            r"Critical Healing by (?:(?P<min>\d+(?:\.\d+)?)\s*-\s*)?"
            r"(?P<max>\d+(?:\.\d+)?)% for 10 seconds\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            selected = match.group("max") if use_max_value or match.group("min") is None else match.group("min")
            value = float(selected)
            return [
                self._effect(
                    StatId.CRITICAL_DAMAGE,
                    value,
                    source_text,
                    condition="successful_dodge_recent",
                ),
                self._effect(
                    StatId.CRITICAL_HEALING,
                    value,
                    source_text,
                    condition="successful_dodge_recent",
                ),
            ]

        match = re.fullmatch(
            r"Adds 200% Status Effect Chance while your Health is above 50%\.\s*"
            r"Adds (?P<value>\d+(?:\.\d+)?)% Healing Done while your Health is 50% or less\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            return [
                self._effect(
                    StatId.HEALING_DONE,
                    float(match.group("value")),
                    source_text,
                    condition="wearer_health_at_or_below_50_percent",
                )
            ]

        match = re.fullmatch(
            r"Casting an Earthen Heart ability grants you (?:a )?Rock Stance for 10 seconds\.\s*"
            r"While (?:you\s*are\s+)?on your Primary Weapon you gain Molten Stance, "
            r"granting you Major Heroism, generating \d+(?:\.\d+)? Ultimate every "
            r"\d+(?:\.\d+)? seconds\.\s*While (?:you\s*are\s+)?on your Secondary "
            r"Weapon you gain Obsidian Stance, increasing your Healing Done and "
            r"damage\s*shields by (?P<value>\d+(?:\.\d+)?)%\.\s*"
            r"Bar Swapping will swap your Stance automatically\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            return [
                self._effect(
                    StatId.HEALING_DONE,
                    float(match.group("value")),
                    source_text,
                    condition="basalt_blooded_obsidian_stance_active",
                )
            ]

        match = re.fullmatch(
            r"While you have a permanent pet active, gain \d[\d,]* Health and "
            r"\d[\d,]* Armor\.\s*While you do not have a permanent pet active, "
            r"increase your Damage Done and Healing Done by (?P<value>15(?:\.0+)?)%\.\s*"
            r"This value is reduced to 7(?:\.0+)?% while affected by Battle Spirit\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            return [
                self._effect(
                    StatId.HEALING_DONE,
                    float(match.group("value")),
                    source_text,
                    condition="beacon_of_oblivion_no_permanent_pet_pve",
                )
            ]

        match = re.fullmatch(
            r"Increase the strength of your Damage Shields by (?P<shield>\d+(?:\.\d+)?)% "
            r"to you and targets within 15 meters of you\.\s*Increase your Healing Done by "
            r"(?P<heal>\d+(?:\.\d+)?)% to targets more than 15 meters away from you\.?",
            text,
            re.IGNORECASE,
        )
        if match:
            return [
                self._effect(
                    StatId.HEALING_DONE,
                    float(match.group("heal")),
                    source_text,
                    condition=BLIND_PATH_DISTANT_HEAL_CONDITION,
                )
            ]

        return []

    @classmethod
    def _clean_description(cls, description: str) -> str:
        text = cls._COLOR_MARKUP.sub("", str(description or "")).strip()
        return cls._BONUS_PREFIX.sub("", text).strip()

    @staticmethod
    def _effect(
        stat: StatId,
        value: float,
        source: str,
        *,
        condition: str,
    ) -> Effect:
        return Effect(
            operation=EffectOperation.ADD_PERCENT,
            value=float(value),
            source=source,
            stat=stat,
            kind=EffectKind.STAT,
            unit=EffectUnit.PERCENT,
            condition=condition,
        )


__all__ = [
    "BLIND_PATH_DISTANT_HEAL_CONDITION",
    "GearSetHealingConditionResolver",
]
