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
    """Map explicitly reviewed always-on power + H1-irrelevant tradeoff bonuses."""

    _TALFYGS_TREACHERY = re.compile(
        r"^\(5 items\)\s*Increases your Weapon and Spell Damage by\s+"
        r"(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)\.\s*"
        r"Increases your damage taken from Flame and Fighter'?s Guild abilities by\s+"
        r"(?P<damage_taken>\d+(?:\.\d+)?)%\.?$",
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

        match = self._TALFYGS_TREACHERY.fullmatch(" ".join(description.split()))
        if not match:
            return []

        key = "max" if use_max_value else "min"
        value = float(match.group(key).replace(",", ""))
        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"
        return [
            Effect(
                operation=EffectOperation.ADD,
                value=value,
                source=source_text,
                stat=StatId.WEAPON_DAMAGE,
                kind=EffectKind.STAT,
                unit=EffectUnit.FLAT,
            ),
            Effect(
                operation=EffectOperation.ADD,
                value=value,
                source=source_text,
                stat=StatId.SPELL_DAMAGE,
                kind=EffectKind.STAT,
                unit=EffectUnit.FLAT,
            ),
        ]


__all__ = ["ExtremeGearSetPowerTradeoffResolver"]
