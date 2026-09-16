from __future__ import annotations

"""Resolve reviewed max-resource gear descriptions with explicit runtime conditions.

This resolver is deliberately narrow. It owns only descriptions whose resource
mutation and condition are explicit enough to materialize without inferring proc
uptime or combat sequencing. It complements ``GearSetEffectResolver`` while these
canonical phrasings are migrated into the shared effect grammar.
"""

import re

from .effect_kinds import EffectKind
from .effects import Effect, EffectOperation, EffectUnit
from .gear_sets import GearSetBonus
from .stat_ids import StatId


class GearSetResourceConditionResolver:
    _COLOR_MARKUP = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
    _BONUS_PREFIX = re.compile(
        r"^\(\d+\s+(?:perfected\s+)?items?\)\s*",
        re.IGNORECASE,
    )
    _NUMBER_OR_RANGE = r"(?:(\d[\d,]*)\s*-\s*)?(\d[\d,]*)"

    def resolve(
        self,
        bonus: GearSetBonus,
        *,
        use_max_value: bool = True,
        source: str | None = None,
    ) -> list[Effect]:
        description = str(bonus.description or "")
        if not description.strip():
            return []

        text = self._clean(description)
        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"

        conditional_patterns = (
            (
                rf"While you have a food buff active, your Max Health is increased by {self._NUMBER_OR_RANGE}"
                rf" and Health Recovery by {self._NUMBER_OR_RANGE}\.?",
                (
                    (StatId.MAX_HEALTH, "food_buff_active"),
                    (StatId.HEALTH_RECOVERY, "food_buff_active"),
                ),
            ),
            (
                rf"While you have a drink buff active, your Max Magicka is increased by {self._NUMBER_OR_RANGE}"
                rf" and Magicka Recovery by {self._NUMBER_OR_RANGE}\.?",
                (
                    (StatId.MAX_MAGICKA, "drink_buff_active"),
                    (StatId.MAGICKA_RECOVERY, "drink_buff_active"),
                ),
            ),
            (
                rf"While you have a drink buff active, your Max Stamina is increased by {self._NUMBER_OR_RANGE}"
                rf" and Stamina Recovery by {self._NUMBER_OR_RANGE}\.?",
                (
                    (StatId.MAX_STAMINA, "drink_buff_active"),
                    (StatId.STAMINA_RECOVERY, "drink_buff_active"),
                ),
            ),
            (
                rf"While you have a pet active, your Max Magicka is increased by {self._NUMBER_OR_RANGE}\.?",
                ((StatId.MAX_MAGICKA, "pet_active"),),
            ),
        )

        for pattern, specs in conditional_patterns:
            match = re.fullmatch(pattern, text, re.IGNORECASE)
            if match:
                values = self._ordered_values(match, use_max_value)
                return [
                    self._effect(stat, values[index], source_text, condition=condition)
                    for index, (stat, condition) in enumerate(specs)
                ]

        armor_master = re.fullmatch(
            r"While you have an Armor ability slotted, your Max Health is increased by "
            r"(?P<value>\d+(?:\.\d+)?)%\.\s*When you use an Armor ability while in combat, "
            r"your Physical and Spell Resistance is increased by "
            r"(?:\d[\d,]*\s*-\s*)?\d[\d,]* for \d+(?:\.\d+)? seconds?\.?",
            text,
            re.IGNORECASE,
        )
        if armor_master:
            return [
                self._effect(
                    StatId.MAX_HEALTH,
                    float(armor_master.group("value")),
                    source_text,
                    condition="armor_ability_slotted",
                    operation=EffectOperation.ADD_PERCENT,
                    unit=EffectUnit.PERCENT,
                )
            ]

        group_resource_patterns = (
            (
                rf"Increases Max Health by {self._NUMBER_OR_RANGE} for you and up to \d+ other group members"
                r" within [\d.]+ meters of you\. This bonus persists through death\.?",
                (StatId.MAX_HEALTH,),
            ),
            (
                rf"Increases Max Magicka and Max Stamina by {self._NUMBER_OR_RANGE} for you and up to \d+ other group members"
                r" within [\d.]+ meters of you\. This bonus persists through death\.?",
                (StatId.MAX_MAGICKA, StatId.MAX_STAMINA),
            ),
        )
        for pattern, stats in group_resource_patterns:
            match = re.fullmatch(pattern, text, re.IGNORECASE)
            if match:
                value = self._ordered_values(match, use_max_value)[0]
                return [self._effect(stat, value, source_text) for stat in stats]

        return []

    @classmethod
    def _clean(cls, description: str) -> str:
        text = cls._COLOR_MARKUP.sub("", description).strip()
        text = cls._BONUS_PREFIX.sub("", text).strip()
        return " ".join(text.split())

    @staticmethod
    def _ordered_values(match: re.Match[str], use_max_value: bool) -> tuple[float, ...]:
        captures = match.groups()
        values: list[float] = []
        for index in range(0, len(captures), 2):
            minimum = captures[index]
            maximum = captures[index + 1]
            chosen = maximum if use_max_value or minimum is None else minimum
            values.append(float(str(chosen).replace(",", "")))
        return tuple(values)

    @staticmethod
    def _effect(
        stat: StatId,
        value: float,
        source: str,
        *,
        condition: str | None = None,
        operation: EffectOperation = EffectOperation.ADD,
        unit: EffectUnit = EffectUnit.FLAT,
    ) -> Effect:
        return Effect(
            operation=operation,
            value=float(value),
            source=source,
            stat=stat,
            kind=EffectKind.STAT,
            unit=unit,
            condition=condition,
        )


__all__ = ["GearSetResourceConditionResolver"]
