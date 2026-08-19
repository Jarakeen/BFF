from __future__ import annotations

import re

from .effect_kinds import EffectKind
from .effects import Effect, EffectOperation, EffectUnit
from .gear_sets import GearSetBonus
from .stat_ids import StatId


class GearSetEffectResolver:
    """Resolve unconditional, static gear-set bonuses into Effects.

    Phase 1 intentionally handles only single-clause stat modifiers.
    Triggered, conditional, proc, cooldown, scaling, and trade-off bonuses
    return an empty list rather than being guessed at.
    """

    _COLOR_MARKUP = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
    _BONUS_PREFIX = re.compile(r"^\(\d+\s+items\)\s*", re.IGNORECASE)
    _RANGE = r"(?P<min>\d[\d,]*)\s*-\s*(?P<max>\d[\d,]*)"
    _NUMBER = r"(?P<value>\d+(?:\.\d+)?)"

    _FLAT_STATS = {
        "Maximum Health": StatId.MAX_HEALTH,
        "Maximum Magicka": StatId.MAX_MAGICKA,
        "Maximum Stamina": StatId.MAX_STAMINA,
        "Health Recovery": StatId.HEALTH_RECOVERY,
        "Magicka Recovery": StatId.MAGICKA_RECOVERY,
        "Stamina Recovery": StatId.STAMINA_RECOVERY,
        "Critical Chance": StatId.CRITICAL_CHANCE,
        "Critical Resistance": StatId.CRITICAL_RESISTANCE,
    }

    def resolve(
        self,
        bonus: GearSetBonus,
        *,
        use_max_value: bool = True,
        source: str | None = None,
    ) -> list[Effect]:
        description = bonus.description
        if not description:
            return []

        text = self._clean_description(description)
        if not text:
            return []

        source_text = source or f"Gear set bonus ({bonus.piece_count} items)"

        # Combined flat stats.
        combined = self._resolve_combined(text, source_text, use_max_value)
        if combined:
            return combined

        # Single flat stat, range form.
        for label, stat in self._FLAT_STATS.items():
            match = re.fullmatch(
                rf"Adds\s+{self._RANGE}\s+{re.escape(label)}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = self._selected_range_value(match, use_max_value)
                return [self._effect(stat, value, source_text)]

        # Single flat stat, scalar form.
        for label, stat in self._FLAT_STATS.items():
            match = re.fullmatch(
                rf"Adds\s+{self._NUMBER}\s+{re.escape(label)}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = float(match.group("value"))
                return [self._effect(stat, value, source_text)]

        # Percent Healing Done / Healing Taken.
        percent_patterns = (
            (r"Adds\s+(?P<value>\d+(?:\.\d+)?)%\s+Healing Done", StatId.HEALING_DONE),
            (r"Adds\s+(?P<value>\d+(?:\.\d+)?)%\s+Healing Taken", StatId.HEALING_TAKEN),
            (
                r"Increases your healing received by\s+(?P<value>\d+(?:\.\d+)?)%\.?",
                StatId.HEALING_TAKEN,
            ),
        )
        for pattern, stat in percent_patterns:
            match = re.fullmatch(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group("value"))
                return [self._effect(
                    stat,
                    value,
                    source_text,
                    operation=EffectOperation.ADD_PERCENT,
                    unit=EffectUnit.PERCENT,
                )]

        # Unconditional percentage stat increases. Phase 1 only accepts a
        # single clause and therefore deliberately rejects anything with a
        # qualifier, second sentence, or trade-off.
        percent_stats = {
            "Healing Done": StatId.HEALING_DONE,
            "Healing Taken": StatId.HEALING_TAKEN,
            "Critical Resistance": StatId.CRITICAL_RESISTANCE,
        }
        for label, stat in percent_stats.items():
            match = re.fullmatch(
                rf"Increases your\s+{re.escape(label)}\s+by\s+(?P<value>\d+(?:\.\d+)?)%",
                text,
                re.IGNORECASE,
            )
            if match:
                return [self._effect(
                    stat,
                    float(match.group("value")),
                    source_text,
                    operation=EffectOperation.ADD_PERCENT,
                    unit=EffectUnit.PERCENT,
                )]

        return []

    def _resolve_combined(
        self,
        text: str,
        source: str,
        use_max_value: bool,
    ) -> list[Effect]:
        combined = (
            (
                "Weapon and Spell Damage",
                (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE),
            ),
            (
                "Armor",
                (StatId.PHYSICAL_RESISTANCE, StatId.SPELL_RESISTANCE),
            ),
            (
                "Offensive Penetration",
                (StatId.PHYSICAL_PENETRATION, StatId.SPELL_PENETRATION),
            ),
        )

        for label, stats in combined:
            match = re.fullmatch(
                rf"Adds\s+{self._RANGE}\s+{re.escape(label)}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = self._selected_range_value(match, use_max_value)
                return [
                    self._effect(stat, value, source)
                    for stat in stats
                ]

            match = re.fullmatch(
                rf"Adds\s+{self._NUMBER}\s+{re.escape(label)}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = float(match.group("value"))
                return [
                    self._effect(stat, value, source)
                    for stat in stats
                ]

        return []

    @classmethod
    def _clean_description(cls, description: str) -> str:
        text = cls._COLOR_MARKUP.sub("", description).strip()
        text = cls._BONUS_PREFIX.sub("", text).strip()
        return text

    @staticmethod
    def _selected_range_value(match: re.Match[str], use_max_value: bool) -> float:
        key = "max" if use_max_value else "min"
        return float(match.group(key).replace(",", ""))

    @staticmethod
    def _effect(
        stat: StatId,
        value: float,
        source: str,
        *,
        operation: EffectOperation = EffectOperation.ADD,
        unit: EffectUnit = EffectUnit.FLAT,
    ) -> Effect:
        return Effect(
            operation=operation,
            value=value,
            source=source,
            stat=stat,
            kind=EffectKind.STAT,
            unit=unit,
        )
