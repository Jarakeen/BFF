from __future__ import annotations

"""Resolve reviewed H1 gear effects that require an explicit pre-event witness."""

import re

from minmax.effect_kinds import EffectKind
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.eso_markup import normalize_eso_markup
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


BLESSING_OF_HIGH_ISLE_CONDITION = "recently_healed_in_combat"


class ExtremeActualHealGearPreconditionEffectResolver:
    """Map exact reviewed temporary self-stat effects behind H1 preconditions."""

    _BLESSING_OF_HIGH_ISLE = re.compile(
        r"^\(5 items\)\s*When you are healed while in combat,\s*"
        r"increase your Weapon and Spell Damage by\s+"
        r"(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)\s+for\s+5 seconds\.?$",
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
        match = self._BLESSING_OF_HIGH_ISLE.fullmatch(" ".join(description.split()))
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
                stat=stat,
                kind=EffectKind.STAT,
                unit=EffectUnit.FLAT,
                condition=BLESSING_OF_HIGH_ISLE_CONDITION,
            )
            for stat in (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE)
        ]


__all__ = [
    "BLESSING_OF_HIGH_ISLE_CONDITION",
    "ExtremeActualHealGearPreconditionEffectResolver",
]
