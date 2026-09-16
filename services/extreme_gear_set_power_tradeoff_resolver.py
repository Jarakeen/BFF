from __future__ import annotations

"""Resolve reviewed compound gear bonuses for Extreme sheet-power projection.

This is intentionally narrower than the shared gear-set resolver. It projects only
power terms whose companion tradeoff is proven irrelevant to the requested Extreme
sheet-power / H1 heal-amount calculation. It must not be used to claim the complete
runtime semantics of the set.
"""

import re

from minmax.effect_kinds import EffectKind
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.eso_markup import normalize_eso_markup
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


class ExtremeGearSetPowerTradeoffResolver:
    """Map explicitly reviewed always-on power + H1-irrelevant companion mechanics."""

    _TALFYGS_TREACHERY = re.compile(
        r"^\(5 items\)\s*Increases your Weapon and Spell Damage by\s+"
        r"(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)\.\s*"
        r"Increases your damage taken from Flame and Fighter'?s Guild abilities by\s+"
        r"(?P<damage_taken>\d+(?:\.\d+)?)%\.?$",
        re.IGNORECASE,
    )
    _DREUGH_KING_SLAYER = re.compile(
        r"^\(5 items\)\s*Gain Major Brutality and Sorcery at all times, increasing your Weapon and Spell Damage by\s+"
        r"(?P<power>\d+(?:\.\d+)?)%\.\s*When you kill an enemy, you gain Major Expedition for\s+"
        r"(?P<duration>\d+(?:\.\d+)?)\s+seconds, increasing your Movement Speedby\s+"
        r"(?P<speed>\d+(?:\.\d+)?)%\.?$",
        re.IGNORECASE,
    )
    _NEW_MOON_ACOLYTE = re.compile(
        r"^\(5 items\)\s*Adds\s+(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)\s+"
        r"Weapon and Spell Damage\.\s*Increases the cost of your active abilities by\s+"
        r"(?P<cost>\d+(?:\.\d+)?)%\.?$",
        re.IGNORECASE,
    )

    @staticmethod
    def _power_effects(
        *,
        operation: EffectOperation,
        value: float,
        unit: EffectUnit,
        source_text: str,
    ) -> list[Effect]:
        return [
            Effect(
                operation=operation,
                value=value,
                source=source_text,
                stat=StatId.WEAPON_DAMAGE,
                kind=EffectKind.STAT,
                unit=unit,
            ),
            Effect(
                operation=operation,
                value=value,
                source=source_text,
                stat=StatId.SPELL_DAMAGE,
                kind=EffectKind.STAT,
                unit=unit,
            ),
        ]

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
        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"

        match = self._TALFYGS_TREACHERY.fullmatch(normalized)
        if match:
            key = "max" if use_max_value else "min"
            value = float(match.group(key).replace(",", ""))
            return self._power_effects(
                operation=EffectOperation.ADD,
                value=value,
                unit=EffectUnit.FLAT,
                source_text=source_text,
            )

        match = self._DREUGH_KING_SLAYER.fullmatch(normalized)
        if match:
            value = float(match.group("power"))
            return self._power_effects(
                operation=EffectOperation.ADD_PERCENT,
                value=value,
                unit=EffectUnit.PERCENT,
                source_text=source_text,
            )

        match = self._NEW_MOON_ACOLYTE.fullmatch(normalized)
        if match:
            key = "max" if use_max_value else "min"
            value = float(match.group(key).replace(",", ""))
            return self._power_effects(
                operation=EffectOperation.ADD,
                value=value,
                unit=EffectUnit.FLAT,
                source_text=source_text,
            )

        return []


__all__ = ["ExtremeGearSetPowerTradeoffResolver"]
