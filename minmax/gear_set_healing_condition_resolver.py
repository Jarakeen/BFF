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
        _ = use_max_value
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


__all__ = ["GearSetHealingConditionResolver"]
